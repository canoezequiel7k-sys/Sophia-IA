from __future__ import annotations

import tkinter as tk
from tkinter import Menu


class ChatView:
    """Vista de chat Tk con estilos básicos y copia por clic derecho."""

    def __init__(self, parent: tk.Widget) -> None:
        self.text = tk.Text(parent, wrap=tk.WORD, bd=0, padx=10, pady=10,
                            bg="#161a29", fg="#edf2f7", font=("Segoe UI", 9))
        self.text.configure(state=tk.DISABLED)
        self.text.tag_configure("user_name", foreground="#f6ad55", font=("Segoe UI", 9, "bold"))
        self.text.tag_configure("user_text", foreground="#cbd5e0")
        self.text.tag_configure("sophia_name", foreground="#00f0ff", font=("Segoe UI", 9, "bold"))
        self.text.tag_configure("sophia_text", foreground="#edf2f7")
        self.text.tag_configure("error", foreground="#fc8181")
        self.text.bind("<Button-3>", self._copy_menu)

    def append(self, speaker: str, message: str, error: bool = False) -> None:
        self.text.configure(state=tk.NORMAL)
        if speaker == "Vos":
            self.text.insert(tk.END, "Vos: ", "user_name")
            self.text.insert(tk.END, message + "\n\n", "user_text")
        else:
            self.text.insert(tk.END, "Sophia: ", "sophia_name")
            self.text.insert(tk.END, message + "\n\n", "error" if error else "sophia_text")
        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)

    def _copy_menu(self, event: tk.Event) -> None:
        menu = Menu(self.text, tearoff=0)
        menu.add_command(label="Copiar", command=lambda: self.text.event_generate("<<Copy>>"))
        menu.tk_popup(event.x_root, event.y_root)
