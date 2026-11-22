r"""Action crawler: triggers EVERY user-facing action / command of the IDE one by one and checks that nothing breaks.

For each context (a sandbox copy of a project of each kind, or no project) and workbench layout (VS / VS Code /
Agent) a worker process opens the IDE offscreen (QSettings org "RADIDE-TEST-CRAWL", cleared before and after),
harvests every entry point (menu bar with dynamic menus filled, tool bars, Command Palette commands, context menus
of Solution Explorer items / editor tabs / designer / docks; crawl_common.harvest) and triggers them one at a time:

  * any dialog that appears is handled: title + class recorded, screenshot (widget.grab), every visible interactive
    child must have an accessible name (QAccessible Name), then Cancel / Close / Esc (reject);
  * windows that open without being modal are recorded and closed the same way;
  * popup menus are captured, never shown; external programs / browsers / hh.exe are recorded, never started;
  * per action time limit; an event-loop heartbeat tells "blocked" (hang) from "still busy in a nested loop".
Checks per action: no Python exception (sys.excepthook, threading.excepthook, tracebacks written to stderr, Qt
critical/fatal messages, tracebacks in the IDE's Output window), no hang, no crash (the parent restarts the worker
after the action that killed it), no modal left open, the main window still visible and responsive, no files written
outside the sandbox (audit hook on open/rename/remove/mkdir; the IDE's own data folder %LOCALAPPDATA%\RADIDE is
reported separately), processes started by the action are ended afterwards (only those).

Skipped on purpose (SKIP_RULES, each with its reason): quit / exit / restart, a second IDE window, uninstall,
delete from disk, git push / sync, publishing to the internet (cloud, FTP, stores, registries), installing or
downloading tool chains / updates, registering Windows shell integration.

Run:
    .venv\Scripts\python samples\Tests\Crawler\test_action_crawler.py                 # default plan (see PLAN)
    ... --contexts python-tk,web --modes vs --full                                    # every action in every context
    ... --quick                                                                        # python-tk / VS only
Report: <out>\crawl_results.json, <out>\CRAWL_REPORT.md (the table action | context | result | dialog | time |
error) and the dialog screenshots in <out>\shots. --out defaults to %QA_OUT% or <temp>\radide-crawl.
Exit code: number of actions with result exception / hang / crash / modal-left / unresponsive.
"""
from __future__ import annotations

import argparse
import faulthandler
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crawl_common as C  # noqa: E402

FREEZE = 8.0          # seconds the UI thread may be blocked by one action before it counts as unresponsive
BAD = ("exception", "hang", "crash", "modal-left", "unresponsive")

# (regex on "path > text", reason) - matched case-insensitively against the full label
SKIP_RULES = [
    (r"(^|> )(e?xit|quit)( |$)|exit ide|close ide|restart (the )?ide|restart rad|^.*> restart$",
     "quits / restarts the IDE"),
    (r"new window", "starts a second IDE process"),
    (r"uninstall", "uninstalls software"),
    (r"delete (the )?(project|solution|folder)|from disk|delete permanently|move to recycle|purge|wipe",
     "deletes files from disk"),
    (r"\bgit\b.*\b(push|sync)\b|^.*> (push|sync|publish branch|force push)\b|push to |pull request",
     "git push / sync changes a remote repository"),
    (r"\b(ftp|sftp|azure|aws|heroku|netlify|vercel|firebase|play store|google play|app store|microsoft store|"
     r"testflight|github pages|gh-pages|docker push|nuget push|npm publish|pypi|crates\.io|pub\.dev|"
     r"upload|deploy to|publish to (the )?(web|cloud|server|store|internet)|cloud deploy|ssh deploy|"
     r"remote deploy|web deploy)\b", "publishes to the internet / cloud / FTP / a store"),
    (r"(^|> )(download|install|update|upgrade)\b(?!.*\.\.\.)(?!.*(project|form|reference|package list))|"
     r"install (the )?(sdk|toolchain|tool chain|compiler|update)|check for updates|download (sdk|tools)|"
     r"get (the )?sdk|setup (sdk|toolchain)|install now|update now|install update", "downloads / installs software"),
    (r"shell integration|file association|register .*(explorer|context menu)|unregister", "changes Windows settings"),
    (r"sign in|log ?in to|sign out|live share|start collaboration|share session", "signs in to an online service"),
    (r"report (a )?(bug|issue)|send feedback", "opens the internet"),
]
SKIP_RE = [(re.compile(p, re.I), why) for p, why in SKIP_RULES]

# default plan: (context, mode, scope) - scope "all" = every entry, "specific" = only entries that are new in this
# context or live in a context-dependent menu (Build / Debug / Project / Publish / ... and every context menu)
PLAN = [("python-tk", "vs", "all"), ("none", "vs", "specific"), ("python-tk", "vscode", "specific"),
        ("python-tk", "agent", "specific")] + [
    (c, "vs", "specific") for c in ("vb6", "csharp", "web", "flask", "flutter", "retro", "dos", "game", "asm",
                                    "firmware")]
CONTEXT_MENUS = {"Build", "Debug", "Project", "Publish", "Site", "Run", "Website", "Mobile", "Test", "Format",
                 "Data", "Firmware", "Retro", "Game", "Assembly"}


