"""Coverage: the Edit menu (functional, offscreen IDE, sandbox copy of the Python Tk sample).

The sample is prepared first: Form1.py gets a module function ``double_it`` (defined once, used twice) and calls
``Helpers.add_numbers`` defined in Helpers.py.

* Edit > Find in Files (Ctrl+Shift+F): the Find and Replace dialog searches the project for "double_it" ->
  Find Results lists Form1.py with the three matching lines and the dock title counts them; a word that is in no
  file gives 0 matches; Replace All of a marker rewrites Helpers.py on disk.
* Edit > Find / Find Next (F3) / Find Previous (Shift+F3): after two Find Next the selection is on the second
  "print(" line; Find Previous moves it back to the first one.
* Edit > Go to Definition (F12): on a use of double_it the cursor jumps to its def line; on Helpers.add_numbers
  Helpers.py opens with the cursor on its def line.
* Edit > Refactor > Find All References: the Find All References window lists the def and both uses of
  double_it in Form1.py.

The editor engine is set to the built-in editor (editor/engine) so editor text / cursor / selection are read
synchronously offscreen (Monaco runs in QtWebEngine and answers asynchronously).

Run:  .venv\\Scripts\\python samples\\Tests\\Coverage\\Edit\\test_edit_menu.py
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cov_harness as H  # noqa: E402
from cov_harness import (C, ROOT, action, check, clear_modal_handlers, finish, on_modal, open_sample, pump,  # noqa: E402
                         sandbox, start, wait)

_orig_window = C.window


def _window_builtin_editor():
    from radide.app import ide_settings
    ide_settings().setValue("editor/engine", "builtin")
    return _orig_window()


C.window = _window_builtin_editor

w = start("edit_menu")
from PyQt6.QtWidgets import QApplication  # noqa: E402

# ------------------------------------------------------------------ prepared sandbox project
SB = sandbox()
prep = SB / "prep" / "EditDemo"
shutil.copytree(ROOT / "samples/Tests/Languages/PythonTk_Form", prep, ignore=C.COPY_IGNORE)
for junk in prep.glob("test_*.py"):
    junk.unlink()
form_py = prep / "Form1.py"
src = form_py.read_text(encoding="utf-8")
src = src.replace("import Helpers\n", "import Helpers\n\n\ndef double_it(value):\n    return value * 2\n", 1)
src = src.replace("    def Button1_Click(self):\n        pass\n",
                  "    def Button1_Click(self):\n        total = Helpers.add_numbers(2, 3)\n"
                  "        print('total', double_it(total))\n\n"
                  "    def Form1_Shown(self):\n        print('shown', double_it(21))\n", 1)
form_py.write_text(src, encoding="utf-8")
(prep / "Helpers.py").write_text((prep / "Helpers.py").read_text(encoding="utf-8") +
                                 "\n\ndef add_numbers(a, b):\n    \"\"\"replace-marker-old\"\"\"\n    return a + b\n",
                                 encoding="utf-8")
proj = open_sample(w, str(prep))
check("prepared Python Tk project opened", w.project is not None and Path(w.project.folder) == proj)
w.open_code("Form1")
pump(0.5)
cv = w._current_code()
ed = cv.editor if cv is not None else None
check("Form1.py open in the built-in code editor", ed is not None and type(ed).__name__ == "CodeEditor",
      type(ed).__name__ if ed is not None else None)
text = ed.text() if ed is not None else ""
lines = text.split("\n")


def line_of(pattern: str, nth: int = 0) -> int:
    hits = [i for i, ln in enumerate(lines) if pattern in ln]
    return hits[nth] if len(hits) > nth else -1


def_line = line_of("def double_it(")
use1, use2 = line_of("double_it(total)"), line_of("double_it(21)")
check("the prepared code is in the editor", min(def_line, use1, use2) >= 0, text[:400])

# ------------------------------------------------------------------ Edit > Find in Files
fif = {}


def find_all(word, action_="find", replace=""):
    def h(dlg):
        if type(dlg).__name__ != "FindInFilesDialog":
            return False
        fif["scope"] = dlg.scope_key()
        dlg.what.setEditText(word)
        if replace:
            dlg.replace.setText(replace)
        dlg._done(action_)
        return True
    return h


on_modal(find_all("double_it"))
a = action(w, "Edit", "Find in Files")
check("Edit > Find in Files has Ctrl+Shift+F", a is not None and a.shortcut().toString() == "Ctrl+Shift+F",
      a and a.shortcut().toString())
H.trigger(a, 0.8)
check("Find in Files searches the current project by default", fif.get("scope") == "project", fif)
rows = [(w.find_results.topLevelItem(i).text(0), int(w.find_results.topLevelItem(i).text(1)),
         w.find_results.topLevelItem(i).text(2)) for i in range(w.find_results.topLevelItemCount())]
check("Find in Files: 3 results, all in Form1.py", len(rows) == 3 and all(r[0] == "Form1.py" for r in rows), rows)
check("Find in Files: the result lines are the def and the two uses",
      sorted(r[1] for r in rows) == sorted([def_line + 1, use1 + 1, use2 + 1]), (rows, def_line, use1, use2))
check("Find in Files: the result text is the code line", any(r[2].startswith("def double_it(") for r in rows), rows)
check("Find in Files: the dock title counts '3 matches in 1 file'",
      "3 matches in 1 file" in w.dock_find.windowTitle(), w.dock_find.windowTitle())
check("Find in Files: the Find Results window is shown", w.dock_find.isVisible())
clear_modal_handlers()
on_modal(find_all("zz_no_such_word_zz"))
H.trigger(a, 0.8)
check("Find in Files: an unknown word gives no results",
      w.find_results.topLevelItemCount() == 0 and "0 matches" in w.dock_find.windowTitle(),
      w.dock_find.windowTitle())
clear_modal_handlers()
on_modal(find_all("replace-marker-old", "replace", "replace-marker-new"))
H.trigger(a, 0.8)
helpers_disk = (proj / "Helpers.py").read_text(encoding="utf-8")
helpers_ed = w._editor_for_file("Helpers.py")
helpers_now = helpers_ed.text() if helpers_ed is not None else helpers_disk
check("Find in Files: Replace All rewrites Helpers.py", "replace-marker-new" in helpers_now and
      "replace-marker-old" not in helpers_now, helpers_now[-200:])
check("Find in Files: Replace All counts the replaced file", "replaced in 1 file" in w.dock_find.windowTitle(),
      w.dock_find.windowTitle())
clear_modal_handlers()

# ------------------------------------------------------------------ Edit > Find / Find Next / Find Previous
w.open_code("Form1")
pump(0.3)
ed = w._current_code().editor
ed.setCursorPosition(0, 0)
H.trigger(action(w, "Edit", "Find"), 0.3)
check("Edit > Find shows the find bar", w.findbar.isVisible())
w.findbar.find.setText("print(")
prints = [i for i, ln in enumerate(ed.text().split("\n")) if "print(" in ln]
a_next, a_prev = action(w, "Edit", "Find Next"), action(w, "Edit", "Find Previous")
check("Edit > Find Next (F3) / Find Previous (Shift+F3) exist",
      a_next is not None and a_prev is not None and a_next.shortcut().toString() == "F3" and
      a_prev.shortcut().toString() == "Shift+F3", (a_next and a_next.shortcut().toString(),
                                                   a_prev and a_prev.shortcut().toString()))
H.trigger(a_next, 0.1)
first = ed.getCursorPosition()[0]
H.trigger(a_next, 0.1)
second = ed.getCursorPosition()[0]
check("Find Next selects the first then the second 'print(' line", len(prints) >= 3 and
      (first, second) == (prints[0], prints[1]) and ed.textCursor().selectedText() == "print(",
      (first, second, prints[:3], ed.textCursor().selectedText()))
H.trigger(a_prev, 0.1)
back = ed.getCursorPosition()[0]
check("Find Previous moves the selection back to the first 'print(' line",
      back == prints[0] and ed.textCursor().selectedText() == "print(", (back, prints[:3]))
H.trigger(a_prev, 0.1)
check("Find Previous before the first match wraps to the last one", ed.getCursorPosition()[0] == prints[-1],
      (ed.getCursorPosition(), prints))
w.findbar.close_bar()

# ------------------------------------------------------------------ Edit > Go to Definition (F12)
a = action(w, "Edit", "Go to Definition")
check("Edit > Go to Definition has F12", a is not None and a.shortcut().toString() == "F12",
      a and a.shortcut().toString())
lines = ed.text().split("\n")
use2 = next(i for i, ln in enumerate(lines) if "double_it(21)" in ln)
def_line = next(i for i, ln in enumerate(lines) if ln.startswith("def double_it("))
ed.setCursorPosition(use2, lines[use2].index("double_it") + 3)
H.trigger(a, 0.5)
check("Go to Definition on double_it jumps to its def line",
      wait(lambda: w._current_code() is not None and w._current_code().editor.getCursorPosition()[0] == def_line, 15),
      (w._current_code().editor.getCursorPosition() if w._current_code() else None, def_line))

w.open_code("Form1")
pump(0.3)
ed = w._current_code().editor
lines = ed.text().split("\n")
call = next(i for i, ln in enumerate(lines) if "Helpers.add_numbers(" in ln)
ed.setCursorPosition(call, lines[call].index("add_numbers") + 2)
H.trigger(a, 0.5)


def on_helpers_def():
    cur = w._current_code()
    if cur is None or Path(str(getattr(cur.editor, "path", ""))).name != "Helpers.py":
        return False
    ln = cur.editor.getCursorPosition()[0]
    return cur.editor.text().split("\n")[ln].startswith("def add_numbers(")


check("Go to Definition on Helpers.add_numbers opens Helpers.py on its def line", wait(on_helpers_def, 20),
      (w.tabs.tabText(w.tabs.currentIndex()),
       w._current_code().editor.getCursorPosition() if w._current_code() else None))

# ------------------------------------------------------------------ Edit > Refactor > Find All References
w.open_code("Form1")
pump(0.3)
ed = w._current_code().editor
lines = ed.text().split("\n")
use1 = next(i for i, ln in enumerate(lines) if "double_it(total)" in ln)
ed.setCursorPosition(use1, lines[use1].index("double_it") + 1)
a = action(w, "Edit", "Refactor", "Find All References")
check("Edit > Refactor > Find All References exists", a is not None)
H.trigger(a, 0.5)


def ref_rows():
    panel = getattr(w, "references_panel", None)
    if panel is None:
        return []
    out = []
    t = panel.tree
    for i in range(t.topLevelItemCount()):
        fi = t.topLevelItem(i)
        for j in range(fi.childCount()):
            ci = fi.child(j)
            out.append((ci.text(1), int(ci.text(2)), ci.text(0)))
    return out


check("Find All References: the references window lists 3 references", wait(lambda: len(ref_rows()) >= 3, 20),
      ref_rows())
rows = ref_rows()
f1 = [r for r in rows if r[0] == "Form1.py"]
expect = sorted([def_line + 1, use1 + 1, use2 + 1])
check("Find All References: the def and both uses in Form1.py", sorted(r[1] for r in f1) == expect, (rows, expect))
check("Find All References: the window title names double_it",
      "double_it" in w.references_panel.title.text() and "3 reference" in w.references_panel.title.text(),
      w.references_panel.title.text())
check("Find All References: the window is shown", w.dock_references.isVisible())
check("no modal dialog left open", QApplication.activeModalWidget() is None)
finish(w)
