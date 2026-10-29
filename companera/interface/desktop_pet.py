import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk
from typing import Any

from PIL import Image, ImageTk

from companera.application.companion import CheckInUseCase
from companera.application.knowledge import SearchKnowledgeUseCase
from companera.domain.models import CheckIn, Mood, Topic
from companera.infrastructure.gemini_service import GeminiService
from companera.infrastructure.json_memory_repository import JsonMemoryRepository
from companera.infrastructure.system_clock import SystemClock


class SophiaDesktopApp:
    """Ventana interactiva de escritorio para Sophia en segundo monitor."""

    def __init__(
        self,
        memory: JsonMemoryRepository,
        knowledge: SearchKnowledgeUseCase,
        gemini: GeminiService,
        local_use_case: CheckInUseCase,
        clock: SystemClock,
    ):
        self.memory = memory
        self.knowledge = knowledge
        self.gemini = gemini
        self.local_use_case = local_use_case
        self.clock = clock

        self.project_root = Path(__file__).resolve().parents[2]
        self.assets_dir = self.project_root / "companera" / "assets" / "sophia"

        self.root = tk.Tk()
        self.root.title("Sophia IA — Compañera")
        self.root.geometry("380x600")
        self.root.minsize(340, 500)
        self.root.configure(bg="#0f111a")

        # Configurar icono si existe
        icon_path = self.assets_dir / "capri.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

        self._drag_data = {"x": 0, "y": 0}
        self._is_always_on_top = False
        self._current_expression = "calm"
        self._cached_images: dict[str, ImageTk.PhotoImage] = {}

        self._load_sprites()
        self._build_ui()
        self._setup_events()

        # Mensaje de bienvenida inicial
        self._add_sophia_message(
            "¡Hola! Ya estoy en tu pantalla. Podés moverme a tu segundo monitor "
            "haciendo clic y arrastrando la barra superior. ¿En qué te ayudo hoy con Python?",
            "calm",
        )

    def _load_sprites(self) -> None:
        """Carga y reescala las expresiones de Sophia para la interfaz."""
        target_size = (160, 160)
        expressions = ["calm", "laugh", "smug", "look", "aside", "wide", "many"]
        for expr in expressions:
            img_file = self.assets_dir / f"face-{expr}.png"
            if img_file.exists():
                try:
                    pil_img = Image.open(img_file).convert("RGBA")
                    pil_img = pil_img.resize(target_size, Image.Resampling.LANCZOS)
                    self._cached_images[expr] = ImageTk.PhotoImage(pil_img)
                except Exception:
                    pass

    def _build_ui(self) -> None:
        """Construye los componentes visuales con estética cyberpunk oscura."""
        # Barra de título personalizada
        self.title_bar = tk.Frame(self.root, bg="#161a29", height=32)
        self.title_bar.pack(fill=tk.X, side=tk.TOP)
        self.title_bar.pack_propagate(False)

        title_label = tk.Label(
            self.title_bar,
            text="✦ SOPHIA IA",
            fg="#00f0ff",
            bg="#161a29",
            font=("Segoe UI", 10, "bold"),
        )
        title_label.pack(side=tk.LEFT, padx=10)

        # Botones de control de ventana
        btn_close = tk.Button(
            self.title_bar,
            text="✕",
            command=self.root.destroy,
            fg="#a0aec0",
            bg="#161a29",
            activeforeground="#ff5555",
            activebackground="#161a29",
            bd=0,
            padx=8,
            font=("Segoe UI", 9),
            cursor="hand2",
        )
        btn_close.pack(side=tk.RIGHT)

        self.btn_pin = tk.Button(
            self.title_bar,
            text="📌",
            command=self._toggle_always_on_top,
            fg="#718096",
            bg="#161a29",
            activeforeground="#00f0ff",
            activebackground="#161a29",
            bd=0,
            padx=6,
            font=("Segoe UI", 9),
            cursor="hand2",
        )
        self.btn_pin.pack(side=tk.RIGHT)

        # Área del personaje (Avatar y estado)
        avatar_frame = tk.Frame(self.root, bg="#0f111a", pady=8)
        avatar_frame.pack(fill=tk.X)

        self.avatar_label = tk.Label(avatar_frame, bg="#0f111a", cursor="hand2")
        self.avatar_label.pack()
        self._update_avatar("calm")
        self.avatar_label.bind("<Button-1>", lambda e: self._on_avatar_click())

        self.status_label = tk.Label(
            avatar_frame,
            text="🟢 Conectada",
            fg="#68d391",
            bg="#0f111a",
            font=("Segoe UI", 8),
        )
        self.status_label.pack(pady=(4, 0))

        # Área de diálogo / chat con scroll
        chat_frame = tk.Frame(self.root, bg="#0f111a", padx=12, pady=4)
        chat_frame.pack(fill=tk.BOTH, expand=True)

        self.chat_history = tk.Text(
            chat_frame,
            bg="#161a29",
            fg="#e2e8f0",
            insertbackground="#00f0ff",
            selectbackground="#2d3748",
            wrap=tk.WORD,
            bd=0,
            padx=10,
            pady=10,
            font=("Segoe UI", 9),
        )
        self.chat_history.pack(fill=tk.BOTH, expand=True)
        self.chat_history.configure(state=tk.DISABLED)

        # Configurar etiquetas de estilo para el chat
        self.chat_history.tag_configure("sophia_name", foreground="#00f0ff", font=("Segoe UI", 9, "bold"))
        self.chat_history.tag_configure("sophia_text", foreground="#edf2f7")
        self.chat_history.tag_configure("user_name", foreground="#f6ad55", font=("Segoe UI", 9, "bold"))
        self.chat_history.tag_configure("user_text", foreground="#cbd5e0")
        self.chat_history.tag_configure("system_note", foreground="#a0aec0", font=("Segoe UI", 8, "italic"))

        # Barra inferior de entrada
        input_frame = tk.Frame(self.root, bg="#161a29", padx=8, pady=8)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.entry_message = tk.Entry(
            input_frame,
            bg="#0f111a",
            fg="#f7fafc",
            insertbackground="#00f0ff",
            bd=0,
            relief=tk.FLAT,
            font=("Segoe UI", 10),
        )
        self.entry_message.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 6))
        self.entry_message.bind("<Return>", lambda e: self._send_message())

        btn_send = tk.Button(
            input_frame,
            text="➤",
            command=self._send_message,
            bg="#00f0ff",
            fg="#0f111a",
            activebackground="#38bdf8",
            activeforeground="#0f111a",
            font=("Segoe UI", 10, "bold"),
            bd=0,
            padx=12,
            cursor="hand2",
        )
        btn_send.pack(side=tk.RIGHT)

    def _setup_events(self) -> None:
        """Permite arrastrar la ventana manteniendo presionado el ratón en la barra de título."""
        self.title_bar.bind("<ButtonPress-1>", self._start_drag)
        self.title_bar.bind("<B1-Motion>", self._do_drag)

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_drag(self, event: tk.Event) -> None:
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        new_x = self.root.winfo_x() + dx
        new_y = self.root.winfo_y() + dy
        self.root.geometry(f"+{new_x}+{new_y}")

    def _toggle_always_on_top(self) -> None:
        self._is_always_on_top = not self._is_always_on_top
        self.root.wm_attributes("-topmost", self._is_always_on_top)
        self.btn_pin.configure(fg="#00f0ff" if self._is_always_on_top else "#718096")

    def _update_avatar(self, expression: str) -> None:
        """Cambia el sprite de expresión de Sophia."""
        if expression in self._cached_images:
            self._current_expression = expression
            self.avatar_label.configure(image=self._cached_images[expression])

    def _on_avatar_click(self) -> None:
        """Reacción simpática al hacer clic sobre Sophia."""
        self._update_avatar("laugh")
        self._add_sophia_message("¡Aquí estoy! Lista para ayudarte a codear.", "laugh")

    def _add_user_message(self, text: str) -> None:
        self.chat_history.configure(state=tk.NORMAL)
        self.chat_history.insert(tk.END, "Vos: ", "user_name")
        self.chat_history.insert(tk.END, f"{text}\n\n", "user_text")
        self.chat_history.see(tk.END)
        self.chat_history.configure(state=tk.DISABLED)

    def _add_sophia_message(self, text: str, expression: str = "calm") -> None:
        self._update_avatar(expression)
        self.chat_history.configure(state=tk.NORMAL)
        self.chat_history.insert(tk.END, "Sophia: ", "sophia_name")
        self.chat_history.insert(tk.END, f"{text}\n\n", "sophia_text")
        self.chat_history.see(tk.END)
        self.chat_history.configure(state=tk.DISABLED)

    def _send_message(self) -> None:
        user_text = self.entry_message.get().strip()
        if not user_text:
            return

        self.entry_message.delete(0, tk.END)
        self._add_user_message(user_text)

        # Mostrar estado de procesamiento y cara de atención
        self.status_label.configure(text="🤔 Pensando...", fg="#f6ad55")
        self._update_avatar("look")

        # Ejecutar la inferencia en segundo plano para no congelar la ventana
        thread = threading.Thread(target=self._process_reply, args=(user_text,), daemon=True)
        thread.start()

    def _process_reply(self, user_text: str) -> None:
        """Procesa la respuesta con Gemini o con el motor local si no hay clave."""
        context_notes = ""
        # Buscar en apuntes locales de Python para enriquecer la respuesta
        matches = self.knowledge.execute(user_text)
        if matches:
            top = matches[0]
            context_notes = f"Tema: {top.title}\n{top.summary}\n{top.content[:600]}"

        if self.gemini.is_configured:
            history = self.memory.history()
            reply, expr = self.gemini.generate_reply(
                user_text, history=history, context_notes=context_notes
            )
        else:
            # Fallback a motor local si no configuró Gemini en .env
            if matches:
                top = matches[0]
                reply = (
                    f"Encontré «{top.title}» en tus apuntes:\n{top.summary}\n\n"
                    f"(Tip: Agregá tu GEMINI_API_KEY en .env para que pueda explicarte todo libremente)."
                )
                expr = "smug"
            else:
                try:
                    local_reply = self.local_use_case.respond(user_text)
                    reply = local_reply.text
                    expr = "calm"
                except Exception:
                    reply = "¿Qué tema de Python querés revisar hoy?"
                    expr = "calm"

        # Guardar en memoria local
        try:
            self.memory.save(
                CheckIn(
                    text=user_text,
                    mood=Mood.CALM,
                    topic=Topic.PROGRAMMING,
                    created_at=self.clock.now(),
                    reply=reply,
                )
            )
        except Exception:
            pass

        # Actualizar la interfaz en el hilo principal
        self.root.after(0, self._render_reply, reply, expr)

    def _render_reply(self, reply: str, expr: str) -> None:
        self.status_label.configure(text="🟢 Conectada", fg="#68d391")
        self._add_sophia_message(reply, expr)

    def run(self) -> None:
        """Inicia el bucle de la aplicación de escritorio."""
        self.root.mainloop()


def start_desktop() -> None:
    """Lanza la aplicación de escritorio de Sophia."""
    project_root = Path(__file__).resolve().parents[2]
    memory = JsonMemoryRepository(project_root / "data" / "memoria.json")
    knowledge = SearchKnowledgeUseCase(
        project_root / "companera" / "python context"  # MarkdownKnowledgeBase
    )
    from companera.infrastructure.keyword_text_analyzer import KeywordTextAnalyzer
    from companera.infrastructure.markdown_knowledge_base import MarkdownKnowledgeBase

    kb = MarkdownKnowledgeBase(project_root / "companera" / "python context")
    knowledge = SearchKnowledgeUseCase(kb)
    clock = SystemClock()
    gemini = GeminiService(project_root=project_root)
    local_use_case = CheckInUseCase(memory, KeywordTextAnalyzer(), clock)

    app = SophiaDesktopApp(
        memory=memory,
        knowledge=knowledge,
        gemini=gemini,
        local_use_case=local_use_case,
        clock=clock,
    )
    app.run()


if __name__ == "__main__":
    start_desktop()
