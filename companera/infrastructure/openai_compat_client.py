from __future__ import annotations

import json
from typing import Callable
from urllib.parse import urlparse

from companera.domain.models import TokenUsage
from companera.infrastructure.http_json import HttpStatusError, ConnectionFailed
from companera.infrastructure.provider_errors import ProviderError, RawCompletion


class OpenAICompatClient:
    def __init__(self, profile, secrets, post: Callable | None = None) -> None:
        if profile.base_url.startswith("http://") and (urlparse(profile.base_url).hostname or "") not in ("localhost", "127.0.0.1"):
            raise ValueError("base_url insegura")
        self.profile = profile
        self.secrets = secrets
        self.post = post

    def complete(self, system_prompt: str, messages, image_b64: str | None = None) -> RawCompletion:
        key = self.secrets.get(self.profile.key_env) if self.profile.key_env else ""
        if self.profile.key_env and not key:
            raise ProviderError("no_key")
        api_messages = [{"role": "system", "text": system_prompt}] + [
            {"role": "user" if m.role == "user" else "assistant", "content": m.text} for m in messages
        ]
        api_messages[0] = {"role": "system", "content": system_prompt}
        payload = {"model": self.profile.model, "messages": api_messages,
                   "temperature": 0.8, "max_tokens": 2048}
        if self.profile.supports_json:
            payload["response_format"] = {"type": "json_object"}
        url = self.profile.base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        try:
            from companera.infrastructure.http_json import post_json
            response = (self.post or post_json)(url, headers, payload, self.profile.timeout)
            data = json.loads(response.body)
        except HttpStatusError as err:
            lower = err.body_text.lower()
            if err.status in (401, 403) or (err.status == 400 and "api key" in lower and "invalid" in lower):
                raise ProviderError("invalid_key") from None
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
                raise ProviderError("server") from None
            raise ProviderError("network") from None
        except ConnectionFailed:
            raise ProviderError("network") from None
        except json.JSONDecodeError:
            raise ProviderError("parse") from None
        try:
            raw = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError):
            raise ProviderError("parse") from None
        u = data.get("usage") or {}
        prompt = int(u.get("prompt_tokens", 0) or 0)
        completion = int(u.get("completion_tokens", 0) or 0)
        total = int(u.get("total_tokens", prompt + completion) or (prompt + completion))
        return RawCompletion(raw, TokenUsage(prompt, completion, total))
