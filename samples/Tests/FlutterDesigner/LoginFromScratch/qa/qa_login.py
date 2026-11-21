"""QA of the advanced Flutter designer through the real IDE.

New Project > Flutter App (visual designer) -> add a blank screen -> build a login screen from scratch with the
palette (double-click) and the Properties inspector editors -> live canvas screenshot -> real mouse click selects
-> save -> flutter analyze -> run the generated app (flutter run -d web-server, the IDE's Exact preview) and grab
it -> import a hand-written Dart screen, edit it visually, regenerate, user code preserved -> templates gallery ->
old absolute-form Flutter flow.  Usage: python qa_login.py [--real]
"""
import json, os, sys, time, shutil, subprocess
ROOT = r"D:\Projects\1AOrganized\PythonProjects\SYSTEMs\PythonIDE"
sys.path.insert(0, ROOT)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
REAL = "--real" in sys.argv
os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
if not REAL:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_QPA_FONTDIR"] = "C:/Windows/Fonts"
__import__("PyQt6.QtWebEngineWidgets")
from pathlib import Path
from PyQt6.QtCore import QCoreApplication, QSettings, Qt, QTimer, QPoint
from PyQt6.QtWidgets import QApplication, QTreeWidgetItemIterator
from PyQt6.QtTest import QTest
QCoreApplication.setOrganizationName("RADIDE-TEST"); QCoreApplication.setApplicationName("RADIDE-TEST")
app = QApplication(sys.argv[:1])
QSettings().clear()
from radide.app import MainWindow
from radide.dialogs import NewProjectDialog
from radide.features.solution_ui import create_project_from_dialog
from radide.flutterdesign import model as M
from radide.flutterdesign.designer import FlutterDesigner

results = []
def check(name, ok, detail=""):
    results.append((name, bool(ok), str(detail)[:400]))
    print(("PASS " if ok else "FAIL ") + name, ("" if ok else str(detail)[:400]), flush=True)
def pump(sec=0.3):
    t = time.time() + sec
    while time.time() < t:
        app.processEvents(); time.sleep(0.01)
def wait(cond, sec):
    t = time.time() + sec
    while time.time() < t:
        if cond(): return True
        pump(0.2)
    return cond()
def close_boxes():
    m = QApplication.activeModalWidget()
    if m is not None:
        print("closing modal:", m.windowTitle(), flush=True); m.close()
killer = QTimer(); killer.timeout.connect(close_boxes); killer.start(700)
def flutter():
    return r"C:\flutter\bin\flutter.bat"
def done():
    json.dump(results, open(os.path.join(OUT, "results%s.json" % ("_real" if REAL else "")), "w"), indent=1)
    print(sum(r[1] for r in results), "/", len(results), "passed", flush=True)

TMP = Path(HERE) / "work"
if TMP.exists():
    shutil.rmtree(TMP, ignore_errors=True)
TMP.mkdir()
win = MainWindow(); win.resize(1700, 1050); win.show(); pump(1)

# ------------------------------------------------------------------------- 1. new project
dlg = NewProjectDialog(win)
itr = QTreeWidgetItemIterator(dlg.langs)
it = None
while itr.value():
    if itr.value().data(0, Qt.ItemDataRole.UserRole) == "flutter": it = itr.value()
    itr += 1
dlg.langs.setCurrentItem(it); pump(0.2)
for i in range(dlg.templates.count()):
    if dlg.templates.item(i).data(Qt.ItemDataRole.UserRole) == "flutter_designer":
        dlg.templates.setCurrentRow(i)
check("New Project > Flutter App (visual designer) exists",
      dlg.templates.currentItem() is not None and dlg.templates.currentItem().data(Qt.ItemDataRole.UserRole) == "flutter_designer")
dlg.location.setText(str(TMP)); dlg.name.setText("QaLogin")
prj = create_project_from_dialog(win, dlg); pump(2)
folder = Path(prj.folder)
check("project created", (folder / "pubspec.yaml").exists(), folder)
mgr = win.flutter_designer

