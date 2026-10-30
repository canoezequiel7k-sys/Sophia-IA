import threading
import tkinter as tk
from pathlib import Path
from typing import Optional

from PIL import Image, ImageTk

from companera.domain.models import CheckIn, Mood, Topic
from companera.infrastructure.gemini_service import GeminiService
from companera.infrastructure.json_memory_repository import JsonMemoryRepository
from companera.infrastructure.system_clock import SystemClock
from companera.infrastructure.sound_effects import SoundEffectService
from companera.infrastructure.voice_service import VoiceService

# Cuántos ms dura la animación de "hablando" por carácter de respuesta
_MS_PER_CHAR = 38
_MIN_TALK_MS = 1800
_MAX_TALK_MS = 7000

# Orden de los frames para pensar y hablar
_THINKING_FRAMES = [
    "cutin-eyes", "cutin-look", "cutin-many",
    "face-look", "face-aside",
]
_TALKING_BASE_FRAMES = [
    "cutin-eyes", "cutin-grin", "cutin-laugh", "cutin-look", "cutin-many",
]


class SophiaDesktopApp:
    """Ventana interactiva de escritorio para Sophia."""

    def __init__(
        self,
        memory: JsonMemoryRepository,
        gemini: GeminiService,
        clock: SystemClock,
        voice: Optional[VoiceService] = None,
        sound: Optional[SoundEffectService] = None,
    ) -> None:
        self._memory = memory
        self._gemini = gemini
        self._clock = clock
        self._voice = voice
        self._sound = sound

        self._assets = Path(__file__).resolve().parents[2] / "companera" / "assets" / "sophia"

        self._root = tk.Tk()
        self._root.title("Sophia")
        self._root.geometry("380x600")
        self._root.minsize(340, 500)
        self._root.configure(bg="#0f111a")

        self._drag = {"x": 0, "y": 0}
        self._pinned = False
        self._sprites: dict[str, ImageTk.PhotoImage] = {}
        self._current_expr = "calm"

        # Estado de animación
        self._anim_id: str | None = None
        self._anim_frames: list[str] = []
        self._anim_index = 0
        self._talk_id: str | None = None

        # Evita enviar mientras ya se está procesando
        self._busy = threading.Lock()

        self._load_sprites()
        self._build_ui()
        self._setup_drag()

        self._welcome()

    # ------------------------------------------------------------------ sprites

    def _load_sprites(self) -> None:
        """Carga y escala todos los sprites disponibles."""
        size = (160, 160)
        for name in [
            "face-calm", "face-laugh", "face-smug", "face-look",
            "face-aside", "face-wide", "face-many",
            "cutin-eyes", "cutin-grin", "cutin-laugh", "cutin-look", "cutin-many",
        ]:
            path = self._assets / f"{name}.png"
            if path.exists():
                try:
                    img = Image.open(path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
                    self._sprites[name] = ImageTk.PhotoImage(img)
                except Exception:
                    pass

    def _show_sprite(self, key: str) -> None:
        """Muestra un sprite dado su clave (ej. 'face-calm' o 'cutin-eyes')."""
        if key in self._sprites:
            self._avatar.configure(image=self._sprites[key])

    # ------------------------------------------------------------------ animaciones

    def _stop_anim(self) -> None:
        if self._anim_id:
            self._root.after_cancel(self._anim_id)
            self._anim_id = None
        if self._talk_id:
            self._root.after_cancel(self._talk_id)
            self._talk_id = None
        self._anim_frames = []
        self._anim_index = 0

    def _play_frame(self, interval: int) -> None:
        if not self._anim_frames:
            return
        frame = self._anim_frames[self._anim_index % len(self._anim_frames)]
        self._show_sprite(frame)
        self._anim_index += 1
        self._anim_id = self._root.after(interval, self._play_frame, interval)

    def _start_anim(self, frames: list[str], interval: int = 260) -> None:
        self._stop_anim()
        available = [f for f in frames if f in self._sprites]
        if not available:
            return
        self._anim_frames = available
        self._play_frame(interval)

    def _thinking_anim(self) -> None:
        self._start_anim(_THINKING_FRAMES, 250)

    def _talking_anim(self, expr: str, duration_ms: int) -> None:
        face = f"face-{expr}" if f"face-{expr}" in self._sprites else "face-calm"
        frames = _TALKING_BASE_FRAMES + [face, "face-calm"]
        self._start_anim(frames, 240)
        self._talk_id = self._root.after(duration_ms, self._finish_talking, expr)

    def _finish_talking(self, expr: str) -> None:
        self._talk_id = None
        self._stop_anim()
        self._show_sprite(f"face-{expr}" if f"face-{expr}" in self._sprites else "face-calm")
        self._status("🟢 Conectada", "#68d391")

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        # Barra de título
        bar = tk.Frame(self._root, bg="#161a29", height=32)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        self._title_bar = bar

        tk.Label(bar, text="✦ SOPHIA", fg="#00f0ff", bg="#161a29",
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=10)

        tk.Button(bar, text="✕", command=self._root.destroy,
                  fg="#a0aec0", bg="#161a29", activeforeground="#ff5555",
                  activebackground="#161a29", bd=0, padx=8,
                  font=("Segoe UI", 9), cursor="hand2").pack(side=tk.RIGHT)

        self._pin_btn = tk.Button(
            bar, text="📌", command=self._toggle_pin,
            fg="#718096", bg="#161a29", activeforeground="#00f0ff",
            activebackground="#161a29", bd=0, padx=6,
            font=("Segoe UI", 9), cursor="hand2",
        )
        self._pin_btn.pack(side=tk.RIGHT)

        # Avatar
        avatar_frame = tk.Frame(self._root, bg="#0f111a", pady=8)
        avatar_frame.pack(fill=tk.X)

        self._avatar = tk.Label(avatar_frame, bg="#0f111a", cursor="hand2")
        self._avatar.pack()
        self._show_sprite("face-calm")
        self._avatar.bind("<Button-1>", lambda _: self._on_avatar_click())

        self._status_lbl = tk.Label(avatar_frame, text="🟢 Conectada",
                                    fg="#68d391", bg="#0f111a", font=("Segoe UI", 8))
        self._status_lbl.pack(pady=(4, 0))

        # Chat
        chat_wrap = tk.Frame(self._root, bg="#0f111a", padx=12, pady=4)
        chat_wrap.pack(fill=tk.BOTH, expand=True)

        self._chat = tk.Text(
            chat_wrap, bg="#161a29", fg="#e2e8f0",
            insertbackground="#00f0ff", selectbackground="#2d3748",
            wrap=tk.WORD, bd=0, padx=10, pady=10, font=("Segoe UI", 9),
        )
        self._chat.pack(fill=tk.BOTH, expand=True)
        self._chat.configure(state=tk.DISABLED)
        self._chat.tag_configure("sophia_name", foreground="#00f0ff", font=("Segoe UI", 9, "bold"))
        self._chat.tag_configure("sophia_text", foreground="#edf2f7")
        self._chat.tag_configure("user_name", foreground="#f6ad55", font=("Segoe UI", 9, "bold"))
        self._chat.tag_configure("user_text", foreground="#cbd5e0")

        # Entrada
        input_bar = tk.Frame(self._root, bg="#161a29", padx=8, pady=8)
        input_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self._entry = tk.Entry(
            input_bar, bg="#0f111a", fg="#f7fafc",
            insertbackground="#00f0ff", bd=0, relief=tk.FLAT, font=("Segoe UI", 10),
        )
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 6))
        self._entry.bind("<Return>", lambda _: self._send())

        tk.Button(
            input_bar, text="➤", command=self._send,
            bg="#00f0ff", fg="#0f111a", activebackground="#38bdf8",
            activeforeground="#0f111a", font=("Segoe UI", 10, "bold"),
            bd=0, padx=12, cursor="hand2",
        ).pack(side=tk.RIGHT)

    # ------------------------------------------------------------------ drag

    def _setup_drag(self) -> None:
        self._title_bar.bind("<ButtonPress-1>", lambda e: self._drag.update(x=e.x, y=e.y))
        self._title_bar.bind("<B1-Motion>", self._do_drag)

    def _do_drag(self, event: tk.Event) -> None:
        x = self._root.winfo_x() + event.x - self._drag["x"]
        y = self._root.winfo_y() + event.y - self._drag["y"]
        self._root.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------ helpers

    def _status(self, text: str, color: str) -> None:
        self._status_lbl.configure(text=text, fg=color)

    def _toggle_pin(self) -> None:
        self._pinned = not self._pinned
        self._root.wm_attributes("-topmost", self._pinned)
        self._pin_btn.configure(fg="#00f0ff" if self._pinned else "#718096")

    def _append_user(self, text: str) -> None:
        self._chat.configure(state=tk.NORMAL)
        self._chat.insert(tk.END, "Vos: ", "user_name")
        self._chat.insert(tk.END, f"{text}\n\n", "user_text")
        self._chat.see(tk.END)
        self._chat.configure(state=tk.DISABLED)

    def _append_sophia(self, text: str, expr: str = "calm") -> None:
        self._show_sprite(f"face-{expr}" if f"face-{expr}" in self._sprites else "face-calm")
        self._chat.configure(state=tk.NORMAL)
        self._chat.insert(tk.END, "Sophia: ", "sophia_name")
        self._chat.insert(tk.END, f"{text}\n\n", "sophia_text")
        self._chat.see(tk.END)
        self._chat.configure(state=tk.DISABLED)

    def _on_avatar_click(self) -> None:
        self._stop_anim()
        self._show_sprite("face-laugh")
        self._append_sophia("¡Acá estoy! ¿En qué andamos?", "laugh")

    def _welcome(self) -> None:
        self._append_sophia(
            "¡Hola! Ya estoy acá, lista para acompañarte. "
            "Podés hablarme de lo que sea, o arrastrarme a tu segundo monitor con la barra de arriba.",
            "calm",
        )
        if self._voice is not None:
            self._voice.speak(
                "¡Hola! Ya estoy acá, lista para acompañarte."
            )
        if self._sound is not None:
            self._sound.play("hello")

    # ------------------------------------------------------------------ mensajería

    def _send(self) -> None:
        text = self._entry.get().strip()
        if not text or not self._busy.acquire(blocking=False):
            return
        if self._voice is not None:
            self._voice.stop()
        if self._sound is not None:
            self._sound.stop()
            self._sound.play("thinking")
        self._entry.delete(0, tk.END)
        self._append_user(text)
        self._status("🤔 Pensando...", "#f6ad55")
        self._thinking_anim()
        threading.Thread(target=self._process, args=(text,), daemon=True).start()

    def _process(self, user_text: str) -> None:
        """Llama a Gemini en segundo plano y agenda la actualización en el hilo de UI."""
        try:
            history = self._memory.history()
            reply, expr = self._gemini.generate_reply(user_text, history=history)
        except Exception as err:
            reply, expr = f"Ups, algo salió mal: {err}", "many"

        try:
            self._memory.save(CheckIn(
                text=user_text,
                mood=Mood.CALM,
                topic=Topic.GENERAL,
                created_at=self._clock.now(),
                reply=reply,
            ))
        except Exception:
            pass

        self._root.after(0, self._render, reply, expr)

    def _render(self, reply: str, expr: str) -> None:
        """Muestra la respuesta y arranca la animación de 'hablando'."""
        self._append_sophia(reply, expr)
        if self._voice is not None:
            self._voice.speak(reply)
        if self._sound is not None:
            self._sound.play("blip")
        duration = max(_MIN_TALK_MS, min(_MAX_TALK_MS, len(reply) * _MS_PER_CHAR))
        self._status("💬 Hablando...", "#00f0ff")
        self._talking_anim(expr, duration)
        self._busy.release()

    # ------------------------------------------------------------------ run

    def run(self) -> None:
        self._root.mainloop()


def start_desktop() -> None:
    """Construye y lanza la aplicación de escritorio de Sophia."""
    project_root = Path(__file__).resolve().parents[2]
    app = SophiaDesktopApp(
        memory=JsonMemoryRepository(project_root / "data" / "memoria.json"),
        gemini=GeminiService(project_root=project_root),
        clock=SystemClock(),
        voice=VoiceService(),
        sound=SoundEffectService(),
    )
    app.run()


if __name__ == "__main__":
    start_desktop()