def skip_reason(label: str) -> str:
    for rx, why in SKIP_RE:
        if rx.search(label):
            return why
    return ""


def label_of(e: dict) -> str:
    return " > ".join(list(e["path"]) + [e["text"]])


# =================================================================================================== worker
class Worker:
    def __init__(self, a):
        self.a = a
        self.ctx, self.mode = a.ctx, a.mode
        self.out = Path(a.out)
        self.sandbox = self.out / "sandbox" / f"{self.ctx}-{self.mode}"
        self.shots = self.out / "shots"
        self.shots.mkdir(parents=True, exist_ok=True)
        self.exc: list[str] = []
        self.qt_msgs: list[str] = []
        self.qt_warn = 0
        self.writes: list[tuple[str, str]] = []
        self.beat = time.time()
        self.cur: dict | None = None
        self.cur_start = 0.0
        self.dialogs: list[dict] = []
        self.dialog_n = 0
        self.closing = False
        self.allowed = []
        self.ide_data = ""
        self.harness_errors: list[str] = []
        self.max_gap = 0.0

    # ------------------------------------------------------------------ hooks
    def install_hooks(self):
        w = self
        real_exit, real_oexit = sys.exit, os._exit

        def traced_exit(code=0):
            emit("EXIT", {"code": str(code), "stack": "".join(traceback.format_stack()[-12:])[-3000:],
                          "key": w.cur["key"] if w.cur else ""})
            real_exit(code)

        def traced_oexit(code):
            if code not in (0, 3):
                emit("EXIT", {"code": str(code), "stack": "".join(traceback.format_stack()[-12:])[-3000:],
                              "key": w.cur["key"] if w.cur else ""})
            real_oexit(code)
        sys.exit, os._exit = traced_exit, traced_oexit
        try:
            from PyQt6.QtCore import QCoreApplication
            real_q = QCoreApplication.exit

            def traced_q(code=0):
                emit("EXIT", {"code": f"QCoreApplication.exit({code})", "stack": "".join(
                    traceback.format_stack()[-12:])[-3000:], "key": w.cur["key"] if w.cur else ""})
                real_q(code)
            QCoreApplication.exit = staticmethod(traced_q)
            QCoreApplication.quit = staticmethod(lambda: traced_q(0))
        except Exception:  # noqa: BLE001
            pass

        def excepthook(t, v, tb):
            text = "".join(traceback.format_exception(t, v, tb))
            w.exc.append(text[-3000:])
            try:
                sys.__stderr__.write("[crawl] uncaught: " + text[-3000:] + chr(10))
            except Exception:  # noqa: BLE001
                pass
        sys.excepthook = excepthook
        threading.excepthook = lambda args: excepthook(args.exc_type, args.exc_value, args.exc_traceback)

        class Tee(io.TextIOBase):
            def __init__(self, real):
                self.real, self.buf = real, ""

            def write(self, s):
                try:
                    self.real.write(s)
                except Exception:  # noqa: BLE001
                    pass
                if w.cur is not None:
                    self.buf += s
                    if len(self.buf) > 200000:
                        self.buf = self.buf[-100000:]
                return len(s)

            def flush(self):
                try:
                    self.real.flush()
                except Exception:  # noqa: BLE001
                    pass
        self.err_tee = Tee(sys.stderr)
        sys.stderr = self.err_tee
        from PyQt6.QtCore import QtMsgType, qInstallMessageHandler

        def qt_handler(kind, ctx, msg):
            if kind in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
                if w.cur is not None:
                    w.qt_msgs.append(msg[:400])
            elif kind == QtMsgType.QtWarningMsg:
                w.qt_warn += 1
        qInstallMessageHandler(qt_handler)

        sb = os.path.normcase(str(self.out.resolve()))
        tmp = os.path.normcase(os.path.realpath(tempfile.gettempdir()))
        self.ide_data = os.path.normcase(str(Path(os.environ.get("LOCALAPPDATA", "")) / "RADIDE"))
        self.ide_data2 = os.path.normcase(str(Path(os.environ.get("APPDATA", "")) / "RADIDE"))
        org = os.path.normcase(str(Path(os.environ.get("LOCALAPPDATA", "")) / C.ORG))
        roam = os.path.normcase(str(Path(os.environ.get("APPDATA", "")) / C.ORG))
        self.allowed = [sb, tmp, org, roam, "nul", "\\\\.\\", "con"]
        wflags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC

        def audit(event, args):
            if w.cur is None:
                return
            try:
                if event == "open":
                    path, mode, flags = args
                    if isinstance(path, int) or path is None:
                        return
                    if mode is not None:
                        if not any(c in str(mode) for c in "wax+"):
                            return
                    elif not (flags or 0) & wflags:
                        return
                elif event in ("os.remove", "os.rename", "os.mkdir", "os.rmdir", "shutil.rmtree", "os.replace"):
                    path = args[0]
                else:
                    return
                p = os.path.normcase(os.path.abspath(os.fsdecode(path)))
                if "__pycache__" in p or p.endswith(".pyc"):
                    return
                if any(p.startswith(a) for a in w.allowed):
                    return
                kind = "ide-data" if p.startswith(w.ide_data) or p.startswith(w.ide_data2) else "outside"
                if len(w.writes) < 50:
                    w.writes.append((kind, f"{event} {p}"))
            except Exception:  # noqa: BLE001
                pass
        sys.addaudithook(audit)

    # ------------------------------------------------------------------ dialogs
    def a11y_missing(self, dlg) -> list[str]:
        """Visible, enabled interactive children without an accessible name (what a screen reader announces):
        accessibleName, else the button's text, else a QLabel whose buddy it is / its QFormLayout label (the same
        fall-backs Qt's accessibility uses; PyQt6 has no QAccessible to ask directly)."""
        from PyQt6.QtWidgets import (QAbstractButton, QAbstractItemView, QAbstractSlider, QAbstractSpinBox,
                                     QComboBox, QFormLayout, QLabel, QLineEdit, QPlainTextEdit, QTextEdit, QWidget)
        kinds = (QAbstractButton, QLineEdit, QComboBox, QAbstractSpinBox, QAbstractSlider, QPlainTextEdit,
                 QTextEdit, QAbstractItemView)
        buddies = {}
        for lb in dlg.findChildren(QLabel):
            if lb.buddy() is not None and lb.text().strip():
                buddies[id(lb.buddy())] = lb.text()
        missing = []
        for wd in dlg.findChildren(QWidget):
            if not isinstance(wd, kinds) or not wd.isVisibleTo(dlg) or not wd.isEnabled():
                continue
            if isinstance(wd, QLineEdit) and isinstance(wd.parentWidget(), (QComboBox, QAbstractSpinBox)):
                continue
            if type(wd).__name__ == "QScrollBar":
                continue                                  # the editor inside a combo / spin box
            name = wd.accessibleName().strip()
            if not name and isinstance(wd, QAbstractButton):
                name = wd.text().replace("&", "").strip()
                if not name and getattr(wd, "defaultAction", None) and wd.defaultAction() is not None:
                    name = wd.defaultAction().text().strip()
            if not name:
                name = buddies.get(id(wd), "")
            if not name:
                par = wd.parentWidget()
                lay = par.layout() if par is not None else None
                if isinstance(lay, QFormLayout):
                    lab = lay.labelForField(wd)
                    if isinstance(lab, QLabel):
                        name = lab.text().strip()
            if not name:
                tip = wd.toolTip()
                missing.append(f"{type(wd).__name__}:{wd.objectName() or '?'}" + (f" (tip: {tip[:40]})" if tip else ""))
        return missing

    def record_dialog(self, dlg, modal: bool):
        self.dialog_n += 1
        title = dlg.windowTitle() or type(dlg).__name__
        shot = ""
        try:
            safe = re.sub(r"[^\w.-]+", "_", f"{self.ctx}-{self.mode}-{self.dialog_n:04d}-{title}")[:90]
            p = self.shots / (safe + ".png")
            dlg.grab().save(str(p))
            shot = p.name
        except Exception:  # noqa: BLE001
            pass
        text = ""
        try:
            from PyQt6.QtWidgets import QMessageBox
            if isinstance(dlg, QMessageBox):
                text = dlg.text()[:300]
        except Exception:  # noqa: BLE001
            pass
        d = {"title": title, "class": type(dlg).__name__, "modal": modal, "shot": shot,
             "a11y_missing": self.a11y_missing(dlg)[:30], "text": text}
        try:
            d["controls"] = C.dialog_controls(dlg)
        except Exception:  # noqa: BLE001
            pass
        self.dialogs.append(d)

    def close_widget(self, dlg):
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox
        try:
            if isinstance(dlg, QMessageBox):
                b = dlg.escapeButton()
                if b is None:
                    for btn in dlg.buttons():
                        if dlg.buttonRole(btn) in (QMessageBox.ButtonRole.RejectRole, QMessageBox.ButtonRole.NoRole):
                            b = btn
                            break
                if b is not None:
                    b.click()
                    return
                dlg.reject()
                return
            if isinstance(dlg, QDialog):
                dlg.reject()
                if dlg.isVisible():
                    QApplication.sendEvent(dlg, QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape,
                                                          Qt.KeyboardModifier.NoModifier))
                if dlg.isVisible():
                    dlg.close()
                return
            dlg.close()
        except Exception as e:  # noqa: BLE001
            self.exc.append(f"closing dialog {type(dlg).__name__}: {e!r}")

    def tick(self):
        """Every 100 ms (also inside nested event loops of dialogs): heartbeat + modal dialogs."""
        now = time.time()
        if self.cur is not None:
            self.max_gap = max(self.max_gap, now - self.beat)
        self.beat = now
        if self.closing:
            return
        from PyQt6.QtWidgets import QApplication
        m = QApplication.activeModalWidget()
        if m is None:
            return
        if self.cur is None:                     # a modal outside an action (start-up, restore): just close it
            self.closing = True
            try:
                print(f"[crawl] closing modal outside an action: {type(m).__name__} '{m.windowTitle()}'",
                      file=sys.__stderr__)
                self.close_widget(m)
            finally:
                self.closing = False
            return
        self.closing = True
        try:
            if len(self.dialogs) < 40:
                try:
                    self.record_dialog(m, True)
                except Exception:  # noqa: BLE001 - the dialog is closed anyway
                    self.harness_errors.append(traceback.format_exc()[-1500:])
            self.close_widget(m)
        finally:
            self.closing = False

    # ------------------------------------------------------------------ boot
    def start(self):
        C.boot(self.a.app_name)
        self.install_hooks()
        from PyQt6.QtCore import QTimer
        self.w = C.window()
        self.timer = QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.folder = C.open_context(self.w, self.ctx, self.sandbox)
        C.set_mode(self.w, self.mode)
        C.pump(1.0)
        self.baseline_tops = self.top_ids()
        try:
            import psutil
            self.ps = psutil.Process()
        except Exception:  # noqa: BLE001
            self.ps = None
        t = threading.Thread(target=self.watchdog, daemon=True)
        t.start()

    def watchdog(self):
        limit = self.a.action_timeout
        while True:
            time.sleep(0.5)
            cur = self.cur
            if cur is None:
                continue
            el = time.time() - self.cur_start
            if el > limit:
                blocked = time.time() - self.beat > 2.0
                msg = {"key": cur["key"], "result": "hang",
                       "error": ("event loop blocked" if blocked else "still running in a nested event loop")
                       + f" after {el:.0f}s", "time": round(el, 2)}
                try:
                    faulthandler.dump_traceback(file=sys.__stderr__, all_threads=True)
                except Exception:  # noqa: BLE001
                    pass
                tb = ""
                try:
                    frame = sys._current_frames().get(threading.main_thread().ident)
                    tb = "".join(traceback.format_stack(frame)[-12:]) if frame else ""
                except Exception:  # noqa: BLE001
                    pass
                msg["traceback"] = tb[-3000:]
                emit("HANG", msg)
                sys.__stdout__.flush()
                end_children()
                os._exit(3)

    def top_ids(self) -> set[int]:
        from PyQt6.QtWidgets import QApplication
        return {id(t) for t in QApplication.topLevelWidgets() if t.isVisible()}

    def children(self) -> set[int]:
        if self.ps is None:
            return set()
        try:
            return {p.pid for p in self.ps.children(recursive=True)}
        except Exception:  # noqa: BLE001
            return set()

    def end_new_processes(self, before: set[int]) -> list[str]:
        if self.ps is None:
            return []
        ended = []
        try:
            for p in self.ps.children(recursive=True):
                if p.pid in before:
                    continue
                try:
                    name = p.name()
                    cmd = " ".join(p.cmdline())[:200]
                except Exception:  # noqa: BLE001
                    continue
                if re.search(r"QtWebEngineProcess|conhost", name, re.I):
                    continue
                if re.search(r"pylsp|language.?server|clangd|omnisharp|jdtls|lsp|tsserver|intelephense|"
                             r"rust-analyzer|gopls|asm-lsp", cmd, re.I):
                    continue
                try:
                    p.kill()
                    ended.append(name)
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass
        return ended

    # ------------------------------------------------------------------ restore state
    def restore(self):
        w = self.w
        notes = []
        try:
            if not w.isVisible():
                notes.append("main window was hidden")
                w.show()
            if getattr(w, "session", None) is not None:
                try:
                    w.stop_project()
                except Exception:  # noqa: BLE001
                    pass
            if self.folder is not None:
                p = getattr(w, "project", None)
                if p is None or os.path.normcase(str(Path(p.folder).resolve())) != os.path.normcase(
                        str(self.folder.resolve())):
                    if not (self.folder / "project.radproj").exists() and not any(self.folder.glob("*.rad*")):
                        self.folder = C.make_sandbox(self.ctx, self.sandbox)
                    w.open_project(self.folder, ask=False)
                    C.pump(1.0)
                    notes.append("project reopened")
            if C.current_mode(w) != self.mode:
                C.set_mode(w, self.mode)
                notes.append("layout restored")
            from PyQt6.QtWidgets import QApplication
            for t in QApplication.topLevelWidgets():
                try:
                    if t is w or not t.isVisible() or id(t) in self.baseline_tops:
                        continue
                    if t.inherits("QMenu") or t.inherits("QTipLabel"):
                        t.hide()
                except RuntimeError:
                    continue
        except Exception as e:  # noqa: BLE001
            notes.append(f"restore failed: {e!r}")
        return notes

    # ------------------------------------------------------------------ run one entry
    def find_entry(self, e: dict, fresh: list[dict]) -> dict | None:
        for f in fresh:
            if f["key"] == e["key"]:
                return f
        return None

    def run(self, e: dict) -> dict:
        from PyQt6.QtWidgets import QApplication
        w = self.w
        rec = {"key": e["key"], "label": label_of(e), "source": e["source"], "context": self.ctx, "mode": self.mode,
               "result": "ok", "dialog": "", "time": 0.0, "error": ""}
        # context menu entries: open the menu again (its actions are built per invocation)
        target = e
        if e["source"] == "context" and e.get("_trigger") is not None:
            menus = C.capture(e["_trigger"])
            fresh = C._menu_entries(menus, e["path"], "context")
            for f in fresh:
                f["key"] = C.entry_key(f)
            target = self.find_entry(e, fresh) or e
        act, btn, cmd = target.get("_action"), target.get("_button"), target.get("_command")
        try:
            (act or btn).objectName() if (act or btn) is not None else None
        except RuntimeError:                             # rebuilt menu: harvest the window again, same key
            fresh = [f for f in C.harvest(w, context=False) if f["key"] == e["key"]]
            if fresh:
                act, btn, cmd = fresh[0].get("_action"), fresh[0].get("_button"), fresh[0].get("_command")
        enabled = True
        try:
            if act is not None:
                enabled = act.isEnabled()
            elif btn is not None:
                enabled = btn.isEnabled()
            elif cmd is not None and cmd.enabled:
                enabled = bool(cmd.enabled())
        except RuntimeError as ex:                       # wrapped C/C++ object deleted
            rec.update(result="stale", error=str(ex)[:200])
            return rec
        except Exception:  # noqa: BLE001
            enabled = False
        if not enabled:
            rec["result"] = "disabled"
            return rec
        out_len = len(w.output.toPlainText())
        self.exc.clear()
        self.qt_msgs.clear()
        self.writes.clear()
        self.dialogs.clear()
        C.RECORDED.clear()
        try:
            from radide.features import help as H
            H.open_url.last = ""
        except Exception:  # noqa: BLE001
            H = None
        self.err_tee.buf = ""
        procs_before = self.children()
        tops_before = self.top_ids()
        t0 = time.time()
        self.cur_start = t0
        self.beat = t0
        self.max_gap = 0.0
        self.cur = e
        emit("START", {"key": e["key"]})
        try:
            if act is not None:
                act.trigger()
            elif btn is not None:
                btn.click()
            elif cmd is not None:
                cmd.callback()
        except Exception:  # noqa: BLE001
            self.exc.append(traceback.format_exc()[-3000:])
        # settle: timers / deferred work / dialogs opened with QTimer.singleShot
        end = time.time() + self.a.settle
        while time.time() < end:
            QApplication.processEvents()
            time.sleep(0.01)
        # windows that opened without being modal
        for t in QApplication.topLevelWidgets():
            try:
                if id(t) in tops_before or t is w or not t.isVisible():
                    continue
            except RuntimeError:                         # deleted by closing an earlier window (DeleteOnClose)
                continue
            if t.inherits("QMenu") or t.inherits("QTipLabel") or t.inherits("QComboBoxPrivateContainer"):
                t.hide()
                continue
            if len(self.dialogs) < 40:
                try:
                    self.record_dialog(t, False)
                except Exception:  # noqa: BLE001
                    self.harness_errors.append(traceback.format_exc()[-1500:])
            self.close_widget(t)
            QApplication.processEvents()
        self.cur = None
        rec["time"] = round(time.time() - t0, 2)
        # ---- checks
        left = QApplication.activeModalWidget()
        out_new = w.output.toPlainText()[out_len:] if len(w.output.toPlainText()) >= out_len else ""
        tb_out = [ln for ln in out_new.splitlines() if re.search(r"Traceback \(most recent|failed to load", ln)]
        err_tb = "Traceback (most recent call last)" in self.err_tee.buf
        errors = []
        if self.exc:
            errors.append(self.exc[0])
        if tb_out:
            i = out_new.find("Traceback")
            errors.append("Output: " + out_new[max(0, i):i + 2500])
        if err_tb:
            i = self.err_tee.buf.find("Traceback (most recent call last)")
            errors.append("stderr: " + self.err_tee.buf[i:i + 2500])
        if self.qt_msgs:
            errors.append("Qt critical: " + "; ".join(self.qt_msgs[:3]))
        if errors:
            rec["result"] = "exception"
            rec["error"] = "\n---\n".join(errors)[:6000]
        if left is not None:
            self.closing = True
            self.close_widget(left)
            self.closing = False
            if rec["result"] == "ok":
                rec["result"] = "modal-left"
                rec["error"] = f"modal still open: {type(left).__name__} '{left.windowTitle()}'"
        # responsive: the event loop runs (heartbeat) right after the action; a freeze of more than FREEZE seconds
        # while the action ran (the UI thread blocked: no repaint, no input) counts as unresponsive too
        C.pump(0.3)
        gap = self.max_gap
        if rec["result"] == "ok" and (time.time() - self.beat > 1.0 or not w.isVisible()):
            rec["result"] = "unresponsive"
            rec["error"] = f"main window not responding after the action (heartbeat {time.time() - self.beat:.1f}s ago)"
        elif rec["result"] == "ok" and gap > FREEZE:
            rec["result"] = "unresponsive"
            rec["error"] = f"UI thread blocked for {gap:.1f}s while the action ran"
        if gap > 1.0:
            rec["freeze"] = round(gap, 1)
        if self.harness_errors:
            rec["harness_errors"] = self.harness_errors[:2]
            self.harness_errors = []
        if self.dialogs:
            rec["dialog"] = " | ".join(f"{d['title']} [{d['class']}]" for d in self.dialogs[:4])
            rec["dialogs"] = self.dialogs[:10]
        outside = [x for k, x in self.writes if k == "outside"]
        if outside:
            rec["writes_outside"] = outside[:10]
        idata = [x for k, x in self.writes if k == "ide-data"]
        if idata:
            rec["writes_ide_data"] = idata[:5]
        opened = list(C.RECORDED)
        if H is not None and getattr(H.open_url, "last", ""):
            opened.append(("help-url", H.open_url.last))
        if opened:
            rec["opened"] = opened[:6]
        ended = self.end_new_processes(procs_before)
        if ended:
            rec["processes_ended"] = ended[:10]
        notes = self.restore()
        if notes:
            rec["notes"] = notes
        return rec


