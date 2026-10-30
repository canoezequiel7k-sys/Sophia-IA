from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from PIL import Image

logger = logging.getLogger("sophia.intro")

INTRO_SEQUENCE = (
    ("intro-grab", 140), ("intro-happy", 200),
    ("intro-mouth1", 110), ("intro-mouth2", 110), ("intro-mouth3", 110),
    ("intro-smear", 90),
    ("intro-wave1", 160), ("intro-wave2", 160), ("intro-wave3", 260),
)


def load_intro_frames(assets_dir: Path, width: int = 224, panel_color: str = "#140f22") -> list[Image.Image]:
    height = round(width * 9 / 16)
    frames: list[Image.Image] = []
    rgb = tuple(int(panel_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    for name, _duration in INTRO_SEQUENCE:
        path = assets_dir / f"{name}.webp"
        if not path.exists():
            logger.warning("Frame de intro ausente: %s", path.name)
            continue
        try:
            with Image.open(path) as source:
                source.seek(0)
                image = source.convert("RGBA")
            image.thumbnail((width, height), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (width, height), rgb + (255,))
            x = (width - image.width) // 2
            y = (height - image.height) // 2
            canvas.alpha_composite(image, (x, y))
            frames.append(canvas.convert("RGBA"))
        except Exception:
            logger.exception("No se pudo cargar el frame de intro %s", path.name)
    return frames
