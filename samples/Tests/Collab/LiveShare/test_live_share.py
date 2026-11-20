"""Live Share end-to-end test: two RAD IDE main windows (host + guest) in one process, real WebSocket on
localhost, real Monaco editors.

Checks: wrong password refused, join, file tree, open shared file, randomised *concurrent* Monaco edits on both
sides (inserts / deletes, Arabic and emoji) converge in both CRDTs, both Monaco models and both Python mirrors,
remote cursor decorations, follow mode, chat, shared terminal, read-only enforced by the host, leave / end.
Screenshots (widget.grab() of the two IDE windows) go to argv[1] (default: a temp folder).

    .venv\\Scripts\\python.exe samples\\Tests\\Collab\\LiveShare\\test_live_share.py [out_dir] [--onscreen]

--onscreen uses the normal Windows platform (the offscreen platform has no fonts and paints web views blank),
use it for meaningful screenshots; the windows are closed at the end.
"""
import os
import random
import shutil
import sys
import tempfile
import time

ONSCREEN = "--onscreen" in sys.argv
if ONSCREEN:
    sys.argv.remove("--onscreen")
else:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
os.environ["RADIDE_COLLAB_QUIET"] = "1"            # no message boxes for refused joins
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
OUT = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="radide_liveshare_out_")
os.makedirs(OUT, exist_ok=True)
WORK = tempfile.mkdtemp(prefix="radide_liveshare_")
PROJ = os.path.join(WORK, "project")
shutil.copytree(os.path.join(HERE, "project"), PROJ)          # never edit the sample itself

__import__("PyQt6.QtWebEngineWidgets")                         # before QApplication
from pathlib import Path  # noqa: E402
from PyQt6.QtCore import QCoreApplication, QSettings, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402
QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
app = QApplication(sys.argv[:1])
QSettings().clear()
from radide.app import MainWindow  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)


def pump(sec=0.05):
    end = time.time() + sec
    while time.time() < end:
        app.processEvents()
        time.sleep(0.003)


def wait(cond, timeout=15.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.005)
    return bool(cond())


def js(editor, code, timeout=5.0):
    box = []
    editor.page().runJavaScript(code, lambda v: box.append(v))
    wait(lambda: box, timeout)
    return box[0] if box else None


def close_boxes():
    m = QApplication.activeModalWidget()
    if m is not None:
        m.close()


killer = QTimer()
killer.timeout.connect(close_boxes)
killer.start(300)

host_win, guest_win = MainWindow(), MainWindow()
for w, x in ((host_win, 0), (guest_win, 1420)):
    w.resize(1400, 860)
    w.move(x, 0)
    w.show()
pump(0.5)
H, G = host_win.live_share, guest_win.live_share
check("Share menu installed", any(a.text().replace("&", "") == "Share" for a in host_win.menuBar().actions()))

# ---------------------------------------------------------------- host starts, guest joins
host_ed = host_win.open_any_file(Path(PROJ) / "main.py")
check("host editor is Monaco", type(host_ed).__name__ == "MonacoEditor", type(host_ed).__name__)
wait(lambda: host_ed._ready, 30)
link = H.start_host(PROJ, password="pa55", readonly=False, name="Huda (host)", port=0)
check("session started with invite link", link.startswith("radide-collab://") and H.session.active, link)
check("host editor bound", "main.py" in H.bindings)
local_link = link.split("//", 1)[0] + "//127.0.0.1:" + link.rsplit(":", 1)[1]

G.join(local_link, password="nope", name="Omar")
check("wrong password refused", wait(lambda: G.last_error == "bad-password") and G.session is None, G.last_error)
check("host still alone", len(H.session.participants) == 1)

G.join(local_link, password="pa55", name="Omar")
check("guest joined", wait(lambda: G.session is not None and G.session.active and len(H.session.participants) == 2))
check("guest sees shared tree", wait(lambda: G.panel.files.topLevelItemCount() >= 3),
      ", ".join(G.session.tree))
G.open_shared("main.py")
check("guest [Live] tab opened", wait(lambda: "main.py" in G.views))
guest_ed = G.views["main.py"].editor
wait(lambda: guest_ed._ready, 30)
pump(0.5)
check("guest editor has host text", wait(lambda: js(guest_ed, "radEditor.getValue()") == host_ed.text()))

