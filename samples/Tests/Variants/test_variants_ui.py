"""UI test of layout variants in the form designer (plan MOTION_VARIANTS_FOLDABLES slice C), offscreen with qh.py.

Opens samples/Tests/Variants/Variants_Qt_Responsive (copied to a temp folder) in the IDE and checks the
sizes bar (Edit: All sizes | This size only, size combo, Add Size..., Edit Sizes..., Hide on this size,
Side-by-side), the orange banner, the size preview (anchored / docked controls follow, hidden controls
hatched), This size only edits from the Properties window and from mouse drags going to the size only,
undo / redo, the Properties markers and context menu (Apply to all sizes / Reset to base / Copy to /
Hide on this size), All sizes edits while a size is shown (geometry by the same distance), the precedence
rules (Language, Blend record), the Sizes gallery, generated code on save and the Arabic catalog.

Run:  python samples/Tests/Variants/test_variants_ui.py
"""
import json
import os
import shutil
import sys

os.environ.setdefault("QA_NAME", "variants_ui")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "QA", "Integration"))
from qh import ROOT, WORK, check, finish, pump, shot, window  # noqa: E402
from pathlib import Path  # noqa: E402

from PyQt6.QtCore import QPoint, Qt, QTimer  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QMenu  # noqa: E402

src = Path(ROOT) / "samples/Tests/Variants/Variants_Qt_Responsive"
d = Path(WORK) / "Variants_Qt_Responsive"
shutil.rmtree(d, ignore_errors=True)
shutil.copytree(src, d)

w = window()
w.open_project(d, ask=False)
pump(1.5)
w.open_designer("Form1")
pump(1.0)
view = w._current_designer()
check("designer opened", view is not None)
from radide.features import variants as fv  # noqa: E402
from radide.variants import model as vm  # noqa: E402

vp = getattr(view, "_variant_preview", None)
bar = getattr(view, "_variant_bar", None)
check("VariantPreview + sizes bar attached to the designer", vp is not None and bar is not None)
check("bar sits above the form (viewport margin)", bar.isVisible() and view.viewportMargins().top() == fv.BAR_H,
      view.viewportMargins().top())
doc = view.doc
form = doc.form
props_panel = w.properties
side, search, save, title, items = (form.find(n) for n in ("pnlSide", "txtSearch", "btnSave", "lblTitle",
                                                         "lstItems"))
base_snapshot = form.snapshot()


def row_of(name):
    t = props_panel.props
    for r in range(t.rowCount()):
        dd = props_panel._row_def(r)
        if dd is not None and dd.name == name:
            return t.item(r, 0)
    return None


# ---------------------------------------------------------------- base: nothing changes
check("combo lists Base design + 3 sizes", bar.combo.count() == 4, [bar.combo.itemText(i) for i in range(4)])
check("not active: design_props is the model", not vp.active and view.design_props(search) is search.props)
check("All sizes checked, This size only not", bar.btn_all.isChecked() and not bar.btn_this.isChecked())
check("live drags allowed in the base design", view.live_drag_ok())
shot(view, "variants_base")

# ---------------------------------------------------------------- pick Phone (preview)
bar.combo.setCurrentIndex(bar.combo.findData("phone"))
bar.combo.activated.emit(bar.combo.currentIndex())
pump(0.4)
fp = view.form_props()
check("Phone shown at its 400 x 700 preview", vp.active and (fp["Width"], fp["Height"]) == (400, 700),
      (fp["Width"], fp["Height"]))
check("frame follows the preview size", view.surface.width() == 400 and view.surface.height() == 700,
      (view.surface.width(), view.surface.height()))
sp = view.design_props(search)
check("search box at the Phone geometry (16, 368 wide)", (sp["Left"], sp["Width"]) == (16, 368), sp)
check("side menu hidden on Phone (hatched), base still visible", vp.hidden(side) and side.props["Visible"])
check("banner says Preview (no orange frame) in All sizes mode", bar.banner.mode == "preview", bar.banner.mode)
check("model untouched by the preview", form.snapshot() == base_snapshot)
pw = view.previews[id(title)]
check("title preview shows the Phone text", "phone" in (pw.text() if hasattr(pw, "text") else str(pw.property("text"))),
      pw.text() if hasattr(pw, "text") else "")
doc.select(search)
pump(0.3)
r = row_of("Left")
check("Properties: Left of txtSearch marked as changed on this size (filled diamond)",
      r is not None and r.text().startswith("◆") and "Base value" in r.toolTip(), r.text() if r else None)
it = props_panel.props.item(props_panel.props.row(r), 1) if r is not None else None
check("Properties shows the Phone value 16", it is not None and it.text() == "16", it.text() if it else None)
shot(view, "variants_phone_preview")

# ---------------------------------------------------------------- This size only
bar.btn_this.click()
pump(0.4)
check("This size only on", vp.this_size and bar.btn_this.isChecked() and not bar.btn_all.isChecked())
check("orange banner frame", bar.banner.mode == "this" and bar.banner.isVisible() and "Phone" in bar.banner.text,
      bar.banner.text)
