"""Tutorials list (Polish item 2, done by another agent and not tested there): course titles are elided with a
tooltip holding the full text, no horizontal scroll bar, the list starts 300 px wide and remembers a new width.
Real IDE, offscreen, qh.py harness (QSettings org RADIDE-TEST, widget.grab only), English and Arabic UI.

    python samples/Tests/Tutorials/Polish/test_tree_ui.py
"""
import os
import sys

os.environ.setdefault("QA_NAME", "tutorials_tree")
_cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offscreen_1920.json")
try:                                    # a 1920 x 1080 offscreen screen (the default one is 800 x 600)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen:configfile=" + os.path.relpath(_cfg).replace("\\", "/"))
except ValueError:                      # another drive: keep the default screen
    pass
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "QA", "Integration"))
from qh import app, check, finish, pump, shot, window  # noqa: E402

from PyQt6.QtCore import QSettings, Qt  # noqa: E402

w = window()
panel = w.show_tutorials()
pump(1.5)
tree = panel.tree
check("tree elides long titles (ElideRight)", tree.textElideMode() == Qt.TextElideMode.ElideRight)
check("no horizontal scroll bar", tree.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
check("list starts 300 px wide (was 210), the lesson beside it", abs(panel.split.sizes()[0] - 300) <= 2
      and panel.split.sizes()[1] > 300, panel.split.sizes())
n = tree.topLevelItemCount()
missing = [tree.topLevelItem(i).text(0) for i in range(n)
           if tree.topLevelItem(i).text(0).split(chr(0x200E))[0].strip() not in tree.topLevelItem(i).toolTip(0)]
check(f"every course ({n}) has its full title in the tooltip", n > 10 and not missing, missing[:5])
kid = tree.topLevelItem(0).child(0) if n else None
check("lessons have tooltips too", kid is not None and bool(kid.toolTip(0)), kid.toolTip(0) if kid else None)
fm = tree.fontMetrics()
col = tree.columnWidth(0) or tree.viewport().width()
longest = max((fm.horizontalAdvance(tree.topLevelItem(i).text(0)) for i in range(n)), default=0)
check("long titles are wider than the column (so they are elided, not scrolled)", longest > col * 0.5, (longest, col))
shot(panel, "tutorials_tree_en")
panel.split.setSizes([360, 700])
panel.split.splitterMoved.emit(360, 1)
pump(0.2)
saved = int(QSettings().value("tutorials/list_width", 0) or QSettings().value(
    next((k for k in QSettings().allKeys() if k.endswith("list_width")), "x"), 0) or 0)
check("a new list width is remembered", 340 <= saved <= 380, saved)
check("the next panel starts with it", abs(panel._split_sizes()[0] - saved) <= 1, panel._split_sizes())

w.dock_tutorials.setFloating(True)          # a narrow panel (small screen): the lesson stays readable
w.dock_tutorials.resize(520, 700)
pump(0.5)
sz = panel.split.sizes()
check("narrow panel: the list gives way so the lesson keeps >= 45 %", sz[1] >= 0.45 * sum(sz) and sz[0] >= 150, sz)
check("narrow panel: the remembered width is not overwritten", abs(panel._split_sizes()[0] - saved) <= 1,
      panel._split_sizes())
w.dock_tutorials.setFloating(False)
pump(0.3)
from radide import i18n  # noqa: E402
i18n.set_language(app, "ar")
pump(0.5)
panel.hide()
panel.show()
pump(0.8)
check("Arabic UI: the tree is right-to-left", tree.layoutDirection() == Qt.LayoutDirection.RightToLeft)
shot(panel, "tutorials_tree_ar")
i18n.set_language(app, "en")
finish(w)
