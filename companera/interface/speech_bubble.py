from __future__ import annotations

import tkinter as tk
from tkinter import font
from typing import Callable

from companera.interface.theme import Theme, theme_for
from companera.interface.layout import place_bubble
from companera.interface.screen_metrics import Rect, monitor_at, ui_scale
from companera.interface.bubble_layout import compute_layout
from companera.interface.intro_sequence import INTRO_SEQUENCE


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
        self._status = "LISTA"
        self._anchor = None
        self._last_title = ""
        self._last_body = ""
        self._last_portrait = None
        self._last_expression = "calm"
        self._thinking_dot_id = None
        self._stage_photos = []
        self._stage_item = None
        self._portrait_item = None
        self._portrait_photos = []
        self._portrait_id = None
        self._portrait_index = 0

    def show(self, title: str, body: str, expression: str = "calm", status: str = "LISTA",
             portrait: object | None = None, seconds: float = 8.0, on_close: Callable[[], None] | None = None,
             stage_frames: list[object] | None = None) -> None:
        self._last_title = title
        self._last_body = body
        self._last_expression = expression
        self._last_portrait = portrait
        self._status = status
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

        scale = ui_scale(self.root)
        monitor = monitor_at(self.root.winfo_rootx(), self.root.winfo_rooty())
        max_height = max(280, int(monitor.h * 0.60))
        title_width_seed = 460 - 108
        body_width_seed = 460 - 128
        title_lines_seed = self._wrapped(title, title_font, int(title_width_seed * scale), 2)
        body_lines_seed = self._wrapped(body, body_font, int(body_width_seed * scale), 1000)
        stage_h = 126 if stage_frames else 0
        layout = compute_layout(title, "\n".join(body_lines_seed),
                                lambda text: title_font.measure(text),
                                lambda text: body_font.measure(text),
                                title_font.metrics("linespace"), body_font.metrics("linespace"),
                                scale=scale, max_height=max_height, stage_h=stage_h)
        width, height = layout.width, layout.height
        title_lines, body_lines = layout.title_lines, layout.body_lines
        title_width = width - int(108 * scale)
        body_width = width - int(128 * scale)

        self.window.geometry(f"{width}x{height}")
        self.canvas = tk.Canvas(self.window, width=width, height=height, bg=KEY_COLOR, highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        x1, y1, x2, y2 = int(12 * scale), int(12 * scale), width - int(12 * scale), height - int(24 * scale)
        polygon = (x1 + int(12 * scale), y1, x2 - int(12 * scale), y1, x2, y1 + int(12 * scale), x2, y2 - int(12 * scale),
                   x2 - int(12 * scale), y2, x1 + int(12 * scale), y2, x1, y2 - int(12 * scale), x1, y1 + int(12 * scale))
        self.canvas.create_polygon(polygon, fill=self.theme.bubble, outline=self.theme.bubble_accent, width=2, smooth=False)
        tail_points = (x1 + int(42 * scale), y2 - 1, x1 + int(68 * scale), y2 - 1, x1 + int(54 * scale), y2 + int(18 * scale))
        self._tail_item = self.canvas.create_polygon(tail_points, fill=self.theme.bubble, outline=self.theme.bubble_accent)

        header_y = int(26 * scale)
        self.canvas.create_rectangle(int(20 * scale), header_y, int(74 * scale), header_y + int(54 * scale),
                                     fill=self.theme.panel, outline=self.theme.bubble_accent, width=2)
        if portrait is not None:
            self._portrait_photos = [portrait]
            self._portrait_item = self.canvas.create_image(int(47 * scale), header_y + int(27 * scale), image=portrait)
        else:
            self._portrait_item = None
            self.canvas.create_text(int(47 * scale), header_y + int(27 * scale), text="S", fill=self.theme.accent,
                                    font=("Consolas", max(12, int(20 * scale)), "bold"))

        self.canvas.create_text(int(88 * scale), header_y + int(8 * scale), anchor="w", text="SOPHIA", fill=self.theme.text,
                                font=("Consolas", max(8, int(11 * scale)), "bold"))
        pill_x1, pill_x2 = width - int(100 * scale), width - int(16 * scale)
        self._status_item = self.canvas.create_rectangle(pill_x1, header_y - int(2 * scale), pill_x2, header_y + int(18 * scale),
                                                         fill=self.theme.pill, outline=self.theme.pill)
        self._status_text_item = self.canvas.create_text((pill_x1 + pill_x2) // 2, header_y + int(8 * scale),
                                                         text=status.upper(), fill="#ffffff",
                                                         font=("Consolas", max(8, int(8 * scale)), "bold"))

        if layout.stage_y is not None and stage_frames:
            from PIL import ImageTk
            self._stage_photos = [ImageTk.PhotoImage(frame) for frame in stage_frames]
            self._stage_item = self.canvas.create_image(width // 2, layout.stage_y + int(63 * scale),
                                                        image=self._stage_photos[0])

        self._title_text_item = self.canvas.create_text(int(88 * scale), layout.title_y, anchor="nw",
                                                        text="\n".join(title_lines), fill=self.theme.text,
                                                        font=title_font, width=title_width)
        self.canvas.create_rectangle(int(88 * scale), layout.body_y, int(92 * scale), layout.body_y + layout.body_h,
                                     fill=self.theme.bubble_accent, outline=self.theme.bubble_accent)
        self._body_text_item = self.canvas.create_text(int(104 * scale), layout.body_y, anchor="nw", text="",
                                                       fill=self.theme.text, font=body_font, width=body_width + int(4 * scale))

        button_x1, button_y, button_x2, button_y2 = layout.button
        self.canvas.create_rectangle(button_x1, button_y, button_x2, button_y2,
                                     fill=self.theme.bubble_accent, outline=self.theme.bubble_accent)
        self.canvas.create_text((button_x1 + button_x2) // 2, (button_y + button_y2) // 2,
                                text="ENTENDIDO", fill="#ffffff", font=("Consolas", max(8, int(9 * scale)), "bold"))
        self.canvas.tag_bind("all", "<Button-1>", lambda _: self.close(on_close))
        self.canvas.bind("<Escape>", lambda _: self.close(on_close))

        self._type_text("\n".join(body_lines), 0)
        duration = max(4000, min(18000, seconds * 1000 + len(body) * 22))
        self._close_id = self.root.after(int(duration), lambda: self.close(on_close))

    def update_status(self, status: str) -> None:
        if self.canvas is not None and self.canvas.winfo_exists() and hasattr(self, "_status_text_item"):
            self.canvas.itemconfigure(self._status_text_item, text=status.upper())

    def start_talking_portrait(self, portraits: list[object], interval_ms: int = 220) -> None:
        if not portraits:
            return
        self.stop_talking_portrait(portraits[0], cancel=True)
        self._portrait_photos = portraits
        self._portrait_index = 0

        def advance() -> None:
            if (self.canvas is None or not self.canvas.winfo_exists() or
                    self._portrait_item is None or not self._portrait_photos):
                return
            self._portrait_index = (self._portrait_index + 1) % len(self._portrait_photos)
            self.canvas.itemconfigure(self._portrait_item, image=self._portrait_photos[self._portrait_index])
            self._portrait_id = self.root.after(interval_ms, advance)

        self._portrait_id = self.root.after(interval_ms, advance)

    def stop_talking_portrait(self, final_portrait: object | None = None, cancel: bool = False) -> None:
        if self._portrait_id is not None:
            try:
                self.root.after_cancel(self._portrait_id)
            except tk.TclError:
                pass
            self._portrait_id = None
        if cancel or self.canvas is None or not self.canvas.winfo_exists() or self._portrait_item is None:
            return
        if final_portrait is not None:
            self.canvas.itemconfigure(self._portrait_item, image=final_portrait)

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
        self._anchor = (root_x, root_y, root_width, root_height, terminal_rect)
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        monitor = monitor_at(root_x + root_width // 2, root_y + root_height // 2)
        pet = Rect(root_x, root_y, root_width, root_height)
        terminal = terminal_rect or Rect(monitor.x, monitor.bottom, 0, 0)
        placement = place_bubble(pet, terminal, Rect(0, 0, width, height), monitor)
        if self.canvas is not None and self.canvas.winfo_exists() and hasattr(self, "_tail_item"):
            y2 = height - 24
            if placement.side in ("left", "right"):
                if placement.side == "left":
                    edge_x = width - 12
                    tail_x = edge_x
                else:
                    edge_x = 12
                    tail_x = edge_x
                tail_y = max(32, min(height - 40, placement.tail_y))
                tail = (edge_x, tail_y - 13, edge_x + (18 if placement.side == "right" else -18), tail_y,
                        edge_x, tail_y + 13)
            else:
                tail_x = max(12, min(width - 12, placement.tail_x))
                tail_y = y2
                if placement.side == "top":
                    tail = (tail_x - 13, 13, tail_x + 13, 13, tail_x, -18)
                else:
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
        anchor = self._anchor
        self.show(title, body, expression, "LISTA", portrait, seconds=12)
        if anchor is not None:
            rx, ry, rw, rh, terminal_rect = anchor
            self.position_near(rx, ry, rw, terminal_rect=terminal_rect, root_height=rh)
        else:
            self.window.deiconify()
        self.update_status("LISTA")

    def play_stage(self, frames: list[object], on_done: Callable[[], None] | None = None) -> None:
        if not frames:
            if on_done:
                on_done()
            return
        anchor = self._anchor
        self.show("¡Hola! Ya estoy acá", "Lista para acompañarte.", "calm", "LISTA",
                  stage_frames=frames, seconds=12)
        if anchor is not None:
            rx, ry, rw, rh, terminal_rect = anchor
            self.position_near(rx, ry, rw, terminal_rect=terminal_rect, root_height=rh)
        else:
            self.window.deiconify()
        self._stage_index = 0
        durations = [duration for _name, duration in INTRO_SEQUENCE]
        if len(durations) < len(frames):
            durations.extend([260] * (len(frames) - len(durations)))

        def advance() -> None:
            if self.canvas is None or not self.canvas.winfo_exists() or self._stage_item is None:
                return
            self._stage_index += 1
            if self._stage_index >= len(self._stage_photos):
                if on_done:
                    on_done()
                return
            self.canvas.itemconfigure(self._stage_item, image=self._stage_photos[self._stage_index])
            delay = max(90, int(durations[self._stage_index]))
            self._stage_id = self.root.after(delay, advance)
        delay = max(90, int(durations[0]))
        self._stage_id = self.root.after(delay, advance)

    def close(self, on_close: Callable[[], None] | None = None) -> None:
        for attr in ("_close_id", "_type_id", "_thinking_dot_id", "_stage_id", "_portrait_id"):
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
