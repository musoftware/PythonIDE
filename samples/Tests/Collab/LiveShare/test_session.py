"""Network-level test (no editors): host + 2 guests over real WebSockets on localhost.
join / wrong password / wrong code / random concurrent edits converge / cursors / chat / read-only enforced /
terminal / leave / end."""
import os
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_FORCE_STDERR_LOGGING", "1")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..")))
from PyQt6.QtCore import QCoreApplication  # noqa: E402

from radide.collab.session import CollabGuest, CollabHost  # noqa: E402

app = QCoreApplication(sys.argv[:1])
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)


def wait(cond, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.005)
    return cond()


def pump(sec):
    end = time.time() + sec
    while time.time() < end:
        app.processEvents()
        time.sleep(0.003)


root = Path(tempfile.mkdtemp(prefix="collab-test-"))
(root / "main.py").write_text("print('hello')\n# مرحبا بالعالم\n", encoding="utf-8")
(root / "sub").mkdir()
(root / "sub" / "util.txt").write_text("util\n", encoding="utf-8")

host = CollabHost("Host")
assert host.start(root, port=0, password="s3cret")
port, code = host.port, host.code
check("host listening", port > 0, f"port {port} code {code}")

# wrong password
bad = CollabGuest("Mallory")
rej = []
bad.rejected.connect(rej.append)
bad.join("127.0.0.1", port, code, "wrong")
check("wrong password rejected", wait(lambda: rej) and rej[0] == "bad-password", str(rej))
check("rejected guest not a participant", len(host.participants) == 1)
bad.stop()
# wrong code
bad2 = CollabGuest("Eve")
rej2 = []
bad2.rejected.connect(rej2.append)
bad2.join("127.0.0.1", port, "ZZZZZZ", "s3cret")
check("wrong code rejected", wait(lambda: rej2) and rej2[0] == "bad-code", str(rej2))
bad2.stop()

g1, g2 = CollabGuest("Ali"), CollabGuest("Sara")
g1.join_link(host.link("127.0.0.1"), "s3cret")
g2.join("127.0.0.1", port, code, "s3cret")
check("two guests joined", wait(lambda: g1.active and g2.active and len(host.participants) == 3))
check("guest sees file tree", "sub/util.txt" in g1.tree and "main.py" in g1.tree, str(g1.tree))
check("participants broadcast", wait(lambda: len(g1.participants) == 3 and len(g2.participants) == 3))

host.ensure_doc("main.py")
g1.open("main.py")
g2.open("main.py")
check("guests opened doc", wait(lambda: "main.py" in g1.docs and "main.py" in g2.docs))
base = host.docs["main.py"].value()
check("doc content", g1.docs["main.py"].value() == base == g2.docs["main.py"].value())

# randomised concurrent edits from three replicas, no event processing between local edits of a round
rng = random.Random(42)
ALPHA = "abc XYZ مرحبا سلام é😀\n"
reps = {"host": host, "g1": g1, "g2": g2}
n_ops = 0
for rnd in range(60):
    for name, s in reps.items():
        for _ in range(rng.randint(0, 3)):
            t = s.docs["main.py"].value()
            if t and rng.random() < 0.4:
                p = rng.randrange(len(t)); n = rng.randint(1, min(6, len(t) - p))
                ops = [("d", p, n)]
            else:
                p = rng.randint(0, len(t))
                ops = [("i", p, "".join(rng.choice(ALPHA) for _ in range(rng.randint(1, 5))))]
            s.local_edit("main.py", ops)
            n_ops += 1
    if rnd % 3 == 0:
        pump(0.01)
same = wait(lambda: host.docs["main.py"].value() == g1.docs["main.py"].value() == g2.docs["main.py"].value(), 10)
check("random concurrent edits converge (3 replicas)", same,
      f"{n_ops} ops, len {len(host.docs['main.py'].value())}, arabic chars={sum(0x600 <= ord(c) <= 0x6ff for c in host.docs["main.py"].value())}")

# cursors
seen = []
host.cursorChanged.connect(lambda pid, path, a, h: seen.append(("host", pid, path, a, h)))
g2.cursorChanged.connect(lambda pid, path, a, h: seen.append(("g2", pid, path, a, h)))
g1.send_cursor("main.py", 3, 7)
check("cursor broadcast to host and other guest",
      wait(lambda: ("host", g1.me, "main.py", 3, 7) in seen and ("g2", g1.me, "main.py", 3, 7) in seen), str(seen[-3:]))

# chat
chats = []
g2.chatReceived.connect(lambda m: chats.append(("g2", m["name"], m["text"])))
host.chatReceived.connect(lambda m: chats.append(("host", m["name"], m["text"])))
g1.send_chat("مرحبا يا فريق")
check("chat relayed", wait(lambda: ("g2", "Ali", "مرحبا يا فريق") in chats and ("host", "Ali", "مرحبا يا فريق") in chats))

# terminal
terms = []
g1.terminalText.connect(terms.append)
host.send_terminal("$ python main.py\nhello\n")
check("terminal output shared", wait(lambda: "".join(terms) == "$ python main.py\nhello\n"))

# read-only enforced by the host
host.set_readonly(g2.me, True)
check("guest notified read-only", wait(lambda: g2.readonly))
before = host.docs["main.py"].value()
g2.local_edit("main.py", [("i", 0, "HACK ")])       # bypass the UI: the host must refuse it
check("read-only edit rejected by host", wait(lambda: host.stats["rejected_updates"] >= 1)
      and not host.docs["main.py"].value().startswith("HACK"))
check("read-only guest reset to host text", wait(lambda: g2.docs["main.py"].value() == host.docs["main.py"].value()))
pump(0.3)
check("other guest unaffected", g1.docs["main.py"].value() == before == host.docs["main.py"].value())
host.set_readonly(g2.me, False)
check("guest writable again", wait(lambda: not g2.readonly))
g2.local_edit("main.py", [("i", 0, "# ok\n")])
check("edit after read-only lifted", wait(lambda: host.docs["main.py"].value().startswith("# ok\n")
                                         and g1.docs["main.py"].value().startswith("# ok\n")))

# path traversal refused
errs = []
g1.docError.connect(lambda p, t: errs.append(p))
g1.open("../outside.txt")
check("path outside shared folder refused", wait(lambda: errs == ["../outside.txt"]))

# leave + end
g1.stop()
check("guest leave removes participant", wait(lambda: len(host.participants) == 2 and len(g2.participants) == 2))
ended = []
g2.ended.connect(ended.append)
host.stop()
check("host end notifies guests", wait(lambda: ended and not g2.active), str(ended))
check("server closed", host.server is None)

shutil.rmtree(root, ignore_errors=True)
ok = all(r[1] for r in RESULTS)
print(f"\n{sum(r[1] for r in RESULTS)}/{len(RESULTS)} passed")
sys.exit(0 if ok else 1)
