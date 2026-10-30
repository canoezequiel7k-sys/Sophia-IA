from __future__ import annotations

import ctypes
import tkinter as tk
from typing import Callable

from companera.interface.terminal_view import TerminalView
from companera.interface.theme import TERMINAL_THEME
from companera.interface.layout import place_terminal
from companera.interface.screen_metrics import Rect, monitor_at


class TerminalWindow:
    def __init__(self, root: tk.Tk, on_send: Callable[[str], None], settings, on_close: Callable[[], None] | None = None, on_palette: Callable[[], None] | None = None) -> None:
        self.root = root
        self.settings = settings
        self.on_close = on_close
        self.window: tk.Toplevel | None = None
        self.view: TerminalView | None = None
        self.on_send = on_send
        self.on_palette = on_palette
        self._drag = {"x": 0, "y": 0}
        self._resize = {"x": 0, "y": 0, "w": 0, "h": 0}

    def open(self) -> None:
        if self.window is not None and self.window.winfo_exists():
            self.focus()
            return
        self.window = tk.Toplevel(self.root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=TERMINAL_THEME.border, highlightbackground=TERMINAL_THEME.border, highlightthickness=1)
        title = tk.Frame(self.window, bg="#15151d", height=34)
        title.pack(fill=tk.X)
        title.pack_propagate(False)
        tk.Label(title, text="sophia — terminal", bg="#15151d", fg=TERMINAL_THEME.text,
                 font=("Consolas", 10, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Button(title, text="—", command=self.minimize, bg="#15151d", fg=TERMINAL_THEME.muted,
                  bd=0, padx=10, cursor="hand2").pack(side=tk.RIGHT)
        tk.Button(title, text="×", command=self.close, bg="#15151d", fg=TERMINAL_THEME.muted,
                  bd=0, padx=10, cursor="hand2").pack(side=tk.RIGHT)
        title.bind("<ButtonPress-1>", self._begin_drag)
        title.bind("<B1-Motion>", self._drag_window)

        self.view = TerminalView(self.window, self.on_send, self.settings.model, on_palette=self.on_palette)
        self.view.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.view.prompt.focus_set()
        w = max(440, getattr(self.settings, "terminal_w", 640))
        h = max(300, getattr(self.settings, "terminal_h", 440))
        x = getattr(self.settings, "terminal_x", None)
        y = getattr(self.settings, "terminal_y", None)
        if x is None or y is None:
            x = max(20, (self.window.winfo_screenwidth() - w) // 2)
            y = max(20, (self.window.winfo_screenheight() - h) // 2)
        self.window.minsize(440, 300)
        self.window.geometry(f"{w}x{h}+{x}+{y}")
        self.window.bind("<Configure>", self._save_geometry)
        grip = tk.Frame(self.window, bg=TERMINAL_THEME.accent, width=8, height=8, cursor="size_nw_se")
        grip.place(relx=1.0, rely=1.0, anchor="se")
        grip.bind("<ButtonPress-1>", self._start_resize)
        grip.bind("<B1-Motion>", self._resize_window)
        self.window.deiconify()

    def _begin_drag(self, event: tk.Event) -> None:
        self._drag["x"] = event.x_root - self.window.winfo_x()
        self._drag["y"] = event.y_root - self.window.winfo_y()

    def _drag_window(self, event: tk.Event) -> None:
        x = event.x_root - self._drag["x"]
        y = event.y_root - self._drag["y"]
        self.window.geometry(f"+{x}+{y}")

    def _start_resize(self, event: tk.Event) -> None:
        self._resize = {
            "x": event.x_root, "y": event.y_root,
            "w": self.window.winfo_width(), "h": self.window.winfo_height(),
        }

    def _resize_window(self, event: tk.Event) -> None:
        w = max(440, self._resize["w"] + event.x_root - self._resize["x"])
        h = max(300, self._resize["h"] + event.y_root - self._resize["y"])
        self.window.geometry(f"{w}x{h}")

    def _save_geometry(self, _event=None) -> None:
        if self.window is None or not self.window.winfo_exists():
            return
        self.settings.terminal_x = self.window.winfo_x()
        self.settings.terminal_y = self.window.winfo_y()
        self.settings.terminal_w = self.window.winfo_width()
        self.settings.terminal_h = self.window.winfo_height()

    def append_user(self, text: str) -> None:
        if self.view is not None:
            self.view.append_user(text)

    def append_sophia(self, text: str, error: bool = False) -> None:
        if self.view is not None:
            self.view.append_sophia(text, error)

    def set_thinking(self, on: bool) -> None:
        if self.view is not None:
            self.view.set_thinking(on)

    def set_status(self, text: str, color: str = "#68d391") -> None:
        if self.view is not None:
            self.view.set_status(text, color)

    def update_status(self, text: str, color: str = "#68d391") -> None:
        self.set_status(text, color)

    def position_near(self, pet_x: int, pet_y: int, pet_width: int = 160) -> None:
        if self.window is None or not self.window.winfo_exists():
            return
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        pet_height = getattr(self, "_pet_height", 160)
        monitor = monitor_at(pet_x + pet_width // 2, pet_y + pet_height // 2)
        placement = place_terminal(Rect(pet_x, pet_y, pet_width, pet_height), Rect(0, 0, width, height), monitor)
        self.window.geometry(f"+{placement.x}+{placement.y}")

    def focus(self) -> None:
        if self.window is not None:
            self.window.lift()
            if self.view is not None:
                self.view.prompt.focus_set()

    def minimize(self) -> None:
        if self.window is not None:
            self.window.withdraw()

    def close(self) -> None:
        if self.window is not None and self.window.winfo_exists():
            self.window.destroy()
        self.window = None
        self.view = None
        if self.on_close is not None:
            self.on_close()
