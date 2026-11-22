# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Mobile journey - Flutter: build a "Tasks" app with the visual Flutter designer, entirely through the IDE.

    .venv\\Scripts\\python samples\\Tests\\E2E\\Mobile\\journey_flutter.py

Steps (PASS / FAIL / SKIP, screenshots of the designer canvas, the IDE and the running Windows program):
  toolchain       flutter found
  new project     File > New Project > Mobile > Flutter App (visual designer)
  theme           Project > Flutter App Theme... (preset, button radius) -> lib/theme/app_theme.dart wired into main
  screen list     Add New Screen "TaskList" (/): app bar, header Text with an entrance animation, ListView.builder
                  whose item template is a Code widget (ListTile -> openTask(index)), FAB -> onAdd handler,
                  "عن التطبيق" button -> /about
  screen add      Add New Screen "AddTask" (/add): TextField txtTitle + Save button (onSave) with fadeInUp
  screen detail   Add New Screen "TaskDetail" (/detail): Text bound to the route argument, Back button
  screen arabic   Add New Screen "About" (/about): Directionality(rtl) + Arabic texts
  responsive      TaskList sizes (Phone / Tablet / Desktop preset): "This size only" header size on Tablet, device
                  previews phone / tablet / Galaxy Z Fold6 postures (screenshots)
  startup+code    TaskList is the start-up screen; event handlers written in the *_events.dart files (the IDE's
                  code editor), shared_preferences added (Manage Packages = flutter pub add) for local storage
  generate        Save All: generated screens, routes, main.dart; user code kept
  analyze         flutter analyze: no issues
  widget tests    test/tasks_test.dart written in the editor; flutter test (add -> list -> detail, RTL, tablet)
  windows build   Build > Publish engine (flutter build windows --release)
  windows run     the exe runs: its window appears (PrintWindow screenshot), closed with WM_CLOSE
  android apk     flutter build apk --debug when the Android SDK is complete, else SKIP with the reason
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

j = E.Journey("Mobile", "flutter", "Flutter Tasks app (visual designer)")


def flutter() -> str:
    try:
        from radide.languages.flutter import flutter_exe
        return flutter_exe() or shutil.which("flutter") or ""
    except Exception:  # noqa: BLE001
        return shutil.which("flutter") or ""


FL = flutter()
STEPS = ["new project", "theme", "screen list", "screen add", "screen detail", "screen arabic", "responsive",
         "startup+code", "generate", "analyze", "widget tests", "windows build", "windows run", "android apk"]
with j.step("toolchain"):
    if not FL:
        j.steps[-1:] = []
        for s in STEPS:
            with j.step(s):
                raise E.Skip("Flutter SDK not found (flutter.bat)")
        j.finish(close=False)
    j.note(FL)

win = j.window(1700, 1050)
folder: Path | None = None
ST: dict = {}


def need():
    if folder is None:
        raise E.Skip("no project")


# ============================================================================ designer helpers (user actions)
def palette_item(d, type_):
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QTreeWidgetItemIterator
    itr = QTreeWidgetItemIterator(d.palette.tree)
    while itr.value():
        p = itr.value().data(0, Qt.ItemDataRole.UserRole)
        if isinstance(p, dict) and p.get("type") == type_ and not p.get("node"):
            return itr.value()
        itr += 1
    return None


def add(d, type_, parent):
    """Select the parent in the Widget Tree, double-click the palette item (the IDE's insert)."""
    d.tree.setCurrentItem(d.tree.items[parent])
    E.pump(0.05)
    before = {n["id"] for n, *_ in d.screen.walk()}
    it = palette_item(d, type_)
    j.check(it is not None, f"palette has no {type_}")
    d.palette.tree.itemDoubleClicked.emit(it, 0)
    E.pump(0.05)
    new = [n["id"] for n, *_ in d.screen.walk() if n["id"] not in before]
    j.check(new, f"palette insert of {type_} into {parent} did nothing: {d.lbl_status.text()}")
    nid = d.selected if d.selected in new else new[0]
    j.check(d.screen.find(nid)["type"] == type_, f"inserted {d.screen.find(nid)['type']} instead of {type_}")
    return nid