def end_children() -> None:
    """Processes this worker started (and the IDE did not end: the VS Code extension host, servers ...)."""
    try:
        import psutil
        for c in psutil.Process().children(recursive=True):
            try:
                c.kill()
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass


def emit(tag: str, obj: dict) -> None:
    sys.__stdout__.write(f"@@{tag} " + json.dumps(obj, ensure_ascii=False, default=str) + "\n")
    sys.__stdout__.flush()


def worker_main(a) -> int:
    faulthandler.enable(file=sys.__stderr__, all_threads=False)     # native crashes: the Python stack in the log
    W = Worker(a)
    W.start()
    done = set()
    if a.done_file and Path(a.done_file).exists():
        done = set(json.loads(Path(a.done_file).read_text(encoding="utf-8")))
    skip_keys = set()
    if a.skip_file and Path(a.skip_file).exists():
        skip_keys = set(json.loads(Path(a.skip_file).read_text(encoding="utf-8")))
    ents = C.harvest(W.w)
    uniq, seen = [], set()
    for e in ents:
        if e["key"] in seen or e.get("kind") not in ("action", "command", "button"):
            continue
        seen.add(e["key"])
        uniq.append(e)
    emit("HARVEST", {"count": len(uniq), "keys": [e["key"] for e in uniq]})
    n = 0
    for e in uniq:
        k = e["key"]
        if k in done:
            continue
        if a.scope == "specific" and k in skip_keys:
            top = e["path"][0] if e["path"] else ""
            if e["source"] != "context" and top not in CONTEXT_MENUS and not k.startswith("palette|") or (
                    k.startswith("palette|")):
                continue
        if a.only and not re.search(a.only, label_of(e), re.I):
            continue
        if a.limit and n >= a.limit:
            break
        n += 1
        why = skip_reason(label_of(e))
        if why:
            emit("END", {"key": k, "label": label_of(e), "source": e["source"], "context": W.ctx, "mode": W.mode,
                         "result": "skipped", "dialog": "", "time": 0, "error": why})
            continue
        try:
            rec = W.run(e)
        except Exception:  # noqa: BLE001 - a harness error must not end the crawl
            W.cur = None
            rec = {"key": k, "label": label_of(e), "source": e["source"], "context": W.ctx, "mode": W.mode,
                   "result": "harness-error", "dialog": "", "time": 0, "error": traceback.format_exc()[-2500:]}
            try:
                W.restore()
            except Exception:  # noqa: BLE001
                pass
        emit("END", rec)
    emit("DONE", {"exceptions_outside_actions": W.exc[:3]})
    try:
        W.w.close()
        C.pump(0.5)
    except Exception:  # noqa: BLE001
        pass
    C.clear_settings(a.app_name)
    end_children()
    sys.__stdout__.flush()
    os._exit(0)


