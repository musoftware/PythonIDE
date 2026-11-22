# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Run the mobile journeys one after another (each in its own process) and print the steps matrix.

    .venv\\Scripts\\python samples\\Tests\\E2E\\Mobile\\run_mobile.py [flutter expo kivy mobileforms]

E2E_OUT (default %TEMP%\\radide-e2e) receives Mobile-<journey>/{results.json, shots/, work/} and logs/<journey>.log;
the matrix is also written to <E2E_OUT>/mobile_matrix.md. Exit code = number of failed steps.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
JOURNEYS = ["flutter", "expo", "kivy", "mobileforms"]
TIMEOUT = {"flutter": 3600, "expo": 5400, "kivy": 1800, "mobileforms": 2400}


def main() -> int:
    names = [a for a in sys.argv[1:] if a in JOURNEYS] or JOURNEYS
    out = Path(os.environ.get("E2E_OUT") or Path(tempfile.gettempdir()) / "radide-e2e")
    (out / "logs").mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, E2E_OUT=str(out), PYTHONIOENCODING="utf-8")
    for n in names:
        log = out / "logs" / f"{n}.log"
        print(f"... {n} (log {log})", flush=True)
        with open(log, "w", encoding="utf-8", errors="replace") as f:
            try:
                subprocess.run([sys.executable, str(HERE / f"journey_{n}.py")], stdout=f, stderr=subprocess.STDOUT,
                               env=env, timeout=TIMEOUT[n], cwd=str(HERE.parents[3]))
            except subprocess.TimeoutExpired:
                f.write(f"\n*** timeout after {TIMEOUT[n]} s\n")
    rows, fails = [], 0
    for n in names:
        res = out / f"Mobile-{n}" / "results.json"
        if not res.exists():
            rows.append(f"| {n} | (no results - see logs/{n}.log) | | | |")
            fails += 1
            continue
        d = json.loads(res.read_text(encoding="utf-8"))
        c = d["counts"]
        fails += c["FAIL"]
        steps = ", ".join(f"{s['step']}={s['status']}" for s in d["steps"])
        rows.append(f"| {d['title']} | {c['PASS']} | {c['FAIL']} | {c['SKIP']} | {steps} |")
    table = "| Journey | PASS | FAIL | SKIP | Steps |\n|---|---|---|---|---|\n" + "\n".join(rows)
    (out / "mobile_matrix.md").write_text(table + "\n", encoding="utf-8")
    print(table)
    return fails


if __name__ == "__main__":
    sys.exit(main())
