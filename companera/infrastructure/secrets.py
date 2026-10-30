from __future__ import annotations

import os
from pathlib import Path
from companera.infrastructure.gemini_service import load_env_file


class SecretStore:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self._env = load_env_file(project_root)

    def get(self, name: str) -> str:
        if not name:
            return ""
        value = os.environ.get(name) or self._env.get(name, "")
        value = value.strip()
        return "" if value.lower() == "tu_clave_aqui" else value

    def is_set(self, name: str) -> bool:
        return bool(self.get(name))
