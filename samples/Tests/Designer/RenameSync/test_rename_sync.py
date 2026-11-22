"""Renaming a control in the designer keeps the code in step, like Visual Studio.

* rename_control renames code only: string literals and comments keep their text, holes of interpolated
  strings (f"{x}", $"{x}", `${x}`) are code - Python, VB, C#, JavaScript, Pascal, Ring, Lua, WinForms VB
* code_segments gives the source back unchanged (round trip) and does not treat a backslash as an escape in
  VB / Pascal ("C:\\" closes the string)
* Ctrl+Z / Ctrl+Y of a rename in the designer emit FormDocument.codeRenamed (old, new) - the IDE renames the
  code back; add / delete / move steps rename nothing; a swap is left alone
* the IDE (MainWindow offscreen): rename Button1 -> btnOK from the Properties window, the code follows,
  Undo puts the code back to Button1, Redo to btnOK; a string "Press Button1" is never touched

Run:  .venv\\Scripts\\python samples\\Tests\\Designer\\RenameSync\\test_rename_sync.py [scratch]
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["RADIDE_NO_BROWSER"] = "1"
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "radide-renamesync"
shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True, exist_ok=True)

results: list[tuple[str, bool]] = []


def ok(name: str, cond, detail="") -> bool:
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:800]}]"), flush=True)
    return bool(cond)


from radide.languages import get_plugin  # noqa: E402
from radide.languages.base import code_segments  # noqa: E402

# ------------------------------------------------------------------ rename_control per language
CASES = [
    ("python-tk",
     'def Button1_Click(self, e):\n    messagebox.showinfo("x", "Press Button1")  # Button1 here\n'
     '    self.Button1.config(text=f"{self.Button1.cget(\'text\')}!")\n    """Button1 doc"""\n',
     ["def btnOK_Click", "self.btnOK.config", "{self.btnOK.cget", '"Press Button1"', "# Button1 here",
      '"""Button1 doc"""']),
    ("vb-basic",
     'Private Sub Button1_Click()\n    MsgBox "C:\\" & Button1.Caption \' Button1 note\n'
     '    x = "say ""Button1"""\nEnd Sub\n',
     ["Sub btnOK_Click", "& btnOK.Caption", "' Button1 note", '"say ""Button1"""']),
    ("csharp-bridge",
     'void Button1_Click(object s, EventArgs e) {\n  MessageBox.Show(@"C:\\" + Button1.Text); // Button1\n'
     '  var t = $"{Button1.Text} Button1"; /* Button1 */\n}\n',
     ["void btnOK_Click", '@"C:\\" + btnOK.Text', "// Button1", '$"{btnOK.Text} Button1"', "/* Button1 */"]),
    ("javascript",
     "function Button1_Click() {\n  alert(`Button1: ${Button1.value}`); // Button1\n  let s = 'Button1';\n}\n",
     ["function btnOK_Click", "`Button1: ${btnOK.value}`", "// Button1", "'Button1'"]),
    ("dos-pascal",
     "procedure Button1_Click; { Button1 }\nbegin\n  WriteLn('Button1 C:\\', Button1.Caption);\nend;\n",
     ["procedure btnOK_Click", "{ Button1 }", "'Button1 C:\\', btnOK.Caption"]),
    ("ring-qt",
     'func Button1_Click\n    Button1.setText("Button1") # Button1\n    // Button1\n',
     ["func btnOK_Click", 'btnOK.setText("Button1")', "# Button1", "// Button1"]),
    ("lua-bridge",
     'function Button1_Click()\n  Button1:SetText("Button1") -- Button1\n  --[[ Button1 ]]\nend\n',
     ["function btnOK_Click", 'btnOK:SetText("Button1")', "-- Button1", "--[[ Button1 ]]"]),
]
for pid, code, expect in CASES:
    try:
        p = get_plugin(pid)
    except Exception as e:  # noqa: BLE001
        ok(f"{pid}: plugin loads", False, e)
        continue
    segs = code_segments(code, p.line_comments, p.block_comment, p.string_quotes, p.string_escapes)
    ok(f"{pid}: code_segments round trip", "".join(t for t, _ in segs) == code)
    out = p.rename_control(code, "Button1", "btnOK")
    missing = [e for e in expect if e not in out]
    ok(f"{pid}: code renamed, strings / comments kept", not missing, f"missing {missing} in:\n{out}")