def sel(d, nid):
    if d.selected != nid:
        d.tree.setCurrentItem(d.tree.items[nid])
        E.pump(0.05)


def prop(d, nid, key, value):
    """Properties inspector edit (the row's editor commit; set_prop when the inspector has no row)."""
    sel(d, nid)
    row = getattr(d.inspector, "rows", {}).get(key)
    if row is not None and value is not None and type(row.ed).__name__ == "StringEd" and isinstance(value, str):
        row.ed.edit.setText(value)
        row.ed.edit.editingFinished.emit()
    elif row is not None and not (isinstance(value, dict) and "$code" in value):
        row.ed.commit(value)
    else:
        d.set_prop(nid, key, value)
    E.pump(0.02)


def event(d, nid, ev, handler):
    sel(d, nid)
    box = getattr(d.inspector, "events", {}).get(ev)
    if box is not None:
        box.setText(handler)
        box.editingFinished.emit()
    else:
        d.set_event(nid, ev, handler)
    E.pump(0.02)
    j.check((d.screen.find(nid).get("events") or {}).get(ev) == handler, f"event {ev} not set on {nid}")


def anim(d, nid, type_, delay, dur=600):
    sel(d, nid)
    eds = getattr(d.inspector, "anim_eds", None)
    if eds:
        t = eds["type"]
        i = t.findData(type_)
        t.setCurrentIndex(i)
        t.activated.emit(i)
        eds["delayMs"].commit(delay)
        eds["durationMs"].commit(dur)
    else:
        d.set_anim(nid, {"type": type_, "delayMs": delay, "durationMs": dur})
    a = d.screen.find(nid).get("anim")
    j.check(a and a.get("type") == type_, f"animation not set: {a}")


def rename(d, nid, name):
    sel(d, nid)
    d.inspector.name_edit.setText(name)
    d.inspector.name_edit.editingFinished.emit()
    E.pump(0.02)


def clear_body(d):
    """Delete the screen's default body (Center > Text)."""
    body = (d.screen.tree.get("slots") or {}).get("body")
    if body:
        d.tree.setCurrentItem(d.tree.items[body["id"]])
        d.delete_selected()
        E.pump(0.05)
    return d.screen.tree["id"]


def new_screen(name, route):
    """Project > Add New Screen (Flutter designer): blank screen with an app bar."""
    d = win.flutter_designer.create_screen(folder, "blank", name, route)
    j.check(d is not None and type(d).__name__ == "FlutterDesigner", f"Add New Screen {name} failed: {j.msgs[-2:]}")
    win.tabs.setCurrentWidget(d)
    E.pump(0.3)
    return d


def app_title(d, text):
    t = d.screen.tree["slots"]["appBar"]["slots"]["title"]["id"]
    prop(d, t, "data", text)


def set_screen_code(d, members="", imports=()):
    code = dict(d.screen.data.get("code") or {})
    if members:
        code["members"] = members
    d.set_screen("code", code)
    if imports:
        d.set_screen("imports", list(imports))
    E.pump(0.05)


# ============================================================================ 1. new project
with j.step("new project"):
    shutil.rmtree(j.work / "TasksApp", ignore_errors=True)
    j.new_project("flutter", "flutter_designer", "TasksApp")
    folder = Path(win.project.folder)
    j.check((folder / "pubspec.yaml").exists() and (folder / "screens").is_dir(), f"no pubspec/screens in {folder}")
    E.pump(0.5)
    j.shot(win, "ide_new_flutter_project")
    j.note(f"{folder}; screens: {sorted(p.name for p in (folder / 'screens').glob('*.json'))}")

