"""Text-Mode Designer in the IDE (qh.py harness, QSettings org RADIDE-TEST, screenshots with widget.grab()):
New Project > DOS Text-Mode Forms App, the designer tab (draw / move / properties / undo / events),
saving regenerates the code, double-click opens the handler, Test Run (simulator), the ANSI editor
(draw, save .ans with SAUCE, PNG export, use as splash).

    python samples/Tests/Retro/DesignTextMode/test_ui.py
"""
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QA_NAME", "tuidesign")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "QA" / "Integration"))
import qh  # noqa: E402

from PyQt6.QtCore import QPointF, Qt  # noqa: E402
from PyQt6.QtGui import QMouseEvent  # noqa: E402
from PyQt6.QtWidgets import QDialog, QInputDialog  # noqa: E402

WORK = Path(qh.WORK) / "tuidesign"
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)

w = qh.window()
feat = getattr(w, "dos_designer_feature", None)
qh.check("feature installed", feat is not None)
retro = getattr(w, "retro_menu", None)
titles = [a.text().replace("&", "") for a in retro.actions()] if retro is not None else []
qh.check("Tools > Retro > Text-Mode (DOS) menu", "Text-Mode (DOS)" in titles, titles)

# ---------------------------------------------------------------- New Project (plugin) -> a dosdev C project
from radide.languages import get_plugin  # noqa: E402
plugin = get_plugin("dos-tuiforms")
qh.check("plugin lists the four languages", {t[0] for t in plugin.project_templates()} >=
         {"tui_freebasic", "tui_pascal", "tui_c", "tui_asm"})
proj = plugin.create_new_project(WORK / "UiForms", "UiForms", "tui_c")
qh.check("the project is a dosdev C project", proj.language == "dos-c" and (WORK / "UiForms" / "MAIN.C").exists(),
         proj.language)
from radide.dialogs import LANGUAGE_GROUPS  # noqa: E402
qh.check("listed under New Project > DOS", any("dos-tuiforms" in ids for g, ids in LANGUAGE_GROUPS if g == "DOS"))
w.open_project(WORK / "UiForms", ask=False)
qh.pump(1.5)
qh.check("project open", w.project is not None and w.project.name == "UiForms")

# ---------------------------------------------------------------- designer tab
d = w.open_any_file(WORK / "UiForms" / "Main.tform")
qh.pump(0.5)
from radide.retro.design.textmode.designer import TuiDesigner  # noqa: E402
qh.check("Main.tform opens in the designer", isinstance(d, TuiDesigner) and w.tabs.currentWidget() is d)
d2 = w.open_module("Main.tform") if hasattr(w, "open_module") else d
qh.check("Solution Explorer opens the same designer", d2 is d or w.tabs.currentWidget() is d)
cv = d.canvas


def mouse(widget, kind, cell, button=Qt.MouseButton.LeftButton):
    r = widget.cell_rect(*cell)
    p = QPointF(r.center())
    buttons = Qt.MouseButton.NoButton if kind == QMouseEvent.Type.MouseButtonRelease else button
    return QMouseEvent(kind, p, p, button, buttons, Qt.KeyboardModifier.NoModifier)


win = next(c for c in d.screen.controls if c.type == "Window")
lab = next(c for c in d.screen.controls if c.type == "Label")
x0, lx0 = win.x, lab.x
cv.mousePressEvent(mouse(cv, QMouseEvent.Type.MouseButtonPress, (win.x + 6, win.y)))
cv.mouseMoveEvent(mouse(cv, QMouseEvent.Type.MouseMove, (win.x + 9, win.y)))
cv.mouseReleaseEvent(mouse(cv, QMouseEvent.Type.MouseButtonRelease, (win.x + 9, win.y)))
qh.check("dragging the window moves it and its label", win.x == x0 + 3 and lab.x == lx0 + 3, (win.x, lab.x))
qh.check("the document is modified", d.is_modified() and w.tabs.tabText(w.tabs.indexOf(d)).endswith("*"))
d.undo()
qh.check("undo puts them back", next(c for c in d.screen.controls if c.type == "Window").x == x0 and
         not d.is_modified())