# ---------------------------------------------------------------- concurrent random edits in both Monacos
EDIT_JS = r"""
(function (seed, n, alpha) {
  let s = seed; function rnd() { s = (s * 1103515245 + 12345) % 2147483648; return s / 2147483648; }
  const m = radEditor.getModel();
  for (let i = 0; i < n; i++) {
    const len = m.getValueLength();
    let start = Math.floor(rnd() * (len + 1)), end = start, text = '';
    if (len > 0 && rnd() < 0.4) end = Math.min(len, start + 1 + Math.floor(rnd() * 5));
    else { const k = 1 + Math.floor(rnd() * 5); for (let j = 0; j < k; j++) text += alpha[Math.floor(rnd() * alpha.length)]; }
    const v = m.getValue();     // never split a surrogate pair
    if (start > 0 && start < len && v.charCodeAt(start) >= 0xDC00 && v.charCodeAt(start) <= 0xDFFF) start--;
    if (end > 0 && end < len && v.charCodeAt(end) >= 0xDC00 && v.charCodeAt(end) <= 0xDFFF) end++;
    if (end < start) end = start;
    const p1 = m.getPositionAt(start), p2 = m.getPositionAt(end);
    radEditor.executeEdits('test', [{ range: new monaco.Range(p1.lineNumber, p1.column, p2.lineNumber, p2.column), text: text }]);
  }
  return m.getValueLength();
})(SEED, COUNT, ALPHA)
"""
alpha = ["a", "b", "z", " ", "\n", "م", "ر", "ح", "ب", "ا", "سلام", "é", "😀", "x=1"]
import json  # noqa: E402
rng = random.Random(2026)


def edit_js(seed, count):
    return EDIT_JS.replace("SEED", str(seed)).replace("COUNT", str(count)).replace("ALPHA", json.dumps(alpha))

total = 0
for rnd in range(25):
    n1, n2 = rng.randint(1, 6), rng.randint(1, 6)
    # both scripts are queued before either IDE processes the other's messages -> truly concurrent edits
    host_ed.page().runJavaScript(edit_js(rng.randrange(1, 10**9), n1))
    guest_ed.page().runJavaScript(edit_js(rng.randrange(1, 10**9), n2))
    total += n1 + n2
    if rnd % 4 == 0:
        pump(0.02)


def converged():
    hv, gv = js(host_ed, "radEditor.getValue()"), js(guest_ed, "radEditor.getValue()")
    hd, gd = H.session.docs["main.py"].value(), G.session.docs["main.py"].value()
    return hv is not None and hv == gv == hd == gd == host_ed.text() == guest_ed.text()


ok = wait(converged, 30)
final = H.session.docs["main.py"].value()
check("concurrent Monaco edits converge (CRDTs, Monaco models, Python mirrors)", ok,
      f"{total} edits, {len(final)} chars, arabic={sum(0x600 <= ord(c) <= 0x6ff for c in final)}, "
      f"emoji={final.count(chr(0x1F600))}")
if not ok:
    print("host doc :", repr(H.session.docs["main.py"].value())[:300])
    print("guest doc:", repr(G.session.docs["main.py"].value())[:300])
    print("host ed  :", repr(js(host_ed, "radEditor.getValue()"))[:300])
    print("guest ed :", repr(js(guest_ed, "radEditor.getValue()"))[:300])

# make the screenshot readable: put the original text back (as an edit of the host - it propagates)
orig = (Path(PROJ) / "main.py").read_text(encoding="utf-8")
host_ed.page().runJavaScript("radEditor.executeEdits('t', [{range: radEditor.getModel().getFullModelRange(), "
                             f"text: {json.dumps(orig)}}}]);")
check("whole-text replace propagates", wait(lambda: js(guest_ed, "radEditor.getValue()") == orig))

# ---------------------------------------------------------------- cursors
guest_ed.page().runJavaScript("radEditor.focus(); radSetSelection(6, 4, 6, 25);")
gid = G.session.me
check("guest cursor reaches host", wait(lambda: H.session.participant(gid).sel != (0, 0)),
      str(H.session.participant(gid).sel))
check("host shows remote cursor decoration",
      wait(lambda: js(host_ed, f"document.querySelectorAll('.rc-c-{gid}').length") > 0
           and js(host_ed, f"document.querySelectorAll('.rc-s-{gid}').length") > 0))
host_ed.page().runJavaScript("radEditor.focus(); radSetCursor(1, 10);")
check("guest shows host cursor decoration", wait(lambda: js(guest_ed, "document.querySelectorAll('.rc-c-0').length") > 0))

# ---------------------------------------------------------------- chat + shared terminal
G.session.send_chat("أهلاً، سأعدل الدالة main")
H.session.send_chat("Sure - I'm on greet.py")
check("chat both ways", wait(lambda: "سأعدل" in H.panel.chat.toPlainText() and "greet.py" in G.panel.chat.toPlainText()))
host_win.log("$ python main.py\nHello, World!")
check("host Output shared read-only with guest",
      wait(lambda: "Hello, World!" in G.panel.term.toPlainText()) and G.panel.term.isReadOnly())