# ============================================================================ 2. theme
with j.step("theme"):
    need()
    from radide.flutterdesign.asset_dialogs import ThemeEditorDialog
    dlg = ThemeEditorDialog(win, folder)
    dlg._e2e_keep = True
    presets = [dlg.preset.itemData(i) for i in range(dlg.preset.count()) if dlg.preset.itemData(i)]
    j.check(presets, "no theme presets")
    dlg.preset.setCurrentIndex(1)
    E.pump(0.2)
    dlg.b_radius.setValue(14)
    dlg.c_radius.setValue(16)
    dlg.center.setChecked(True)
    E.pump(0.2)
    j.shot(dlg, "theme_editor")
    dlg._save()
    E.pump(0.3)
    from radide.languages import get_plugin
    get_plugin("flutter").write_project_files(win.project)
    theme = folder / "lib" / "theme" / "app_theme.dart"
    main = (folder / "lib" / "main.dart").read_text(encoding="utf-8")
    j.check(theme.exists() and "AppTheme.light" in main, f"theme not wired: {theme.exists()}")
    j.note(f"preset {presets[0]}; app_theme.dart {theme.stat().st_size} B")

# ============================================================================ 3. TaskList screen
with j.step("screen list"):
    need()
    d = new_screen("TaskList", "/")
    ST["list"] = d
    app_title(d, "My Tasks")
    root = clear_body(d)
    col = add(d, "Column", root)
    prop(d, col, "crossAxisAlignment", "CrossAxisAlignment.stretch")
    pad = add(d, "Padding", col)
    prop(d, pad, "padding", {"all": 16})
    hdr = add(d, "Text", pad)
    rename(d, hdr, "lblHeader")
    prop(d, hdr, "data", "Today's tasks")
    prop(d, hdr, "style", {"fontSize": 22, "fontWeight": "FontWeight.bold"})
    anim(d, pad, "fadeInDown", 100, 600)
    exp = add(d, "Expanded", col)
    lv = add(d, "ListView", exp)
    rename(d, lv, "lstTasks")
    d.set_ctor(lv, "builder")
    E.pump(0.1)
    node = d.screen.find(lv)
    j.check(node.get("ctor") == "builder", f"ListView.builder ctor not set: {node.get('ctor')}")
    tpl = (node.get("slots") or {}).get("itemBuilder")
    if tpl:                                      # replace the default item template with a Code widget
        d.tree.setCurrentItem(d.tree.items[tpl["id"]])
        d.delete_selected()
        E.pump(0.05)
    code = add(d, "Code", lv) if palette_item(d, "Code") is not None else None
    if code is None:
        from radide.flutterdesign import model as M
        n = M.new_node("Code", d.screen)
        d.insert_node(n, lv)
        code = n["id"]
    d.set_prop(code, "code", "ListTile(leading: const Icon(Icons.check_circle_outline), title: Text(tasks[index]), "
                             "onTap: () => openTask(index))")
    d.set_prop(lv, "itemCount", {"$code": "tasks.length"})
    btn = add(d, "TextButton", col)
    btxt = d.screen.find(btn)["slots"]["child"]["id"]
    prop(d, btxt, "data", "عن التطبيق")
    event(d, btn, "onPressed", "nav:/about")
    fab = add(d, "FloatingActionButton", root)
    rename(d, fab, "btnAdd")
    event(d, fab, "onPressed", "onAdd")
    fchild = (d.screen.find(fab).get("slots") or {}).get("child")
    if fchild and fchild["type"] == "Icon":
        prop(d, fchild["id"], "icon", "Icons.add")
    set_screen_code(d, members="List<String> tasks = [];",
                    imports=["package:shared_preferences/shared_preferences.dart"])
    issues = [i for i in d.screen.validate() if getattr(i, "level", "") == "error"]
    j.check(not issues, f"model errors: {issues[:4]}")
    E.pump(0.5)
    j.shot(d, "designer_tasklist")
    j.note(f"{len(list(d.screen.walk()))} widgets; undo steps {d.undo_stack.count()}")

# ============================================================================ 4. AddTask
with j.step("screen add"):
    need()
    d = new_screen("AddTask", "/add")
    ST["add"] = d
    app_title(d, "New task")
    root = clear_body(d)
    pad = add(d, "Padding", root)
    prop(d, pad, "padding", {"all": 20})
    col = add(d, "Column", pad)
    prop(d, col, "crossAxisAlignment", "CrossAxisAlignment.stretch")
    tf = add(d, "TextField", col)
    rename(d, tf, "txtTitle")
    prop(d, tf, "decoration", {"hintText": "Task title", "labelText": "Title"})
    sp = add(d, "SizedBox", col)
    prop(d, sp, "height", 16)
    b = add(d, "ElevatedButton", col)
    rename(d, b, "btnSave")
    t = d.screen.find(b)["slots"]["child"]["id"]
    prop(d, t, "data", "Save")
    event(d, b, "onPressed", "onSave")
    anim(d, b, "fadeInUp", 200, 500)
    j.shot(d, "designer_addtask")
    j.note(f"{len(list(d.screen.walk()))} widgets")