# =================================================================================================== parent
def new_job(proc):
    """The worker and every process it starts in a Windows Job Object (tools/run_tests.py), ended afterwards."""
    try:
        sys.path.insert(0, str(C.ROOT / "tools"))
        from run_tests import _Job
        j = _Job()
        j.assign(proc)
        return j
    except Exception:  # noqa: BLE001
        return None


def end_job(job) -> None:
    if job is None:
        return
    try:
        job.terminate()
        job.close()
    except Exception:  # noqa: BLE001
        pass
    time.sleep(1.0)


clear_test_org = C.clear_test_org


def kill_tree(proc: subprocess.Popen) -> None:
    try:
        import psutil
        p = psutil.Process(proc.pid)
        for c in p.children(recursive=True):
            try:
                c.kill()
            except Exception:  # noqa: BLE001
                pass
        p.kill()
    except Exception:  # noqa: BLE001
        try:
            proc.kill()
        except Exception:  # noqa: BLE001
            pass


def run_job(ctx, mode, scope, args, out: Path, seen_keys: set, results: list, jobs_so_far=(),
            started_at: float = 0.0) -> dict:
    jobs_so_far = list(jobs_so_far)
    done: set[str] = set()
    info = {"context": ctx, "mode": mode, "scope": scope, "harvested": 0, "restarts": 0}
    jobdir = out / "jobs"
    jobdir.mkdir(parents=True, exist_ok=True)
    done_file = jobdir / f"{ctx}-{mode}.done.json"
    skip_file = jobdir / f"{ctx}-{mode}.seen.json"
    skip_file.write_text(json.dumps(sorted(seen_keys)), encoding="utf-8")
    log = open(jobdir / f"{ctx}-{mode}.log", "a", encoding="utf-8")
    harvested: list[str] = []
    for attempt in range(args.max_restarts + 1):
        done_file.write_text(json.dumps(sorted(done)), encoding="utf-8")
        cmd = [sys.executable, "-X", "utf8", str(Path(__file__).resolve()), "--worker", "--ctx", ctx, "--mode", mode,
               "--scope", scope, "--out", str(out), "--done-file", str(done_file), "--skip-file", str(skip_file),
               "--action-timeout", str(args.action_timeout), "--settle", str(args.settle),
               "--app-name", f"crawl-{ctx}-{mode}-{attempt}"]      # own QtWebEngine profile per attempt
        if args.limit:
            cmd += ["--limit", str(args.limit)]
        if args.only:
            cmd += ["--only", args.only]
        env = dict(os.environ)
        env.update(C.ENV)
        tmp = out / "sandbox" / "tmp" / f"{ctx}-{mode}"
        tmp.mkdir(parents=True, exist_ok=True)
        env["TEMP"] = env["TMP"] = str(tmp)
        env["PYTHONUNBUFFERED"] = "1"
        p = subprocess.Popen(cmd, cwd=str(C.ROOT), env=env, stdout=subprocess.PIPE, stderr=log,
                             text=True, encoding="utf-8", errors="replace", bufsize=1)
        job = new_job(p)
        q: list[str] = []
        th = threading.Thread(target=lambda: [q.append(ln) for ln in p.stdout], daemon=True)
        th.start()
        current = None
        exit_info = None
        last = time.time()
        boot_deadline = time.time() + 300
        finished = False
        while True:
            while q:
                ln = q.pop(0)
                last = time.time()
                if not ln.startswith("@@"):
                    log.write(ln)
                    continue
                tag, _, body = ln[2:].partition(" ")
                try:
                    obj = json.loads(body)
                except Exception:  # noqa: BLE001
                    continue
                if tag == "HARVEST":
                    harvested = obj["keys"]
                    info["harvested"] = obj["count"]
                    say(f"[{ctx}/{mode}] {obj['count']} entries harvested")
                elif tag == "START":
                    current = obj["key"]
                elif tag in ("END", "HANG"):
                    if tag == "HANG":
                        obj.setdefault("label", obj["key"].split("|", 2)[-1])
                        obj.update(context=ctx, mode=mode, source=obj["key"].split("|", 1)[0], dialog="")
                    done.add(obj["key"])
                    current = None
                    results.append(obj)
                    if len(done) % 50 == 0:
                        say(f"  [{ctx}/{mode}] {len(done)}/{len(harvested)} done")
                        write_report(out, results, jobs_so_far + [info], started_at)
                    if obj["result"] not in ("ok", "disabled", "skipped"):
                        say(f"  {obj['result'].upper():12} {ctx}/{mode} {obj.get('label', obj['key'])[:90]}  "
                            f"{(obj.get('error') or '').splitlines()[0][:120] if obj.get('error') else ''}")
                elif tag == "DONE":
                    finished = True
                elif tag == "EXIT":
                    exit_info = obj
                    log.write(f"EXIT {obj}"+chr(10))
            if p.poll() is not None and not q and not th.is_alive():
                break
            if current is not None and time.time() - last > args.action_timeout + 30:
                kill_tree(p)
                results.append({"key": current, "label": current.split("|", 2)[-1], "context": ctx, "mode": mode,
                                "source": current.split("|", 1)[0], "result": "hang", "dialog": "",
                                "time": round(time.time() - last, 1), "error": "worker killed by the parent"})
                done.add(current)
                current = None
            if current is None and not harvested and time.time() > boot_deadline:
                kill_tree(p)
                info["error"] = "worker did not start"
                break
            time.sleep(0.05)
        end_job(job)                    # everything the worker started and left running (WebEngine, servers ...)
        if finished:
            break
        rc = p.returncode
        if current is not None:
            results.append({"key": current, "label": current.split("|", 2)[-1], "context": ctx, "mode": mode,
                            "source": current.split("|", 1)[0], "result": "crash", "dialog": "", "time": 0,
                            "error": f"worker exited with code {rc} during the action"
                            + (f"; exit called: {exit_info['code']} " + exit_info['stack'] if exit_info else "")})
            done.add(current)
            say(f"  CRASH        {ctx}/{mode} {current[:100]} (exit {rc})")
        if not harvested:
            boot_failures = info.get("boot_failures", 0) + 1
            info["boot_failures"] = boot_failures
            if boot_failures >= 5:
                info["error"] = f"worker failed before harvesting (exit {rc}), {boot_failures} times"
                break
            say(f"[{ctx}/{mode}] worker crashed while starting (exit {rc}): trying again")
            continue
        if set(harvested) <= done:
            break
        info["restarts"] += 1
        say(f"[{ctx}/{mode}] restarting the worker (exit {rc}), {len(done)}/{len(harvested)} done")
    log.close()
    seen_keys.update(harvested)
    return info


