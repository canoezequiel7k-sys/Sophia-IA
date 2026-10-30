from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    window: str
    panel: str
    accent: str
    text: str
    user: str
    error: str


DARK = Theme("#0f111a", "#161a29", "#00f0ff", "#edf2f7", "#f6ad55", "#fc8181")
LIGHT = Theme("#f7fafc", "#edf2f7", "#0077b6", "#1a202c", "#b7791f", "#c53030")


def theme_for(name: str, accent: str | None = None) -> Theme:
    base = LIGHT if name == "claro" else DARK
    return Theme(base.window, base.panel, accent or base.accent, base.text, base.user, base.error)
