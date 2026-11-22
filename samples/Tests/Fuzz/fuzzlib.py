"""Shared fuzzing helpers (pure Python, no external fuzzer): seeded mutators, a watchdog'ed worker
process per target (time limit, memory limit, writes outside the work folder are refused and reported)
and delta debugging (ddmin) to shrink a failing input to a minimal reproduction.

Used by test_parsers.py (parser fuzzing) and test_designer_model.py (shrinking of operation sequences).
"""
from __future__ import annotations

import json
import os
import queue
import random
import re
import struct
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CORPUS = HERE / "corpus"
MAX_SIZE = 4 * 1024 * 1024

INTERESTING_8 = [0, 1, 0x7F, 0x80, 0xFF, 0x20, 0x0A, 0x22, 0x5C]
INTERESTING_16 = [0, 0x7FFF, 0x8000, 0xFFFF, 0x100, 0x1000]
INTERESTING_32 = [0, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0x10000, 0x40000000, 0xFFFFFFF0]
INTERESTING_NUMS = ["0", "-1", "1", "65535", "65536", "2147483647", "2147483648", "-2147483649",
                    "4294967296", "18446744073709551616", "99999999999999999999999999", "1e308", "-1e308",
                    "1e999", "NaN", "Infinity", "0x7fffffff", "&HFFFFFFFF", "00000000000000", "-0", "1.5"]
BAD_UTF8 = [b"\xff", b"\xc3", b"\xed\xa0\x80", b"\xf4\x90\x80\x80", b"\xc0\xaf", b"\x80\x80", b"\xfe\xff",
            b"\x00", b"\xef\xbb\xbf"]
NASTY_TEXT = ['"', "'", "\\", "\r\n", "\n", "\t", "\x00", "{", "}", "[", "]", "(", ")", "<", ">", "&", ";",
              "\u202e", "\u0627\u0644\u0639\u0631\u0628\u064a\u0629", "\U0001F600", "\ufeff", "%s", "{0}",
              "${x}", '"""', "'''", "*/", "/*", "--", "End", "Begin", "End Sub", "#"]


# =============================================================================== mutation
def _num_spans(data: bytes):
    return [m.span() for m in re.finditer(rb"-?\d+", data[:200000])]


def mutate(data: bytes, rng: random.Random, kind: str = "bytes", others: list[bytes] | None = None,
           tokens: list[bytes] | None = None) -> bytes:
    """1..4 random edits of *data*. kind: bytes | text | json (text kinds add number / token / UTF-8 edits)."""
    b = bytearray(data)
    for _ in range(rng.choice((1, 1, 2, 2, 3, 4))):
        ops = ["flip", "byte", "int", "del", "ins", "dup", "trunc", "splice"]
        if kind in ("text", "json"):
            ops += ["num", "num", "tok", "utf8", "line_dup", "line_del", "line_swap", "nasty"]
        op = rng.choice(ops)
        n = len(b)
        if op == "flip" and n:
            i = rng.randrange(n)
            b[i] ^= 1 << rng.randrange(8)
        elif op == "byte" and n:
            b[rng.randrange(n)] = rng.choice(INTERESTING_8 + [rng.randrange(256)])
        elif op == "int" and n >= 8:
            w = rng.choice((2, 4, 4, 8))
            i = rng.randrange(n - w + 1)
            v = rng.choice(INTERESTING_16 if w == 2 else INTERESTING_32) if w != 8 else rng.choice(
                [0, 2 ** 63 - 1, 2 ** 64 - 1, 2 ** 32])
            v &= (1 << (8 * w)) - 1
            b[i:i + w] = v.to_bytes(w, rng.choice(("little", "big")))
        elif op == "del" and n:
            i = rng.randrange(n)
            b[i:i + rng.randint(1, max(1, min(n - i, rng.choice((4, 64, 1024)))))] = b""
        elif op == "ins":
            i = rng.randrange(n + 1)
            b[i:i] = bytes(rng.randrange(256) for _ in range(rng.randint(1, 32)))
        elif op == "dup" and n:
            i = rng.randrange(n)
            chunk = bytes(b[i:i + rng.randint(1, 256)])
            reps = rng.choice((2, 10, 100, 1000, 10000))
            if len(chunk) * reps + n < MAX_SIZE:
                b[i:i] = chunk * reps
        elif op == "trunc" and n:
            del b[rng.randrange(n):]
        elif op == "splice" and others:
            o = rng.choice(others)
            if o:
                i, j = rng.randrange(n + 1), rng.randrange(len(o))
                b[i:] = o[j:j + rng.randint(1, 4096)]
        elif op == "num":
            spans = _num_spans(bytes(b))
            if spans:
                s, e = rng.choice(spans)
                b[s:e] = rng.choice(INTERESTING_NUMS).encode()
        elif op == "tok" and tokens:
            i = rng.randrange(n + 1)
            b[i:i] = rng.choice(tokens)
        elif op == "utf8":
            i = rng.randrange(n + 1)
            b[i:i] = rng.choice(BAD_UTF8)
        elif op == "nasty":
            i = rng.randrange(n + 1)
            b[i:i] = rng.choice(NASTY_TEXT).encode("utf-8", "surrogatepass")
        elif op.startswith("line_"):
            lines = bytes(b).split(b"\n")
            if len(lines) > 1:
                i = rng.randrange(len(lines))
                if op == "line_dup":
                    lines[i:i] = [lines[i]] * rng.choice((1, 2, 50))
                elif op == "line_del":
                    del lines[i]
                else:
                    j = rng.randrange(len(lines))
                    lines[i], lines[j] = lines[j], lines[i]
                b = bytearray(b"\n".join(lines))
    if kind == "json" and rng.random() < 0.5:
        try:
            doc = json.loads(bytes(data).decode("utf-8-sig"))
        except Exception:  # noqa: BLE001
            doc = None
        if doc is not None:
            return json.dumps(mutate_json(doc, rng), ensure_ascii=rng.random() < 0.5).encode()
    return bytes(b[:MAX_SIZE])