def say(*a):
    print(*a, flush=True)


def write_report(out: Path, results: list, jobs: list, started: float) -> dict:
    from collections import Counter
    counts = Counter(r["result"] for r in results)
    (out / "crawl_results.json").write_text(json.dumps({"jobs": jobs, "counts": counts, "results": results},
                                                       indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    lines = ["# Action crawler report", "",
             f"Run: {time.strftime('%Y-%m-%d %H:%M')}, {time.time() - started:.0f} s. "
             f"Results: " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())), "",
             "| Context / layout | Scope | Entries harvested | Worker restarts |", "|---|---|---|---|"]
    for j in jobs:
        lines.append(f"| {j['context']} / {j['mode']} | {j['scope']} | {j['harvested']} | {j['restarts']}"
                     f"{' (' + j['error'] + ')' if j.get('error') else ''} |")
    order = {"crash": 0, "hang": 1, "exception": 2, "modal-left": 3, "unresponsive": 4, "ok": 5, "skipped": 6,
             "disabled": 7, "stale": 8}
    lines += ["", "| Action | Context | Result | Dialog | Time (s) | Error |", "|---|---|---|---|---|---|"]

    def cell(s):
        return str(s or "").replace("|", "\\|").replace("\n", " ")[:200]
    for r in sorted(results, key=lambda r: (order.get(r["result"], 9), r.get("label", ""))):
        err = r.get("error") or ""
        if r.get("writes_outside"):
            err = (err + " WRITES OUTSIDE: " + "; ".join(r["writes_outside"][:2])).strip()
        lines.append(f"| {cell(r.get('label'))} | {r['context']}/{r['mode']} | {r['result']} | {cell(r.get('dialog'))}"
                     f" | {r.get('time', '')} | {cell(err.splitlines()[-1] if err and r['result'] in BAD else err)} |")
    a11y = {}
    for r in results:
        for d in r.get("dialogs", []) or []:
            if d.get("a11y_missing"):
                a11y.setdefault(f"{d['title']} [{d['class']}]", set()).update(d["a11y_missing"])
    if a11y:
        lines += ["", "## Dialogs with interactive controls that have no accessible name", ""]
        for k, v in sorted(a11y.items()):
            lines.append(f"* **{cell(k)}**: {', '.join(sorted(v)[:12])}{' ...' if len(v) > 12 else ''}")
    helps = [r for r in results if r.get("opened") and (r.get("label", "").startswith("Help")
                                                        or "help" in r.get("label", "").lower())]
    if helps:
        lines += ["", "## Help / documentation targets (recorded, never opened)", "",
                  "| Action | Would open | Target exists |", "|---|---|---|"]
        for r in sorted(helps, key=lambda r: r["label"]):
            for kind, target in r["opened"][:3]:
                t = str(target)
                m = re.search(r"([A-Za-z]:[\\/][^\"'|]+?\.(chm|html?|pdf|md))", t, re.I)
                exists = "" if t.startswith("http") or not m else ("yes" if Path(m.group(1)).exists() else "NO")
                lines.append(f"| {cell(r['label'])} | {kind}: `{cell(t)[:150]}` | {exists} |")
    outside = [(r["label"], x) for r in results for x in r.get("writes_outside", [])]
    if outside:
        lines += ["", "## Files written outside the sandbox", ""] + [f"* {cell(a)}: `{b}`" for a, b in outside[:200]]
    (out / "CRAWL_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", action="store_true")
    ap.add_argument("--ctx", default="python-tk")
    ap.add_argument("--mode", default="vs")
    ap.add_argument("--scope", default="all")
    ap.add_argument("--contexts", default="")
    ap.add_argument("--modes", default="")
    ap.add_argument("--full", action="store_true", help="every entry in every context (no de-duplication)")
    ap.add_argument("--quick", action="store_true", help="python-tk / VS layout only")
    ap.add_argument("--out", default=os.environ.get("QA_OUT") or str(Path(tempfile.gettempdir()) / "radide-crawl"))
    ap.add_argument("--done-file", default="")
    ap.add_argument("--skip-file", default="")
    ap.add_argument("--action-timeout", type=float, default=25.0)
    ap.add_argument("--settle", type=float, default=0.6)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="regex: only entries whose label matches (debugging)")
    ap.add_argument("--max-restarts", type=int, default=40)
    ap.add_argument("--app-name", default="crawl")
    ap.add_argument("--builtin-editor", action="store_true",
                    help="the built-in code editor instead of Monaco (machines where QtWebEngine cannot start)")
    a = ap.parse_args()
    if a.worker:
        return worker_main(a)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if a.builtin_editor:
        os.environ["RADIDE_CRAWL_BUILTIN_EDITOR"] = "1"
    if a.quick:
        plan = [("python-tk", "vs", "all")]
    elif a.contexts or a.modes:
        ctxs = [c for c in (a.contexts or "python-tk").split(",") if c]
        modes = [m for m in (a.modes or "vs").split(",") if m]
        plan = [(c, m, "all" if (a.full or i == 0) else "specific") for i, (c, m) in
                enumerate((c, m) for c in ctxs for m in modes)]
    else:
        plan = [(c, m, "all" if a.full else s) for c, m, s in PLAN]
    started = time.time()
    results: list = []
    jobs: list = []
    seen: set = set()
    clear_test_org()
    for ctx, mode, scope in plan:
        say(f"=== {ctx} / {mode} ({scope})")
        jobs.append(run_job(ctx, mode, scope, a, out, seen, results, jobs, started))
        write_report(out, results, jobs, started)
    counts = write_report(out, results, jobs, started)
    clear_test_org()
    bad = sum(counts.get(k, 0) for k in BAD)
    for r in results:
        if r["result"] in BAD:
            print(f"FAIL {r['result']}: {r['context']}/{r['mode']} {r.get('label')}")
    total = len(results)
    print(f"{total - bad}/{total} actions passed (ok {counts.get('ok', 0)}, disabled {counts.get('disabled', 0)}, "
          f"skipped {counts.get('skipped', 0)}, exception {counts.get('exception', 0)}, hang {counts.get('hang', 0)}, "
          f"crash {counts.get('crash', 0)}, modal-left {counts.get('modal-left', 0)}); report: {out / 'CRAWL_REPORT.md'}")
    return bad


if __name__ == "__main__":
    sys.exit(main())
