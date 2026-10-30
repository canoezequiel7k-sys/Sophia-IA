from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from companera.application.prompt_builder import build_messages, build_system_prompt
from companera.application.reply_parser import parse_reply
from companera.application.quota import classify_quota, QuotaState
from companera.domain.models import CheckIn, Reply, TokenUsage
from companera.infrastructure.profile_store import ProfileStore
from companera.infrastructure.secrets import SecretStore
from companera.infrastructure.usage_tracker import UsageTracker

logger = logging.getLogger("sophia.router")


class ModelRouter:
    def __init__(self, project_root: Path, settings=None, clients=None, usage_tracker=None, quota_state=None) -> None:
        self.project_root = project_root
        self.settings = settings
        self.secrets = SecretStore(project_root)
        store = ProfileStore(project_root, settings.model if settings else "")
        self._profiles, self._fallback_chain = store.load()
        self._profile_store = store
        self._active_id = settings.active_model if settings and settings.active_model else self._profiles[0].id
        if self._active_id not in profiles_ids(self._profiles):
            self._active_id = self._profiles[0].id
        self._clients = clients or {}
        self._usage = usage_tracker or UsageTracker(project_root / "data" / "uso.json")
        self._quota = quota_state or QuotaState()
        self._client_factory = None

    def profiles(self):
        return list(self._profiles)

    def active(self):
        return next((p for p in self._profiles if p.id == self._active_id), self._profiles[0])

    def set_active(self, profile_id: str) -> tuple[bool, str]:
        profile = next((p for p in self._profiles if p.id == profile_id), None)
        if profile is None:
            return False, f"Modelo desconocido: {profile_id}"
        if profile.key_env and not self.secrets.is_set(profile.key_env):
            return False, f"Falta {profile.key_env} en .env"
        self._active_id = profile_id
        if self.settings is not None:
            self.settings.active_model = profile_id
            from pathlib import Path
            self.settings.save(self.project_root / "data" / "settings.json")
        return True, profile.label

    def _client_for(self, profile):
        if profile.id in self._clients:
            return self._clients[profile.id]
        from companera.infrastructure.gemini_client import GeminiClient
        from companera.infrastructure.openai_compat_client import OpenAICompatClient
        if profile.kind == "gemini":
            client = GeminiClient(profile, self.secrets)
        else:
            client = OpenAICompatClient(profile, self.secrets)
        self._clients[profile.id] = client
        return client

    def _error_reply(self, error_code: str, profile_label: str = "") -> Reply:
        messages = {
            "no_key": f"Falta configurar la clave para {profile_label or 'este modelo'} en `.env`.",
            "invalid_key": "La clave no es válida o no tiene permiso. Revisá la configuración.",
            "bad_request": "El proveedor rechazó la solicitud.",
            "quota_minute": "Alcancé el límite por minuto. Probá de nuevo en unos segundos.",
            "quota_day": "El modelo llegó al límite diario. Probá de nuevo después de medianoche del Pacífico.",
            "quota": "No quedó cupo disponible. Probá de nuevo más tarde.",
            "server": "El proveedor tuvo un problema temporal. Probá de nuevo.",
            "network": f"No pude conectar con {profile_label or 'el proveedor'}. Revisá tu conexión a internet.",
            "parse": "No pude interpretar la respuesta del proveedor.",
        }
        return Reply(messages.get(error_code, "No pude comunicarme."), "aside", False, error_code, model_label=profile_label)

    def generate_reply(self, user_message: str, history: list[CheckIn] | None = None) -> Reply:
        active = self.active()
        system = build_system_prompt(self.project_root, True)
        messages = build_messages(history, user_message, 8)
        now = datetime.now(timezone.utc)
        ids = [active.id] + ([x for x in self._fallback_chain if x != active.id] if getattr(self.settings, "auto_fallback", False) else [])
        if active.key_env and not self.secrets.is_set(active.key_env):
            return self._error_reply("no_key", active.label)
        attempted = 0
        for pid in ids[:3]:
            profile = next((p for p in self._profiles if p.id == pid), None)
            if profile is None:
                continue
            if self._quota.blocked_until(pid, now):
                continue
            if profile.key_env and not self.secrets.is_set(profile.key_env):
                continue
            if pid != active.id and pid not in getattr(self.settings, "acknowledged_providers", []):
                continue
            attempted += 1
            try:
                raw = self._client_for(profile).complete(system, messages)
                reply = parse_reply(raw.text)
                usage = raw.usage
                if usage.total <= 0:
                    prompt_text = system + "\n" + "\n".join(m.text for m in messages)
                    prompt_tokens = max(1, len(prompt_text) // 4)
                    completion_tokens = max(1, len(reply.text) // 4)
                    usage = TokenUsage(prompt_tokens, completion_tokens, prompt_tokens + completion_tokens)
                reply = Reply(reply.text, reply.expression, True, None, reply.mood, reply.topic,
                              reply.facts, reply.title, reply.target, reply.target_label,
                              usage, profile.label)
                self._usage.record(profile.id, usage, now)
                if pid != active.id:
                    reply = Reply(reply.text, reply.expression, True, reply.error_code, reply.mood, reply.topic,
                                  reply.facts, reply.title, reply.target, reply.target_label,
                                  reply.usage, reply.model_label)
                return reply
            except Exception as err:
                code = getattr(err, "code", "network")
                if code == "quota" or code.startswith("quota_") or code in ("server", "network"):
                    from companera.application.quota import QuotaInfo
                    detail = getattr(err, "detail", "")
                    info = classify_quota(detail)
                    if code.startswith("quota_"):
                        info = QuotaInfo(code.replace("quota_", ""))
                    if code == "quota":
                        if info.kind == "day":
                            code = "quota_day"
                        elif info.kind == "minute":
                            code = "quota_minute"
                    self._quota.mark(profile.id, info, now)
                    if getattr(self.settings, "auto_fallback", False) and attempted < 3:
                        continue
                return self._error_reply(code, profile.label)
        return self._error_reply("network", active.label)

    def analyze_screen(self, user_message: str, image_b64: str) -> Reply:
        profile = self.active()
        if not profile.supports_vision:
            return Reply("Este modelo no puede ver imágenes.", "aside", False, "unsupported_vision", model_label=profile.label)
        system = build_system_prompt(self.project_root, True)
        messages = build_messages(None, user_message, 8)
        try:
            raw = self._client_for(profile).complete(system, messages, image_b64=image_b64)
            reply = parse_reply(raw.text)
            usage = raw.usage
            if usage.total <= 0:
                prompt_text = system + "\n" + "\n".join(m.text for m in messages) + "\n[image]"
                prompt_tokens = max(1, len(prompt_text) // 4)
                completion_tokens = max(1, len(reply.text) // 4)
                usage = TokenUsage(prompt_tokens, completion_tokens, prompt_tokens + completion_tokens)
            self._usage.record(profile.id, usage, datetime.now(timezone.utc))
            return Reply(reply.text, reply.expression, True, None, reply.mood, reply.topic, reply.facts,
                         reply.title, reply.target, reply.target_label, usage, profile.label)
        except Exception as err:
            return self._error_reply(getattr(err, "code", "network"), profile.label)

    def generate_screen_reply(self, user_message: str, image_b64: str) -> Reply:
        return self.analyze_screen(user_message, image_b64)


def profiles_ids(profiles) -> set[str]:
    return {p.id for p in profiles}
