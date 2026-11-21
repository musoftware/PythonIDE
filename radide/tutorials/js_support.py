"""JavaScript / TypeScript blocks of the tutorials (course "javascript", guide "node-frontend").

Block kinds (fence info strings, the shared format of vb-basic/README.md):

* ```` ```js run ```` / ```` ```ts run ````   a console program -> a "JavaScript" / "TypeScript" project without
  forms (what File > New Project > Console Application makes): ``Program.js`` / ``Program.ts``, run by Node.js
  through the IDE's own run command (``_radmain.js`` -> ``radgui.runConsole``).  ```text input`` = its stdin,
  ```text output`` = the expected output (stdout + stderr).
* ```` ```js form run ```` / ```` ```ts form run ````   ``Form1.js`` / ``Form1.ts`` of a GUI Bridge Windows Application
  (handlers ``<Control>_<Event>(e)``).  The project's Form1 gets the controls of the hidden test comment
  (``"controls": [["Button", "btnHello", {"Text": "Say hello"}], ...]``, ``"form": {"Text": ..., "Width": ...}``)
  or else the controls the code names (``ui.lblOut``, ``get("txtName", ...)``, ``function btnGo_Click``) with the
  usual prefixes (btn, txt, lbl, lst, cbo, chk, opt, tmr, prg, grp, num), laid out in a column.
* ``exercise`` / ``solution`` as in the other courses; ``// #file: name.js`` lines split a block into files
  (the other files are modules of the project, loaded before Program / Form1; ``package.json`` is just written).

Hidden ``<!-- test: {...} -->`` keys for form blocks (checked with the IDE's real GUI Bridge runtime, Tk hidden):
  ``steps``   ordered ``["set", "txtName", "Text", "Sara"]``, ``["click", "btnHello"]``,
              ``["event", "lstNames", "SelectedIndexChanged"]``, ``["tick", "tmrClock"]``
  ``expect``  ``{"lblOut.Text": "Hello Sara", "lstLog.ListCount": "3", "lstLog.List(0)": "a"}`` (``re:`` = regex)
  ``msgbox``  the expected msgbox() texts, ``inputs`` = the answers of input()
Console blocks may use ``"timeout"`` (seconds) and ``"norun"`` (only ``node --check``: servers, endless programs).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
LANGS = {"js": "js", "javascript": "js", "node": "js", "ts": "ts", "typescript": "ts"}
PLUGIN_IDS = {"js": "javascript", "ts": "typescript"}
EXT = {"js": ".js", "ts": ".ts"}
PREFIXES = (("btn", "Button"), ("cmd", "Button"), ("txt", "TextBox"), ("lbl", "Label"), ("lst", "ListBox"),
            ("cbo", "ComboBox"), ("chk", "CheckBox"), ("opt", "RadioButton"), ("tmr", "Timer"),
            ("prg", "ProgressBar"), ("grp", "GroupBox"), ("num", "NumericUpDown"), ("pic", "PictureBox"))
RX_NAME = re.compile(r"""(?:\bui\.|["'])((?:""" + "|".join(p for p, _t in PREFIXES) + r""")[A-Z]\w*)|"""
                     r"""\bfunction\s+((?:""" + "|".join(p for p, _t in PREFIXES) + r""")[A-Z]\w*)_\w+\s*\(""")
STDIN_RX = re.compile(r"process\.stdin|readFileSync\(\s*0\b|readline")


# ===================================================================== block facts
def lang_of(block) -> str:
    return LANGS.get(block.lang, block.lang)


def default_file(block) -> str:
    ext = EXT[lang_of(block)]
    return f"Form1{ext}" if block.form else f"Program{ext}"


def reads_stdin(block) -> bool:
    return not block.form and bool(STDIN_RX.search(block.code))


def node_exe() -> str | None:
    try:
        from ..languages import get_plugin
        exe = get_plugin("javascript").tool()
        if exe:
            return exe
    except Exception:  # noqa: BLE001
        pass
    return shutil.which("node")


# ===================================================================== projects
def _clean(dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)


def _ordered(files: dict[str, str], main: str) -> list[str]:
    """Code files in load order: the helper modules first, the main file (Program / Form1) last."""
    code = [f for f in files if f.lower().endswith((".js", ".ts")) and f != main]
    return code + ([main] if main in files and not main.startswith("Form1.") else [])


def make_console(files: dict[str, str], dest: Path, name: str, lang: str = "js"):
    from ..model import Project
    _clean(dest)
    main = f"Program{EXT[lang]}"
    project = Project(dest, name, PLUGIN_IDS[lang])
    for fname, text in files.items():
        p = dest / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    project.modules = _ordered(files, main) or list(files)
    project.startup = Path(main).stem if main in files else ""
    project.save()
    return project


def controls(code: str, spec: dict | None = None) -> list[tuple[str, str, dict]]:
    """(type, name, props) of Form1's controls: from the test comment or from the names the code uses."""
    spec = spec or {}
    if spec.get("controls"):
        return [(c[0], c[1], dict(c[2]) if len(c) > 2 else {}) for c in spec["controls"]]
    names: list[str] = []
    for m in RX_NAME.finditer(code):
        n = m.group(1) or m.group(2)
        if n not in names:
            names.append(n)
    out = []
    for n in names:
        typ = next((t for p, t in PREFIXES if n.startswith(p)), None)
        if typ:
            out.append((typ, n, {}))
    return out


def make_form(files: dict[str, str], dest: Path, name: str, spec: dict | None = None, lang: str = "js"):
    """A GUI Bridge Windows Application: Form1 with the controls of *spec* / of the code, Form1.js|ts."""
    from ..model import Form
    from ..workspace import create_project
    _clean(dest)
    ext = EXT[lang]
    project = create_project(dest, name, PLUGIN_IDS[lang])
    code = files.get(f"Form1{ext}") or next(iter(files.values()), "")
    form = Form.load(project.form_path("Form1"))
    spec = spec or {}
    y = 12
    for typ, cname, props in controls(code, spec):
        try:
            c = form.add(typ, 12, y)
        except KeyError:                       # a control type this IDE build does not have
            continue
        c.props["Name"] = cname
        default = {"Label": {"Width": 360, "Text": ""}, "TextBox": {"Width": 220, "Text": ""},
                   "ComboBox": {"Width": 220}, "Button": {"Text": cname[3:], "Width": 140},
                   "ListBox": {"Width": 300, "Height": 120}, "CheckBox": {"Text": cname[3:], "Width": 220},
                   "RadioButton": {"Text": cname[3:], "Width": 220}}.get(typ, {})
        c.props.update(default)
        c.props.update(props)
        try:
            y = max(y + 34, int(c.props.get("Top", y)) + int(c.props.get("Height", 24)) + 10)
        except (TypeError, ValueError):
            y += 34
    form.props.update(spec.get("form") or {})
    try:
        form.props["Height"] = max(int(form.props.get("Height", 300)), y + 60)
    except (TypeError, ValueError):
        pass
    form.save(project.form_path("Form1"))
    for fname, text in files.items():
        p = dest / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        if not fname.startswith("Form1.") and fname.lower().endswith(ext) and fname not in project.modules:
            project.modules.append(fname)
    project.save()
    return project


def make_project(block, files: dict[str, str], dest: Path, name: str):
    dest = Path(dest).resolve()
    target = block.check_target()
    lang = lang_of(block)
    if block.form or target.form:
        return make_form(files, dest, name, target.spec, lang)
    return make_console(files, dest, name, lang)


# ===================================================================== running
def run_console(folder: Path, stdin: str | None, timeout: int = 25) -> tuple[bool, str]:
    """Run a console project with the IDE's own run spec (python -m radide.runtimes.bridge ... node _radmain.js);
    (finished, stdout + stderr)."""
    from ..languages import get_plugin
    from ..model import Project
    project = Project.load(folder)
    plugin = get_plugin(project.language)
    if not node_exe():
        return False, "Node.js غير موجود: ثبّت Node.js 22 أو أحدث من https://nodejs.org"
    spec = plugin.run_spec(folder, project.startup or "Program", "")
    try:
        r = subprocess.run([spec.program, *spec.args], cwd=str(spec.cwd), env=spec.env,
                           input=(stdin or "").encode("utf-8"), capture_output=True, timeout=timeout,
                           creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return False, "<<انتهت المهلة: هل في البرنامج حلقة لا تنتهي، أو خادم ما زال يعمل؟>>"
    out = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
    out = "\n".join(ln for ln in out.replace("\r\n", "\n").split("\n") if not ln.startswith("------ "))
    return True, out


def syntax_only(folder: Path) -> tuple[bool, str]:
    """``node --check`` for every .js file (TypeScript: the type stripper) - servers and endless programs."""
    node = node_exe()
    if not node:
        return False, "Node.js غير موجود"
    errors = []
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() == ".js" and not p.name.startswith(("_rad", "radgui")):
            r = subprocess.run([node, "--check", p.name], cwd=str(folder), capture_output=True,
                               creationflags=NO_WINDOW)
            if r.returncode:
                errors.append((r.stdout + r.stderr).decode("utf-8", "replace"))
        elif p.suffix.lower() == ".ts":
            js = ("const m = require('module'); const fs = require('fs');"
                  "m.stripTypeScriptTypes(fs.readFileSync(process.argv[1], 'utf8'), {mode: 'transform'});")
            r = subprocess.run([node, "--no-warnings", "-e", js, p.name], cwd=str(folder), capture_output=True,
                               creationflags=NO_WINDOW)
            if r.returncode:
                errors.append((r.stdout + r.stderr).decode("utf-8", "replace"))
    return not errors, "\n".join(errors)


def run_form(folder: Path, spec: dict | None, timeout: int = 40) -> dict:
    """Run a GUI project headless with the real GUI Bridge (child process, Tk hidden); the result dict has
    output, errors (stderr of the program), msgbox, values, fatal."""
    sp, rp = folder / "_spec.json", folder / "_result.json"
    sp.write_text(json.dumps(spec or {}, ensure_ascii=False), encoding="utf-8")
    if rp.exists():
        rp.unlink()
    repo = Path(__file__).resolve().parents[2]
    env = dict(os.environ, PYTHONPATH=str(repo), PYTHONIOENCODING="utf-8")
    try:
        subprocess.run([sys.executable, "-m", "radide.tutorials.js_support", "--child", str(folder), str(sp),
                        str(rp)], cwd=str(folder), env=env, timeout=(spec or {}).get("timeout", timeout),
                       capture_output=True, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return {"fatal": "انتهت المهلة: لم يرد البرنامج", "output": ""}
    if not rp.exists():
        return {"fatal": "توقف البرنامج دون نتيجة", "output": ""}
    return json.loads(rp.read_text(encoding="utf-8"))


def child(folder: str, spec_path: str, result_path: str) -> None:
    """The headless GUI run (``python -m radide.tutorials.js_support --child <folder> <spec> <result>``)."""
    import io
    import threading
    folder_p = Path(folder)
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    from ..languages import get_plugin
    from ..model import Project
    from ..runtimes import vbrun
    from ..runtimes.bridge import BridgeRuntime
    from ..runtimes.vbinterp import to_str
    project = Project.load(folder_p)
    plugin = get_plugin(project.language)
    plugin.prepare(folder_p, project)
    program = plugin.run_command(folder_p, project)
    handlers = set(plugin.handlers_in_project(folder_p, project))
    out = io.StringIO()
    real_stdout = sys.stdout
    sys.stdout = out
    result = {"msgbox": [], "values": {}, "fatal": None, "errors": ""}
    inputs = list(spec.get("inputs", []))
    err_lines: list[str] = []

    class Headless(BridgeRuntime):
        def start_program(self):
            self.proc = subprocess.Popen(self.program, cwd=str(self.folder), stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                         encoding="utf-8", errors="replace", bufsize=1, creationflags=NO_WINDOW)
            threading.Thread(target=self._reader, daemon=True).start()
            threading.Thread(target=lambda: err_lines.extend(self.proc.stderr), daemon=True).start()

        def msgbox(self, prompt, buttons, title):
            result["msgbox"].append(str(prompt))
            return 1

        def inputbox(self, prompt, title, default):
            return inputs.pop(0) if inputs else (default or "")

    def finish(code=0):
        sys.stdout = real_stdout
        try:
            if rt.proc and rt.proc.poll() is None:
                rt.proc.kill()
        except Exception:  # noqa: BLE001
            pass
        result["output"] = out.getvalue()
        result["errors"] = "".join(err_lines)
        Path(result_path).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        os._exit(code)

    rt = Headless(folder_p, program, handlers)
    rt.end = finish
    vbrun.messagebox.showerror = lambda *a, **k: None
    try:
        rt.load()
        rt.start_program()
        start = rt.forms[(rt.project.startup or rt.project.forms[0]).lower()]
        rt.startup_form = start
        start.load()
        if rt.root is not None:
            try:
                rt.root.attributes("-alpha", 0.0)
            except Exception:  # noqa: BLE001
                pass
        start.vb_call("show", [])
        if rt.root is not None:
            rt.root.update()
        for step in spec.get("steps", []):
            vf = rt.startup_form
            op = step[0]
            if op == "set":
                vf.vb_get(step[1].lower()).vb_set(step[2].lower(), step[3])
            elif op == "click":
                rt.event(step[1], "Click")
            elif op == "event":
                rt.event(step[1], step[2])
            elif op == "tick":
                rt.event(step[1], "Tick")
            if rt.root is not None:
                rt.root.update()
        vf = rt.startup_form
        for key in spec.get("expect", {}):
            ctl, _, prop = key.partition(".")
            obj = vf if ctl.lower() in (vf.name.lower(), "me") else vf.vb_get(ctl.lower())
            mm = re.match(r"(\w+)\((.*)\)$", prop)
            if mm:                                   # lstLog.List(0)
                value = obj.vb_call(mm.group(1).lower(), [json.loads(a) for a in mm.group(2).split(",")])
            else:
                value = obj.vb_get(prop.lower())
            result["values"][key] = to_str(value)
        import time
        time.sleep(0.2)                              # the last stderr lines of the program
    except SystemExit:
        pass
    except Exception as ex:  # noqa: BLE001
        import traceback
        result["fatal"] = "harness: " + "".join(traceback.format_exception(ex))[-1500:]
    finish()


# ===================================================================== check ("تحقق")
def _project_files(folder: Path) -> dict[str, str]:
    out = {}
    for p in sorted(Path(folder).iterdir()):
        if p.is_file() and p.suffix.lower() in (".js", ".ts", ".json") and not p.name.startswith(("_rad", "radgui")) \
                and p.name not in ("project.radproj", "tsconfig.json") and not p.name.endswith(".form"):
            out[p.name] = p.read_text(encoding="utf-8", errors="replace")
    return out


def check(block, code, folder, work: Path, norm, CheckResult, block_files):
    target = block.check_target()
    spec = target.spec or {}
    expected = target.expected
    work = Path(work).resolve()
    files = _project_files(folder) if folder else block_files(block, code)
    form = block.form or target.form
    proj = make_project(block, files, work, "Check")
    if form:
        r = run_form(work, spec)
        problems = []
        if r.get("fatal"):
            problems.append("خطأ: " + str(r["fatal"]))
        errs = (r.get("errors") or "").strip()
        if errs and not spec.get("errors_ok"):
            problems.append("خطأ أثناء التشغيل:\n" + errs[-1500:])
        if "msgbox" in spec and r.get("msgbox") != spec["msgbox"]:
            problems.append("رسائل msgbox: المتوقع " + " | ".join(spec["msgbox"]) + " ، الناتج " +
                            " | ".join(r.get("msgbox") or []))
        for k, v in (spec.get("expect") or {}).items():
            got = (r.get("values") or {}).get(k)
            if str(v).startswith("re:") and got is not None and re.fullmatch(str(v)[3:], got):
                continue
            if got != str(v):
                problems.append(f"{k}: المتوقع «{v}» والناتج «{got}»")
        if expected is not None and norm(r.get("output", "")) != norm(expected):
            problems.append("المخرجات لا تطابق المطلوب")
        out = r.get("output", "")
        if r.get("msgbox"):
            out += ("\n" if out else "") + "\n".join(f"[msgbox] {m}" for m in r["msgbox"])
        if not spec.get("expect") and "msgbox" not in spec and expected is None and not problems:
            return CheckResult(True, out, None, [], "يعمل البرنامج بلا أخطاء. اضغط «جرّبه» وجرّب الأزرار بنفسك.")
        return CheckResult(not problems, out, expected, problems)
    if spec.get("norun"):
        from ..languages import get_plugin
        get_plugin(proj.language).prepare(work, proj)
        ok, out = syntax_only(work)
        return CheckResult(ok, out, None, [] if ok else ["خطأ في الصياغة"],
                           "الكود سليم الصياغة. هذا برنامج يبقى يعمل (خادم مثلًا): شغّله بـ «جرّبه»." if ok else "")
    finished, out = run_console(work, target.stdin, int(spec.get("timeout", 25)))
    if not finished:
        return CheckResult(False, out, expected, [out])
    if expected is None and target is not block and target.code.strip():
        make_project(target, block_files(target), work.parent / (work.name + "-sol"), "Check")
        _f, expected = run_console(work.parent / (work.name + "-sol"), target.stdin)
    if expected is None:
        return CheckResult(True, out, None, [], "يعمل البرنامج بلا أخطاء.")
    ok = norm(out) == norm(expected)
    return CheckResult(ok, out, expected, [] if ok else ["المخرجات لا تطابق المطلوب"])


if __name__ == "__main__":
    if len(sys.argv) >= 5 and sys.argv[1] == "--child":
        child(sys.argv[2], sys.argv[3], sys.argv[4])