def random_json(rng: random.Random, depth: int = 0):
    r = rng.random()
    if depth > 4 or r < 0.35:
        return rng.choice([None, True, False, 0, -1, 2 ** 31, 2 ** 64, 1.5, float("1e308"), "", "x",
                           "\u0627", "Form1", "Button", "../../x", "C:\\Windows", " ", "\x00"])
    if r < 0.65:
        return [random_json(rng, depth + 1) for _ in range(rng.randint(0, 4))]
    keys = ["type", "props", "controls", "Name", "Parent", "Left", "Top", "Width", "Height", "name",
            "language", "forms", "startup", "projects", "path", "cells", "source", "outputs", "metadata",
            "nbformat", "cell_type", "version", "states", "variants", "animations", "contributes", "main",
            "engines", "publisher", "activationEvents", "items", "Items", "TabPages", "Dock", "Anchor"]
    return {rng.choice(keys): random_json(rng, depth + 1) for _ in range(rng.randint(0, 5))}


def mutate_json(doc, rng: random.Random):
    """Replace / delete / retype one random node of a parsed JSON document."""
    nodes = []

    def walk(x, parent, key, depth):
        nodes.append((parent, key))
        if depth > 12 or len(nodes) > 5000:
            return
        if isinstance(x, dict):
            for k, v in list(x.items()):
                walk(v, x, k, depth + 1)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, x, i, depth + 1)
    walk(doc, None, None, 0)
    for _ in range(rng.randint(1, 3)):
        parent, key = rng.choice(nodes)
        if parent is None:
            if rng.random() < 0.1:
                return random_json(rng)
            continue
        try:
            r = rng.random()
            if r < 0.3 and isinstance(parent, dict):
                parent.pop(key, None)
            elif r < 0.4 and isinstance(parent, list) and key < len(parent):
                del parent[key]
            elif r < 0.5:
                v = parent[key]
                parent[key] = [v] if not isinstance(v, list) else {"x": v}
            else:
                parent[key] = random_json(rng, 2)
        except (KeyError, IndexError, TypeError):
            pass
    return doc


def deep_nest(open_tok: bytes, close_tok: bytes, depth: int, middle: bytes = b"") -> bytes:
    return open_tok * depth + middle + close_tok * depth


