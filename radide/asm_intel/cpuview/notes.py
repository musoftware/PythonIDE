"""User comments and labels of the CPU view, kept per project in ``<project>/.radide/cpu_notes.json``.

Addresses are stored *static* (run-time address minus the session's relocation slide, see nativedbg's
AsmDapSession.slide) so that a comment survives ASLR and the next debugging session. The 8086 emulator has no
relocation (linear addresses). A program run without a project keeps its notes next to the program.

    {"version": 1, "programs": {"sum.exe": {"comments": {"0x140001010": "loop body"}, "labels": {...}}}}
"""
from __future__ import annotations

import json
from pathlib import Path


class CpuNotes:
    def __init__(self, path: Path | None, program: str = ""):
        self.path = Path(path) if path else None
        self.program = program or "program"
        self.comments: dict[int, str] = {}
        self.labels: dict[int, str] = {}
        self.load()

    # ------------------------------------------------------------ file
    def _all(self) -> dict:
        if self.path is None or not self.path.is_file():
            return {"version": 1, "programs": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) and isinstance(data.get("programs"), dict) else \
                {"version": 1, "programs": {}}
        except (OSError, ValueError):
            return {"version": 1, "programs": {}}

    def load(self) -> None:
        mine = self._all()["programs"].get(self.program) or {}
        self.comments = {int(k, 16): str(v) for k, v in (mine.get("comments") or {}).items() if _is_hex(k)}
        self.labels = {int(k, 16): str(v) for k, v in (mine.get("labels") or {}).items() if _is_hex(k)}

    def save(self) -> bool:
        if self.path is None:
            return False
        data = self._all()
        data["programs"][self.program] = {
            "comments": {hex(a): t for a, t in sorted(self.comments.items()) if t},
            "labels": {hex(a): t for a, t in sorted(self.labels.items()) if t}}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
            return True
        except OSError:
            return False

    # ------------------------------------------------------------ editing (static addresses)
    def set_comment(self, addr: int, text: str) -> None:
        if text.strip():
            self.comments[addr] = text.strip()
        else:
            self.comments.pop(addr, None)
        self.save()

    def set_label(self, addr: int, text: str) -> None:
        if text.strip():
            self.labels[addr] = text.strip()
        else:
            self.labels.pop(addr, None)
        self.save()

    def label_address(self, name: str) -> int | None:
        for a, n in self.labels.items():
            if n == name or n.lower() == name.lower():
                return a
        return None


def _is_hex(k) -> bool:
    try:
        int(str(k), 16)
        return True
    except ValueError:
        return False


def notes_path(win, program_path: str | Path | None) -> Path | None:
    """<project>/.radide/cpu_notes.json, else next to the program, else None."""
    proj = getattr(win, "project", None) if win is not None else None
    folder = getattr(proj, "folder", None)
    if folder:
        return Path(folder) / ".radide" / "cpu_notes.json"
    if program_path:
        return Path(program_path).parent / ".radide" / "cpu_notes.json"
    return None
