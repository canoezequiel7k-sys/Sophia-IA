from __future__ import annotations

import ctypes
import tkinter as tk
from typing import Callable

from companera.interface.terminal_view import TerminalView
from companera.interface.theme import TERMINAL_THEME
from companera.interface.layout import place_terminal
from companera.interface.screen_metrics import Rect, monitor_at, ui_scale
from companera.interface.terminal_model import TerminalHistory


class TerminalWindow:
    def __init__(self, root: tk.Tk, on_send: Callable[[str], None], settings,
                 history: TerminalHistory | None = None, on_close: Callable[[], None] | None = None,
                 on_palette: Callable[[], None] | None = None) -> None:
        self.root = root
        self.settings = settings
        self.on_close = on_close
        self.window: tk.Toplevel | None = None
        self.view: TerminalView | None = None
        self.on_send = on_send
        self.on_palette = on_palette
        self.history = history or TerminalHistory()
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
        scale = ui_scale(self.root)
        title = tk.Frame(self.window, bg="#15151d", height=int(34 * scale))
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

        self.view = TerminalView(self.window, self.history, self.on_send, self.settings.model,
                                 on_palette=self.on_palette)
        self.view.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.view.prompt.focus_set()
        self.window.update_idletasks()
        scale = ui_scale(self.root)
        real_prompt_h = self.view.prompt.winfo_reqheight() + self.view.status.winfo_reqheight() + int(24 * scale)
        footer_h = 18
        title_h = title.winfo_reqheight()
        log_min = int(4 * 16 * scale)
        min_w = max(440, int(440 * scale))
        min_h = title_h + real_prompt_h + footer_h + log_min + int(24 * scale)
        min_h = max(int(300 * scale), min_h)
        self.window.minsize(min_w, min_h)
        w = max(min_w, int(getattr(self.settings, "terminal_w", 680) * scale))
        h = max(min_h, int(getattr(self.settings, "terminal_h", 460) * scale))
        x = getattr(self.settings, "terminal_x", None)
        y = getattr(self.settings, "terminal_y", None)
        pet_x = getattr(self.settings, "pet_x", None)
        pet_y = getattr(self.settings, "pet_y", None)
        monitor = monitor_at(int(pet_x or 0), int(pet_y or 0))
        w = min(w, monitor.w - int(40 * scale))
        h = min(h, monitor.h - int(40 * scale))
        valid_saved = False
        if isinstance(x, int) and isinstance(y, int):
            saved_monitor = monitor_at(x + w // 2, y + h // 2)
            valid_saved = (saved_monitor.x <= x and x + w <= saved_monitor.right
                           and saved_monitor.y <= y and y + h <= saved_monitor.bottom)
        if not valid_saved:
            placement = place_terminal(Rect(int(pet_x or monitor.x), int(pet_y or monitor.y), 160, 160),
                                       Rect(0, 0, w, h), monitor)
            x, y = placement.x, placement.y
        self.window.geometry(f"{w}x{h}+{x}+{y}")
        self.window.bind("<Configure>", self._save_geometry)
        grip = tk.Frame(self.window, bg=TERMINAL_THEME.accent, width=8, height=8, cursor="size_nw_se")
        grip.place(relx=1.0, rely=1.0, anchor="se")
        grip.bind("<ButtonPress-1>", self._start_resize)
        grip.bind("<B1-Motion>", self._resize_window)
        grip.bind("<ButtonRelease-1>", self._save_geometry)
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
        scale = ui_scale(self.root)
        w = max(int(440 * scale), self._resize["w"] + event.x_root - self._resize["x"])
        h = max(int(300 * scale), self._resize["h"] + event.y_root - self._resize["y"])
        monitor = monitor_at(event.x_root, event.y_root)
        w = min(w, monitor.w - int(20 * scale))
        h = min(h, monitor.h - int(20 * scale))
        self.window.geometry(f"{w}x{h}")

    def _save_geometry(self, event=None) -> None:
        if self.window is None or not self.window.winfo_exists():
            return
        if event is not None and getattr(event, "widget", None) is not None and event.widget is not self.window:
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
            self._save_geometry()
            self.window.destroy()
        self.window = None
        self.view = None
        if self.on_close is not None:
            self.on_close()
