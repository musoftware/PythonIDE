"""Tools > Options > AI (docs/CONTRACTS.md 9.1): every AI provider with its status, install /
sign-in help, API keys, base URLs, models, a Test button, and the default provider per purpose.
Also Tools > AI Settings... which opens the Options dialog on this page."""
from __future__ import annotations

import subprocess
import sys
import threading

from PyQt6.QtCore import QObject, QProcess, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFormLayout, QGridLayout, QGroupBox,
                             QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QPlainTextEdit,
                             QPushButton, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)

from .. import ai
from .. import theme as T

KIND_LABEL = {"cli": "CLI (account)", "local": "Local", "api": "API key", "web": "Web chat"}
PURPOSE_LABEL = {"chat": "Chat", "complete": "Inline completion", "edit": "Inline edit (Ctrl+I)",
                 "agent": "Agents", "commit": "Commit messages"}
AUTO = "(automatic - best free option)"


class _Detector(QObject):
    """Runs provider detection off the UI thread."""
    done = pyqtSignal(str, bool, str)

    def run(self, provs):
        def work():
            for p in provs:
                try:
                    ok, why = p.available()
                except Exception as e:  # noqa: BLE001
                    ok, why = False, str(e)
                self.done.emit(p.id, ok, why)
        threading.Thread(target=work, name="ai-detect", daemon=True).start()


