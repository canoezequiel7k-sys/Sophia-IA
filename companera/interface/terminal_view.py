from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import Menu
from typing import Callable

from companera.application.commands import COMMANDS
from companera.interface.terminal_render import parse_inline, wrap
from companera.interface.theme import TERMINAL_THEME, terminal_font


class TerminalView(tk.Frame):
    def __init__(self, master, on_submit: Callable[[str], None], model: str = "gemini", on_palette: Callable[[], None] | None = None) -> None:
        super().__init__(master, bg=TERMINAL_THEME.background)
        self.on_submit = on_submit
        self.on_palette = on_palette
        self.model = model
        self.history: list[tuple[str, str, bool]] = []
        self.sent_history: list[str] = []
        self.sent_index = 0
        self._thinking = False
        self._spinner_index = 0
        self._thinking_started = 0
        family, size = terminal_font(self)
        mono = (family, size)

        self.log = tk.Text(self, bg=TERMINAL_THEME.background, fg=TERMINAL_THEME.text,
                           insertbackground=TERMINAL_THEME.accent_light, selectbackground="#3f3268",
                           bd=0, padx=14, pady=10, wrap=tk.WORD, font=mono, state=tk.DISABLED)
        self.scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.log.yview)
        self.log.configure(yscrollcommand=self._on_scroll)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.log.tag_configure("user_bar", foreground=TERMINAL_THEME.accent)
        self.log.tag_configure("sophia", foreground=TERMINAL_THEME.sophia, font=(family, size, "bold"))
        self.log.tag_configure("sophia_text", foreground=TERMINAL_THEME.text, font=mono)
        self.log.tag_configure("error", foreground=TERMINAL_THEME.error, font=mono)
        self.log.tag_configure("muted", foreground=TERMINAL_THEME.muted, font=(family, size - 1))
        self.log.tag_configure("bold", foreground=TERMINAL_THEME.text, font=(family, size, "bold"))
        self.log.tag_configure("code", foreground=TERMINAL_THEME.code, font=mono)

        self.jump = tk.Label(self, text="Ir al final ↓", bg=TERMINAL_THEME.surface, fg=TERMINAL_THEME.accent_light,
                             font=(family, 9), padx=8, pady=3, cursor="hand2")
        self.jump.bind("<Button-1>", lambda _e: self.scroll_to_end())

        prompt_wrap = tk.Frame(self, bg=TERMINAL_THEME.background, padx=10, pady=6)
        prompt_wrap.pack(side=tk.BOTTOM, fill=tk.X)
        prompt_box = tk.Frame(prompt_wrap, bg=TERMINAL_THEME.surface, highlightbackground=TERMINAL_THEME.accent,
                              highlightthickness=2)
        prompt_box.pack(fill=tk.X)
        tk.Label(prompt_box, text="›", bg=TERMINAL_THEME.surface, fg=TERMINAL_THEME.accent_light,
                 font=(family, 14, "bold"), padx=8).pack(side=tk.LEFT, anchor="n", pady=4)
        self.prompt = tk.Text(prompt_box, bg=TERMINAL_THEME.surface, fg=TERMINAL_THEME.text,
                              insertbackground=TERMINAL_THEME.accent_light, selectbackground="#3f3268",
                              bd=0, height=1, wrap=tk.WORD, font=mono, padx=4, pady=8)
        self.prompt.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.prompt_placeholder = True
        self._set_placeholder()
        self.prompt.bind("<FocusIn>", self._clear_placeholder)
        self.prompt.bind("<Return>", self._enter)
        self.prompt.bind("<KeyRelease>", self._prompt_key_release)
        self.prompt.bind("<Up>", self._history_up)
        self.prompt.bind("<Down>", self._history_down)
        self.prompt.bind("<Control-l>", lambda _e: self.clear_view())
        self.prompt.bind("<Control-c>", lambda _e: "break")
        self.prompt.bind("<Control-p>", lambda _e: self._open_palette())
        self.prompt.bind("<Tab>", self._slash_tab)
        self.prompt.bind("<Escape>", lambda _e: self._close_slash_menu())
        self.prompt.bind("<Button-3>", lambda e: self._copy_or_context(e))

        self.status = tk.Label(prompt_wrap, text=f"Sophia · {model} · Gemini", bg=TERMINAL_THEME.background,
                               fg=TERMINAL_THEME.muted, font=(family, 9), anchor="w")
        self.status.pack(side=tk.LEFT, fill=tk.X, pady=6)
        self.status_right = tk.Label(prompt_wrap, text="● ONLINE", bg=TERMINAL_THEME.background,
                                     fg="#68d391", font=(family, 9), anchor="e")
        self.status_right.pack(side=tk.RIGHT, pady=6)
        self._slash_menu: Menu | None = None

        footer = tk.Label(self, text="~/Documents/Sophia IA                    ctrl+p comandos",
                          bg=TERMINAL_THEME.background, fg=TERMINAL_THEME.muted, font=(family, 8), anchor="w", padx=10)
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=3)
        self._resize_id = None
        self.bind("<Configure>", self._schedule_reflow)
        self.log.bind("<Button-3>", self._copy_or_context)

    def _set_placeholder(self) -> None:
        self.prompt.configure(fg=TERMINAL_THEME.muted)
        self.prompt.insert("1.0", "Preguntale algo a Sophia…")
        self.prompt_placeholder = True

    def _clear_placeholder(self, _event=None) -> None:
        if self.prompt_placeholder:
            self.prompt.delete("1.0", tk.END)
            self.prompt.configure(fg=TERMINAL_THEME.text)
            self.prompt_placeholder = False

    def _enter(self, event=None) -> str:
        if event is not None and event.state & 0x1:
            return None
        self._clear_placeholder()
        text = self.prompt.get("1.0", "end-1c").strip()
        if not text:
            return "break"
        self.prompt.delete("1.0", tk.END)
        self.prompt_placeholder = False
        self.sent_history.append(text)
        self.sent_index = len(self.sent_history)
        self.on_submit(text)
        return "break"

    def _prompt_key_release(self, _event=None) -> None:
        self._resize_prompt()
        text = self.prompt.get("1.0", "end-1c").strip()
        if text.startswith("/"):
            matches = [command.strip() for command in COMMANDS if command.strip().startswith(text)]
            if matches:
                if self._slash_menu is not None:
                    self._slash_menu.unpost()
                menu = Menu(self.prompt, tearoff=0, bg=TERMINAL_THEME.surface, fg=TERMINAL_THEME.text,
                            activebackground=TERMINAL_THEME.accent, activeforeground="#ffffff")
                for command in matches[:8]:
                    menu.add_command(label=command, command=lambda value=command: self._insert_slash(value))
                x = self.prompt.winfo_rootx() + 12
                y = self.prompt.winfo_rooty() - min(210, 28 * len(matches[:8]))
                menu.tk_popup(x, y)
                self._slash_menu = menu
        else:
            self._close_slash_menu()

    def _insert_slash(self, command: str) -> None:
        self._clear_placeholder()
        self.prompt.delete("1.0", tk.END)
        self.prompt.insert("1.0", command)
        self.prompt.focus_set()

    def _resize_prompt(self, _event=None) -> None:
        if self.prompt_placeholder:
            return
        content = self.prompt.get("1.0", "end-1c")
        lines = max(1, min(5, content.count("\n") + 1))
        self.prompt.configure(height=lines)

    def _history_up(self, _event=None) -> str:
        if not self.sent_history:
            return "break"
        self._clear_placeholder()
        self.sent_index = max(0, self.sent_index - 1)
        self.prompt.delete("1.0", tk.END)
        self.prompt.insert("1.0", self.sent_history[self.sent_index])
        return "break"

    def _history_down(self, _event=None) -> str:
        if not self.sent_history:
            return "break"
        self.sent_index = min(len(self.sent_history), self.sent_index + 1)
        self.prompt.delete("1.0", tk.END)
        if self.sent_index < len(self.sent_history):
            self.prompt.insert("1.0", self.sent_history[self.sent_index])
        return "break"

    def _open_palette(self) -> str:
        if self.on_palette is not None:
            self.on_palette()
        return "break"

    def _slash_tab(self, _event=None) -> str:
        text = self.prompt.get("1.0", "end-1c").strip()
        if text.startswith("/"):
            matches = [c.strip() for c in COMMANDS if c.strip().startswith(text)]
            if matches:
                self.prompt.delete("1.0", tk.END)
                self.prompt.insert("1.0", matches[0])
        return "break"

    def _close_slash_menu(self) -> None:
        if self._slash_menu is not None:
            self._slash_menu.unpost()
            self._slash_menu = None

    def _copy_or_context(self, event=None) -> None:
        if event is not None and hasattr(event, "x_root"):
            try:
                self.clipboard_clear()
                selection = self.log.selection_get()
                self.clipboard_append(selection)
            except Exception:
                pass

    def append_user(self, text: str) -> None:
        self.history.append(("user", text, False))
        self._trim_history()
        self._render_all()

    def append_sophia(self, text: str, error: bool = False) -> None:
        self.set_thinking(False)
        self.history.append(("sophia", text, error))
        self._trim_history()
        self._render_all()

    def clear_view(self, _event=None) -> str:
        self.history.clear()
        self._render_all()
        return "break"

    def _trim_history(self) -> None:
        if len(self.history) > 300:
            self.history = self.history[-300:]

    def _render_all(self) -> None:
        if not self.winfo_exists():
            return
        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        family, size = terminal_font(self)
        columns = max(40, int(self.winfo_width() / 7.0))
        for role, text, error in self.history:
            if role == "user":
                for line in wrap(text, columns, " ▎  "):
                    if line.startswith(" ▎  "):
                        self.log.insert(tk.END, " ▎  ", "user_bar")
                        line = line[4:]
                    self.log.insert(tk.END, line + "\n", "sophia_text")
                self.log.insert(tk.END, "\n")
            else:
                stamp = datetime.now().strftime("%H:%M")
                self.log.insert(tk.END, f"◆ Sophia · {stamp}\n", "error" if error else "sophia")
                for line in wrap(text, columns):
                    for kind, chunk in parse_inline(line):
                        self.log.insert(tk.END, chunk, kind)
                    self.log.insert(tk.END, "\n")
                self.log.insert(tk.END, "\n")
        self.log.configure(state=tk.DISABLED)
        self.after_idle(self.scroll_to_end)

    def set_thinking(self, on: bool) -> None:
        self._thinking = on
        if on:
            import time
            self._thinking_started = time.monotonic()
            self._spinner_index = 0
            self._spin_thinking()
            self.status_right.configure(text="PENSANDO", fg="#f6ad55")
        else:
            self.status_right.configure(text="● ONLINE", fg="#68d391")

    def _spin_thinking(self) -> None:
        if not self.winfo_exists() or not self._thinking:
            return
        import time
        frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        elapsed = int(time.monotonic() - self._thinking_started)
        frame = frames[self._spinner_index % len(frames)]
        self._spinner_index += 1
        self.status_right.configure(text=f"{frame} PENSANDO {elapsed}s", fg="#f6ad55")
        self.after(90, self._spin_thinking)

    def set_status(self, text: str, color: str = "#68d391") -> None:
        self.status_right.configure(text=text, fg=color)

    def _schedule_reflow(self, _event=None) -> None:
        if self._resize_id is not None:
            self.after_cancel(self._resize_id)
        self._resize_id = self.after(150, self._render_all)

    def _on_scroll(self, first: str, last: str) -> None:
        self.scrollbar.set(first, last)
        if float(last) < 0.995:
            self.jump.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")
        elif self.jump.winfo_manager() == "place":
            self.jump.place_forget()

    def scroll_to_end(self) -> None:
        self.log.see(tk.END)
        if self.jump.winfo_manager() == "place":
            self.jump.place_forget()
