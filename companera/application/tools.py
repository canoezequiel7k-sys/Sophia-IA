from __future__ import annotations

import datetime as dt
import logging
import threading
import webbrowser
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("sophia.tools")


class Permission(str, Enum):
    SAFE = "SAFE"
    CONFIRM = "CONFIRM"


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    permission: Permission
    runner: Callable[..., Any]

    def run(self, confirm: Callable[[str], bool] = lambda _: True, **kwargs: Any) -> Any:
        if self.permission == Permission.CONFIRM and not confirm(kwargs.get("url") or kwargs.get("path") or ""):
            return "Acción cancelada por el usuario."
        logger.info("Ejecutando herramienta %s", self.name)
        return self.runner(**kwargs)


class ToolRegistry:
    """Registro local de herramientas; admite como máximo tres llamadas por turno."""

    MAX_CALLS = 3

    def __init__(self, project_root: Path, allowed_folders: list[str] | None = None) -> None:
        self.project_root = project_root
        self.allowed_folders = allowed_folders or []
        self.tools: dict[str, Tool] = {}
        self._calls = 0
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(Tool("get_datetime", "Devuelve fecha y hora local", {}, Permission.SAFE, lambda: dt.datetime.now().astimezone().isoformat()))
        self.register(Tool("take_note", "Agrega una nota a data/notas.md", {"text": "string"}, Permission.SAFE, self._take_note))
        self.register(Tool("set_timer", "Programa un temporizador local", {"minutes": "number", "label": "string"}, Permission.SAFE, self._set_timer))
        self.register(Tool("open_url", "Abre una URL solo tras confirmación", {"url": "string"}, Permission.CONFIRM, self._open_url))
        self.register(Tool("read_text_file", "Lee un archivo permitido", {"path": "string"}, Permission.CONFIRM, self.read_text_file))

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def reset(self) -> None:
        self._calls = 0

    def run(self, name: str, confirm: Callable[[str], bool] = lambda _: True, **kwargs: Any) -> Any:
        if self._calls >= self.MAX_CALLS:
            return "Se alcanzó el límite de tres llamadas a herramientas por turno."
        tool = self.tools.get(name)
        if tool is None:
            return "Herramienta desconocida."
        self._calls += 1
        return tool.run(confirm=confirm, **kwargs)

    def _take_note(self, text: str) -> str:
        path = self.project_root / "data" / "notas.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"- {text}\n")
        return "Nota guardada."

    def _set_timer(self, minutes: float, label: str = "Temporizador") -> str:
        def finish() -> None:
            logger.info("Temporizador vencido: %s", label)
        threading.Timer(max(0.1, float(minutes) * 60), finish).start()
        return f"Temporizador configurado: {label}"

    def _open_url(self, url: str) -> str:
        if not (url.startswith("http://") or url.startswith("https://")):
            return "URL rechazada: solo se permiten http y https."
        webbrowser.open(url)
        return "Enlace abierto tras confirmación."

    def read_text_file(self, path: str) -> str:
        """Lee solo dentro de una carpeta permitida, nunca .env ni archivos grandes."""
        if not self.allowed_folders:
            return "La lectura de archivos está desactivada: no hay carpetas permitidas."
        raw = Path(path)
        if ".." in raw.parts:
            return "Ruta rechazada."
        try:
            resolved = raw.resolve(strict=True)
        except (OSError, RuntimeError):
            return "No se pudo resolver la ruta solicitada."
        allowed = [Path(folder).resolve() for folder in self.allowed_folders]
        if resolved.name.casefold() == ".env" or resolved.suffix.casefold() in (".env", ".exe", ".dll", ".bin"):
            return "Archivo rechazado por seguridad."
        if not any(resolved == folder or folder in resolved.parents for folder in allowed):
            return "Ruta fuera de las carpetas permitidas."
        if resolved.stat().st_size > 50 * 1024:
            return "El archivo supera el límite de 50 KB."
        try:
            return resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return "El archivo no parece texto UTF-8."