# assets: my own lamps (Pillow) through the asset manager API
subprocess.run([sys.executable, os.path.join(HERE, "make_art.py"), str(TMP)], check=True)
from radide.flutterdesign import assets as A
a1 = A.import_asset(folder, TMP / "lamp_long.png"); a2 = A.import_asset(folder, TMP / "lamp_short.png")
check("assets imported + registered", "assets/images/" in (folder / "pubspec.yaml").read_text(encoding="utf-8"),
      (a1.rel, a2.rel))

# ------------------------------------------------------------------------- 2. blank screen
d = mgr.create_screen(folder, "blank_noappbar", "SignIn", "/signin"); pump(0.5)
check("Add New Screen (blank, no app bar) opens the designer", isinstance(d, FlutterDesigner), type(d))
win.tabs.setCurrentWidget(d); pump(0.3)
live_ok = False
if d.live is not None:
    live_ok = wait(lambda: d.live_ready, 180)
check("live Flutter canvas ready", live_ok, d.lbl_status.text())

pal = d.palette.tree
def pal_item(type_):
    itr = QTreeWidgetItemIterator(pal)
    while itr.value():
        p = itr.value().data(0, Qt.ItemDataRole.UserRole)
        if isinstance(p, dict) and p.get("type") == type_ and not p.get("node"):
            return itr.value()
        itr += 1
    raise KeyError(type_)
def add(type_, parent):
    """Select the parent in the Widget Tree, double-click the palette item."""
    d.tree.setCurrentItem(d.tree.items[parent]); pump(0.05)
    assert d.selected == parent, (d.selected, parent)
    before = set(n["id"] for n, *_ in d.screen.walk())
    pal.itemDoubleClicked.emit(pal_item(type_), 0); pump(0.05)
    new = [n["id"] for n, *_ in d.screen.walk() if n["id"] not in before]
    assert new, f"palette insert of {type_} into {parent} did nothing: {d.lbl_status.text()}"
    nid = d.selected
    node = d.screen.find(nid)
    assert node["type"] == type_, (node, type_)
    return nid
def prop(nid, key, value):
    """Inspector editor commit (the same path a user edit takes)."""
    if d.selected != nid:
        d.tree.setCurrentItem(d.tree.items[nid]); pump(0.05)
    row = d.inspector.rows[key]
    if value is not None and type(row.ed).__name__ == "StringEd":
        row.ed.edit.setText(value); row.ed.edit.editingFinished.emit()
    else:
        row.ed.commit(value)
    pump(0.02)
    got = (d.screen.find(nid).get("props") or {}).get(key)
    assert got == value or (isinstance(value, dict) and got), (nid, key, value, got)
def anim(nid, type_, delay, dur=600):
    if d.selected != nid:
        d.tree.setCurrentItem(d.tree.items[nid]); pump(0.05)
    t = d.inspector.anim_eds["type"]
    i = t.findData(type_); t.setCurrentIndex(i); t.activated.emit(i)
    d.inspector.anim_eds["delayMs"].commit(delay)
    d.inspector.anim_eds["durationMs"].commit(dur)
    a = d.screen.find(nid).get("anim")
    assert a and a["type"] == type_ and a["delayMs"] == delay, a
def name(nid, n):
    if d.selected != nid:
        d.tree.setCurrentItem(d.tree.items[nid]); pump(0.05)
    d.inspector.name_edit.setText(n); d.inspector.name_edit.editingFinished.emit()

