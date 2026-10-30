from __future__ import annotations

import logging
import threading
from pathlib import Path
from queue import Queue
from typing import Callable

logger = logging.getLogger("sophia.tray")
try:
    import pystray
    from PIL import Image
    PYSTRAY_AVAILABLE = True
except Exception:
    pystray = None
    Image = None
    PYSTRAY_AVAILABLE = False


class SophiaTray:
    def __init__(self, events: Queue, project_root: Path) -> None:
        self.events = events
        self.project_root = project_root
        self.icon = None

    def start(self) -> None:
        if not PYSTRAY_AVAILABLE:
            logger.info("pystray no está instalado; la bandeja queda desactivada")
            return
        tray_icon = self.project_root / "companera" / "assets" / "sophia" / "tray.png"
        try:
            image = Image.open(tray_icon) if tray_icon.exists() else Image.new("RGBA", (64, 64), "#00f0ff")
            menu = pystray.Menu(
                pystray.MenuItem("Mostrar/Ocultar", lambda: self.events.put(("tray_toggle", None))),
                pystray.MenuItem("Mute", lambda: self.events.put(("tray_mute", None))),
                pystray.MenuItem("Salir", lambda: self.events.put(("tray_exit", None))),
            )
            self.icon = pystray.Icon("Sophia", image, "Sophia IA", menu)
            threading.Thread(target=self.icon.run, daemon=True).start()
        except Exception:
            logger.exception("No se pudo iniciar la bandeja del sistema")

    def stop(self) -> None:
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                logger.exception("No se pudo detener la bandeja")
