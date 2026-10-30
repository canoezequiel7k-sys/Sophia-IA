from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from companera.domain.models import CheckIn, Mood, Topic, VALID_EXPRESSIONS
from companera.infrastructure.gemini_service import SOPHIA_SYSTEM_PROMPT


@dataclass(frozen=True)
class ChatMessage:
    role: str
    text: str


def build_system_prompt(project_root: Path, include_json_instructions: bool = True) -> str:
    persona_path = project_root / "companera" / "persona" / "sophia.md"
    try:
        persona = persona_path.read_text(encoding="utf-8") if persona_path.exists() else SOPHIA_SYSTEM_PROMPT
    except OSError:
        persona = SOPHIA_SYSTEM_PROMPT
    facts: list[str] = []
    try:
        data = json.loads((project_root / "data" / "perfil.json").read_text(encoding="utf-8"))
        if isinstance(data, dict):
            facts = [str(x)[:120] for x in data.get("facts", []) if isinstance(x, str) and x.strip()][:50]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    if facts:
        persona += "\nLo que sabés del usuario:\n- " + "\n- ".join(facts)
    if include_json_instructions:
        persona += "\nDevolvé JSON con text, expression, mood, topic, facts, title, target y target_label. "
        persona += "expression permitidas: " + ", ".join(sorted(VALID_EXPRESSIONS)) + ". "
        persona += "mood: " + ", ".join([x.value for x in Mood]) + ". "
        persona += "topic: " + ", ".join([x.value for x in Topic]) + ". "
        persona += "target: none, clock, tray, active_window."
    return persona


def build_messages(history: list[CheckIn] | None, user_message: str, limit: int = 8) -> list[ChatMessage]:
    messages: list[ChatMessage] = []
    for item in (history or [])[-limit:]:
        messages.append(ChatMessage("user", item.text))
        if item.reply:
            messages.append(ChatMessage("assistant", item.reply))
    messages.append(ChatMessage("user", user_message))
    return messages