ids = {}
build_err = None
try:
    root = d.screen.tree["id"]
    body = d.screen.tree["slots"]["body"]["id"]
    d.tree.setCurrentItem(d.tree.items[body]); d.delete_selected(); pump(0.1)
    prop(root, "backgroundColor", "#FFFFFFFF")
    scv = add("SingleChildScrollView", root)
    col = add("Column", scv)
    prop(col, "crossAxisAlignment", "CrossAxisAlignment.stretch")
    # header: gradient + rounded bottom + Stack with lamps and title
    hdr = add("Container", col); ids["header"] = hdr
    prop(hdr, "width", None)
    prop(hdr, "height", 400)
    prop(hdr, "decoration", {"gradient": {"type": "linear", "begin": "Alignment.topCenter", "end": "Alignment.bottomCenter",
                                          "colors": ["#FF6A5AE0", "#FF8F94FB"]},
                             "borderRadius": {"bl": 48, "br": 48}})
    stk = add("Stack", hdr)
    for key, (left, w, h, rel, dl) in {"lamp1": (30, 80, 200, a1.rel, 200), "lamp2": (140, 80, 150, a2.rel, 400)}.items():
        pos = add("Positioned", stk)
        prop(pos, "left", left); prop(pos, "top", 0); prop(pos, "width", w); prop(pos, "height", h)
        img = add("Image", pos); ids[key] = img
        d.set_ctor(img, "asset"); pump(0.05)     # inspector constructor combo
        prop(img, "src", rel)
        prop(img, "fit", "BoxFit.contain")
        anim(pos, "fadeInDown", dl, 800)
    clock = add("Positioned", stk)
    prop(clock, "right", 40); prop(clock, "top", 40); prop(clock, "left", None)
    ic = add("Icon", clock); ids["clock"] = ic
    prop(ic, "icon", "Icons.access_time_filled"); prop(ic, "size", 64); prop(ic, "color", "#E6FFFFFF")
    anim(clock, "fadeIn", 600, 800)
    tpos = add("Positioned", stk)
    prop(tpos, "left", 0); prop(tpos, "right", 0); prop(tpos, "bottom", 70); prop(tpos, "top", None)
    title = add("Text", tpos); ids["title"] = title
    prop(title, "data", "Login")
    prop(title, "textAlign", "TextAlign.center")
    prop(title, "style", {"color": "#FFFFFFFF", "fontSize": 40, "fontWeight": "FontWeight.bold"})
    anim(tpos, "fadeInUp", 800, 800)
    # form area
    pad = add("Padding", col)
    prop(pad, "padding", {"all": 30})
    fcol = add("Column", pad)
    prop(fcol, "crossAxisAlignment", "CrossAxisAlignment.stretch")
    card = add("Container", fcol); ids["card"] = card
    prop(card, "width", None); prop(card, "height", None)
    prop(card, "padding", {"all": 5})
    prop(card, "decoration", {"color": "#FFFFFFFF", "borderRadius": 12,
                              "boxShadow": [{"color": "#338F94FB", "blur": 20, "offset": [0, 10]}]})
    anim(card, "fadeInUp", 1000, 700)
    ccol = add("Column", card)
    e_box = add("Container", ccol)
    prop(e_box, "width", None); prop(e_box, "height", None)
    prop(e_box, "padding", {"all": 8})
    prop(e_box, "decoration", {"border": {"bottom": {"color": "#FFEEEEEE", "width": 1}}})
    email = add("TextField", e_box); ids["email"] = email
    name(email, "txtEmail")
    prop(email, "decoration", {"hintText": "Email or phone number", "prefixIcon": "Icons.email_outlined",
                               "border": "none", "hintStyle": {"color": "#FF9E9E9E"}})
    prop(email, "keyboardType", "TextInputType.emailAddress")
    p_box = add("Container", ccol)
    prop(p_box, "width", None); prop(p_box, "height", None)
    prop(p_box, "padding", {"all": 8})
    prop(p_box, "decoration", None)          # the palette Container comes with a light box
    pwd = add("TextField", p_box); ids["password"] = pwd
    name(pwd, "txtPassword")
    prop(pwd, "obscureText", True)
    prop(pwd, "decoration", {"hintText": "Password", "prefixIcon": "Icons.lock_outline",
                             "suffixIcon": "Icons.visibility_off_outlined", "border": "none",
                             "hintStyle": {"color": "#FF9E9E9E"}})
    sp = add("SizedBox", fcol); prop(sp, "height", 30); prop(sp, "width", None)
    ink = add("InkWell", fcol); ids["button"] = ink
    name(ink, "btnLogin")
    prop(ink, "borderRadius", 12)
    d.inspector.events["onTap"].setText("onLogin"); d.inspector.events["onTap"].editingFinished.emit()
    bbox = add("Container", ink)
    prop(bbox, "width", None); prop(bbox, "height", 52)
    prop(bbox, "alignment", "Alignment.center")
    prop(bbox, "decoration", {"gradient": {"type": "linear", "begin": "Alignment.centerLeft", "end": "Alignment.centerRight",
                                           "colors": ["#FF6A5AE0", "#FF8F94FB"]}, "borderRadius": 12})
    btxt = add("Text", bbox); ids["button_text"] = btxt
    prop(btxt, "data", "Login")
    prop(btxt, "style", {"color": "#FFFFFFFF", "fontSize": 18, "fontWeight": "FontWeight.bold"})
    anim(ink, "fadeInUp", 1200, 700)
    sp2 = add("SizedBox", fcol); prop(sp2, "height", 16); prop(sp2, "width", None)
    fb = add("TextButton", fcol); ids["forgot"] = fb
    ftxt = d.screen.find(fb)["slots"]["child"]["id"]
    prop(ftxt, "data", "Forgot Password?")
    prop(ftxt, "style", {"color": "#FF6A5AE0", "fontWeight": "FontWeight.w600"})
    d.tree.setCurrentItem(d.tree.items[fb]); pump(0.05)
    d.inspector.events["onPressed"].setText("onForgot"); d.inspector.events["onPressed"].editingFinished.emit()
    anim(fb, "fadeIn", 1400, 700)
