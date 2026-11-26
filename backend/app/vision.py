"""AI body-plan extraction from a photo or a free-text description.

Two interchangeable providers: Claude (ANTHROPIC_API_KEY) and Google Gemini
(GEMINI_API_KEY). VISION_PROVIDER=claude|gemini picks one when both keys are set;
otherwise whichever key exists is used. With neither, callers fall back to the
keyword planner (text) or return a clear error (photos).
"""
from __future__ import annotations

import base64
import json
import os
import time
from typing import Optional

import anthropic
import requests
from pydantic import ValidationError

from .generator import BodyPlan

MODEL = os.environ.get("ORIGAMI_CLAUDE_MODEL", "claude-opus-5-5")
# The Lite model: plenty for naming a subject and its flaps, and far less likely than the
# flagship Flash model to be overloaded for free-tier keys.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_ATTEMPTS = 3
GEMINI_RETRY_DELAY = 1.5  # seconds; grows with each retry
NO_KEY ="Set GEMINI_API_KEY or ANTHROPIC_API_KEY on the backend to enable photo identification."

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string", "description": "Short name of the object, e.g. 'koi fish'."},
        "category": {"type": "string", "enum": ["bird", "fish", "quadruped", "flower", "insect",
                                                 "container", "plane", "geometric", "other"]},
        "appendages": {"type": "array", "items": {"type": "string"},
                       "description": "Parts that each need their own origami flap, most important first."},
        "search_terms": {"type": "array", "items": {"type": "string"},
                         "description": "2-5 search phrases for existing origami models of this subject."},
        "notes": {"type": "string", "description": "One sentence on what makes this subject hard or easy to fold."},
        "recognized": {"type": "boolean", "description": "False if the image has no clear foldable subject."},
    },
    "required": ["subject", "category", "appendages", "search_terms", "notes", "recognized"],
    "additionalProperties": False,
}

SYSTEM = (
    "You help an origami app plan a model. Identify the single main subject the user wants "
    "to fold and describe its body plan for uniaxial origami: list the parts that would each "
    "need a separate flap (head, tail, each wing, each leg or leg pair, petals, fins). Keep "
    "appendages to the ones a simple model needs (usually 1-6). Search terms should be what "
    "an origami tutorial title would call it."
)


class VisionUnavailable(RuntimeError):
    pass


_client: Optional[anthropic.Anthropic] = None


def _has_claude() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _has_gemini() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def provider() -> Optional[str]:
    """The provider to use: 'claude', 'gemini', or None when no key is configured."""
    choice = os.environ.get("VISION_PROVIDER", "").strip().lower()
    if choice == "claude" and _has_claude():
        return "claude"
    if choice == "gemini" and _has_gemini():
        return "gemini"
    if _has_claude():
        return "claude"
    if _has_gemini():
        return "gemini"
    return None


def available() -> bool:
    return provider() is not None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not _has_claude():
            raise VisionUnavailable(NO_KEY)
        _client = anthropic.Anthropic()
    return _client


def _to_plan(data: dict, source: str) -> BodyPlan:
    if not data.pop("recognized", True):
        raise VisionUnavailable("No clear object found in the photo. Try a closer, uncluttered shot.")
    try:
        return BodyPlan(**data, source=source)
    except (TypeError, ValidationError) as e:
        raise VisionUnavailable("The AI returned an unexpected answer; try again.") from e


def _call(content: list) -> BodyPlan:
    if provider() == "gemini":
        return _call_gemini(content)
    if provider() is None:
        raise VisionUnavailable(NO_KEY)
    return _call_claude(content)


def _gemini_schema(schema: dict) -> dict:
    """Gemini's responseSchema is an OpenAPI subset: drop keys it rejects."""
    out = {k: v for k, v in schema.items() if k != "additionalProperties"}
    if "properties" in out:
        out["properties"] = {k: _gemini_schema(v) for k, v in out["properties"].items()}
    if "items" in out:
        out["items"] = _gemini_schema(out["items"])
    return out