# =============================================================================== delta debugging
def ddmin(items: list, test, max_probes: int = 400) -> list:
    """Classic ddmin: a smaller list of *items* for which test(list) is still True."""
    n, probes = 2, 0
    while len(items) >= 2 and probes < max_probes:
        chunk = -(-len(items) // n)
        reduced = False
        for i in range(n):
            cand = items[:i * chunk] + items[(i + 1) * chunk:]
            if not cand:
                continue
            probes += 1
            if test(cand):
                items, n, reduced = cand, max(n - 1, 2), True
                break
            if probes >= max_probes:
                break
        if not reduced:
            if n >= len(items):
                break
            n = min(len(items), n * 2)
    return items


def shrink_bytes(data: bytes, test, max_probes: int = 300) -> bytes:
    """Lines first (text inputs shrink much faster), then bytes."""
    lines = data.split(b"\n")
    if len(lines) > 2:
        kept = ddmin([ln + b"\n" for ln in lines[:-1]] + [lines[-1]], lambda c: test(b"".join(c)),
                     max_probes // 2)
        data = b"".join(kept)
    if len(data) <= 4096:
        data = bytes(ddmin(list(data), lambda c: test(bytes(c)), max_probes // 2))
    return data


# =============================================================================== worker process
@dataclass
class Result:
    st: str                 # ok | handled | crash | hang | oom | write | died
    sig: str = ""
    msg: str = ""
    tb: str = ""
    secs: float = 0.0

    @property
    def bad(self) -> bool:
        return self.st not in ("ok", "handled")


class Worker:
    """One target's worker process (fuzz_worker.py). run(data) -> Result; the process is killed and
    restarted after a hang (no reply within *timeout* s) or when its memory exceeds *mem_mb*."""

    def __init__(self, target: str, work: Path, timeout: float = 10.0, mem_mb: int = 1500):
        self.target, self.work, self.timeout, self.mem_mb = target, Path(work), timeout, mem_mb
        self.proc = None
        self.q: queue.Queue = queue.Queue()
        self.started = 0

    def _env(self) -> dict:
        env = dict(os.environ)
        w = str(self.work)
        env.update({"RADFUZZ_WORK": w, "TEMP": str(self.work / "tmp"), "TMP": str(self.work / "tmp"),
                    "LOCALAPPDATA": str(self.work / "localappdata"), "APPDATA": str(self.work / "appdata"),
                    "USERPROFILE": str(self.work / "home"), "HOME": str(self.work / "home"),
                    "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1", "QT_QPA_PLATFORM": "offscreen",
                    "RADIDE_NO_BROWSER": "1", "PYTHONUTF8": "1"})
        env.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
        return env

    def start(self) -> None:
        for sub in ("tmp", "localappdata", "appdata", "home", "case"):
            (self.work / sub).mkdir(parents=True, exist_ok=True)
        self.q = queue.Queue()
        err = open(self.work / "worker_stderr.txt", "ab")     # noqa: SIM115 - lives with the process
        self.proc = subprocess.Popen([sys.executable, "-X", "utf8", str(HERE / "fuzz_worker.py"), self.target],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err,
                                     env=self._env(), cwd=str(self.work / "case"))
        self.started += 1
        q, out = self.q, self.proc.stdout

        def reader():
            for line in out:
                q.put(line)
            q.put(None)
        threading.Thread(target=reader, daemon=True).start()
        line = self._wait(180.0)
        if line is None or not line.startswith(b'{"ready"'):
            raise RuntimeError(f"fuzz worker for {self.target} did not start: {line!r} "
                               f"(see {self.work / 'worker_stderr.txt'})")

    def _wait(self, timeout: float):
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return None

    def kill(self) -> None:
        if self.proc is not None:
            try:
                self.proc.kill()
                self.proc.wait(10)
            except Exception:  # noqa: BLE001
                pass
            self.proc = None

    def close(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.stdin.write(struct.pack("<I", 0xFFFFFFFF))
                self.proc.stdin.flush()
                self.proc.wait(10)
            except Exception:  # noqa: BLE001
                pass
        self.kill()

    def run(self, data: bytes, timeout: float | None = None) -> Result:
        if self.proc is None or self.proc.poll() is not None:
            self.start()
        if timeout is None:     # the limit grows with the input: +10 s per MB (big files may take linear time)
            timeout = self.timeout + 10.0 * len(data) / 1_000_000
        try:
            self.proc.stdin.write(struct.pack("<I", len(data)) + data)
            self.proc.stdin.flush()
        except OSError:
            self.kill()
            return Result("died", "worker-pipe", "the worker process died before the case was sent")
        try:
            import psutil
            ps = psutil.Process(self.proc.pid)
        except Exception:  # noqa: BLE001
            ps = None
        t0 = time.monotonic()
        while True:
            try:
                line = self.q.get(timeout=0.05)
                break
            except queue.Empty:
                pass
            el = time.monotonic() - t0
            if el > timeout:
                self.kill()
                return Result("hang", "hang", f"no result after {timeout:.0f} s", secs=el)
            if ps is not None:
                try:
                    rss = ps.memory_info().rss
                except Exception:  # noqa: BLE001
                    rss = 0
                if rss > self.mem_mb * 1024 * 1024:
                    self.kill()
                    return Result("oom", "memory", f"worker memory {rss // 2 ** 20} MB > {self.mem_mb} MB",
                                  secs=el)
        if line is None:
            code = self.proc.poll() if self.proc else None
            self.kill()
            return Result("died", f"died:{code}", f"the worker process exited (code {code})",
                          secs=time.monotonic() - t0)
        d = json.loads(line)
        return Result(d["st"], d.get("sig", ""), d.get("msg", ""), d.get("tb", ""), d.get("t", 0.0))


# =============================================================================== reporting
class Report:
    def __init__(self):
        self.results: list[tuple[str, bool, str]] = []

    def check(self, name: str, cond: bool, detail: str = "") -> bool:
        self.results.append((name, bool(cond), detail))
        print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:900]}]"), flush=True)
        return bool(cond)

    def summary(self) -> int:
        fails = sum(1 for _, ok, _ in self.results if not ok)
        print(f"\n{len(self.results) - fails}/{len(self.results)} passed, {fails} failed", flush=True)
        return fails