except Exception as e:  # noqa: BLE001
    import traceback; traceback.print_exc()
    build_err = repr(e)
check("login screen built with palette + inspector", build_err is None, build_err)
issues = d.screen.validate()
check("model validates (no errors)", not [i for i in issues if getattr(i, "level", "") == "error"], issues[:5])
check("undo stack recorded the build", d.undo_stack.count() > 60, d.undo_stack.count())
anims = [n for n, *_ in d.screen.walk() if n.get("anim")]
check("staggered animations (7, distinct delays)", len(anims) == 7 and len({a["anim"]["delayMs"] for a in anims}) == 7,
      [(a["id"], a["anim"]) for a in anims])

# ------------------------------------------------------------------------- 3. live canvas
if live_ok:
    wait(lambda: all(i in d.live.rects for i in ids.values()), 20)
    missing = [k for k, i in ids.items() if i not in d.live.rects]
    check("live canvas reports bounds of all key widgets", not missing, missing)
    d.play_animations(); pump(3.5)
    d.tree.setCurrentItem(d.tree.items[root]); pump(0.8)
    d.live_box.grab().save(os.path.join(OUT, "canvas_live.png"))
    d.grab().save(os.path.join(OUT, "designer_full.png"))
    win.grab().save(os.path.join(OUT, "ide_window.png"))
    # header proportions: the header top 400dp and the card below it
    r_h, r_c, r_e = d.live.rects.get(ids["header"]), d.live.rects.get(ids["card"]), d.live.rects.get(ids["email"])
    check("canvas layout: card below header, email inside card",
          r_h and r_c and r_e and r_c.top() > r_h.bottom() and r_c.contains(r_e.center()), (r_h, r_c, r_e))
    # real mouse clicks on the web view -> selection
    target = d.live.view.focusProxy() or d.live.view
    for key in ("email", "title", "button_text", "lamp1"):
        r = d.live.rects[ids[key]]
        pt = target.mapFrom(d.live.view, r.center().toPoint()) if target is not d.live.view else r.center().toPoint()
        d.tree.setCurrentItem(d.tree.items[root]); pump(0.3)
        QTest.mouseClick(target, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pt)
        ok = wait(lambda: d.selected != root, 3)
        sel = d.selected
        # a click may land on an inner widget of the same node (Text inside a TextButton) - accept descendants/self
        chain = []
        cur = sel
        while cur:
            chain.append(cur); p, _w = d.screen.parent_of(cur); cur = p["id"] if p else None
        check(f"real click on canvas selects {key}", ok and (ids[key] == sel or ids[key] in chain[:2]),
              (sel, d.screen.find(sel).get("type") if sel else None, ids[key]))
    d.tree.setCurrentItem(d.tree.items[ids["email"]]); pump(0.6)
    d.live_box.grab().save(os.path.join(OUT, "canvas_selected_email.png"))
    # edit -> rendered
    got = []
    d.live.rendered.connect(lambda s, ms: got.append(ms))
    prop(ids["title"], "data", "Welcome")
    wait(lambda: bool(got), 10)
    check("inspector edit re-renders the live canvas", bool(got), got)
    d.undo(); pump(0.5)
    check("undo restores title", d.screen.find(ids["title"])["props"]["data"] == "Login")
    issues_live = d.live.issues
    check("live preview reports no runtime issues", not issues_live, issues_live[:5])

