"""Crash recovery like Visual Studio's AutoRecover.

Every *Tools > Options > Auto-save* interval (60 s by default) the unsaved documents of every open project -
code editors, module editors and form designers - are copied to

    %LOCALAPPDATA%\\RADIDE\\recovery\\<project folder hash>\\
        manifest.json          {"folder", "project", "time", "pid", "files": {rel: {"kind": "code"|"form"}}}
        code\\<relative file>   the editor text
        forms\\<form>.form      the designer's form (the .form JSON)

The project files themselves are never touched, and nothing is written into the project folder (a read-only
project or one under Program Files gets recovery too). A save of everything, a clean exit and a
"Discard" answer remove the snapshot; a snapshot that is still there at the next start therefore means the
IDE crashed, was killed or the PC lost power:

* start-up (no project on the command line): "Recover unsaved work" lists those projects and opens the one
  chosen - its documents come back modified (unsaved), the user decides whether to save them;
* opening such a project later offers the same.

Every write is atomic (radide/safeio.py) and a failure (disk full, ...) never interrupts the user."""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from ..safeio import atomic_write_text, folder_key, recovery_root

VERSION = 1
MAX_TEXT = 16 * 1024 * 1024
MANIFEST = "manifest.json"
# a snapshot younger than this, written by another IDE that is still running, belongs to that IDE
ACTIVE_SECONDS = 15 * 60


def _tr(text: str) -> str:
    try:
        from ..i18n import tr
        return tr(text)
    except Exception:  # noqa: BLE001
        return text


def _states(win) -> list[dict]:
    """Every open project with its documents (the active one included)."""
    states = list(getattr(win, "_pstates", {}).values())
    if not states and getattr(win, "project", None) is not None:
        states = [{"project": win.project, "plugin": getattr(win, "plugin", None), "docs": win.docs,
                   "codeviews": win.codeviews, "modviews": win.modviews}]
    return states


def _code_file(st: dict, name: str, cv) -> str:
    plugin = getattr(cv.editor, "plugin", None) or st.get("plugin")
    try:
        return plugin.code_file(name)
    except Exception:  # noqa: BLE001
        return ""


def _safe_rel(rel: str) -> bool:
    p = Path(rel)
    return bool(rel) and not p.is_absolute() and ".." not in p.parts and not p.drive


def set_dir(folder) -> Path:
    return recovery_root() / folder_key(Path(folder).resolve())


def dirty_documents(st: dict) -> tuple[dict[str, str], dict[str, str]]:
    """({relative code file: text}, {form name: form JSON}) of the unsaved documents of one project."""
    code: dict[str, str] = {}
    forms: dict[str, str] = {}
    for name, cv in st.get("codeviews", {}).items():
        if cv.editor.isModified():
            rel = _code_file(st, name, cv)
            if _safe_rel(rel):
                code[rel] = cv.editor.text()
    for mod, mv in st.get("modviews", {}).items():
        if mv.editor.isModified() and _safe_rel(mod):
            code[mod] = mv.editor.text()
    for name, doc in st.get("docs", {}).items():
        if getattr(doc, "modified", False):
            try:
                forms[name] = json.dumps(doc.form.to_dict(), indent=1, ensure_ascii=False)
            except Exception:  # noqa: BLE001 - a form that cannot be serialised is skipped, not fatal
                pass
    return ({k: v for k, v in code.items() if len(v) <= MAX_TEXT},
            {k: v for k, v in forms.items() if len(v) <= MAX_TEXT})


