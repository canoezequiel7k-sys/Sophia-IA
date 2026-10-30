from __future__ import annotations

from dataclasses import dataclass

from companera.interface.screen_metrics import Rect


@dataclass(frozen=True)
class Placement:
    x: int
    y: int
    w: int
    h: int
    tail_x: int


def _intersects(a: Rect, b: Rect) -> bool:
    return a.x < b.right and a.right > b.x and a.y < b.bottom and a.bottom > b.y


def place_terminal(pet: Rect, size: Rect, monitor: Rect) -> Rect:
    x = pet.x - size.w - 16
    y = pet.y + pet.h - size.h
    x = max(monitor.x, min(x, monitor.right - size.w))
    y = max(monitor.y, min(y, monitor.bottom - size.h))
    return Rect(x, y, size.w, size.h)


def place_bubble(pet: Rect, terminal: Rect, size: Rect, monitor: Rect) -> Placement:
    candidates = [
        Rect(pet.x + pet.w // 2 - size.w // 2, pet.y - size.h - 16, size.w, size.h),
        Rect(terminal.right + 16, pet.y + (pet.h - size.h) // 2, size.w, size.h),
        Rect(pet.right + 16, pet.y + (pet.h - size.h) // 2, size.w, size.h),
        Rect(pet.x + pet.w // 2 - size.w // 2, monitor.bottom - size.h, size.w, size.h),
    ]
    chosen = candidates[-1]
    for candidate in candidates:
        bounded = Rect(max(monitor.x, min(candidate.x, monitor.right - candidate.w)),
                       max(monitor.y, min(candidate.y, monitor.bottom - candidate.h)),
                       candidate.w, candidate.h)
        if not _intersects(bounded, terminal):
            chosen = bounded
            break
    tail_x = max(chosen.x + 12, min(pet.x + pet.w // 2, chosen.right - 12))
    return Placement(chosen.x, chosen.y, chosen.w, chosen.h, tail_x)
