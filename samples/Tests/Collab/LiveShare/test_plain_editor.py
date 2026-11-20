"""PlainBinding (built-in QPlainTextEdit editor) over a real session: random edits on both sides converge."""
import os
import random
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..")))
from PyQt6.QtGui import QTextCursor  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv[:1])
from radide.collab import binding as B  # noqa: E402
from radide.collab.session import CollabGuest, CollabHost  # noqa: E402
from radide.editor import CodeEditor  # noqa: E402
from radide.languages import get_plugin  # noqa: E402


def wait(c, t=8):
    e = time.time() + t
    while time.time() < e:
        app.processEvents()
        if c():
            return True
        time.sleep(0.005)
    return c()


root = Path(tempfile.mkdtemp())
(root / "a.py").write_text("x = 1\n# مرحبا\n", encoding="utf-8")
h = CollabHost("H")
h.start(root, port=0)
g = CollabGuest("G")
g.join("127.0.0.1", h.port, h.code)
assert wait(lambda: g.active)
h.ensure_doc("a.py")
g.open("a.py")
assert wait(lambda: "a.py" in g.docs)
plug = get_plugin("python-tk")
eh, eg = CodeEditor(plug, root / "a.py"), CodeEditor(plug, root / "a.py")
eh.setPlainText(h.docs["a.py"].value())
eg.setPlainText("stale")
bh, bg = B.bind(h, "a.py", eh), B.bind(g, "a.py", eg)
h.docRemote.connect(lambda p, ops: bh.remote(ops))
g.docRemote.connect(lambda p, ops: bg.remote(ops))
print(type(bh).__name__, repr(eg.toPlainText()))
rng = random.Random(3)
for _ in range(80):
    for ed in (eh, eg):
        c = ed.textCursor()
        t = ed.toPlainText()
        u16 = [0]
        for ch in t:                      # cursor positions between whole characters (UTF-16 units)
            u16.append(u16[-1] + (2 if ord(ch) > 0xFFFF else 1))
        n = len(t)
        i = rng.randint(0, n)
        c.setPosition(u16[i])
        if n and rng.random() < 0.4:
            c.setPosition(u16[min(n, i + rng.randint(1, 3))], QTextCursor.MoveMode.KeepAnchor)
            c.removeSelectedText()
        else:
            c.insertText(rng.choice(["a", "ب", "😀", "\n", "سلام "]))
    if rng.random() < 0.3:
        app.processEvents()
ok = wait(lambda: eh.toPlainText() == eg.toPlainText() == h.docs["a.py"].value() == g.docs["a.py"].value())
print("PlainBinding converge:", ok, len(eh.toPlainText()))
g.stop()
h.stop()
sys.exit(0 if ok else 1)
