"""Shared part of the event matrix: the event log, the step runner (used by test_events.py for the Win32 exes and
by tk_driver.py for the Tk engines in their own process) and the normalisation / comparison of the log."""
from __future__ import annotations

import threading
import time
from pathlib import Path

from spec import IGNORED, STEPS, expected


# ------------------------------------------------------------------ log
class FileLog:
    """Lines appended to a file by the program; markers are appended by the runner while the program is quiet."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.unlink(missing_ok=True)
        self.path.touch()

    def lines(self) -> list[str]:
        try:
            return self.path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return []

    def mark(self, text: str):
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")


class PipeLog:
    """Lines read from the program's stdout (VB6 Debug.Print in the native exe) by a thread."""

    def __init__(self, stream):
        self._lines: list[str] = []
        self._lock = threading.Lock()

        def pump():
            for raw in iter(stream.readline, b""):
                with self._lock:
                    self._lines.append(raw.decode("utf-8", "replace").rstrip("\r\n"))
        threading.Thread(target=pump, daemon=True).start()

    def lines(self) -> list[str]:
        with self._lock:
            return list(self._lines)

    def mark(self, text: str):
        with self._lock:
            self._lines.append(text)


class ListLog:
    """In-process log (vbrun Debug.Print output)."""

    def __init__(self, path: Path | None = None):
        self._lines: list[str] = []
        self.path = path

    def write(self, s: str):
        for ln in str(s).splitlines() or [""]:
            self._lines.append(ln)
            if self.path:
                with open(self.path, "a", encoding="utf-8", newline="\n") as f:
                    f.write(ln + "\n")

    def lines(self) -> list[str]:
        return list(self._lines)

    def mark(self, text: str):
        self.write(text)


# ------------------------------------------------------------------ runner
def settle(log, pump, quiet=0.5, limit=5.0, least=0.25):
    """Wait (pumping the GUI when in process) until the log has been quiet for *quiet* seconds."""
    t0 = time.time()
    n, last = len(log.lines()), time.time()
    while time.time() - t0 < limit:
        pump(0.05)
        m = len(log.lines())
        if m != n:
            n, last = m, time.time()
        elif time.time() - last >= quiet and time.time() - t0 >= least:
            break


def run_steps(driver, log, family: str, startup_wait=1.0):
    """Drive *driver* through every step of spec.STEPS that applies to *family*; markers go into the log:
    STEP <name> / READ <value> / FOCUS <name> / ALIVE <0|1>."""
    driver.pump(startup_wait)
    settle(log, driver.pump)
    for step in STEPS:
        if expected(step, family) is None:
            continue
        log.mark(f"STEP {step['name']}")
        why = driver.cannot(step) if hasattr(driver, "cannot") else ""
        if why:                                  # the engine cannot be driven for this step here
            log.mark(f"SKIPSTEP {why}")
            continue
        for op in step["ops"]:
            if op[0] == "wait":
                driver.pump(op[1])
            elif op[0] == "click":
                driver.click(op[1], op[2], op[3])
            elif op[0] == "key":
                driver.key(op[1], op[2])
            elif op[0] == "text":
                driver.text(op[1], op[2])
            elif op[0] == "close":
                driver.close()
            elif op[0] == "msgbox":
                driver.msgbox(op[1], op[2])
            driver.pump(0.05)
        settle(log, driver.pump, limit=8.0 if step["name"] == "close" else 5.0)
        if step.get("read"):
            log.mark(f"READ {driver.read(step['read'][0])}")
        if step.get("focus"):
            log.mark(f"FOCUS {driver.focus()}")
        if "alive" in step:
            if not step["alive"]:
                driver.wait_exit()
            log.mark(f"ALIVE {int(driver.alive())}")
        if "alive" in step and not driver.alive():
            break
    log.mark("STEP <end>")


# ------------------------------------------------------------------ normalisation / comparison
VB_BUTTON = {1: "L", 2: "R", 4: "M"}
NEUTRAL_BUTTON = {1: "L", 2: "M", 3: "R"}


def _num(s) -> str:
    try:
        v = float(s)
    except (TypeError, ValueError):
        return str(s)
    return str(int(v)) if v == int(v) else f"{v:g}"


def _key_name(tok: str) -> str:
    if tok.isdigit():
        v = int(tok)
        return chr(v) if 65 <= v <= 90 or 48 <= v <= 57 else tok
    return tok.upper() if len(tok) == 1 else tok


