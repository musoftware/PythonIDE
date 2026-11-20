"""Local helper processes used by the WSL and Dev Container backends (wsl.exe, docker.exe)."""
from __future__ import annotations

import codecs
import queue
import subprocess
import sys
import threading
import time
from typing import Callable

from .base import ShellBackend

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def kill_tree(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, creationflags=NO_WINDOW)
    else:
        import os
        import signal
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def run(argv: list[str], timeout: float = 30, input_bytes: bytes | None = None) -> tuple[int, bytes]:
    try:
        p = subprocess.run(argv, capture_output=True, timeout=timeout, input=input_bytes, creationflags=NO_WINDOW)
        return p.returncode, p.stdout + p.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e).encode()


def run_stream(argv: list[str], on_output: Callable[[str], None], should_stop: Callable[[], bool] = lambda: False,
               timeout: float | None = None) -> int:
    """Run *argv*, streaming stdout+stderr as text. Returns the exit code (-1 when stopped)."""
    try:
        p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             creationflags=NO_WINDOW)
    except OSError as e:
        on_output(f"Cannot start {argv[0]}: {e}\n")
        return -1
    q: queue.Queue = queue.Queue()

    def reader():
        while True:
            b = p.stdout.read1(65536) if hasattr(p.stdout, "read1") else p.stdout.read(4096)
            if not b:
                break
            q.put(b)
        q.put(None)
    threading.Thread(target=reader, daemon=True).start()
    dec = codecs.getincrementaldecoder("utf-8")(errors="replace")
    start = time.monotonic()
    while True:
        try:
            b = q.get(timeout=0.05)
        except queue.Empty:
            if should_stop() or (timeout and time.monotonic() - start > timeout):
                kill_tree(p.pid)
                p.wait(5)
                return -1
            continue
        if b is None:
            break
        on_output(dec.decode(b))
    tail = dec.decode(b"", final=True)
    if tail:
        on_output(tail)
    return p.wait()


class ProcessShell(ShellBackend):
    """An interactive shell in a local process (pipes, no console window)."""

    def __init__(self, argv: list[str]):
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     creationflags=NO_WINDOW)
        self.q: queue.Queue = queue.Queue()
        threading.Thread(target=self._reader, daemon=True).start()
        self._ended = False

    def _reader(self):
        out = self.proc.stdout
        while True:
            b = out.read1(65536) if hasattr(out, "read1") else out.read(4096)
            if not b:
                break
            self.q.put(b)
        self.q.put(None)

    def write(self, data: bytes) -> None:
        if data == b"\x03":            # no PTY: Ctrl+C cannot be delivered as a signal
            return self.interrupt()
        try:
            self.proc.stdin.write(data.replace(b"\r\n", b"\n"))
            self.proc.stdin.flush()
        except OSError:
            pass

    def interrupt(self) -> None:
        # without a terminal the best we can do is end the commands started by this shell
        # (the shell process restarts on the next command - see RemoteTerminal)
        self.close()

    def poll(self) -> bytes | None:
        out = b""
        while True:
            try:
                b = self.q.get_nowait()
            except queue.Empty:
                break
            if b is None:
                self._ended = True
                break
            out += b
        if not out and self._ended:
            return None
        return out

    def close(self) -> None:
        if self.proc.poll() is None:
            kill_tree(self.proc.pid)
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                pass


__all__ = ["run", "run_stream", "ProcessShell", "kill_tree", "NO_WINDOW"]
