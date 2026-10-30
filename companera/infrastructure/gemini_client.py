from __future__ import annotations

import json
from typing import Any, Callable

from companera.domain.models import TokenUsage, VALID_EXPRESSIONS, Mood, Topic
from companera.infrastructure.http_json import HttpStatusError, ConnectionFailed
from companera.infrastructure.provider_errors import ProviderError, RawCompletion


class GeminiClient:
    def __init__(self, profile, secrets, post: Callable | None = None) -> None:
        self.profile = profile
        self.secrets = secrets
        self.post = post

    def complete(self, system_prompt: str, messages, image_b64: str | None = None) -> RawCompletion:
        key = self.secrets.get(self.profile.key_env)
        if not key:
            raise ProviderError("no_key")
        contents: list[dict[str, Any]] = []
        for message in messages:
            role = "user" if message.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": message.text}]})
        if image_b64:
            contents.append({"role": "user", "parts": [
                {"inline_data": {"mime_type": "image/png", "data": image_b64}},
                {"text": "Analizá esta captura y respondé con JSON."},
            ]})
        schema = {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "expression": {"type": "string", "enum": sorted(VALID_EXPRESSIONS)},
                "mood": {"type": "string", "enum": [x.value for x in Mood]},
                "topic": {"type": "string", "enum": [x.value for x in Topic]},
                "facts": {"type": "array", "items": {"type": "string"}},
                "title": {"type": "string"},
                "target": {"type": "string", "enum": ["none", "clock", "tray", "active_window"]},
                "target_label": {"type": "string"},
            },
            "required": ["text", "expression", "mood", "topic", "title", "target", "target_label"],
        }
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]}, "contents": contents,
            "generationConfig": {"temperature": 0.8, "maxOutputTokens": 2048,
                                 "responseMimeType": "application/json", "responseSchema": schema},
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.profile.model}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": key}
        try:
            from companera.infrastructure.http_json import post_json
            response = (self.post or post_json)(url, headers, payload, self.profile.timeout)
            data = json.loads(response.body)
        except HttpStatusError as err:
            lower = err.body_text.lower()
            if err.status in (401, 403):
                raise ProviderError("invalid_key", detail="") from None
            if err.status == 400 and ("api key" in lower or "invalid" in lower and "key" in lower):
                raise ProviderError("invalid_key", detail="") from None
            if err.status == 400:
                raise ProviderError("bad_request", detail="payload inválido") from None
            if err.status == 429:
                retry_text = err.body_text
                header_retry = err.headers.get("retry-after") or err.headers.get("Retry-After")
                if header_retry:
                    retry_text += f" retryDelay {header_retry}s"
                raise ProviderError("quota", detail=retry_text) from None
            if err.status == 404:
                raise ProviderError("bad_request", detail="modelo no encontrado") from None
            if 500 <= err.status < 600:
                raise ProviderError("server", detail="") from None
            raise ProviderError("network", detail="") from None
        except ConnectionFailed:
            raise ProviderError("network") from None
        except json.JSONDecodeError:
            raise ProviderError("parse") from None
        try:
            candidate = data["candidates"][0]
            finish = str(candidate.get("finishReason", ""))
            raw = candidate["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError):
            raise ProviderError("parse") from None
        meta = data.get("usageMetadata") or {}
        prompt = int(meta.get("promptTokenCount", 0) or 0)
        completion = int(meta.get("completionTokenCount", meta.get("candidatesTokenCount", 0)) or 0)
        total = int(meta.get("totalTokenCount", prompt + completion) or (prompt + completion))
        return RawCompletion(raw, TokenUsage(prompt, completion, total), finish)