check("live drag path off in This size only", not view.live_drag_ok())
undo_before = len(doc._undo)
props_panel._set("Text", "Find a customer")
pump(0.3)
check("Properties edit went to the Phone size only",
      search.variants.get("phone", {}).get("Text") == "Find a customer" and search.props["Text"] == "",
      (search.variants, search.props["Text"]))
check("one undo step recorded", len(doc._undo) == undo_before + 1, (undo_before, len(doc._undo)))
check("designer shows the Phone text", view.previews[id(search)].text() == "Find a customer",
      view.previews[id(search)].text())
r = row_of("Text")
check("Text row gets the filled diamond", r is not None and r.text().startswith("◆"), r.text() if r else None)
doc.undo()
pump(0.3)
search = form.find("txtSearch")
check("undo removes the override", "Text" not in form.find("txtSearch").variants.get("phone", {}),
      form.find("txtSearch").variants)
doc.redo()
pump(0.3)
search = form.find("txtSearch")
check("redo brings it back", search.variants.get("phone", {}).get("Text") == "Find a customer")

# mouse drag of the status-less list: moves it on Phone only
items = form.find("lstItems")
base_left = items.props["Left"]
rect = view.overlay.abs_rect(items)
start = rect.center()
QTest.mousePress(view.overlay, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
for step in (4, 12, 24):
    QTest.mouseMove(view.overlay, start + QPoint(step, 16))
    pump(0.05)
QTest.mouseRelease(view.overlay, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start + QPoint(24, 16))
pump(0.3)
ov = items.variants.get("phone", {})
check("drag moved lstItems on Phone only (override, base Left kept)",
      ov.get("Left") == 40 and ov.get("Top") == 128 and items.props["Left"] == base_left, (ov, items.props["Left"]))
check("drag kept the Phone width (no base width written)", ov.get("Width") == 368, ov)
check("dragged control was not re-parented", items.props.get("Parent", "") == "")

# Hide on this size
save = form.find("btnSave")
doc.select(save)
pump(0.2)
check("Hide on this size enabled with a selection", bar.btn_hide.isEnabled())
bar.btn_hide.click()
pump(0.3)
check("Hide on this size: Visible False on Phone, base visible",
      save.variants["phone"].get("Visible") is False and save.props["Visible"] is True, save.variants)
check("hidden control hatched in the designer", vp.hidden(save))
check("button now reads Show on this size", bar.btn_hide.text() == "Show on this size" or bar.btn_hide.isChecked())
shot(view, "variants_this_size")
bar.btn_hide.click()
pump(0.2)
check("Show on this size again", save.variants.get("phone", {}).get("Visible", True) is True)

# Properties context menu actions
m = QMenu()
doc.prop_menu(m, save, "Left")
names = [a.text() for a in m.actions() if a.text()]
check("prop menu: Apply to all sizes / Reset to base / Copy to / Hide on this size",
      {"Apply to all sizes", "Reset to base", "Copy to", "Hide on this size"} <= set(names), names)
props_panel._set("Width", 200)
pump(0.2)
check("Width override on Phone", save.variants["phone"]["Width"] == 200)
fv.VariantPreview.of(view).copy_to(save, "Width", "tablet")
check("Copy to > Tablet", save.variants["tablet"]["Width"] == 200, save.variants)
vp.reset_to_base(save, "Width")
check("Reset to base removes the Phone Width", "Width" not in save.variants.get("phone", {}), save.variants)
vp.apply_to_all(save, "Width")
check("Apply to all sizes: no Width override left", not vm.overridden_in(form, save, "Width"),
      vm.overridden_in(form, save, "Width"))

# precedence: a Language being edited refuses This size only; a Blend record switches it off
form.props["Language"] = "Arabic (ar)"
vp.set_mode("all")
check("This size only refused while a Language is edited", vp.set_mode("this") is False and not vp.this_size)
form.props["Language"] = "(Default)"
check("allowed again with (Default)", vp.set_mode("this") and vp.this_size)
from radide.features.states import BlendPreview  # noqa: E402
bp = BlendPreview.of(view)
bp.recording, bp.state = True, "Base"
vp._check_record()
check("a Blend record switches This size only off", not vp.this_size and vp.active)
bp.recording, bp.state = False, ""

# ---------------------------------------------------------------- All sizes while Phone is shown
bar.btn_all.click()
pump(0.2)
lst = form.find("lstItems")
left_before = lst.props["Left"]
shown_before = view.design_props(lst)["Left"]
props_panel._set("Text", "")
doc.select(lst)
pump(0.2)
view.doc.set_geometry(lst, shown_before + 8, view.design_props(lst)["Top"], view.design_props(lst)["Width"],
                      view.design_props(lst)["Height"])
pump(0.2)
check("All sizes + preview: geometry edit moves the base by the same distance",
      lst.props["Left"] == left_before + 8, (left_before, lst.props["Left"]))
title = form.find("lblTitle")
props_panel_owner = doc.select(title)
pump(0.2)
props_panel._set("FontSize", 16)
pump(0.2)
check("All sizes: non-overridden property changes the base", title.props["FontSize"] == 16)

# ---------------------------------------------------------------- back to the base design
bar.combo.setCurrentIndex(0)
bar.combo.activated.emit(0)
pump(0.3)
check("Base design: preview off, model values shown", not vp.active and view.design_props(lst) is lst.props
      and view.form_props()["Width"] == 760)
doc.select(form.find("txtSearch"))
pump(0.2)
r = row_of("Left")
check("Properties: hollow diamond = changed on other sizes", r is not None and r.text().startswith("◇"),
      r.text() if r else None)

# ---------------------------------------------------------------- Add Size... / Edit Sizes...
def accept_add():
    dlg = getattr(view, "_variant_dialog", None)
    if dlg is None or not dlg.isVisible():
        QTimer.singleShot(50, accept_add)
        return
    pick = dlg._parts["pick"]
    for i in range(pick.count()):
        if pick.itemData(i) == ["landscape"]:
            pick.setCurrentIndex(i)
    dlg.accept()


QTimer.singleShot(50, accept_add)
made = fv.add_size_dialog(view)
pump(0.3)
check("Add Size: Landscape added, selected and edited alone",
      made is not None and vm.size(form, made["id"]) is not None and vp.vid == made["id"] and vp.this_size,
      made)
check("combo lists the new size", bar.combo.findData(made["id"]) >= 0)


def accept_edit():
    dlg = getattr(view, "_variant_dialog", None)
    if dlg is None or not dlg.isVisible() or "grid" not in dlg._parts:
        QTimer.singleShot(50, accept_edit)
        return
    grid = dlg._parts["grid"]
    grid.selectRow(grid.rowCount() - 1)
    dlg._parts["remove"]()
    grid.item(0, 0).setText("Small phone")
    dlg.accept()


QTimer.singleShot(50, accept_edit)
fv.edit_sizes_dialog(view)
pump(0.3)
check("Edit Sizes: last size removed, back to the base", vm.size(form, made["id"]) is None and not vp.active)
check("Edit Sizes: Phone renamed", vm.label(form, "phone") == "Small phone", vm.label(form, "phone"))
doc.undo()
pump(0.3)
check("Edit Sizes is one undo step", vm.size(form, made["id"]) is not None and vm.label(form, "phone") == "Phone")

# ---------------------------------------------------------------- Sizes gallery + side by side
panel = w.sizes_panel
w.dock_sizes.show()
w.dock_sizes.raise_()
panel.bind(view)
panel.render()
pump(0.3)
n = len(vm.sizes(form)) + 1
check("Sizes gallery: one thumbnail per size + base", panel.list.count() == n, panel.list.count())
item = next(panel.list.item(i) for i in range(panel.list.count())
            if panel.list.item(i).data(Qt.ItemDataRole.UserRole) == "tablet")
panel._clicked(item)
pump(0.3)
check("clicking a thumbnail shows that size", vp.vid == "tablet" and view.form_props()["Width"] == 800)
icon = panel.list.item(0).icon().pixmap(panel.thumb_size())
check("thumbnails are real pictures", not icon.isNull() and icon.width() > 50)
bar.btn_side.click()
pump(0.4)
check("Side-by-side: Sizes window floats with large thumbnails",
      panel.side_by_side and w.dock_sizes.isFloating() and panel.list.iconSize().width() >= 300)
shot(w.dock_sizes, "variants_side_by_side")
bar.btn_side.click()
pump(0.3)
check("Side-by-side off docks it again", not panel.side_by_side and not w.dock_sizes.isFloating())

# ---------------------------------------------------------------- designer right-click menu
m = QMenu()
w._designer_menu("Form1", m, form.find("btnSave"))
labels = [a.text() for a in m.actions()]
check("designer menu: Layout Size submenu + Hide on this size",
      "Layout Size" in labels and "Hide on this size" in labels, labels)

# ---------------------------------------------------------------- save: generated code has the variants
vp.set_size(None)
w.save_all()
pump(1.0)
code = (d / "Form1_designer.py").read_text(encoding="utf-8")
check("saved designer code contains the variants runtime", "_RadVariants(" in code and "'tablet'" in code)
data = json.loads((d / "Form1.form").read_text(encoding="utf-8"))
check("saved .form keeps sizes and per-control overrides",
      len(data["variants"]["sizes"]) >= 3 and any(c.get("variants") for c in data["controls"]))
compile(code, "Form1_designer.py", "exec")
check("generated designer compiles", True)

# ---------------------------------------------------------------- Arabic
cat = json.loads((Path(ROOT) / "radide/i18n/ar.json").read_text(encoding="utf-8"))["strings"]
keys = ["Edit:", "All sizes", "This size only", "Sizes", "Add Size...", "Edit Sizes...", "Apply to all sizes",
        "Reset to base", "Copy to", "Hide on this size", "Show on this size", "Overridden on this size",
        "Overridden on other sizes", "Side-by-side", "Base design", "Layout Size", "Size:"]
missing = [k for k in keys if not cat.get(k)]
check("Arabic strings for the sizes UI", not missing, missing)

finish(w)
