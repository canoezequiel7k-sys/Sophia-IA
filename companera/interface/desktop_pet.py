import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from typing import Optional

from PIL import Image, ImageTk

from companera.application.commands import handle_command
from companera.application.chat_service import ChatService
from companera.interface.tray import SophiaTray
from companera.interface.pet_window import PetWindow
from companera.interface.speech_bubble import SpeechBubble
from companera.interface.pointer_overlay import PointerOverlay
from companera.interface.avatar_animator import AvatarAnimator
from companera.interface.terminal_window import TerminalWindow
from companera.interface.terminal_view import TerminalView
from companera.interface.command_palette import CommandPalette, PaletteAction
from companera.interface.screen_metrics import Rect
from companera.interface.intro_sequence import load_intro_frames, INTRO_SEQUENCE
from companera.infrastructure.screen_targets import resolve_target
from companera.infrastructure.screen_capture import capture_screen_png
from companera.domain.models import Reply
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
        self._root.geometry("520x760")
        self._root.minsize(440, 620)
        self._root.configure(bg="#0f111a")
        icon = self._assets / "capri.ico"
        if icon.exists():
            try:
                self._root.iconbitmap(str(icon))
            except tk.TclError:
                logger.exception("No se pudo cargar el ícono de Sophia")

        self._drag = {"x": 0, "y": 0}
        self._avatar_press = {"x_root": 0, "y_root": 0, "moved": False}
        self._chat_service = ChatService(self._memory, self._clock, self._gemini)
        self._tray: SophiaTray | None = None
        self._pinned = False
        self._sprites: dict[str, ImageTk.PhotoImage] = {}
        self._portraits: dict[str, ImageTk.PhotoImage] = {}
        self._current_expr = "calm"

        # Estado de animación
        self._anim_id: str | None = None
        self._anim_frames: list[str] = []
        self._anim_index = 0
        self._talk_id: str | None = None
        self._rest_anim = AvatarAnimator(self._settings.rest_animation)
        self._rest_anim_id: str | None = None

        # Evita enviar mientras ya se está procesando
        self._busy = threading.Lock()

        self._pet_bubble: tk.Toplevel | None = None
        self._pet_window: PetWindow | None = None
        self._speech_bubble = SpeechBubble(self._root)
        self._pointer_overlay = PointerOverlay(self._root)
        self._pet_chat = TerminalWindow(self._root, self._send_pet_text, self._settings,
                                        on_palette=lambda: self._open_main_palette())
        self._palette: CommandPalette | None = None
        self._load_sprites()
        self._build_ui()
        self._setup_drag()
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_events()
        if self._settings.minimize_to_tray:
            self._tray = SophiaTray(self._events, Path(__file__).resolve().parents[2])
            self._tray.start()
        if self._settings.pet_mode:
            self._toggle_pet_mode(force=True)

        self._welcome()

    # ------------------------------------------------------------------ sprites

    def _load_sprites(self) -> None:
        """Carga y escala todos los sprites disponibles."""
        size = (200, 200)
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
                if name.startswith("face-"):
                    portrait = Image.open(path).convert("RGBA")
                    portrait.thumbnail((54, 54), Image.Resampling.LANCZOS)
                    self._portraits[name] = ImageTk.PhotoImage(portrait)
        cutout_path = self._assets / "capri-cutout.png"
        if cutout_path.exists():
            try:
                img = Image.open(cutout_path).convert("RGBA")
                img.thumbnail((360, 360), Image.Resampling.LANCZOS)
                self._sprites["pet-capri"] = ImageTk.PhotoImage(img)
            except Exception:
                logger.exception("No se pudo cargar el personaje flotante")

    def _show_sprite(self, key: str) -> None:
        """Muestra un sprite dado su clave (ej. 'face-calm' o 'cutin-eyes')."""
        if key in self._sprites:
            self._avatar.configure(image=self._sprites[key])
            # La mascota flotante mantiene siempre el recorte capri-cutout.

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
        if self._pet_window is not None:
            self._pet_window.set_state("thinking")

    def _talking_anim(self, expr: str, duration_ms: int) -> None:
        if self._pet_window is not None:
            self._pet_window.set_state("talking")
        self._talk_id = self._root.after(duration_ms, self._finish_talking, expr)

    def _finish_talking(self, expr: str) -> None:
        self._talk_id = None
        self._stop_anim()
        self._show_sprite(f"face-{expr}" if f"face-{expr}" in self._sprites else "face-calm")
        if self._pet_window is not None:
            self._pet_window.set_state("idle")
        self._speech_bubble.update_status("LISTA")
        self._pet_chat.set_status("● ONLINE", "#68d391")
        self._status("🟢 Conectada", "#68d391")

    def _schedule_rest(self) -> None:
        if not self._settings.rest_animation or self._closing or not self._pet_window:
            return
        if self._rest_anim_id:
            return
        delay = self._rest_anim.idle_delay_ms()
        self._rest_anim_id = self._root.after(delay, self._rest_breathe)

    def _rest_breathe(self) -> None:
        self._rest_anim_id = None
        if not self._settings.rest_animation or self._closing or self._pet_window is None:
            return
        window = self._pet_window.window
        if not window.winfo_exists() or getattr(self._pet_window, "_drag", {}).get("moved", False):
            self._schedule_rest()
            return
        x, y = window.winfo_x(), window.winfo_y()
        window.geometry(f"+{x}+{y - 2}")
        self._rest_anim_id = self._root.after(600, self._rest_return)

    def _rest_return(self) -> None:
        self._rest_anim_id = None
        if self._pet_window is not None and self._pet_window.window.winfo_exists():
            if not getattr(self._pet_window, "_drag", {}).get("moved", False):
                x, y = self._pet_window.window.winfo_x(), self._pet_window.window.winfo_y()
                self._pet_window.window.geometry(f"+{x}+{y + 2}")
        self._schedule_rest()

    def _stop_rest(self) -> None:
        if self._rest_anim_id:
            try:
                self._root.after_cancel(self._rest_anim_id)
            except tk.TclError:
                pass
            self._rest_anim_id = None

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        # Barra de título
        bar = tk.Frame(self._root, bg="#161a29", height=32)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        self._title_bar = bar
        self._title_frame = bar

        tk.Label(bar, text="✦ SOPHIA", fg="#00f0ff", bg="#161a29",
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=10)

        tk.Button(bar, text="✕", command=self._on_close,
                  fg="#a0aec0", bg="#161a29", activeforeground="#ff5555",
                  activebackground="#161a29", bd=0, padx=14,
                  font=("Segoe UI", 12), cursor="hand2").pack(side=tk.RIGHT)

        self._pin_btn = tk.Button(
            bar, text="📌", command=self._toggle_pin,
            fg="#718096", bg="#161a29", activeforeground="#00f0ff",
            activebackground="#161a29", bd=0, padx=6,
            font=("Segoe UI", 9), cursor="hand2",
        )
        self._pin_btn.pack(side=tk.RIGHT)

        # Avatar
        self._avatar_frame = tk.Frame(self._root, bg="#0f111a", pady=8)
        self._avatar_frame.pack(fill=tk.X)

        self._avatar = tk.Label(self._avatar_frame, bg="#0f111a", cursor="hand2")
        self._avatar.pack()
        self._show_sprite("face-calm")
        self._avatar.bind("<Button-3>", lambda event: self._avatar_menu(event))

        connected = getattr(self._gemini, "is_configured", False)
        voice_unavailable = self._voice is not None and not self._voice.is_available()
        if voice_unavailable and self._settings.voice_enabled:
            initial_status, initial_color = "⚠️ Voz no disponible", "#f6ad55"
        else:
            initial_status, initial_color = ("🟢 Conectada" if connected else "⚠️ Sin clave", "#68d391" if connected else "#f6ad55")
        self._status_lbl = tk.Label(
            self._avatar_frame,
            text=initial_status,
            fg=initial_color,
            bg="#0f111a", font=("Segoe UI", 8),
        )
        self._status_lbl.pack(pady=4)

        # Terminal principal estilo OpenCode. La vista reemplaza al chat antiguo.
        self._chat_wrap = tk.Frame(self._root, bg="#0b0b10", padx=0, pady=0)
        self._chat_wrap.pack(fill=tk.BOTH, expand=True)
        self._main_terminal = TerminalView(
            self._chat_wrap, self._send_pet_text, self._settings.model,
            on_palette=lambda: self._open_main_palette(),
        )
        self._main_terminal.pack(fill=tk.BOTH, expand=True)
        self._chat = self._main_terminal.log
        self._entry = tk.Entry(self._root)
        self._entry.place_forget()

    # ------------------------------------------------------------------ drag

    def _setup_drag(self) -> None:
        def begin_drag(event: tk.Event) -> None:
            self._drag.update(
                x=event.x_root - self._root.winfo_x(),
                y=event.y_root - self._root.winfo_y(),
            )

        def begin_avatar(event: tk.Event) -> None:
            begin_drag(event)
            self._avatar_press.update(x_root=event.x_root, y_root=event.y_root, moved=False)

        def avatar_drag(event: tk.Event) -> None:
            dx = abs(event.x_root - self._avatar_press["x_root"])
            dy = abs(event.y_root - self._avatar_press["y_root"])
            if dx >= 4 or dy >= 4:
                self._avatar_press["moved"] = True
            if self._avatar_press["moved"]:
                self._do_drag(event)

        def avatar_release(event: tk.Event) -> None:
            if not self._avatar_press["moved"]:
                self._on_avatar_click()

        self._title_bar.bind("<ButtonPress-1>", begin_drag)
        self._title_bar.bind("<B1-Motion>", self._do_drag)
        self._avatar.bind("<ButtonPress-1>", begin_avatar)
        self._avatar.bind("<B1-Motion>", avatar_drag)
        self._avatar.bind("<ButtonRelease-1>", avatar_release)

    def _do_drag(self, event: tk.Event) -> None:
        x = event.x_root - self._drag["x"]
        y = event.y_root - self._drag["y"]
        self._root.geometry(f"+{x}+{y}")
        self._position_pet_bubble()
        if self._speech_bubble.window is not None and self._pet_window is not None:
            self._speech_bubble.position_near(
                self._pet_window.window.winfo_x(),
                self._pet_window.window.winfo_y(),
                self._pet_window.window.winfo_width(),
            )

    # ------------------------------------------------------------------ helpers

    def _status(self, text: str, color: str) -> None:
        self._status_lbl.configure(text=text, fg=color)

    def _save_settings(self) -> None:
        root = Path(__file__).resolve().parents[2]
        try:
            self._settings.save(root / "data" / "settings.json")
        except Exception:
            logger.exception("No se pudo guardar la configuración de audio")

    def _refresh_audio_buttons(self) -> None:
        if hasattr(self, "_voice_btn"):
            if self._voice is not None and not self._voice.is_available():
                self._voice_btn.configure(text="⚠️ VOZ NO DISPONIBLE", bg="#f6ad55", fg="#111827", activebackground="#f6ad55")
            elif self._settings.voice_enabled:
                self._voice_btn.configure(text="🔊 VOZ ACTIVADA", bg="#00f0ff", fg="#0f111a", activebackground="#38bdf8")
            else:
                self._voice_btn.configure(text="🔇 VOZ SILENCIADA", bg="#fc8181", fg="#111827", activebackground="#f6ad55")
        if hasattr(self, "_sfx_btn"):
            if self._settings.sfx_enabled:
                self._sfx_btn.configure(text="🔔 EFECTOS ON", bg="#68d391", fg="#111827")
            else:
                self._sfx_btn.configure(text="🔕 EFECTOS OFF", bg="#4a5568", fg="#e2e8f0")

    def _show_pet_bubble(self, text: str) -> None:
        if not getattr(self._settings, "pet_mode", False) or self._closing:
            return
        if self._pet_bubble is not None and self._pet_bubble.winfo_exists():
            label = getattr(self._pet_bubble, "_message_label", None)
            if label is not None:
                label.configure(text=text)
                self._position_pet_bubble()
                return
        bubble = tk.Toplevel(self._root)
        bubble.overrideredirect(True)
        bubble.configure(bg="#00f0ff")
        frame = tk.Frame(bubble, bg="#111827", highlightbackground="#00f0ff", highlightthickness=2)
        frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        label = tk.Label(frame, text=text, bg="#111827", fg="#e2e8f0",
                         font=("Segoe UI", 10), wraplength=280, justify=tk.LEFT,
                         padx=14, pady=12, cursor="hand2")
        label.pack(fill=tk.BOTH, expand=True)
        bubble._message_label = label
        bubble.bind("<Button-1>", lambda _: self._close_pet_bubble())
        label.bind("<Button-1>", lambda _: self._close_pet_bubble())
        self._pet_bubble = bubble
        self._position_pet_bubble()
        duration = max(3500, min(12000, 1800 + len(text) * 38))
        self._root.after(duration, self._close_pet_bubble)

    def _position_pet_bubble(self) -> None:
        if self._pet_bubble is None or not self._pet_bubble.winfo_exists():
            return
        self._pet_bubble.update_idletasks()
        width = max(300, self._pet_bubble.winfo_width())
        height = max(90, self._pet_bubble.winfo_height())
        x = self._root.winfo_x() + 280
        y = self._root.winfo_y() + 20
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        if x + width > screen_w:
            x = max(0, self._root.winfo_x() - width + 20)
        y = min(max(0, y), max(0, screen_h - height - 20))
        self._pet_bubble.geometry(f"{width}x{height}+{x}+{y}")

    def _position_speech_for_pet(self, x: int, y: int) -> None:
        width = self._pet_window.window.winfo_width() if self._pet_window is not None else 160
        height = self._pet_window.window.winfo_height() if self._pet_window is not None else 160
        terminal_rect = None
        if self._pet_chat.window is not None and self._pet_chat.window.winfo_exists():
            self._pet_chat.position_near(x, y, width)
            terminal_rect = Rect(
                self._pet_chat.window.winfo_x(), self._pet_chat.window.winfo_y(),
                self._pet_chat.window.winfo_width(), self._pet_chat.window.winfo_height(),
            )
        if self._speech_bubble.window is not None and self._speech_bubble.window.winfo_exists():
            self._speech_bubble.position_near(x, y, width, terminal_rect=terminal_rect, root_height=height)

    def _close_pet_bubble(self) -> None:
        if self._pet_bubble is not None and self._pet_bubble.winfo_exists():
            self._pet_bubble.destroy()
        self._pet_bubble = None

    def _avatar_menu(self, event: tk.Event) -> None:
        menu = tk.Menu(self._root, tearoff=0)
        menu.add_command(label="🔊 Activar voz" if not self._settings.voice_enabled else "🔇 Silenciar voz", command=self._toggle_voice)
        menu.add_command(label="💬 Abrir conversación IA", command=self._toggle_pet_chat)
        menu.add_command(label="Modo mascota/chat", command=self._toggle_pet_mode)
        menu.add_command(label="Salir", command=self._on_close)
        menu.tk_popup(event.x_root, event.y_root)

    def _toggle_pet_mode(self, force: bool | None = None) -> None:
        if force is None:
            self._settings.pet_mode = not self._settings.pet_mode
        else:
            self._settings.pet_mode = bool(force)
        try:
            if self._settings.pet_mode:
                def save_pet_position(x: int, y: int) -> None:
                    self._settings.pet_x = x
                    self._settings.pet_y = y
                    self._save_settings()
                if self._pet_window is None or not self._pet_window.window.winfo_exists():
                    self._pet_window = PetWindow(
                        self._root, self._assets,
                        avatar_size=self._settings.avatar_size,
                        on_click=self._on_avatar_click,
                        on_menu=self._avatar_menu,
                        on_position=save_pet_position,
                        on_drag=lambda x, y: self._position_speech_for_pet(x, y),
                    )
                    self._pet_window.restore_position(self._settings.pet_x, self._settings.pet_y)
                self._schedule_rest()
                self._root.withdraw()
            else:
                self._stop_rest()
                if self._pet_window is not None:
                    self._pet_window.close()
                    self._pet_window = None
                self._close_pet_bubble()
                self._speech_bubble.close()
                self._pet_chat.close()
                self._root.deiconify()
                self._root.overrideredirect(False)
                self._root.geometry("520x760")
                self._show_sprite(f"face-{self._current_expr}" if f"face-{self._current_expr}" in self._sprites else "face-calm")
                self._title_frame.pack(fill=tk.X)
                self._avatar_frame.pack(fill=tk.X, after=self._title_frame)
                self._chat_wrap.pack(fill=tk.BOTH, expand=True, after=self._avatar_frame)
            self._save_settings()
        except tk.TclError:
            logger.exception("No se pudo cambiar el modo mascota")

    def _open_main_palette(self) -> None:
        actions = [
            PaletteAction("Activar/silenciar voz", "voz", self._toggle_voice),
            PaletteAction("Activar/desactivar efectos", "sonidos", self._toggle_sfx),
            PaletteAction("Detener voz", "audio", self._stop_speech),
            PaletteAction("Limpiar terminal", "historial", self._clear_main_terminal),
            PaletteAction("Señalar reloj", "puntero", lambda: self._palette_action_point("clock", "RELOJ")),
            PaletteAction("Señalar ventana activa", "puntero", lambda: self._palette_action_point("active_window", "VENTANA ACTIVA")),
            PaletteAction("Abrir terminal", "conversación", self._toggle_pet_chat),
            PaletteAction("Cambiar modo ventana", "interfaz", lambda: self._toggle_pet_mode(False)),
            PaletteAction("Salir", "aplicación", lambda: self._on_close(force_exit=True)),
        ]
        self._palette = CommandPalette(self._root, actions)
        self._palette.open()

    def _clear_main_terminal(self) -> None:
        if hasattr(self, "_main_terminal"):
            self._main_terminal.clear_view()
        if hasattr(self, "_pet_chat") and self._pet_chat.view is not None:
            self._pet_chat.view.clear_view()

    def _palette_action_point(self, target: str, label: str) -> None:
        point = resolve_target(target)
        if point is not None:
            self._pointer_overlay.point_at(point.x, point.y, label, self._get_pet_origin())

    def _toggle_voice(self) -> None:
        self._settings.voice_enabled = not self._settings.voice_enabled
        if not self._settings.voice_enabled and self._voice is not None:
            self._voice.stop()
        self._refresh_audio_buttons()
        self._save_settings()
        if self._voice is not None and not self._voice.is_available():
            self._status("⚠️ Voz no disponible", "#f6ad55")
        else:
            self._status("🔇 Voz silenciada" if not self._settings.voice_enabled else "🟢 Voz activada",
                         "#fc8181" if not self._settings.voice_enabled else "#68d391")

    def _get_pet_origin(self) -> tuple[int, int]:
        if self._pet_window is not None:
            return self._pet_window.window.winfo_rootx(), self._pet_window.window.winfo_rooty()
        return self._root.winfo_rootx() + 180, self._root.winfo_rooty() + 300

    def _toggle_sfx(self) -> None:
        self._settings.sfx_enabled = not self._settings.sfx_enabled
        if not self._settings.sfx_enabled and self._sound is not None:
            self._sound.stop()
        self._refresh_audio_buttons()
        self._save_settings()

    def _stop_speech(self) -> None:
        if self._voice is not None:
            self._voice.stop()
        if self._sound is not None:
            self._sound.stop()
        self._stop_anim()
        self._speech_bubble.update_status("LISTA")
        if getattr(self._gemini, "is_configured", False):
            self._status("🟢 Conectada", "#68d391")
        else:
            self._status("⚠️ Sin clave", "#f6ad55")

    def _toggle_pin(self) -> None:
        self._pinned = not self._pinned
        self._root.wm_attributes("-topmost", self._pinned)
        self._pin_btn.configure(fg="#00f0ff" if self._pinned else "#718096")

    def _append_user(self, text: str) -> None:
        if hasattr(self, "_pet_chat"):
            self._pet_chat.append_user(text)
        if hasattr(self, "_main_terminal"):
            self._main_terminal.append_user(text)

    def _append_sophia(self, text: str, expr: str = "calm", error: bool = False, title: str = "") -> None:
        face = f"face-{expr}" if f"face-{expr}" in self._sprites else "face-calm"
        if hasattr(self, "_pet_chat"):
            self._pet_chat.append_sophia(text, error)
        if hasattr(self, "_main_terminal"):
            self._main_terminal.append_sophia(text, error)
        self._show_sprite(face)
        if self._settings.pet_mode:
            provisional_title = title.strip()[:60] if title.strip() else text.split(".", 1)[0][:60]
            body = text[len(provisional_title):].strip(" .") if not title and text.startswith(provisional_title) else text
            portrait = self._portraits.get(face)
            if self._speech_bubble.window is not None and self._speech_bubble.window.winfo_exists():
                self._speech_bubble.update_content(provisional_title, body, expr, portrait)
                self._speech_bubble.update_status("LISTA")
            else:
                self._speech_bubble.show(provisional_title, body, expr, "LISTA", portrait,
                                         self._settings.bubble_seconds)
            if self._speech_bubble.window is not None:
                if self._pet_window is not None:
                    self._speech_bubble.position_near(
                        self._pet_window.window.winfo_x(),
                        self._pet_window.window.winfo_y(),
                        self._pet_window.window.winfo_width(),
                    )
        else:
            self._show_pet_bubble(text)

    def _send_pet_text(self, text: str) -> None:
        if self._closing:
            return
        self._submit_text(text)

    def _toggle_pet_chat(self) -> None:
        if self._closing:
            return
        if self._pet_chat.window is not None and self._pet_chat.window.winfo_exists():
            self._pet_chat.close()
            return
        self._stop_anim()
        self._show_sprite("face-look")
        self._pet_chat.open()
        if self._pet_window is not None and self._pet_window.window.winfo_exists():
            self._pet_chat.position_near(
                self._pet_window.window.winfo_x(),
                self._pet_window.window.winfo_y(),
                self._pet_window.window.winfo_width(),
            )

    def _on_avatar_click(self) -> None:
        if self._closing:
            return
        self._toggle_pet_chat()

    def _play_intro(self) -> None:
        if not self._settings.show_intro or self._speech_bubble.window is None:
            return
        def decode_and_play() -> None:
            frames = load_intro_frames(self._assets, width=224, panel_color=self._speech_bubble.theme.bubble)
            if frames and not self._closing:
                self._events.put(("intro_frames", frames))
        threading.Thread(target=decode_and_play, daemon=True).start()

    def _welcome(self) -> None:
        self._append_sophia(
            "¡Hola! Ya estoy acá, lista para acompañarte. "
            "Podés hablarme de lo que sea, o arrastrarme a tu segundo monitor con la barra de arriba.",
            "calm",
        )
        self._play_intro()
        if self._settings.speak_welcome and self._voice is not None and self._settings.voice_enabled:
            self._voice.speak("¡Hola! Ya estoy acá, lista para acompañarte.")
        if self._settings.speak_welcome and self._sound is not None and self._settings.sfx_enabled:
            self._sound.play("hello")

    # ------------------------------------------------------------------ mensajería

    def _send(self) -> None:
        text = self._entry.get().strip() if hasattr(self, "_entry") else ""
        self._submit_text(text)

    def _submit_text(self, text: str) -> None:
        text = text.strip()
        if self._closing or not text or not self._busy.acquire(blocking=False):
            return
        command_result = handle_command(text, self._memory)
        if command_result is not None:
            if hasattr(self, "_entry"):
                try:
                    self._entry.delete(0, tk.END)
                except tk.TclError:
                    pass
            self._append_user(text)
            lowered = text.strip().lower()
            if lowered in ("/mute", "/callate", "/silenciar"):
                self._settings.voice_enabled = False
                if self._voice is not None:
                    self._voice.stop()
            elif lowered in ("/unmute", "/activarvoz"):
                self._settings.voice_enabled = True
            self._refresh_audio_buttons()
            self._save_settings()
            if command_result == "PANTALLA_CONFIRMAR":
                if messagebox.askyesno("Captura opt-in", "Esta imagen se enviará a Google Gemini. ¿Querés continuar?"):
                    captured = capture_screen_png()
                    if captured is not None:
                        image_b64, _ = captured
                        self._append_sophia("Voy a mirar la pantalla que elegiste enviar.", "look")
                        threading.Thread(target=self._process_screen, args=(image_b64,), daemon=True).start()
                        return
                    command_result = "No pude capturar la pantalla con las herramientas disponibles."
                else:
                    command_result = "Captura cancelada. No se envió nada a Google."
            if command_result.startswith("SEÑALAR:"):
                target, label = command_result.split(":", 1)[1].split("|", 1)
                point = resolve_target(target.lower())
                if point is not None:
                    origin = self._get_pet_origin()
                    self._pointer_overlay.point_at(point.x, point.y, label, origin)
                command_result = f"Señalando: {label.lower()}"
            self._append_sophia(command_result, "calm")
            self._busy.release()
            return
        if self._voice is not None:
            self._voice.stop()
        if self._sound is not None:
            self._sound.stop()
            self._sound.play("thinking")
        if hasattr(self, "_entry"):
            try:
                self._entry.delete(0, tk.END)
            except tk.TclError:
                pass
        self._append_user(text)
        self._status("🤔 Pensando...", "#f6ad55")
        self._speech_bubble.update_status("PENSANDO")
        self._pet_chat.set_thinking(True)
        if hasattr(self, "_main_terminal"):
            self._main_terminal.set_thinking(True)
        if self._pet_window is not None:
            self._pet_window.set_state("thinking")
        portrait = self._portraits.get("face-look")
        self._speech_bubble.show_thinking(portrait)
        if self._pet_window is not None:
            self._speech_bubble.position_near(
                self._pet_window.window.winfo_x(),
                self._pet_window.window.winfo_y(),
                self._pet_window.window.winfo_width(),
            )
        threading.Thread(target=self._process, args=(text,), daemon=True).start()

    def _process_screen(self, image_b64: str) -> None:
        try:
            reply = self._gemini.generate_screen_reply(
                "Mirá esta captura y explicame de forma breve qué hay en ella. Señalá active_window solo si ayuda realmente.",
                image_b64,
            )
        except Exception as err:
            logger.exception("Falló el análisis opt-in de pantalla")
            reply = Reply("No pude analizar la captura.", "aside", False, "network")
        if not self._closing:
            self._events.put(("reply", reply))

    def _process(self, user_text: str) -> None:
        """Llama a ChatService en segundo plano y publica el resultado por la cola."""
        try:
            reply = self._chat_service.send(user_text)
        except Exception as err:
            logger.exception("Falló el procesamiento del mensaje")
            reply = Reply(f"Ups, algo salió mal: {err}", "many", False, "network")
        if not self._closing:
            self._events.put(("reply", reply))

    def _render(self, reply: Reply) -> None:
        """Muestra la respuesta con desbloqueo garantizado."""
        try:
            self._append_sophia(reply.text, reply.expression if reply.ok else "many", error=not reply.ok,
                                title=getattr(reply, "title", ""))
            if reply.ok and getattr(reply, "target", "none") != "none":
                point = resolve_target(reply.target)
                if point is not None:
                    label = reply.target_label or reply.target.upper()
                    self._pointer_overlay.point_at(point.x, point.y, label, self._get_pet_origin())
            if reply.ok:
                if self._voice is not None and self._settings.voice_enabled:
                    self._voice.speak(reply.text)
                if self._sound is not None and self._settings.sfx_enabled:
                    self._sound.play("blip")
                duration = max(_MIN_TALK_MS, min(_MAX_TALK_MS, len(reply.text) * _MS_PER_CHAR))
                self._status("💬 Hablando...", "#00f0ff")
                self._speech_bubble.update_status("HABLANDO")
                self._pet_chat.set_status("HABLANDO", "#7c3aed")
                if hasattr(self, "_main_terminal"):
                    self._main_terminal.set_status("HABLANDO", "#7c3aed")
                if self._pet_window is not None:
                    self._pet_window.set_state("talking")
                    self._root.after(duration, lambda: self._pet_window.set_state("idle") if self._pet_window else None)
            else:
                if self._sound is not None and self._settings.sfx_enabled:
                    self._sound.play("error")
                self._status("⚠️ Error", "#fc8181")
                self._pet_chat.set_status("ERROR", "#c53030")
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
                elif kind == "intro_frames":
                    frames = payload if isinstance(payload, list) else []
                    if frames:
                        self._speech_bubble.play_stage(frames)
                        if self._pet_window is not None:
                            self._speech_bubble.position_near(
                                self._pet_window.window.winfo_x(),
                                self._pet_window.window.winfo_y(),
                                self._pet_window.window.winfo_width(),
                            )
                elif kind == "tray_toggle":
                    if self._root.state() == "withdrawn":
                        self._root.deiconify()
                        self._root.lift()
                    else:
                        self._root.withdraw()
                elif kind == "tray_mute":
                    self._toggle_voice()
                elif kind == "tray_exit":
                    self._on_close(force_exit=True)
        except queue.Empty:
            logger.debug("No hay eventos pendientes")
        if not self._closing:
            try:
                self._root.after(50, self._poll_events)
            except tk.TclError:
                logger.exception("La ventana se cerró mientras llegaba una respuesta")

    def _on_close(self, force_exit: bool = False) -> None:
        if not force_exit and self._settings.minimize_to_tray:
            self._root.withdraw()
            return
        self._closing = True
        self._stop_anim()
        self._stop_rest()
        self._pet_chat.close()
        self._speech_bubble.close()
        if self._tray is not None:
            self._tray.stop()
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
