# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Open / build / run / publish every example project in samples/Examples (scripting, web, game, assembly,
DOS and retro languages) through RAD IDE's own code paths and print a results table.

    .venv\\Scripts\\python samples\\Tests\\Examples\\test_examples_scripting.py [filter ...] [options]

    filter            substring of a project key, e.g.  Python  JavaScript/Notepad  Retro/
    --group G         only the examples of group module ex_G.py (python, pyweb, js, scripts, ring, lowlevel)
    --no-publish      skip Build > Publish (PyInstaller builds take a while)
    --list            print the project keys and exit

Every example is checked in its own child process (a crash or a hung GUI cannot stop the run):
open (designer loads every form, no control lost), build (the language's own build / the IDE's toolchain),
run (the program's own window appears and its main interaction works - driven through the IDE's bridge host,
Win32 messages or the emulator hooks; web stacks through HTTP requests to the dev server the test starts),
publish (Build > Publish: kind, size, Python inside or not).  Only processes the test started are closed.

The table is written to results.json / results.md next to this file (rows of other runs are kept).
QSettings org/app "RADIDE-TEST-EX2" is cleared before and after; QT_QPA_PLATFORM=offscreen, RADIDE_NO_BROWSER=1.

Group modules (ex_*.py next to this file) each define EXAMPLES = {"<Language>/<Name>": {"lang": "<plugin id>",
"test": fn}} where fn(folder: Path, res: exlib.Result, opts: dict) fills res.step("open"|"build"|"run"|"publish",
ok, note) and res["size"].
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exlib  # noqa: E402

exlib.setup_env()
RESULTS = HERE / "results.json"
CHILD_TIMEOUT = int(os.environ.get("RADIDE_EX_TIMEOUT", "1500"))


def groups() -> dict[str, dict]:
    out = {}
    for p in sorted(HERE.glob("ex_*.py")):
        try:
            mod = importlib.import_module(p.stem)
        except Exception as e:  # noqa: BLE001 - a broken group must not hide the others
            print(f"FAIL cannot import {p.name}: {e}", flush=True)
            continue
        out[p.stem[3:]] = getattr(mod, "EXAMPLES", {})
    return out


def child(key: str, opts: dict) -> int:
    exlib.clear_qsettings()
    for g, examples in groups().items():
        if key in examples:
            spec = examples[key]
            res = exlib.Result(key, spec.get("lang", ""))
            res["group"] = g
            t0 = time.time()
            try:
                spec["test"](exlib.EXAMPLES / key, res, opts)
            except Exception as e:  # noqa: BLE001
                import traceback
                traceback.print_exc()
                res["notes"].append(f"exception: {e!r}"[:400])
                for k in ("open", "build", "run", "publish"):
                    if res[k] == "-":
                        res[k] = "FAIL"
                        break
            res["seconds"] = round(time.time() - t0, 1)
            exlib.emit(res)
            sys.stdout.flush()
            exlib.clear_qsettings()
            os._exit(0)          # Tk / Qt leftovers must not keep the child alive
    print(f"unknown example {key}")
    return 2


def table(rows: list[dict]) -> str:
    head = "| Project | Language | Open | Build | Run | Publish | Size | Result |\n|---|---|---|---|---|---|---|---|\n"
    return head + "".join(
        f"| {r['project']} | {r.get('language', '')} | {r['open']} | {r['build']} | {r['run']} | {r['publish']} | "
        f"{r.get('size', '-')} | {r['result']} |\n" for r in rows)


def main(argv: list[str]) -> int:
    opts = {"publish": "--no-publish" not in argv}
    if "--child" in argv:
        return child(argv[argv.index("--child") + 1], opts)
    only_group = argv[argv.index("--group") + 1] if "--group" in argv else ""
    skip = {"--group", only_group, "--no-publish", "--list"}
    filters = [a for a in argv if a not in skip and not a.startswith("--")]
    keys = []
    for g, examples in groups().items():
        if only_group and g != only_group:
            continue
        keys += [k for k in examples if not filters or any(f.lower() in k.lower() for f in filters)]
    if "--list" in argv:
        print("\n".join(keys))
        return 0
    exlib.clear_qsettings()
    old = {}
    if RESULTS.exists():
        try:
            old = {r["project"]: r for r in json.loads(RESULTS.read_text(encoding="utf-8"))}
        except (ValueError, KeyError):
            old = {}
    rows = []
    for key in keys:
        print(f"\n===== {key}", flush=True)
        cmd = [sys.executable, "-u", str(Path(__file__).resolve()), "--child", key] + \
              ([] if opts["publish"] else ["--no-publish"])
        row = None
        try:
            p = subprocess.Popen(cmd, cwd=str(exlib.ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding="utf-8", errors="replace")
            t_end = time.time() + CHILD_TIMEOUT
            assert p.stdout is not None
            for line in p.stdout:
                if line.startswith("@@RESULT@@"):
                    row = json.loads(line[len("@@RESULT@@"):])
                else:
                    print("  " + line.rstrip(), flush=True)
                if time.time() > t_end:
                    break
            try:
                p.wait(timeout=30)
            except subprocess.TimeoutExpired:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
        except Exception as e:  # noqa: BLE001
            print(f"  runner error: {e}")
        if row is None:
            row = exlib.Result(key, "").finish()
            row["result"] = "FAIL"
            row["notes"].append("child process gave no result (crash or timeout)")
        if not opts["publish"] and key in old and row.get("publish") == "-":
            row["publish"], row["size"] = old[key].get("publish", "-"), old[key].get("size", "-")
            row["notes"].append("publish: kept from an earlier run")
        old[key] = row
        rows.append(row)
    latest = {}                        # other runs (parallel groups) may have written rows meanwhile
    if RESULTS.exists():
        try:
            latest = {r["project"]: r for r in json.loads(RESULTS.read_text(encoding="utf-8"))}
        except (ValueError, KeyError):
            latest = {}
    latest.update({r["project"]: r for r in rows})
    known = {k for ex in groups().values() for k in ex}
    all_rows = sorted((r for k, r in latest.items() if k in known), key=lambda r: r["project"])
    RESULTS.write_text(json.dumps(all_rows, indent=1, ensure_ascii=False), encoding="utf-8")
    (HERE / "results.md").write_text("# Example projects - results\n\n" + table(all_rows), encoding="utf-8")
    print("\n" + table(rows))
    exlib.clear_qsettings()
    bad = [r["project"] for r in rows if r["result"] != "ok"]
    print(f"{len(rows) - len(bad)}/{len(rows)} examples passed" + (f"; failed: {', '.join(bad)}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