# ---------------------------------------------------------------- follow mode
G.follow(0)
host_win.open_any_file(Path(PROJ) / "notes.txt")
pump(0.3)
H._scan_tabs()
check("follow: guest opens the file the host switched to", wait(lambda: "notes.txt" in G.views))
check("follow: it is the guest's current tab",
      wait(lambda: guest_win.tabs.currentWidget() is G.views.get("notes.txt")))
G.follow(None)
guest_win.tabs.setCurrentWidget(G.views["main.py"])
host_win.open_any_file(Path(PROJ) / "main.py")
pump(0.3)

# ---------------------------------------------------------------- read-only enforced by the host
H.session.set_readonly(gid, True)
check("guest editor becomes read-only", wait(lambda: guest_ed.isReadOnly() and G.session.readonly))
before = H.session.docs["main.py"].value()
G.session.local_edit("main.py", [("i", 0, "# sneaky\n")])          # bypass the read-only editor
check("host refuses the read-only guest's edit",
      wait(lambda: H.session.stats["rejected_updates"] >= 1) and H.session.docs["main.py"].value() == before)
check("guest reverted to the host text", wait(lambda: js(guest_ed, "radEditor.getValue()") == before
                                              and G.session.docs["main.py"].value() == before))
H.session.set_readonly(gid, False)
check("guest can edit again", wait(lambda: not guest_ed.isReadOnly()))
guest_ed.page().runJavaScript("radEditor.executeEdits('t', [{range: new monaco.Range(1,1,1,1), text: '# edited by Omar\\n'}]);")
check("guest edit reaches host editor", wait(lambda: host_ed.text().startswith("# edited by Omar\n")))
guest_ed.page().runJavaScript("radEditor.focus(); radSetSelection(7, 10, 7, 30);")
host_ed.page().runJavaScript("radEditor.focus(); radSetSelection(3, 0, 3, 12);")
pump(0.8)

# ---------------------------------------------------------------- screenshots (IDE windows only)
from PyQt6.QtCore import Qt  # noqa: E402
for w, ctl in ((host_win, H), (guest_win, G)):
    ctl.show()
    ctl.panel.tabs.setCurrentIndex(0)
    w.resizeDocks([ctl.dock], [430], Qt.Orientation.Horizontal)
pump(1.5)
host_win.grab().save(os.path.join(OUT, "liveshare_host.png"))
guest_win.grab().save(os.path.join(OUT, "liveshare_guest.png"))
G.panel.tabs.setCurrentIndex(1)
pump(0.3)
G.dock.grab().save(os.path.join(OUT, "liveshare_guest_terminal.png"))
check("screenshots saved", os.path.getsize(os.path.join(OUT, "liveshare_host.png")) > 10000, OUT)

# ---------------------------------------------------------------- Arabic UI
from radide import i18n  # noqa: E402
i18n.set_language(app, "ar")
pump(0.8)
share = next(a for a in guest_win.menuBar().actions() if a.text().replace("&", "") == "Share")
check("Arabic: Share menu and Live Share panel translated",
      "مشاركة" in i18n.shown(share) and "انضممت" in i18n.shown(G.panel.status),
      f"{i18n.shown(share)} | {i18n.shown(G.panel.status)}")
G.panel.tabs.setCurrentIndex(0)
pump(0.5)
guest_win.grab().save(os.path.join(OUT, "liveshare_guest_ar.png"))
i18n.set_language(app, "en")
pump(0.5)

# ---------------------------------------------------------------- leave / rejoin / end
G.end()
check("guest leaves", wait(lambda: len(H.session.participants) == 1) and G.session is None)
G.join(local_link, password="pa55", name="Omar")
check("guest rejoins", wait(lambda: G.session is not None and G.session.active and len(H.session.participants) == 2))
H.end()
check("host ends session, guest notified", wait(lambda: G.session is None) and H.session is None)
check("Share actions reset", H.a_start.isEnabled() and not H.a_end.isEnabled())

# ---------------------------------------------------------------- cleanup
killer.stop()
for w in (host_win, guest_win):
    for ed in w.findChildren(type(host_ed)):
        ed.setModified(False)
    for i in range(w.tabs.count()):
        e = getattr(w.tabs.widget(i), "editor", None)
        if e is not None:
            e.setModified(False)
    w.close()
pump(0.5)
QSettings().clear()
shutil.rmtree(WORK, ignore_errors=True)
passed = sum(r[1] for r in results)
print(f"\n{passed}/{len(results)} passed; screenshots in {OUT}")
sys.exit(0 if passed == len(results) else 1)
