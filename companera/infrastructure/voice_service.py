"""Servicio de voz para Sophia.

Usa edge-tts (texto a voz con voces gratuitas de Microsoft Edge) para generar
audio en español argentino y pygame para reproducirlo sin bloquear la UI.

Si no están disponibles las dependencias, falla silenciosamente para que
Sophia siga funcionando sin voz.
"""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path
from typing import Optional

try:
    import edge_tts  # type: ignore

    _EDGE_TTS_AVAILABLE = True
except Exception:  # pragma: no cover - depende de entorno
    edge_tts = None  # type: ignore[assignment]
    _EDGE_TTS_AVAILABLE = False

try:
    import pygame  # type: ignore

    _PYGAME_AVAILABLE = True
except Exception:  # pragma: no cover - depende de entorno
    pygame = None  # type: ignore[assignment]
    _PYGAME_AVAILABLE = False

# Voz femenina en español argentino por defecto.
DEFAULT_VOICE = "es-AR-ElenaNeural"


class VoiceService:
    """Genera y reproduce audio de los mensajes de Sophia."""

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        cache_dir: Optional[Path] = None,
    ) -> None:
        self._voice = voice
        self._cache_dir = cache_dir or (
            Path(__file__).resolve().parents[2] / "data" / "voice_cache"
        )
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._pygame_initialized = False

    # ------------------------------------------------------------------ API

    def is_available(self) -> bool:
        """True si edge-tts y pygame están instalados."""
        return _EDGE_TTS_AVAILABLE and _PYGAME_AVAILABLE

    def speak(self, text: str) -> None:
        """Reproduce el texto como voz en un hilo separado (no bloquea)."""
        if not self.is_available() or not text.strip():
            return
        thread = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
        thread.start()

    def stop(self) -> None:
        """Detiene la reproducción actual (útil si el usuario envía un mensaje nuevo)."""
        if not _PYGAME_AVAILABLE:
            return
        with self._lock:
            try:
                if pygame.get_init() and pygame.mixer.get_init():
                    pygame.mixer.music.stop()
            except Exception:
                pass

    # ------------------------------------------------------------------ internos

    def _speak_sync(self, text: str) -> None:
        try:
            mp3_path = self._generate_mp3(text)
            self._play(mp3_path)
        except Exception:
            # La voz nunca debe romper la aplicación.
            pass

    def _cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _generate_mp3(self, text: str) -> Path:
        """Genera un MP3 con edge-tts (usando caché si ya existe)."""
        path = self._cache_dir / f"{self._cache_key(text)}.mp3"
        if not path.exists():
            import asyncio

            asyncio.run(self._save_mp3(text, path))
        return path

    async def _save_mp3(self, text: str, path: Path) -> None:
        assert edge_tts is not None
        communicate = edge_tts.Communicate(text, voice=self._voice)
        await communicate.save(str(path))

    def _play(self, path: Path) -> None:
        if not _PYGAME_AVAILABLE:
            return
        with self._lock:
            if not self._pygame_initialized:
                assert pygame is not None
                pygame.mixer.init()
                self._pygame_initialized = True
            assert pygame is not None
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