# ------------------------------------------------------------------------- 4. save + generated dart
win.save_all(); pump(1)
dart = folder / "lib/screens/sign_in.dart"
ev = folder / "lib/screens/sign_in_events.dart"
code = dart.read_text(encoding="utf-8") if dart.exists() else ""
check("Save All generates sign_in.dart + events file", dart.exists() and ev.exists())
for frag in ("LinearGradient", "BoxShadow", "BorderRadius.only", "Image.asset('assets/images/lamp_long.png'",
             "hintText: 'Email or phone number'", "Icons.email_outlined", "obscureText: true", "RadFx",
             "TextButton", "Forgot Password?", "Positioned", "onTap: onLogin"):
    check(f"generated contains {frag}", frag.replace(" ", "") in code.replace(" ", "").replace("\n", ""), "")
evt = ev.read_text(encoding="utf-8") if ev.exists() else ""
check("events file has onLogin/onForgot stubs", "void onLogin(" in evt and "void onForgot(" in evt, evt[:500])
main_dart = (folder / "lib/main.dart").read_text(encoding="utf-8")
check("main.dart includes designed routes", "designedRoutes" in main_dart)
# user code in the events file must survive regenerating
evt2 = evt.replace("void onLogin() {", "void onLogin() {\n    debugPrint('QA user code ${txtEmail.text}');", 1)
ev.write_text(evt2, encoding="utf-8")
prop(ids["forgot"] if False else ftxt, "data", "Forgot password?")
win.save_all(); pump(1)
evt3 = ev.read_text(encoding="utf-8")
check("user handler code preserved after regenerate", "QA user code ${txtEmail.text}" in evt3)
check("regenerated with the new text", "Forgot password?" in dart.read_text(encoding="utf-8"))

def run(cmd, cwd, timeout=900):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, encoding="utf-8",
                       errors="replace", shell=False)
    return p.returncode, p.stdout + p.stderr
rc, out = run([flutter(), "pub", "get", "--offline"], folder)
if rc != 0:
    rc, out = run([flutter(), "pub", "get"], folder)
check("flutter pub get", rc == 0, out[-800:])
rc, out = run([flutter(), "analyze", "--no-pub"], folder)
open(os.path.join(OUT, "analyze.txt"), "w", encoding="utf-8").write(out)
check("flutter analyze clean", rc == 0 and "No issues found" in out, out[-1500:])

