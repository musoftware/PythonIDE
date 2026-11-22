"""Debugger matrix: every language the IDE debugs (forms) x every debugger feature, in the real IDE.

    .venv\\Scripts\\python samples\\Tests\\Debugger\\test_debug_matrix.py                    # all languages
    .venv\\Scripts\\python samples\\Tests\\Debugger\\test_debug_matrix.py vb-basic,c-bridge  # some
    .venv\\Scripts\\python samples\\Tests\\Debugger\\test_debug_matrix.py --table <scratch>  # table of an earlier run

It runs the QA matrix's "debug" family (samples/Tests/QA/AllLanguages/checks/debug.py) - one offscreen IDE,
a project per language created like File > New Project, F5 with a breakpoint in Button1_Click, a REAL click on
the program's window, then Locals / Call Stack / Immediate / Watch, Step Over / Into / Out, Continue,
conditional breakpoint, hit count, Stop, and a second run that throws in the handler (Break on Exceptions) -
and prints a language x feature table (P = PASS, F = FAIL, S = SKIP, . = not run).

Environment: QSettings organization RADIDE-TEST-DBG (cleared before / after), scratch in %TEMP%. Debuggers come
from the IDE's own locators (gdb, netcoredbg, js-debug, dlv, Dart SDK, JDK, PSES, Strawberry Perl, ...); a
missing one makes that language's steps fail with the reason in the details. Only processes the test started
are closed. Exit code = number of FAIL steps.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
QA = REPO / "samples" / "Tests" / "QA" / "AllLanguages" / "test_all_languages.py"

LANGS = ["vb-basic", "python-tk", "python-qt", "ring-qt", "csharp-bridge", "powershell-bridge", "java-bridge",
         "javascript", "typescript", "c-bridge", "cpp-bridge", "rust-bridge", "fortran-bridge", "go-bridge",
         "lua-bridge", "ruby-bridge", "perl-bridge", "dart-bridge"]
FEATURES = ["start", "breakpoint", "locals", "callstack", "immediate", "watch", "step_over", "step_into",
            "step_out", "continue", "condition", "hitcount", "stop", "exception"]
SHORT = {"breakpoint": "bp", "callstack": "stack", "immediate": "immed", "step_over": "over", "step_into": "into",
         "step_out": "out", "continue": "cont", "condition": "cond", "hitcount": "hits", "exception": "exc"}


def table(results: list[dict]) -> tuple[str, int]:
    heads = [SHORT.get(f, f) for f in FEATURES]
    w = max(len(r["language"]) for r in results) if results else 10
    lines = ["language".ljust(w) + " | " + " ".join(h.ljust(5) for h in heads) + " | pass"]
    lines.append("-" * len(lines[0]))
    fails = 0
    details = []
    for r in results:
        sub = {k.split(".", 1)[1]: v for k, v in r.get("sub", {}).items() if k.startswith("debug.")}
        cells, n = [], 0
        for f in FEATURES:
            v = sub.get(f, "")
            c = "P" if v.startswith("PASS") else "F" if v.startswith("FAIL") else "S" if v.startswith("SKIP") else "."
            n += c == "P"
            fails += c == "F"
            cells.append(c.ljust(5))
            if c in "FS":
                details.append(f"  {r['language']} {f}: {v[:300]}")
        for k, v in sub.items():
            if k not in FEATURES and v.startswith("FAIL"):
                fails += 1
                details.append(f"  {r['language']} {k}: {v[:300]}")
        lines.append(r["language"].ljust(w) + " | " + " ".join(cells) + f" | {n}/{len(FEATURES)}")
    return "\n".join(lines + ([""] + details if details else [])), fails


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--table" in sys.argv:
        scratch = Path(args[0]) if args else Path(tempfile.gettempdir()) / "radide_debug_matrix"
        res = json.loads((scratch / "ide_results.json").read_text(encoding="utf-8"))["results"]
        text, fails = table(res)
        print(text)
        return fails
    langs = args[0] if args else ",".join(LANGS)
    scratch = Path(tempfile.gettempdir()) / "radide_debug_matrix"
    env = dict(os.environ, RADIDE_QA_ORG="RADIDE-TEST-DBG", PYTHONIOENCODING="utf-8", RADIDE_NO_BROWSER="1")
    env.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-gpu-compositing")
    subprocess.run([sys.executable, str(QA), "--lang", langs, "--check", "debug", "--scratch", str(scratch)],
                   cwd=str(REPO), env=env)
    res = json.loads((scratch / "ide_results.json").read_text(encoding="utf-8"))["results"]
    text, fails = table(res)
    print("\n" + text)
    return fails


if __name__ == "__main__":
    sys.exit(main())
