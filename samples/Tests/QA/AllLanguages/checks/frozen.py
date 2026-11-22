"""Check family "frozen": the IntelliSense / designer / run checks again inside the release build.

The release RADIDE.exe runs Python code when started with RADIDE_AS_PYTHON=1 (tools/radide_frozen_main.py ->
radide.paths.run_as_python), so this test's own IDE child (checks/ide_child.py) runs inside the frozen IDE: it
imports the frozen radide package and its bundled data, which finds frozen-only problems (missing modules,
data files, component packages). Programs it starts get RADIDE.exe as their Python (like a PC without Python).
"""
from __future__ import annotations

import json
import os
import subprocess

from pathlib import Path

DEFAULT_BUILDS = [
    Path(os.environ.get("TEMP", "")) / "claude" / "a04f521f5a700edd" / "02e2bcf1-4b7c-48a3-a5b6-de40fd6242d9" /
    "scratchpad" / "build-ide" / "dist" / "RADIDE" / "RADIDE.exe",
    Path(__file__).resolve().parents[5] / "dist" / "RADIDE" / "RADIDE.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "RAD IDE" / "RADIDE.exe",
]


def find_build(explicit: str = "") -> Path | None:
    for p in ([Path(explicit)] if explicit else []) + DEFAULT_BUILDS:
        if p and p.is_file():
            return p
    return None


def run(cases, checks: set[str], scratch: Path, exe: Path, timeout: float = 3600) -> dict:
    """{(lang, template): {"frozen.<family>.<check>": status}} from the frozen child."""
    driver = Path(__file__).resolve().parent.parent / "test_all_languages.py"
    out = scratch / "frozen_results.json"
    log = scratch / "frozen_child.log"
    out.unlink(missing_ok=True)
    env = dict(os.environ, RADIDE_AS_PYTHON="1", QA_CHILD_LOG=str(log))
    for k in ("PYTHONPATH", "PYTHONHOME"):
        env.pop(k, None)
    argv = [str(exe), str(driver), "--ide-child", "--prefix", "frozen.",
            "--lang", ",".join(f"{l}:{t}" for l, t in cases), "--check", ",".join(sorted(checks)),
            "--scratch", str(scratch / "frozen"), "--json", str(out)]
    try:
        subprocess.run(argv, cwd=str(scratch), env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        pass
    res: dict = {}
    if out.is_file():
        for d in json.loads(out.read_text(encoding="utf-8")).get("results", []):
            res[(d["language"], d["template"])] = {k: v for k, v in d.get("sub", {}).items()}
            if d.get("notes"):
                res[(d["language"], d["template"])]["__notes__"] = d["notes"]
    if not res:
        tail = log.read_text(encoding="utf-8", errors="replace")[-1500:] if log.is_file() else ""
        for c in cases:
            res[c] = {"frozen.start": f"FAIL: the frozen IDE child wrote no results. {tail}"}
    return res


