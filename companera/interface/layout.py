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
    tail_y: int = 0
    side: str = "bottom"


def _intersects(a: Rect, b: Rect) -> bool:
    return a.x < b.right and a.right > b.x and a.y < b.bottom and a.bottom > b.y


def place_terminal(pet: Rect, size: Rect, monitor: Rect) -> Rect:
    x = pet.x - size.w - 16
    y = pet.y + pet.h - size.h
    x = max(monitor.x, min(x, monitor.right - size.w))
    y = max(monitor.y, min(y, monitor.bottom - size.h))
    return Rect(x, y, size.w, size.h)


def place_bubble(pet: Rect, terminal: Rect, size: Rect, monitor: Rect) -> Placement:
    mouth_y = pet.y + int(pet.h * 0.58)
    right_x = pet.right + 16
    left_x = pet.x - size.w - 16
    candidates = [
        ("left", Rect(left_x, pet.y + int(pet.h * 0.18), size.w, size.h)),
        ("right", Rect(right_x, pet.y + int(pet.h * 0.18), size.w, size.h)),
        ("bottom", Rect(pet.x + pet.w // 2 - size.w // 2, pet.bottom + 16, size.w, size.h)),
        ("top", Rect(pet.x + pet.w // 2 - size.w // 2, pet.y - size.h - 16, size.w, size.h)),
    ]
    chosen_side = "bottom"
    chosen = Rect(monitor.x, monitor.bottom - size.h, size.w, size.h)
    for side, candidate in candidates:
        bounded = Rect(max(monitor.x, min(candidate.x, monitor.right - candidate.w)),
                       max(monitor.y, min(candidate.y, monitor.bottom - candidate.h)),
                       size.w, size.h)
        if not _intersects(bounded, terminal) and not _intersects(bounded, pet):
            chosen = bounded
            chosen_side = side
            break
    if chosen_side == "left" or chosen_side == "right":
        tail_y = max(chosen.y + 32, min(mouth_y - chosen.y, chosen.bottom - chosen.y - 32))
        tail_x = chosen.right - chosen.x if chosen_side == "left" else 0
    else:
        tail_x = max(chosen.x + 12, min(pet.x + pet.w // 2, chosen.right - 12))
        tail_y = chosen.bottom - chosen.y if chosen_side == "top" else 0
        tail_x -= chosen.x
    return Placement(chosen.x, chosen.y, chosen.w, chosen.h, tail_x, tail_y, chosen_side)
