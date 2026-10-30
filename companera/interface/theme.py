from dataclasses import dataclass, replace
from tkinter import font


@dataclass(frozen=True)
class TerminalTheme:
    background: str = "#0b0b10"
    surface: str = "#15151d"
    border: str = "#2a2440"
    text: str = "#e6e6ef"
    muted: str = "#7a7a8c"
    accent: str = "#7c3aed"
    accent_light: str = "#a78bfa"
    sophia: str = "#00f0ff"
    error: str = "#ff6b81"
    code: str = "#f6ad55"

TERMINAL_THEME = TerminalTheme()


def terminal_font(root) -> tuple[str, int]:
    try:
        families = set(font.families(root))
    except Exception:
        families = set()
    family = "Cascadia Mono" if "Cascadia Mono" in families else "Consolas"
    return family, 11


@dataclass(frozen=True)
class Theme:
    window: str
    panel: str
    accent: str
    text: str
    user: str
    error: str
    bubble: str = "#140f22"
    bubble_accent: str = "#7c3aed"
    pill: str = "#6d28d9"
    pointer: str = "#ff2d6f"
    bubble_secondary: str = "#c4b5fd"


DARK = Theme("#0f111a", "#161a29", "#00f0ff", "#edf2f7", "#f6ad55", "#fc8181")
LIGHT = Theme("#f7fafc", "#edf2f7", "#0077b6", "#1a202c", "#b7791f", "#c53030", "#ffffff", "#0077b6", "#38bdf8", "#d53f8c", "#4a5568")


def theme_for(name: str, accent: str | None = None) -> Theme:
    base = LIGHT if name == "claro" else DARK
    return replace(base, accent=accent or base.accent)
