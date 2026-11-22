"""Runs the IDE check families (intellisense, designer, debug, optionally run) for several languages in ONE
process with one offscreen MainWindow; started by the driver as a child process (also inside the frozen
RADIDE.exe for the "frozen" family). Writes {"results": [Result...]} as JSON."""
from __future__ import annotations

import json
import shutil
import time
import traceback
from dataclasses import asdict
from pathlib import Path

from . import common as C

FAMILIES = ("intellisense", "designer", "debug")


def run(cases: list[tuple[str, str]], checks: set[str], scratch: Path, out_json: Path, prefix: str = "") -> int:
    scratch.mkdir(parents=True, exist_ok=True)
    results: list[C.Result] = []

    def save():
        out_json.write_text(json.dumps({"results": [asdict(x) for x in results]}, indent=2), encoding="utf-8")

    host = None
    try:
        from .ide import host as get_host
        host = get_host()
    except Exception as e:  # noqa: BLE001
        for pid, t in cases:
            r = C.Result(pid, t)
            r.sub[f"{prefix}ide.start"] = f"FAIL: the IDE could not start: {type(e).__name__}: {e}"
            r.note(traceback.format_exc())
            results.append(r)
        save()
        return 1
    pl_all = C.plugins()
    for pid, template in cases:
        pl = pl_all[pid]
        r = C.Result(pid, template, pl.display_name)
        t0 = time.time()
        folder = scratch / f"{pid}__{template or 'default'}"
        shutil.rmtree(folder, ignore_errors=True)
        print(f"[ide] {pid} ({template}) ...", flush=True)
        try:
            project = C.create(folder, "QA" + "".join(ch for ch in pid.title() if ch.isalnum()), pl, template)
            if C.has_form_code(pl) and getattr(project, "forms", None) and "Form1" in project.forms:
                C.add_click_form(project, pl)
        except Exception as e:  # noqa: BLE001
            r.sub[f"{prefix}ide.create"] = f"FAIL: {type(e).__name__}: {e}"
            r.note(traceback.format_exc())
            results.append(r)
            save()
            continue
        if C.is_website(pl):
            for fam in FAMILIES:
                if fam in checks:
                    r.sub[f"{prefix}{fam}.all"] = "SKIP: web sites use the web workspace (not covered here)"
            results.append(r)
            save()
            continue
        try:
            host.open_project(folder)
        except Exception as e:  # noqa: BLE001
            r.sub[f"{prefix}ide.open"] = f"FAIL: open_project: {type(e).__name__}: {e}"
            r.note(traceback.format_exc())
            results.append(r)
            save()
            continue
        mods = {}
        if "intellisense" in checks:
            from . import intellisense
            mods["intellisense"] = intellisense
        if "designer" in checks:
            from . import designer
            mods["designer"] = designer
        if "debug" in checks:
            from . import debug
            mods["debug"] = debug
        for fam, mod in mods.items():
            before = dict(r.sub)
            try:
                mod.run(host, r, pl, project, folder)
            except Exception as e:  # noqa: BLE001
                r.sub[f"{fam}.error"] = f"FAIL: {type(e).__name__}: {e}"
                r.note(traceback.format_exc())
            if prefix:                                  # frozen run: keep the keys apart
                new = {k: v for k, v in r.sub.items() if k not in before}
                for k in new:
                    r.sub.pop(k)
                r.sub.update({prefix + k: v for k, v in new.items()})
        if "run" in checks:
            from .pipeline import step_run
            try:
                step_run(r, pl, project, folder, type("A", (), {"timeout": 25, "build_timeout": 900})())
            except Exception as e:  # noqa: BLE001
                r.run = f"FAIL: {type(e).__name__}: {e}"
            if prefix:
                r.sub[prefix + "run.form"] = r.run
                r.run = ""
        if host.closed_dialogs:
            r.note("dialogs closed by the test: " + " | ".join(host.closed_dialogs[-5:]))
            host.closed_dialogs.clear()
        r.seconds = time.time() - t0
        results.append(r)
        print(f"    {json.dumps(r.sub)[:600]}", flush=True)
        save()
    try:
        host.close()
    except Exception:  # noqa: BLE001
        pass
    save()
    return 0
