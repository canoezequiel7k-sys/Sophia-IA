"""Servicio de voz para Sophia.

Usa edge-tts (texto a voz con voces gratuitas de Microsoft Edge) para generar
audio en español argentino y pygame para reproducirlo sin bloquear la UI.

Si no están disponibles las dependencias, falla silenciosamente para que
Sophia siga funcionando sin voz.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from companera.infrastructure.speech_text import clean_for_speech

logger = logging.getLogger("sophia.voice")

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
# Velocidad de habla por defecto (+15% para sonar más natural y fluida).
DEFAULT_RATE = "+15%"


class VoiceService:
    """Genera y reproduce audio de los mensajes de Sophia."""

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        rate: str = DEFAULT_RATE,
        cache_dir: Optional[Path] = None,
        tts_generator: Optional[Any] = None,
        audio_backend: Optional[Any] = None,
        cache_enabled: bool = True,
        cache_max_age_days: int = 14,
        cache_max_mb: int = 100,
        volume: float = 0.8,
    ) -> None:
        self._voice = voice
        self._rate = rate
        self._cache_dir = cache_dir or (
            Path(__file__).resolve().parents[2] / "data" / "voice_cache"
        )
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._tts_generator = tts_generator
        self._audio = audio_backend
        self._cache_enabled = cache_enabled
        self._cache_max_age_days = cache_max_age_days
        self._cache_max_mb = cache_max_mb
        self._volume = min(1.0, max(0.0, float(volume)))
        self._lock = threading.Lock()
        self._generation = 0
        self._speaking = False
        self._pygame_initialized = False
        self._active_threads: set[threading.Thread] = set()
        self._threads_lock = threading.Lock()
        self._cleanup_cache()

    # ------------------------------------------------------------------ API

    def is_available(self) -> bool:
        """True si edge-tts y pygame están instalados."""
        return _EDGE_TTS_AVAILABLE and _PYGAME_AVAILABLE

    def speak(self, text: str) -> None:
        """Reproduce texto limpio en un hilo separado (no bloquea la UI)."""
        if not self.is_available() or not text.strip():
            return
        with self._lock:
            self._generation += 1
            generation = self._generation
        cleaned = clean_for_speech(text)
        if not cleaned:
            return
        thread = threading.Thread(target=self._speak_sync, args=(cleaned, generation), daemon=True)
        with self._threads_lock:
            self._active_threads.add(thread)
        thread.start()

    def set_volume(self, volume: float) -> None:
        """Actualiza el volumen sin requerir reiniciar el servicio."""
        self._volume = min(1.0, max(0.0, float(volume)))
        if _PYGAME_AVAILABLE and pygame is not None:
            try:
                if pygame.get_init() and pygame.mixer.get_init():
                    pygame.mixer.music.set_volume(self._volume)
            except Exception:
                logger.exception("No se pudo actualizar el volumen de voz")

    def stop(self) -> None:
        """Cancela generación y reproducción sin esperar al audio."""
        with self._lock:
            self._generation += 1
            self._speaking = False
        if _PYGAME_AVAILABLE and pygame is not None:
            try:
                if pygame.get_init() and pygame.mixer.get_init():
                    pygame.mixer.music.stop()
            except Exception:
                logger.exception("No se pudo detener la voz")

    # ------------------------------------------------------------------ internos

    def is_speaking(self) -> bool:
        return self._speaking

    def _speak_sync(self, text: str, generation: int) -> None:
        try:
            with self._lock:
                if generation != self._generation:
                    return
            mp3_path = self._generate_mp3(text, generation)
            with self._lock:
                if generation != self._generation:
                    return
            self._play(mp3_path, generation)
        except Exception:
            logger.exception("La generación o reproducción de voz falló")
        finally:
            current = threading.current_thread()
            with self._threads_lock:
                self._active_threads.discard(current)

    def _cleanup_cache(self) -> None:
        """Elimina caché antigua y limita el tamaño máximo configurado."""
        if not self._cache_enabled:
            return
        cutoff = time.time() - self._cache_max_age_days * 86400
        files = [p for p in self._cache_dir.glob("*.mp3") if p.is_file()]
        for path in files:
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                logger.exception("No se pudo limpiar un archivo de caché antiguo")
        files = sorted((p for p in self._cache_dir.glob("*.mp3") if p.is_file()), key=lambda p: p.stat().st_mtime)
        max_bytes = self._cache_max_mb * 1024 * 1024
        total = sum(p.stat().st_size for p in files)
        for path in files:
            if total <= max_bytes:
                break
            try:
                total -= path.stat().st_size
                path.unlink()
            except OSError:
                logger.exception("No se pudo limpiar la caché de voz")

    def _cache_key(self, text: str) -> str:
        payload = f"{self._voice}|{self._rate}|{text}".encode("utf-8")
        return hashlib.md5(payload).hexdigest()

    def _generate_mp3(self, text: str, generation: int | None = None) -> Path:
        """Genera un MP3 con edge-tts (usando caché si ya existe)."""
        path = self._cache_dir / f"{self._cache_key(text)}.mp3"
        if not path.exists() and self._cache_enabled:
            import asyncio

            if self._tts_generator is not None:
                if generation is not None:
                    with self._lock:
                        if generation != self._generation:
                            return path
                result = self._tts_generator(text=text, path=path)
                if callable(result):
                    if generation is not None:
                        with self._lock:
                            if generation != self._generation:
                                return path
                    result()
            else:
                asyncio.run(self._save_mp3(text, path))
        elif not self._cache_enabled:
            import asyncio

            asyncio.run(self._save_mp3(text, path))
        return path

    async def _save_mp3(self, text: str, path: Path) -> None:
        assert edge_tts is not None
        communicate = edge_tts.Communicate(
            text,
            voice=self._voice,
            rate=self._rate,
        )
        await communicate.save(str(path))

    def _play(self, path: Path, generation: int | None = None) -> None:
        backend = self._audio
        if backend is None:
            if not _PYGAME_AVAILABLE or pygame is None:
                return
            backend = pygame
        with self._lock:
            if not self._pygame_initialized:
                if hasattr(backend, "mixer"):
                    backend.mixer.init()
                self._pygame_initialized = True
            backend.mixer.music.load(str(path))
            if hasattr(backend.mixer.music, "set_volume"):
                backend.mixer.music.set_volume(self._volume)
            backend.mixer.music.play()
            self._speaking = True
        while True:
            with self._lock:
                if generation is not None and generation != self._generation:
                    break
            if hasattr(backend.mixer.music, "get_busy"):
                busy = backend.mixer.music.get_busy()
            else:
                busy = False
            if not busy:
                break
            if hasattr(backend, "time"):
                backend.time.Clock().tick(10)
            else:
                time.sleep(0.05)
        with self._lock:
            if generation is None or generation == self._generation:
                self._speaking = False