try:
    from radide.foreign.winforms_vb import PLUGIN as WFVB
    code = 'Private Sub Button1_Click(sender As Object, e As EventArgs) Handles Button1.Click\n' \
           '    MessageBox.Show("Button1 C:\\") \' Button1\nEnd Sub\n'
    out = WFVB.rename_control(code, "Button1", "btnOK")
    ok("WinForms VB: field + Handles renamed, text kept",
       "Handles btnOK.Click" in out and '"Button1 C:\\"' in out and "' Button1" in out, out)
except Exception as e:  # noqa: BLE001
    ok("WinForms VB plugin", False, e)

# rename_symbol (used for form renames) still changes strings: file names must follow
py = get_plugin("python-tk")
ok("rename_symbol (form rename) still renames inside strings", py.rename_symbol('load("Form1")', "Form1", "Main")
   == 'load("Main")')
ok("REM only at the start of a word (QBasic)", "PREMIUM" in "".join(
    t for t, c in code_segments("x = PREMIUM ' c\n", ["'", "REM "], None, ['"'], False) if c))

# ------------------------------------------------------------------ FormDocument undo / redo
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
__import__("PyQt6.QtWebEngineWidgets")  # must come before the QApplication
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
app = QApplication(sys.argv[:1])
QSettings().clear()
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
for _n in ("warning", "critical", "information"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))

from radide.document import FormDocument  # noqa: E402
from radide.model import Form  # noqa: E402

doc = FormDocument(Form(), SCRATCH / "F.form")
b1 = doc.add_control("Button", 10, 10)
doc.add_control("Label", 10, 50)
got: list = []
doc.codeRenamed.connect(lambda o, n: got.append((o, n)))
first = b1.name
doc.set_prop(b1, "Name", "btnOK")
ok("a rename itself does not emit codeRenamed (renamed does)", got == [])
doc.undo()
ok("Undo of a rename -> codeRenamed(btnOK, first name)", got == [("btnOK", first)], got)
doc.redo()
ok("Redo -> codeRenamed(first name, btnOK)", got[-1:] == [(first, "btnOK")], got)
got.clear()
doc.add_control("TextBox", 10, 90)
doc.undo()
ok("Undo of an add renames nothing", got == [], got)
c = doc.form.find("btnOK")
doc.checkpoint()
doc.set_geometry(c, 40, 40, 80, 30)
doc.undo()
ok("Undo of a move renames nothing", got == [], got)
ok("a swap is left alone", FormDocument._renames([("Button", "A"), ("Button", "B")],
                                                [("Button", "B"), ("Button", "A")]) == [])

# ------------------------------------------------------------------ the real IDE
try:
    from radide import workspace
    from radide.app import MainWindow
    proj = SCRATCH / "RenPy"
    workspace.create_project(proj, "RenPy", "python-tk")
    win = MainWindow()
    win.resize(1200, 800)
    win.show()
    app.processEvents()
    win.open_project(proj, ask=False)
    win.open_designer("Form1")
    d = win._doc("Form1")
    btn = d.add_control("Button", 20, 20)
    old = btn.name
    win.goto_event("Form1", btn, "Click")
    cv = win._codeview("Form1")
    code = cv.editor.text()
    ok("double-click wrote the Click handler", f"{old}_Click" in code, code[-600:])
    marker = f'        print("Press {old}")  # {old} note\n'
    lines = code.splitlines(keepends=True)
    at = next(i for i, ln in enumerate(lines) if f"def {old}_Click" in ln)
    lines.insert(at + 1, marker)
    win._replace_code(cv, "".join(lines))
    win.open_designer("Form1")
    d.select(btn)
    win.properties._set("Name", "btnOK")
    code = cv.editor.text()
    ok("rename from the Properties window renames the handler", "def btnOK_Click" in code, code[-800:])
    ok("... but not the text of the string / comment", marker in code, code[-800:])
    win.edit_undo() if win._current_designer() else d.undo()
    code = cv.editor.text()
    ok("Undo in the designer: the code is back to the first name",
       f"def {old}_Click" in code and "btnOK" not in code and d.form.find(old) is not None, code[-800:])
    d.redo()
    code = cv.editor.text()
    ok("Redo: the code is btnOK again", "def btnOK_Click" in code and f"def {old}_Click" not in code, code[-800:])
    ok("string kept through undo / redo", marker in code)
    cv.editor.setModified(False)
    d.set_modified(False)
    win.close()
except Exception as e:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    ok("IDE part", False, e)

QSettings().clear()
fails = sum(1 for _n, c in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
os._exit(fails)
