from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from companera.domain.models import ModelProfile

logger = logging.getLogger("sophia.models")


def _gemini_model(project_root: Path) -> str:
    try:
        from companera.infrastructure.gemini_service import load_env_file
        env = load_env_file(project_root)
    except Exception:
        env = {}
    return os.environ.get("GEMINI_MODEL") or env.get("GEMINI_MODEL") or "gemini-3.1-flash-lite-preview"


class ProfileStore:
    def __init__(self, project_root: Path, settings_model: str = "") -> None:
        self.path = project_root / "data" / "models.json"
        self.project_root = project_root
        self.settings_model = settings_model

    def default_profiles(self) -> list[ModelProfile]:
        model = os.environ.get("GEMINI_MODEL") or self.settings_model or _gemini_model(self.project_root)
        return [
            ModelProfile("gemini-lite", "Gemini Flash-Lite", "gemini", model, key_env="GEMINI_API_KEY"),
            ModelProfile("groq-free", "Groq Llama 3.3 70B", "openai_compat",
                         model="llama-3.3-70b-versatile", base_url="https://api.groq.com/openai/v1",
                         key_env="GROQ_API_KEY", supports_json=True, supports_vision=False, timeout=15.0),
            ModelProfile("openrouter-free", "OpenRouter Free", "openai_compat",
                         model="meta-llama/llama-3.3-70b-instruct:free", base_url="https://openrouter.ai/api/v1",
                         key_env="OPENROUTER_API_KEY", supports_json=True, supports_vision=False, timeout=20.0),
            ModelProfile("mistral-free", "Mistral Small", "openai_compat",
                         model="mistral-small-latest", base_url="https://api.mistral.ai/v1",
                         key_env="MISTRAL_API_KEY", supports_json=True, supports_vision=False, timeout=15.0),
            ModelProfile("ollama-local", "Ollama Local", "openai_compat",
                         model="llama3.2:3b", base_url="http://127.0.0.1:11434/v1",
                         key_env="", supports_json=True, supports_vision=False, timeout=30.0),
        ]

    def load(self) -> tuple[list[ModelProfile], list[str]]:
        defaults = self.default_profiles()
        if not self.path.exists():
            self.save(defaults, [defaults[0].id])
            return defaults, [defaults[0].id]
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            profiles: list[ModelProfile] = []
            seen: set[str] = set()
            for item in raw.get("profiles", []):
                pid = str(item.get("id", "")).strip()
                kind = str(item.get("kind", "")).strip()
                if not pid or pid in seen or kind not in ("gemini", "openai_compat"):
                    raise ValueError("profile inválido")
                base_url = str(item.get("base_url", "")).strip()
                if kind == "openai_compat" and base_url.startswith("http://"):
                    from urllib.parse import urlparse
                    host = urlparse(base_url).hostname or ""
                    if host not in ("localhost", "127.0.0.1"):
                        raise ValueError("base_url insegura")
                profiles.append(ModelProfile(
                    pid, str(item.get("label", pid)).strip(), kind,
                    str(item.get("model", "")).strip(), base_url,
                    str(item.get("key_env", "")).strip(),
                    bool(item.get("supports_json", True)),
                    bool(item.get("supports_vision", False)),
                    float(item.get("timeout", 15.0)),
                ))
                seen.add(pid)
            if not profiles:
                raise ValueError("sin perfiles")
            existing = {p.id for p in profiles}
            added = False
            for profile in defaults:
                if profile.id not in existing:
                    profiles.append(profile)
                    added = True
            fallback = [str(x) for x in raw.get("fallback_chain", [])]
            if not fallback:
                fallback = [defaults[0].id]
            if added:
                self.save(profiles, fallback)
            return profiles, fallback
        except Exception:
            logger.warning("data/models.json está dañado; se usan perfiles por defecto")
            return defaults, [defaults[0].id]

    def save(self, profiles: list[ModelProfile], fallback_chain: list[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"profiles": [{
            "id": p.id, "label": p.label, "kind": p.kind, "model": p.model,
            "base_url": p.base_url, "key_env": p.key_env,
            "supports_json": p.supports_json, "supports_vision": p.supports_vision,
            "timeout": p.timeout,
        } for p in profiles], "fallback_chain": fallback_chain}
        tmp: Path | None = None
        try:
            with NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, delete=False, suffix=".json") as handle:
                tmp = Path(handle.name)
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            tmp.replace(self.path)
        finally:
            if tmp is not None and tmp.exists():
                tmp.unlink(missing_ok=True)
