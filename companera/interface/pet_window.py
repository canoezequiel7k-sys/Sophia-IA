from __future__ import annotations

import ctypes
import ctypes.wintypes
import sys
import tkinter as tk
from pathlib import Path
from typing import Callable

from PIL import Image, ImageTk


KEY_COLOR = "#010203"


class PetWindow:
    def __init__(self, root: tk.Tk, assets_dir: Path, avatar_size: int = 160,
                 on_click: Callable[[], None] | None = None,
                 on_menu: Callable[[tk.Event], None] | None = None,
                 on_position: Callable[[int, int], None] | None = None,
                 on_drag: Callable[[int, int], None] | None = None) -> None:
        self.root = root
        self.assets_dir = assets_dir
        self.avatar_size = avatar_size
        self.on_click = on_click
        self.on_menu = on_menu
        self.on_position = on_position
        self.on_drag = on_drag
        self.window = tk.Toplevel(root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=KEY_COLOR)
        if sys.platform == "win32":
            try:
                self.window.attributes("-transparentcolor", KEY_COLOR)
            except tk.TclError:
                pass
        self._drag = {"x": 0, "y": 0, "start_x": 0, "start_y": 0, "moved": False}
        self._state = "idle"
        self._state_anim_id: str | None = None
        self.label = tk.Label(self.window, bg=KEY_COLOR, cursor="hand2")
        self.label.pack()
        self._load()
        self.label.bind("<ButtonPress-1>", self._begin)
        self.label.bind("<B1-Motion>", self._drag_window)
        self.label.bind("<ButtonRelease-1>", self._release)
        if on_menu is not None:
            self.label.bind("<Button-3>", on_menu)

    def _composite(self, image: Image.Image) -> Image.Image:
        key = (1, 2, 3, 255)
        image = image.convert("RGBA")
        pixels = image.load()
        for y in range(image.height):
            for x in range(image.width):
                r, g, b, a = pixels[x, y]
                if a < 128:
                    pixels[x, y] = (0, 0, 0, 0)
                else:
                    pixels[x, y] = (r, g, b, 255)
        result = Image.new("RGBA", image.size, key[:3] + (255,))
        result.alpha_composite(image)
        return result.convert("RGB")

    def _load(self) -> None:
        path = self.assets_dir / "capri-cutout.png"
        if path.exists():
            image = Image.open(path).convert("RGBA")
            image.thumbnail((self.avatar_size * 2, self.avatar_size * 2), Image.Resampling.LANCZOS)
            image = self._composite(image)
            size = (image.width, image.height)
            self.photo = ImageTk.PhotoImage(image)
            self.label.configure(image=self.photo)
            self.window.geometry(f"{size[0]}x{size[1]}")

    def workarea_default_position(self) -> tuple[int, int]:
        if sys.platform == "win32":
            try:
                rect = ctypes.wintypes.RECT()
                if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
                    width = self.window.winfo_reqwidth()
                    height = self.window.winfo_reqheight()
                    return rect.right - width - 20, rect.bottom - height - 20
            except Exception:
                pass
        return max(0, self.root.winfo_screenwidth() - 220), max(0, self.root.winfo_screenheight() - 320)

    def restore_position(self, x: int | None, y: int | None) -> None:
        valid = False
        if x is not None and y is not None:
            if sys.platform == "win32":
                try:
                    vx = ctypes.windll.user32.GetSystemMetrics(76)
                    vy = ctypes.windll.user32.GetSystemMetrics(77)
                    vw = ctypes.windll.user32.GetSystemMetrics(78)
                    vh = ctypes.windll.user32.GetSystemMetrics(79)
                    valid = vx <= x < vx + vw and vy <= y < vy + vh
                except Exception:
                    valid = True
            else:
                valid = 0 <= x < self.root.winfo_screenwidth() and 0 <= y < self.root.winfo_screenheight()
        if valid:
            self.window.geometry(f"+{x}+{y}")
        else:
            px, py = self.workarea_default_position()
            self.window.geometry(f"+{px}+{py}")

    def _begin(self, event: tk.Event) -> None:
        self._drag["x"] = event.x_root - self.window.winfo_x()
        self._drag["y"] = event.y_root - self.window.winfo_y()
        self._drag["start_x"] = event.x_root
        self._drag["start_y"] = event.y_root
        self._drag["moved"] = False

    def _drag_window(self, event: tk.Event) -> None:
        dx = abs(event.x_root - self._drag["start_x"])
        dy = abs(event.y_root - self._drag["start_y"])
        if dx >= 4 or dy >= 4:
            self._drag["moved"] = True
        if self._drag["moved"]:
            x = event.x_root - self._drag["x"]
            y = event.y_root - self._drag["y"]
            self.window.geometry(f"+{x}+{y}")
            if self.on_drag is not None:
                self.on_drag(x, y)

    def _release(self, event: tk.Event) -> None:
        if not self._drag["moved"] and self.on_click is not None:
            self.on_click()
        elif self.on_position is not None:
            self.on_position(self.window.winfo_x(), self.window.winfo_y())
        self._drag["moved"] = False

    def show_sprite(self, photo: object) -> None:
        # El recorte Capri es fijo en el avatar flotante; esta API queda reservada
        # por compatibilidad, pero no reemplaza la mascota.
        return

    def set_state(self, state: str) -> None:
        if state not in ("idle", "thinking", "talking"):
            state = "idle"
        self._state = state
        if self._state_anim_id:
            try:
                self.window.after_cancel(self._state_anim_id)
            except tk.TclError:
                pass
            self._state_anim_id = None
        self._animate_state()

    def _animate_state(self) -> None:
        if not self.window.winfo_exists() or self._drag["moved"]:
            return
        base_x = self.window.winfo_x()
        base_y = self.window.winfo_y()
        offset = -2 if self._state == "thinking" else 0
        self.window.geometry(f"+{base_x}+{base_y + offset}")
        if self._state == "thinking":
            def return_origin() -> None:
                if self.window.winfo_exists() and not self._drag["moved"]:
                    self.window.geometry(f"+{base_x}+{base_y}")
            self._state_anim_id = self.window.after(1200, return_origin)

    def close(self) -> None:
        if self.window.winfo_exists():
            self.window.destroy()
