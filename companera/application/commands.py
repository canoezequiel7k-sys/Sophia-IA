from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CommandAction(str, Enum):
    NONE = "NONE"
    MUTE_VOICE = "MUTE_VOICE"
    UNMUTE_VOICE = "UNMUTE_VOICE"
    MUTE_SOUND = "MUTE_SOUND"
    UNMUTE_SOUND = "UNMUTE_SOUND"
    CLEAR_HISTORY = "CLEAR_HISTORY"
    FORGET_PROFILE = "FORGET_PROFILE"
    POINT = "POINT"
    SCREEN = "SCREEN"
    EXIT = "EXIT"
    OPEN_MODEL_PICKER = "OPEN_MODEL_PICKER"
    SET_MODEL = "SET_MODEL"
    TOGGLE_FALLBACK = "TOGGLE_FALLBACK"


@dataclass(frozen=True)
class CommandResult:
    message: str = ""
    action: CommandAction = CommandAction.NONE
    arg: str = ""


COMMANDS = (
    "/help", "/mute voice", "/mute sound", "/unmute voice",
    "/unmute sound", "/profile", "/forget", "/clear",
    "/point clock", "/point window", "/screen", "/model",
    "/model list", "/model fallback on", "/model fallback off", "/exit",
)


def handle_command(message: str, memory_clear: object | None = None) -> CommandResult | None:
    """Interpreta comandos locales y devuelve acciones tipadas."""
    stripped = message.strip()
    if not stripped.startswith("/"):
        return None
    parts = stripped.lower().split(maxsplit=1)
    command = parts[0]
    argument = parts[1].strip() if len(parts) > 1 else ""

    if command in ("/help", "/ayuda"):
        return CommandResult("Available commands: " + ", ".join(COMMANDS))
    if command == "/mute":
        if argument in ("", "voice"):
            return CommandResult("Voice muted.", CommandAction.MUTE_VOICE)
        if argument == "sound":
            return CommandResult("Sound effects muted.", CommandAction.MUTE_SOUND)
        return CommandResult("Use /mute voice or /mute sound.")
    if command == "/unmute":
        if argument in ("", "voice"):
            return CommandResult("Voice enabled.", CommandAction.UNMUTE_VOICE)
        if argument == "sound":
            return CommandResult("Sound effects enabled.", CommandAction.UNMUTE_SOUND)
        return CommandResult("Use /unmute voice or /unmute sound.")
    if command == "/profile" or command == "/perfil":
        return CommandResult("Local profile available; manage it in data/perfil.json.")
    if command == "/forget" or command == "/olvidar":
        if argument == "all":
            return CommandResult("Profile cleared.", CommandAction.FORGET_PROFILE)
        return CommandResult("Use /forget all to erase the complete profile.")
    if command in ("/clear", "/limpiar"):
        return CommandResult("Conversation history cleared.", CommandAction.CLEAR_HISTORY)
    if command in ("/screen", "/pantalla"):
        return CommandResult("", CommandAction.SCREEN)
    if command == "/point" or command == "/señalar":
        if argument in ("clock", "tray", "reloj", "bandeja"):
            return CommandResult("Señalando: clock", CommandAction.POINT, "clock")
        if argument in ("window", "active_window", "ventana"):
            return CommandResult("Señalando: active window", CommandAction.POINT, "active_window")
        return CommandResult("Use /point clock or /point window.")
    if command == "/exit" or command == "/salir":
        return CommandResult("Closing Sophia…", CommandAction.EXIT)
    if command in ("/model", "/modelo"):
        if not argument:
            return CommandResult("", CommandAction.OPEN_MODEL_PICKER)
        if argument == "list":
            return CommandResult("", CommandAction.SET_MODEL, "list")
        if argument.startswith("fallback "):
            return CommandResult("", CommandAction.TOGGLE_FALLBACK, argument.split(maxsplit=1)[1])
        return CommandResult("", CommandAction.SET_MODEL, argument)
    if command in ("/silenciar", "/callate"):
        return CommandResult("Voice muted.", CommandAction.MUTE_VOICE)
    if command in ("/activarvoz", "/unmutevoice"):
        return CommandResult("Voice enabled.", CommandAction.UNMUTE_VOICE)
    return CommandResult("Unknown command. Available commands: " + ", ".join(COMMANDS))
