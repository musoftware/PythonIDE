"""Shared helpers of the .NET importer (also used by the Java, Python-exe, VB6 and Electron importers):
progress messages, running and downloading tools, AI rewrite, Python literals / identifiers, JSON output."""
from __future__ import annotations

import json
import keyword
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

from ..base import ai_translate as _base_ai_translate


# ============================================================================ shared helpers
def say(progress, text: str) -> None:
    if progress is None:
        return
    try:
        progress(text)
    except TypeError:
        try:
            progress(0, text)
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        pass


def run_tool(cmd: list[str], cwd: Path | None = None, timeout: int = 900, env: dict | None = None
             ) -> tuple[int, str]:
    """Run a command without a console window; (exit code, stdout+stderr)."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, creationflags=flags,
                           env=env)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, f"timed out after {timeout} s: {' '.join(cmd[:3])}"
    except OSError as e:
        return -1, str(e)


def download(url: str, dest: Path, progress=None, timeout: int = 120) -> bool:
    """Download *url* to *dest* (atomic rename).  Used only for open-source tools in tools_dir()."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    say(progress, f"Downloading {url.rsplit('/', 1)[-1]} ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RADIDE-importer"})
        with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as fh:
            shutil.copyfileobj(r, fh)
        if tmp.stat().st_size < 1024:
            tmp.unlink(missing_ok=True)
            return False
        os.replace(tmp, dest)
        return True
    except Exception:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        return False


def ai_rewrite(source: str, source_lang: str, context: str, progress=None) -> tuple[str | None, str]:
    """AI translation through base.ai_translate (CONTRACTS 9.1), never raises."""
    try:
        return _base_ai_translate(source, source_lang, "Python (tkinter)", context, progress)
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def pystr(value: str) -> str:
    """A double-quoted Python string literal."""
    out = repr(value)
    if out.startswith("'") and '"' not in value:
        out = '"' + out[1:-1].replace("\\'", "'") + '"'
    return out


PY_RESERVED = set(keyword.kwlist) | {"str", "int", "len", "list", "dict", "float", "bool", "type", "print",
                                     "max", "min", "abs", "round", "range", "self", "object", "id", "input",
                                     "sum", "format", "map", "next", "iter", "set", "math", "random",
                                     "messagebox", "datetime", "tk"}


def py_ident(name: str) -> str:
    name = name.lstrip("@")
    return name + "_" if name in PY_RESERVED else name


def save_json(obj, path: Path) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
