"""Provider selection and the Gemini path, with the HTTP call faked."""
import json

import pytest

from app import vision


class FakeResponse:
    def __init__(self, status: int, payload: dict):
        self.status_code = status
        self._payload = payload
        self.ok = 200 <= status < 300
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._payload


PLAN = {
    "subject": "koi fish", "category": "fish", "appendages": ["head", "tail", "fin"],
    "search_terms": ["koi"], "notes": "Fins are short.", "recognized": True,
}


def gemini_ok(plan=PLAN):
    return FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": json.dumps(plan)}]}}]})


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "GEMINI_API_KEY", "VISION_PROVIDER"):
        monkeypatch.delenv(k, raising=False)


@pytest.fixture
def capture(monkeypatch):
    calls = []

    def install(response):
        def fake_post(url, headers, json, timeout):
            calls.append({"url": url, "headers": headers, "json": json})
            return response
        monkeypatch.setattr(vision.requests, "post", fake_post)
        return calls
    return install


def test_no_keys_means_unavailable():
    assert vision.provider() is None
    assert not vision.available()
    with pytest.raises(vision.VisionUnavailable, match="GEMINI_API_KEY"):
        vision.plan_from_text("crane")


def test_provider_selection(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    assert vision.provider() == "gemini"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    assert vision.provider() == "claude"  # Claude wins by default when both are set
    monkeypatch.setenv("VISION_PROVIDER", "gemini")
    assert vision.provider() == "gemini"
    monkeypatch.delenv("GEMINI_API_KEY")
    assert vision.provider() == "claude"  # requested provider has no key: use the one that does


def test_gemini_photo_request_and_plan(monkeypatch, capture):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = capture(gemini_ok())
    plan = vision.plan_from_image(b"\x89PNG fake", "image/png", "the orange one")
    assert plan.subject == "koi fish" and plan.category == "fish" and plan.source == "gemini"

    req = calls[0]
    assert req["headers"]["x-goog-api-key"] == "test-key"
    assert req["url"].endswith(f"/models/{vision.GEMINI_MODEL}:generateContent")
    parts = req["json"]["contents"][0]["parts"]
    assert parts[0]["inline_data"]["mime_type"] == "image/png"
    assert "the orange one" in parts[1]["text"]
    schema = req["json"]["generationConfig"]["responseSchema"]
    assert "additionalProperties" not in json.dumps(schema)


def test_gemini_unrecognized_image(monkeypatch, capture):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    capture(gemini_ok({**PLAN, "recognized": False}))
    with pytest.raises(vision.VisionUnavailable, match="No clear object"):
        vision.plan_from_image(b"x", "image/jpeg")


@pytest.mark.parametrize("response, message", [
    (FakeResponse(403, {}), "rejected"),
    (FakeResponse(400, {"error": {"message": "API key not valid."}}), "rejected"),
    (FakeResponse(429, {}), "rate-limited"),
    (FakeResponse(200, {"promptFeedback": {"blockReason": "SAFETY"}}), "declined"),
    (FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}), "unexpected"),
    (FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": "{\"subject\": 1}"}]}}]}), "unexpected"),
    (FakeResponse(500, {}), "Could not reach"),
])
def test_gemini_errors(monkeypatch, capture, response, message):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    capture(response)
    with pytest.raises(vision.VisionUnavailable, match=message):
        vision.plan_from_text("crane")


def test_api_falls_back_to_keywords_when_gemini_fails(monkeypatch, capture):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setenv("GEMINI_API_KEY", "k")
    capture(FakeResponse(429, {}))
    r = TestClient(app).post("/api/generate", json={"query": "swan"}).json()
    assert r["plan"]["source"] == "keywords"
    assert "rate-limited" in r["warning"]
    assert TestClient(app).get("/api/health").json()["vision_provider"] == "gemini"
