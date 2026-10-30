from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h


def virtual_screen() -> Rect:
    if sys.platform == "win32":
        try:
            x = ctypes.windll.user32.GetSystemMetrics(76)
            y = ctypes.windll.user32.GetSystemMetrics(77)
            w = ctypes.windll.user32.GetSystemMetrics(78)
            h = ctypes.windll.user32.GetSystemMetrics(79)
            return Rect(x, y, w, h)
        except Exception:
            pass
    return Rect(0, 0, 1920, 1080)


def monitor_at(x: int, y: int, fallback_w: int = 1920, fallback_h: int = 1080) -> Rect:
    if sys.platform == "win32":
        try:
            import ctypes.wintypes
            point = ctypes.wintypes.POINT(x, y)
            monitor = ctypes.windll.user32.MonitorFromPoint(point, 2)
            info = ctypes.wintypes.RECT()
            class MonitorInfo(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.wintypes.DWORD), ("rcMonitor", ctypes.wintypes.RECT), ("rcWork", ctypes.wintypes.RECT), ("dwFlags", ctypes.wintypes.DWORD)]
            mi = MonitorInfo()
            mi.cbSize = ctypes.sizeof(MonitorInfo)
            if monitor and ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(mi)):
                r = mi.rcWork
                return Rect(r.left, r.top, r.right - r.left, r.bottom - r.top)
        except Exception:
            pass
    virtual = virtual_screen()
    return Rect(virtual.x, virtual.y, virtual.w, virtual.h)