class AIPage(QWidget):
    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win = win
        self.provs = [p for p in ai.providers()]
        self.status: dict[str, tuple[bool, str]] = {}
        self.edits: dict[str, dict] = {}          # provider id -> pending changes
        self.test_job = None
        self.proc: QProcess | None = None

        intro = QLabel("<b>Free AI without API keys:</b> sign in once to a CLI agent with your own account "
                       "(Claude Code, Gemini CLI, Codex, Copilot, Qwen Code, opencode), or run local models with "
                       "Ollama / LM Studio. API keys are optional. Web chats are under View > AI Web Chats.")
        intro.setWordWrap(True)
        T.role(intro, "banner")

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Provider", "Kind", "Status"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for p in self.provs:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(p.name))
            self.table.setItem(r, 1, QTableWidgetItem(KIND_LABEL.get(p.kind, p.kind)))
            self.table.setItem(r, 2, QTableWidgetItem("checking..."))
            self.table.item(r, 0).setData(Qt.ItemDataRole.UserRole, p.id)
        self.table.currentCellChanged.connect(lambda r, *_: self._select(r))

        # ---- details of the selected provider
        self.box = QGroupBox("Provider")
        dl = QVBoxLayout(self.box)
        self.desc = QLabel()
        self.desc.setWordWrap(True)
        self.desc.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.state = QLabel()
        self.state.setWordWrap(True)
        self.state.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        dl.addWidget(self.desc)
        dl.addWidget(self.state)
        form = QFormLayout()
        self.f_enabled = QCheckBox("Use this provider (automatic defaults, pickers)")
        self.f_key = QLineEdit()
        self.f_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.f_key.setPlaceholderText("paste the API key (stored in " +
                                      ("Windows Credential Manager" if ai.secret_backend() == "keyring"
                                       else "the IDE settings - unencrypted") + ")")
        self.f_show = QCheckBox("show")
        self.f_show.toggled.connect(lambda on: self.f_key.setEchoMode(
            QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        self.f_forget = QPushButton("Remove key")
        self.f_forget.clicked.connect(self._forget_key)
        keyrow = QHBoxLayout()
        keyrow.addWidget(self.f_key, 1)
        keyrow.addWidget(self.f_show)
        keyrow.addWidget(self.f_forget)
        self.keyrow = QWidget()
        self.keyrow.setLayout(keyrow)
        keyrow.setContentsMargins(0, 0, 0, 0)
        self.f_url = QLineEdit()
        self.f_path = QLineEdit()
        self.f_path.setPlaceholderText("(found on PATH)")
        self.f_model = QComboBox()
        self.f_model.setEditable(True)
        self.f_model.setMinimumContentsLength(24)
        self.f_think = QCheckBox("Let thinking models think (slower, Ollama 'think')")
        form.addRow(self.f_enabled)
        form.addRow("API key:", self.keyrow)
        form.addRow("Base URL:", self.f_url)
        form.addRow("Program:", self.f_path)
        form.addRow("Model:", self.f_model)
        form.addRow(self.f_think)
        self.form = form
        dl.addLayout(form)
        btns = QHBoxLayout()
        self.b_test = QPushButton("Test")
        self.b_test.setToolTip("Send a tiny prompt and show the answer")
        self.b_install = QPushButton("Install with npm")
        self.b_login = QPushButton("Sign in...")
        self.b_login.setToolTip("Opens a console window running the CLI so you can sign in with your account")
        self.b_pull = QPushButton("Pull model...")
        self.b_refresh = QPushButton("Refresh")
        for b in (self.b_test, self.b_install, self.b_login, self.b_pull, self.b_refresh):
            btns.addWidget(b)
        btns.addStretch(1)
        dl.addLayout(btns)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        self.log.setPlaceholderText("Test / install output")
        dl.addWidget(self.log)
        self.b_test.clicked.connect(self._test)
        self.b_install.clicked.connect(self._install)
        self.b_login.clicked.connect(self._login)
        self.b_pull.clicked.connect(self._pull)
        self.b_refresh.clicked.connect(self._refresh)
        for w, sig in ((self.f_key, "textEdited"), (self.f_url, "textEdited"), (self.f_path, "textEdited")):
            getattr(w, sig).connect(lambda _t, ww=w: self._remember(ww))
        self.f_model.currentTextChanged.connect(lambda _t: self._remember(self.f_model))
        self.f_enabled.toggled.connect(lambda _b: self._remember(self.f_enabled))
        self.f_think.toggled.connect(lambda _b: self._remember(self.f_think))

        # ---- defaults per purpose
        dbox = QGroupBox("Default provider for each purpose")
        g = QGridLayout(dbox)
        self.def_prov: dict[str, QComboBox] = {}
        self.def_model: dict[str, QComboBox] = {}
        s = ai.settings()
        for row, purpose in enumerate(ai.PURPOSES):
            pc = QComboBox()
            pc.addItem(AUTO, "")
            for p in self.provs:
                pc.addItem(p.name, p.id)
            mc = QComboBox()
            mc.setEditable(True)
            mc.setMinimumContentsLength(18)
            pid = str(s.value(f"ai/default/{purpose}/provider", "") or "")
            i = pc.findData(pid)
            pc.setCurrentIndex(max(0, i))
            self._fill_models(mc, pid, str(s.value(f"ai/default/{purpose}/model", "") or ""))
            pc.currentIndexChanged.connect(lambda _i, pc=pc, mc=mc: self._fill_models(mc, pc.currentData(), ""))
            g.addWidget(QLabel(PURPOSE_LABEL[purpose] + ":"), row, 0)
            g.addWidget(pc, row, 1)
            g.addWidget(mc, row, 2)
            self.def_prov[purpose], self.def_model[purpose] = pc, mc
        self.auto_note = QLabel()
        T.role(self.auto_note, "muted")
        self.auto_note.setWordWrap(True)
        g.addWidget(self.auto_note, len(ai.PURPOSES), 0, 1, 3)
        g.setColumnStretch(2, 1)

        self.table.setMinimumWidth(330)
        self.table.setMinimumHeight(300)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.table)
        split.addWidget(self.box)
        split.setStretchFactor(0, 4)
        split.setStretchFactor(1, 5)
        split.setChildrenCollapsible(False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.addWidget(intro)
        lay.addWidget(split, 1)
        lay.addWidget(dbox)

        self.detector = _Detector(self)
        self.detector.done.connect(self._on_status)
        self.detector.run(self.provs)
        ai.hub().models_changed.connect(self._on_models)
        T.changed.connect(self._recolor)
        self.table.selectRow(0)
        self._select(0)

    # ------------------------------------------------------------ table
    def current(self):
        r = self.table.currentRow()
        return self.provs[r] if 0 <= r < len(self.provs) else None

    def _row(self, pid: str) -> int:
        return next((i for i, p in enumerate(self.provs) if p.id == pid), -1)

    def _on_status(self, pid: str, ok: bool, why: str):
        try:
            self.status[pid] = (ok, why)
            r = self._row(pid)
            if r < 0:
                return
            it = self.table.item(r, 2)
            it.setText(("Ready" if ok else "Not ready") + (f" - {why}" if why else ""))
            it.setForeground(QColor(T.color("success" if ok else "muted")))
            it.setToolTip(why)
            self.table.item(r, 0).setToolTip(f"{self.provs[r].name} - model: {self.provs[r].default_model or '-'}")
            cur = self.current()
            if cur is not None and cur.id == pid:
                self._show_state(cur)
            if len(self.status) == len(self.provs):
                self._update_auto_note()
        except RuntimeError:            # the dialog was closed
            pass

    def _recolor(self, *_):
        for pid, (ok, _w) in self.status.items():
            r = self._row(pid)
            if r >= 0:
                self.table.item(r, 2).setForeground(QColor(T.color("success" if ok else "muted")))

    def _update_auto_note(self):
        parts = []
        for purpose in ai.PURPOSES:
            try:
                p, m = ai.default(purpose)
                parts.append(f"{PURPOSE_LABEL[purpose]}: {p.name}{' / ' + m if m else ''}")
            except Exception:  # noqa: BLE001
                pass
        self.auto_note.setText("Now used: " + ";  ".join(parts))

    def _on_models(self, pid: str):
        try:
            cur = self.current()
            if cur is not None and cur.id == pid:
                text = self.f_model.currentText()
                self._fill_model_combo(self.f_model, cur, text)
            for purpose, pc in self.def_prov.items():
                if pc.currentData() == pid:
                    self._fill_models(self.def_model[purpose], pid, self.def_model[purpose].currentText())
        except RuntimeError:
            pass

    # ------------------------------------------------------------ details
    def _select(self, r: int):
        if not (0 <= r < len(self.provs)):
            return
        p = self.provs[r]
        self._loading = True
        pend = self.edits.get(p.id, {})
        self.box.setTitle(p.name)
        bits = [p.description or ""]
        if getattr(p, "homepage", ""):
            bits.append(f"<a href='{p.homepage}'>{p.homepage}</a>")
        key_url = getattr(p, "key_url", "")
        if key_url:
            bits.append(f"Get a key: <a href='{key_url}'>{key_url}</a>")
        if p.install_hint and p.kind != "cli":
            bits.append(p.install_hint)
        self.desc.setText("<br>".join(b for b in bits if b))
        self.desc.setOpenExternalLinks(True)
        self._show_state(p)
        has_key = p.kind == "api" or p.id == "openai-compatible"
        has_url = hasattr(p, "base_url")
        self._row_visible(self.keyrow, has_key)
        self._row_visible(self.f_url, has_url)
        self._row_visible(self.f_path, p.kind == "cli")
        self._row_visible(self.f_think, p.id == "ollama")
        self.f_enabled.setChecked(pend.get("enabled", p.enabled()))
        self.f_key.setText(pend.get("key", "") if "key" in pend else "")
        stored = has_key and self._has_key(p)
        self.f_forget.setEnabled(stored)
        self.f_key.setPlaceholderText(("a key is stored - type a new one to replace it"
                                       if stored else "paste the API key") +
                                      (" - stored in Windows Credential Manager" if ai.secret_backend() == "keyring"
                                       else " - stored UNENCRYPTED in the IDE settings (pip install keyring)"))
        if has_url:
            self.f_url.setText(pend.get("base_url", str(p.config("base_url", "") or "")))
            self.f_url.setPlaceholderText(getattr(p, "base_url_default", "") or p.base_url())
        self.f_path.setText(pend.get("path", str(p.config("path", "") or "")))
        self._fill_model_combo(self.f_model, p, pend.get("model", str(p.config("model", "") or "")))
        self.f_think.setChecked(pend.get("think", str(p.config("think", "false")).lower() in ("1", "true")))
        self.b_install.setVisible(p.kind == "cli" and bool(p.npm_package))
        self.b_login.setVisible(p.kind == "cli" and bool(getattr(p, "login_cmd", "")))
        self.b_pull.setVisible(p.id == "ollama")
        self._loading = False

    def _forget_key(self):
        p = self.current()
        if p is None:
            return
        ai.set_secret(p.id, "")
        self.edits.get(p.id, {}).pop("key", None)
        self.f_key.clear()
        p.invalidate()
        self.log.setPlainText(f"The API key of {p.name} was removed.")
        self._select(self.table.currentRow())
        self._refresh()

    def _has_key(self, p) -> bool:
        try:
            return bool(p.api_key())
        except Exception:  # noqa: BLE001
            return False

    def _row_visible(self, w, on: bool):
        w.setVisible(on)
        lab = self.form.labelForField(w)
        if lab is not None:
            lab.setVisible(on)

    def _show_state(self, p):
        st = self.status.get(p.id)
        if st is None:
            self.state.setText("Status: checking...")
            return
        ok, why = st
        colour = T.color("success" if ok else "error")
        txt = f"<span style='color:{colour}'><b>{'Ready' if ok else 'Not ready'}</b></span> - {why}"
        if p.kind == "cli":
            if p.npm_package:
                txt += f"<br>Install / update: <code>npm install -g {p.npm_package}</code>"
            if p.login_hint:
                txt += f"<br>Sign in: {p.login_hint}"
        self.state.setText(txt)

    def _fill_model_combo(self, combo: QComboBox, p, current: str):
        combo.blockSignals(True)
        combo.clear()
        try:
            ms = p.models()
        except Exception:  # noqa: BLE001
            ms = []
        if p.kind != "cli":
            combo.addItem("")          # "" = provider default
        combo.addItems(ms)
        combo.setCurrentText(current)
        combo.blockSignals(False)

    def _fill_models(self, combo: QComboBox, pid: str, current: str):
        combo.blockSignals(True)
        combo.clear()
        if pid:
            try:
                combo.addItem("")
                combo.addItems(ai.get(pid).models())
            except Exception:  # noqa: BLE001
                pass
        combo.setEnabled(bool(pid))
        combo.setCurrentText(current)
        combo.blockSignals(False)

    def _remember(self, w):
        if getattr(self, "_loading", False):
            return
        p = self.current()
        if p is None:
            return
        e = self.edits.setdefault(p.id, {})
        if w is self.f_key:
            e["key"] = self.f_key.text().strip()
        elif w is self.f_url:
            e["base_url"] = self.f_url.text().strip()
        elif w is self.f_path:
            e["path"] = self.f_path.text().strip().strip('"')
        elif w is self.f_model:
            e["model"] = self.f_model.currentText().strip()
        elif w is self.f_enabled:
            e["enabled"] = self.f_enabled.isChecked()
        elif w is self.f_think:
            e["think"] = self.f_think.isChecked()

    # ------------------------------------------------------------ apply
    def apply(self):
        warn = False
        for pid, e in self.edits.items():
            p = ai.get(pid)
            if e.get("key"):
                warn |= ai.set_secret(pid, e["key"]) == "settings"
            if "base_url" in e:
                p.set_config("base_url", e["base_url"])
            if "path" in e:
                p.set_config("path", e["path"])
            if "model" in e:
                p.set_config("model", "" if e["model"] == "default" and p.kind == "cli" else e["model"])
            if "enabled" in e:
                p.set_config("enabled", "true" if e["enabled"] else "false")
            if "think" in e:
                p.set_config("think", "true" if e["think"] else "false")
            p.invalidate()
            p.refresh_models()
        self.edits.clear()
        for purpose in ai.PURPOSES:
            pid = self.def_prov[purpose].currentData() or ""
            ai.set_default(purpose, pid, self.def_model[purpose].currentText().strip() if pid else "")
        if warn:
            self.log.appendPlainText("Note: keyring is not available - API keys are stored unencrypted in the "
                                     "IDE settings. Install it with: pip install keyring")
        self._select(self.table.currentRow())
        self._refresh()

    def _refresh(self):
        for p in self.provs:
            p.invalidate()
        self.status.clear()
        for r in range(self.table.rowCount()):
            self.table.item(r, 2).setText("checking...")
        self.detector.run(self.provs)

    # ------------------------------------------------------------ actions
    def _test(self):
        p = self.current()
        if p is None:
            return
        if self.test_job is not None and not self.test_job.done:
            self.test_job.cancel()
            return
        self.apply()                # test what is on screen
        self.log.clear()
        model = self.f_model.currentText().strip()
        self.log.appendPlainText(f"> {p.name}{' / ' + model if model else ''}: Reply with exactly: OK")
        self.log.appendPlainText("")
        job = p.chat([ai.Message("user", "Reply with exactly: OK")], model=model or None, max_tokens=20)
        self.test_job = job
        self.b_test.setText("Stop")

        def on_delta(s):
            try:
                self.log.insertPlainText(s)
            except RuntimeError:
                pass

        def on_end(ok, msg):
            try:
                self.b_test.setText("Test")
                self.log.appendPlainText(f"\n{'OK' if ok else 'FAILED'} in {job.elapsed():.1f} s" +
                                         ("" if ok else f"\n{msg}"))
                self.status[p.id] = (ok, "test passed" if ok else msg.splitlines()[0])
                self._on_status(p.id, *self.status[p.id])
            except RuntimeError:
                pass
        job.delta.connect(on_delta)
        job.finished.connect(lambda _t: on_end(True, ""))
        job.failed.connect(lambda m: on_end(False, m))

    def _run_process(self, program: str, args: list[str], title: str):
        if self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning:
            self.log.appendPlainText("(another command is still running)")
            return
        self.log.clear()
        self.log.appendPlainText(f"$ {title}")
        pr = QProcess(self)
        pr.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        pr.readyReadStandardOutput.connect(
            lambda: self.log.appendPlainText(bytes(pr.readAllStandardOutput()).decode("utf-8", "replace").rstrip()))

        def done(code, _status):
            try:
                self.log.appendPlainText(f"(finished, exit code {code})")
                from ..ai import providers_cli
                providers_cli.clear_cache()
                self._refresh()
            except RuntimeError:
                pass
        pr.finished.connect(done)
        pr.errorOccurred.connect(lambda _e: self.log.appendPlainText(f"cannot start {program}: {pr.errorString()}"))
        self.proc = pr
        pr.start(program, args)

    def _install(self):
        p = self.current()
        if p is None or not p.npm_package:
            return
        import shutil
        npm = shutil.which("npm.cmd") or shutil.which("npm")
        if not npm:
            self.log.setPlainText("npm was not found. Install Node.js first: winget install OpenJS.NodeJS.LTS")
            return
        self._run_process(npm, ["install", "-g", f"{p.npm_package}@latest"],
                          f"npm install -g {p.npm_package}@latest")

    def _login(self):
        p = self.current()
        cmd = getattr(p, "login_cmd", "") if p is not None else ""
        if not cmd:
            return
        folder = str(getattr(getattr(self.win, "project", None), "folder", "") or "") or None
        try:
            if sys.platform == "win32":
                subprocess.Popen(["cmd", "/k", cmd], cwd=folder, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                term = next((t for t in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm")
                             if __import__("shutil").which(t)), "")
                if not term:
                    raise OSError("no terminal emulator found")
                subprocess.Popen([term, "-e", cmd], cwd=folder)
            self.log.setPlainText(f"A console window runs `{cmd}`: sign in there, close it, then press Refresh.")
        except OSError as e:
            self.log.setPlainText(f"Run `{cmd}` in a terminal to sign in ({e}).")

    def _pull(self):
        p = self.current()
        if p is None or p.id != "ollama":
            return
        name, ok = QInputDialog.getText(self, "Pull an Ollama model",
                                        "Model name (e.g. qwen2.5-coder:7b, qwen2.5-coder:1.5b for completion, "
                                        "llama3.2, deepseek-r1:8b):", text="qwen2.5-coder:7b")
        if not ok or not name.strip():
            return
        exe = p.exe()
        if not exe:
            self.log.setPlainText("Ollama is not installed: winget install Ollama.Ollama")
            return
        self._run_process(exe, ["pull", name.strip()], f"ollama pull {name.strip()}")

    def shutdown(self):
        if self.test_job is not None and not self.test_job.done:
            self.test_job.cancel()
        try:
            ai.hub().models_changed.disconnect(self._on_models)
        except (TypeError, RuntimeError):
            pass
        try:
            T.changed.disconnect(self._recolor)
        except (TypeError, RuntimeError):
            pass


# ===================================================================== Options dialog hook
def _options_page(dialog):
    page = AIPage(dialog.win, dialog)
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setWidget(page)
    sa.setMinimumHeight(420)
    dialog.ai_page = page
    dialog.finished.connect(lambda _r: page.shutdown())
    return sa, "AI", page.apply


def show_ai_settings(win):
    from . import settings as S
    dlg = S.OptionsDialog(win)
    win._options_dialog = dlg
    from PyQt6.QtWidgets import QTabWidget
    tabs = dlg.findChild(QTabWidget)
    if tabs is not None:
        for i in range(tabs.count()):
            if tabs.tabText(i) == "AI":
                tabs.setCurrentIndex(i)
    dlg.resize(max(dlg.width(), 860), max(dlg.height(), 720))
    dlg.exec()


def install(win) -> None:
    from . import settings as S
    hooks = getattr(S, "PAGE_HOOKS", None)
    if hooks is not None and _options_page not in hooks:
        hooks.append(_options_page)
    win.ai = ai
    tools = next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Tools"), None)
    if tools is not None:
        win.a_ai_settings = tools.addAction("AI &Settings...", lambda: show_ai_settings(win))
        win.a_ai_settings.setToolTip("AI providers (CLI agents, local models, API keys) and defaults")


__all__ = ["AIPage", "show_ai_settings", "install"]