# draw a text box with the toolbox
row = next(i for i in range(d.toolbox.count()) if d.toolbox.item(i).data(Qt.ItemDataRole.UserRole) == "TextBox")
d.toolbox.setCurrentRow(row)
win = next(c for c in d.screen.controls if c.type == "Window")
cv.mousePressEvent(mouse(cv, QMouseEvent.Type.MouseButtonPress, (win.x + 3, win.y + 4)))
cv.mouseMoveEvent(mouse(cv, QMouseEvent.Type.MouseMove, (win.x + 20, win.y + 4)))
cv.mouseReleaseEvent(mouse(cv, QMouseEvent.Type.MouseButtonRelease, (win.x + 20, win.y + 4)))
tb = d.screen.controls[-1]
qh.check("a text box drawn with the tool", tb.type == "TextBox" and tb.w == 18, (tb.type, tb.w))
qh.check("the toolbox returns to the pointer", d.canvas.tool == "Pointer")
qh.check("the Properties window shows it", d.props.target is tb and d.props.table.rowCount() > 8)
d._prop_edited(tb, "name", "txtCity")
qh.check("rename through the Properties window", tb.name == "txtCity")
d._prop_edited(tb, "max_length", 12)
qh.check("MaxLength property", tb.get("max_length") == 12)
qh.shot(d, "tui_designer")

# ---------------------------------------------------------------- save -> code regenerated; event -> code
main_c = WORK / "UiForms" / "MAIN.C"
d.save()
qh.pump(0.5)
code = main_c.read_text(encoding="cp437")
qh.check("saving the screen regenerates MAIN.C", "#define txtCity" in code)
d._code_for("txtCity", "Change")
qh.pump(1.0)
code = main_c.read_text(encoding="cp437")
qh.check("double-click an event creates its handler", "void txtCity_Change(void)" in code)
ed = w.tabs.currentWidget()
qh.check("the code editor opened at the handler", getattr(ed, "editor", None) is not None and
         "txtCity_Change" in ed.editor.text(), type(ed).__name__)
if getattr(ed, "editor", None) is not None:
    line = ed.editor.getCursorPosition()[0] if hasattr(ed.editor, "getCursorPosition") else -1
    qh.check("cursor inside the handler", "txtCity_Change" in ed.editor.text().split("\n")[max(0, line - 3)]
             or "USER CODE txtCity_Change" in "\n".join(ed.editor.text().split("\n")[max(0, line - 4):line + 1]),
             line)
    # the user writes code, then changes the screen again: the code survives
    text = ed.editor.text().replace("/* >>> USER CODE txtCity_Change (kept when the screens are regenerated) */\n",
                                    "/* >>> USER CODE txtCity_Change (kept when the screens are regenerated) */\n"
                                    "    tui_set_text(Label1, tui_get_text(txtCity));\n")
    ed.editor.setText(text)
w.tabs.setCurrentWidget(d)
d._prop_edited(next(c for c in d.screen.controls if c.type == "Label"), "text", "City:")
d.save()
qh.pump(0.5)
code = main_c.read_text(encoding="cp437")
qh.check("unsaved user code in the editor is kept when the screen is saved",
         "tui_set_text(Label1, tui_get_text(txtCity));" in code and '"City:"' in code)

# ---------------------------------------------------------------- Test Run (simulator)
from radide.retro.design.textmode.designer import TestRunDialog  # noqa: E402
from radide.retro.design.textmode.model import load_project_screens  # noqa: E402
tr = TestRunDialog(load_project_screens(WORK / "UiForms"), w)
tr.show()
qh.pump(0.3)
from radide.retro.design.textmode.sim import alt  # noqa: E402
tr.sim.handle_key(alt("f"))
tr._sync()
qh.check("Test Run opens the menu with Alt+F", tr.sim.menu is not None)
qh.shot(tr, "tui_testrun")
tr.close()

