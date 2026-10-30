from __future__ import annotations

import ctypes
import sys
from typing import NamedTuple


class Point(NamedTuple):
    x: int
    y: int


class Rect(NamedTuple):
    left: int
    top: int
    right: int
    bottom: int


def _rect_center(rect: Rect) -> Point:
    return Point((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)


def clock_area() -> Point | None:
    if sys.platform != "win32":
        return None
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW("Shell_TrayWnd", None)
        rect = ctypes.wintypes.RECT()
        if hwnd and user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            width = max(1, rect.right - rect.left)
            return Point(rect.right - max(80, width // 8), rect.bottom - 18)
    except Exception:
        return None
    return None


def tray() -> Point | None:
    return clock_area()


def active_window() -> Point | None:
    if sys.platform != "win32":
        return None
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        rect = ctypes.wintypes.RECT()
        if hwnd and ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return Point(rect.right - 30, rect.top + 30)
    except Exception:
        return None
    return None


def screen_corner(name: str) -> Point | None:
    if sys.platform != "win32":
        return None
    try:
        rect = ctypes.wintypes.RECT()
        SPI_GETWORKAREA = 48
        if not ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
            return None
        name = name.lower()
        if name in {"top_left", "arriba_izquierda"}:
            return Point(rect.left, rect.top)
        if name in {"top_right", "arriba_derecha"}:
            return Point(rect.right, rect.top)
        if name in {"bottom_left", "abajo_izquierda"}:
            return Point(rect.left, rect.bottom)
        return Point(rect.right, rect.bottom)
    except Exception:
        return None


def mouse_position() -> Point | None:
    if sys.platform != "win32":
        return None
    try:
        point = ctypes.wintypes.POINT()
        if ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
            return Point(point.x, point.y)
    except Exception:
        return None
    return None


def resolve_target(target: str) -> Point | None:
    if target == "clock" or target == "tray":
        return clock_area()
    if target == "active_window":
        return active_window()
    return None