def snapshot(win) -> int:
    """Write the recovery snapshot of every open project; the number of documents saved. Never raises."""
    total = 0
    for st in _states(win):
        project = st.get("project")
        try:
            folder = Path(project.folder)
            code, forms = dirty_documents(st)
            d = set_dir(folder)
            if not code and not forms:
                if d.exists():
                    shutil.rmtree(d, ignore_errors=True)
                continue
            files = {}
            for rel, text in code.items():
                (d / "code" / rel).parent.mkdir(parents=True, exist_ok=True)
                atomic_write_text(d / "code" / rel, text, newline="")
                files[rel] = {"kind": "code"}
            for name, text in forms.items():
                (d / "forms").mkdir(parents=True, exist_ok=True)
                atomic_write_text(d / "forms" / f"{name}.form", text, newline="")
                files[name] = {"kind": "form"}
            for kind, sub in (("code", d / "code"), ("form", d / "forms")):       # documents saved since
                if sub.is_dir():
                    for p in [p for p in sub.rglob("*") if p.is_file()]:
                        key = p.relative_to(sub).as_posix() if kind == "code" else p.stem
                        if key not in files:
                            p.unlink()
            manifest = {"version": VERSION, "folder": str(folder.resolve()), "project": project.name,
                        "time": time.time(), "pid": os.getpid(), "files": files}
            atomic_write_text(d / MANIFEST, json.dumps(manifest, indent=1, ensure_ascii=False), newline="")
            total += len(files)
        except Exception as e:  # noqa: BLE001 - disk full, no LOCALAPPDATA ...: try again next time
            try:
                win.log(f"[recovery] snapshot of {getattr(project, 'name', '?')} failed: {e}")
            except Exception:  # noqa: BLE001
                pass
    return total


def discard(folder) -> None:
    shutil.rmtree(set_dir(folder), ignore_errors=True)


def discard_open(win) -> None:
    """All open projects were saved or their changes discarded: no recovery needed any more."""
    for st in _states(win):
        try:
            discard(st["project"].folder)
        except Exception:  # noqa: BLE001
            pass


