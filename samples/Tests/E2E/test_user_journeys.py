# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Web + mobile user journeys for tools/run_tests.py (one PASS / FAIL / SKIP line per journey step).

    python samples/Tests/E2E/test_user_journeys.py [scratch folder] [web|mobile|web:php,node|mobile:flutter ...]

Default: the web journeys of the core stacks (php static node flask django fastapi) and every mobile journey.
"web:all" adds aspnet, spring, nestjs, rails, codeigniter, laravel (long; rails wants a short scratch path).
Runs Web/run_web.py and Mobile/run_mobile.py with E2E_OUT=<scratch>, reads every results.json back.
Exit code = number of failed steps."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE = ["php", "static", "node", "flask", "django", "fastapi"]
HEAVY = ["aspnet", "spring", "nestjs", "rails", "codeigniter", "laravel"]


def main() -> int:
    args = sys.argv[1:]
    scratch = Path(args.pop(0)) if args and not args[0].startswith(("web", "mobile")) else \
        Path(tempfile.gettempdir()) / "radide-e2e-journeys"
    scratch.mkdir(parents=True, exist_ok=True)
    plan = args or ["web", "mobile"]
    env = dict(os.environ, E2E_OUT=str(scratch), PYTHONIOENCODING="utf-8")
    for item in plan:
        area, _, names = item.partition(":")
        sel = [n for n in names.split(",") if n]
        if area == "web":
            stacks = CORE + HEAVY if sel == ["all"] else (sel or CORE)
            subprocess.run([sys.executable, str(HERE / "Web" / "run_web.py"), *stacks, "--out", str(scratch)], env=env)
        elif area == "mobile":
            subprocess.run([sys.executable, str(HERE / "Mobile" / "run_mobile.py"), *sel], env=env)
    fails = passes = skips = 0
    for res in sorted(scratch.glob("*-*/results.json")):
        r = json.loads(res.read_text(encoding="utf-8"))
        for s in r["steps"]:
            name = f"{r['area']}/{r['journey']}/{s['step']}"
            if s["status"] == "PASS":
                passes += 1
                print(f"PASS {name}")
            elif s["status"] == "SKIP":
                skips += 1
                print(f"SKIP {name} ({s.get('detail', '')[:200]})")
            else:
                fails += 1
                print(f"FAIL {name}  [{s.get('detail', '')[:400]}]")
    print(f"{passes}/{passes + fails} passed ({skips} skipped)")
    return min(fails, 100)


if __name__ == "__main__":
    sys.exit(main())