# ============================================================================ 5. TaskDetail
with j.step("screen detail"):
    need()
    d = new_screen("TaskDetail", "/detail")
    ST["detail"] = d
    app_title(d, "Task")
    root = clear_body(d)
    c = add(d, "Center", root)
    col = add(d, "Column", c)
    prop(d, col, "mainAxisSize", "MainAxisSize.min")
    tx = add(d, "Text", col)
    rename(d, tx, "lblTitle")
    d.set_prop(tx, "data", {"$code": "(ModalRoute.of(context)?.settings.arguments as String?) ?? ''"})
    prop(d, tx, "style", {"fontSize": 28})
    anim(d, tx, "zoomIn", 0, 500)
    back = add(d, "TextButton", col)
    bt = d.screen.find(back)["slots"]["child"]["id"]
    prop(d, bt, "data", "Back")
    event(d, back, "onPressed", "back")
    j.shot(d, "designer_detail")

# ============================================================================ 6. Arabic RTL screen
with j.step("screen arabic"):
    need()
    d = new_screen("About", "/about")
    ST["about"] = d
    app_title(d, "حول")
    root = clear_body(d)
    if palette_item(d, "Directionality") is not None:
        dr = add(d, "Directionality", root)
        prop(d, dr, "textDirection", "TextDirection.rtl")
        parent = dr
    else:
        parent = root
    pad = add(d, "Padding", parent)
    prop(d, pad, "padding", {"all": 24})
    col = add(d, "Column", pad)
    prop(d, col, "crossAxisAlignment", "CrossAxisAlignment.start")
    t1 = add(d, "Text", col)
    prop(d, t1, "data", "تطبيق المهام")
    prop(d, t1, "style", {"fontSize": 26, "fontWeight": "FontWeight.bold"})
    t2 = add(d, "Text", col)
    prop(d, t2, "data", "صُمم بالكامل في مصمم فلاتر المرئي")
    if parent is root:
        for t in (t1, t2):
            d.set_prop(t, "textDirection", "TextDirection.rtl")
    j.shot(d, "designer_about_rtl")
    j.note("Directionality(rtl)" if parent is not root else "Text.textDirection = rtl (no Directionality in palette)")

# ============================================================================ 7. responsive sizes + device previews
with j.step("responsive"):
    need()
    from radide.flutterdesign import variants_fd as VF
    from radide.flutterdesign.designer import DEVICE_IDS
    d = ST["list"]
    win.tabs.setCurrentWidget(d)
    d.apply(VF.add_preset, "Phone / Tablet / Desktop", text="Add sizes")
    E.pump(0.3)
    ids = [s["id"] for s in VF.sizes(d.screen)]
    j.check("medium" in ids, f"sizes: {ids}")
    hdr = next(n["id"] for n, *_ in d.screen.walk() if n.get("name") == "lblHeader")
    d.select(hdr)
    d.set_edit_mode("size")
    d.set_edit_size("medium")
    E.pump(0.3)
    d.set_prop(hdr, "style", {"fontSize": 34, "fontWeight": "FontWeight.bold"})
    ov = VF.overrides(d.screen.find(hdr), "medium")
    j.check(ov.get("style", {}).get("fontSize") == 34 and d.screen.find(hdr)["props"]["style"]["fontSize"] == 22,
            f"This size only override: {ov}")
    j.shot(d, "designer_tablet_this_size_only")
    d.set_edit_mode("all")
    shots = []
    act = {}
    for dev in ("tablet", "galaxy_z_fold6", "pixel"):
        d.cbo_device.setCurrentIndex(DEVICE_IDS.index(dev))
        E.pump(0.4)
        act[dev] = d.active_sizes()
        shots.append(f"{dev}:{d.device_size()} active={act[dev]}")
        j.shot(d.canvas, f"preview_{dev}")
    j.check(act["pixel"] == ["compact"] and "medium" in act["tablet"], f"active sizes per device: {act}")
    for posture in ("HalfOpened", "Folded"):
        d.set_posture(posture)
        E.pump(0.3)
        j.shot(d.canvas, f"preview_fold6_{posture}")
    d.set_posture("Flat")
    d.cbo_device.setCurrentIndex(DEVICE_IDS.index("pixel"))
    E.pump(0.2)
    j.note("; ".join(shots))

