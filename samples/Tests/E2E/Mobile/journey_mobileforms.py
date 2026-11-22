# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Mobile journey - "Mobile" forms: a phone-frame form designed in the classic (VB-style) designer, layout sizes
(variants) for phone / tablet / foldable, device previews, and the code the IDE generates for Flutter, React
Native and Kivy from the same form.

    .venv\\Scripts\\python samples\\Tests\\E2E\\Mobile\\journey_mobileforms.py

Steps:
  new project    File > New Project > Mobile > Flutter App (phone-frame form designer)
  design         Toolbox: Label, text field, button, list on the phone form; Properties edits; Click handler
                 (double-click the button -> code editor) that adds the text to the list
  sizes          Sizes bar: Add Size Phone + Tablet + Half-open (foldable); This size only on Tablet: the list
                 moves right of the input (two columns), the label text changes; base untouched
  devices        Device property: Pixel, Galaxy Tab, Galaxy Z Fold6 (Flat / HalfOpened / Folded postures) - the
                 form follows the device's safe area; screenshots of each
  generate dart  Save All: lib/*_designer.dart uses RadVariant / rv.pick; flutter analyze clean
  generate rn    the same form through the React Native generator: placeV / useSizes, node --check-able JSX
                 shape (balanced tags), handler wiring
  generate kivy  the same form through the Kivy generator: root.radsizes, KV parses with kivy's Builder
  flutter test   a widget test written in the editor: phone size shows one column, tablet two, tap adds
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import e2e_lib as E  # noqa: E402

j = E.Journey("Mobile", "mobileforms", "Mobile forms (phone frame) + sizes + 3 code generators")
win = j.window(1600, 1000)
folder: Path | None = None
ST: dict = {}


def flutter() -> str:
    try:
        from radide.languages.flutter import flutter_exe
        return flutter_exe() or shutil.which("flutter") or ""
    except Exception:  # noqa: BLE001
        return shutil.which("flutter") or ""


FL = flutter()


def need():
    if folder is None or "view" not in ST:
        raise E.Skip("no designed form")


# ============================================================================ 1. new project
with j.step("new project"):
    shutil.rmtree(j.work / "PhoneForms", ignore_errors=True)
    j.new_project("flutter", "flutter_app", "PhoneForms")
    folder = Path(win.project.folder)
    form = win.project.startup or win.project.forms[0]
    win.open_designer(form)
    E.pump(0.6)
    v = win._current_designer()
    j.check(v is not None, "form designer did not open")
    ST["view"], ST["form"] = v, form
    j.check(getattr(v, "phone", None) is not None and getattr(v.phone, "active", True), "no phone frame")
    j.shot(v, "designer_phone_frame")
    j.note(f"form {form}, device {v.doc.form.props.get('Device')}, {[c.name for c in v.doc.form.controls]}")

# ============================================================================ 2. design
HANDLER_BODY = {
    "flutter": "    final t = txtItem.text.trim();\n    if (t.isEmpty) return;\n    lstItems.addItem(t);\n"
               "    lblCount.text = 'Items: ${lstItems.count}';\n    txtItem.text = '';\n",
}

with j.step("design"):
    if "view" not in ST:
        raise E.Skip("no designer")
    v = ST["view"]
    doc = v.doc
    from PyQt6.QtCore import QPoint
    # start from an empty form (the template's sample controls are deleted like a user would)
    for c in list(doc.form.controls):
        if c.type not in ("AppBar",):
            doc.select(c)
            doc.delete_selected() if hasattr(doc, "delete_selected") else doc.remove_control(c)
    E.pump(0.2)
    made = {}
    for typ, name, x, y, w, h, text in (("Label", "lblCount", 16, 72, 320, 32, "Items: 0"),
                                        ("MTextField", "txtItem", 16, 112, 240, 56, ""),
                                        ("Button", "btnAdd", 264, 116, 120, 48, "Add"),
                                        ("MListView", "lstItems", 16, 180, 368, 420, None)):
        v.create_control(typ, QPoint(x, y))
        E.pump(0.05)
        c = doc.selected
        j.check(c is not None and c.type == typ, f"Toolbox {typ}: {c}")
        doc.set_prop(c, "Name", name)
        doc.set_geometry(c, x, y, w, h) if hasattr(doc, "set_geometry") else None
        if text is not None and "Text" in c.props:
            doc.set_prop(c, "Text", text)
        made[name] = c
    if "Hint" in made["txtItem"].props:
        doc.set_prop(made["txtItem"], "Hint", "New item")
    ab = next((c for c in doc.form.controls if c.type == "AppBar"), None)
    if ab is not None:
        doc.set_prop(ab, "Title", "Shopping list")
    E.pump(0.3)
    j.shot(v, "designer_form_designed")
    # double-click the button: the Click handler in the code editor
    win.save_all()
    code_before = (folder / f"lib/{re.sub(r'(?<!^)(?=[A-Z])', '_', ST['form']).lower()}.dart")
    if hasattr(v, "controlDoubleClicked"):
        v.controlDoubleClicked.emit(made["btnAdd"])
    elif hasattr(win, "_on_control_dclick"):
        win._on_control_dclick(made["btnAdd"])
    else:
        doc.select(made["btnAdd"])
        win.view_code()
    E.pump(0.8)
    ed = win._editor_for_file(Path(win.plugin.code_file(ST["form"])).name) if hasattr(win, "_editor_for_file") else None
    text = ed.text() if ed is not None else ""
    if "btnAdd_Click" not in text and ed is not None:
        code, line = win.plugin.add_handler(text, "btnAdd_Click", doc.form)
        ed.setText(code)
        text = code
    j.check("btnAdd_Click" in text, f"no btnAdd_Click handler in the code editor: {text[:400]}")
    lines = text.split("\n")
    k = next(i for i, ln in enumerate(lines) if "btnAdd_Click" in ln)
    while k < len(lines) and "{" not in lines[k]:
        k += 1
    lines.insert(k + 1, HANDLER_BODY["flutter"])
    ed.setText("\n".join(lines))
    win.save_all()
    E.pump(0.5)
    j.shot(win, "ide_click_handler")
    j.note(f"controls {[c.name for c in doc.form.controls]}")

# ============================================================================ 3. sizes (variants)
with j.step("sizes"):
    need()
    from radide.variants import model as vm
    v = ST["view"]
    doc = v.doc
    vp = getattr(v, "_variant_preview", None)
    bar = getattr(v, "_variant_bar", None)
    j.check(vp is not None and bar is not None, "no sizes bar on the mobile form designer")
    for key in ("phone", "tablet", "halfopen"):
        vp.add_size(vm.preset(key), select=False)
    E.pump(0.2)
    j.check([s["id"] for s in vm.sizes(doc.form)] == ["phone", "tablet", "halfopen"], vm.sizes(doc.form))
    vp.set_size("tablet")
    j.check(vp.set_mode("this"), "This size only refused")
    E.pump(0.3)
    lst, txt, btn, lbl = (doc.form.find(n) for n in ("lstItems", "txtItem", "btnAdd", "lblCount"))
    base_left = lst.props["Left"]
    doc.set_prop(lst, "Left", 420)
    doc.set_prop(lst, "Top", 112)
    doc.set_prop(lbl, "Text", "Items (tablet): 0")
    E.pump(0.3)
    ov = vm.overrides(doc.form, lst, "tablet")
    j.check(ov.get("Left") == 420 and lst.props["Left"] == base_left, f"override {ov}, base {lst.props['Left']}")
    j.check(vm.overrides(doc.form, lbl, "tablet").get("Text") == "Items (tablet): 0", "label text override")
    j.shot(v, "designer_tablet_this_size")
    vp.set_mode("all")
    vp.set_size("halfopen")
    E.pump(0.4)
    j.shot(v, "designer_halfopen_size")
    vp.set_size(None)
    E.pump(0.3)
    j.note(f"sizes {[s['id'] for s in vm.sizes(doc.form)]}; tablet override {ov}")

# ============================================================================ 4. devices
with j.step("devices"):
    need()
    v = ST["view"]
    doc = v.doc
    sizes = {}
    for dev, posture in (("pixel", None), ("galaxy_tab_s9", None), ("galaxy_z_fold6", "Flat"),
                         ("galaxy_z_fold6", "HalfOpened"), ("galaxy_z_fold6", "Folded")):
        from radide import devices as DV
        if dev not in DV.DEVICES:
            continue
        doc.set_prop(None, "Device", dev)
        if posture:
            doc.set_prop(None, "Posture", posture)
        E.pump(0.4)
        key = dev + (f"/{posture}" if posture else "")
        sizes[key] = (doc.form.props["Width"], doc.form.props["Height"])
        j.shot(v, "device_" + key.replace("/", "_"))
    doc.set_prop(None, "Posture", "Flat")
    doc.set_prop(None, "Device", "pixel")
    E.pump(0.3)
    j.check(len(sizes) >= 4, f"devices tried: {sizes}")
    if "galaxy_z_fold6/Folded" in sizes and "galaxy_z_fold6/Flat" in sizes:
        j.check(sizes["galaxy_z_fold6/Folded"][0] < sizes["galaxy_z_fold6/Flat"][0],
                f"folded cover screen should be narrower: {sizes}")
    j.note(str(sizes))

# ============================================================================ 5. generated Flutter code
with j.step("generate dart"):
    need()
    win.save_all()
    E.pump(0.8)
    from radide.languages import get_plugin
    get_plugin("flutter").write_project_files(win.project)
    des = next((p for p in (folder / "lib").glob("*_designer.dart")), None)
    j.check(des is not None, "no *_designer.dart")
    dart = des.read_text(encoding="utf-8")
    for frag in ("RadVariant.of(context", "rv.pick", "lstItems", "btnAdd_Click", "Items (tablet): 0"):
        j.check(frag in dart, f"{des.name} lacks {frag}")
    if not FL:
        raise E.Skip("generated code checked; flutter analyze skipped: Flutter SDK not found")
    code, out = E.run([FL, "pub", "get"], cwd=folder, timeout=600)
    code, out = E.run([FL, "analyze", "--no-pub"], cwd=folder, timeout=600)
    (j.out / "analyze.txt").write_text(out, encoding="utf-8")
    errs = [ln for ln in out.splitlines() if " error " in ln]
    j.check(not errs, f"analyze errors: {errs[:6]}")
    j.note(f"{des.name} {len(dart)} chars; analyze: {'No issues found' if 'No issues' in out else 'infos/warnings only'}")

# ============================================================================ 6. React Native generator
with j.step("generate rn"):
    need()
    from radide.mobile import codegen_rn as RN
    form = ST["view"].doc.form
    jsx = RN.generate_designer(form, f"{form.props['Name']}.jsx")
    (j.work / "rn_designer.jsx").write_text(jsx, encoding="utf-8")
    for frag in ("lstItems", "btnAdd", "Items (tablet): 0"):
        j.check(frag in jsx, f"RN code lacks {frag}")
    j.check(re.search(r"useSizes|placeV|radSizes|sizes", jsx), "RN code has no per-size placement")
    opens = len(re.findall(r"<R\.Screen\b", jsx))
    j.check(opens == 1 and "</R.Screen>" in jsx, "R.Screen not balanced")
    j.note(f"{len(jsx)} chars of JSX")

# ============================================================================ 7. Kivy generator
with j.step("generate kivy"):
    need()
    from radide.mobile import codegen_kivy as KV
    form = ST["view"].doc.form
    src = KV.generate_designer(form, f"{form.props['Name']}.py") if hasattr(KV, "generate_designer") else ""
    j.check(src and "lstItems" in src, "Kivy code not generated")
    (j.work / "kivy_designer.py").write_text(src, encoding="utf-8")
    j.check(re.search(r"radsizes|RadSize|sizes", src), "Kivy code has no per-size layout")
    kv = re.search(r'KV\s*=\s*(?:r)?"""(.*?)"""', src, re.S) or re.search(r"Builder\.load_string\((?:r)?'''(.*?)'''", src, re.S)
    if kv:
        chk = j.work / "kv_check.py"
        chk.write_text("import os,sys\nos.environ['KIVY_NO_ARGS']='1'\nos.environ['KIVY_NO_CONSOLELOG']='1'\n"
                       "from kivy.lang import Parser\nParser(content=open(sys.argv[1],encoding='utf-8').read())\n"
                       "print('KV OK')\n", encoding="utf-8")
        (j.work / "form.kv").write_text(kv.group(1), encoding="utf-8")
        code, out = E.run([sys.executable, str(chk), str(j.work / "form.kv")], timeout=120)
        if "No module named 'kivy'" in out:
            j.note("kivy not installed: KV parse skipped")
        else:
            j.check("KV OK" in out, f"KV does not parse: {out[-600:]}")
            j.note("KV parses")
    j.note(f"{len(src)} chars of Python/KV")

# ============================================================================ 8. flutter test
TEST = """import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:phone_forms/main.dart';

void main() {
  testWidgets('phone: add an item', (tester) async {
    await tester.binding.setSurfaceSize(const Size(412, 915));
    await tester.pumpWidget(const RadMobileApp());
    await tester.pumpAndSettle();
    expect(find.text('Items: 0'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'Milk');
    await tester.tap(find.text('Add'));
    await tester.pumpAndSettle();
    expect(find.text('Milk'), findsOneWidget);
    expect(find.text('Items: 1'), findsOneWidget);
  });

  testWidgets('tablet: the size override applies', (tester) async {
    await tester.binding.setSurfaceSize(const Size(800, 1000));
    await tester.pumpWidget(const RadMobileApp());
    await tester.pumpAndSettle();
    expect(find.text('Items (tablet): 0'), findsOneWidget);
  });
}
"""

with j.step("flutter test"):
    need()
    if not FL:
        raise E.Skip("Flutter SDK not found")
    main = (folder / "lib" / "main.dart").read_text(encoding="utf-8")
    m = re.search(r"class (\w+) extends StatelessWidget", main)
    test = TEST.replace("RadMobileApp", m.group(1) if m else "RadMobileApp")
    pkg = re.search(r"^name:\s*(\S+)", (folder / "pubspec.yaml").read_text(encoding="utf-8"), re.M).group(1)
    test = test.replace("package:phone_forms/", f"package:{pkg}/")
    j.edit(folder / "test" / "form_test.dart", test)
    for old in (folder / "test").glob("*.dart"):
        if old.name != "form_test.dart":
            old.unlink()
    code, out = E.run([FL, "test", "--no-pub", "test/form_test.dart"], cwd=folder, timeout=900)
    (j.out / "flutter_test.txt").write_text(out, encoding="utf-8")
    j.check(code == 0 and "All tests passed" in out, out[-1500:])
    j.note("2 widget tests passed (phone add, tablet override)")

j.finish()
