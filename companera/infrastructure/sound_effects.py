"""Efectos de sonido procedimentales para Sophia.

Inspirado en el sistema de sonidos de Capri Desktop (voice.js), pero adaptado
para Python + pygame. Genera tonos simples en memoria (sin archivos externos)
para los momentos clave: saludo, pensando, hablando, finalizado y error.
"""

from __future__ import annotations

import math
import struct
import logging
import threading
from typing import Optional

try:
    import pygame
    _PYGAME_AVAILABLE = True
except Exception:
    pygame = None  # type: ignore[assignment]
    _PYGAME_AVAILABLE = False

logger = logging.getLogger("sophia.sound")


class SoundEffectService:
    """Reproduce efectos de sonido cortos sin bloquear la UI."""

    SAMPLE_RATE = 22050

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._initialized = False
        self._lock = threading.Lock()
        self._sounds: dict[str, "pygame.mixer.Sound"] = {}

    def is_available(self) -> bool:
        return self._enabled and _PYGAME_AVAILABLE and pygame is not None

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    def play(self, name: str) -> None:
        """Reproduce un efecto por nombre (no bloquea)."""
        if not self.is_available():
            return
        threading.Thread(target=self._play_sync, args=(name,), daemon=True).start()

    def stop(self) -> None:
        """Detiene toda reproducción de efectos, incluso cuando están desactivados."""
        if not _PYGAME_AVAILABLE or pygame is None:
            return
        with self._lock:
            try:
                if pygame.get_init() and pygame.mixer.get_init():
                    pygame.mixer.stop()
            except Exception:
                logger.exception("No se pudo detener un efecto de sonido")

    # ------------------------------------------------------------------ interno

    def _ensure_mixer(self) -> None:
        if not self._initialized:
            pygame.mixer.init(
                frequency=self.SAMPLE_RATE, size=-16, channels=1, buffer=512
            )
            self._initialized = True

    def _pcm16(self, samples: list[float]) -> bytes:
        """Convierte muestras flotantes [-1, 1] a bytes PCM 16-bit mono."""
        buf = bytearray()
        for s in samples:
            sample = int(max(-1.0, min(1.0, s)) * 32767)
            buf.extend(struct.pack("<h", sample))
        return bytes(buf)

    def _tone(
        self,
        frequency: float,
        duration_ms: float,
        volume: float = 0.1,
        wave: str = "sine",
    ) -> bytes:
        """Genera un tono simple en PCM."""
        n = int(self.SAMPLE_RATE * duration_ms / 1000.0)
        samples: list[float] = []
        for i in range(n):
            t = i / self.SAMPLE_RATE
            phase = 2 * math.pi * frequency * t
            if wave == "sine":
                value = math.sin(phase)
            elif wave == "square":
                value = 1.0 if math.sin(phase) >= 0 else -1.0
            elif wave == "triangle":
                value = (
                    2.0 * abs(2.0 * (t * frequency - math.floor(t * frequency + 0.5))) - 1.0
                )
            else:
                value = math.sin(phase)
            samples.append(value * volume)
        return self._pcm16(samples)

    def _load(self, name: str) -> Optional["pygame.mixer.Sound"]:
        if name in self._sounds:
            return self._sounds[name]
        data = self._generate(name)
        if data is None:
            return None
        sound = pygame.mixer.Sound(buffer=data)
        self._sounds[name] = sound
        return sound

    def _generate(self, name: str) -> Optional[bytes]:
        if name == "hello":
            # Saludo: arpegio ascendente suave (3 notas)
            parts = []
            for freq, dur in [(520, 120), (650, 120), (780, 220)]:
                parts.append(self._tone(freq, dur, 0.12, "sine"))
            return b"".join(parts)

        if name == "blip":
            # Sonido corto de "hablando"
            return self._tone(880, 60, 0.08, "sine")

        if name == "thinking":
            # Tono bajo mientras piensa
            return self._tone(220, 400, 0.06, "triangle")

        if name == "done":
            # Arpegio de finalización
            parts = []
            for freq, dur in [(650, 100), (780, 100), (1040, 300)]:
                parts.append(self._tone(freq, dur, 0.12, "sine"))
            return b"".join(parts)

        if name == "error":
            # Tono grave descendente
            parts = []
            for i in range(6):
                freq = 400 - i * 50
                parts.append(self._tone(freq, 80, 0.15, "sine"))
            return b"".join(parts)

        return None

    def _play_sync(self, name: str) -> None:
        with self._lock:
            try:
                self._ensure_mixer()
                sound = self._load(name)
                if sound:
                    sound.play()
            except Exception:
                logger.exception("Falló la reproducción de un efecto de sonido")