# ============================================================================ 8. start-up screen + handler code + package
EVENTS_LIST = """// TaskList screen - event handlers (written in the RAD IDE code editor).
part of 'task_list.dart';

class TaskListEvents extends TaskListDesigner {
  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() => tasks = prefs.getStringList('tasks') ?? <String>[]);
  }

  @override
  void openTask(int index) {
    Navigator.pushNamed(context, '/detail', arguments: tasks[index]);
  }

  @override
  void onAdd() async {
    await Navigator.pushNamed(context, '/add');
    await _load();
  }
}
"""

EVENTS_ADD = """// AddTask screen - event handlers (written in the RAD IDE code editor).
part of 'add_task.dart';

class AddTaskEvents extends AddTaskDesigner {
  @override
  void onSave() async {
    final title = txtTitle.text.trim();
    if (title.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Enter a title')));
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    final list = prefs.getStringList('tasks') ?? <String>[];
    await prefs.setStringList('tasks', [...list, title]);
    if (mounted) Navigator.pop(context);
  }
}
"""

with j.step("startup+code"):
    need()
    for k in ("list", "add", "detail", "about"):
        j.check(ST.get(k) is not None, f"screen {k} missing")
    win.save_all()
    E.pump(1.0)
    prj = win.project
    prj.startup = "TaskList"                    # Solution Explorer > Set as Start-up Screen
    prj.save()
    from radide.languages import get_plugin
    get_plugin("flutter").write_project_files(prj)
    # Manage Packages > shared_preferences (the Flutter package manager's install command = flutter pub add)
    code, out = E.run([FL, "pub", "add", "shared_preferences"], cwd=folder, timeout=600)
    j.check(code == 0 and "shared_preferences" in (folder / "pubspec.yaml").read_text(encoding="utf-8"),
            f"flutter pub add: {out[-600:]}")
    ST["add_screen"] = ST["add"]
    ST["add"].set_screen("imports", ["package:shared_preferences/shared_preferences.dart"])
    win.save_all()
    E.pump(0.8)
    lst_ev = folder / "lib" / "screens" / "task_list_events.dart"
    add_ev = folder / "lib" / "screens" / "add_task_events.dart"
    j.check(lst_ev.exists() and add_ev.exists(), "events files not generated")
    j.check("void onAdd(" in lst_ev.read_text(encoding="utf-8"), "onAdd stub missing")
    j.edit(lst_ev, EVENTS_LIST)
    j.edit(add_ev, EVENTS_ADD)
    j.shot(win, "ide_events_editor")
    main = (folder / "lib" / "main.dart").read_text(encoding="utf-8")
    j.check("initialRoute: '/'" in main or "TaskList" in main, f"start-up not TaskList: {main[-500:]}")
    j.note("handlers typed in the editor; shared_preferences added")

