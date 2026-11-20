"""Share > Start Collaboration Session (Live Share style real-time collaboration).

The host shares a folder (the open project's folder by default) on the local network: a WebSocket server, an
invite link with a join code (radide-collab://<ip>:<port>/<code>) and an optional password.  Guests - other
RAD IDE windows on the LAN - join with the link and get:

  * the shared file tree; double-click opens a file in a "[Live]" tab,
  * editing together: every file is a CRDT (pycrdt / Yjs) so concurrent edits converge; every participant's
    cursor and selection is shown in their colour with their name (Monaco decorations),
  * Follow mode (jump to whatever the followed participant is editing),
  * the host's Terminal and Output as a shared read-only terminal,
  * a chat panel,
  * the host can make guests read-only (one by one or all) - enforced by the host, not only in the UI,
  * a clean end: End Session (host) / Leave Session (guest).

Programmatic use (tests, macros): win.live_share.start_host(root, password=..., readonly=...) -> link,
win.live_share.join(link, password=..., name=...), win.live_share.open_shared(rel), win.live_share.end().
"""
from __future__ import annotations

import getpass
import html
import os
import re
import tempfile
import time
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QPixmap, QTextCursor
from PyQt6.QtWidgets import (QApplication, QCheckBox, QDialog, QDialogButtonBox, QDockWidget, QFileDialog,
                             QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QMessageBox,
                             QPlainTextEdit, QPushButton, QSpinBox, QSplitter, QTabWidget, QTextBrowser,
                             QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..collab import binding as B
from ..collab import protocol as P
from ..collab.session import CollabGuest, CollabHost, available

LIVE_TAG = " [Live]"


def _settings(win):
    return getattr(win, "settings", None)


def _tr(text: str) -> str:
    """Participant rows are user content (not auto-translated); only their fixed words are."""
    try:
        from .. import i18n
        return i18n.tr(text)
    except Exception:  # noqa: BLE001
        return text


def _swatch(color: str) -> QIcon:
    pm = QPixmap(12, 12)
    pm.fill(QColor(color))
    return QIcon(pm)


# ============================================================================ dialogs
class StartDialog(QDialog):
    def __init__(self, win, root: str, name: str):
        super().__init__(win)
        self.setWindowTitle("Start Collaboration Session")
        f = QFormLayout(self)
        self.name = QLineEdit(name)
        self.root = QLineEdit(root)
        browse = QToolButton(text="...")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.root, 1)
        row.addWidget(browse)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("optional")
        self.port = QSpinBox()
        self.port.setRange(1024, 65535)
        self.port.setValue(P.DEFAULT_PORT)
        self.readonly = QCheckBox("Guests join read-only")
        f.addRow("Your name:", self.name)
        f.addRow("Shared folder:", row)
        f.addRow("Password:", self.password)
        f.addRow("Port:", self.port)
        f.addRow("", self.readonly)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Start Sharing")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)
        self.resize(520, self.sizeHint().height())

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Shared folder", self.root.text())
        if d:
            self.root.setText(d)


class JoinDialog(QDialog):
    def __init__(self, win, link: str, name: str):
        super().__init__(win)
        self.setWindowTitle("Join Collaboration Session")
        f = QFormLayout(self)
        self.link = QLineEdit(link)
        self.link.setPlaceholderText("radide-collab://192.168.1.10:47820/ABC123")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("if the host set one")
        self.name = QLineEdit(name)
        f.addRow("Invite link or code:", self.link)
        f.addRow("Password:", self.password)
        f.addRow("Your name:", self.name)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Join")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)
        self.resize(520, self.sizeHint().height())


