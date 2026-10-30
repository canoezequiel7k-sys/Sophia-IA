from __future__ import annotations

import random
from PIL import Image


class AvatarAnimator:
    """Utilidades locales para vida en reposo y fundidos de sprites."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._blend_cache: dict[tuple[str, str, int], Image.Image] = {}

    def idle_delay_ms(self) -> int:
        return random.randint(4000, 9000)

    def blend(self, first: Image.Image, second: Image.Image, step: int) -> Image.Image:
        alpha = min(1.0, max(0.0, step / 6.0))
        return Image.blend(first, second, alpha)