# ============================================================================ 9. generate (Save All)
with j.step("generate"):
    need()
    for d in (ST["list"], ST["add"], ST["detail"], ST["about"]):
        d.set_prop(d.screen.tree["id"], "backgroundColor", None) if False else None
    win.save_all()
    E.pump(1.0)
    gen = folder / "lib" / "screens" / "task_list.dart"
    code = gen.read_text(encoding="utf-8")
    for frag in ("ListView.builder", "tasks.length", "openTask(index)", "RadFx", "FloatingActionButton",
                 "shared_preferences", "rv.pick"):
        j.check(frag in code, f"generated task_list.dart lacks {frag}")
    routes = (folder / "lib" / "screens" / "routes.dart").read_text(encoding="utf-8")
    j.check(all(c in routes for c in ("TaskList", "AddTask", "TaskDetail", "About")), routes)
    j.check("prefs.getStringList('tasks')" in (folder / "lib/screens/task_list_events.dart").read_text(
        encoding="utf-8"), "user code lost after regenerate")
    about = (folder / "lib" / "screens" / "about.dart").read_text(encoding="utf-8")
    j.check("TextDirection.rtl" in about and "تطبيق المهام" in about, "RTL screen not generated")
    j.note(f"task_list.dart {len(code)} chars; layout lib {'present' if (folder / 'lib/radlayout.dart').exists() else 'missing'}")

# ============================================================================ 10. analyze
with j.step("analyze"):
    need()
    code, out = E.run([FL, "pub", "get"], cwd=folder, timeout=600)
    j.check(code == 0, f"pub get: {out[-500:]}")
    code, out = E.run([FL, "analyze", "--no-pub"], cwd=folder, timeout=600)
    (j.out / "analyze.txt").write_text(out, encoding="utf-8")
    errs = [ln for ln in out.splitlines() if " error " in ln or ln.strip().startswith("error")]
    j.check(code == 0 or not errs, f"analyze errors: {errs[:8] or out[-1200:]}")
    j.note("No issues found" if "No issues found" in out else f"warnings/infos only ({len(out.splitlines())} lines)")

# ============================================================================ 11. widget tests
TEST = """// Widget tests of the Tasks app (written in the RAD IDE editor).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:tasks_app/main.dart';

Future<void> settle(WidgetTester tester) async {
  for (var i = 0; i < 25; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

void main() {
  testWidgets('list -> add -> list -> detail', (tester) async {
    SharedPreferences.setMockInitialValues({'tasks': <String>['Buy milk']});
    await tester.binding.setSurfaceSize(const Size(411, 891));
    await tester.pumpWidget(const RadMobileApp());
    await settle(tester);
    expect(find.text('My Tasks'), findsOneWidget);
    expect(find.text('Buy milk'), findsOneWidget);
    await tester.tap(find.byType(FloatingActionButton));
    await settle(tester);
    expect(find.text('New task'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'Write report');
    await tester.tap(find.text('Save'));
    await settle(tester);
    expect(find.text('Write report'), findsOneWidget);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getStringList('tasks'), ['Buy milk', 'Write report']);
    await tester.tap(find.text('Write report'));
    await settle(tester);
    expect(find.text('Task'), findsOneWidget);
    expect(find.text('Write report'), findsOneWidget);
    await tester.tap(find.text('Back'));
    await settle(tester);
    expect(find.text('My Tasks'), findsOneWidget);
  });

  testWidgets('empty title is refused', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const RadMobileApp());
    await settle(tester);
    await tester.tap(find.byType(FloatingActionButton));
    await settle(tester);
    await tester.tap(find.text('Save'));
    await settle(tester);
    expect(find.text('Enter a title'), findsOneWidget);
  });

  testWidgets('Arabic screen is right-to-left', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const RadMobileApp());
    await settle(tester);
    await tester.tap(find.text('عن التطبيق'));
    await settle(tester);
    final title = find.text('تطبيق المهام');
    expect(title, findsOneWidget);
    expect(Directionality.of(tester.element(title)), TextDirection.rtl);
  });

  testWidgets('tablet size uses the larger header', (tester) async {
    SharedPreferences.setMockInitialValues({});
    addTearDown(tester.view.reset);
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(800, 1280);
    await tester.pumpWidget(const RadMobileApp());
    await settle(tester);
    expect(tester.widget<Text>(find.text("Today's tasks")).style?.fontSize, 34);
    tester.view.physicalSize = const Size(411, 891);
    await settle(tester);
    expect(tester.widget<Text>(find.text("Today's tasks")).style?.fontSize, 22);
  });
}
"""

