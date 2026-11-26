"""Claude-powered body-plan extraction from a photo or a free-text description.

Optional: if no Anthropic credentials are configured, callers fall back to the
keyword planner (text) or return a clear error (photos).
"""
from __future__ import annotations

import base64
import json
import os
from typing import Optional

import anthropic

from .generator import BodyPlan

MODEL = os.environ.get("ORIGAMI_CLAUDE_MODEL", "claude-opus-5-5")

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


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            raise VisionUnavailable("Set ANTHROPIC_API_KEY in backend/.env to enable photo identification.")
        _client = anthropic.Anthropic()
    return _client


def available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _call(content: list) -> BodyPlan:
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
    data = json.loads(text)
    if not data.pop("recognized", True):
        raise VisionUnavailable("No clear object found in the photo. Try a closer, uncluttered shot.")
    return BodyPlan(**data, source="claude")


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
