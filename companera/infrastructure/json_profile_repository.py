from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

logger = logging.getLogger("sophia.profile")
SENSITIVE_RE = re.compile(r"(?i)(contraseña|password|clave|api[_-]?key|dni|documento|tarjeta)")

@dataclass(frozen=True)
class UserProfile:
    facts: list[str]
    updated_at: datetime


class JsonProfileRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> UserProfile:
        if not self.path.exists():
            return UserProfile([], datetime.now())
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            facts = [str(f)[:120] for f in data.get("facts", []) if isinstance(f, str)][:50]
            updated = datetime.fromisoformat(data["updated_at"])
            return UserProfile(facts, updated)
        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
            logger.exception("No se pudo cargar el perfil; se usa uno vacío")
            return UserProfile([], datetime.now())

    def add(self, facts: tuple[str, ...] | list[str]) -> None:
        current = self.load()
        combined: list[str] = list(current.facts)
        for fact in facts:
            clean = fact.strip()[:120]
            if not clean or SENSITIVE_RE.search(clean):
                continue
            if clean not in combined:
                combined.append(clean)
        combined = combined[:50]
        self.save(UserProfile(combined, datetime.now()))

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def save(self, profile: UserProfile) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp: Path | None = None
        try:
            with NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, delete=False, suffix=".json") as handle:
                tmp = Path(handle.name)
                json.dump({"facts": profile.facts, "updated_at": profile.updated_at.isoformat()}, handle, ensure_ascii=False, indent=2)
            tmp.replace(self.path)
        except (OSError, TypeError, ValueError):
            logger.exception("No se pudo guardar el perfil")
        finally:
            if tmp is not None and tmp.exists():
                tmp.unlink(missing_ok=True)
