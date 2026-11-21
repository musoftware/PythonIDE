"""Headless runner for the Python blocks of the tutorials (radide/tutorials/pyrun.py runs it in a child process).

    python py_child.py <folder> <spec.json> <result.json>

Modes (spec["_mode"]): console (run main.py as __main__), notebook (run the # %% cells, show each cell's last
expression like Jupyter), tk / qt (create Form1 hidden, run the scripted steps, read the controls back).
Message boxes and input dialogs are answered from the spec and recorded.  Standard library only (+ the GUI
toolkit of the mode), so it runs with any Python.
"""
from __future__ import annotations

import os
import sys

# this folder (radide/tutorials: html.py, course folders...) must not shadow the learner's imports (html, ...)
_HERE = os.path.normcase(os.path.dirname(os.path.abspath(__file__)))
sys.path[:] = [p for p in sys.path if os.path.normcase(os.path.abspath(p or os.curdir)) != _HERE]

import ast  # noqa: E402
import json  # noqa: E402
import runpy  # noqa: E402
import traceback  # noqa: E402

folder, spec_path, result_path = sys.argv[1:4]
spec = json.load(open(spec_path, encoding="utf-8"))
mode = spec.get("_mode", "console")
main_file = spec.get("_main") or "main.py"
result = {"values": {}, "msgbox": [], "error": None}
answers = list(spec.get("answers") or [])
os.chdir(folder)
sys.path.insert(0, folder)
sys.argv = [os.path.join(folder, main_file)]
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def finish(code=0):
    sys.stdout.flush()
    sys.stderr.flush()
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    os._exit(code)


def record_error(e: BaseException) -> None:
    result["error"] = f"{type(e).__name__}: {e}"
    here = os.path.normcase(os.path.abspath(folder))
    tb = [fr for fr in traceback.extract_tb(e.__traceback__)       # only the learner's files (not runpy, not us)
          if fr.filename.startswith("Cell In[") or not fr.filename.startswith("<") and os.path.normcase(os.path.abspath(fr.filename)).startswith(here + os.sep)]
    lines = []
    for fr in tb:
        if fr.filename.startswith("Cell In["):              # a notebook cell, shown like Jupyter does
            lines.append(f"  {fr.filename}, line {fr.lineno}")
        else:
            lines.append(f'  File "{os.path.basename(fr.filename)}", line {fr.lineno}, in {fr.name}')
        if fr.line:
            lines.append("    " + fr.line.strip())
    if isinstance(e, SyntaxError) and e.filename and not e.filename.startswith("Cell In["):
        e.filename = os.path.basename(e.filename)
    tail = "".join(traceback.format_exception_only(type(e), e)).rstrip("\n")
    if tb or not isinstance(e, SyntaxError):
        lines.insert(0, "Traceback (most recent call last):")
    print("\n".join(lines + [tail]), file=sys.stderr)


def answer(default=""):
    return str(answers.pop(0)) if answers else default


# ===================================================================== console
def run_console():
    try:
        runpy.run_path(main_file, run_name="__main__")
    except SystemExit:
        pass
    except BaseException as e:  # noqa: BLE001 - shown like Python shows it
        record_error(e)


# ===================================================================== notebook
def run_notebook():
    import re
    text = open(main_file, encoding="utf-8").read()
    cells, cur, kind = [], [], "code"
    for line in text.splitlines():
        m = re.match(r"^#\s*%%(.*)$", line)
        if m:
            if cur and kind == "code":
                cells.append("\n".join(cur))
            cur, kind = [], ("markdown" if "[markdown]" in m.group(1) else "code")
        else:
            cur.append(line)
    if cur and kind == "code":
        cells.append("\n".join(cur))
    ns = {"__name__": "__main__"}
    import warnings                    # plt.show() on the Agg backend: the figure is shown in the IDE only
    warnings.filterwarnings("ignore", message=".*non-interactive.*")
    try:
        import matplotlib
        matplotlib.use("Agg")
    except ImportError:
        pass
    import linecache
    n = 0
    for src in cells:
        if not src.strip():
            continue
        n += 1
        name = f"Cell In[{n}]"
        linecache.cache[name] = (len(src), None, src.splitlines(True), name)
        try:
            tree = ast.parse(src)
            last = None
            quiet = src.rstrip().endswith(";")
            if tree.body and isinstance(tree.body[-1], ast.Expr):
                last = ast.Expression(tree.body.pop().value)
            exec(compile(tree, name, "exec"), ns)
            if last is not None:
                value = eval(compile(last, name, "eval"), ns)
                if value is not None and not quiet:
                    print(repr(value))
        except BaseException as e:  # noqa: BLE001
            record_error(e)
            return


