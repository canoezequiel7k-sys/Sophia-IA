from dataclasses import dataclass, replace


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
