"""Python blocks of the tutorials (course "python", guide "jupyter-datascience").

Block kinds (fence info strings):

* ``python run`` / ``python exercise`` / ``python solution``   - a console program ``main.py`` (``# #file: x.py``
  lines split the block into several files; ``text input`` = what the user types for ``input()``).
* ``python form run`` (also ``exercise`` / ``solution``)         - a Tkinter form: the block is ``Form1.py`` (the code
  file of a python-tk Windows Application: ``class Form1(Form1Designer)`` with the event handlers).
* ``python qt form run``                                         - the same with PySide6 (python-qt).
* ``python notebook run``                                        - notebook cells in the percent format (``# %%``,
  ``# %% [markdown]``): "جرّبه" opens them as ``notebook.ipynb``; the check runs the cells in order and shows the
  value of each cell's last expression like Jupyter does.

The controls of a form come from the hidden test comment (``"controls": [["Button", "btnHello", {"Text": "..."}]]``,
``"form": {"Text": ..., "Width": ..., "Height": ...}``) or else from the names the code uses (``self.btnHello``,
``def btnHello_Click``) with the usual prefixes (btn, txt, lbl, lst, cbo, chk, opt, tmr, num, prg, grp).
The same comment scripts the headless check: ``"set": {"txtName": "Sara"}``, ``"click": ["btnHello"]``,
``"select": {"lstNames": 1}``, ``"steps"`` (an ordered list of ``["set"|"click"|"select"|"tick", name, value]``),
``"expect": {"lblResult": "..."}`` (``re:`` = regular expression), ``"msgbox": [...]``, ``"answers": [...]``
(``simpledialog`` / ``QInputDialog`` replies).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

CHILD = Path(__file__).resolve().parent / "py_child.py"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
PY_PREFIXES = (("btn", "Button"), ("cmd", "Button"), ("txt", "TextBox"), ("lbl", "Label"), ("lst", "ListBox"),
               ("cbo", "ComboBox"), ("cmb", "ComboBox"), ("chk", "CheckBox"), ("opt", "RadioButton"),
               ("rdo", "RadioButton"), ("tmr", "Timer"), ("num", "NumericUpDown"), ("prg", "ProgressBar"),
               ("grp", "GroupBox"), ("trk", "TrackBar"), ("pic", "PictureBox"))


def words(block) -> set[str]:
    return {w.lower() for w in block.info.split()[1:]}


def is_qt(block) -> bool:
    return "qt" in words(block)


def is_notebook(block) -> bool:
    return "notebook" in words(block)


def default_file(block) -> str:
    if block.form:
        return "Form1.py"
    return "main.py"


def python_exe() -> str:
    """A console python.exe (not pythonw) with the IDE's packages (PySide6, pandas, matplotlib)."""
    exe = Path(sys.executable)
    cand = exe.with_name("python.exe") if os.name == "nt" else exe
    return str(cand if cand.exists() else exe)


# ===================================================================== projects
def form_controls(code: str, spec: dict | None) -> list[tuple[str, str, dict]]:
    """(type, name, props) of the form's controls: the test comment's list, else the names the code uses."""
    spec = spec or {}
    if spec.get("controls"):
        return [(c[0], c[1], dict(c[2]) if len(c) > 2 else {}) for c in spec["controls"]]
    names: list[str] = []
    for m in re.finditer(r"\bself\.([a-z]{3}[A-Z]\w*?)(?:_var)?\b|\bdef\s+([a-z]{3}[A-Z]\w*)_[A-Z]\w*\s*\(", code):
        n = m.group(1) or m.group(2)
        if n and n not in names:
            names.append(n)
    out = []
    for n in names:
        typ = next((t for p, t in PY_PREFIXES if n.startswith(p)), None)
        if typ:
            out.append((typ, n, {}))
    return out


