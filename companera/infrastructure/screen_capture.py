from __future__ import annotations

import base64
import io
import logging

from PIL import ImageGrab

logger = logging.getLogger("sophia.screen")


def capture_screen_png() -> tuple[str, bytes] | None:
    """Captura la pantalla en memoria y devuelve una imagen PNG; nunca la guarda en disco."""
    try:
        image = ImageGrab.grab(all_screens=True)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return encoded, buffer.getvalue()
    except Exception:
        logger.exception("No se pudo capturar la pantalla")
        return None
