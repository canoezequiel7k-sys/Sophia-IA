from __future__ import annotations

import tkinter as tk
from tkinter import Menu, ttk, font as tkfont
from typing import Callable, Optional

from companera.application.commands import COMMANDS
from companera.interface.terminal_render import parse_inline, wrap
from companera.interface.theme import TERMINAL_THEME, terminal_font
from companera.interface.terminal_model import TerminalHistory


class TerminalView(tk.Frame):
    def __init__(self, master, history: Optional[TerminalHistory] = None,
                 on_submit: Callable[[str], None] | None = None, model: str = "gemini",
                 on_palette: Callable[[], None] | None = None) -> None:
        super().__init__(master, bg=TERMINAL_THEME.background)
        self.on_submit = on_submit or (lambda _text: None)
        self.on_palette = on_palette
        self.model = model
        self.history = history or TerminalHistory()
        self._history_callback = lambda message: self.after_idle(self._render_all, message.role == "user" if message is not None else False)
        self.history.subscribe(self._history_callback)
        self.bind("<Destroy>", lambda _e: self.history.unsubscribe(self._history_callback))
        self._legacy_messages: list[tuple[str, str, bool, str]] = []
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
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Sophia.Vertical.TScrollbar", troughcolor=TERMINAL_THEME.background,
                        background=TERMINAL_THEME.border, bordercolor=TERMINAL_THEME.background,
                        lightcolor=TERMINAL_THEME.border, darkcolor=TERMINAL_THEME.border,
                        arrowcolor=TERMINAL_THEME.accent_light)
        style.map("Sophia.Vertical.TScrollbar", background=[("active", TERMINAL_THEME.accent)])
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, style="Sophia.Vertical.TScrollbar",
                                       command=self.log.yview)
        self.log.configure(yscrollcommand=self._on_scroll, wrap=tk.NONE, height=1)
        footer = tk.Frame(self, bg=TERMINAL_THEME.background, padx=10, pady=3)
        prompt_wrap = tk.Frame(self, bg=TERMINAL_THEME.background, padx=10, pady=6)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        prompt_wrap.pack(side=tk.BOTTOM, fill=tk.X)
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
        self.prompt.bind("<KeyPress>", self._placeholder_key_press)
        self.prompt.bind("<Return>", self._enter)
        self.prompt.bind("<KeyRelease>", self._prompt_key_release)
        self.prompt.bind("<Up>", self._history_up)
        self.prompt.bind("<Down>", self._history_down)
        self.prompt.bind("<Control-l>", lambda _e: self.clear_view())
        self.prompt.bind("<Control-c>", lambda _e: self._copy_prompt_selection(_e))
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

        footer_left = tk.Label(footer, text="~/Documents/Sophia IA", bg=TERMINAL_THEME.background,
                               fg=TERMINAL_THEME.muted, font=(family, 8), anchor="w")
        footer_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        footer_right = tk.Label(footer, text="ctrl+p comandos", bg=TERMINAL_THEME.background,
                                fg=TERMINAL_THEME.muted, font=(family, 8), anchor="e")
        footer_right.pack(side=tk.RIGHT)
        self._resize_id = None
        self.log.bind("<Configure>", self._schedule_reflow)
        self.log.bind("<Button-1>", lambda _e: self.log.focus_set())
        self.log.bind("<Control-c>", self._copy_selection)
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

    def _placeholder_key_press(self, event=None) -> str | None:
        if not self.prompt_placeholder:
            return None
        if event is not None:
            if event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
                                "Caps_Lock", "Num_Lock", "Scroll_Lock", "Up", "Down", "Left", "Right",
                                "Home", "End", "Page_Up", "Page_Down"):
                return None
            if event.keysym in ("BackSpace", "Delete"):
                return "break"
        self._clear_placeholder()
        return None

    def _enter(self, event=None) -> str:
        if event is not None and event.state & 0x1:
            return None
        if self._slash_menu is not None:
            try:
                if self._slash_menu.winfo_manager() == "place":
                    selection = self._slash_menu.curselection()
                    index = selection[0] if selection else 0
                    if 0 <= index < self._slash_menu.size():
                        command = self._slash_menu.get(index)
                        self._close_slash_menu()
                        self.prompt.delete("1.0", tk.END)
                        self.prompt_placeholder = False
                        text = command.strip()
                        if text:
                            self.sent_history.append(text)
                            self.sent_index = len(self.sent_history)
                            self.on_submit(text)
                            self.prompt.delete("1.0", tk.END)
                            self._set_placeholder()
                        return "break"
            except tk.TclError:
                pass
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

    def _prompt_key_release(self, event=None) -> None:
        self._resize_prompt()
        if event is not None and event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        text = self.prompt.get("1.0", "end-1c").strip()
        if text.startswith("/"):
            matches = [command.strip() for command in COMMANDS if text == "/" or command.strip().startswith(text)]
            if matches:
                rebuild = True
                if self._slash_menu is not None:
                    try:
                        current = [self._slash_menu.get(i) for i in range(self._slash_menu.size())]
                        rebuild = current != matches[:8]
                    except tk.TclError:
                        rebuild = True
                if rebuild:
                    if self._slash_menu is None:
                        self._slash_menu = tk.Listbox(self, bg=TERMINAL_THEME.surface, fg=TERMINAL_THEME.text,
                                                      selectbackground=TERMINAL_THEME.accent,
                                                      selectforeground="#ffffff", bd=1,
                                                      highlightthickness=1,
                                                      highlightbackground=TERMINAL_THEME.border,
                                                      activestyle="none",
                                                      font=(terminal_font(self)[0], terminal_font(self)[1]))
                    else:
                        self._slash_menu.delete(0, tk.END)
                    for command in matches[:8]:
                        self._slash_menu.insert(tk.END, command)
                    if self._slash_menu.size() > 0:
                        self._slash_menu.selection_set(0)
                        self._slash_menu.activate(0)
                menu_width = min(360, max(220, self.winfo_width() - 108))
                menu_height = min(210, 28 * max(1, self._slash_menu.size()))
                y = max(8, self.prompt.winfo_rooty() - self.winfo_rooty() - menu_height - 8)
                self._slash_menu.place(x=54, y=y, width=menu_width, height=menu_height)
                self._slash_menu.lift()
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
        if self._slash_menu is not None and self._slash_menu.winfo_manager() == "place":
            selection = self._slash_menu.curselection()
            index = max(0, (selection[0] - 1) if selection else 0)
            self._slash_menu.selection_clear(0, tk.END)
            self._slash_menu.selection_set(index)
            self._slash_menu.activate(index)
            self._slash_menu.see(index)
            return "break"
        if not self.sent_history:
            return "break"
        if self.prompt.index(tk.INSERT).split(".")[0] != "1":
            return None
        self._clear_placeholder()
        self.sent_index = max(0, self.sent_index - 1)
        self.prompt.delete("1.0", tk.END)
        self.prompt.insert("1.0", self.sent_history[self.sent_index])
        return "break"

    def _history_down(self, _event=None) -> str:
        if self._slash_menu is not None and self._slash_menu.winfo_manager() == "place":
            selection = self._slash_menu.curselection()
            index = min(self._slash_menu.size() - 1, (selection[0] + 1) if selection else 0)
            self._slash_menu.selection_clear(0, tk.END)
            self._slash_menu.selection_set(index)
            self._slash_menu.activate(index)
            self._slash_menu.see(index)
            return "break"
        if not self.sent_history:
            return "break"
        last_line = str(self.prompt.index("end-1c")).split(".")[0]
        if self.prompt.index(tk.INSERT).split(".")[0] != last_line:
            return None
        self.sent_index = min(len(self.sent_history), self.sent_index + 1)
        self.prompt.delete("1.0", tk.END)
        if self.sent_index < len(self.sent_history):
            self.prompt.insert("1.0", self.sent_history[self.sent_index])
        return "break"

    def _open_palette(self) -> str:
        self._clear_placeholder()
        self.prompt.delete("1.0", tk.END)
        self.prompt.insert("1.0", "/")
        self.prompt.focus_set()
        self._prompt_key_release()
        return "break"

    def _slash_tab(self, _event=None) -> str:
        text = self.prompt.get("1.0", "end-1c").strip()
        if text.startswith("/"):
            if self._slash_menu is not None and self._slash_menu.size() > 0:
                selection = self._slash_menu.curselection()
                index = selection[0] if selection else 0
                value = self._slash_menu.get(index)
                self._insert_slash(value)
            else:
                matches = [c.strip() for c in COMMANDS if c.strip().startswith(text)]
                if matches:
                    self._insert_slash(matches[0])
        return "break"

    def _close_slash_menu(self) -> None:
        if self._slash_menu is not None:
            self._slash_menu.place_forget()
            self._slash_menu.destroy()
            self._slash_menu = None

    def _copy_selection(self, _event=None) -> str:
        try:
            selection = self.log.selection_get()
            self.log.clipboard_clear()
            self.log.clipboard_append(selection)
        except tk.TclError:
            pass
        return "break"

    def _copy_prompt_selection(self, _event=None) -> str:
        try:
            selection = self.prompt.selection_get()
            self.prompt.clipboard_clear()
            self.prompt.clipboard_append(selection)
        except tk.TclError:
            pass
        return "break"

    def _copy_or_context(self, event=None) -> None:
        if event is not None and hasattr(event, "x_root"):
            try:
                self.clipboard_clear()
                selection = self.log.selection_get()
                self.clipboard_append(selection)
            except Exception:
                pass

    def append_user(self, text: str) -> None:
        self.history.add_user(text)

    def append_sophia(self, text: str, error: bool = False) -> None:
        self.set_thinking(False)
        self.history.add_sophia(text, error)

    def clear_view(self, _event=None) -> str:
        self.history.clear()
        self._render_all()
        return "break"

    def _trim_history(self) -> None:
        return

    def _render_all(self, force_user: bool = False) -> None:
        if not self.winfo_exists():
            return
        if self.log.winfo_width() <= 1:
            self.after_idle(self._render_all)
            return
        at_bottom = self.log.yview()[1] >= 0.999
        old_position = self.log.yview()[0]
        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        family, size = terminal_font(self)
        fnt = tkfont.Font(font=self.log.cget("font"))
        char_w = max(1, fnt.measure("0"))
        pad = int(str(self.log.cget("padx")).split()[0] if self.log.cget("padx") else 14)
        columns = max(30, (self.log.winfo_width() - 2 * pad - 4) // char_w - 1)
        for message in self.history.messages:
            if message.role == "user":
                for line in wrap(message.text, columns, " ▎  "):
                    if line.startswith(" ▎  "):
                        self.log.insert(tk.END, " ▎  ", "user_bar")
                        line = line[4:]
                    self.log.insert(tk.END, line + "\n", "sophia_text")
                self.log.insert(tk.END, "\n")
            else:
                self.log.insert(tk.END, f"◆ Sophia · {message.stamp}\n", "error" if message.error else "sophia")
                for line in wrap(message.text, columns):
                    for kind, chunk in parse_inline(line):
                        self.log.insert(tk.END, chunk, kind)
                    self.log.insert(tk.END, "\n")
                self.log.insert(tk.END, "\n")
        self.log.configure(state=tk.DISABLED)
        if at_bottom or force_user:
            self.after_idle(self.scroll_to_end)
        else:
            self.log.yview_moveto(old_position)
            if self.jump.winfo_manager() != "place":
                self.jump.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")

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
