from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable


@dataclass(frozen=True)
class TerminalMessage:
    role: str
    text: str
    error: bool = False
    stamp: str = "00:00"


class TerminalHistory:
    def __init__(self, limit: int = 300) -> None:
        self.limit = limit
        self._messages: list[TerminalMessage] = []
        self._subscribers: set[Callable[[TerminalMessage], None]] = set()

    @property
    def messages(self) -> tuple[TerminalMessage, ...]:
        return tuple(self._messages)

    def subscribe(self, callback: Callable[[TerminalMessage], None]) -> Callable[[], None]:
        self._subscribers.add(callback)
        return lambda: self.unsubscribe(callback)

    def unsubscribe(self, callback: Callable[[TerminalMessage], None]) -> None:
        self._subscribers.discard(callback)

    def _stamp(self) -> str:
        return datetime.now().strftime("%H:%M")

    def add(self, role: str, text: str, error: bool = False) -> TerminalMessage:
        message = TerminalMessage(role=role, text=text, error=error, stamp=self._stamp())
        self._messages.append(message)
        if len(self._messages) > self.limit:
            self._messages = self._messages[-self.limit:]
        for callback in tuple(self._subscribers):
            callback(message)
        return message

    def add_user(self, text: str) -> TerminalMessage:
        return self.add("user", text)

    def add_sophia(self, text: str, error: bool = False) -> TerminalMessage:
        return self.add("sophia", text, error)

    def clear(self) -> None:
        self._messages.clear()
        notification = TerminalMessage(role="clear", text="", error=False, stamp=self._stamp())
        for callback in tuple(self._subscribers):
            callback(notification)
