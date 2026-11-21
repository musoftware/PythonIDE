"""Raw bus traffic log: every byte sent to / received from an adapter (AT commands, hex requests, CAN frames,
J2534 messages) as timestamped entries. The Bus Monitor panel (link/qt.py) shows it live; ``save()`` writes a
plain-text log. Thread-safe: adapters log from worker threads, listeners are called on that thread."""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass

TX, RX, INFO, ERROR = "tx", "rx", "info", "error"


@dataclass
class LogEntry:
    t: float            # time.time()
    channel: str        # "elm", "can", "j2534", "sim", "uds", ...
    direction: str      # tx / rx / info / error
    text: str

    def line(self) -> str:
        ms = int((self.t - int(self.t)) * 1000)
        arrow = {TX: ">>", RX: "<<", INFO: "--", ERROR: "!!"}.get(self.direction, "  ")
        return f"{time.strftime('%H:%M:%S', time.localtime(self.t))}.{ms:03d} {self.channel:<6} {arrow} {self.text}"


class BusLog:
    def __init__(self, maxlen: int = 20000):
        self.entries: deque[LogEntry] = deque(maxlen=maxlen)
        self.listeners: list = []
        self.enabled = True
        self._lock = threading.Lock()

    def add(self, channel: str, direction: str, text: str) -> None:
        if not self.enabled:
            return
        e = LogEntry(time.time(), channel, direction, text.rstrip())
        with self._lock:
            self.entries.append(e)
            listeners = list(self.listeners)
        for fn in listeners:
            try:
                fn(e)
            except Exception:  # noqa: BLE001 - a broken listener must not break the bus
                pass

    def tx(self, channel: str, text: str) -> None:
        self.add(channel, TX, text)

    def rx(self, channel: str, text: str) -> None:
        self.add(channel, RX, text)

    def info(self, channel: str, text: str) -> None:
        self.add(channel, INFO, text)

    def error(self, channel: str, text: str) -> None:
        self.add(channel, ERROR, text)

    def subscribe(self, fn) -> None:
        with self._lock:
            if fn not in self.listeners:
                self.listeners.append(fn)

    def unsubscribe(self, fn) -> None:
        with self._lock:
            if fn in self.listeners:
                self.listeners.remove(fn)

    def clear(self) -> None:
        with self._lock:
            self.entries.clear()

    def snapshot(self) -> list[LogEntry]:
        with self._lock:
            return list(self.entries)

    def text(self) -> str:
        return "\n".join(e.line() for e in self.snapshot())

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(self.text() + "\n")


BUS_LOG = BusLog()          # the IDE-wide log the Bus Monitor shows


def printable(data: bytes) -> str:
    """ELM text with control characters made visible (\\r -> ↵)."""
    return data.decode("ascii", "replace").replace("\r\n", "↵").replace("\r", "↵").replace("\n", "↵")
