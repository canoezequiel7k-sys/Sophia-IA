import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from typing import Optional

from PIL import Image, ImageTk

from companera.application.commands import handle_command
from companera.domain.models import CheckIn, Mood, Reply, Topic
from companera.infrastructure.settings import Settings
from companera.infrastructure.gemini_service import GeminiService
from companera.infrastructure.json_memory_repository import JsonMemoryRepository
from companera.infrastructure.system_clock import SystemClock
from companera.infrastructure.sound_effects import SoundEffectService
from companera.infrastructure.voice_service import VoiceService

# Cuántos ms dura la animación de "hablando" por carácter de respuesta
_MS_PER_CHAR = 38
_MIN_TALK_MS = 1800
_MAX_TALK_MS = 7000

logger = logging.getLogger("sophia.ui")

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
        settings: Settings | None = None,
    ) -> None:
        self._memory = memory
        self._gemini = gemini
        self._clock = clock
        self._voice = voice
        self._sound = sound
        self._settings = settings or Settings()
        self._closing = False
        self._events: queue.Queue[tuple[str, object]] = queue.Queue()

        self._assets = Path(__file__).resolve().parents[2] / "companera" / "assets" / "sophia"

        self._root = tk.Tk()
        self._root.title("Sophia")
        self._root.geometry("380x600")
        self._root.minsize(340, 500)
        self._root.configure(bg="#0f111a")
        icon = self._assets / "capri.ico"
        if icon.exists():
            try:
                self._root.iconbitmap(str(icon))
            except tk.TclError:
                logger.exception("No se pudo cargar el ícono de Sophia")

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
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_events()

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
                    logger.exception("No se pudo cargar un sprite de Sophia")

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
        self._avatar.bind("<Button-3>", lambda event: self._avatar_menu(event))

        connected = getattr(self._gemini, "is_configured", False)
        self._status_lbl = tk.Label(
            avatar_frame,
            text="🟢 Conectada" if connected else "⚠️ Sin clave",
            fg="#68d391" if connected else "#f6ad55",
            bg="#0f111a", font=("Segoe UI", 8),
        )
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
        self._chat.tag_configure("error_text", foreground="#fc8181")
        self._chat.bind("<Button-3>", lambda event: self._chat.event_generate("<<Copy>>"))

        # Entrada
        input_bar = tk.Frame(self._root, bg="#161a29", padx=8, pady=8)
        input_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self._entry = tk.Entry(
            input_bar, bg="#0f111a", fg="#f7fafc",
            insertbackground="#00f0ff", bd=0, relief=tk.FLAT, font=("Segoe UI", 10),
        )
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 6))
        self._entry.bind("<Return>", lambda _: self._send())

        controls = tk.Frame(input_bar, bg="#161a29")
        controls.pack(side=tk.RIGHT, padx=(0, 4))
        tk.Button(controls, text="🔊" if self._settings.voice_enabled else "🔇", width=2,
                  command=self._toggle_voice, bg="#161a29", fg="#e2e8f0", bd=0).pack(side=tk.LEFT)
        tk.Button(controls, text="🔔" if self._settings.sfx_enabled else "🔕", width=2,
                  command=self._toggle_sfx, bg="#161a29", fg="#e2e8f0", bd=0).pack(side=tk.LEFT)
        tk.Button(controls, text="⏹", width=2,
                  command=self._stop_speech, bg="#161a29", fg="#e2e8f0", bd=0).pack(side=tk.LEFT)

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

    def _save_settings(self) -> None:
        root = Path(__file__).resolve().parents[2]
        try:
            self._settings.save(root / "data" / "settings.json")
        except Exception:
            logger.exception("No se pudo guardar la configuración de audio")

    def _avatar_menu(self, event: tk.Event) -> None:
        menu = tk.Menu(self._root, tearoff=0)
        menu.add_command(label="Mute voz", command=self._toggle_voice)
        menu.add_command(label="Modo mascota/chat", command=self._toggle_pet_mode)
        menu.add_command(label="Salir", command=self._on_close)
        menu.tk_popup(event.x_root, event.y_root)

    def _toggle_pet_mode(self) -> None:
        self._settings.pet_mode = not self._settings.pet_mode
        try:
            if self._settings.pet_mode and getattr(self._root, "overrideredirect", None):
                self._root.overrideredirect(True)
                if hasattr(self._root, "winfo_screenwidth"):
                    self._root.geometry("220x220")
                self._root.attributes("-transparentcolor", "#0f111a") if hasattr(self._root, "attributes") else None
            else:
                self._root.overrideredirect(False)
                self._root.geometry("380x600")
            self._save_settings()
        except tk.TclError:
            logger.exception("No se pudo cambiar el modo mascota")

    def _toggle_voice(self) -> None:
        self._settings.voice_enabled = not self._settings.voice_enabled
        if not self._settings.voice_enabled and self._voice is not None:
            self._voice.stop()
        self._save_settings()

    def _toggle_sfx(self) -> None:
        self._settings.sfx_enabled = not self._settings.sfx_enabled
        if not self._settings.sfx_enabled and self._sound is not None:
            self._sound.stop()
        self._save_settings()

    def _stop_speech(self) -> None:
        if self._voice is not None:
            self._voice.stop()
        if self._sound is not None:
            self._sound.stop()
        self._stop_anim()
        if getattr(self._gemini, "is_configured", False):
            self._status("🟢 Conectada", "#68d391")
        else:
            self._status("⚠️ Sin clave", "#f6ad55")

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

    def _append_sophia(self, text: str, expr: str = "calm", error: bool = False) -> None:
        self._show_sprite(f"face-{expr}" if f"face-{expr}" in self._sprites else "face-calm")
        self._chat.configure(state=tk.NORMAL)
        self._chat.insert(tk.END, "Sophia: ", "sophia_name")
        self._chat.insert(tk.END, f"{text}\n\n", "error_text" if error else "sophia_text")
        self._chat.see(tk.END)
        self._chat.configure(state=tk.DISABLED)

    def _on_avatar_click(self) -> None:
        if self._closing:
            return
        self._stop_anim()
        self._show_sprite("face-laugh")
        message = "¡Acá estoy! ¿En qué andamos?"
        self._append_sophia(message, "laugh")
        if self._voice is not None and self._settings.voice_enabled:
            self._voice.speak(message)
        if self._sound is not None and self._settings.sfx_enabled:
            self._sound.play("hello")

    def _play_intro(self) -> None:
        if not self._settings.show_intro:
            return
        order = [
            "intro-wave1", "intro-wave2", "intro-wave3",
            "intro-mouth1", "intro-mouth2", "intro-mouth3",
            "intro-grab", "intro-smear", "intro-happy",
        ]
        intro = []
        for name in order:
            path = self._assets / f"{name}.webp"
            if not path.exists():
                continue
            try:
                frame = Image.open(path).convert("RGBA")
                if getattr(frame, "n_frames", 1) != 1:
                    frame.seek(0)
                frame.thumbnail((160, 160), Image.Resampling.LANCZOS)
                intro.append(ImageTk.PhotoImage(frame))
            except Exception:
                logger.exception("No se pudo cargar un frame de intro")
        if not intro:
            return
        index = 0
        def advance() -> None:
            nonlocal index
            if self._closing or index >= len(intro):
                self._show_sprite("face-calm")
                return
            self._avatar.configure(image=intro[index])
            index += 1
            self._root.after(220, advance)
        advance()

    def _welcome(self) -> None:
        self._play_intro()
        self._append_sophia(
            "¡Hola! Ya estoy acá, lista para acompañarte. "
            "Podés hablarme de lo que sea, o arrastrarme a tu segundo monitor con la barra de arriba.",
            "calm",
        )
        if self._settings.speak_welcome and self._voice is not None and self._settings.voice_enabled:
            self._voice.speak("¡Hola! Ya estoy acá, lista para acompañarte.")
        if self._settings.speak_welcome and self._sound is not None and self._settings.sfx_enabled:
            self._sound.play("hello")

    # ------------------------------------------------------------------ mensajería

    def _send(self) -> None:
        text = self._entry.get().strip()
        if self._closing or not text or not self._busy.acquire(blocking=False):
            return
        command_result = handle_command(text, self._memory)
        if command_result is not None:
            self._entry.delete(0, tk.END)
            self._append_user(text)
            if text.strip().lower() in ("/mute", "/callate"):
                self._settings.voice_enabled = False
            self._append_sophia(command_result, "calm")
            self._busy.release()
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
        """Llama a Gemini en segundo plano y envía el resultado por la cola."""
        try:
            history = self._memory.history()
            reply = self._gemini.generate_reply(user_text, history=history)
        except Exception as err:
            logger.exception("Falló el procesamiento del mensaje")
            reply = Reply(f"Ups, algo salió mal: {err}", "many", False, "network")

        if reply.ok:
            try:
                self._memory.save(CheckIn(
                    text=user_text,
                    mood=reply.mood or Mood.CALM,
                    topic=reply.topic or Topic.GENERAL,
                    created_at=self._clock.now(),
                    reply=reply.text,
                ))
            except Exception:
                logger.exception("No se pudo guardar el intercambio")
        if not self._closing:
            self._events.put(("reply", reply))

    def _render(self, reply: Reply) -> None:
        """Muestra la respuesta con desbloqueo garantizado."""
        try:
            self._append_sophia(reply.text, reply.expression if reply.ok else "many", error=not reply.ok)
            if reply.ok:
                if self._voice is not None and self._settings.voice_enabled:
                    self._voice.speak(reply.text)
                if self._sound is not None and self._settings.sfx_enabled:
                    self._sound.play("blip")
                duration = max(_MIN_TALK_MS, min(_MAX_TALK_MS, len(reply.text) * _MS_PER_CHAR))
                self._status("💬 Hablando...", "#00f0ff")
                self._talking_anim(reply.expression, duration)
            else:
                if self._sound is not None and self._settings.sfx_enabled:
                    self._sound.play("error")
                self._status("⚠️ Error", "#fc8181")
        finally:
            self._busy.release()

    def _poll_events(self) -> None:
        if self._closing:
            return
        try:
            while True:
                kind, payload = self._events.get_nowait()
                if kind == "reply" and isinstance(payload, Reply):
                    self._render(payload)
        except queue.Empty:
            logger.debug("No hay eventos pendientes")
        if not self._closing:
            try:
                self._root.after(50, self._poll_events)
            except tk.TclError:
                logger.exception("La ventana se cerró mientras llegaba una respuesta")

    def _on_close(self) -> None:
        self._closing = True
        self._stop_anim()
        if self._voice is not None:
            self._voice.stop()
        if self._sound is not None:
            self._sound.stop()
        try:
            self._root.destroy()
        except tk.TclError:
            logger.exception("Tcl falló durante el cierre seguro")

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
