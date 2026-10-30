from __future__ import annotations

import tkinter as tk
from tkinter import font
from typing import Callable

from companera.interface.theme import Theme, theme_for
from companera.interface.layout import place_bubble
from companera.interface.screen_metrics import Rect, monitor_at


KEY_COLOR = "#010203"


class SpeechBubble:
    def __init__(self, root: tk.Tk, theme: Theme | None = None) -> None:
        self.root = root
        self.theme = theme or theme_for("oscuro")
        self.window: tk.Toplevel | None = None
        self.canvas: tk.Canvas | None = None
        self._close_id: str | None = None
        self._type_id: str | None = None
        self._tail_side = "left"

    def show(self, title: str, body: str, expression: str = "calm", status: str = "LISTA",
             portrait: object | None = None, seconds: float = 8.0, on_close: Callable[[], None] | None = None) -> None:
        self.close()
        self.window = tk.Toplevel(self.root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=KEY_COLOR)
        try:
            self.window.attributes("-transparentcolor", KEY_COLOR)
        except tk.TclError:
            pass

        title_font = font.Font(self.window, family="Consolas", size=12, weight="bold")
        body_font = font.Font(self.window, family="Consolas", size=10)

        body_len = len(body)
        width = 360 if body_len <= 110 else 420
        title_width = width - 108
        body_width = width - 128
        title_lines = self._wrapped(title, title_font, title_width, 2)
        body_lines = self._wrapped(body, body_font, body_width, 18)
        title_h = max(24, len(title_lines) * 18)
        body_h = max(42, len(body_lines) * 16)

        button_h = 34
        height = 112 + title_h + body_h + button_h + 26
        screen_h = self.root.winfo_screenheight()
        if height > screen_h - 80:
            height = max(260, screen_h - 80)

        self.window.geometry(f"{width}x{height}")
        self.canvas = tk.Canvas(self.window, width=width, height=height, bg=KEY_COLOR, highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        x1, y1, x2, y2 = 12, 12, width - 12, height - 24
        polygon = (x1 + 12, y1, x2 - 12, y1, x2, y1 + 12, x2, y2 - 12,
                   x2 - 12, y2, x1 + 12, y2, x1, y2 - 12, x1, y1 + 12)
        self.canvas.create_polygon(polygon, fill=self.theme.bubble, outline=self.theme.bubble_accent,
                                   width=2, smooth=False)
        tail_points = getattr(self, "_tail_points", (x1 + 42, y2 - 1, x1 + 68, y2 - 1, x1 + 54, y2 + 18))
        self._tail_item = self.canvas.create_polygon(tail_points, fill=self.theme.bubble, outline=self.theme.bubble_accent)

        self.canvas.create_rectangle(20, 26, 74, 80, fill=self.theme.panel, outline=self.theme.bubble_accent, width=2)
        if portrait is not None:
            self.canvas.create_image(47, 53, image=portrait)
        else:
            self.canvas.create_text(47, 53, text="S", fill=self.theme.accent, font=("Consolas", 20, "bold"))

        self.canvas.create_text(88, 34, anchor="w", text="SOPHIA", fill=self.theme.text,
                                font=("Consolas", 11, "bold"))
        pill_x1, pill_x2 = width - 100, width - 16
        self._status_item = self.canvas.create_rectangle(pill_x1, 24, pill_x2, 44, fill=self.theme.pill, outline=self.theme.pill)
        self._status_text_item = self.canvas.create_text((pill_x1 + pill_x2) // 2, 34, text=status.upper(), fill="#ffffff",
                                                          font=("Consolas", 8, "bold"))

        title_y = 72
        body_y = title_y + title_h + 8
        self._title_text_item = self.canvas.create_text(88, title_y, anchor="nw", text="\n".join(title_lines), fill=self.theme.text,
                                                        font=title_font, width=title_width)
        available_body_h = height - body_y - button_h - 34
        actual_body_h = min(body_h, max(42, available_body_h))
        self.canvas.create_rectangle(88, body_y, 92, body_y + actual_body_h,
                                     fill=self.theme.bubble_accent, outline=self.theme.bubble_accent)
        self._body_text_item = self.canvas.create_text(104, body_y, anchor="nw", text="", fill=self.theme.text,
                                                       font=body_font, width=body_width)

        button_y = height - button_h - 26
        button_x1 = width - 146
        button_x2 = width - 18
        self.canvas.create_rectangle(button_x1, button_y, button_x2, button_y + button_h,
                                     fill=self.theme.bubble_accent, outline=self.theme.bubble_accent)
        self.canvas.create_text((button_x1 + button_x2) // 2, button_y + button_h // 2,
                                text="ENTENDIDO", fill="#ffffff", font=("Consolas", 9, "bold"))
        self.canvas.tag_bind("all", "<Button-1>", lambda _: self.close(on_close))
        self.canvas.bind("<Escape>", lambda _: self.close(on_close))

        self._type_text("\n".join(body_lines), 0)
        duration = max(4000, min(18000, seconds * 1000 + len(body) * 22))
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

    def position_near(self, root_x: int, root_y: int, root_width: int = 360,
                      terminal_rect: Rect | None = None, root_height: int = 160) -> None:
        if self.window is None or not self.window.winfo_exists():
            return
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        monitor = monitor_at(root_x + root_width // 2, root_y + root_height // 2)
        pet = Rect(root_x, root_y, root_width, root_height)
        terminal = terminal_rect or Rect(monitor.x, monitor.bottom, 0, 0)
        placement = place_bubble(pet, terminal, Rect(0, 0, width, height), monitor)
        if self.canvas is not None and self.canvas.winfo_exists() and hasattr(self, "_tail_item"):
            y2 = height - 24
            tail_x = max(12, min(width - 12, placement.tail_x - placement.x))
            tail = (tail_x - 13, y2 - 1, tail_x + 13, y2 - 1, tail_x, y2 + 18)
            self.canvas.coords(self._tail_item, *tail)
        self.window.geometry(f"+{placement.x}+{placement.y}")
        self.window.update_idletasks()
        self.window.deiconify()

    def show_thinking(self, portrait: object | None = None) -> None:
        self.show("", "Procesando tu mensaje", "look", "PENSANDO", portrait, seconds=60)
        if not hasattr(self, "_thinking_dot_id"):
            self._thinking_dot_index = 0
        self._thinking_dot_index = 0
        dots = ["●○○", "○●○", "○○●"]
        def animate() -> None:
            if self.canvas is None or not self.canvas.winfo_exists():
                return
            value = dots[self._thinking_dot_index % len(dots)]
            self._thinking_dot_index += 1
            if hasattr(self, "_body_text_item"):
                self.canvas.itemconfigure(self._body_text_item, text=value)
            self._thinking_dot_id = self.root.after(350, animate)
        animate()

    def update_content(self, title: str, body: str, expression: str = "calm", portrait: object | None = None) -> None:
        if self.window is None or not self.window.winfo_exists():
            return
        if hasattr(self, "_thinking_dot_id"):
            try:
                self.root.after_cancel(self._thinking_dot_id)
            except tk.TclError:
                pass
        if hasattr(self, "_type_id"):
            try:
                self.root.after_cancel(self._type_id)
            except tk.TclError:
                pass
        title_font = font.Font(self.window, family="Consolas", size=12, weight="bold")
        body_font = font.Font(self.window, family="Consolas", size=10)
        width = self.window.winfo_width()
        title_lines = self._wrapped(title, title_font, max(180, width - 108), 2)
        body_lines = self._wrapped(body, body_font, max(180, width - 128), 18)
        if hasattr(self, "_title_text_item"):
            self.canvas.itemconfigure(self._title_text_item, text="\n".join(title_lines))
        else:
            self._title_text_item = self.canvas.create_text(88, 72, anchor="nw", text="\n".join(title_lines), fill=self.theme.text, font=title_font, width=max(180, width - 108))
        self._type_text("\n".join(body_lines), 0)

    def play_stage(self, frames: list[object], on_done: Callable[[], None] | None = None) -> None:
        if self.window is None or self.canvas is None or not self.window.winfo_exists():
            return
        from PIL import ImageTk
        self._stage_photos = [ImageTk.PhotoImage(frame) for frame in frames]
        if not self._stage_photos:
            if on_done:
                on_done()
            return
        width = 400
        height = 250
        self.window.withdraw()
        self.window.geometry(f"{width}x{height}")
        self.canvas.configure(width=width, height=height)
        self.canvas.delete("all")
        x1, y1, x2, y2 = 12, 12, width - 12, height - 24
        self.canvas.create_polygon((x1 + 12, y1, x2 - 12, y1, x2, y1 + 12, x2, y2 - 12,
                                    x2 - 12, y2, x1 + 12, y2, x1, y2 - 12, x1, y1 + 12),
                                   fill=self.theme.bubble, outline=self.theme.bubble_accent, width=2)
        self.canvas.create_text(88, 34, anchor="w", text="SOPHIA", fill=self.theme.text,
                                font=("Consolas", 11, "bold"))
        self.canvas.create_rectangle(width - 100, 24, width - 16, 44, fill=self.theme.pill, outline=self.theme.pill)
        self.canvas.create_text(width - 58, 34, text="LISTA", fill="#ffffff", font=("Consolas", 8, "bold"))
        self._stage_item = self.canvas.create_image(200, 145, image=self._stage_photos[0])
        self._stage_index = 0
        durations = [140, 200, 110, 110, 110, 90, 160, 160, 260]
        def advance() -> None:
            if self.canvas is None or not self.canvas.winfo_exists():
                return
            self._stage_index += 1
            if self._stage_index >= len(self._stage_photos):
                if on_done:
                    on_done()
                return
            self.canvas.itemconfigure(self._stage_item, image=self._stage_photos[self._stage_index])
            delay = durations[self._stage_index] if self._stage_index < len(durations) else 260
            self._stage_id = self.root.after(delay, advance)
        self._stage_id = self.root.after(durations[0], advance)
        self.window.deiconify()

    def close(self, on_close: Callable[[], None] | None = None) -> None:
        for attr in ("_close_id", "_type_id", "_thinking_dot_id", "_stage_id"):
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
