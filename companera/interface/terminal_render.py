from __future__ import annotations

import re
import textwrap
from typing import Iterable


def parse_inline(text: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    pattern = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*)")
    pos = 0
    for match in pattern.finditer(text):
        if match.start() > pos:
            result.append(("plain", text[pos:match.start()]))
        token = match.group(0)
        if token.startswith("**"):
            result.append(("bold", token[2:-2]))
        else:
            result.append(("code", token[1:-1]))
        pos = match.end()
    if pos < len(text):
        result.append(("plain", text[pos:]))
    return result or [("plain", text)]


def wrap(text: str, columns: int = 72, prefix: str = "") -> list[str]:
    columns = max(20, columns)
    lines: list[str] = []
    in_code = False
    for source in text.splitlines() or [""]:
        stripped = source.strip()
        if source.startswith("```") or stripped.startswith("```"):
            in_code = not in_code
            lines.append(prefix + stripped if stripped else prefix)
            continue
        if in_code or source.startswith("    "):
            chunks = textwrap.wrap(source.strip(), width=max(20, columns - len(prefix)), replace_whitespace=False, drop_whitespace=False) or [source.strip()]
            lines.extend(prefix + chunk for chunk in chunks)
        elif stripped.startswith("- ") or stripped.startswith("• "):
            marker = "• "
            chunks = textwrap.wrap(stripped[2:], width=max(20, columns - len(prefix) - 2), subsequent_indent="  ", break_long_words=True, break_on_hyphens=False)
            for index, chunk in enumerate(chunks or [""]):
                lines.append(prefix + (marker if index == 0 else "  ") + chunk)
        else:
            chunks = textwrap.wrap(source, width=max(20, columns - len(prefix)), replace_whitespace=False, break_long_words=True, break_on_hyphens=False) or [""]
            lines.extend(prefix + chunk for chunk in chunks)
    return lines
