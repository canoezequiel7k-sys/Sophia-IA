import threading
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk

from companera.domain.models import CheckIn, Mood, Topic
from companera.infrastructure.gemini_service import GeminiService
from companera.infrastructure.json_memory_repository import JsonMemoryRepository
from companera.infrastructure.system_clock import SystemClock


class SophiaDesktopApp:
    """Ventana interactiva de escritorio para Sophia en segundo monitor."""

    def __init__(
        self,
        memory: JsonMemoryRepository,
        gemini: GeminiService,
        clock: SystemClock,
    ):
        self.memory = memory
        self.gemini = gemini
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
        self._animation_after_id: str | None = None
        self._talking_after_id: str | None = None
        self._animation_frames: list[str] = []
        self._animation_index = 0
        self._send_lock = threading.Lock()

        self._load_sprites()
        self._build_ui()
        self._setup_events()

        # Mensaje de bienvenida inicial
        self._add_sophia_message(
            "¡Hola! Ya estoy acá contigo. Podés arrastrarme por la barra superior "
            "y conversar conmigo de cualquier tema.",
            "calm",
        )

    def _load_sprites(self) -> None:
        """Carga los sprites de expresión y las imágenes de transición."""
        target_size = (160, 160)
        expressions = ["calm", "laugh", "smug", "look", "aside", "wide", "many"]
        cutins = ["eyes", "grin", "laugh", "look", "many"]

        for expr in expressions:
            img_file = self.assets_dir / f"face-{expr}.png"
            if img_file.exists():
                try:
                    pil_img = Image.open(img_file).convert("RGBA")
                    pil_img = pil_img.resize(target_size, Image.Resampling.LANCZOS)
                    self._cached_images[f"face-{expr}"] = ImageTk.PhotoImage(pil_img)
                except Exception:
                    pass

        for cutin in cutins:
            img_file = self.assets_dir / f"cutin-{cutin}.png"
            if img_file.exists():
                try:
                    pil_img = Image.open(img_file).convert("RGBA")
                    pil_img = pil_img.resize(target_size, Image.Resampling.LANCZOS)
                    self._cached_images[f"cutin-{cutin}"] = ImageTk.PhotoImage(pil_img)
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
        """Cambia el sprite de expresión o de transición de Sophia."""
        image_key = expression if expression in self._cached_images else f"face-{expression}"
        if image_key in self._cached_images:
            self._current_expression = expression.replace("face-", "")
            self.avatar_label.configure(image=self._cached_images[image_key])

    def _stop_animation(self) -> None:
        if self._animation_after_id is not None:
            self.root.after_cancel(self._animation_after_id)
            self._animation_after_id = None
        if self._talking_after_id is not None:
            self.root.after_cancel(self._talking_after_id)
            self._talking_after_id = None
        self._animation_frames = []
        self._animation_index = 0

    def _start_animation(self, frames: list[str], interval_ms: int = 280) -> None:
        """Recorre cutins y expresiones mientras Sophia piensa o habla."""
        self._stop_animation()
        available = [frame for frame in frames if frame in self._cached_images]
        if not available:
            return
        self._animation_frames = available
        self._play_animation_frame(interval_ms)

    def _play_animation_frame(self, interval_ms: int) -> None:
        if not self._animation_frames:
            return
        frame = self._animation_frames[self._animation_index % len(self._animation_frames)]
        self._update_avatar(frame)
        self._animation_index += 1
        self._animation_after_id = self.root.after(interval_ms, self._play_animation_frame, interval_ms)

    def _start_thinking_animation(self) -> None:
        self._start_animation([
            "cutin-eyes", "cutin-grin", "cutin-look", "cutin-many",
            "face-look", "face-aside", "face-calm",
        ], 240)

    def _start_talking_animation(self, final_expression: str, duration_ms: int) -> None:
        frames = [
            "cutin-eyes", "cutin-grin", "cutin-laugh", "cutin-look", "cutin-many",
            f"face-{final_expression}", "face-calm", "face-laugh",
        ]
        self._start_animation(frames, 260)
        self._talking_after_id = self.root.after(
            duration_ms,
            self._finish_talking_animation,
            final_expression,
        )

    def _finish_talking_animation(self, final_expression: str) -> None:
        self._talking_after_id = None
        self._stop_animation()
        self._update_avatar(final_expression)
        self.status_label.configure(text="🟢 Conectada", fg="#68d391")

    def _on_avatar_click(self) -> None:
        """Reacción simpática al hacer clic sobre Sophia."""
        self._stop_animation()
        self._update_avatar("laugh")
        self._add_sophia_message("¡Acá estoy! ¿En qué puedo acompañarte ahora?", "laugh")

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
        if not user_text or not self._send_lock.acquire(blocking=False):
            return

        self.entry_message.delete(0, tk.END)
        self._add_user_message(user_text)

        self.status_label.configure(text="🤔 Pensando...", fg="#f6ad55")
        self._start_thinking_animation()

        thread = threading.Thread(target=self._process_reply, args=(user_text,), daemon=True)
        thread.start()

    def _process_reply(self, user_text: str) -> None:
        """Obtiene una respuesta sin congelar la interfaz."""
        try:
            if self.gemini.is_configured:
                history = self.memory.history()
                reply, expr = self.gemini.generate_reply(user_text, history=history)
            else:
                reply = (
                    "Todavía necesito configurar `GEMINI_API_KEY` en el archivo `.env` "
                    "para poder conversar por el modelo."
                )
                expr = "aside"
        except Exception as error:
            reply = f"Tuve un problema técnico al generar la respuesta: {error}"
            expr = "many"

        try:
            self.memory.save(
                CheckIn(
                    text=user_text,
                    mood=Mood.CALM,
                    topic=Topic.GENERAL,
                    created_at=self.clock.now(),
                    reply=reply,
                )
            )
        except Exception:
            pass

        self.root.after(0, self._render_reply, reply, expr)

    def _render_reply(self, reply: str, expr: str) -> None:
        self.status_label.configure(text="💬 Hablando...", fg="#00f0ff")
        duration_ms = max(1800, min(6500, len(reply) * 38))
        self._add_sophia_message(reply, expr)
        self._start_talking_animation(expr, duration_ms)
        self._send_lock.release()

    def run(self) -> None:
        """Inicia el bucle de la aplicación de escritorio."""
        self.root.mainloop()


def start_desktop() -> None:
    """Lanza la aplicación de escritorio de Sophia."""
    project_root = Path(__file__).resolve().parents[2]
    memory = JsonMemoryRepository(project_root / "data" / "memoria.json")
    clock = SystemClock()
    gemini = GeminiService(project_root=project_root)

    app = SophiaDesktopApp(
        memory=memory,
        gemini=gemini,
        clock=clock,
    )
    app.run()


if __name__ == "__main__":
    start_desktop()
