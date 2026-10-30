from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from tempfile import NamedTemporaryFile


@dataclass
class Settings:
    """Configuración persistente de la aplicación."""
    voice_enabled: bool = True
    voice_name: str = "es-AR-ElenaNeural"
    voice_rate: str = "+15%"
    voice_pitch: str = "+0Hz"
    volume: float = 0.8
    sfx_enabled: bool = True
    speak_welcome: bool = True
    model: str = "gemini-3.1-flash-lite-preview"
    always_on_top: bool = False
    theme: str = "oscuro"
    avatar_size: int = 160
    allowed_folders: list[str] = field(default_factory=list)
    cache_enabled: bool = True
    cache_max_age_days: int = 14
    cache_max_mb: int = 100
    pet_mode: bool = True
    rest_animation: bool = True
    show_intro: bool = True
    minimize_to_tray: bool = True
    stream_enabled: bool = False
    sleepy_minutes: int = 15
    start_with_windows: bool = False
    pet_x: int | None = None
    pet_y: int | None = None
    always_on_top_pet: bool = True
    bubble_seconds: float = 8.0
    screen_awareness_enabled: bool = False
    terminal_x: int | None = None
    terminal_y: int | None = None
    terminal_w: int = 680
    terminal_h: int = 460
    active_model: str | None = None
    usage_soft_limit: int | None = None
    auto_fallback: bool = False
    acknowledged_providers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.volume = min(1.0, max(0.0, float(self.volume)))
        self.avatar_size = self.avatar_size if self.avatar_size in (120, 160, 220) else 160
        self.theme = self.theme if self.theme in ("oscuro", "claro") else "oscuro"
        self.allowed_folders = [str(Path(p)) for p in (self.allowed_folders or [])]
        self.terminal_w = self.terminal_w if isinstance(self.terminal_w, int) and self.terminal_w > 0 else 680
        self.terminal_h = self.terminal_h if isinstance(self.terminal_h, int) and self.terminal_h > 0 else 460

    @classmethod
    def load(cls, path: Path) -> "Settings":
        """Carga configuración; un archivo ausente o inválido usa valores seguros."""
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return cls()
            names = {field.name for field in fields(cls)}
            return cls(**{key: value for key, value in raw.items() if key in names})
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            return cls()

    def save(self, path: Path) -> None:
        """Guarda la configuración con una escritura atómica."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp: Path | None = None
        try:
            with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".json") as handle:
                tmp = Path(handle.name)
                json.dump(asdict(self), handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            tmp.replace(path)
        finally:
            if tmp is not None and tmp.exists():
                tmp.unlink(missing_ok=True)