# ------------------------------------------------------------------------- 5. run the generated app (web)
from radide.flutterdesign import live as LV
from PyQt6.QtWebEngineWidgets import QWebEngineView
appview = QWebEngineView(); appview.resize(393, 852)
appview.setWindowTitle("QA app"); appview.show()
runner = LV.LivePreview(view=appview)
statuses = []
runner.statusChanged.connect(lambda t: statuses.append(t))
buildlog = []
runner.buildOutput.connect(lambda t: buildlog.append(t))
runner.start_exact(folder, "/signin")
has_view = [False]
def probe():
    runner.page.runJavaScript("!!document.querySelector('flutter-view, flt-glass-pane')",
                              lambda v: has_view.__setitem__(0, bool(v)))
t0 = time.time()
while time.time() - t0 < 300 and not has_view[0]:
    probe(); pump(2)
check("generated app runs (flutter run -d web-server)", has_view[0], (statuses[-5:], "".join(buildlog)[-1500:]))
if has_view[0]:
    pump(6)    # animations finish + network/font settle
    appview.grab().save(os.path.join(OUT, "app_running.png"))
open(os.path.join(OUT, "run_log.txt"), "w", encoding="utf-8").write("".join(buildlog))
runner.shutdown(); pump(2)
appview.close()

# ------------------------------------------------------------------------- 6. import a hand-written Dart screen
hand = TMP / "hand_profile.dart"
hand.write_text(r'''import 'package:flutter/material.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});
  static const routeName = '/profile';

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  int _taps = 0;

  Widget _badge(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: Colors.amber, borderRadius: BorderRadius.circular(20)),
      child: Text(text),
    );
  }

  @override
  Widget build(BuildContext context) {
    final greeting = 'Hello #$_taps';
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const CircleAvatar(radius: 40, backgroundColor: Colors.indigo),
            const SizedBox(height: 16),
            Text(greeting, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            _badge('PRO'),
            ElevatedButton(
              onPressed: () => setState(() => _taps++),
              child: const Text('Tap me'),
            ),
          ],
        ),
      ),
    );
  }
}
''', encoding="utf-8")
di = mgr.create_screen(folder, "import", "Profile", "/profile", dart_file=str(hand)); pump(1)
check("import Dart screen opens in the designer", isinstance(di, FlutterDesigner), type(di))
if isinstance(di, FlutterDesigner):
    types = [n["type"] for n, *_ in di.screen.walk()]
    check("imported tree has real widgets", all(t in types for t in ("Scaffold", "AppBar", "Padding", "Column",
                                                                       "CircleAvatar", "ElevatedButton")), types)
    codes = [n for n, *_ in di.screen.walk() if n["type"] == "Code"]
    check("unknown helper call kept as Code node", any("_badge" in (n.get("props") or {}).get("code", "") for n in codes),
          codes)
    check("prelude + members preserved", "greeting" in (di.screen.data.get("code") or {}).get("prelude", "")
          and "_badge" in (di.screen.data.get("code") or {}).get("members", ""), di.screen.data.get("code"))
    # visual edits
    av = next(n["id"] for n, *_ in di.screen.walk() if n["type"] == "CircleAvatar")
    di.tree.setCurrentItem(di.tree.items[av]); pump(0.1)
    di.inspector.rows["backgroundColor"].ed.commit("#FFE91E63")
    di.inspector.rows["radius"].ed.commit(56)
    colid = next(n["id"] for n, *_ in di.screen.walk() if n["type"] == "Column")
    di.tree.setCurrentItem(di.tree.items[colid]); pump(0.1)
    di.palette.tree.itemDoubleClicked.emit(
        next(i for i in [di.palette.tree.findItems("Divider", Qt.MatchFlag.MatchRecursive)[0]]), 0)
    pump(0.2)
    check("visual edit inserted Divider", any(n["type"] == "Divider" for n, *_ in di.screen.walk()))
    di.save(); pump(1)
    pdart = folder / "lib/screens/profile.dart"
    ptxt = pdart.read_text(encoding="utf-8") if pdart.exists() else ""
    check("regenerated profile.dart keeps hand code (prelude, _badge, setState)",
          "final greeting = 'Hello #$_taps';" in ptxt and "Widget _badge(String text)" in ptxt and "_badge('PRO')" in ptxt
          and "_taps++" in ptxt, ptxt[:1500])
    check("regenerated profile.dart has the visual edits", "Color(0xFFE91E63)" in ptxt and "radius: 56" in ptxt
          and "Divider(" in ptxt, "")
    rc, out = run([flutter(), "analyze", "--no-pub"], folder)
    open(os.path.join(OUT, "analyze2.txt"), "w", encoding="utf-8").write(out)
    check("flutter analyze clean after import + edit", rc == 0 and "No issues found" in out, out[-1500:])
    if di.live is not None and wait(lambda: di.live_ready, 60):
        pump(2); di.live_box.grab().save(os.path.join(OUT, "imported_profile_canvas.png"))

