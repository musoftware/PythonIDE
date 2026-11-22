"""NETWORK TEST - popular real extensions from Open VSX in RAD IDE: install, activate, commands, UI, unsupported API.

    python samples/Tests/VSX/test_vsx_matrix.py <scratch folder> [ext.id ...]

Downloads each extension (and its dependencies) from open-vsx.org into a scratch RADIDE_VSX_ROOT, starts the IDE
with a small multi-language project and records per extension: installed (version), activation result,
contributed vs registered commands, a safe command run (one that only shows UI), theme / icon theme
registered, and every API / command the extension host reported as unsupported. Writes matrix.json + matrix.md
in the scratch folder. Skips (exit 0) when Open VSX is not reachable. Exit code = number of extensions that
failed to install or activate."""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SCRATCH = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEMP", ".")) / "vsx_matrix_test"
os.environ["RADIDE_VSX_ROOT"] = str(SCRATCH / "vsxroot")
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-gpu-compositing --disable-logging --log-level=3")
sys.path.insert(0, str(REPO))

# (id, kind, a command that only shows UI / reports state, or None)
MATRIX = [
    ("esbenp.prettier-vscode", "formatter", None),
    ("dbaeumer.vscode-eslint", "linter", "eslint.showOutputChannel"),
    ("usernamehw.errorlens", "ui", "errorLens.toggle"),
    ("Gruntfuggly.todo-tree", "view", "todo-tree.refresh"),
    ("christian-kohler.path-intellisense", "completion", None),
    ("streetsidesoftware.code-spell-checker", "linter", "cSpell.displayVersion"),
    ("ritwickdey.LiveServer", "server", None),
    ("PKief.material-icon-theme", "icon theme", None),
    ("zhuangtongfa.material-theme", "color theme", None),
    ("dracula-theme.theme-dracula", "color theme", None),
    ("yzhang.markdown-all-in-one", "markdown", None),
    ("redhat.vscode-yaml", "language server", None),
    ("redhat.vscode-xml", "language server", None),
    ("charliermarsh.ruff", "linter", "ruff.showLogs"),
    ("ms-pyright.pyright", "language server", None),
    ("ms-python.python", "language", None),
    ("eamodio.gitlens", "git", None),
    ("golang.Go", "language", None),
    ("rust-lang.rust-analyzer", "language server", None),
    ("llvm-vs-code-extensions.vscode-clangd", "language server", None),
    ("redhat.java", "language server", None),
]
if len(sys.argv) > 2:
    want = {a.lower() for a in sys.argv[2:]}
    MATRIX = [m for m in MATRIX if m[0].lower() in want]

from radide.vsx import manager, registry  # noqa: E402

try:
    registry.search("prettier", "", 0, 1, "relevance")
except Exception as e:  # noqa: BLE001
    print(f"SKIP: Open VSX not reachable ({e})")
    sys.exit(0)

if SCRATCH.exists():
    shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
ROWS: dict[str, dict] = {}
for eid, kind, _cmd in MATRIX:
    row = ROWS.setdefault(eid.lower(), {"id": eid, "kind": kind})
    t0 = time.time()
    try:
        got = manager.install(eid)
        main = next((x for x in got if x.id == eid.lower()), None)
        from radide.vsx import package as P
        inst = main or P.get_installed(eid.lower())
        row.update(installed=inst.version if inst else "?", deps=[x.id for x in got if x.id != eid.lower()],
                   has_code=bool(inst and inst.main), seconds=round(time.time() - t0, 1))
    except Exception as e:  # noqa: BLE001
        row.update(installed=None, error=str(e)[:300])
    print(eid, "->", row.get("installed") or row.get("error"), flush=True)

__import__("PyQt6.QtWebEngineWidgets")
from PyQt6.QtCore import QCoreApplication, QSettings, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

app = QApplication(sys.argv[:1])
QCoreApplication.setOrganizationName("RADIDE-TEST-VSX2")
QCoreApplication.setApplicationName("RADIDE-TEST-VSX2-MATRIX")
QSettings().clear()
DIALOGS = []


def close_dialogs():
    w = QApplication.activeModalWidget()
    if isinstance(w, QMessageBox):
        DIALOGS.append(w.text()[:160])
        w.done(0)
    elif isinstance(w, QDialog):
        DIALOGS.append(w.windowTitle()[:120])
        w.reject()


_t = QTimer()
_t.timeout.connect(close_dialogs)
_t.start(300)


def wait(cond, timeout=20.0, step=0.05):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(step)
    app.processEvents()
    return False


