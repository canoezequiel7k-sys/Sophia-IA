import ctypes
import logging
from pathlib import Path

from companera.infrastructure.gemini_service import GeminiService
from companera.application.model_router import ModelRouter
from companera.infrastructure.json_memory_repository import JsonMemoryRepository
from companera.infrastructure.logging_config import configure_logging
from companera.infrastructure.settings import Settings
from companera.infrastructure.sound_effects import SoundEffectService
from companera.infrastructure.system_clock import SystemClock
from companera.infrastructure.voice_service import VoiceService
from companera.interface.desktop_pet import SophiaDesktopApp


def main() -> None:
    """Compone las dependencias y lanza Sophia IA en modo escritorio."""
    project_root = Path(__file__).resolve().parent
    logger = configure_logging(project_root)
    try:
        if hasattr(ctypes, "windll"):
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        logger.exception("No se pudo configurar la escala DPI de Windows")

    settings = Settings.load(project_root / "data" / "settings.json")
    memory = JsonMemoryRepository(project_root / "data" / "memoria.json")
    gemini = GeminiService(model=settings.model, project_root=project_root)
    router = ModelRouter(project_root=project_root, settings=settings)
    voice = VoiceService(
        voice=settings.voice_name,
        rate=settings.voice_rate,
        cache_enabled=settings.cache_enabled,
        cache_max_age_days=settings.cache_max_age_days,
        cache_max_mb=settings.cache_max_mb,
        volume=settings.volume,
    )
    sound = SoundEffectService(enabled=settings.sfx_enabled, volume=settings.volume)
    # Composition Root: se inyecta el ModelRouter (implementa LanguageModel) como
    # el modelo de conversación. La UI depende del puerto, no de la implementación.
    app = SophiaDesktopApp(
        memory=memory,
        model=router,
        clock=SystemClock(),
        voice=voice,
        sound=sound,
        settings=settings,
    )
    app.run()


if __name__ == "__main__":
    main()
