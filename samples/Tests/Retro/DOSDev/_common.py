"""Shared helpers of the DOS development tests (no Qt)."""
from __future__ import annotations

import os
import socket
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
WORK = Path(os.environ.get("DOSDEV_WORK") or (Path(tempfile.gettempdir()) / "radide-dosdev"))
WORK.mkdir(parents=True, exist_ok=True)
RESULTS: list[tuple[str, str]] = []          # (name, PASS | FAIL | SKIP)


def online(host: str = "github.com") -> bool:
    try:
        socket.create_connection((host, 443), timeout=5).close()
        return True
    except OSError:
        return False


def check(name: str, cond, detail="") -> bool:
    RESULTS.append((name, "PASS" if cond else "FAIL"))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:900]}]"), flush=True)
    return bool(cond)


def skip(name: str, reason: str) -> None:
    RESULTS.append((name, "SKIP"))
    print(f"SKIP {name}  ({reason})", flush=True)


def summary() -> int:
    p = sum(r == "PASS" for _, r in RESULTS)
    f = [n for n, r in RESULTS if r == "FAIL"]
    s = sum(r == "SKIP" for _, r in RESULTS)
    print(f"{p}/{len(RESULTS)} passed, {s} skipped; FAILED: {f or 'none'}", flush=True)
    return 1 if f else 0
