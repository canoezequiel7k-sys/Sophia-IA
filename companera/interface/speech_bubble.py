from __future__ import annotations

import tkinter as tk
from tkinter import font
from typing import Callable

from companera.interface.theme import Theme, theme_for


KEY_COLOR = "#010203"


class SpeechBubble:
    def __init__(self, root: tk.Tk, theme: Theme | None = None) -> None:
        self.root = root
        self.theme = theme or theme_for("oscuro")
        self.window: tk.Toplevel | None = None
        self.canvas: tk.Canvas | None = None
        self._close_id: str | None = None
        self._type_id: str | None = None

    def show(self, title: str, body: str, expression: str = "calm", status: str = "LISTA",
             portrait: object | None = None, seconds: float = 8.0, on_close: Callable[[], None] | None = None) -> None:
        self.close()
        self.window = tk.Toplevel(self.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=KEY_COLOR)
        try:
            self.window.attributes("-transparentcolor", KEY_COLOR)
        except tk.TclError:
            pass

        title_font = font.Font(self.window, family="Consolas", size=12, weight="bold")
        body_font = font.Font(self.window, family="Consolas", size=10)
        title_lines = self._wrapped(title, title_font, 320, 2)
        body_lines = self._wrapped(body, body_font, 300, 8)
        title_h = max(28, len(title_lines) * 18)
        body_h = max(50, len(body_lines) * 16)
        width = 360
        height = 56 + title_h + body_h + 58

        self.window.geometry(f"{width}x{height}")
        self.canvas = tk.Canvas(self.window, width=width, height=height, bg=KEY_COLOR, highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        x1, y1, x2, y2 = 12, 12, width - 12, height - 24
        polygon = (x1 + 12, y1, x2 - 12, y1, x2, y1 + 12, x2, y2 - 12,
                   x2 - 12, y2, x1 + 12, y2, x1, y2 - 12, x1, y1 + 12)
        self.canvas.create_polygon(polygon, fill=self.theme.bubble, outline=self.theme.bubble_accent,
                                   width=2, smooth=False)
        self.canvas.create_polygon((x1 + 42, y2 - 1, x1 + 68, y2 - 1, x1 + 54, y2 + 18),
                                   fill=self.theme.bubble, outline=self.theme.bubble_accent)

        self.canvas.create_rectangle(20, 26, 74, 80, fill=self.theme.panel, outline=self.theme.bubble_accent, width=2)
        if portrait is not None:
            self.canvas.create_image(47, 53, image=portrait)
        else:
            self.canvas.create_text(47, 53, text="S", fill=self.theme.accent, font=("Consolas", 20, "bold"))

        self.canvas.create_text(88, 34, anchor="w", text="SOPHIA", fill=self.theme.text,
                                font=("Consolas", 11, "bold"))
        pill_x1, pill_x2 = 260, 344
        self._status_item = self.canvas.create_rectangle(pill_x1, 24, pill_x2, 44, fill=self.theme.pill, outline=self.theme.pill)
        self._status_text_item = self.canvas.create_text((pill_x1 + pill_x2) // 2, 34, text=status.upper(), fill="#ffffff",
                                                          font=("Consolas", 8, "bold"))

        self.canvas.create_text(88, 70, anchor="nw", text="\n".join(title_lines), fill=self.theme.text,
                                font=title_font, width=252)
        self.canvas.create_rectangle(88, 92, 92, 92 + body_h, fill=self.theme.bubble_accent, outline=self.theme.bubble_accent)
        self.canvas.create_text(104, 92, anchor="nw", text="", fill=self.theme.text,
                                font=body_font, width=232)
        self._body_text_item = self.canvas.create_text(104, 92, anchor="nw", text="", fill=self.theme.text,
                                                       font=body_font, width=232)

        button_y = height - 52
        self.canvas.create_rectangle(216, button_y, 342, button_y + 34,
                                     fill=self.theme.bubble_accent, outline=self.theme.bubble_accent)
        self.canvas.create_text(279, button_y + 17, text="ENTENDIDO", fill="#ffffff",
                                font=("Consolas", 9, "bold"))
        self.canvas.tag_bind("all", "<Button-1>", lambda _: self.close(on_close))
        self.canvas.bind("<Escape>", lambda _: self.close(on_close))

        self._type_text("\n".join(body_lines), 0)
        duration = max(3000, min(12000, seconds * 1000 + len(body) * 18))
        self._close_id = self.root.after(int(duration), lambda: self.close(on_close))

    def update_status(self, status: str) -> None:
        if self.canvas is not None and self.canvas.winfo_exists() and hasattr(self, "_status_text_item"):
            self.canvas.itemconfigure(self._status_text_item, text=status.upper())

    def _wrapped(self, text: str, text_font: font.Font, width: int, max_lines: int) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if text_font.measure(candidate) <= width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
            if len(lines) >= max_lines:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        return lines or [""]

    def _type_text(self, text: str, index: int) -> None:
        if self.canvas is None or not self.canvas.winfo_exists():
            return
        self.canvas.itemconfigure(self._body_text_item, text=text[:index])
        if index < len(text):
            self._type_id = self.root.after(18, self._type_text, text, index + 1)

    def position_near(self, root_x: int, root_y: int, root_width: int = 360) -> None:
        if self.window is None or not self.window.winfo_exists():
            return
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = root_x + root_width + 18
        y = root_y + 20
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        if x + width > screen_w:
            x = max(0, root_x - width - 18)
        y = min(max(0, y), max(0, screen_h - height - 20))
        self.window.geometry(f"+{x}+{y}")

    def close(self, on_close: Callable[[], None] | None = None) -> None:
        for attr in ("_close_id", "_type_id"):
            after_id = getattr(self, attr, None)
            if after_id is not None:
                try:
                    self.root.after_cancel(after_id)
                except tk.TclError:
                    pass
                setattr(self, attr, None)
        if self.window is not None and self.window.winfo_exists():
            self.window.destroy()
        self.window = None
        self.canvas = None
        if on_close is not None:
            on_close()
