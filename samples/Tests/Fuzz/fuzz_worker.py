"""Worker process of the parser fuzzer: runs one target (targets.py) on inputs sent by fuzzlib.Worker.

Protocol: stdin = 4-byte little-endian length + input bytes (0xFFFFFFFF = quit); stdout = one JSON line
per input: {"st": ok|handled|crash|write, "sig", "msg", "tb", "t"}.  The target's own prints go to NUL.
Every file write / delete / rename outside RADFUZZ_WORK is refused (audit hook) and reported as "write".
"""
from __future__ import annotations

import json
import os
import shutil
import struct
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
sys.setrecursionlimit(3000)

WORK = os.path.normcase(os.path.abspath(os.environ["RADFUZZ_WORK"]))
CASE = Path(WORK) / "case"

# private protocol handles; fd 0 / 1 go to NUL so nothing the target prints or reads disturbs them
_in = os.fdopen(os.dup(0), "rb", 0)
_out = os.fdopen(os.dup(1), "wb", 0)
_nul = os.open(os.devnull, os.O_RDWR)
os.dup2(_nul, 0)
os.dup2(_nul, 1)
sys.stdin = open(os.devnull, encoding="utf-8")            # noqa: SIM115
sys.stdout = open(os.devnull, "w", encoding="utf-8")      # noqa: SIM115

VIOLATIONS: list[str] = []
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC


def _outside(p) -> str | None:
    if isinstance(p, int) or p is None:
        return None
    try:
        s = os.fsdecode(p)
    except Exception:  # noqa: BLE001
        return None
    if s.lower() in ("nul", os.devnull.lower()) or s.startswith("\\\\.\\"):
        return None
    full = os.path.normcase(os.path.abspath(s))
    if full == WORK or full.startswith(WORK + os.sep):
        return None
    return s


def _audit(event, args):
    paths = ()
    if event == "open":
        path, mode, flags = (list(args) + [None, None, None])[:3]
        writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or \
                  (mode is None and isinstance(flags, int) and flags & _WRITE_FLAGS)
        if writing:
            paths = (path,)
    elif event in ("os.remove", "os.rmdir", "os.mkdir", "os.truncate", "os.chmod", "shutil.rmtree",
                   "os.symlink", "os.link", "shutil.copyfile", "shutil.move"):
        paths = args[-1:] if event in ("shutil.copyfile", "shutil.move", "os.symlink", "os.link") else args[:1]
    elif event in ("os.rename", "os.replace"):
        paths = args[:2]
    elif event == "subprocess.Popen":
        VIOLATIONS.append(f"subprocess started: {str(args[1])[:200]}")
        raise PermissionError("fuzz worker: starting programs is not allowed")
    for p in paths:
        bad = _outside(p)
        if bad is not None:
            VIOLATIONS.append(f"{event} {bad}")
            raise PermissionError(f"fuzz worker: write outside the work folder refused: {bad}")


def _sig(e: BaseException) -> str:
    frames = traceback.extract_tb(e.__traceback__)
    mine = [f for f in frames if os.sep + "radide" + os.sep in f.filename]
    f = (mine or frames or [None])[-1]
    where = f"{Path(f.filename).relative_to(ROOT) if str(f.filename).startswith(str(ROOT)) else f.filename}:" \
            f"{f.lineno}" if f is not None else "?"
    return f"{type(e).__name__}@{where}".replace("\\", "/")


def _send(d: dict) -> None:
    _out.write((json.dumps(d) + "\n").encode())
    _out.flush()


def main() -> None:
    import targets
    T = targets.TARGETS[sys.argv[1]]
    sys.addaudithook(_audit)
    T.setup()
    allowed = T.allowed()
    _send({"ready": True})
    while True:
        hdr = _in.read(4)
        if len(hdr) < 4:
            return
        (n,) = struct.unpack("<I", hdr)
        if n == 0xFFFFFFFF:
            return
        data = b""
        while len(data) < n:
            chunk = _in.read(n - len(data))
            if not chunk:
                return
            data += chunk
        shutil.rmtree(CASE, ignore_errors=True)
        CASE.mkdir(parents=True, exist_ok=True)
        os.chdir(CASE)
        del VIOLATIONS[:]
        t0 = time.perf_counter()
        res = {"st": "ok"}
        try:
            T.run(data, CASE)
        except allowed as e:
            res = {"st": "handled", "sig": type(e).__name__, "msg": str(e)[:300]}
        except RecursionError as e:
            res = {"st": "crash", "sig": _sig(e), "msg": "RecursionError", "tb": traceback.format_exc()[-3000:]}
        except BaseException as e:  # noqa: BLE001 - everything else is a finding
            if isinstance(e, KeyboardInterrupt):
                raise
            res = {"st": "crash", "sig": _sig(e), "msg": f"{type(e).__name__}: {str(e)[:300]}",
                   "tb": traceback.format_exc()[-4000:]}
        if VIOLATIONS:
            res = {"st": "write", "sig": "write-outside", "msg": "; ".join(VIOLATIONS)[:500],
                   "tb": res.get("tb", "")}
        res["t"] = round(time.perf_counter() - t0, 4)
        _send(res)


if __name__ == "__main__":
    main()
