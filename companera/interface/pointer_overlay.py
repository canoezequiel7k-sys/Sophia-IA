from __future__ import annotations

import ctypes
import math
import sys
import tkinter as tk


KEY_COLOR = "#010203"


class PointerOverlay:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.window: tk.Toplevel | None = None
        self.canvas: tk.Canvas | None = None
        self._after_id: str | None = None

    def point_at(self, x: int, y: int, label: str, origin: tuple[int, int]) -> None:
        self.clear()
        if sys.platform == "win32":
            try:
                sm_x = 76; sm_y = 77; sm_w = 78; sm_h = 79
                user32 = ctypes.windll.user32
                vx = user32.GetSystemMetrics(sm_x)
                vy = user32.GetSystemMetrics(sm_y)
                vw = user32.GetSystemMetrics(sm_w)
                vh = user32.GetSystemMetrics(sm_h)
            except Exception:
                vx = vy = 0; vw = self.root.winfo_screenwidth(); vh = self.root.winfo_screenheight()
        else:
            vx = vy = 0; vw = self.root.winfo_screenwidth(); vh = self.root.winfo_screenheight()

        self.window = tk.Toplevel(self.root)
        self.window.overrideredirect(True)
        self.window.geometry(f"{vw}x{vh}+{vx}+{vy}")
        self.window.attributes("-topmost", True)
        if sys.platform == "win32" and hasattr(self.window, "attributes"):
            self.window.attributes("-transparentcolor", KEY_COLOR)
        self.window.configure(bg=KEY_COLOR)
        self.canvas = tk.Canvas(self.window, bg=KEY_COLOR, highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        if sys.platform == "win32":
            try:
                hwnd = ctypes.windll.user32.GetParent(self.window.winfo_id()) or self.window.winfo_id()
                gwl_style = -16; ws_toolwindow = 0x00000080
                gwl_exstyle = -20; ws_ex_layered = 0x00080000; ws_ex_transparent = 0x00000020
                style = ctypes.windll.user32.GetWindowLongW(hwnd, gwl_style)
                exstyle = ctypes.windll.user32.GetWindowLongW(hwnd, gwl_exstyle)
                ctypes.windll.user32.SetWindowLongW(hwnd, gwl_style, style | ws_toolwindow)
                ctypes.windll.user32.SetWindowLongW(hwnd, gwl_exstyle, exstyle | ws_ex_layered | ws_ex_transparent)
            except Exception:
                pass

        ox = origin[0] - vx; oy = origin[1] - vy
        tx = x - vx; ty = y - vy
        self.window.bind("<Escape>", lambda _: self.clear())
        self._animate_line(ox, oy, tx, ty, label, 0)

    def _animate_line(self, ox: int, oy: int, tx: int, ty: int, label: str, step: int) -> None:
        if self.canvas is None or self.window is None:
            return
        progress = min(1.0, step / 18.0)
        px = ox + (tx - ox) * progress
        py = oy + (ty - oy) * progress
        self.canvas.delete("all")
        line = self.canvas.create_line(ox, oy, px, py, fill="#00f0ff", width=3, dash=(8, 7), smooth=False)
        if progress >= 1.0:
            angle = math.atan2(ty - oy, tx - ox)
            size = 14
            points = (
                tx, ty,
                tx - size * math.cos(angle - 0.55), ty - size * math.sin(angle - 0.55),
                tx - size * math.cos(angle + 0.55), ty - size * math.sin(angle + 0.55),
            )
            self.canvas.create_polygon(points, fill="#ff2d6f", outline="#ff2d6f")
            lx = min(max(tx + 12, 20), self.canvas.winfo_width() - 170)
            ly = max(20, ty - 38)
            self.canvas.create_rectangle(lx, ly, lx + 150, ly + 32, fill="#ff2d6f", outline="#ff2d6f")
            self.canvas.create_text(lx + 75, ly + 16, text=label.upper(), fill="#ffffff", font=("Consolas", 9, "bold"))
            self._after_id = self.root.after(8000, self.clear)
            return
        self._after_id = self.root.after(16, self._animate_line, ox, oy, tx, ty, label, step + 1)

    def clear(self) -> None:
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        if self.window is not None and self.window.winfo_exists():
            self.window.destroy()
        self.window = None
        self.canvas = None