def _layout(form, controls) -> None:
    """Controls without Left/Top go in a column (like the C++ GUI blocks)."""
    y, auto = 12, False
    for typ, cname, props in controls:
        try:
            c = form.add(typ, 12, y)
        except KeyError:
            continue
        c.props["Name"] = cname
        explicit = "Top" in props or "Left" in props
        if not explicit:
            auto = True
            if typ == "Label":
                c.props["Width"], c.props["Text"] = 360, ""
            elif typ in ("TextBox", "ComboBox"):
                c.props["Width"] = 220
                if typ == "TextBox":
                    c.props["Text"] = ""
            elif typ == "Button":
                c.props["Text"], c.props["Width"], c.props["Height"] = cname[3:], 140, 28
            elif typ == "ListBox":
                c.props["Width"], c.props["Height"] = 260, 120
            elif typ in ("CheckBox", "RadioButton"):
                c.props["Text"], c.props["Width"] = cname[3:], 220
        for k, v in props.items():
            c.props[k] = v
        if not explicit and typ != "Timer":
            c.props["Top"] = y
            try:
                y += int(c.props.get("Height", 23)) + 12
            except (TypeError, ValueError):
                y += 34
    if auto:
        try:
            form.props["Height"] = max(int(form.props.get("Height", 300)), y + 50)
            form.props["Width"] = max(int(form.props.get("Width", 400)), 400)
        except (TypeError, ValueError):
            pass


def make_py_project(block, files: dict[str, str], dest: Path, name: str = "Lesson"):
    """A RAD IDE project for a Python block (*dest* is already empty)."""
    from ..model import Form, Project
    language = "python-qt" if is_qt(block) else "python-tk"
    spec = block.check_target().spec or {}
    if block.form:
        from ..languages import get_plugin
        from ..workspace import create_project
        project = create_project(dest, name, language)
        code = files.get("Form1.py") or next(iter(files.values()), "")
        form = Form.load(project.form_path("Form1"))
        form.props.update(spec.get("form") or {})
        _layout(form, form_controls(code, spec))
        form.save(project.form_path("Form1"))
        for fname, text in files.items():
            (dest / fname).parent.mkdir(parents=True, exist_ok=True)
            (dest / fname).write_text(text, encoding="utf-8")
            if fname != "Form1.py" and fname.lower().endswith(".py") and fname not in project.modules:
                project.modules.append(fname)
        plugin = get_plugin(language)
        (dest / plugin.designer_file("Form1")).write_text(plugin.generate_designer(form, code), encoding="utf-8")
        project.save()
        return project
    project = Project(dest, name, language)
    if is_notebook(block):
        from ..notebook.model import Notebook
        code = files.pop("main.py", "")
        Notebook.from_py(code, dest / "notebook.ipynb").save(dest / "notebook.ipynb")
    for fname, text in files.items():
        (dest / fname).parent.mkdir(parents=True, exist_ok=True)
        (dest / fname).write_text(text, encoding="utf-8")
        if fname.lower().endswith(".py"):
            project.modules.append(fname)
    mains = [m for m in project.modules if m.lower() == "main.py"] or project.modules[:1]
    project.startup = Path(mains[0]).stem if mains else ""
    project.save()
    return project