# ------------------------------------------------------------------------- 7. templates gallery
from radide.features.flutter_designer import NewScreenDialog
nd = NewScreenDialog(win, folder)
tpls = [nd.list.item(i).data(Qt.ItemDataRole.UserRole + 0) for i in range(nd.list.count())]
from radide.features import flutter_designer as FD
keys = [nd.list.item(i).data(FD.ROLE) for i in range(nd.list.count())]
icons = sum(1 for i in range(nd.list.count()) if not nd.list.item(i).icon().isNull())
check("templates gallery lists the templates with thumbnails", sum(k.startswith("tpl:") for k in keys) >= 9 and icons >= 12,
      (keys, icons))
nd.show(); pump(0.5); nd.grab().save(os.path.join(OUT, "templates_gallery.png")); nd.close()
dt = mgr.create_screen(folder, "tpl:dashboard" if "tpl:dashboard" in keys else keys[-1], "Dash"); pump(0.5)
check("template instantiated + opens", isinstance(dt, FlutterDesigner) and (folder / "screens/Dash.fscreen.json").exists())

# ------------------------------------------------------------------------- 8. Arabic UI strings
ar = json.load(open(os.path.join(ROOT, "radide/i18n/ar.json"), encoding="utf-8"))
strs = ar.get("strings", ar)
probe_strings = ["Palette", "Widget Tree", "Properties", "Flutter App (visual designer)", "Add New Screen",
                 "Blank screen", "Import from Dart...", "Start from", "Animation type", "Delay (ms)",
                 "Select a widget", "Search widgets", "Snippets", "Rotate", "Dark", "Frame", "Play", "Interact",
                 "Dart code", "Save", "Flutter (live)", "Qt preview (fast)", "Events", "Screen name", "Route",
                 "Theme seed colour", "Flutter Assets...", "Flutter App Theme..."]
from radide import i18n as I18N
I18N.load("ar")
missing_ar = [s for s in probe_strings if I18N.tr(s) == s]     # tr() handles "..." / ":" suffixes
I18N.load("en")
check("Arabic strings exist for designer UI", not missing_ar, missing_ar)

# ------------------------------------------------------------------------- 9. old absolute-form Flutter flow
from radide.languages import get_plugin
fp = get_plugin("flutter")
old = fp.create_new_project(TMP / "OldForms", "OldForms", "flutter_app")
fp.write_project_files(old)
om = (TMP / "OldForms/lib/main.dart")
check("old absolute-position Flutter project still generates", om.exists() and bool(old.forms), old.forms)
rc, out = run([flutter(), "pub", "get", "--offline"], TMP / "OldForms")
rc, out = run([flutter(), "analyze", "--no-pub"], TMP / "OldForms")
open(os.path.join(OUT, "analyze_old.txt"), "w", encoding="utf-8").write(out)
check("old form project analyzes (no errors)", " error " not in out and "error -" not in out, out[-1200:])

done()
for v in list(mgr.editors.values()):
    try: v.shutdown()
    except Exception: pass
QSettings().clear()
win.close(); pump(0.5)
print("project", folder, flush=True)
os._exit(0)
