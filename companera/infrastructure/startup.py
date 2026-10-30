from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger("sophia.startup")


def startup_shortcut_path() -> Path:
    base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    return Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Sophia IA.lnk"


def set_start_with_windows(enabled: bool, executable: Path) -> bool:
    """Crea o elimina el acceso directo opt-in al inicio de Windows."""
    shortcut = startup_shortcut_path()
    if not enabled:
        if shortcut.exists():
            shortcut.unlink()
        return True
    if not shortcut.parent.exists():
        shortcut.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "$ws=New-Object -ComObject WScript.Shell;"
        f"$s=$ws.CreateShortcut('{str(shortcut).replace(chr(39), chr(39)*2)}');"
        f"$s.TargetPath='{str(executable).replace(chr(39), chr(39)*2)}';"
        f"$s.WorkingDirectory='{str(executable.parent).replace(chr(39), chr(39)*2)}';"
        "$s.Save()"
    )
    try:
        subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], check=True, capture_output=True)
        return True
    except (OSError, subprocess.SubprocessError):
        logger.exception("No se pudo configurar el inicio con Windows")
        return False
