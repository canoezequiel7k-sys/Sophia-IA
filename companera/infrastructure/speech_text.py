from __future__ import annotations

import re

_EMOJI_RE = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
_URL_RE = re.compile(r"(?:https?://|www\.)\S+", flags=re.IGNORECASE)
_CODE_BLOCK_RE = re.compile(r"```.*?```", flags=re.DOTALL)


def clean_for_speech(text: str) -> str:
    """Convierte texto de chat a una versión segura y natural para voz."""
    cleaned = _CODE_BLOCK_RE.sub("te dejé el código en el chat", text)
    cleaned = cleaned.replace("```", "").replace("`", "")
    cleaned = re.sub(r"[*_#]", "", cleaned)
    cleaned = _URL_RE.sub("un enlace", cleaned)
    cleaned = _EMOJI_RE.sub("", cleaned)
    return " ".join(cleaned.split()).strip()