# ===================================================================== running headless
def run_py(block, files: dict[str, str], work: Path, stdin: str | None, spec: dict | None,
           timeout: int = 60) -> dict:
    """Run a Python block in *work* with py_child.py; returns {output, values, msgbox, error, fatal}."""
    from . import _clean
    work = Path(work).resolve()
    _clean(work)
    for fname, text in files.items():
        p = work / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    spec = dict(spec or {})
    mode = "qt" if block.form and is_qt(block) else "tk" if block.form else \
        "notebook" if is_notebook(block) else "console"
    spec["_mode"] = mode
    if block.form:                                # the designer file the IDE generates for Form1.py
        from ..model import Form
        from ..languages import get_plugin
        plugin = get_plugin("python-qt" if mode == "qt" else "python-tk")
        form = Form()
        form.props["Name"] = form.props["Text"] = "Form1"
        form.props.update(spec.get("form") or {})
        code = files.get("Form1.py", "")
        _layout(form, form_controls(code, spec))
        (work / plugin.designer_file("Form1")).write_text(plugin.generate_designer(form, code), encoding="utf-8")
    spec["_main"] = "Form1.py" if block.form else ("main.py" if "main.py" in files else next(iter(files), ""))
    sp, rp = work / "_spec.json", work / "_result.json"
    sp.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONUNBUFFERED="1", MPLBACKEND="Agg",
               QT_QPA_PLATFORM="offscreen" if mode == "qt" else os.environ.get("QT_QPA_PLATFORM", ""))
    if not env["QT_QPA_PLATFORM"]:
        env.pop("QT_QPA_PLATFORM")
    try:
        r = subprocess.run([python_exe(), "-X", "utf8", str(CHILD), str(work), str(sp), str(rp)], cwd=str(work),
                           input=(stdin or "").encode("utf-8"), capture_output=True, env=env,
                           timeout=spec.get("timeout", timeout), creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return {"fatal": "انتهت المهلة: هل في البرنامج حلقة لا تنتهي أو ينتظر إدخالًا؟", "output": ""}
    out = r.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
    res = {}
    if rp.exists():
        try:
            res = json.loads(rp.read_text(encoding="utf-8"))
        except ValueError:
            res = {}
    else:
        res["fatal"] = "توقف البرنامج دون نتيجة:\n" + r.stderr.decode("utf-8", "replace")[-1500:]
    res["output"] = out + r.stderr.decode("utf-8", "replace").replace("\r\n", "\n")
    return res


def check_py(block, files: dict[str, str], work: Path):
    from . import CheckResult, block_files, norm
    target = block.check_target()
    spec = target.spec or {}
    expected = target.expected
    r = run_py(block, files, work, target.stdin, spec)
    problems = []
    if r.get("fatal"):
        problems.append("خطأ: " + str(r["fatal"]))
    shows_error = bool(expected and ("Traceback (most recent call last)" in expected or "Error:" in expected))
    if r.get("error") and not spec.get("error") and not shows_error:
        problems.append("خطأ تشغيل: " + str(r["error"]))
    elif spec.get("error") and spec["error"] not in str(r.get("error") or ""):
        problems.append(f"كان متوقعًا الخطأ {spec['error']}")
    if expected is None and target is not block and target.code.strip() and not spec.get("expect") \
            and "msgbox" not in spec:
        expected = run_py(target, block_files(target), work.parent / (work.name + "-sol"), target.stdin,
                          spec).get("output")
    out = r.get("output", "")
    if expected is not None and norm(out) != norm(expected):
        problems.append("المخرجات لا تطابق المطلوب")
    if "msgbox" in spec and (r.get("msgbox") or []) != spec["msgbox"]:
        problems.append("الرسائل: المتوقع " + " | ".join(spec["msgbox"]) + " ، الناتج " +
                        " | ".join(r.get("msgbox") or []))
    for k, v in (spec.get("expect") or {}).items():
        got = (r.get("values") or {}).get(k)
        if str(v).startswith("re:") and got is not None and re.fullmatch(str(v)[3:], got, re.S):
            continue
        if got != str(v):
            problems.append(f"{k}: المتوقع «{v}» والناتج «{got}»")
    if r.get("msgbox"):
        out += ("\n" if out else "") + "\n".join(f"[رسالة] {m}" for m in r["msgbox"])
    if expected is None and not spec.get("expect") and "msgbox" not in spec and not problems:
        return CheckResult(True, out, None, [], "يعمل البرنامج بلا أخطاء.")
    return CheckResult(not problems, out, expected, problems)


__all__ = ["check_py", "default_file", "form_controls", "is_notebook", "is_qt", "make_py_project", "python_exe",
           "run_py"]