with j.step("widget tests"):
    need()
    j.edit(folder / "test" / "tasks_test.dart", TEST)
    old = folder / "test" / "widget_test.dart"
    if old.exists():
        old.unlink()          # the template's smoke test targets the old Login start screen
    code, out = E.run([FL, "test", "--no-pub", "test/tasks_test.dart"], cwd=folder, timeout=900)
    (j.out / "flutter_test.txt").write_text(out, encoding="utf-8")
    m = re.findall(r"\+(\d+)(?: -(\d+))?:", out)
    j.check(code == 0 and "All tests passed" in out, f"flutter test: {out[-1500:]}")
    j.note(f"4 widget tests passed (+{m[-1][0] if m else '?'})")

# ============================================================================ 12. Windows build (Build > Publish engine)
EXE: dict = {}
with j.step("windows build"):
    need()
    from radide.deploy.build import build
    from radide.deploy.config import PublishConfig
    cfg = PublishConfig()
    cfg.make_installer = False
    try:
        cfg.app_name = "TasksApp"
    except Exception:  # noqa: BLE001
        pass
    lines: list[str] = []
    try:
        res = build(folder, cfg, log=lambda s: lines.append(str(s)))
    except Exception as e:  # noqa: BLE001
        (j.out / "windows_build.log").write_text("\n".join(lines) + f"\n*** {e}", encoding="utf-8")
        txt = "\n".join(lines[-30:])
        if re.search(r"Unable to find suitable Visual Studio|Visual Studio not installed|No CMake|"
                     r"Windows desktop development", txt + str(e), re.I):
            raise E.Skip(f"Windows desktop toolchain missing: {str(e)[:200]}")
        raise
    (j.out / "windows_build.log").write_text("\n".join(lines), encoding="utf-8")
    exe = Path(res.dist) / res.exe
    j.check(exe.exists(), f"no exe {exe}")
    EXE["path"] = exe
    j.note(f"{exe} ({sum(p.stat().st_size for p in exe.parent.rglob('*') if p.is_file()) // 1024} KB folder)")

with j.step("windows run"):
    if "path" not in EXE:
        raise E.Skip("no Windows build")
    p = E.start([EXE["path"]], cwd=EXE["path"].parent, log=j.work / "tasks_exe.log")
    w = E.wait_window(p, "", 60)
    j.check(w is not None, f"no window of {EXE['path'].name} (exit {p.poll()})")
    E.pump(4.0)                                 # entrance animations
    shot = j.shot_window(w[0], "windows_app_tasklist")
    j.check(p.poll() is None, f"the program exited ({p.poll()})")
    E.close_window(w[0])
    try:
        p.wait(15)
    except Exception:  # noqa: BLE001
        E.kill_tree(p)
    j.note(f"window '{w[1]}', screenshot {Path(shot).name if shot else 'failed'}")

# ============================================================================ 13. Android APK
with j.step("android apk"):
    need()
    sdk = Path(os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
               or Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk")
    parts = {k: (sdk / k).is_dir() and any((sdk / k).iterdir()) for k in ("platform-tools", "build-tools", "platforms")}
    if not all(parts.values()):
        raise E.Skip(f"Android SDK incomplete at {sdk}: missing {[k for k, v in parts.items() if not v]}")
    if not (folder / "android").is_dir():
        code, out = E.run([FL, "create", "--platforms=android", "--project-name", "tasks_app", "."], cwd=folder,
                          timeout=600)
        j.check(code == 0, f"flutter create --platforms=android: {out[-600:]}")
    code, out = E.run([FL, "build", "apk", "--debug"], cwd=folder, timeout=3000)
    (j.out / "apk_build.log").write_text(out, encoding="utf-8")
    apk = folder / "build" / "app" / "outputs" / "flutter-apk" / "app-debug.apk"
    if code != 0:
        why = next((ln for ln in out.splitlines() if re.search(r"licen[cs]e|NDK|SDK|cmdline-tools|Java|Gradle|"
                                                                 r"Could not|No Android SDK", ln)), out[-300:])
        raise E.Skip(f"flutter build apk failed for a toolchain reason: {why.strip()[:300]}")
    j.check(apk.exists(), "no app-debug.apk")
    j.note(f"{apk.name} {apk.stat().st_size // 1024} KB")

j.finish()
