"""Test every runnable block of the Arabic BASIC course with the IDE's own VB6 interpreter.

    python radide/tutorials/vb-basic/tools/check_lessons.py [lesson-file-substring ...] [-v]

Blocks that are tested (fenced code blocks in the lessons):
    ```vb run            a standard module (Module1.bas) started at Sub Main
    ```vb form run       a VB6 form (.frm text: Begin VB.Form ... End + its code), started as the startup form
    ```vb solution       / ```vb form solution   - the same, for exercise solutions
    ```vb exercise       starter code: only checked for syntax errors
A block may hold several files separated by lines of the form  '#file: Name.ext  (e.g. a class module).

A following ```output block is the expected Debug.Print output (compared line by line, trailing spaces
ignored).  An HTML comment just before a block gives the scripted test:
    <!-- test: {"inputs": ["5", "7"],                      InputBox answers (in order)
                "steps": [["set", "txtA", "Text", "3"],     set a property
                          ["click", "cmdAdd"],               run cmdAdd_Click
                          ["click", "cmdNum", 2],            control array element 2
                          ["event", "Timer1", "Timer"],      run Timer1_Timer
                          ["menu", "mnuFileExit"]],          run a menu item's _Click
                "expect": {"lblResult.Caption": "7"},       control properties after the steps
                "msgbox": ["Hello"],                        MsgBox prompts (in order)
                "error": 11} -->                            the program must stop with this run-time error

Each block runs in its own process (a child of this script), headless: MsgBox/InputBox are scripted and the
form windows are hidden.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
COURSE = HERE.parent
REPO = COURSE.parents[2]

FENCE = re.compile(r"^```([^\n`]*)\n(.*?)^```[ \t]*$", re.M | re.S)
TEST = re.compile(r"<!--\s*test:\s*(\{.*?\})\s*-->\s*$", re.S)


def blocks(md: str):
    """Yield (info, code, test-spec, expected-output or None, line)."""
    found = list(FENCE.finditer(md))
    for i, m in enumerate(found):
        info = m.group(1).strip().split()
        if not info or info[0] not in ("vb", "basic", "vba"):
            continue
        kind = [w for w in info[1:]]
        before = md[:m.start()].rstrip()
        spec = None
        k = before.rfind("<!--")
        t = TEST.match(before[k:]) if k >= 0 and before.endswith("-->") else None
        if t:
            spec = json.loads(t.group(1))
        expected = None
        if i + 1 < len(found):
            nxt = found[i + 1]
            between = md[m.end():nxt.start()]
            if nxt.group(1).strip() == "output" and len(between.strip().splitlines()) <= 3:
                expected = nxt.group(2)
        yield kind, m.group(2), spec, expected, md.count("\n", 0, m.start()) + 1


def split_files(code: str, default: str) -> dict[str, str]:
    files: dict[str, str] = {}
    name = default
    cur: list[str] = []
    for ln in code.splitlines():
        mm = re.match(r"\s*'#file:\s*(\S+)\s*$", ln)
        if mm:
            if any(x.strip() for x in cur):
                files[name] = "\n".join(cur) + "\n"
            name, cur = mm.group(1), []
            continue
        cur.append(ln)
    if any(x.strip() for x in cur):
        files[name] = "\n".join(cur) + "\n"
    return files


def make_project(kind: list[str], code: str, dest: Path) -> None:
    """Turn a block into a RAD IDE vb-basic project (the same thing the tutorial runner does)."""
    sys.path.insert(0, str(REPO))
    from radide.importers.vb6_import import _FrmConverter, parse_frm
    from radide.importers.python_import import ImportReport
    from radide.model import Project
    dest.mkdir(parents=True, exist_ok=True)
    is_form = "form" in kind
    files = split_files(code, "Form1.frm" if is_form else "Module1.bas")
    project = Project(dest, "Lesson", "vb-basic")
    for name, text in files.items():
        if name.lower().endswith(".frm"):
            root, body = parse_frm(text)
            form = _FrmConverter(ImportReport(), name).convert(root)
            form.save(project.form_path(form.name))
            (dest / f"{form.name}.bas").write_text(body, encoding="utf-8")
            project.forms.append(form.name)
            if not project.startup:
                project.startup = form.name
        else:
            (dest / name).write_text(text, encoding="utf-8")
            project.modules.append(name)
    if not project.startup:
        project.startup = "Sub Main"
    project.save()


# ------------------------------------------------------------------ child: run one project headless
def child(folder: str, spec_path: str, result_path: str) -> None:
    import io
    sys.path.insert(0, str(REPO))
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    from radide.runtimes import vbrun
    from radide.runtimes.vbinterp import EndProgram, VBRuntimeError
    out = io.StringIO()
    real_stdout = sys.stdout
    sys.stdout = out
    result = {"msgbox": [], "error": None, "values": {}, "fatal": None}
    inputs = list(spec.get("inputs", []))

    def finish(code=0):
        sys.stdout = real_stdout
        result["output"] = out.getvalue()
        Path(result_path).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        os._exit(code)

    rt = vbrun.Runtime(Path(folder))
    rt.interp.output = lambda s: print(s)

    def msgbox(prompt, buttons, title):
        result["msgbox"].append(str(prompt))
        answers = spec.get("msgbox_answers", [])
        return answers.pop(0) if answers else (6 if buttons & 7 in (3, 4) else 1)

    def inputbox(prompt, title, default):
        return inputs.pop(0) if inputs else (default or "")

    def runtime_error(ex: VBRuntimeError):
        result["error"] = {"number": ex.number, "description": str(ex.description), "line": ex.line}
        finish()

    def fatal(text, filename="", line=0):
        result["fatal"] = text
        finish()

    rt.msgbox, rt.inputbox, rt.runtime_error, rt.fatal = msgbox, inputbox, runtime_error, fatal
    rt.end = finish
    vbrun.messagebox.showerror = lambda *a, **k: None
    try:
        rt.load()
        start = (rt.project.startup or "").lower()
        if start not in rt.forms:
            found = rt.interp.find_proc("main", None)
            if found is None:
                fatal("No Sub Main")
            rt.interp.call_proc(found[0], found[1], [])
        else:
            vf = rt.forms[start]
            rt.startup_form = vf
            vf.load()
            vf.vb_call("show", [])
        if rt.root is not None:
            try:
                rt.root.attributes("-alpha", 0.0)
            except Exception:  # noqa: BLE001
                pass
            rt.root.update()
        for step in spec.get("steps", []):
            vf = rt.startup_form or (next(iter(rt.forms.values())) if rt.forms else None)
            op = step[0]
            if op == "set":
                vf.vb_get(step[1].lower()).vb_set(step[2].lower(), step[3])
            elif op in ("click", "event", "menu"):
                ev = "Click" if op != "event" else step[2]
                idx = step[2] if op == "click" and len(step) > 2 else (step[3] if len(step) > 3 else None)
                rt.run_handler(vf, f"{step[1]}_{ev}", "Click" if ev == "Click" else ev, index=idx)
            elif op == "form":                       # switch to another loaded form: ["form", "Form2"]
                rt.startup_form = rt.forms[step[1].lower()]
            if rt.root is not None:
                rt.root.update()
        for key in spec.get("expect", {}):
            ctl, _, prop = key.partition(".")
            vf = rt.startup_form or next(f for f in rt.forms.values() if f.loaded)
            obj = vf.vb_get(ctl.lower())
            result["values"][key] = str(obj.vb_get(prop.lower()))
    except EndProgram:
        finish()
    except VBRuntimeError as ex:
        runtime_error(ex)
    except SystemExit:
        finish()
    except Exception as ex:  # noqa: BLE001
        import traceback
        result["fatal"] = "harness: " + "".join(traceback.format_exception(ex))[-1500:]
    finish()


# ------------------------------------------------------------------ parent
def check_syntax(code: str, kind: list[str]) -> str | None:
    sys.path.insert(0, str(REPO))
    from radide.importers.vb6_import import parse_frm
    from radide.runtimes.vbparse import VBSyntaxError, parse_module
    for name, text in split_files(code, "Form1.frm" if "form" in kind else "Module1.bas").items():
        if name.lower().endswith(".frm"):
            _, text = parse_frm(text)
        try:
            parse_module(text, Path(name).stem, name)
        except VBSyntaxError as e:
            return f"{name}({e.line}): {e.msg}"
    return None


def norm(text: str) -> list[str]:
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def run_block(kind, code, spec, expected, work: Path) -> list[str]:
    problems = []
    tested = spec is not None
    spec = spec or {}
    if "exercise" in kind:
        e = check_syntax(code, kind)
        return [e] if e else []
    make_project(kind, code, work)
    spec_path, res_path = work / "_spec.json", work / "_result.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    try:
        subprocess.run([sys.executable, __file__, "--child", str(work), str(spec_path), str(res_path)],
                       timeout=spec.get("timeout", 30), capture_output=True, cwd=str(work))
    except subprocess.TimeoutExpired:
        return ["timeout (endless loop?)"]
    if not res_path.exists():
        return ["no result (crash)"]
    r = json.loads(res_path.read_text(encoding="utf-8"))
    if os.environ.get("VBCOURSE_SHOW"):
        print(json.dumps(r, ensure_ascii=False, indent=1))
    if r.get("fatal"):
        problems.append("fatal: " + r["fatal"])
    want_err = spec.get("error")
    got_err = r.get("error")
    if want_err is None and got_err:
        problems.append(f"run-time error {got_err['number']}: {got_err['description']} (line {got_err['line']})")
    elif want_err is not None and (not got_err or got_err["number"] != want_err):
        problems.append(f"expected run-time error {want_err}, got {got_err}")
    if expected is not None and norm(r.get("output", "")) != norm(expected):
        problems.append("output differs:\n--- expected\n" + "\n".join(norm(expected)) +
                        "\n--- got\n" + "\n".join(norm(r.get("output", ""))))
    if "msgbox" in spec and r["msgbox"] != spec["msgbox"]:
        problems.append(f"MsgBox: expected {spec['msgbox']!r}, got {r['msgbox']!r}")
    for k, v in spec.get("expect", {}).items():
        if r["values"].get(k) != str(v):
            problems.append(f"{k}: expected {v!r}, got {r['values'].get(k)!r}")
    if ("run" in kind or "solution" in kind) and expected is None and not tested:
        problems.append("untested block: add an ```output block or a <!-- test: --> comment")
    return problems


def main(argv: list[str]) -> int:
    if argv[:1] == ["--child"]:
        child(*argv[1:4])
        return 0
    verbose = "-v" in argv
    filters = [a for a in argv if not a.startswith("-")]
    files = sorted(COURSE.glob("[0-9][0-9]-*.md"))
    if filters and all(Path(x).is_file() for x in filters):      # explicit .md files (e.g. drafts)
        files = [Path(x) for x in filters]
    elif filters:
        files = [f for f in files if any(x in f.name for x in filters)]
    total = failed = 0
    tmp = Path(tempfile.mkdtemp(prefix="vbcourse-"))
    for f in files:
        md = f.read_text(encoding="utf-8")
        for n, (kind, code, spec, expected, line) in enumerate(blocks(md)):
            if not ({"run", "solution", "exercise"} & set(kind)):
                continue
            total += 1
            probs = run_block(kind, code, spec, expected, tmp / f"{f.stem}_{n}")
            if probs:
                failed += 1
                print(f"FAIL {f.name}:{line} [{' '.join(kind)}]")
                for p in probs:
                    print("    " + p.replace("\n", "\n    "))
            elif verbose:
                print(f"ok   {f.name}:{line} [{' '.join(kind)}]")
    print(f"{total - failed}/{total} blocks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
