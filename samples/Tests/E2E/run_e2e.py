"""End-to-end user journeys against the REAL frozen RAD IDE (RADIDE.exe), driven through the automation channel.

    python samples/Tests/E2E/run_e2e.py <scratch> --onedir <build>/dist/RADIDE [--setup RADIDE-x-setup-win64.exe]
                                        [--only J1,J2,...] [--langs vb,python-tk,...] [--source]

Everything runs on a hidden Win32 desktop (nothing appears on the user's screen), the IDE offscreen, in a
portable copy of the build (settings inside the copy) or a per-user install in <scratch> (installer journeys).
Reports: <scratch>/report/<journey>/report.md|json + screenshots, and <scratch>/report/summary.md.

Journeys
  J1  fresh start (start page, clean Output) + VB6 "hello" app built entirely in the UI: Toolbox, Properties,
      double-click -> handler, IntelliSense, F5, typing + clicking in the running program, stop, Build Native Exe,
      the exe runs on its own and has no Python inside
  J2  the same flow for Python Tk / Qt, C, C++, C#, Go, Rust, Java, JavaScript, TypeScript, Lua, Fortran, PHP,
      Ruby, Perl (SKIP when a toolchain is missing)
  J3  open existing projects copied from samples/VB6/Business and samples/Examples, edit, save, reopen, Events tab
  J4  Claude Code extension (cached .vsix): install, the open project is the workspace folder, Command Palette,
      fake-CLI openDiff -> Accept -> file saved (no real Claude conversation)
  J5  debugger: breakpoints in VB6 and Python handlers hit after a real click, Locals
  J6  installer: per-user install into <scratch>, start, update through Help > Check for Updates against a local
      fake release server, rollback (Install Another Version), setup while an old IDE runs, uninstall
  J7  UI language Arabic <-> English + dark theme (screenshots, leftover English strings)
  J8  designer under load: 400 controls, undo / redo, Auto Hide tool windows, View menu
Exit code = number of failed steps.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from radauto import Abort, Desktop, Report, Skip, check  # noqa: E402
import e2e_common as C  # noqa: E402

REPO = HERE.parent.parent.parent

# ------------------------------------------------------------------------------------------------ languages
VB_CODE = 'lblOut.Caption = "Hello, " & txtName.Text\nMe.Caption = "E2E-CLICK " & lblOut.Caption'


LANGS = {
    "vb": C.Lang("vb-basic", "VB6", VB_CODE, text_prop="Text", intellisense="lblOut.", publish="native"),
    "python-tk": C.Lang("python-tk", "Python Tk",
                        'self.lblOut.config(text="Hello, " + self.txtName.get())\n'
                        'self.root.title("E2E-CLICK " + self.lblOut.cget("text"))\nprint("E2E-CLICK", flush=True)',
                        intellisense="self.", publish="publish"),
    "python-qt": C.Lang("python-qt", "Python Qt",
                        'self.lblOut.setText("Hello, " + self.txtName.text())\n'
                        'self.setWindowTitle("E2E-CLICK " + self.lblOut.text())\nprint("E2E-CLICK", flush=True)',
                        intellisense="self.", publish="publish"),
    "c": C.Lang("c-bridge", "C",
                'static char b[300], t[320]; const char *n = rad_get("txtName", "Text"); int i = 0, j;\n'
                'const char *h = "Hello, "; for (j = 0; h[j]; j++) b[i++] = h[j];\n'
                'for (j = 0; n[j] && i < 280; j++) b[i++] = n[j]; b[i] = 0;\n'
                'rad_set("lblOut", "Caption", b);\n'
                'i = 0; h = "E2E-CLICK "; for (j = 0; h[j]; j++) t[i++] = h[j]; for (j = 0; b[j]; j++) t[i++] = b[j]; t[i] = 0;\n'
                'rad_set("Form1", "Caption", t);', needs=("gcc",)),
    "cpp": C.Lang("cpp-bridge", "C++",
                  'std::string s = "Hello, " + rad::get("txtName", "Text");\nrad::set("lblOut", "Caption", s);\n'
                  'rad::set("Form1", "Caption", "E2E-CLICK " + s);', needs=("g++",)),
    "csharp": C.Lang("csharp-bridge", "CSharp",
                     'lblOut.Text = "Hello, " + txtName.Text;\nSet("Form1", "Caption", "E2E-CLICK " + lblOut.Text);',
                     intellisense="lblOut.", needs=("dotnet",)),
    "go": C.Lang("go-bridge", "Go",
                 's := "Hello, " + Get("txtName", "Text")\nSet("lblOut", "Caption", s)\nSet("Form1", "Caption", "E2E-CLICK "+s)',
                 needs=("go",)),
    "rust": C.Lang("rust-bridge", "Rust",
                   'let s = format!("Hello, {}", get("txtName", "Text"));\nset("lblOut", "Caption", &s);\n'
                   'set("Form1", "Caption", &format!("E2E-CLICK {}", s));', needs=("cargo",)),
    "java": C.Lang("java-bridge", "Java",
                   'lblOut.setText("Hello, " + txtName.getText());\nset("Form1", "Caption", "E2E-CLICK " + lblOut.getText());',
                   needs=("java",)),
    "javascript": C.Lang("javascript", "JavaScript",
                         'ui.lblOut.Caption = "Hello, " + ui.txtName.Text;\nset("Form1", "Caption", "E2E-CLICK " + ui.lblOut.Caption);',
                         needs=("node",)),
    "typescript": C.Lang("typescript", "TypeScript",
                         'const s: string = "Hello, " + get("txtName", "Text");\nset("lblOut", "Caption", s);\n'
                         'set("Form1", "Caption", "E2E-CLICK " + s);', needs=("node",)),
    "lua": C.Lang("lua-bridge", "Lua",
                  'ui.lblOut.Caption = "Hello, " .. ui.txtName.Text\nrad.set("Form1", "Caption", "E2E-CLICK " .. ui.lblOut.Caption)'),
    "fortran": C.Lang("fortran-bridge", "Fortran",
                      "call rad_set('lblOut', 'Caption', 'Hello, ' // trim(rad_get('txtName', 'Text')))\n"
                      "call rad_set('Form1', 'Caption', 'E2E-CLICK Hello, ' // trim(rad_get('txtName', 'Text')))",
                      needs=("gfortran",)),
    "php": C.Lang("php", "PHP",
                  "$s = 'Hello, ' . rad_get('txtName', 'Text');\nrad_set('lblOut', 'Caption', $s);\n"
                  "rad_set('Form1', 'Caption', 'E2E-CLICK ' . $s);", needs=("php",), publish="none"),
    "ruby": C.Lang("ruby-bridge", "Ruby",
                   's = "Hello, " + ui.txtName.Text\nui.lblOut.Caption = s\nRad.set("Form1", "Caption", "E2E-CLICK " + s)',
                   needs=("ruby",), publish="none"),
    "perl": C.Lang("perl-bridge", "Perl",
                   "my $s = 'Hello, ' . rad_get('txtName', 'Text');\nrad_set('lblOut', 'Caption', $s);\n"
                   "rad_set('Form1', 'Caption', 'E2E-CLICK ' . $s);", needs=("perl",), publish="none"),
}


# ------------------------------------------------------------------------------------------------ journeys
def j1_first_start_and_vb6(env: C.Env, rep: Report):
    C.portable_copy(env, fresh=True)
    ide = None

    def start():
        nonlocal ide
        t = time.monotonic()
        ide = C.launch(env, "J1")
        rep.ide = ide
        h = ide.call("hello")
        check(h["frozen"] or env.source, f"not the frozen exe: {h}")
        check(h["portable"] or env.source, f"not portable: {h}")
        return f"{time.monotonic() - t:.0f}s, {h['version']}, python={h['python']}"
    rep.step("first start (frozen, portable, offscreen)", start, critical=True, shot=True)

    def start_page():
        tabs = ide.call("tabs")
        ws = ide.call("widgets", sel={"cls": "StartPage"}) or ide.call("widgets", sel={"text": "Recent Projects"})
        check(ws or any("start" in t.lower() for t in tabs["tabs"]), f"no start page: {tabs}")
        return tabs["tabs"]
    rep.step("start page shown", start_page)
    rep.step("no errors in Output at start", lambda: (time.sleep(5), C.no_internal_errors(ide))[1])

    def python_found():
        h = ide.call("hello")
        check(h["python"].lower().endswith("python.exe") and "radide.exe" not in h["python"].lower(),
              f"no real Python found: {h['python']}")
        return h["python"]
    rep.step("a real Python found for user programs", python_found)

    root = env.scratch / "projects" / "J1"
    root.mkdir(parents=True, exist_ok=True)
    C.hello_journey(env, ide, rep, LANGS["vb"], root)
    rep.step("no internal errors during the journey", lambda: C.no_internal_errors(ide))
    ide.quit()


def j2_languages(env: C.Env, rep: Report, langs: list[str]):
    C.portable_copy(env)
    ide = C.launch(env, "J2")
    rep.ide = ide
    root = env.scratch / "projects" / "J2"
    root.mkdir(parents=True, exist_ok=True)
    for key in langs:
        L = LANGS[key]
        try:
            C.hello_journey(env, ide, rep, L, root)
        except Abort:
            pass
        except Exception as e:  # noqa: BLE001
            rep.steps.append({"journey": rep.journey, "step": f"{L.title}: (harness)", "status": "FAIL",
                              "detail": f"{e}", "trace": traceback.format_exc()[-2000:]})
        try:                                   # never leave a program running into the next language
            if ide.call("run_state")["running"]:
                ide.call("trigger", path="Debug/Stop Debugging")
        except Exception:  # noqa: BLE001
            try:
                ide.quit()
            except Exception:  # noqa: BLE001
                pass
            ide = C.launch(env, "J2")
            rep.ide = ide
    rep.step("no internal errors in Output", lambda: C.no_internal_errors(ide))
    ide.quit()


from journeys_more import (j3_existing_projects, j5_debugger, j7_language_theme, j8_designer_load,  # noqa: E402
                           j10_two_windows)

from journey_claude import j4_claude  # noqa: E402
from journey_install import j6_install_update  # noqa: E402
from journey_fullapp import j9_customer_manager  # noqa: E402

JOURNEYS = {"J9": j9_customer_manager, "J6": j6_install_update, "J4": j4_claude, "J1": j1_first_start_and_vb6, "J2": j2_languages, "J3": j3_existing_projects, "J5": j5_debugger,
            "J7": j7_language_theme, "J8": j8_designer_load, "J10": j10_two_windows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--onedir", default="")
    ap.add_argument("--setup", default="")
    ap.add_argument("--next-setup", default="", help="the same build packaged as a higher version (J6 update)")
    ap.add_argument("--only", default="")
    ap.add_argument("--langs", default="")
    ap.add_argument("--source", action="store_true", help="drive `python -m radide` (developing journeys)")
    a = ap.parse_args(argv)
    scratch = Path(a.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    env = C.Env(scratch=scratch, onedir=Path(a.onedir) if a.onedir else None,
                setup=Path(a.setup) if a.setup else None, source=a.source, out=scratch / "report")
    env.next_setup = Path(a.next_setup) if a.next_setup else None
    if not env.source and not (env.onedir and (env.onedir / "RADIDE.exe").is_file()):
        print("need --onedir <build>/dist/RADIDE (or --source)")
        return 2
    only = [x.strip().upper() for x in a.only.split(",") if x.strip()] or sorted(JOURNEYS)
    langs = [x.strip() for x in a.langs.split(",") if x.strip()] or [k for k in LANGS if k != "vb"]
    totals = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    rows = []
    with Desktop(f"RADIDE_E2E_{os.getpid()}") as desk:
        env.desktop = desk.name
        for j in only:
            fn = JOURNEYS.get(j)
            if fn is None:
                print(f"unknown journey {j}")
                continue
            rep = Report(j, env.out / j)
            print(f"===== {j}: {fn.__doc__ or fn.__name__}", flush=True)
            try:
                fn(env, rep, langs) if j == "J2" else fn(env, rep)
            except Abort as e:
                print(f"{j} aborted at {e}", flush=True)
            except Exception as e:  # noqa: BLE001
                rep.steps.append({"journey": j, "step": "(journey crashed)", "status": "FAIL", "detail": str(e),
                                  "trace": traceback.format_exc()[-3000:]})
                print(traceback.format_exc(), flush=True)
            finally:
                if rep.ide is not None:
                    try:
                        rep.ide.quit(10)
                    except Exception:  # noqa: BLE001
                        pass
            c = rep.save()
            rows.append((j, c))
            for k in totals:
                totals[k] += c[k]
    lines = ["# RAD IDE E2E journeys", "", "| journey | PASS | FAIL | SKIP |", "|---|---|---|---|"]
    lines += [f"| {j} | {c['PASS']} | {c['FAIL']} | {c['SKIP']} |" for j, c in rows]
    lines += [f"| **total** | {totals['PASS']} | {totals['FAIL']} | {totals['SKIP']} |"]
    (env.out).mkdir(parents=True, exist_ok=True)
    (env.out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"{totals['PASS']}/{totals['PASS'] + totals['FAIL']} passed ({totals['SKIP']} skipped)")
    return totals["FAIL"]


if __name__ == "__main__":
    sys.exit(main())
