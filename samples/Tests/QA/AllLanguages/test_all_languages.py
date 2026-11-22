"""End-to-end QA matrix: every project language / template of the New Project dialog, every check family.

    .venv\\Scripts\\python samples/Tests/QA/AllLanguages/test_all_languages.py [options]

Each language plugin (radide/languages; foreign-only plugins excluded) gets its default template (or all with
--all-templates), created with the same code as File > New Project. Languages with forms get Button1 +
TextBox1 ("QA") + Label1 and a Button1_Click handler: Label1.Text = "Hi " + TextBox1.Text; Form1.Text = Label1.Text.

Check families (--check, default: all but frozen), one module each in checks/:

  build         checks/pipeline.py      the language's build command (plugin.build_command / py_compile)
  run           checks/pipeline.py      the IDE run spec; a form's window is clicked (posted Win32 messages to
                                        the program's own window), its title must become "Hi QA"; console
                                        programs must exit 0; web sites: DevServer + HTTP GET
  publish       checks/pipeline.py      Build > Publish (radide.deploy.build.build, kind auto = native where a
                                        native builder exists) and the published exe run the same way
  intellisense  checks/intellisense.py  completion (plugin + editor/LSP + typing "M" in Monaco), hover,
                                        signature, definition, diagnostics in the Error List, formatting
  designer      checks/designer.py      add / rename a control, double-click handler stub, Properties > Events,
                                        save + reopen
  debug         checks/debug.py         breakpoint in Button1_Click hit, Locals, Step Over, Continue / Stop
  frozen        checks/frozen.py        intellisense + designer + run inside the release RADIDE.exe
                                        (RADIDE_AS_PYTHON=1); --frozen-exe to choose the build

The IDE families run in a child process (one offscreen MainWindow, QSettings org "RADIDE-TEST-QA", cleared
before/after). Missing toolchains the IDE cannot get by itself are SKIP, not FAIL. Only processes started by the
test are closed or killed. Prints a summary table and writes results.json (merged with earlier runs).

Options:
  --lang a,b          language ids, fnmatch patterns ("asm-*") or id:template; --only is the same
  --skip a,b          language ids to leave out
  --group NAME        a New Project dialog group (Native, Web, Assembly, ...)
  --check a,b         check families (default build,run,publish,intellisense,designer,debug; "all" adds frozen)
  --all-templates     every template of languages with their own templates
  --no-published-run  publish without running the exe
  --scratch DIR / --json FILE / --timeout SEC / --frozen-exe PATH / --frozen-checks a,b / --list
Exit code = number of FAIL results.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(HERE.parents[3]))
sys.path.insert(0, str(HERE))
if os.environ.get("QA_CHILD_LOG"):          # frozen child: the windowed exe has no console
    sys.stdout = sys.stderr = open(os.environ["QA_CHILD_LOG"], "w", encoding="utf-8", buffering=1)

from checks import common as C  # noqa: E402

PIPELINE = ("build", "run", "publish")
IDE_FAMILIES = ("intellisense", "designer", "debug")
DEFAULT_CHECKS = PIPELINE + IDE_FAMILIES
ALL_CHECKS = DEFAULT_CHECKS + ("frozen",)


def parse_cases(args) -> list[tuple[str, str]]:
    pl = C.plugins()
    order = [pid for ids in C.groups().values() for pid in ids if pid in pl]
    order += sorted(pid for pid in pl if pid not in order)
    if args.group:
        g = {k.lower(): v for k, v in C.groups().items()}.get(args.group.lower(), [])
        order = [x for x in order if x in g]
    explicit_tpl: dict[str, str] = {}
    if args.lang:
        pats = []
        for x in (s.strip() for s in args.lang.split(",")):
            if not x:
                continue
            if ":" in x:
                x, t = x.split(":", 1)
                explicit_tpl[x] = t
            pats.append(x)
        order = [x for x in order if any(fnmatch.fnmatch(x, pt) for pt in pats)]
    if args.skip:
        pats = [x.strip() for x in args.skip.split(",") if x.strip()]
        order = [x for x in order if not any(fnmatch.fnmatch(x, pt) for pt in pats)]
    cases = []
    for pid in order:
        if pid in explicit_tpl:
            cases.append((pid, explicit_tpl[pid]))
            continue
        tps = C.templates_of(pl[pid])
        cases += [(pid, t) for t in (tps if args.all_templates else tps[:1])]
    return cases


def parse_checks(text: str) -> set[str]:
    if not text:
        return set(DEFAULT_CHECKS)
    out = set()
    for x in (s.strip().lower() for s in text.split(",")):
        if x == "all":
            out |= set(ALL_CHECKS)
        elif x in ALL_CHECKS or x == "run":
            out.add(x)
        elif x:
            raise SystemExit(f"unknown check family: {x} (known: {', '.join(ALL_CHECKS)})")
    return out


# ---------------------------------------------------------------------------------------------- table
def short(s: str, n: int) -> str:
    s = (s or "").replace("\n", " ")
    return s if len(s) <= n else s[:n - 1] + "~"


def table(results: list[C.Result]) -> str:
    st = C.status
    head = ("language", "template", "build", "run", "publish kind", "exe size", "python?", "intelli", "designer",
            "debug", "frozen", "result")
    rows = [head]
    for r in results:
        size = f"{r.exe_size / 1024:,.0f} KB" if r.exe_size else ""
        if r.dist_size and r.dist_size != r.exe_size:
            size += f" ({r.dist_size / 1048576:,.1f} MB dir)"
        pub = r.publish_kind or ""
        if st(r.publish) in ("FAIL", "SKIP", "n/a"):
            pub = f"{pub} {st(r.publish)}".strip()
        run = st(r.run) + ("/" + st(r.published_run) if r.published_run else "")
        rows.append((r.language, short(r.template, 16), st(r.build), run, short(pub, 30), size, r.python_inside,
                     st(r.intellisense), st(r.designer), st(r.debug), st(r.frozen), r.result))
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(head))]
    lines = [" | ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)) for row in rows]
    lines.insert(1, "-+-".join("-" * w for w in widths))
    return "\n".join(lines)


def details(results: list[C.Result]) -> str:
    out = []
    for r in results:
        bad = [(k, v) for k, v in [("create", r.create), ("build", r.build), ("run", r.run), ("publish", r.publish),
                                   ("published_run", r.published_run), *sorted(r.sub.items())]
               if C.status(v) == "FAIL"]
        for k, v in bad:
            out.append(f"  FAIL {r.language} {k}: {short(v, 300)}")
    return "\n".join(out)


# ---------------------------------------------------------------------------------------------- main
def settings_clear():
    try:
        from PyQt6.QtCore import QSettings
        QSettings(C.ORG, C.APP).clear()
    except Exception:  # noqa: BLE001
        pass


def run_ide_child(cases, checks, scratch: Path, prefix: str = "", exe: str | None = None) -> dict:
    """IDE families in a child process; returns {(lang, tpl): Result dict}."""
    out = scratch / f"ide_results{'_' + prefix.strip('.') if prefix else ''}.json"
    out.unlink(missing_ok=True)
    argv = [exe or sys.executable, str(Path(__file__).resolve()), "--ide-child", "--lang",
            ",".join(f"{l}:{t}" for l, t in cases), "--check", ",".join(sorted(checks)),
            "--scratch", str(scratch / "ide"), "--json", str(out)]
    if prefix:
        argv += ["--prefix", prefix]
    env = C.child_env(None)
    subprocess.run(argv, cwd=str(scratch), env=env)
    res = {}
    if out.is_file():
        for d in json.loads(out.read_text(encoding="utf-8")).get("results", []):
            res[(d["language"], d["template"])] = d
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lang", "--only", dest="lang", default="")
    ap.add_argument("--skip", default="")
    ap.add_argument("--group", default="")
    ap.add_argument("--check", default="")
    ap.add_argument("--all-templates", action="store_true")
    ap.add_argument("--no-run", action="store_true")
    ap.add_argument("--no-publish", action="store_true")
    ap.add_argument("--no-published-run", action="store_true")
    ap.add_argument("--scratch", default=str(Path(tempfile.gettempdir()) / "radide_qa_all_languages"))
    ap.add_argument("--json", default="")
    ap.add_argument("--timeout", type=float, default=25)
    ap.add_argument("--build-timeout", type=float, default=900)
    ap.add_argument("--frozen-exe", default="")
    ap.add_argument("--frozen-checks", default="intellisense,designer,run")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--ide-child", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--prefix", default="", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    checks = parse_checks(args.check)
    scratch = Path(args.scratch)
    scratch.mkdir(parents=True, exist_ok=True)

    if args.ide_child:                    # child: one offscreen IDE for all the cases
        from checks import ide_child
        cases = [tuple(x.split(":", 1)) if ":" in x else (x, "") for x in args.lang.split(",") if x]
        return ide_child.run(cases, checks, scratch, Path(args.json), args.prefix)

    from PyQt6.QtCore import QCoreApplication
    QCoreApplication.setOrganizationName(C.ORG)
    QCoreApplication.setApplicationName(C.APP)
    app = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])  # noqa: F841 - DevServer signals
    settings_clear()
    cases = parse_cases(args)
    if args.list:
        for pid, t in cases:
            print(f"{pid:22} {t}")
        return 0
    out_json = Path(args.json) if args.json else scratch / "results.json"
    old = []
    if out_json.is_file():
        try:
            old = json.loads(out_json.read_text(encoding="utf-8")).get("results", [])
        except (OSError, ValueError):
            old = []
    pl_all = C.plugins()
    results: list[C.Result] = []

    def save():
        merged = {(d["language"], d["template"]): d for d in old}
        merged.update({(x.language, x.template): asdict(x) for x in results})
        out_json.write_text(json.dumps({"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                                        "checks": sorted(checks), "results": list(merged.values())}, indent=2),
                            encoding="utf-8")

    from checks import pipeline
    try:
        for i, (pid, t) in enumerate(cases, 1):
            pl = pl_all[pid]
            r = C.Result(pid, t, pl.display_name)
            results.append(r)
            t0 = time.time()
            if not checks & set(PIPELINE):
                continue
            print(f"[{i}/{len(cases)}] {pid} ({t}) ...", flush=True)
            folder = scratch / f"{pid}__{t or 'default'}"
            shutil.rmtree(folder, ignore_errors=True)
            try:
                project = C.create(folder, "QA" + "".join(ch for ch in pid.title() if ch.isalnum()), pl, t)
                if C.has_form_code(pl) and getattr(project, "forms", None) and "Form1" in project.forms:
                    C.add_click_form(project, pl)
                    r.create = "PASS (form + Click handler)"
                else:
                    r.create = "PASS"
            except Exception as e:  # noqa: BLE001
                r.create = f"FAIL: {type(e).__name__}: {e}"
                r.note(traceback.format_exc())
                r.result = C.overall(r)
                save()
                continue
            pipeline.run(r, pl, project, folder, args, scratch, checks)
            r.seconds = time.time() - t0
            r.result = C.overall(r)
            print(f"    build={short(r.build, 90)}\n    run={short(r.run, 150)}\n    publish={r.publish_kind} "
                  f"{short(r.publish, 110)} | exe={r.exe_size:,} py={r.python_inside}\n    published run="
                  f"{short(r.published_run, 150)}\n    => {r.result} ({r.seconds:.0f}s)", flush=True)
            save()
        ide = checks & set(IDE_FAMILIES)
        if ide:
            print(f"------ IDE checks ({', '.join(sorted(ide))}) in a child process ...", flush=True)
            got = run_ide_child(cases, ide, scratch)
            for r in results:
                d = got.get((r.language, r.template))
                if d is None:
                    r.sub["ide.child"] = "FAIL: the IDE child process gave no result (crashed?)"
                    continue
                r.sub.update(d.get("sub", {}))
                r.notes += d.get("notes", [])
            save()
        if "frozen" in checks:
            from checks import frozen
            exe = frozen.find_build(args.frozen_exe)
            if exe is None:
                for r in results:
                    r.frozen = "SKIP: no release build found (tools/build_ide_release.py; --frozen-exe)"
            else:
                print(f"------ frozen checks in {exe} ...", flush=True)
                got = frozen.run(cases, {x.strip() for x in args.frozen_checks.split(",") if x.strip()},
                                 scratch, exe)
                for r in results:
                    d = got.get((r.language, r.template), {})
                    notes = d.pop("__notes__", [])
                    r.sub.update(d)
                    r.notes += [f"[frozen] {n}" for n in notes]
        for r in results:
            for fam in IDE_FAMILIES:
                setattr(r, fam, C.summarize(r.sub, fam))
            fz = {k[len("frozen."):]: v for k, v in r.sub.items() if k.startswith("frozen.")}
            if fz:
                fails = [k for k, v in fz.items() if C.status(v) == "FAIL"]
                r.frozen = ("FAIL: " + ", ".join(fails)) if fails else \
                    (f"PASS ({sum(C.status(v) == 'PASS' for v in fz.values())}/{len(fz)})"
                     if any(C.status(v) == "PASS" for v in fz.values()) else "SKIP")
            r.result = C.overall(r)
        save()
    finally:
        settings_clear()
    print()
    print(table(results))
    det = details(results)
    if det:
        print("\nFailures:\n" + det)
    fails = sum(r.result == "FAIL" for r in results)
    print(f"\n{len(results)} cases: {sum(r.result.startswith('PASS') for r in results)} PASS, {fails} FAIL, "
          f"{sum(r.result == 'SKIP' for r in results)} SKIP.  Results: {out_json}")
    return fails


if __name__ == "__main__":
    sys.exit(main())