def _call_gemini(content: list) -> BodyPlan:
    parts = []
    for block in content:
        if block["type"] == "image":
            src = block["source"]
            parts.append({"inline_data": {"mime_type": src["media_type"], "data": src["data"]}})
        else:
            parts.append({"text": block["text"]})
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": _gemini_schema(PLAN_SCHEMA),
        },
    }
    r = None
    for attempt in range(GEMINI_ATTEMPTS):
        if attempt:
            time.sleep(GEMINI_RETRY_DELAY * attempt)
        try:
            r = requests.post(
                GEMINI_URL.format(model=GEMINI_MODEL),
                headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
                json=body,
                timeout=60,
            )
        except requests.RequestException as e:
            if attempt == GEMINI_ATTEMPTS - 1:
                raise VisionUnavailable("Could not reach Gemini; try again.") from e
            continue
        # 500/503 are Gemini's "overloaded, try again" answers; anything else is final.
        if r.status_code not in (500, 503):
            break
    if r.status_code == 503:
        raise VisionUnavailable("Gemini is overloaded right now; try again in a minute.")
    if r.status_code in (401, 403):
        raise VisionUnavailable("Gemini API key was rejected.")
    if r.status_code == 429:
        raise VisionUnavailable("Gemini is rate-limited right now (free-tier limit?); try again shortly.")
    if r.status_code == 400:
        msg = r.json().get("error", {}).get("message", "") if r.headers.get("content-type", "").startswith("application/json") else ""
        if "API key" in msg:
            raise VisionUnavailable("Gemini API key was rejected.")
        raise VisionUnavailable(f"Gemini could not read that input: {msg or 'bad request'}")
    if not r.ok:
        raise VisionUnavailable("Could not reach Gemini; try again.")

    payload = r.json()
    candidates = payload.get("candidates") or []
    if not candidates:
        if payload.get("promptFeedback", {}).get("blockReason"):
            raise VisionUnavailable("Gemini declined to identify this image.")
        raise VisionUnavailable("Gemini returned no answer.")
    text = "".join(p.get("text", "") for p in candidates[0].get("content", {}).get("parts", []))
    if not text:
        raise VisionUnavailable("Gemini declined to identify this image.")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise VisionUnavailable("Gemini returned an unexpected answer; try again.") from e
    return _to_plan(data, "gemini")


def _call_claude(content: list) -> BodyPlan:
    client = _get_client()
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=SYSTEM,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": PLAN_SCHEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": content}],
        )
    except anthropic.AuthenticationError as e:
        raise VisionUnavailable("Anthropic API key was rejected.") from e
    except anthropic.RateLimitError as e:
        raise VisionUnavailable("Claude is rate-limited right now; try again shortly.") from e
    except anthropic.BadRequestError as e:
        raise VisionUnavailable(f"Claude could not read that input: {e.message}") from e
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        raise VisionUnavailable("Could not reach Claude; try again.") from e

    if response.stop_reason == "refusal":
        raise VisionUnavailable("Claude declined to identify this image.")
    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise VisionUnavailable("Claude returned no answer.")
    return _to_plan(json.loads(text), "claude")


def plan_from_image(image: bytes, media_type: str, hint: str = "") -> BodyPlan:
    if media_type not in {"image/jpeg", "image/png", "image/gif", "image/webp"}:
        raise VisionUnavailable("Upload a JPEG, PNG, GIF or WebP image.")
    data = base64.standard_b64encode(image).decode("utf-8")
    prompt = "What should I fold to make an origami version of this?"
    if hint:
        prompt += f" The user adds: {hint}"
    return _call([
        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}},
        {"type": "text", "text": prompt},
    ])


def plan_from_text(query: str) -> BodyPlan:
    return _call([{"type": "text", "text": f"I want to fold: {query}"}])
