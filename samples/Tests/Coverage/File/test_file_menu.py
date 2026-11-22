"""Coverage: the File menu (functional, offscreen IDE, sandbox copies of the samples).

* File > Open File (Ctrl+O): QFileDialog.getOpenFileName returns a sandbox text file -> it opens in an editor
  tab holding the file's text.
* File > New Image > Icon (.ico) / Cursor (.cur) / Image (.png / .bmp): the New Image dialog opens preset to the
  right kind; OK opens the image editor (IconEditor) on a file saved into the project's Resources folder with a
  valid header (ICO type 1 / CUR type 2 with the chosen sizes / PNG); a pixel drawn and saved is in the file.
* File > App Gallery: the dialog lists every web template of radide.web_site.gallery; Cancel creates nothing.
* File > New Project (.NET, Visual Studio 2022) (Ctrl+Alt+Shift+N): the "Create a new project" wizard lists the
  .NET templates, the search box filters them; Cancel creates nothing.
* File > Import > Python GUI Program (Tkinter / Qt): a small tkinter script written into the sandbox becomes a
  RAD IDE project (<name>_RAD) whose Form1 holds its Label / TextBox / Button, and the project is opened.
* File > Open Folder (Ctrl+K, Ctrl+O): QFileDialog.getExistingDirectory returns a plain sandbox folder -> it
  opens as a folder workspace whose (code / text) files are listed in Solution Explorer.
* File > New Notebook > Import Python Script as Notebook: a percent-format script becomes <name>.ipynb with one
  cell per "# %%" block (markdown cell included) and opens in a notebook tab.
* File > New Notebook > Open Notebook: an existing .ipynb opens in a notebook tab with its cells.

The editor engine is set to the built-in editor (editor/engine) so editor text is read synchronously offscreen
(no QtWebEngine / Monaco warm-up).

Run:  .venv\\Scripts\\python samples\\Tests\\Coverage\\File\\test_file_menu.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cov_harness as H  # noqa: E402
from cov_harness import (C, action, check, clear_modal_handlers, finish, on_modal, open_sample, pump,  # noqa: E402
                         sandbox, start, wait)

_orig_window = C.window


def _window_builtin_editor():
    from radide.app import ide_settings
    ide_settings().setValue("editor/engine", "builtin")
    return _orig_window()


C.window = _window_builtin_editor

w = start("file_menu")
from PyQt6.QtWidgets import QApplication, QFileDialog  # noqa: E402

SB = sandbox()
proj = open_sample(w, "python-tk")
check("Python Tk sample opened", w.project is not None and w.project.language == "python-tk")


def widget_text(wd) -> str:
    for obj in (getattr(wd, "editor", None), wd):
        if obj is None:
            continue
        for meth in ("text", "toPlainText"):
            f = getattr(obj, meth, None)
            if callable(f):
                try:
                    t = f()
                except TypeError:
                    continue
                if isinstance(t, str):
                    return t
    return ""


class patched_dialog:
    """QFileDialog.<name> returns *value* while the block runs (no dialog is shown)."""
    def __init__(self, name, value):
        self.name, self.value, self.calls = name, value, []

    def __enter__(self):
        self.orig = QFileDialog.__dict__.get(self.name)
        setattr(QFileDialog, self.name, staticmethod(lambda *a, **k: (self.calls.append(a), self.value)[1]))
        return self

    def __exit__(self, *exc):
        setattr(QFileDialog, self.name, self.orig)
        return False


# ------------------------------------------------------------------ File > Open File
docs = SB / "docs"
docs.mkdir(exist_ok=True)
notes = docs / "notes.txt"
notes.write_text("Coverage notes\nline two: open-file-marker-4711\n", encoding="utf-8")
a = action(w, "File", "Open File")
check("File > Open File exists with Ctrl+O", a is not None and a.shortcut().toString() == "Ctrl+O",
      a and a.shortcut().toString())
with patched_dialog("getOpenFileName", (str(notes), "All files (*)")) as pd:
    H.trigger(a, 1.0)
check("Open File asked for a file", len(pd.calls) == 1, pd.calls)
cur = w.tabs.currentWidget()
check("Open File: an editor tab named notes.txt is current",
      cur is not None and "notes.txt" in w.tabs.tabText(w.tabs.currentIndex()),
      w.tabs.tabText(w.tabs.currentIndex()))
check("Open File: the tab holds the file's text", "open-file-marker-4711" in widget_text(cur),
      (type(cur).__name__, widget_text(cur)[:200]))

# ------------------------------------------------------------------ File > New Image
seen_kind = []


def new_image_ok(name):
    def h(dlg):
        if type(dlg).__name__ != "NewImageDialog":
            return False
        seen_kind.append((dlg.kind.currentText(), dlg.extension()))
        if dlg.extension() == ".png":
            dlg.w.setValue(40)
            dlg.h.setValue(30)
        dlg.name.setText(name)
        dlg.accept()
        return True
    return h


res = proj / "Resources"
for item, name, ext, magic in (("Icon (.ico)", "CovIcon", ".ico", b"\x00\x00\x01\x00"),
                               ("Cursor (.cur)", "CovCursor", ".cur", b"\x00\x00\x02\x00"),
                               ("Image (.png / .bmp)", "CovImage", ".png", b"\x89PNG\r\n\x1a\n")):
    clear_modal_handlers()
    seen_kind.clear()
    on_modal(new_image_ok(name))
    a = action(w, "File", "New Image", item)
    check(f"File > New Image > {item} exists", a is not None)
    H.trigger(a, 0.8)
    check(f"New Image > {item}: the dialog is preset to {ext}", seen_kind and seen_kind[0][1] == ext, seen_kind)
    f = res / f"{name}{ext}"
    check(f"New Image > {item}: Resources/{f.name} written", wait(f.exists, 5), sorted(p.name for p in res.glob("*"))
          if res.exists() else "no Resources folder")
    data = f.read_bytes() if f.exists() else b""
    check(f"New Image > {item}: valid {ext} header", data.startswith(magic), data[:8])
    if ext in (".ico", ".cur"):
        n = int.from_bytes(data[4:6], "little") if len(data) >= 6 else 0
        check(f"New Image > {item}: the 4 default sizes (16, 32, 48, 256) are stored", n == 4, n)
    ed = w.tabs.currentWidget()
    check(f"New Image > {item}: the image editor is the current tab", type(ed).__name__ == "IconEditor",
          type(ed).__name__)
    if type(ed).__name__ == "IconEditor":
        check(f"New Image > {item}: the editor edits that file",
              ed.doc.path is not None and Path(ed.doc.path).resolve() == f.resolve(), ed.doc.path)
        check(f"New Image > {item}: icon kind matches", bool(ed.doc.is_icon) == (ext != ".png"), ed.doc.is_icon)
        if ext == ".png":
            check("New Image > PNG: the chosen 40x30 size", (ed.doc.frame.width, ed.doc.frame.height) == (40, 30),
                  (ed.doc.frame.width, ed.doc.frame.height))
        from PyQt6.QtGui import QColor
        ed.doc.checkpoint()
        ed.doc.set_pixel(2, 3, QColor(255, 0, 0, 255))
        check(f"New Image > {item}: drawing marks the document modified", ed.is_modified())
        ok = ed.save()
        check(f"New Image > {item}: Save succeeds and clears the modified flag", ok and not ed.is_modified())
        from radide.imaging.document import ImageDocument
        back = ImageDocument(f)
        px = back.pixel(2, 3, merged=True)
        check(f"New Image > {item}: the drawn pixel is in the saved file", (px.red(), px.green(), px.alpha()) ==
              (255, 0, 255), (px.red(), px.green(), px.blue(), px.alpha()))
clear_modal_handlers()

# ------------------------------------------------------------------ File > App Gallery (list + Cancel)
from radide.web_site import gallery  # noqa: E402

gal = {}
gal_loc = SB / "gallery"
gal_loc.mkdir(exist_ok=True)


def gallery_cancel(dlg):
    if type(dlg).__name__ != "AppGalleryDialog":
        return False
    from PyQt6.QtCore import Qt
    gal["ids"] = [dlg.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(dlg.list.count())]
    gal["titles"] = [dlg.list.item(i).text() for i in range(dlg.list.count())]
    dlg.location.setText(str(gal_loc))
    gal["name"] = dlg.name.text()
    gal["details"] = dlg.details.text()
    dlg.search.setText("wordpress")
    gal["visible_wp"] = [dlg.list.item(i).text() for i in range(dlg.list.count()) if not dlg.list.item(i).isHidden()]
    dlg.search.setText("")
    dlg.reject()
    return True


on_modal(gallery_cancel)
a = action(w, "File", "App Gallery")
check("File > App Gallery exists", a is not None)
H.trigger(a, 1.0)
check("App Gallery dialog opened", "ids" in gal, gal)
check("App Gallery lists every gallery template", gal.get("ids") == [t.id for t in gallery.TEMPLATES],
      (gal.get("ids"), [t.id for t in gallery.TEMPLATES]))
check("App Gallery lists PHP + SQLite, Bootstrap and WordPress",
      all(any(x in t for t in gal.get("titles", [])) for x in ("PHP + SQLite", "Bootstrap", "WordPress")),
      gal.get("titles"))
check("App Gallery preselects a template and proposes a site name", bool(gal.get("name")) and
      "<h3" in gal.get("details", ""), (gal.get("name"), gal.get("details", "")[:200]))
check("App Gallery search 'wordpress' leaves only WordPress", gal.get("visible_wp") == ["WordPress"],
      gal.get("visible_wp"))
check("App Gallery Cancel creates nothing", not any(gal_loc.iterdir()), list(gal_loc.iterdir()))
check("App Gallery Cancel keeps the project", w.project is not None and Path(w.project.folder) == proj)
clear_modal_handlers()

# ------------------------------------------------------------------ File > New Project (.NET, Visual Studio 2022)
wiz = {}
dn_loc = SB / "dotnet"


def wizard_cancel(dlg):
    if type(dlg).__name__ != "NewProjectWizard":
        return False
    wiz["title"] = dlg.windowTitle()
    wiz["count"] = dlg.list.count()
    wiz["texts"] = [dlg.list.item(i).text() for i in range(dlg.list.count())]
    wiz["templates"] = len(dlg.templates)
    dlg.search.setText("console")
    pump(0.2)
    wiz["console"] = [dlg.list.item(i).text() for i in range(dlg.list.count()) if not dlg.list.item(i).isHidden()]
    dlg.loc_edit.setText(str(dn_loc))
    dlg.reject()
    wiz["result"] = dlg.result_info
    return True


on_modal(wizard_cancel)
a = action(w, "File", "New Project (.NET, Visual Studio 2022)")
check("File > New Project (.NET, Visual Studio 2022) has Ctrl+Alt+Shift+N",
      a is not None and a.shortcut().toString() == "Ctrl+Alt+Shift+N", a and a.shortcut().toString())
H.trigger(a, 1.0)
check(".NET wizard opened as 'Create a new project'", wiz.get("title") == "Create a new project", wiz.get("title"))
check(".NET wizard lists its templates (10+)", wiz.get("count", 0) >= 10 and wiz.get("templates", 0) >= 10,
      (wiz.get("count"), wiz.get("templates")))
alltext = " | ".join(wiz.get("texts", []))
check(".NET wizard lists Console App and Windows Forms App", "Console" in alltext and "Windows Forms" in alltext,
      alltext[:600])
check(".NET wizard search 'console' filters the list",
      wiz.get("console") and all("console" in t.lower() or "\n" in t for t in wiz["console"]) and
      len(wiz["console"]) < wiz.get("count", 0), wiz.get("console"))
check(".NET wizard Cancel returns no project", wiz.get("result") is None)
check(".NET wizard Cancel creates nothing", not dn_loc.exists())
clear_modal_handlers()

# ------------------------------------------------------------------ File > Import > Python GUI Program
imp_src = SB / "tkapp" / "calc.py"
imp_src.parent.mkdir(exist_ok=True)
imp_src.write_text('''import tkinter as tk

root = tk.Tk()
root.title("Calc")
root.geometry("320x200")
lbl = tk.Label(root, text="Amount:")
lbl.place(x=10, y=12)
ent = tk.Entry(root)
ent.place(x=90, y=12, width=120)


def on_go():
    print(ent.get())


btn = tk.Button(root, text="Go", command=on_go)
btn.place(x=10, y=60)
root.mainloop()
''', encoding="utf-8")
imp_dest = SB / "imports"
imp_dest.mkdir(exist_ok=True)
w.save_all()
infos = []


def import_report(dlg):
    if type(dlg).__name__ != "QMessageBox":
        return False
    infos.append(dlg.windowTitle())
    dlg.accept()
    return True


on_modal(import_report)
a = action(w, "File", "Import", "Python GUI Program (Tkinter / Qt)")
check("File > Import > Python GUI Program exists", a is not None)
with patched_dialog("getOpenFileName", (str(imp_src), "")), patched_dialog("getExistingDirectory", str(imp_dest)):
    H.trigger(a, 0.5)
target = imp_dest / "calc_RAD"
check("Import: the project file calc_RAD/project.radproj is written", wait((target / "project.radproj").exists, 90),
      list(imp_dest.glob("*")))
check("Import: the original script is kept in _original", (target / "_original" / "calc.py").exists())
check("Import: the new project is opened", wait(lambda: w.project is not None and
                                                 Path(w.project.folder).resolve() == target.resolve(), 15),
      w.project and w.project.folder)
check("Import: a report was shown", "Import Python Program" in infos, infos)
form_file = target / "Form1.form"
ctrls = []
if form_file.exists():
    fj = json.loads(form_file.read_text(encoding="utf-8"))
    ctrls = [(c["type"], c["props"].get("Text", "")) for c in fj.get("controls", [])]
    check("Import: Form1 keeps the window title 'Calc'", fj["props"].get("Text") == "Calc", fj["props"].get("Text"))
check("Import: Form1 holds the Label 'Amount:'", ("Label", "Amount:") in ctrls, ctrls)
check("Import: Form1 holds the Button 'Go'", ("Button", "Go") in ctrls, ctrls)
check("Import: Form1 holds a TextBox for the Entry", any(t == "TextBox" for t, _ in ctrls), ctrls)
code = (target / "Form1.py").read_text(encoding="utf-8") if (target / "Form1.py").exists() else ""
check("Import: the Button's command became a handler in Form1.py", "def " in code and "print(" in code, code[:600])
clear_modal_handlers()

# ------------------------------------------------------------------ File > Open Folder
folder = SB / "plainfolder"
(folder / "sub").mkdir(parents=True, exist_ok=True)
(folder / "todo.txt").write_text("todo\n", encoding="utf-8")
(folder / "main.py").write_text("print('hi')\n", encoding="utf-8")
(folder / "sub" / "inner.txt").write_text("inner\n", encoding="utf-8")
w.save_all()
a = action(w, "File", "Open Folder")
check("File > Open Folder has Ctrl+K, Ctrl+O", a is not None and a.shortcut().toString() == "Ctrl+K, Ctrl+O",
      a and a.shortcut().toString())
with patched_dialog("getExistingDirectory", str(folder)) as pd:
    H.trigger(a, 2.0)
check("Open Folder asked for a folder", len(pd.calls) == 1)


def tree_texts():
    out = []
    t = w.solution
    stack = [t.topLevelItem(i) for i in range(t.topLevelItemCount())]
    while stack:
        it = stack.pop()
        out.append(it.text(0).split("  [")[0])      # "todo.txt  [VS Code folder]": the language tag dropped
        it.setExpanded(True)
        stack.extend(it.child(i) for i in range(it.childCount()))
    return out


check("Open Folder: Solution Explorer lists todo.txt and main.py",
      wait(lambda: {"todo.txt", "main.py"} <= set(tree_texts()), 10), tree_texts()[:40])
check("Open Folder: the file of the sub folder is listed (sub/inner.txt)",
      any(t.replace("\\", "/") == "sub/inner.txt" for t in tree_texts()), tree_texts()[:40])
check("Open Folder: the folder is the open project/workspace", w.project is not None and
      Path(w.project.folder).resolve() == folder.resolve(), w.project and w.project.folder)

# ------------------------------------------------------------------ File > New Notebook (QtWebEngine views last)
nb_src = SB / "nb" / "analysis.py"
nb_src.parent.mkdir(exist_ok=True)
nb_src.write_text("# %% [markdown]\n# # Sales analysis\n\n# %%\ntotal = sum([1, 2, 3])\n\n# %%\nprint(total * 2)\n",
                  encoding="utf-8")
a = action(w, "File", "New Notebook", "Import Python Script as Notebook")
check("File > New Notebook > Import Python Script as Notebook exists", a is not None)
with patched_dialog("getOpenFileName", (str(nb_src), "")):
    H.trigger(a, 2.0)
nb_file = nb_src.with_suffix(".ipynb")
check("Import as Notebook: analysis.ipynb written next to the script", nb_file.exists())
nbj = json.loads(nb_file.read_text(encoding="utf-8")) if nb_file.exists() else {}
cells = nbj.get("cells", [])
src = ["".join(c.get("source", "")) if isinstance(c.get("source"), list) else c.get("source", "") for c in cells]
check("Import as Notebook: valid nbformat 4", nbj.get("nbformat") == 4, nbj.get("nbformat"))
check("Import as Notebook: 3 cells (markdown + 2 code)",
      [c.get("cell_type") for c in cells] == ["markdown", "code", "code"], [c.get("cell_type") for c in cells])
check("Import as Notebook: the cells hold the script's blocks",
      len(src) == 3 and src[0].strip() == "# Sales analysis" and "total = sum" in src[1] and "print(total" in src[2],
      src)
cur = w.tabs.currentWidget()
check("Import as Notebook: opens in a notebook tab", type(cur).__name__ == "NotebookView" and
      "analysis.ipynb" in w.tabs.tabText(w.tabs.currentIndex()), (type(cur).__name__,
                                                                   w.tabs.tabText(w.tabs.currentIndex())))

nb2 = SB / "nb" / "existing.ipynb"
nb2.write_text(json.dumps({"cells": [
    {"cell_type": "markdown", "id": "m1", "metadata": {}, "source": ["# Existing notebook"]},
    {"cell_type": "code", "id": "c1", "metadata": {}, "execution_count": None, "outputs": [],
     "source": ["x = 40 + 2\n", "x"]}],
    "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}},
    "nbformat": 4, "nbformat_minor": 5}), encoding="utf-8")
a = action(w, "File", "New Notebook", "Open Notebook")
check("File > New Notebook > Open Notebook exists", a is not None)
with patched_dialog("getOpenFileName", (str(nb2), "")):
    H.trigger(a, 2.0)
cur = w.tabs.currentWidget()
check("Open Notebook: existing.ipynb opens in a notebook tab", type(cur).__name__ == "NotebookView" and
      "existing.ipynb" in w.tabs.tabText(w.tabs.currentIndex()), (type(cur).__name__,
                                                                    w.tabs.tabText(w.tabs.currentIndex())))
if type(cur).__name__ == "NotebookView":
    srcs = [c.source for c in cur.notebook.cells]
    check("Open Notebook: the view holds the file's 2 cells", len(srcs) == 2 and "x = 40 + 2" in srcs[1], srcs)
check("no modal dialog left open", QApplication.activeModalWidget() is None)
if H.tracebacks(w):                         # the details of a feature that failed to load
    print(H.output_text(w)[-3000:], flush=True)
finish(w)