proj = SCRATCH / "Polyglot"
shutil.copytree(REPO / "samples" / "HelloPython", proj)
src = proj / "src"
src.mkdir()
for name, text in {"app.js": "const x = 1\nconsole.log( x )\n", "notes.md": "# Title\n\nSome teh text.\n",
                   "conf.yaml": "name: demo\nitems:\n  - a\n", "data.xml": "<root><a>1</a></root>\n",
                   "main.go": "package main\n\nfunc main() {}\n", "lib.rs": "fn main() {}\n",
                   "hello.c": "int main(void) { return 0; }\n", "Hello.java": "class Hello {}\n",
                   "tool.py": "import os\nprint( os.name )\n"}.items():
    (src / name).write_text(text, "utf-8")

from radide.app import MainWindow  # noqa: E402

win = MainWindow()
win.resize(1400, 900)
win.show()
win.open_project(proj, ask=False)
svc = win.vsx_host
wait(lambda: svc.host.running() and svc.host.init_result is not None, 60)
for name in ("tool.py", "app.js", "notes.md", "conf.yaml", "data.xml", "main.go", "lib.rs", "hello.c", "Hello.java"):
    try:
        ed = win.open_file(src / name) if callable(getattr(win, "open_file", None)) else win.open_any_file(src / name)
    except Exception as e:  # noqa: BLE001
        print("open", name, e)
        ed = None
    # the page of a Monaco editor loads while its tab is shown: the document reaches the extension host then
    wait(lambda: ed is None or getattr(ed, "_ready", False), 40)
    wait(lambda: False, 0.4)
code_ids = [r["id"].lower() for r in ROWS.values() if r.get("has_code")]
wait(lambda: all(i in svc.activation for i in code_ids), 120)
wait(lambda: False, 5)

from radide.vsx import contrib_themes  # noqa: E402

themes = {s.ext_id if hasattr(s, "ext_id") else "": s for s in contrib_themes.collect()}
for eid, kind, cmd in MATRIX:
    row = ROWS[eid.lower()]
    if not row.get("installed"):
        continue
    ext = next((e for e in svc.extensions if e.id == eid.lower()), None) if row.get("has_code") else None
    act = svc.activation.get(eid.lower()) if row.get("has_code") else "declarative"
    row["activation"] = act
    pj = (ext.package_json if ext is not None else None) or {}
    contributed = [c.get("command") for c in ((pj.get("contributes") or {}).get("commands") or []) if isinstance(c, dict)]
    row["commandsContributed"] = len(contributed)
    row["commandsRegistered"] = len([c for c in contributed if c in svc.host_commands])
    if cmd:
        box = {}
        svc.execute(cmd, [], lambda r: box.setdefault("v", r))
        row["command"] = {"id": cmd, "ran": wait(lambda: "v" in box, 15)}
    row["unsupported"] = sorted({a for e, a in svc.unsupported if e == eid.lower()})
    if kind == "color theme":
        try:
            from radide import theme as TH
            row["themes"] = [n for n in TH.THEMES if any(w in n.lower() for w in ("dracula", "one dark"))]
        except Exception:  # noqa: BLE001
            pass
    if kind == "icon theme":
        try:
            from radide.vsx import contrib_icons
            row["iconThemes"] = [t.get("id") if isinstance(t, dict) else str(t)
                                 for t in (contrib_icons.available() if hasattr(contrib_icons, "available") else [])]
        except Exception as e:  # noqa: BLE001
            row["iconThemes"] = str(e)

win.grab().save(str(SCRATCH / "matrix_ide.png"))
NL = chr(10)
(SCRATCH / "matrix_output.txt").write_text(NL.join(f"=== {k}{NL}{v[-6000:]}" for k, v in svc.output.texts.items()),
                                           "utf-8")
(SCRATCH / "matrix.json").write_text(json.dumps(list(ROWS.values()), indent=1), "utf-8")
lines = ["| Extension | Version | Activation | Commands registered | Command run | Unsupported |", "|---|---|---|---|---|---|"]
bad = 0
for r in ROWS.values():
    ok = r.get("installed") and (r.get("activation") in ("active", "declarative"))
    bad += 0 if ok else 1
    lines.append(f"| {r['id']} | {r.get('installed') or 'ERROR: ' + str(r.get('error'))[:80]} | {r.get('activation', '-')} | "
                 f"{r.get('commandsRegistered', '-')}/{r.get('commandsContributed', '-')} | "
                 f"{(r.get('command') or {}).get('ran', '-')} | {', '.join(r.get('unsupported') or []) or '-'} |")
(SCRATCH / "matrix.md").write_text("\n".join(lines) + "\n", "utf-8")
print("\n".join(lines))
if DIALOGS:
    print("dialogs dismissed:", DIALOGS[:20])
QSettings().clear()
try:
    svc.stop()
except Exception:  # noqa: BLE001
    pass
os._exit(bad)
