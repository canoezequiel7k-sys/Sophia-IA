from __future__ import annotations

import json
import re
from companera.domain.models import Mood, Reply, Topic, VALID_EXPRESSIONS


def parse_reply(raw: str) -> Reply:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:-1] if len(lines) >= 2 and lines[-1].strip().startswith("```") else lines[1:]
            text = "\n".join(lines).strip()
    start, end = text.find("{"), text.rfind("}")
    candidate = text[start:end + 1] if start >= 0 and end > start else ""
    if not candidate:
        match = re.search(r"\[EXPR:\s*([a-zA-Z]+)\]\s*$", text)
        expr = match.group(1).lower() if match else "calm"
        clean = text[:match.start()].strip() if match else text
        return Reply(clean, expr if expr in VALID_EXPRESSIONS else "calm")
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"\[EXPR:\s*([a-zA-Z]+)\]\s*$", text)
        expr = match.group(1).lower() if match else "calm"
        clean = text[:match.start()].strip() if match else text
        return Reply(clean, expr if expr in VALID_EXPRESSIONS else "calm")
    expr = str(data.get("expression", "calm")).lower()
    if expr not in VALID_EXPRESSIONS:
        expr = "calm"
    try:
        mood = Mood(str(data.get("mood", "calm")))
    except ValueError:
        mood = Mood.CALM
    try:
        topic = Topic(str(data.get("topic", "general")))
    except ValueError:
        topic = Topic.GENERAL
    target = str(data.get("target", "none")).strip()
    if target not in {"none", "clock", "tray", "active_window"}:
        target = "none"
    facts = tuple(str(x).strip()[:120] for x in data.get("facts", []) if isinstance(x, str) and x.strip())[:50]
    return Reply(
        str(data.get("text", candidate)).strip(), expr, True, None, mood, topic, facts,
        str(data.get("title", "")).strip()[:60], target,
        str(data.get("target_label", "")).strip()[:40].upper(),
    )