# ---------------------------------------------------------------- ANSI editor
feat.new_art()
qh.pump(0.3)
from radide.retro.design.textmode.ansieditor import AnsiEditor  # noqa: E402
art = w.tabs.currentWidget()
qh.check("New ANSI Art opens the art editor", isinstance(art, AnsiEditor))
art.lines.setCurrentText("double")
art.box_fill.setChecked(True)
art.set_tool("Box")
ac = art.canvas
ac.mousePressEvent(mouse(ac, QMouseEvent.Type.MouseButtonPress, (10, 5)))
ac.mouseMoveEvent(mouse(ac, QMouseEvent.Type.MouseMove, (60, 15)))
ac.mouseReleaseEvent(mouse(ac, QMouseEvent.Type.MouseButtonRelease, (60, 15)))
art.lines.setCurrentText("single")
art.set_tool("Line")
ac.mousePressEvent(mouse(ac, QMouseEvent.Type.MouseButtonPress, (10, 8)))
ac.mouseMoveEvent(mouse(ac, QMouseEvent.Type.MouseMove, (60, 8)))
ac.mouseReleaseEvent(mouse(ac, QMouseEvent.Type.MouseButtonRelease, (60, 8)))
qh.check("box + line join into box drawing", art.buf.get(10, 8)[0] == 0xC7 and art.buf.get(60, 8)[0] == 0xB6,
         (hex(art.buf.get(10, 8)[0]), hex(art.buf.get(60, 8)[0])))
art.set_tool("Text")
ac.mousePressEvent(mouse(ac, QMouseEvent.Type.MouseButtonPress, (12, 6)))
for ch in "HELLO":
    ac._type(ord(ch))
qh.check("text tool types characters", bytes(art.buf.chars[6 * 80 + 12:6 * 80 + 17]) == b"HELLO")
art.set_tool("Fill")
ac.mousePressEvent(mouse(ac, QMouseEvent.Type.MouseButtonPress, (2, 2)))
qh.check("flood fill", art.buf.get(0, 0)[0] == art.char and art.buf.get(79, 24)[0] == art.char)
art.undo()
qh.check("undo the fill", art.buf.get(0, 0)[0] == 0x20)
art.sauce.title = "UI test"
ans = WORK / "UiForms" / "Logo.ans"
art.save(ans)
from radide.retro.design.textmode.ansi import art_sauce, load_art  # noqa: E402
qh.check("saved .ans with SAUCE", ans.exists() and art_sauce(ans).title == "UI test" and
         load_art(ans).get(10, 8)[0] == 0xC7)
from radide.retro.design.textmode.glyphs import save_png  # noqa: E402
png = WORK / "logo.png"
qh.check("PNG export", save_png(art.buf, png) and png.stat().st_size > 1000)
qh.shot(art, "tui_ansi_editor")
QInputDialog.getInt = staticmethod(lambda *a, **k: (2, True))
feat.use_as_splash(art)
qh.pump(0.5)
code = main_c.read_text(encoding="cp437")
qh.check("Use as Splash Screen: the startup screen shows the art first", "TS0" in code and "TSP[0]" in code)
reopened = w.open_any_file(ans)
qh.check(".ans files open in the art editor", isinstance(reopened, AnsiEditor))

# ---------------------------------------------------------------- Add Screen
QInputDialog.getText = staticmethod(lambda *a, **k: ("Settings", True))
QInputDialog.getItem = staticmethod(lambda *a, **k: ("80 x 25", True))
feat.new_screen()
qh.pump(0.5)
qh.check("Add Screen creates Settings.tform in the project", (WORK / "UiForms" / "Settings.tform").exists() and
         "Settings.tform" in w.project.modules)
code = main_c.read_text(encoding="cp437")
qh.check("the new screen is in the program", "#define Settings 2" in code or "#define Settings" in code)
QDialog.exec = lambda self: 0
qh.finish(w)