# ===================================================================== forms
def control_value(w, form, name):
    if mode == "qt":
        from PySide6 import QtWidgets as W
        if isinstance(w, W.QListWidget):
            return "|".join(w.item(i).text() for i in range(w.count()))
        if isinstance(w, W.QComboBox):
            return w.currentText()
        if isinstance(w, (W.QCheckBox, W.QRadioButton)):
            return str(w.isChecked())
        if isinstance(w, (W.QSpinBox, W.QDoubleSpinBox, W.QSlider, W.QProgressBar)):
            return str(w.value())
        if hasattr(w, "toPlainText"):
            return w.toPlainText()
        if hasattr(w, "text"):
            return w.text()
        return str(w)
    import tkinter as tk
    var = getattr(form, name + "_var", None)
    if isinstance(w, tk.Listbox):
        return "|".join(str(x) for x in w.get(0, "end"))
    if isinstance(w, tk.Text):
        return w.get("1.0", "end-1c")
    if var is not None:
        return str(var.get())
    for opt in ("text", "value"):
        try:
            return str(w.cget(opt))
        except Exception:  # noqa: BLE001
            continue
    return str(w)


def do_step(form, app, verb, name, value=None):
    w = getattr(form, name)
    if mode == "qt":
        from PySide6 import QtWidgets as W
        if verb == "set":
            if isinstance(w, (W.QSpinBox, W.QSlider)):
                w.setValue(int(value))
            elif isinstance(w, W.QComboBox):
                w.setCurrentText(str(value))
            elif hasattr(w, "setPlainText"):
                w.setPlainText(str(value))
            else:
                w.setText(str(value))
        elif verb == "click":
            w.click()
        elif verb == "select":
            (w.setCurrentRow if isinstance(w, W.QListWidget) else w.setCurrentIndex)(int(value))
        elif verb == "tick":
            for _ in range(int(value or 1)):
                w.timeout.emit()
        app.processEvents()
        return
    import tkinter as tk
    var = getattr(form, name + "_var", None)
    if verb == "set":
        if var is not None:
            var.set(value)
        elif isinstance(w, tk.Text):
            w.delete("1.0", "end")
            w.insert("1.0", str(value))
        else:
            w.delete(0, "end")
            w.insert(0, str(value))
    elif verb == "click":
        w.invoke()
    elif verb == "select":
        if isinstance(w, tk.Listbox):
            w.selection_clear(0, "end")
            w.selection_set(int(value))
            w.event_generate("<<ListboxSelect>>")
        else:
            w.current(int(value))
            w.event_generate("<<ComboboxSelected>>")
    elif verb == "tick":
        for _ in range(int(value or 1)):
            w._tick()
    app.update()


def run_form():
    steps = []
    for k, v in (spec.get("set") or {}).items():
        steps.append(["set", k, v])
    for k, v in (spec.get("select") or {}).items():
        steps.append(["select", k, v])
    steps += list(spec.get("steps") or [])
    for k in spec.get("click") or []:
        steps.append(["click", k])
    if mode == "qt":
        from PySide6 import QtWidgets as W
        app = W.QApplication.instance() or W.QApplication([main_file])

        def box(kind):
            def show(*a, **k):
                text = a[2] if len(a) > 2 else k.get("text", "")
                result["msgbox"].append(str(text))
                return W.QMessageBox.StandardButton.Yes if kind == "question" else W.QMessageBox.StandardButton.Ok
            return staticmethod(show)
        for kind in ("information", "warning", "critical", "question", "about"):
            setattr(W.QMessageBox, kind, box(kind))

        def get_text(*a, **k):
            return answer(), True
        W.QInputDialog.getText = staticmethod(get_text)
        W.QInputDialog.getInt = staticmethod(lambda *a, **k: (int(answer("0")), True))
        W.QInputDialog.getDouble = staticmethod(lambda *a, **k: (float(answer("0")), True))
    else:
        import tkinter as tk
        from tkinter import messagebox, simpledialog

        def box(kind):
            def show(title=None, message=None, **k):
                result["msgbox"].append(str(message if message is not None else k.get("message", "")))
                return True if kind.startswith("ask") else "ok"
            return show
        for kind in ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel", "askquestion"):
            setattr(messagebox, kind, box(kind))
        messagebox.askquestion = lambda *a, **k: (result["msgbox"].append(str(a[1] if len(a) > 1 else k.get(
            "message", ""))), "yes")[1]
        simpledialog.askstring = lambda *a, **k: answer()
        simpledialog.askinteger = lambda *a, **k: int(answer("0"))
        simpledialog.askfloat = lambda *a, **k: float(answer("0"))
        tk.Tk.mainloop = lambda self, n=0: None
    try:
        ns = runpy.run_path(main_file, run_name="lesson_form")
        form = ns["Form1"]()
        if mode == "qt":
            form.show()
            app.processEvents()
            app.processEvents()
        else:
            form.root.withdraw()
            form.root.update()
            app = form.root
        for st in steps:
            do_step(form, app, *st)
        for name in spec.get("expect") or {}:
            w = getattr(form, name, None)
            result["values"][name] = None if w is None else control_value(w, form, name)
    except SystemExit:
        pass
    except BaseException as e:  # noqa: BLE001
        record_error(e)


try:
    if mode in ("tk", "qt"):
        run_form()
    elif mode == "notebook":
        run_notebook()
    else:
        run_console()
except BaseException as e:  # noqa: BLE001
    record_error(e)
finish()
