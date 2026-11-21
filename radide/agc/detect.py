"""File > Open Folder: recognise Apollo AGC programs (radide/project_detect.py calls ``detect_agc``)."""
from __future__ import annotations

from pathlib import Path


def detect_agc(folder: Path, Candidate, walk) -> list:
    files = walk(folder, 2, 1500)
    agc = [f for f in files if f.lower().endswith(".agc")]
    if not agc:
        return []
    top = sorted(f for f in agc if "/" not in f)
    if not top:
        return []
    main = next((f for f in top if f.upper() == "MAIN.AGC"), top[0])
    try:
        text = (Path(folder) / main).read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    includes = sum(1 for ln in text.splitlines() if ln.strip().startswith("$"))
    flight = includes >= 20 or any(k in text.upper() for k in ("COMANCHE", "LUMINARY", "COLOSSUS", "ARTEMIS"))
    title = (f"Apollo flight program ({len(top)} log sections, built with yaYUL)" if flight else
             f"Apollo AGC program ({len(top)} file{'s' if len(top) != 1 else ''}, {main})")
    modules = sorted(top, key=lambda n: (n != main, n))
    c = Candidate("agc", title, "agc-yul", "app", folder, 0.9, [main] + top[:2], startup=Path(main).stem,
                  modules=modules)
    c.extra["agc"] = {"assembler": "yayul", "run": "yaagc"} if flight else {"assembler": "auto", "run": "emulator"}
    c.notes.append("F5 assembles MAIN.agc (built-in assembler, or yaYUL for interpretive code) and runs it with the "
                   "DSKY panel.")
    return [c]


__all__ = ["detect_agc"]