def _pid_alive(pid: int) -> bool:
    if not pid or pid == os.getpid():
        return False
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, int(pid))         # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return bool(ok) and code.value == 259               # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_set(d: Path) -> dict | None:
    try:
        m = json.loads((d / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(m, dict) or not isinstance(m.get("files"), dict) or not m.get("folder"):
        return None
    m["dir"] = str(d)
    return m


def pending(include_live: bool = False) -> list[dict]:
    """Recovery snapshots left by an IDE that is gone (crashed / killed), newest first."""
    root = recovery_root()
    out = []
    if not root.is_dir():
        return out
    for d in root.iterdir():
        if not d.is_dir() or d.name == "backups":
            continue
        m = read_set(d)
        if m is None or not m["files"]:
            continue
        if not include_live and _pid_alive(int(m.get("pid") or 0)) \
                and time.time() - float(m.get("time") or 0) < ACTIVE_SECONDS:
            continue                                     # another running IDE's own snapshot
        if not Path(m["folder"]).is_dir():
            continue
        out.append(m)
    return sorted(out, key=lambda m: -float(m.get("time") or 0))


def for_folder(folder) -> dict | None:
    m = read_set(set_dir(folder))
    if m is None or not m["files"]:
        return None
    if _pid_alive(int(m.get("pid") or 0)) and time.time() - float(m.get("time") or 0) < ACTIVE_SECONDS:
        return None
    return m


def restore(win, m: dict) -> list[str]:
    """Put the snapshot *m* into the open project's editors / designers (they become modified)."""
    d = Path(m["dir"])
    done = []
    for key, info in m["files"].items():
        kind = (info or {}).get("kind")
        try:
            if kind == "form":
                text = (d / "forms" / f"{key}.form").read_text(encoding="utf-8")
                json.loads(text)
                if key not in getattr(win.project, "forms", []):
                    continue
                doc = win._doc(key)
                doc.checkpoint()                          # Undo goes back to the saved form
                doc._restore(text)
                win.open_designer(key)
                done.append(f"{key} [Design]")
            elif kind == "code" and _safe_rel(key):
                text = (d / "code" / key).read_text(encoding="utf-8")
                ed = win._editor_for_file(key) if "/" not in key else None
                if ed is None and hasattr(win, "open_file"):
                    ed = win.open_file(Path(win.project.folder) / key)
                if ed is not None:
                    ed.setText(text)
                    try:
                        ed.setModified(True)
                    except Exception:  # noqa: BLE001
                        pass
                    done.append(key)
        except Exception as e:  # noqa: BLE001
            try:
                win.log(f"[recovery] {key} could not be restored: {e}")
            except Exception:  # noqa: BLE001
                pass
    return done


def _ask(win, title: str, text: str) -> bool | None:
    """True / False; None = not asked (a test run without RADIDE_TEST_RECOVERY_ANSWER never blocks a
    test suite with a dialog; the snapshot is kept)."""
    from PyQt6.QtCore import QCoreApplication
    from PyQt6.QtWidgets import QMessageBox
    auto = os.environ.get("RADIDE_TEST_RECOVERY_ANSWER")           # tests: "yes" / "no" without a dialog
    if auto:
        return auto.lower().startswith("y")
    if QCoreApplication.organizationName().upper().startswith("RADIDE-TEST"):
        return None
    return QMessageBox.question(win, title, text) == QMessageBox.StandardButton.Yes


def _names(m: dict) -> str:
    return "\n  ".join(k + (" [Design]" if (v or {}).get("kind") == "form" else "") for k, v in m["files"].items())


def offer_for_project(win) -> list[str]:
    """After a project opened: restore its snapshot from a crashed session (asks first)."""
    restored: list[str] = []
    for st in _states(win):
        try:                    # temp files of a save that was killed half-way (the real files are intact)
            from ..safeio import clean_stale_temps
            clean_stale_temps(st["project"].folder)
        except Exception:  # noqa: BLE001
            pass
        m = for_folder(st["project"].folder)
        if m is None:
            continue
        key = folder_key(Path(m["folder"]))
        accepted = key in getattr(win, "_recovery_accepted", set())
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(float(m.get("time") or 0)))
        answer = True if accepted else _ask(win, _tr("Recover Unsaved Work"),
                            _tr("RAD IDE closed unexpectedly. Unsaved changes of these documents were "
                                "recovered:") + f"\n  {_names(m)}\n\n" +
                            _tr(f"Saved at: {when}") + "\n\n" +
                            _tr("Restore them? (They are opened as unsaved changes; the files on disk "
                                "stay as they are until you save.)"))
        if answer is None:
            continue
        if answer:
            if win.project is not st["project"] and hasattr(win, "activate_project"):
                win.activate_project(st["project"])
            restored += restore(win, m)
            try:
                win.log(_tr("Recovered unsaved changes:") + " " + ", ".join(restored))
            except Exception:  # noqa: BLE001
                pass
        else:
            discard(m["folder"])
    if hasattr(win, "_recovery_accepted"):
        win._recovery_accepted.clear()
    return restored


def offer_at_startup(win) -> str | None:
    """At start-up: snapshots of crashed sessions -> open the newest project and restore it. Returns the
    folder that was opened (None when nothing was offered / accepted)."""
    sets = pending()
    if not sets:
        return None
    lines = "\n  ".join(f"{m.get('project') or Path(m['folder']).name}  ({len(m['files'])})  {m['folder']}"
                        for m in sets[:8])
    answer = _ask(win, _tr("Recover Unsaved Work"),
                _tr("RAD IDE closed unexpectedly. Unsaved work was recovered for:") + f"\n  {lines}\n\n" +
                _tr("Open the project and restore the unsaved changes?"))
    if answer is None:
        return None
    if not answer:
        if _ask(win, _tr("Recover Unsaved Work"), _tr("Delete the recovered files?")):
            for m in sets:
                discard(m["folder"])
        return None
    m = sets[0]
    if not hasattr(win, "_recovery_accepted"):
        win._recovery_accepted = set()
    win._recovery_accepted.add(folder_key(Path(m["folder"])))
    target = Path(m["folder"])
    try:
        win.open_project(target, ask=False)
    except TypeError:
        win.open_project(target)
    return str(target)


__all__ = ["discard", "discard_open", "dirty_documents", "for_folder", "offer_at_startup", "offer_for_project",
           "pending", "restore", "set_dir", "snapshot"]