def normalize(line: str, family: str) -> str | None:
    """'EVT cmdA_MouseDown 5 6 1' -> 'cmdA_MouseDown x=5 y=6 b=L' (None: not an event line / ignored)."""
    if not line.startswith("EVT "):
        return None
    name, _, rest = line[4:].partition(" ")
    if name in IGNORED or name.endswith(("_MouseMove", "_MouseEnter", "_MouseLeave")):
        return None
    ev = name.rsplit("_", 1)[-1]
    p = rest.split()
    if ev in ("MouseDown", "MouseUp"):
        if family == "vb6":
            b, x, y = (int(float(p[0])) if p else 0), (p[2] if len(p) > 2 else "?"), (p[3] if len(p) > 3 else "?")
            return f"{name} x={_num(x)} y={_num(y)} b={VB_BUTTON.get(b, b)}"
        x, y = (p[0] if p else "?"), (p[1] if len(p) > 1 else "?")
        b = int(p[2]) if len(p) > 2 and p[2].lstrip("-").isdigit() else 0
        return f"{name} x={_num(x)} y={_num(y)} b={NEUTRAL_BUTTON.get(b, b)}"
    if ev in ("KeyDown", "KeyUp"):
        if family == "vb6":
            return f"{name} key={_key_name(p[0]) if p else '?'}"
        return f"{name} key={_key_name(p[3]) if len(p) > 3 else '?'}"
    if ev == "KeyPress":
        if family == "vb6":
            return f"{name} char={chr(int(p[0])) if p and p[0].isdigit() else '?'}"
        if len(p) > 4:
            return f"{name} char={p[4]}"
        if len(p) > 3 and p[3].isdigit() and len(p[3]) > 1:          # the character code ("97")
            return f"{name} char={chr(int(p[3]))}"
        return f"{name} char={p[3] if len(p) > 3 and len(p[3]) == 1 else '?'}"
    return f"{name} {rest}".rstrip()


def split_steps(lines: list[str]) -> tuple[list[str], dict[str, dict]]:
    """Log -> (lines before the first step, {step: {"lines": [...], "read": .., "focus": .., "alive": ..}})."""
    pre: list[str] = []
    steps: dict[str, dict] = {}
    cur = None
    for ln in lines:
        if ln.startswith("STEP "):
            name = ln[5:].strip()
            cur = None if name == "<end>" else steps.setdefault(name, {"lines": []})
            continue
        if cur is None:
            if not steps:
                pre.append(ln)
            continue
        for key in ("READ", "FOCUS", "ALIVE", "SKIPSTEP"):
            if ln.startswith(key + " ") or ln == key:
                cur[key.lower()] = ln[len(key) + 1:]
                break
        else:
            cur["lines"].append(ln)
    return pre, steps


def compare(lines: list[str], family: str) -> list[tuple[str, str, bool | None, str]]:
    """[(step, event family, passed (None: skipped), detail)] for every step of the family."""
    pre, steps = split_steps(lines)
    steps.setdefault("lifecycle_start", {"lines": []})["lines"][:0] = pre
    out = []
    for step in STEPS:
        want = expected(step, family)
        if want is None:
            continue
        got_step = steps.get(step["name"])
        if got_step is None:
            out.append((step["name"], step["family"], False, "step not reached"))
            continue
        if got_step.get("skipstep"):
            out.append((step["name"], step["family"], None, got_step["skipstep"]))
            continue
        got = [n for n in (normalize(ln, family) for ln in got_step["lines"]) if n]
        missing = [h for h in ([step["has"]] if step.get("has") else []) if h not in got]
        got = [g for g in got if g.split(" ")[0] not in step.get("ignore", ())]
        if step.get("ignore_focus"):
            got = [g for g in got if not g.split(" ")[0].endswith(("_GotFocus", "_LostFocus", "_Validate"))]
        if step["mode"] == "suffix":
            good = got[-len(want):] == want
        else:
            good = got == want
        detail = "" if good else f"got {got} want {want}"
        if missing:
            good = False
            detail += f" missing {missing}"
        if step.get("read") and got_step.get("read") != step["read"][1]:
            good = False
            detail += f" text={got_step.get('read')!r} want {step['read'][1]!r}"
        if step.get("focus") and (got_step.get("focus") or "").lower() != step["focus"].lower():
            good = False
            detail += f" focus={got_step.get('focus')!r} want {step['focus']!r}"
        if "alive" in step and got_step.get("alive") != str(int(step["alive"])):
            good = False
            detail += f" alive={got_step.get('alive')!r} want {int(step['alive'])}"
        out.append((step["name"], step["family"], good, detail.strip()))
    return out


def dialogs_of(pid: int) -> list[int]:
    """Visible message boxes (#32770) of process *pid*."""
    import ctypes
    from ctypes import wintypes as wt
    u = ctypes.WinDLL("user32")
    out = []
    proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(h, _l):
        p = wt.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u.IsWindowVisible(h):
            b = ctypes.create_unicode_buffer(64)
            u.GetClassNameW(h, b, 64)
            if b.value == "#32770":
                out.append(h)
        return True
    u.EnumWindows(proc(cb), 0)
    return out


def close_dialogs(pid: int) -> int:
    import ctypes
    u = ctypes.WinDLL("user32")
    u.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
    hs = dialogs_of(pid)
    for h in hs:
        u.PostMessageW(h, 0x0010, 0, 0)          # WM_CLOSE (an OK-only message box returns IDOK)
    return len(hs)
