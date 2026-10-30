from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class BubbleLayout:
    width: int
    height: int
    title_lines: list[str]
    body_lines: list[str]
    stage_y: int | None
    title_y: int
    body_y: int
    body_h: int
    button: tuple[int, int, int, int]
    truncated: bool


def _wrap_paragraphs(text: str, max_chars: int) -> list[str]:
    lines: list[str] = []
    paragraphs = str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blank_pending = False
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            if lines and not blank_pending:
                lines.append("")
                blank_pending = True
            continue
        blank_pending = False
        words = paragraph.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word[:max_chars]
                while len(current) == max_chars and len(word) > max_chars:
                    rest = word[max_chars:] if len(word) > max_chars else ""
                    if rest:
                        lines.append(current)
                        word = rest
                        current = word[:max_chars]
                    else:
                        break
        if current:
            lines.append(current)
    return lines


def compute_layout(title: str, body: str, measure_title: Callable[[str], int],
                   measure_body: Callable[[str], int], line_h_title: int,
                   line_h_body: int, scale: float = 1.0,
                   max_height: int = 648, stage_h: int = 0) -> BubbleLayout:
    scale = max(1.0, float(scale))
    margin = max(12, int(12 * scale))
    max_width = max(320, int(460 * scale))
    min_width = max(320, int(320 * scale))
    body_width = max(180, max_width - int(128 * scale))
    char_estimate = max(20, body_width // 8)

    title_lines = _wrap_paragraphs(title, max(10, char_estimate * 2 // 3))
    body_lines = _wrap_paragraphs(body, max(20, char_estimate))
    widest = 0
    for line in title_lines + body_lines:
        widest = max(widest, measure_title(line), measure_body(line))
    width = min(max_width, max(min_width, int(widest + 128 * scale)))

    available_body_width = width - int(128 * scale)
    title_lines = _wrap_paragraphs(title, max(10, available_body_width // max(1, measure_title("M") or 1)))
    body_lines = _wrap_paragraphs(body, max(20, available_body_width // max(1, measure_body("M") or 1)))

    y = margin + int(12 * scale)
    header_h = int(56 * scale)
    y += header_h + int(10 * scale)

    stage_y = None
    if stage_h > 0:
        stage_y = y
        y += int(stage_h * scale) + int(10 * scale)

    title_y = y
    if title_lines:
        title_h = len(title_lines) * max(1, int(line_h_title * scale))
        y += title_h + int(8 * scale)
    body_y = y

    button_h = int(34 * scale)
    fixed_after_body = button_h + int(12 * scale) + margin + int(18 * scale)
    available = max(0, int(max_height) - y - fixed_after_body)
    line_h = max(1, int(line_h_body * scale))
    max_lines = max(1, available // line_h)
    truncated = len(body_lines) > max_lines
    visible = body_lines[:max_lines]
    if truncated and visible:
        visible[-1] = visible[-1].rstrip(" .") + "…"
    body_h = len(visible) * line_h
    y += body_h + int(10 * scale)

    button_x1 = width - int(146 * scale)
    button_x2 = width - int(18 * scale)
    button = (button_x1, y, button_x2, y + button_h)
    height = y + button_h + int(12 * scale) + margin + int(18 * scale)
    height = min(max_height, max(int(180 * scale), height))
    return BubbleLayout(width, height, title_lines, visible if truncated else body_lines,
                        stage_y, title_y, body_y, body_h, button, truncated)
