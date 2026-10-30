from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Callable

from companera.interface.theme import TERMINAL_THEME, terminal_font


@dataclass(frozen=True)
class PaletteAction:
    label: str
    hint: str
    callback: Callable[[], None]


class CommandPalette:
    def __init__(self, root: tk.Tk, actions: list[PaletteAction]) -> None:
        self.root = root
        self.actions = actions
        self.filtered = actions
        self.window: tk.Toplevel | None = None
        self.selected = 0

    def open(self) -> None:
        if self.window is not None and self.window.winfo_exists():
            self.close()
            return
        self.window = tk.Toplevel(self.root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=TERMINAL_THEME.border, highlightbackground=TERMINAL_THEME.accent,
                              highlightthickness=1)
        family, size = terminal_font(self.window)
        self.entry = tk.Entry(self.window, bg=TERMINAL_THEME.surface, fg=TERMINAL_THEME.text,
                              insertbackground=TERMINAL_THEME.accent_light, bd=0,
                              font=(family, size), relief=tk.FLAT)
        self.entry.pack(fill=tk.X, padx=1, pady=1, ipady=8)
        self.entry.bind("<KeyRelease>", lambda _e: self._filter())
        self.entry.bind("<Up>", lambda _e: self._move(-1))
        self.entry.bind("<Down>", lambda _e: self._move(1))
        self.entry.bind("<Return>", lambda _e: self._run())
        self.entry.bind("<Escape>", lambda _e: self.close())
        self.listbox = tk.Listbox(self.window, bg=TERMINAL_THEME.background, fg=TERMINAL_THEME.text,
                                  selectbackground=TERMINAL_THEME.accent, selectforeground="#ffffff",
                                  bd=0, highlightthickness=0, font=(family, size), height=10)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.listbox.bind("<Double-Button-1>", lambda _e: self._run())
        self._refresh()
        x = self.root.winfo_rootx() + 80
        y = self.root.winfo_rooty() + 100
        self.window.geometry(f"420x300+{x}+{y}")
        self.window.deiconify()
        self.entry.focus_set()

    def _filter(self) -> None:
        query = self.entry.get().lower().strip()
        self.filtered = [a for a in self.actions if query in a.label.lower() or query in a.hint.lower()] if query else self.actions
        self.selected = 0
        self._refresh()

    def _refresh(self) -> None:
        self.listbox.delete(0, tk.END)
        for action in self.filtered:
            text = action.label if not action.hint else f"{action.label}  ·  {action.hint}"
            self.listbox.insert(tk.END, text)
        if self.filtered:
            self.listbox.selection_set(0)

    def _move(self, delta: int) -> str:
        if not self.filtered:
            return "break"
        self.selected = max(0, min(len(self.filtered) - 1, self.selected + delta))
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(self.selected)
        self.listbox.activate(self.selected)
        self.listbox.see(self.selected)
        return "break"

    def _run(self) -> str:
        if 0 <= self.selected < len(self.filtered):
            action = self.filtered[self.selected]
            self.close()
            action.callback()
        return "break"

    def close(self) -> None:
        if self.window is not None and self.window.winfo_exists():
            self.window.destroy()
        self.window = None
