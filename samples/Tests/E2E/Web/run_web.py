# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Run the web journeys (journey_web.py <stack>) one after another and write the journeys x steps matrix.

    .venv\\Scripts\\python samples\\Tests\\E2E\\Web\\run_web.py [stack ...] [--out DIR] [--timeout 3600]

Default stacks: every stacks/<name>.py. Each journey runs in its own process (E2E_OUT=<out>); its results.json is
read back. Writes <out>/web_matrix.md and <out>/web_matrix.json; exit code = number of failed steps.
Rails needs a short output folder (gems with long paths fail under MAX_PATH): use --out C:\\Temp\\rade2f or similar.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = ["toolchain", "new project", "code", "database", "design", "run", "pages", "login", "crud", "api", "arabic",
         "preview", "debug", "intellisense", "publish folder", "publish ftp", "published run"]
ABBR = {"PASS": "PASS", "FAIL": "**FAIL**", "SKIP": "SKIP"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stacks", nargs="*")
    ap.add_argument("--out", default=os.environ.get("E2E_OUT") or str(Path(tempfile.gettempdir()) / "radide-e2e"))
    ap.add_argument("--timeout", type=int, default=3600)
    a = ap.parse_args()
    stacks = a.stacks or sorted(p.stem for p in (HERE / "stacks").glob("*.py") if not p.stem.startswith("_"))
    out = Path(a.out)
    (out / "logs").mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, E2E_OUT=str(out))
    rows = {}
    for s in stacks:
        t = time.time()
        log = out / "logs" / f"{s}.log"
        print(f"=== {s} ...", flush=True)
        with open(log, "w", encoding="utf-8", errors="replace") as f:
            try:
                subprocess.run([sys.executable, str(HERE / "journey_web.py"), s], env=env, stdout=f,
                               stderr=subprocess.STDOUT, timeout=a.timeout)
            except subprocess.TimeoutExpired:
                f.write(f"\nTIMEOUT after {a.timeout}s\n")
        res = out / f"Web-{s}" / "results.json"
        if res.exists() and res.stat().st_mtime >= t:
            rows[s] = json.loads(res.read_text(encoding="utf-8"))
        else:
            rows[s] = {"counts": {"PASS": 0, "FAIL": 1, "SKIP": 0}, "steps": [
                {"step": "journey", "status": "FAIL", "detail": f"no results (see {log})"}]}
        print(f"    {rows[s]['counts']}  ({round(time.time() - t)} s)", flush=True)
    total = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    lines = ["# Web journeys - RAD Store per stack", "", "| step | " + " | ".join(stacks) + " |",
             "|---|" + "---|" * len(stacks)]
    by = {s: {x["step"]: x["status"] for x in rows[s]["steps"]} for s in stacks}
    for st in STEPS:
        lines.append(f"| {st} | " + " | ".join(ABBR.get(by[s].get(st, "-"), "-") for s in stacks) + " |")
    lines.append("| **PASS / FAIL / SKIP** | " + " | ".join(
        f"{rows[s]['counts']['PASS']} / {rows[s]['counts']['FAIL']} / {rows[s]['counts']['SKIP']}" for s in stacks)
        + " |")
    for s in stacks:
        for k in total:
            total[k] += rows[s]["counts"][k]
    lines += ["", f"Total: {total['PASS']} passed, {total['FAIL']} failed, {total['SKIP']} skipped", "",
              "## Not passed", ""]
    for s in stacks:
        for x in rows[s]["steps"]:
            if x["status"] != "PASS":
                lines.append(f"- **{s} / {x['step']}** {x['status']}: {str(x.get('detail', ''))[:300]}")
    (out / "web_matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "web_matrix.json").write_text(json.dumps({"total": total, "stacks": {s: rows[s]["counts"] for s in stacks}},
                                                    indent=1), encoding="utf-8")
    print("\n".join(lines))
    sys.exit(min(total["FAIL"], 100))


if __name__ == "__main__":
    main()