# ============================================================================ panel
class LiveSharePanel(QWidget):
    def __init__(self, ctl: "LiveShare"):
        super().__init__()
        self.ctl = ctl
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)
        self.status = QLabel("Not in a collaboration session")
        self.status.setWordWrap(True)
        f = self.status.font()
        f.setBold(True)
        self.status.setFont(f)
        lay.addWidget(self.status)
        row = QHBoxLayout()
        self.link = QLineEdit()
        self.link.setReadOnly(True)
        self.link.setPlaceholderText("Invite link")
        self.copy = QPushButton("Copy Link")
        self.copy.clicked.connect(ctl.copy_link)
        row.addWidget(self.link, 1)
        row.addWidget(self.copy)
        lay.addLayout(row)
        row = QHBoxLayout()
        self.b_start = QPushButton("Start Session...")
        self.b_start.clicked.connect(ctl.start_dialog)
        self.b_join = QPushButton("Join...")
        self.b_join.clicked.connect(ctl.join_dialog)
        self.b_end = QPushButton("End Session")
        self.b_end.clicked.connect(ctl.end)
        self.ro_all = QCheckBox("Guests read-only")
        self.ro_all.toggled.connect(lambda on: ctl.set_all_readonly(on))
        for w in (self.b_start, self.b_join, self.b_end):
            row.addWidget(w)
        row.addStretch(1)
        row.addWidget(self.ro_all)
        lay.addLayout(row)

        split = QSplitter(Qt.Orientation.Vertical)
        self.people = QTreeWidget()
        self.people.setHeaderLabels(["Participant", "Role", "File", "Read-only"])
        self.people.setRootIsDecorated(False)
        self.people.setProperty("i18n_skip_items", True)
        self.people.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.people.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.people.customContextMenuRequested.connect(self._people_menu)
        self.people.itemChanged.connect(self._people_changed)
        self.people.itemDoubleClicked.connect(lambda it, _c: ctl.follow(it.data(0, Qt.ItemDataRole.UserRole)))
        split.addWidget(self.people)
        self.files = QTreeWidget()
        self.files.setHeaderLabels(["Shared files"])
        self.files.setProperty("i18n_skip_items", True)
        self.files.itemActivated.connect(self._file_activated)
        split.addWidget(self.files)
        self.tabs = QTabWidget()
        chat = QWidget()
        cl = QVBoxLayout(chat)
        cl.setContentsMargins(0, 0, 0, 0)
        self.chat = QTextBrowser()
        self.chat.setProperty("i18n_skip", True)
        self.chat.setOpenExternalLinks(False)
        self.chat_in = QLineEdit()
        self.chat_in.setPlaceholderText("Message...  (Enter to send)")
        self.chat_in.returnPressed.connect(self._send_chat)
        cl.addWidget(self.chat, 1)
        cl.addWidget(self.chat_in)
        self.tabs.addTab(chat, "Chat")
        self.term = QPlainTextEdit()
        self.term.setReadOnly(True)
        self.term.setProperty("i18n_skip", True)
        self.term.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.term.setMaximumBlockCount(5000)
        fnt = self.term.font()
        fnt.setFamily("Consolas")
        self.term.setFont(fnt)
        self.tabs.addTab(self.term, "Shared Terminal")
        split.addWidget(self.tabs)
        split.setSizes([120, 200, 220])
        lay.addWidget(split, 1)
        self._filling = False
        self.refresh()

    # ------------------------------------------------------------ refresh
    def refresh(self) -> None:
        s = self.ctl.session
        active = s is not None and s.active
        self.b_start.setVisible(not active)
        self.b_join.setVisible(not active)
        self.b_end.setVisible(active)
        self.b_end.setText("End Session" if active and s.is_host else "Leave Session")
        self.ro_all.setVisible(active and s.is_host)
        self.link.setText(self.ctl.link if active and s.is_host else "")
        self.link.setVisible(active and s.is_host)
        self.copy.setVisible(active and s.is_host)
        self.chat_in.setEnabled(active)
        if not active:
            self.status.setText("Not in a collaboration session")
        elif s.is_host:
            n = len(s.participants)
            self.status.setText(f"Sharing '{s.session_name}' - {n} participant(s), password protected" if s.password
                                else f"Sharing '{s.session_name}' - {n} participant(s)")
        else:
            self.status.setText(f"Joined '{s.session_name}' as {s.name} (read-only)" if s.readonly
                                else f"Joined '{s.session_name}' as {s.name}")
        self.fill_people()

    def fill_people(self) -> None:
        s = self.ctl.session
        self._filling = True
        self.people.clear()
        if s is not None and s.active:
            for p in sorted(s.participants.values(), key=lambda p: p.id):
                me = _tr(" (you)") if p.id == s.me else ""
                follow = _tr("  [following]") if self.ctl.following == p.id else ""
                it = QTreeWidgetItem([p.name + me + follow, _tr("Host" if p.host else "Guest"), p.path or "", ""])
                it.setIcon(0, _swatch(p.color))
                it.setData(0, Qt.ItemDataRole.UserRole, p.id)
                if not p.host:
                    it.setFlags(it.flags() | (Qt.ItemFlag.ItemIsUserCheckable if s.is_host else Qt.ItemFlag.NoItemFlags))
                    it.setCheckState(3, Qt.CheckState.Checked if p.readonly else Qt.CheckState.Unchecked)
                self.people.addTopLevelItem(it)
        self._filling = False

    def fill_files(self) -> None:
        s = self.ctl.session
        self.files.clear()
        if s is None:
            return
        folders: dict[str, QTreeWidgetItem] = {}
        st = self.style()
        dir_icon = st.standardIcon(st.StandardPixmap.SP_DirIcon)
        file_icon = st.standardIcon(st.StandardPixmap.SP_FileIcon)
        for rel in s.tree:
            parts = rel.split("/")
            parent = None
            for i in range(len(parts) - 1):
                key = "/".join(parts[:i + 1])
                if key not in folders:
                    it = QTreeWidgetItem([parts[i]])
                    it.setIcon(0, dir_icon)
                    (parent.addChild(it) if parent else self.files.addTopLevelItem(it))
                    folders[key] = it
                parent = folders[key]
            it = QTreeWidgetItem([parts[-1]])
            it.setIcon(0, file_icon)
            it.setData(0, Qt.ItemDataRole.UserRole, rel)
            (parent.addChild(it) if parent else self.files.addTopLevelItem(it))
        if len(s.tree) < 200:
            self.files.expandAll()

    # ------------------------------------------------------------ slots
    def _file_activated(self, it, _col=0):
        rel = it.data(0, Qt.ItemDataRole.UserRole)
        if rel:
            self.ctl.open_shared(rel)

    def _send_chat(self):
        text = self.chat_in.text()
        self.chat_in.clear()
        if self.ctl.session is not None:
            self.ctl.session.send_chat(text)

    def add_chat(self, msg: dict) -> None:
        ts = time.strftime("%H:%M", time.localtime(float(msg.get("ts", time.time()))))
        color = re.sub(r"[^#0-9a-fA-F]", "", str(msg.get("color", "#888")))
        self.chat.append(f'<span style="color:gray">{ts}</span> <b style="color:{color}">'
                         f'{html.escape(str(msg.get("name", "?")))}</b>: {html.escape(str(msg.get("text", "")))}')

    def add_term(self, text: str) -> None:
        self.term.moveCursor(QTextCursor.MoveOperation.End)
        self.term.insertPlainText(text)
        self.term.moveCursor(QTextCursor.MoveOperation.End)

    def _people_changed(self, it, col):
        if self._filling or col != 3:
            return
        s = self.ctl.session
        if s is not None and s.is_host:
            s.set_readonly(it.data(0, Qt.ItemDataRole.UserRole), it.checkState(3) == Qt.CheckState.Checked)

    def _people_menu(self, pos):
        it = self.people.itemAt(pos)
        s = self.ctl.session
        if it is None or s is None:
            return
        pid = it.data(0, Qt.ItemDataRole.UserRole)
        m = QMenu(self)
        if pid != s.me:
            if self.ctl.following == pid:
                m.addAction("Stop Following", lambda: self.ctl.follow(None))
            else:
                m.addAction("Follow", lambda: self.ctl.follow(pid))
        p = s.participant(pid)
        if s.is_host and p is not None and not p.host:
            m.addAction("Make Editor" if p.readonly else "Make Read-only",
                        lambda: s.set_readonly(pid, not p.readonly))
            m.addAction("Remove from Session", lambda: s.kick(pid))
        if not m.isEmpty():
            m.exec(self.people.viewport().mapToGlobal(pos))


