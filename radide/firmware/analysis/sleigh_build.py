"""Compile the vendored community SLEIGH processor modules (third_party/ghidra-processors/<name>) on first use.

The SLEIGH compiler comes with the ``pypcode`` wheel (``pypcode/bin/sleigh[.exe]``), so no Java and no Ghidra
installation are needed. The compiled ``.sla`` depends on the SLEIGH version, therefore it is built into a cache
folder keyed by the pypcode version and the source files (``%LOCALAPPDATA%\\RADIDE\\sleigh\\<name>-<hash>``)
instead of being shipped.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VENDOR = ROOT / "third_party" / "ghidra-processors"

# module folder -> (main .slaspec files, sleigh options, patch function name)
MODULES: dict[str, dict] = {
    "C166": dict(specs=["c166.slaspec"], args=["-t", "-u", "-n"], patch="_fix_export_order"),
    "RL78": dict(specs=["rl78.slaspec"], args=["-u", "-n"], patch=""),
}


def cache_root() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "RADIDE" / "sleigh"
    return Path(os.path.expanduser("~")) / ".cache" / "radide" / "sleigh"


def sleigh_compiler() -> Path | None:
    try:
        import pypcode
    except ImportError:
        return None
    b = Path(pypcode.__file__).parent / "bin"
    for name in ("sleigh.exe", "sleigh"):
        if (b / name).is_file():
            return b / name
    return None


_EXPORT_STMT = re.compile(r"export\s+\*(\[\w+\])?:(\d+)\s+(\w+)$")


def _fix_body(body: str) -> str | None:
    parts = [p.strip() for p in body.split(";") if p.strip()]
    idx = next((i for i, p in enumerate(parts) if p.startswith("export ")), None)
    if idx is None or idx == len(parts) - 1:
        return None
    exp, pre, rest = parts[idx], parts[:idx], parts[idx + 1:]
    m = _EXPORT_STMT.match(exp)
    if m and not any(re.match(r"local\s+%s\b" % re.escape(m.group(3)), p) for p in pre):
        # exports a register that a later statement changes: take the value first
        pre = pre + [f"local _ea:2 = {m.group(3)}"]
        exp = f"export *{m.group(1) or ''}:{m.group(2)} _ea"
    return " " + "; ".join(pre + rest + [exp]) + "; "


def _fix_export_order(text: str) -> str:
    """Ghidra's Java SLEIGH compiler accepts statements after ``export``; the C++ compiler wants it last."""
    out = []
    for line in text.splitlines(keepends=True):
        m = re.search(r"\{([^{}]*export[^{}]*)\}", line)
        if m:
            nb = _fix_body(m.group(1))
            if nb is not None:
                line = line[:m.start(1)] + nb + line[m.end(1):]
        out.append(line)
    return "".join(out)


def _digest(name: str) -> str:
    h = hashlib.sha1()
    try:
        import pypcode
        h.update(pypcode.__version__.encode())
    except ImportError:
        pass
    src = VENDOR / name / "data" / "languages"
    for p in sorted(src.iterdir()):
        if p.is_file():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    h.update(b"fix-v1")
    return h.hexdigest()[:12]


def available_modules() -> list[str]:
    return [n for n in MODULES if (VENDOR / n / "data" / "languages").is_dir()]


def build(name: str, force: bool = False) -> Path:
    """Path to the folder holding the compiled module (``.ldefs`` + ``.sla`` + specs). Raises RuntimeError."""
    if name not in MODULES:
        raise RuntimeError(f"unknown SLEIGH module {name!r}")
    src = VENDOR / name / "data" / "languages"
    if not src.is_dir():
        raise RuntimeError(f"SLEIGH sources for {name} are missing ({src})")
    comp = sleigh_compiler()
    if comp is None:
        raise RuntimeError("pypcode (with its SLEIGH compiler) is not installed: pip install pypcode")
    spec = MODULES[name]
    out = cache_root() / f"{name}-{_digest(name)}"
    if not force and all((out / s.replace(".slaspec", ".sla")).is_file() for s in spec["specs"]):
        return out
    tmp = Path(tempfile.mkdtemp(prefix=f"{name}-", dir=str(_ensure(cache_root()))))
    try:
        for p in src.iterdir():
            if p.is_file():
                data = p.read_text(encoding="utf-8", errors="replace") if p.suffix in (".sinc", ".slaspec") else None
                if data is not None and spec["patch"]:
                    data = globals()[spec["patch"]](data)
                    (tmp / p.name).write_text(data, encoding="utf-8", newline="")
                else:
                    shutil.copy2(p, tmp / p.name)
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        for s in spec["specs"]:
            r = subprocess.run([str(comp), *spec["args"], s, s.replace(".slaspec", ".sla")], cwd=str(tmp),
                               capture_output=True, text=True, timeout=300, creationflags=flags)
            if r.returncode != 0 or not (tmp / s.replace(".slaspec", ".sla")).is_file():
                errs = [ln for ln in (r.stdout + r.stderr).splitlines() if "ERROR" in ln or "rror" in ln][:8]
                raise RuntimeError(f"SLEIGH compile of {name}/{s} failed: " + ("; ".join(errs) or r.stderr[-400:]))
        if out.exists():
            shutil.rmtree(out, ignore_errors=True)
        try:
            tmp.rename(out)
        except OSError:                 # another process built it at the same time
            if not out.exists():
                raise
        return out
    finally:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)


def _ensure(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def ldefs_path(name: str) -> Path:
    d = build(name)
    found = sorted(d.glob("*.ldefs"))
    if not found:
        raise RuntimeError(f"no .ldefs in {d}")
    return found[0]


if __name__ == "__main__":         # python -m radide.firmware.analysis.sleigh_build [--force]
    for n in available_modules():
        print(n, "->", build(n, force="--force" in sys.argv))