# ============================================================================ controller
class LiveShare(QObject):
    sessionChanged = pyqtSignal()

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.session = None
        self.link = ""
        self.bindings: dict[str, object] = {}        # rel path -> binding
        self.views: dict[str, QWidget] = {}          # guest: rel path -> ModuleView of a shared file
        self.following: int | None = None
        self._reveal: dict[str, int] = {}            # rel -> code point to reveal when the editor appears
        self._term_buf = ""
        self._term_timer = QTimer(self)
        self._term_timer.setSingleShot(True)
        self._term_timer.setInterval(120)
        self._term_timer.timeout.connect(self._flush_term)
        self._mirror: Path | None = None
        self.last_error = ""
        self.panel = LiveSharePanel(self)
        self.dock = QDockWidget("Live Share", win)
        self.dock.setObjectName("LiveShare")
        self.dock.setWidget(self.panel)
        win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock.hide()
        try:
            win.tabs.currentChanged.connect(lambda _i: QTimer.singleShot(0, self._scan_tabs))
        except AttributeError:
            pass

    # ------------------------------------------------------------ helpers
    def _name(self) -> str:
        st = _settings(self.win)
        name = st.value("collab/name", "") if st is not None else ""
        if not name:
            try:
                name = getpass.getuser()
            except Exception:  # noqa: BLE001
                name = "User"
        return str(name)

    def _remember(self, key: str, value) -> None:
        st = _settings(self.win)
        if st is not None:
            st.setValue(key, value)

    def _log(self, text: str) -> None:
        try:
            self.win.log(f"[Live Share] {text}")
        except Exception:  # noqa: BLE001
            pass

    def show(self) -> None:
        self.dock.show()
        self.dock.raise_()

    def _status(self, text: str) -> None:
        try:
            self.win.statusBar().showMessage(text, 6000)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------ start / join / end
    def start_dialog(self) -> None:
        if self.session is not None and self.session.active:
            self.show()
            return
        ok, why = available()
        if not ok:
            QMessageBox.warning(self.win, "Live Share", why)
            return
        proj = getattr(self.win, "project", None)
        root = str(proj.folder) if proj is not None else ""
        if not root:
            cv = self.win._current_code() if hasattr(self.win, "_current_code") else None
            root = str(Path(cv.editor.path).parent) if cv is not None and hasattr(cv.editor, "path") else os.getcwd()
        d = StartDialog(self.win, root, self._name())
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        self._remember("collab/name", d.name.text().strip())
        link = self.start_host(d.root.text(), password=d.password.text(), readonly=d.readonly.isChecked(),
                               name=d.name.text().strip(), port=d.port.value())
        if link:
            QApplication.clipboard().setText(link)
            self._status("Invite link copied to the clipboard")

    def start_host(self, root, password: str = "", readonly: bool = False, name: str = "",
                   port: int = P.DEFAULT_PORT) -> str:
        self.end()
        root = Path(root)
        if not root.is_dir():
            QMessageBox.warning(self.win, "Live Share", f"Not a folder: {root}")
            return ""
        h = CollabHost(name or self._name(), self)
        h.text_provider = self._host_text
        self._wire(h)
        h.saveRequested.connect(self._host_save)
        if not h.start(root, port=port, password=password, guests_readonly=readonly):
            return ""
        self.session = h
        self.link = h.link()
        self.panel.ro_all.blockSignals(True)
        self.panel.ro_all.setChecked(readonly)
        self.panel.ro_all.blockSignals(False)
        self._hook_terminal(True)
        self._scan_tabs()
        self.panel.fill_files()
        self.panel.term.clear()
        self._after_change()
        self._log(f"Session started - invite link: {self.link}")
        self.show()
        return self.link

    def join_dialog(self) -> None:
        if self.session is not None and self.session.active:
            self.show()
            return
        ok, why = available()
        if not ok:
            QMessageBox.warning(self.win, "Live Share", why)
            return
        clip = QApplication.clipboard().text().strip()
        d = JoinDialog(self.win, clip if clip.startswith(P.SCHEME) else "", self._name())
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        self._remember("collab/name", d.name.text().strip())
        self.join(d.link.text(), password=d.password.text(), name=d.name.text().strip())

    def join(self, link: str, password: str = "", name: str = "") -> bool:
        self.end()
        g = CollabGuest(name or self._name(), self)
        self._wire(g)
        g.joined.connect(self._on_joined)
        g.rejected.connect(self._on_rejected)
        g.docOpened.connect(self._on_doc_opened)
        g.docError.connect(lambda path, text: self._status(text or f"Cannot open {path}"))
        g.terminalText.connect(self.panel.add_term)
        g.readonlyChanged.connect(self._on_readonly)
        self.session = g
        if not g.join_link(link, password):
            self.session = None
            QMessageBox.warning(self.win, "Live Share", "Not a valid invite link")
            return False
        self._status("Joining the collaboration session...")
        return True

    def end(self) -> None:
        s = self.session
        if s is None:
            return
        s.stop()
        self._cleanup()

    def _cleanup(self) -> None:
        self._hook_terminal(False)
        for b in list(self.bindings.values()):
            try:
                b.detach()
            except Exception:  # noqa: BLE001
                pass
        self.bindings.clear()
        for rel, v in list(self.views.items()):          # guest tabs stay open as local copies
            try:
                v.editor.setReadOnly(False)
                i = self.win.tabs.indexOf(v)
                if i >= 0:
                    self.win.tabs.setTabText(i, Path(rel).name + " [ended]")
            except RuntimeError:
                pass
        self.views.clear()
        self.following = None
        if self.session is not None:
            self.session.deleteLater()
        self.session = None
        self.link = ""
        self._after_change()

    def _wire(self, s) -> None:
        s.participantsChanged.connect(self._on_participants)
        s.chatReceived.connect(self.panel.add_chat)
        s.cursorChanged.connect(self._on_cursor)
        s.docRemote.connect(self._on_remote)
        s.docReset.connect(self._on_reset)
        s.treeChanged.connect(self.panel.fill_files)
        s.ended.connect(self._on_ended)
        s.message.connect(self._log)

    def _after_change(self) -> None:
        self.panel.refresh()
        self._update_actions()
        self.sessionChanged.emit()

    # ------------------------------------------------------------ session events
    def _on_joined(self) -> None:
        g = self.session
        self.panel.term.setPlainText(g.term_backlog)
        self.panel.fill_files()
        self._after_change()
        self._log(f"Joined '{g.session_name}' as {g.name}")
        self.show()

    def _on_rejected(self, reason: str) -> None:
        text = {"bad-password": "Wrong password", "bad-code": "Unknown session code",
                "unreachable": "The host cannot be reached", "bad-link": "Not a valid invite link"}.get(reason, reason)
        self._log(f"Join refused: {text}")
        self._status(f"Live Share: {text}")
        if self.session is not None and self.session is self.sender():
            self.session.stop()
            self._cleanup()
        if not os.environ.get("RADIDE_COLLAB_QUIET"):
            QTimer.singleShot(0, lambda: QMessageBox.warning(self.win, "Live Share", text))
        self.last_error = reason

    def _on_ended(self, reason: str) -> None:
        self._log(reason)
        self._status(f"Live Share: {reason}")
        sess = self.sender()
        QTimer.singleShot(0, lambda: self.session is sess and self._cleanup())

    def _on_participants(self) -> None:
        s = self.session
        if s is None:
            return
        gone = [pid for b in self.bindings.values() for pid in list(b.cursors) if pid not in s.participants]
        for pid in gone:
            for b in self.bindings.values():
                b.drop_cursor(pid)
        if self.following is not None and self.following not in s.participants:
            self.following = None
        self.panel.refresh()

    def _on_cursor(self, pid: int, path: str, a: int, h: int) -> None:
        for rel, b in list(self.bindings.items()):
            try:
                if rel == path:
                    b.set_cursor(pid, a, h)
                else:
                    b.drop_cursor(pid)
            except RuntimeError:                      # the editor was deleted
                self.bindings.pop(rel, None)
        if self.following == pid and path:
            self._go_to(path, h)
        self.panel.fill_people()

    def _on_remote(self, path: str, ops: list) -> None:
        b = self.bindings.get(path)
        if b is not None:
            try:
                b.remote(ops)
            except RuntimeError:                      # the editor was deleted (tab / project closed)
                self.bindings.pop(path, None)

    def _on_reset(self, path: str) -> None:
        b = self.bindings.get(path)
        if b is not None:
            b.restart()

    def _on_readonly(self, ro: bool) -> None:
        for v in self.views.values():
            try:
                v.editor.setReadOnly(ro)
            except RuntimeError:
                pass
        self.panel.refresh()
        self._status("Live Share: the host made you read-only" if ro else "Live Share: you can edit")

    # ------------------------------------------------------------ host: editors and files
    def _host_text(self, rel: str):
        ed = self._open_editor_for(rel)
        return ed.text() if ed is not None else None

    def _open_editor_for(self, rel: str):
        s = self.session
        if s is None or not s.is_host:
            return None
        for w in self._tab_widgets():
            ed = getattr(w, "editor", None)
            if ed is not None and hasattr(ed, "path") and P.rel_of(s.root, ed.path) == rel:
                return ed
        return None

    def _tab_widgets(self):
        tabs = getattr(self.win, "tabs", None)
        if tabs is None:
            return []
        return [tabs.widget(i) for i in range(tabs.count())]

    def _scan_tabs(self) -> None:
        """Bind the host's open editors of shared files; send our position when the current tab changes."""
        s = self.session
        if s is None or not s.active:
            return
        if s.is_host:
            for w in self._tab_widgets():
                ed = getattr(w, "editor", None)
                if ed is None or not hasattr(ed, "path"):
                    continue
                rel = P.rel_of(s.root, ed.path)
                if rel is None:
                    continue
                b = self.bindings.get(rel)
                if b is not None and b.editor is ed:
                    continue
                if b is not None:
                    b.detach()
                if s.ensure_doc(rel) is None:
                    continue
                nb = B.bind(s, rel, ed)
                if nb is not None:
                    self.bindings[rel] = nb
                    self._push_cursors_to(rel)
        cur = self.win.tabs.currentWidget() if hasattr(self.win, "tabs") else None
        for rel, b in self.bindings.items():
            if cur is not None and getattr(cur, "editor", None) is b.editor:
                sel = getattr(b, "local_sel", (0, 0))
                s.send_cursor(rel, *sel)
                if rel in self._reveal:
                    b.reveal(self._reveal.pop(rel))

    def _push_cursors_to(self, rel: str) -> None:
        s, b = self.session, self.bindings.get(rel)
        if s is None or b is None:
            return
        for p in s.participants.values():
            if p.id != s.me and p.path == rel:
                b.set_cursor(p.id, *p.sel)

    def _host_save(self, rel: str) -> None:
        s = self.session
        if s is None:
            return
        if s.save_to_disk(rel):
            ed = self._open_editor_for(rel)
            if ed is not None:
                ed.setModified(False)
            self._log(f"Saved {rel} (requested by a guest)")

    # ------------------------------------------------------------ guest: shared files
    def open_shared(self, rel: str) -> None:
        s = self.session
        if s is None or not s.active:
            return
        if s.is_host:
            p = P.safe_rel(s.root, rel)
            if p is not None and p.is_file():
                self.win.open_any_file(p)
                self._scan_tabs()
            return
        if rel in self.views:
            self._show_view(rel)
        else:
            s.open(rel)

    def _mirror_dir(self) -> Path:
        if self._mirror is None:
            code = getattr(self.session, "code", "") or "session"
            self._mirror = Path(tempfile.gettempdir()) / "radide-collab" / f"{code}-{os.getpid()}"
        return self._mirror

    def _on_doc_opened(self, rel: str) -> None:
        s = self.session
        if s is None or s.is_host:
            return
        if rel in self.views:
            self._show_view(rel)
            return
        doc = s.docs.get(rel)
        if doc is None:
            return
        path = self._mirror_dir() / rel
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(doc.value(), encoding="utf-8")
        except OSError:
            pass
        from ..app import ModuleView
        from ..languages import all_plugins, get_plugin
        ext = path.suffix.lower()
        plugin = next((p for p in all_plugins() if p.code_ext == ext), None) or get_plugin("python-tk")
        mv = ModuleView(plugin, path)
        mv.setProperty("radLiveShare", rel)
        mv.setToolTip(f"{rel} (shared by {s.session_name})")
        mv.editor.setText(doc.value())
        mv.editor.setModified(False)
        mv.editor.setReadOnly(s.readonly)
        mv.editor.contextMenuAboutToShow.connect(
            lambda m, rel=rel: m.addAction("Save on Host (Live Share)", lambda: self.save_on_host(rel)))
        self.views[rel] = mv
        nb = B.bind(s, rel, mv.editor)
        if nb is not None:
            self.bindings[rel] = nb
        self._show_view(rel)
        self._push_cursors_to(rel)

    def _show_view(self, rel: str) -> None:
        mv = self.views.get(rel)
        if mv is None:
            return
        self.win._show_tab(mv, Path(rel).name + LIVE_TAG)
        QTimer.singleShot(0, self._scan_tabs)

    def save_on_host(self, rel: str | None = None) -> None:
        s = self.session
        if s is None:
            return
        rel = rel or self._current_rel()
        if not rel:
            return
        if s.is_host:
            self._host_save(rel)
        else:
            s.save(rel)
            self._status(f"Live Share: asked the host to save {rel}")

    def _current_rel(self) -> str | None:
        cur = self.win.tabs.currentWidget() if hasattr(self.win, "tabs") else None
        for rel, b in self.bindings.items():
            if cur is not None and getattr(cur, "editor", None) is b.editor:
                return rel
        return None

    # ------------------------------------------------------------ follow mode
    def follow(self, pid) -> None:
        s = self.session
        if pid is None or s is None or pid == s.me:
            self.following = None
        else:
            self.following = int(pid)
            p = s.participant(self.following)
            if p is not None and p.path:
                self._go_to(p.path, p.sel[1])
        self.panel.fill_people()
        self._update_actions()

    def _go_to(self, rel: str, cp: int) -> None:
        b = self.bindings.get(rel)
        cur = self.win.tabs.currentWidget() if hasattr(self.win, "tabs") else None
        if b is not None and cur is not None and getattr(cur, "editor", None) is b.editor:
            b.reveal(cp)
            return
        self._reveal[rel] = cp
        self.open_shared(rel)

    # ------------------------------------------------------------ permissions
    def set_all_readonly(self, on: bool) -> None:
        s = self.session
        if s is not None and s.is_host:
            s.set_all_readonly(on)
            self.panel.refresh()
        self._update_actions()

    def copy_link(self) -> None:
        if self.link:
            QApplication.clipboard().setText(self.link)
            self._status("Invite link copied to the clipboard")

    # ------------------------------------------------------------ shared terminal (host)
    def _hook_terminal(self, on: bool) -> None:
        docs = []
        term = getattr(self.win, "terminal", None)
        if term is not None and hasattr(term, "out"):
            docs.append(term.out.document())
        out = getattr(self.win, "output", None)
        if out is not None and hasattr(out, "document"):
            docs.append(out.document())
        for d in docs:
            try:
                if on:
                    d.contentsChange.connect(self._term_changed)
                else:
                    d.contentsChange.disconnect(self._term_changed)
            except (TypeError, RuntimeError):
                pass

    def _term_changed(self, pos: int, _removed: int, added: int) -> None:
        s = self.session
        if s is None or not s.is_host or added <= 0:
            return
        doc = self.sender()
        if doc is None:
            return
        c = QTextCursor(doc)
        c.setPosition(pos)
        c.setPosition(min(pos + added, doc.characterCount() - 1), QTextCursor.MoveMode.KeepAnchor)
        text = c.selectedText().replace(" ", "\n").replace(" ", "\n")
        if text.startswith("[Live Share]") or "\n[Live Share]" in text:
            return
        self._term_buf += text
        if not self._term_timer.isActive():
            self._term_timer.start()

    def _flush_term(self) -> None:
        s, text = self.session, self._term_buf
        self._term_buf = ""
        if s is not None and s.is_host and text:
            s.send_terminal(text)
            self.panel.add_term(text)

    # ------------------------------------------------------------ menu
    def build_menu(self) -> None:
        win = self.win
        mb = win.menuBar()
        menu = next((a.menu() for a in mb.actions() if a.menu() is not None
                     and a.text().replace("&", "") == "Share"), None)
        if menu is None:
            menu = QMenu("&Share", win)
            before = next((a for a in mb.actions() if a.text().replace("&", "") in ("Window", "Help")), None)
            if before is not None:
                mb.insertMenu(before, menu)
            else:
                mb.addMenu(menu)
        self.menu = menu
        if menu.actions():
            menu.addSeparator()

        def act(text, slot, shortcut=None, checkable=False):
            a = QAction(text, win)
            if shortcut:
                a.setShortcut(shortcut)
            a.setCheckable(checkable)
            a.triggered.connect(slot)
            menu.addAction(a)
            return a
        self.a_start = act("Start &Collaboration Session...", self.start_dialog)
        self.a_join = act("&Join Collaboration Session...", self.join_dialog)
        menu.addSeparator()
        self.a_copy = act("Copy &Invite Link", self.copy_link)
        self.a_ro = act("Guests &Read-only", lambda on: self.set_all_readonly(on), checkable=True)
        self.follow_menu = menu.addMenu("&Follow Participant")
        self.follow_menu.aboutToShow.connect(self._fill_follow_menu)
        self.a_save = act("Save Shared File on &Host", lambda: self.save_on_host())
        self.a_window = act("Live Share &Window", self.show)
        menu.addSeparator()
        self.a_end = act("&End Collaboration Session", self.end)
        win.a_live_share_start, win.a_live_share_join = self.a_start, self.a_join
        self._update_actions()

    def _fill_follow_menu(self) -> None:
        m = self.follow_menu
        m.clear()
        s = self.session
        if s is None or not s.active:
            m.addAction("(no session)").setEnabled(False)
            return
        a = m.addAction("Nobody", lambda: self.follow(None))
        a.setCheckable(True)
        a.setChecked(self.following is None)
        for p in s.participants.values():
            if p.id == s.me:
                continue
            a = m.addAction(_swatch(p.color), p.name, lambda pid=p.id: self.follow(pid))
            a.setCheckable(True)
            a.setChecked(self.following == p.id)

    def _update_actions(self) -> None:
        if not hasattr(self, "a_start"):
            return
        s = self.session
        active = s is not None and s.active
        host = active and s.is_host
        self.a_start.setEnabled(not active)
        self.a_join.setEnabled(not active)
        self.a_copy.setEnabled(host)
        self.a_ro.setEnabled(host)
        self.a_ro.blockSignals(True)
        self.a_ro.setChecked(bool(host and s.guests_readonly))
        self.a_ro.blockSignals(False)
        self.a_save.setEnabled(active)
        self.follow_menu.setEnabled(active)
        self.a_end.setEnabled(active)
        self.a_end.setText("&End Collaboration Session" if host or not active else "&Leave Collaboration Session")


# ============================================================================ install
def install(win) -> None:
    B.register_channel()
    ctl = LiveShare(win)
    win.live_share = ctl
    win.dock_live_share = ctl.dock
    ctl.build_menu()
    try:
        from . import workbench
        workbench.register_view("liveshare", "Live Share", icon="globe", factory=lambda w: w.dock_live_share,
                                modes=("vscode", "agent"), area="side", order=88,
                                tooltip="Live Share - real-time collaboration")
    except Exception:  # noqa: BLE001 - the layouts feature is optional
        pass
    orig_close = win.closeEvent

    def close_event(e):
        orig_close(e)
        if e.isAccepted():
            try:
                ctl.end()
            except Exception:  # noqa: BLE001
                pass
    win.closeEvent = close_event
