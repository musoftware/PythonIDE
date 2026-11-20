"""The full Git client (Visual Studio "Git" menu + Git Changes window).

Extends the Git Changes panel of git_panel.py - it never replaces it:
  * Git menu: Fetch / Pull / Push / Sync with a progress bar and plain-language explanations of
    authentication and network errors, New Branch, Manage Branches, Merge, Rebase, Continue / Abort,
    Stash, History graph, Blame, Compare with commit, Tags, Cherry-pick / Revert / Reset (graph menu),
    Amend (checkbox next to Commit), Undo last commit, .gitignore editor, Git settings, GitHub (gh).
  * new tabs beside Diff / History: Graph (commit graph with branch lanes), Branches (local + remote,
    ahead / behind, track), Stashes, Tags, GitHub (pull requests, issues, create / checkout a PR).
  * a banner while a merge / rebase / cherry-pick / revert is in progress with Resolve / Continue / Abort.
  * a 3-way merge conflict resolver: Incoming (theirs) | Base | Current (ours) panes, take left / right /
    both / base per conflict, an editable Result, Accept = write the file and mark it resolved (git add).
  * Blame: a blame window with the author / date / commit beside every line, and inline blame
    annotations at the end of the lines in the code editor (Monaco).
  * the branch picker in the status bar (click it: switch / new branch, like Visual Studio).
Logic lives in radide/git_ops.py (tested without a window)."""
from __future__ import annotations

import re
import subprocess
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QPointF, QProcess, QProcessEnvironment, QRectF, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (QAction, QBrush, QColor, QDesktopServices, QFont, QKeySequence, QPainter, QPen,
                         QTextCursor, QTextFormat)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
                             QSplitter, QStyledItemDelegate, QTextEdit, QToolButton, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

from .. import git_ops as go
from .. import theme

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
LANE_COLORS = ["#2F72D6", "#D13438", "#2E9E4F", "#C27C0E", "#8E44AD", "#0F9DB3", "#C2185B", "#6D8B00"]
ROW_H = 22
LANE_W = 14


def clean(text: str) -> str:
    return ANSI.sub("", text or "").strip()


class Busy:
    def __enter__(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

    def __exit__(self, *exc):
        QApplication.restoreOverrideCursor()


def _btn(text: str, tip: str, slot) -> QToolButton:
    b = QToolButton(text=text)
    b.setToolTip(tip)
    b.clicked.connect(slot)
    return b


def _ask_yes(parent, title: str, text: str) -> bool:
    return QMessageBox.question(parent, title, text) == QMessageBox.StandardButton.Yes


# ===================================================================== commit graph
class GraphDelegate(QStyledItemDelegate):
    """Paints the lanes of one GraphRow in column 0."""

    def paint(self, painter: QPainter, option, index):
        row = index.data(Qt.ItemDataRole.UserRole)
        super().paint(painter, option, index)
        if not isinstance(row, go.GraphRow):
            return
        r = option.rect
        top, bottom, mid = r.top(), r.bottom() + 1, r.center().y()

        def x(i):
            return r.left() + 6 + i * LANE_W + LANE_W / 2

        def pen(i):
            p = QPen(QColor(LANE_COLORS[i % len(LANE_COLORS)]), 2)
            p.setCapStyle(Qt.PenCapStyle.RoundCap)
            return p
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        sha = row.commit.sha
        for i, h in enumerate(row.before):                      # lanes passing by
            if h is not None and h != sha:
                painter.setPen(pen(i))
                painter.drawLine(QPointF(x(i), top), QPointF(x(i), bottom))
        for i in row.incoming:                                  # children above -> this commit
            painter.setPen(pen(i))
            painter.drawLine(QPointF(x(i), top), QPointF(x(row.col), mid))
        for pc in row.parent_cols:                              # this commit -> parents below
            painter.setPen(pen(pc if pc != row.col else row.col))
            painter.drawLine(QPointF(x(row.col), mid), QPointF(x(pc), bottom))
        c = QColor(LANE_COLORS[row.col % len(LANE_COLORS)])
        painter.setPen(QPen(QColor(theme.color("base")), 1.5))
        painter.setBrush(QBrush(c))
        rad = 5 if len(row.commit.parents) < 2 else 6
        painter.drawEllipse(QPointF(x(row.col), mid), rad, rad)
        painter.restore()

    def sizeHint(self, option, index):
        row = index.data(Qt.ItemDataRole.UserRole)
        w = 12 + (row.width if isinstance(row, go.GraphRow) else 1) * LANE_W
        return QSize(w, ROW_H)


class GraphView(QWidget):
    PAGE = 400

    def __init__(self, ctl: "GitFull"):
        super().__init__()
        self.ctl = ctl
        self.rows: list[go.GraphRow] = []
        self.all_refs = QCheckBox("All branches")
        self.all_refs.setChecked(True)
        self.all_refs.toggled.connect(lambda _v: self.reload())
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter (message, author, commit)")
        self.filter.textChanged.connect(self._apply_filter)
        bar = QHBoxLayout()
        bar.setContentsMargins(2, 2, 2, 2)
        bar.addWidget(self.all_refs)
        bar.addWidget(self.filter, 1)
        bar.addWidget(_btn("Refresh", "Reload the history", self.reload))
        self.more = _btn("Load more", "Show older commits", self.load_more)
        bar.addWidget(self.more)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Graph", "Refs", "Message", "Author", "Date", "Commit"])
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setItemDelegateForColumn(0, GraphDelegate(self.tree))
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        self.tree.itemDoubleClicked.connect(lambda it, _c: self.ctl.show_commit(self.sha(it)))
        for col, w in ((0, 90), (1, 130), (2, 340), (3, 110), (4, 115)):
            self.tree.setColumnWidth(col, w)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(bar)
        lay.addWidget(self.tree, 1)

    def sha(self, it) -> str:
        row = it.data(0, Qt.ItemDataRole.UserRole) if it is not None else None
        return row.commit.sha if isinstance(row, go.GraphRow) else ""

    def reload(self):
        self.rows = []
        self.tree.clear()
        self.load_more()

    def load_more(self):
        g = self.ctl.gx()
        if g is None or not g.has_commits():
            return
        with Busy():
            # lanes need the whole prefix: recompute over everything loaded so far
            n = len(self.rows) + self.PAGE
            self.rows = g.graph(n=n, all_refs=self.all_refs.isChecked())
        self.more.setEnabled(len(self.rows) >= n)
        self._fill()

    def _fill(self):
        self.tree.clear()
        width = max((r.width for r in self.rows), default=1)
        self.tree.setColumnWidth(0, min(12 + width * LANE_W, 260))
        head_font = QFont()
        head_font.setBold(True)
        items = []
        for r in self.rows:
            c = r.commit
            refs = ", ".join(x.replace("HEAD -> ", "HEAD → ") for x in c.refs.split(", ") if x)
            it = QTreeWidgetItem(["", refs, c.subject, c.author, c.date, c.short])
            it.setData(0, Qt.ItemDataRole.UserRole, r)
            it.setSizeHint(0, QSize(10, ROW_H))
            it.setToolTip(2, f"{c.sha}\n{c.author}  {c.date}\n\n{c.subject}")
            if refs:
                it.setForeground(1, QBrush(QColor(theme.color("link"))))
            if "HEAD" in c.refs:
                for col in range(1, 6):
                    it.setFont(col, head_font)
            items.append(it)
        self.tree.addTopLevelItems(items)
        self._apply_filter(self.filter.text())

    def _apply_filter(self, text: str):
        t = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            hay = " ".join(it.text(c) for c in range(1, 6)).lower() + " " + self.sha(it)
            it.setHidden(bool(t) and t not in hay)

    def _menu(self, pos):
        it = self.tree.itemAt(pos)
        sha = self.sha(it)
        if not sha:
            return
        short = sha[:8]
        m = QMenu(self)
        c = self.ctl
        m.addAction("View commit details", lambda: c.show_commit(sha))
        m.addAction("Compare with working copy", lambda: c.compare_commit_worktree(sha))
        m.addSeparator()
        m.addAction(f"Checkout {short} (detached)", lambda: c.checkout_ref(sha))
        m.addAction("New branch from here...", lambda: c.new_branch(start=sha))
        m.addAction("New tag here...", lambda: c.new_tag(sha))
        m.addSeparator()
        m.addAction("Cherry-pick into the current branch", lambda: c.cherry_pick(sha))
        m.addAction("Revert (new commit that undoes it)", lambda: c.revert(sha))
        rs = m.addMenu("Reset current branch to here")
        rs.addAction("Keep changes (--mixed)", lambda: c.reset(sha, "mixed"))
        rs.addAction("Keep changes staged (--soft)", lambda: c.reset(sha, "soft"))
        rs.addAction("Delete changes (--hard)", lambda: c.reset(sha, "hard"))
        m.addSeparator()
        m.addAction("Copy commit id", lambda: QApplication.clipboard().setText(sha))
        m.exec(self.tree.viewport().mapToGlobal(pos))


# ===================================================================== branches
class BranchesView(QWidget):
    def __init__(self, ctl: "GitFull"):
        super().__init__()
        self.ctl = ctl
        c = ctl
        bar = QHBoxLayout()
        bar.setContentsMargins(2, 2, 2, 2)
        for text, tip, slot in (
                ("New...", "Create a branch (from the selected one)", lambda: c.new_branch(start=self.current())),
                ("Switch", "Checkout the selected branch (a remote branch gets a local tracking branch)",
                 self.switch),
                ("Merge into current", "Merge the selected branch into the current branch", self.merge),
                ("Rebase onto", "Rebase the current branch onto the selected branch", self.rebase),
                ("Rename...", "Rename the selected local branch", self.rename),
                ("Delete", "Delete the selected branch", self.delete),
                ("Track...", "Set the remote branch the selected local branch tracks (upstream)", self.track),
                ("Remotes...", "Add / remove remotes (GitHub, GitLab ... URLs)", c.manage_remotes),
                ("Refresh", "Reload", self.reload)):
            bar.addWidget(_btn(text, tip, slot))
        bar.addStretch(1)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Branch", "Tracking", "Ahead / behind", "Last commit", "Date"])
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 140)
        self.tree.setColumnWidth(2, 120)
        self.tree.setColumnWidth(3, 260)
        self.tree.itemDoubleClicked.connect(lambda _i, _c: self.switch())
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(bar)
        lay.addWidget(self.tree, 1)

    def reload(self):
        self.tree.clear()
        g = self.ctl.gx()
        if g is None:
            return
        bold = QFont()
        bold.setBold(True)
        local = QTreeWidgetItem(self.tree, ["Local"])
        remote = QTreeWidgetItem(self.tree, ["Remotes"])
        for top in (local, remote):
            top.setFont(0, bold)
        groups: dict[str, QTreeWidgetItem] = {}
        for b in g.branches():
            if b.remote:
                rname = b.name.split("/", 1)[0]
                parent = groups.get(rname)
                if parent is None:
                    parent = groups[rname] = QTreeWidgetItem(remote, [rname])
            else:
                parent = local
            it = QTreeWidgetItem(parent, [("✓ " if b.head else "") + b.name, b.upstream, b.track,
                                          b.subject, b.date])
            it.setData(0, Qt.ItemDataRole.UserRole, b)
            it.setToolTip(0, f"{b.name}  {b.sha}" + (f"\ntracks {b.upstream}" if b.upstream else ""))
            if b.head:
                for col in range(5):
                    it.setFont(col, bold)
            if b.track == "gone":
                it.setForeground(2, QBrush(QColor(theme.color("error"))))
        self.tree.expandAll()

    def branch(self) -> go.Branch | None:
        it = self.tree.currentItem()
        b = it.data(0, Qt.ItemDataRole.UserRole) if it is not None else None
        return b if isinstance(b, go.Branch) else None

    def current(self) -> str:
        b = self.branch()
        return b.name if b else ""

    def _need(self) -> go.Branch | None:
        b = self.branch()
        if b is None:
            QMessageBox.information(self, "Branches", "Select a branch first.")
        return b

    def switch(self):
        b = self._need()
        if b:
            self.ctl.switch_branch(b.name, b.remote)

    def merge(self):
        b = self._need()
        if b:
            self.ctl.merge(b.name)

    def rebase(self):
        b = self._need()
        if b:
            self.ctl.rebase(b.name)

    def rename(self):
        b = self._need()
        if b is None or b.remote:
            return
        new, ok = QInputDialog.getText(self, "Rename branch", f"New name for '{b.name}':", text=b.name)
        if ok and new.strip() and new.strip() != b.name:
            self.ctl.do(self.ctl.gx().rename_branch(b.name, new.strip()), "Rename branch")

    def delete(self):
        b = self._need()
        if b:
            self.ctl.delete_branch(b)

    def track(self):
        b = self._need()
        if b is None or b.remote:
            return
        g = self.ctl.gx()
        remotes = [x.name for x in g.branches() if x.remote]
        if not remotes:
            QMessageBox.information(self, "Track", "There are no remote branches. Fetch first or add a remote.")
            return
        choices = ["(none - stop tracking)"] + remotes
        guess = next((i for i, r in enumerate(choices) if r.endswith("/" + b.name)), 0)
        up, ok = QInputDialog.getItem(self, "Track remote branch", f"'{b.name}' tracks:", choices, guess, False)
        if ok:
            if up.startswith("("):
                self.ctl.do(g.unset_upstream(b.name), "Unset upstream")
            else:
                self.ctl.do(g.set_upstream(b.name, up), "Set upstream")

    def _menu(self, pos):
        b = self.branch()
        if b is None:
            return
        m = QMenu(self)
        m.addAction("Switch to this branch", self.switch)
        m.addAction("New branch from here...", lambda: self.ctl.new_branch(start=b.name))
        m.addAction("Merge into current branch", self.merge)
        m.addAction("Rebase current branch onto this", self.rebase)
        m.addAction("Compare with current (diff)", lambda: self.ctl.show_text(
            f"Diff HEAD...{b.name}", self.ctl.gx().run("diff", f"HEAD...{b.name}")[1]))
        if not b.remote:
            m.addSeparator()
            m.addAction("Rename...", self.rename)
            m.addAction("Track remote branch...", self.track)
            m.addAction("Push (publish)", lambda: self.ctl.push(branch=b.name))
        m.addSeparator()
        m.addAction("Delete", self.delete)
        m.exec(self.tree.viewport().mapToGlobal(pos))


# ===================================================================== stashes / tags
class StashView(QWidget):
    def __init__(self, ctl: "GitFull"):
        super().__init__()
        self.ctl = ctl
        bar = QHBoxLayout()
        bar.setContentsMargins(2, 2, 2, 2)
        for text, tip, slot in (("Stash All...", "Save every change (also new files) and clean the folder",
                                 ctl.stash_save),
                                ("Apply", "Apply the selected stash and keep it", lambda: self._act("apply")),
                                ("Pop", "Apply the selected stash and remove it", lambda: self._act("pop")),
                                ("Drop", "Delete the selected stash", lambda: self._act("drop")),
                                ("Refresh", "Reload", self.reload)):
            bar.addWidget(_btn(text, tip, slot))
        bar.addStretch(1)
        self.list = QTreeWidget()
        self.list.setHeaderLabels(["Stash", "When", "Message"])
        self.list.setRootIsDecorated(False)
        self.list.setColumnWidth(0, 90)
        self.list.setColumnWidth(1, 120)
        self.list.currentItemChanged.connect(self._show)
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setFont(QFont("Consolas", 9))
        self.view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        from .git_panel import DiffHighlighter
        self._hl = DiffHighlighter(self.view.document())
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self.list)
        split.addWidget(self.view)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(bar)
        lay.addWidget(split, 1)

    def reload(self):
        self.list.clear()
        self.view.clear()
        g = self.ctl.gx()
        if g is None:
            return
        for ref, when, msg in g.stashes():
            QTreeWidgetItem(self.list, [ref, when, msg])

    def ref(self) -> str:
        it = self.list.currentItem()
        return it.text(0) if it else ""

    def _show(self, it, _prev=None):
        if it is not None and self.ctl.gx():
            self.view.setPlainText(self.ctl.gx().stash_show(it.text(0)))

    def _act(self, what: str):
        ref = self.ref()
        if not ref:
            QMessageBox.information(self, "Stash", "Select a stash first.")
            return
        g = self.ctl.gx()
        if what == "drop":
            if _ask_yes(self, "Drop stash", f"Delete {ref} for good?"):
                self.ctl.do(g.stash_drop(ref), "Drop stash")
        else:
            self.ctl.do(g.stash_apply(ref, pop=(what == "pop")), f"Stash {what}")
        self.reload()


class TagsView(QWidget):
    def __init__(self, ctl: "GitFull"):
        super().__init__()
        self.ctl = ctl
        bar = QHBoxLayout()
        bar.setContentsMargins(2, 2, 2, 2)
        for text, tip, slot in (("New Tag...", "Tag the current commit", lambda: ctl.new_tag("")),
                                ("Checkout", "Checkout the tagged commit (detached HEAD)", self.checkout),
                                ("Push", "Push the selected tag to the remote", self.push),
                                ("Push All", "git push --tags", lambda: ctl.run_net(["push", "--tags"],
                                                                                   "Push tags")),
                                ("Delete", "Delete the selected tag (locally)", self.delete),
                                ("Refresh", "Reload", self.reload)):
            bar.addWidget(_btn(text, tip, slot))
        bar.addStretch(1)
        self.list = QTreeWidget()
        self.list.setHeaderLabels(["Tag", "Commit", "Date", "Message"])
        self.list.setRootIsDecorated(False)
        self.list.setColumnWidth(0, 140)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(bar)
        lay.addWidget(self.list, 1)

    def reload(self):
        self.list.clear()
        g = self.ctl.gx()
        if g is None:
            return
        for name, commit, date, msg in g.tags():
            QTreeWidgetItem(self.list, [name, commit, date, msg])

    def tag(self) -> str:
        it = self.list.currentItem()
        if it is None:
            QMessageBox.information(self, "Tags", "Select a tag first.")
            return ""
        return it.text(0)

    def checkout(self):
        t = self.tag()
        if t:
            self.ctl.checkout_ref(t)

    def push(self):
        t = self.tag()
        g = self.ctl.gx()
        if t and g and g.remotes():
            self.ctl.run_net(["push", g.remotes()[0], t], f"Push tag {t}")

    def delete(self):
        t = self.tag()
        if t and _ask_yes(self, "Delete tag", f"Delete the tag '{t}' locally?"):
            self.ctl.do(self.ctl.gx().delete_tag(t), "Delete tag")
            g = self.ctl.gx()
            if g.remotes() and _ask_yes(self, "Delete tag", f"Also delete '{t}' on {g.remotes()[0]}?"):
                self.ctl.run_net(["push", g.remotes()[0], "--delete", f"refs/tags/{t}"], "Delete remote tag")
            self.reload()


# ===================================================================== GitHub
class _Signals(QObject):
    done = pyqtSignal(object)
    progress = pyqtSignal(int, int)


class GitHubView(QWidget):
    def __init__(self, ctl: "GitFull"):
        super().__init__()
        self.ctl = ctl
        self.sig = _Signals()
        self.sig.done.connect(lambda f: f())
        self.sig.progress.connect(self._progress)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.b_get = _btn("Download GitHub CLI", "Download the official portable gh zip from github.com/cli/cli "
                          "into %LOCALAPPDATA%\\RADIDE\\tools\\gh (no admin rights)", self.download)
        self.b_login = _btn("Sign in...", "gh auth login (opens a console window and your browser)", self.login)
        self.prog = QProgressBar()
        self.prog.setMaximumHeight(14)
        self.prog.hide()
        top = QHBoxLayout()
        top.setContentsMargins(2, 2, 2, 2)
        top.addWidget(self.info, 1)
        top.addWidget(self.prog)
        top.addWidget(self.b_get)
        top.addWidget(self.b_login)
        self.kind = QComboBox()
        self.kind.addItems(["Pull Requests", "Issues"])
        self.state = QComboBox()
        self.state.addItems(["open", "closed", "all"])
        self.kind.currentIndexChanged.connect(lambda _i: self.reload())
        self.state.currentIndexChanged.connect(lambda _i: self.reload())
        bar = QHBoxLayout()
        bar.setContentsMargins(2, 0, 2, 2)
        bar.addWidget(self.kind)
        bar.addWidget(self.state)
        for text, tip, slot in (("Refresh", "Reload from GitHub", self.reload),
                                ("Create PR...", "Create a pull request for the current branch", self.create_pr),
                                ("Checkout PR", "Checkout the selected pull request locally (gh pr checkout)",
                                 self.checkout),
                                ("Open in Browser", "Open the selected item on github.com", self.open_web)):
            bar.addWidget(_btn(text, tip, slot))
        bar.addStretch(1)
        self.list = QTreeWidget()
        self.list.setHeaderLabels(["#", "Title", "Author", "Branch / Labels", "State"])
        self.list.setRootIsDecorated(False)
        self.list.setColumnWidth(0, 50)
        self.list.setColumnWidth(1, 330)
        self.list.itemDoubleClicked.connect(lambda _i, _c: self.open_web())
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(top)
        lay.addLayout(bar)
        lay.addWidget(self.list, 1)

    def gh(self) -> go.GitHub | None:
        g = self.ctl.gx()
        return go.GitHub(g.toplevel() or g.folder) if g else None

    def _bg(self, work, done):
        """Run work() in a thread, done(result) on the UI thread."""
        def target():
            try:
                res = work()
            except Exception as e:  # noqa: BLE001
                res = e
            self.sig.done.emit(lambda: done(res))
        threading.Thread(target=target, daemon=True).start()

    def update_info(self):
        exe = go.find_gh()
        self.b_get.setVisible(not exe)
        self.b_login.setVisible(bool(exe))
        if not exe:
            self.info.setText("The GitHub CLI (gh) is not installed. Download it (official open-source zip, "
                              "about 12 MB) to list and create pull requests and issues from the IDE.")
            return False
        gh = self.gh()
        if gh is None:
            self.info.setText("Open a project in a git repository.")
            return False
        self.info.setText(f"gh: {exe} - checking sign-in...")
        self._bg(gh.auth_status, lambda r: self.info.setText(
            f"gh: {exe}\n" + ("Signed in. " + (r[1].splitlines()[1].strip() if len(r[1].splitlines()) > 1 else "")
                             if isinstance(r, tuple) and r[0] else
                             "Not signed in - click 'Sign in...' (gh auth login).")))
        return True

    def reload(self):
        self.list.clear()
        if not self.update_info():
            return
        gh = self.gh()
        kind = self.kind.currentIndex()
        state = self.state.currentText()
        self.list.addTopLevelItem(QTreeWidgetItem(["", "Loading..."]))
        self._bg(lambda: gh.prs(state) if kind == 0 else gh.issues(state), lambda r: self._fill(r, kind))

    def _fill(self, res, kind):
        self.list.clear()
        if isinstance(res, Exception):
            res = ([], str(res))
        items, err = res
        if err:
            hint = go.explain_gh_error(err)
            QTreeWidgetItem(self.list, ["", (hint or err.splitlines()[0] if err else "error")])
            self.ctl.win.log(f"[github] {err}")
            return
        for d in items:
            author = (d.get("author") or {}).get("login", "")
            extra = (f"{d.get('headRefName', '')} → {d.get('baseRefName', '')}" if kind == 0 else
                     ", ".join(l.get("name", "") for l in d.get("labels", [])))
            st = d.get("state", "") + (" (draft)" if d.get("isDraft") else "")
            it = QTreeWidgetItem(self.list, [str(d.get("number", "")), d.get("title", ""), author, extra, st])
            it.setData(0, Qt.ItemDataRole.UserRole, d)
        if not items:
            QTreeWidgetItem(self.list, ["", "(none)"])

    def selected(self) -> dict | None:
        it = self.list.currentItem()
        d = it.data(0, Qt.ItemDataRole.UserRole) if it else None
        return d if isinstance(d, dict) else None

    def open_web(self):
        d = self.selected()
        if d and d.get("url"):
            QDesktopServices.openUrl(QUrl(d["url"]))

    def checkout(self):
        d = self.selected()
        if not d or self.kind.currentIndex() != 0:
            QMessageBox.information(self, "GitHub", "Select a pull request first.")
            return
        gh = self.gh()
        with Busy():
            code, text = gh.checkout_pr(int(d["number"]))
        self.ctl.report(code, text, f"Checkout PR #{d['number']}", gh=True)
        self.ctl.refresh_all()

    def create_pr(self):
        g = self.ctl.gx()
        gh = self.gh()
        if gh is None or not gh.exe:
            self.update_info()
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Create Pull Request")
        form = QFormLayout(dlg)
        branch = g.branch()
        title = QLineEdit(g.stdout("log", "-1", "--pretty=%s").strip())
        base = QComboBox()
        base.setEditable(True)
        locals_ = [b.name for b in g.branches() if not b.remote and b.name != branch]
        base.addItems(sorted(locals_, key=lambda n: (n not in ("main", "master", "develop"), n)))
        body = QPlainTextEdit()
        body.setPlaceholderText("Describe the change...")
        draft = QCheckBox("Draft")
        form.addRow("Branch:", QLabel(branch))
        form.addRow("Into (base):", base)
        form.addRow("Title:", title)
        form.addRow("Description:", body)
        form.addRow("", draft)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)
        dlg.resize(560, 380)
        if dlg.exec() != QDialog.DialogCode.Accepted or not title.text().strip():
            return
        if not g.upstream() and _ask_yes(self, "Create PR", f"'{branch}' is not on the remote yet. Push it first?"):
            self.ctl.push(branch=branch, confirm=False,
                          after=lambda ok: ok and self._create(gh, title.text(), body.toPlainText(),
                                                               base.currentText(), draft.isChecked()))
            return
        self._create(gh, title.text(), body.toPlainText(), base.currentText(), draft.isChecked())

    def _create(self, gh, title, body, base, draft):
        with Busy():
            code, text = gh.create_pr(title.strip(), body, base.strip(), draft=draft)
        if self.ctl.report(code, text, "Create pull request", gh=True):
            url = next((l for l in text.splitlines() if l.startswith("https://")), "")
            if url and _ask_yes(self, "Pull request created", f"{url}\n\nOpen it in the browser?"):
                QDesktopServices.openUrl(QUrl(url))
        self.reload()

    def login(self):
        exe = go.find_gh()
        if not exe:
            return
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        try:
            subprocess.Popen([exe, "auth", "login", "--web", "--git-protocol", "https"], creationflags=flags)
        except OSError as e:
            QMessageBox.warning(self, "GitHub", str(e))
            return
        QMessageBox.information(self, "GitHub", "A console window opened: follow its steps (it shows a code and "
                                "opens github.com in your browser). Click Refresh here when you are done.")

    def download(self):
        if not _ask_yes(self, "GitHub CLI", "Download the official GitHub CLI (open source, MIT licence) from\n"
                        "https://github.com/cli/cli/releases\ninto " + str(go.tools_dir() / "gh") + " ?"):
            return
        self.b_get.setEnabled(False)
        self.prog.show()
        self.prog.setRange(0, 0)

        def work():
            return go.download_gh(progress=lambda d, t: self.sig.progress.emit(d, t))

        def done(res):
            self.prog.hide()
            self.b_get.setEnabled(True)
            if isinstance(res, Exception):
                QMessageBox.warning(self, "GitHub CLI", f"Download failed:\n{res}")
                return
            self.ctl.win.log(f"[github] gh installed: {res}")
            self.reload()
        self._bg(work, done)

    def _progress(self, done: int, total: int):
        if total:
            self.prog.setRange(0, total)
            self.prog.setValue(done)


# ===================================================================== 3-way merge resolver
class MergeResolver(QDialog):
    """Incoming (theirs) | Base | Current (ours) on top, the editable Result below."""

    def __init__(self, parent, git: go.GitX, path: str):
        super().__init__(parent)
        self.git, self.path = git, path
        self.setWindowTitle(f"Merge - {path}")
        self.segs, self.eol = go.merge_segments(git, path)
        self.conflicts = [s for s in self.segs if isinstance(s, go.Conflict)]
        self.cur = 0
        self.panes = {}
        self.ranges = {}
        top = QSplitter()
        for side, title in (("theirs", "Incoming (theirs)"), ("base", "Base (common ancestor)"),
                            ("ours", "Current (ours)")):
            w = QWidget()
            l = QVBoxLayout(w)
            l.setContentsMargins(0, 0, 0, 0)
            lab = QLabel(title)
            lab.setStyleSheet("font-weight:bold;")
            ed = QPlainTextEdit()
            ed.setReadOnly(True)
            ed.setFont(QFont("Consolas", 10))
            ed.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
            lines, ranges = go.side_text(self.segs, side)
            ed.setPlainText("\n".join(lines))
            self.panes[side], self.ranges[side] = ed, ranges
            l.addWidget(lab)
            l.addWidget(ed, 1)
            top.addWidget(w)
            if side == "base":
                self.base_box = w
        self.base_box.setVisible(False)
        self.result = QPlainTextEdit()
        self.result.setFont(QFont("Consolas", 10))
        self.result.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.result.setPlainText("\n".join(go.initial_result(self.segs)))
        self.result.textChanged.connect(self._update)
        bar = QHBoxLayout()
        self.pos = QLabel()
        bar.addWidget(_btn("▲ Prev", "Previous conflict", lambda: self.go_to(self.cur - 1)))
        bar.addWidget(_btn("▼ Next", "Next conflict", lambda: self.go_to(self.cur + 1)))
        bar.addWidget(self.pos)
        bar.addSpacing(12)
        self.b_left = _btn("Take Incoming ◀", "Use the incoming (left) version of this conflict",
                           lambda: self.take("theirs"))
        self.b_right = _btn("▶ Take Current", "Use the current (right) version of this conflict",
                            lambda: self.take("ours"))
        self.b_both = _btn("Take Both", "Current first, then incoming", lambda: self.take("both"))
        self.b_both2 = _btn("Both (incoming first)", "Incoming first, then current", lambda: self.take("both2"))
        self.b_base = _btn("Take Base", "Use the common ancestor", lambda: self.take("base"))
        for b in (self.b_left, self.b_right, self.b_both, self.b_both2, self.b_base):
            bar.addWidget(b)
        self.show_base = QCheckBox("Show base")
        self.show_base.toggled.connect(self.base_box.setVisible)
        bar.addWidget(self.show_base)
        bar.addStretch(1)
        bar.addWidget(_btn("All Incoming", "Take the incoming side for every remaining conflict",
                           lambda: self.take_all("theirs")))
        bar.addWidget(_btn("All Current", "Take the current side for every remaining conflict",
                           lambda: self.take_all("ours")))
        bar.addWidget(_btn("Reset", "Start again from the conflicts", self.reset))
        self.status = QLabel()
        theme.role(self.status, "note")
        res_lab = QLabel("Result (editable)")
        res_lab.setStyleSheet("font-weight:bold;")
        res_box = QWidget()
        rl = QVBoxLayout(res_box)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(res_lab)
        rl.addWidget(self.result, 1)
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(top)
        split.addWidget(res_box)
        split.setSizes([360, 320])
        bb = QDialogButtonBox()
        self.b_accept = bb.addButton("Accept Merge", QDialogButtonBox.ButtonRole.AcceptRole)
        self.b_accept.setToolTip("Write the result to the file and mark it resolved (git add)")
        bb.addButton(QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept_merge)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(bar)
        lay.addWidget(split, 1)
        lay.addWidget(self.status)
        lay.addWidget(bb)
        self.resize(1200, 780)
        for ed in self.panes.values():
            ed.verticalScrollBar().valueChanged.connect(self._sync_scroll)
        self._syncing = False
        self._update()
        QTimer.singleShot(0, lambda: self.go_to(0))

    # ---------------------------------------------------------------- navigation / highlight
    def _sync_scroll(self, v):
        if self._syncing:
            return
        self._syncing = True
        for ed in self.panes.values():
            if ed.verticalScrollBar().value() != v:
                ed.verticalScrollBar().setValue(v)
        self._syncing = False

    def go_to(self, k: int):
        if not self.conflicts:
            return
        self.cur = max(0, min(len(self.conflicts) - 1, k))
        self._highlight()
        for side, ed in self.panes.items():
            a, _b = self.ranges[side][self.cur]
            self._reveal(ed, a)
        blk = go.find_block(self.result.toPlainText().split("\n"), self.cur + 1)
        if blk:
            self._reveal(self.result, blk[0])
        self._update()

    @staticmethod
    def _reveal(ed: QPlainTextEdit, line: int):
        b = ed.document().findBlockByNumber(max(0, line))
        c = QTextCursor(b)
        ed.setTextCursor(c)
        ed.centerCursor()

    def _sel(self, ed, a, b, colour: QColor):
        out = []
        doc = ed.document()
        for ln in range(a, max(b, a + 1) if b > a else a + 1):
            blk = doc.findBlockByNumber(ln)
            if not blk.isValid():
                break
            s = QTextEdit.ExtraSelection()
            s.format.setBackground(colour)
            s.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            s.cursor = QTextCursor(blk)
            out.append(s)
        return out

    def _highlight(self):
        hues = {"theirs": QColor(47, 114, 214), "base": QColor(128, 128, 128), "ours": QColor(46, 158, 79)}
        for side, ed in self.panes.items():
            sels = []
            for k, (a, b) in enumerate(self.ranges[side]):
                c = QColor(hues[side])
                c.setAlpha(110 if k == self.cur else 45)
                sels += self._sel(ed, a, b, c)
            ed.setExtraSelections(sels)
        lines = self.result.toPlainText().split("\n")
        sels = []
        for k in range(len(self.conflicts)):
            blk = go.find_block(lines, k + 1)
            if blk:
                c = QColor(211, 84, 0)
                c.setAlpha(110 if k == self.cur else 50)
                sels += self._sel(self.result, blk[0], blk[1], c)
        self.result.setExtraSelections(sels)

    def _update(self):
        text = self.result.toPlainText()
        left = go.remaining_conflicts(text)
        n = len(self.conflicts)
        self.pos.setText(f"Conflict {self.cur + 1 if n else 0} of {n}")
        open_cur = n and go.find_block(text.split("\n"), self.cur + 1) is not None
        for b in (self.b_left, self.b_right, self.b_both, self.b_both2, self.b_base):
            b.setEnabled(bool(open_cur))
        self.status.setText(f"{left} unresolved conflict(s) left in the result." if left else
                            "All conflicts are resolved - review the result and click Accept Merge.")
        if hasattr(self, "_hl_timer"):
            self._hl_timer.start()
        else:
            self._hl_timer = QTimer(self, singleShot=True, interval=150)
            self._hl_timer.timeout.connect(self._highlight)

    # ---------------------------------------------------------------- taking sides
    def _choice(self, c: go.Conflict, how: str) -> list[str]:
        return {"theirs": c.theirs, "ours": c.ours, "base": c.base, "both": c.ours + c.theirs,
                "both2": c.theirs + c.ours}[how]

    def take(self, how: str, k: int | None = None) -> bool:
        k = self.cur if k is None else k
        lines = self.result.toPlainText().split("\n")
        blk = go.find_block(lines, k + 1)
        if blk is None:
            return False
        lines[blk[0]:blk[1]] = self._choice(self.conflicts[k], how)
        self._set_result(lines)
        nxt = next((j for j in range(len(self.conflicts))
                    if go.find_block(self.result.toPlainText().split("\n"), j + 1)), None)
        if k == self.cur and nxt is not None:
            self.go_to(nxt)
        else:
            self._highlight()
        return True

    def take_all(self, how: str):
        for k in range(len(self.conflicts)):
            self.take(how, k)
        self._highlight()

    def reset(self):
        if _ask_yes(self, "Reset", "Discard your choices and edits in the result?"):
            self._set_result(go.initial_result(self.segs))
            self.go_to(0)

    def _set_result(self, lines: list[str]):
        sb = self.result.verticalScrollBar().value()
        self.result.setPlainText("\n".join(lines))
        self.result.verticalScrollBar().setValue(sb)

    # ---------------------------------------------------------------- accept
    def accept_merge(self):
        text = self.result.toPlainText()
        if go.remaining_conflicts(text) and not _ask_yes(
                self, "Accept Merge", "The result still contains conflict markers.\nSave it anyway?"):
            return
        top = self.git.toplevel() or self.git.folder
        data = text if text.endswith("\n") or not text else text + "\n"
        if self.eol == "\r\n":
            data = data.replace("\n", "\r\n")
        try:
            (top / self.path).write_bytes(data.encode("utf-8"))
        except OSError as e:
            QMessageBox.warning(self, "Merge", str(e))
            return
        code, out = self.git.stage([self.path])
        if code != 0:
            QMessageBox.warning(self, "Merge", f"Could not mark the file resolved:\n{out}")
            return
        self.accept()


def resolve_file(parent, git: go.GitX, path: str) -> bool:
    """Open the right resolver for one conflicted file; True when it was resolved."""
    top = git.toplevel() or git.folder
    have = {k: git.raw("cat-file", "-e", f":{k}:{path}")[0] == 0 for k in (1, 2, 3)}
    binary = False
    for k in (2, 3):
        if have[k]:
            binary = binary or b"\0" in git.raw("show", f":{k}:{path}")[1][:8000]
    if not (have[2] and have[3]) or binary:            # deleted on one side, or a binary file
        msg = (f"'{path}' is a binary file." if binary else
               f"'{path}' was {'deleted in the incoming branch' if have[2] else 'deleted in the current branch'}"
               " and changed in the other one.")
        box = QMessageBox(parent)
        box.setWindowTitle("Resolve conflict")
        box.setText(msg + "\nWhich version do you want to keep?")
        b_cur = box.addButton("Keep Current" if have[2] else "Delete (current)",
                              QMessageBox.ButtonRole.AcceptRole)
        b_inc = box.addButton("Keep Incoming" if have[3] else "Delete (incoming)",
                              QMessageBox.ButtonRole.AcceptRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        side = {b_cur: 2, b_inc: 3}.get(box.clickedButton())
        if side is None:
            return False
        if have[side]:
            git.run("checkout", "--ours" if side == 2 else "--theirs", "--", str(top / path))
            return git.stage([path])[0] == 0
        return git.run("rm", "-q", "--", str(top / path))[0] == 0
    dlg = MergeResolver(parent, git, path)
    return dlg.exec() == QDialog.DialogCode.Accepted


# ===================================================================== blame
class _BlameMargin(QWidget):
    def __init__(self, view: "BlameEdit"):
        super().__init__(view)
        self.view = view

    def sizeHint(self):
        return QSize(self.view.margin_width(), 0)

    def paintEvent(self, e):
        self.view.paint_margin(e)


class BlameEdit(QPlainTextEdit):
    """Read-only text with author / date / commit painted beside every line (new chunk = new label)."""

    def __init__(self, lines: list[go.BlameLine]):
        super().__init__()
        self.lines = lines
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setPlainText("\n".join(l.text for l in lines))
        self.margin = _BlameMargin(self)
        self.blockCountChanged.connect(lambda _n: self.setViewportMargins(self.margin_width(), 0, 0, 0))
        self.updateRequest.connect(self._on_update)
        self.setViewportMargins(self.margin_width(), 0, 0, 0)
        shas = list(dict.fromkeys(l.sha for l in lines))
        self.shade = {s: i % 2 for i, s in enumerate(shas)}

    def margin_width(self) -> int:
        return self.fontMetrics().horizontalAdvance("0" * 46)

    def label(self, i: int) -> str:
        l = self.lines[i]
        if l.uncommitted:
            return "Not committed yet"
        return f"{l.sha[:7]} {l.date} {l.author[:18]}"

    def _on_update(self, rect, dy):
        if dy:
            self.margin.scroll(0, dy)
        else:
            self.margin.update(0, rect.y(), self.margin.width(), rect.height())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        self.margin.setGeometry(QRectF(cr.left(), cr.top(), self.margin_width(), cr.height()).toRect())

    def paint_margin(self, e):
        p = QPainter(self.margin)
        base = QColor(theme.color("alt_base"))
        alt = QColor(theme.color("window"))
        p.fillRect(e.rect(), base)
        muted = QColor(theme.color("muted"))
        text = QColor(theme.color("text"))
        block = self.firstVisibleBlock()
        n = block.blockNumber()
        geo = self.blockBoundingGeometry(block).translated(self.contentOffset())
        top, h = geo.top(), geo.height()
        while block.isValid() and top <= e.rect().bottom():
            if n < len(self.lines):
                ln = self.lines[n]
                r = QRectF(0, top, self.margin.width(), h)
                if self.shade.get(ln.sha):
                    p.fillRect(r, alt)
                first = n == 0 or self.lines[n - 1].sha != ln.sha
                if first:
                    p.setPen(text if not ln.uncommitted else muted)
                    p.drawText(r.adjusted(4, 0, -4, 0), Qt.AlignmentFlag.AlignVCenter, self.label(n))
                    p.setPen(QPen(muted, 0.5))
                    p.drawLine(QPointF(0, top), QPointF(self.margin.width(), top))
            block = block.next()
            n += 1
            top += h
        p.setPen(QPen(muted, 1))
        p.drawLine(self.margin.width() - 1, e.rect().top(), self.margin.width() - 1, e.rect().bottom())


class BlameDialog(QDialog):
    def __init__(self, ctl: "GitFull", git: go.GitX, path: Path, lines: list[go.BlameLine], line: int = 0):
        super().__init__(ctl.win)
        self.ctl, self.git = ctl, git
        self.setWindowTitle(f"Blame - {path.name}")
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.view = BlameEdit(lines)
        self.view.cursorPositionChanged.connect(self._info)
        self.info = QLabel()
        theme.role(self.info, "info")
        self.info.setWordWrap(True)
        bar = QHBoxLayout()
        bar.addWidget(_btn("Show commit", "Show the commit of the current line", self._show_commit))
        bar.addWidget(_btn("Blame before this commit", "Blame the parent of this line's commit",
                           self._older))
        bar.addStretch(1)
        lay = QVBoxLayout(self)
        lay.addLayout(bar)
        lay.addWidget(self.view, 1)
        lay.addWidget(self.info)
        self.path = path
        self.resize(1100, 700)
        QTimer.singleShot(0, lambda: MergeResolver._reveal(self.view, line))

    def _cur(self) -> go.BlameLine | None:
        n = self.view.textCursor().blockNumber()
        return self.view.lines[n] if 0 <= n < len(self.view.lines) else None

    def _info(self):
        l = self._cur()
        if l:
            self.info.setText("Not committed yet (changed in the editor / working copy)" if l.uncommitted else
                              f"{l.sha[:10]}  {l.author}  {l.date}\n{l.summary}")

    def _show_commit(self):
        l = self._cur()
        if l and not l.uncommitted:
            self.ctl.show_commit(l.sha)

    def _older(self):
        l = self._cur()
        if not l or l.uncommitted:
            return
        top = self.git.toplevel() or self.git.folder
        rel = self.path.resolve().relative_to(top.resolve()).as_posix()
        code, text = self.git.run("blame", "--porcelain", f"{l.sha}^", "--", rel)
        if code != 0:
            QMessageBox.information(self, "Blame", "There is no older version of this line.")
            return
        self.view.lines = go.parse_blame(text)
        self.view.setPlainText("\n".join(x.text for x in self.view.lines))
        self.setWindowTitle(f"Blame - {self.path.name} @ {l.sha[:7]}^")


# ===================================================================== compare with commit
class CompareDialog(QDialog):
    def __init__(self, ctl: "GitFull", git: go.GitX, rel: str):
        super().__init__(ctl.win)
        self.git, self.rel = git, rel
        self.setWindowTitle(f"Compare - {rel}")
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.ref = QComboBox()
        self.ref.setEditable(True)
        self.ref.addItems(git.refs_for_compare())
        self.ref.lineEdit().setPlaceholderText("any commit, branch or tag")
        self.mode = QComboBox()
        self.mode.addItems(["Commit → working copy", "Changes made in that commit"])
        self.hist = QTreeWidget()
        self.hist.setHeaderLabels(["Commit", "Date", "Author", "Message"])
        self.hist.setRootIsDecorated(False)
        for h in git.file_log(rel):
            QTreeWidgetItem(self.hist, list(h))
        self.hist.currentItemChanged.connect(lambda it, _p: it and self.ref.setCurrentText(it.text(0)))
        self.diff = QPlainTextEdit()
        self.diff.setReadOnly(True)
        self.diff.setFont(QFont("Consolas", 9))
        self.diff.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        from .git_panel import DiffHighlighter
        self._hl = DiffHighlighter(self.diff.document())
        self.ref.currentTextChanged.connect(lambda _t: self.update_diff())
        self.mode.currentIndexChanged.connect(lambda _i: self.update_diff())
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Compare with:"))
        bar.addWidget(self.ref, 1)
        bar.addWidget(self.mode)
        split = QSplitter()
        split.addWidget(self.hist)
        split.addWidget(self.diff)
        split.setSizes([360, 700])
        lay = QVBoxLayout(self)
        lay.addLayout(bar)
        lay.addWidget(split, 1)
        self.resize(1150, 680)
        self.update_diff()

    def update_diff(self):
        ref = self.ref.currentText().strip()
        if not ref:
            return
        if self.mode.currentIndex() == 0:
            text = self.git.compare_with(self.rel, ref)
        else:
            text = self.git.run("show", "--stat", "-p", ref, "--", self.rel)[1]
        self.diff.setPlainText(text or "(no differences)")


# ===================================================================== .gitignore
class GitignoreDialog(QDialog):
    def __init__(self, ctl: "GitFull", git: go.GitX, extra: list[str] | None = None):
        super().__init__(ctl.win)
        self.top = git.toplevel() or git.folder
        self.git = git
        self.setWindowTitle(".gitignore")
        self.templates = QListWidget()
        for name in go.GITIGNORE_TEMPLATES:
            it = QListWidgetItem(name)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Unchecked)
            self.templates.addItem(it)
        add = QPushButton("Add checked templates →")
        add.clicked.connect(self.add_templates)
        self.edit = QPlainTextEdit()
        self.edit.setFont(QFont("Consolas", 10))
        try:
            self.edit.setPlainText((self.top / ".gitignore").read_text(encoding="utf-8"))
        except OSError:
            pass
        if extra:
            self._append(extra, "added from Git Changes")
        self.check = QLineEdit()
        self.check.setPlaceholderText("Test a path: is it ignored? (e.g. build/out.exe)")
        self.check.returnPressed.connect(self.test_path)
        self.check_res = QLabel()
        theme.role(self.check_res, "muted")
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("Templates"))
        ll.addWidget(self.templates, 1)
        ll.addWidget(add)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel(str(self.top / ".gitignore")))
        rl.addWidget(self.edit, 1)
        rl.addWidget(self.check)
        rl.addWidget(self.check_res)
        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([220, 520])
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.save)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(split, 1)
        lay.addWidget(bb)
        self.resize(780, 520)

    def _append(self, patterns: list[str], header: str):
        have = {l.strip() for l in self.edit.toPlainText().splitlines()}
        new = [p for p in patterns if p.strip() and p.strip() not in have]
        if not new:
            return
        text = self.edit.toPlainText()
        if text and not text.endswith("\n"):
            text += "\n"
        text += ("\n" if text else "") + f"# {header}\n" + "\n".join(new) + "\n"
        self.edit.setPlainText(text)

    def add_templates(self):
        for i in range(self.templates.count()):
            it = self.templates.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                self._append(go.GITIGNORE_TEMPLATES[it.text()].splitlines(), it.text())
                it.setCheckState(Qt.CheckState.Unchecked)

    def test_path(self):
        p = self.check.text().strip()
        if not p:
            return
        self.save(close=False)
        code, text = self.git.run("check-ignore", "-v", "--no-index", "--", p)
        self.check_res.setText(f"ignored by: {text.strip()}" if code == 0 else "not ignored")

    def save(self, close: bool = True):
        try:
            (self.top / ".gitignore").write_text(self.edit.toPlainText(), encoding="utf-8")
        except OSError as e:
            QMessageBox.warning(self, ".gitignore", str(e))
            return
        if close:
            self.accept()


# ===================================================================== controller
class GitFull(QObject):
    def __init__(self, win, panel):
        super().__init__(panel)
        self.win, self.panel = win, panel
        self.proc: QProcess | None = None
        self._inline_on: set[int] = set()
        self._build_panel()
        self._build_menu()
        self._build_status()
        panel.network = self.network                 # the panel's Pull / Push buttons use the new runner
        panel.commit_override = self.commit_override
        panel.refreshed.connect(self.on_refreshed)
        theme.changed.connect(lambda _n: self.graph.tree.viewport().update())

    # ---------------------------------------------------------------- helpers
    def gx(self) -> go.GitX | None:
        g = self.panel.git
        if g is None or not g.exe:
            return None
        return go.GitX(g.folder, g.exe)

    def repo(self) -> go.GitX | None:
        g = self.gx()
        if g is None or not g.is_repo():
            QMessageBox.information(self.win, "Git", "Open a project that is in a git repository "
                                    "(Git Changes > Init Repository creates one).")
            return None
        return g

    def report(self, code: int, text: str, what: str, gh: bool = False) -> bool:
        text = clean(text)
        if code != 0:
            hint = go.explain_gh_error(text) if gh else go.explain_error(text)
            self.win.log(f"[git] {what} failed:\n{text}")
            box = QMessageBox(QMessageBox.Icon.Warning, "Git", f"{what} failed.", parent=self.win)
            box.setInformativeText(hint or text[:600])
            box.setDetailedText(text)
            box.exec()
            return False
        if text:
            self.win.log(f"[git] {what}: {text}")
        self.win.statusBar().showMessage(f"{what}: done", 4000)
        return True

    def do(self, res: tuple[int, str], what: str) -> bool:
        ok = self.report(res[0], res[1], what)
        self.refresh_all()
        return ok

    def refresh_all(self):
        try:
            self.panel.refresh()
        except Exception as e:  # noqa: BLE001
            self.win.log(f"[git] {e}")
        idx = self.panel.right.currentIndex()
        w = self.panel.right.widget(idx)
        if hasattr(w, "reload") and w is not self.github:
            w.reload()
        try:
            self.win._fill_solution()
            self._reload_open_editors()
        except Exception:  # noqa: BLE001
            pass

    def _reload_open_editors(self):
        """After checkout / merge / stash the files on disk changed: reload unmodified editors."""
        for views in (getattr(self.win, "codeviews", {}), getattr(self.win, "modviews", {})):
            for v in list(views.values()):
                ed = getattr(v, "editor", None)
                path = getattr(ed, "path", None) or getattr(v, "path", None)
                if ed is None or path is None or ed.isModified():
                    continue
                try:
                    disk = Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")
                except (OSError, UnicodeDecodeError):
                    continue
                if disk != ed.text():
                    ed.setText(disk)
                    ed.setModified(False)

    def show_text(self, title: str, text: str):
        self.panel.diff.setPlainText(clean(text) or "(nothing)")
        self.panel.right.setCurrentWidget(self.panel.diff)
        self.win.statusBar().showMessage(title, 4000)
        try:
            self.win.dock_git.show()
            self.win.dock_git.raise_()
        except Exception:  # noqa: BLE001
            pass

    def show_commit(self, sha: str):
        g = self.gx()
        if g and sha:
            self.show_text(f"Commit {sha[:8]}", g.run("show", "--stat", "-p", sha)[1])

    # ---------------------------------------------------------------- panel additions
    def _build_panel(self):
        p = self.panel
        lay = p.layout()
        # banner: merge / rebase in progress
        self.banner = QWidget()
        bl = QHBoxLayout(self.banner)
        bl.setContentsMargins(6, 3, 6, 3)
        self.banner_text = QLabel()
        self.b_resolve = QPushButton("Resolve Conflicts...")
        self.b_resolve.clicked.connect(self.resolve_conflicts)
        self.b_continue = QPushButton("Continue")
        self.b_continue.clicked.connect(self.continue_op)
        self.b_abort = QPushButton("Abort")
        self.b_abort.clicked.connect(self.abort_op)
        bl.addWidget(self.banner_text, 1)
        for b in (self.b_resolve, self.b_continue, self.b_abort):
            bl.addWidget(b)
        theme.role(self.banner, "banner")
        self.banner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.banner.hide()
        lay.insertWidget(1, self.banner)
        # tool bar: Fetch / Sync, branch menu, progress
        bar = lay.itemAt(0).layout()
        self.b_fetch = _btn("Fetch", "Download new commits and branches from the remote (does not change your "
                            "files)", self.fetch)
        self.b_sync = _btn("Sync", "Pull, then push", self.sync)
        self.b_branch = QToolButton(text="Branches ▾")
        self.b_branch.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.b_branch.setToolTip("Switch / create branches")
        self.branch_menu = QMenu(self.b_branch)
        self.branch_menu.aboutToShow.connect(lambda: self._fill_branch_menu(self.branch_menu))
        self.b_branch.setMenu(self.branch_menu)
        self.b_stash = _btn("Stash", "Stash all changes (save them aside and clean the working folder)",
                            self.stash_save)
        self.prog = QProgressBar()
        self.prog.setMaximumWidth(160)
        self.prog.setMaximumHeight(16)
        self.prog.setTextVisible(True)
        self.prog.hide()
        self.b_cancel = _btn("✕", "Cancel the running git command", self.cancel_net)
        self.b_cancel.hide()
        pos = bar.count() - 1                           # before the stretch
        for w in (self.b_fetch, self.b_sync, self.b_branch, self.b_stash, self.prog, self.b_cancel):
            bar.insertWidget(pos, w)
            pos += 1
        # amend checkbox above the Commit button
        cl = p.b_commit.parentWidget().layout()
        row = QHBoxLayout()
        self.amend = QCheckBox("Amend")
        self.amend.setToolTip("Replace the last commit (message and/or content) instead of making a new one")
        self.amend.toggled.connect(self._on_amend)
        row.addWidget(self.amend)
        row.addStretch(1)
        cl.insertLayout(cl.indexOf(p.b_commit), row)
        # new tabs
        self.graph = GraphView(self)
        self.branches = BranchesView(self)
        self.stashes = StashView(self)
        self.tags = TagsView(self)
        self.github = GitHubView(self)
        for w, title in ((self.graph, "Graph"), (self.branches, "Branches"), (self.stashes, "Stashes"),
                         (self.tags, "Tags"), (self.github, "GitHub")):
            p.right.addTab(w, title)
        p.right.currentChanged.connect(self._tab_changed)
        # changes context menu + double click on a conflict
        p.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        p.tree.customContextMenuRequested.connect(self._changes_menu)
        p.tree.itemDoubleClicked.connect(self._changes_double)

    def _tab_changed(self, i: int):
        w = self.panel.right.widget(i)
        if w is self.github:
            self.github.reload()
        elif hasattr(w, "reload"):
            w.reload()

    def on_refreshed(self):
        g = self.gx()
        repo = g is not None and g.is_repo()
        remote = repo and bool(g.remotes())
        for b in (self.b_fetch, self.b_sync):
            b.setVisible(bool(remote))
        for b in (self.b_branch, self.b_stash, self.amend):
            b.setVisible(bool(repo))
        st = g.state() if repo else ""
        self.banner.setVisible(bool(st))
        if st:
            n = len(g.conflicts())
            names = {"merge": "Merge", "rebase": "Rebase", "cherry-pick": "Cherry-pick", "revert": "Revert"}
            self.banner_text.setText(f"{names[st]} in progress - " + (
                f"{n} file(s) with conflicts. Resolve them, then Continue." if n else
                "all conflicts are resolved. Click Continue to finish (or commit)."))
            self.b_resolve.setVisible(n > 0)
            self.b_continue.setEnabled(n == 0)
            if st == "merge" and not self.panel.msg.toPlainText().strip():
                self.panel.msg.setPlainText(g.merge_message())
        try:
            self.status_btn.setVisible(bool(repo))
            if repo:
                self.status_btn.setText(f" ⎇ {g.branch()} ")
                self.panel.status_label.hide()
        except RuntimeError:
            pass

    # ---------------------------------------------------------------- menus
    def _build_menu(self):
        w = self.win
        m = QMenu("&Git", w)
        self.menu = m

        def act(menu, text, slot, shortcut=None, tip=""):
            a = QAction(text, w)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            if tip:
                a.setStatusTip(tip)
            a.triggered.connect(lambda _c=False: self._safe(slot))
            menu.addAction(a)
            return a
        act(m, "&Git Changes", lambda: self._show_tab(None), tip="The Git Changes window")
        act(m, "&Commit All...", lambda: self._show_tab(None) or self.panel.msg.setFocus())
        m.addSeparator()
        act(m, "&Fetch", self.fetch)
        act(m, "&Pull", lambda: self.network("pull"))
        act(m, "Pull (&rebase)", lambda: self.network("pull", rebase=True))
        act(m, "P&ush", lambda: self.network("push"))
        act(m, "Force Push (with lease)...", self.force_push)
        act(m, "&Sync (pull, then push)", self.sync)
        m.addSeparator()
        act(m, "&New Branch...", self.new_branch, "Ctrl+Shift+Alt+B")
        act(m, "Manage &Branches", lambda: self._show_tab(self.branches))
        act(m, "&Merge into current branch...", lambda: self.merge(None))
        act(m, "R&ebase current branch onto...", lambda: self.rebase(None))
        act(m, "Resolve &Conflicts...", self.resolve_conflicts)
        act(m, "Continue merge / rebase", self.continue_op)
        act(m, "Abort merge / rebase", self.abort_op)
        m.addSeparator()
        act(m, "S&tash All...", self.stash_save)
        act(m, "Stas&hes", lambda: self._show_tab(self.stashes))
        act(m, "&Tags", lambda: self._show_tab(self.tags))
        m.addSeparator()
        act(m, "View &History (graph)", lambda: self._show_tab(self.graph), "Ctrl+Alt+H")
        act(m, "B&lame current file", self.blame_current)
        act(m, "Toggle &inline blame in the editor", self.toggle_inline_blame)
        act(m, "Compare current file with &commit...", self.compare_current)
        m.addSeparator()
        act(m, "&Amend last commit", lambda: (self._show_tab(None), self.amend.setChecked(True)))
        act(m, "&Undo last commit (keep changes)", self.undo_commit)
        m.addSeparator()
        gh = m.addMenu("Git&Hub")
        act(gh, "Pull Requests and Issues", lambda: self._show_tab(self.github))
        act(gh, "Create Pull Request...", lambda: (self._show_tab(self.github), self.github.create_pr()))
        act(gh, "Sign in (gh auth login)...", self.github.login)
        act(gh, "Download GitHub CLI...", self.github.download)
        m.addSeparator()
        act(m, "Edit .&gitignore...", self.edit_gitignore)
        act(m, "&Remotes...", self.manage_remotes)
        act(m, "Git &Settings...", self.settings_dialog)
        bar = w.menuBar()
        view = next((a for a in bar.actions() if a.text().replace("&", "") == "View"), None)
        acts = bar.actions()
        nxt = acts[acts.index(view) + 1] if view is not None and acts.index(view) + 1 < len(acts) else None
        if nxt is not None:
            bar.insertMenu(nxt, m)
        else:
            bar.addMenu(m)

    def _safe(self, slot):
        try:
            slot()
        except Exception as e:  # noqa: BLE001 - git must never break the IDE
            import traceback
            self.win.log(f"[git] {e}\n{traceback.format_exc()}")

    def _show_tab(self, w):
        try:
            self.win.dock_git.show()
            self.win.dock_git.raise_()
        except Exception:  # noqa: BLE001
            pass
        if w is not None:
            self.panel.right.setCurrentWidget(w)
            self._tab_changed(self.panel.right.currentIndex())
        self.panel.refresh()

    def _build_status(self):
        self.status_btn = QToolButton()
        self.status_btn.setAutoRaise(True)
        self.status_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.status_btn.setToolTip("Current git branch - click to switch or create a branch")
        menu = QMenu(self.status_btn)
        menu.aboutToShow.connect(lambda: self._fill_branch_menu(menu))
        self.status_btn.setMenu(menu)
        self.status_btn.hide()
        self.win.statusBar().addPermanentWidget(self.status_btn)

    def _fill_branch_menu(self, menu: QMenu):
        menu.clear()
        g = self.gx()
        if g is None or not g.is_repo():
            menu.addAction("(not a git repository)").setEnabled(False)
            return
        menu.addAction("New Branch...", lambda: self._safe(self.new_branch))
        menu.addAction("Manage Branches", lambda: self._show_tab(self.branches))
        menu.addSeparator()
        cur = g.branch()
        bs = g.branches()
        for b in [x for x in bs if not x.remote]:
            a = menu.addAction(("✓ " if b.head else "    ") + b.name + (f"   [{b.track}]" if b.track else ""))
            a.triggered.connect(lambda _c=False, n=b.name: self._safe(lambda: self.switch_branch(n)))
            a.setEnabled(b.name != cur)
        remotes = [x for x in bs if x.remote]
        if remotes:
            rm = menu.addMenu("Remote branches")
            for b in remotes:
                rm.addAction(b.name, lambda n=b.name: self._safe(lambda: self.switch_branch(n, True)))

    # ---------------------------------------------------------------- branch actions
    def new_branch(self, start: str = ""):
        g = self.repo()
        if g is None:
            return
        if not g.has_commits():
            QMessageBox.information(self.win, "New branch", "Make the first commit before creating branches.")
            return
        dlg = QDialog(self.win)
        dlg.setWindowTitle("Create a new branch")
        form = QFormLayout(dlg)
        name = QLineEdit()
        name.setPlaceholderText("feature/my-change")
        base = QComboBox()
        base.setEditable(True)
        refs = g.refs_for_compare()
        cur = g.branch()
        base.addItems([cur] + [r for r in refs if r != cur])
        if start:
            base.setCurrentText(start)
        checkout = QCheckBox("Checkout branch")
        checkout.setChecked(True)
        form.addRow("Branch name:", name)
        form.addRow("Based on:", base)
        form.addRow("", checkout)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)
        dlg.resize(420, 150)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        n = re.sub(r"\s+", "-", name.text().strip())
        if not n:
            return
        b = base.currentText().strip()
        remote = any(x.remote and x.name == b for x in g.branches())
        self.do(g.create_branch(n, b if b != cur else "", checkout.isChecked(), track=remote), "Create branch")

    def switch_branch(self, name: str, remote: bool = False):
        g = self.repo()
        if g is None:
            return
        try:
            self.win.save_all()
        except Exception:  # noqa: BLE001
            pass
        with Busy():
            code, text = g.switch(name, remote)
        if code != 0 and re.search(r"would be overwritten|commit your changes or stash", text, re.I):
            box = QMessageBox(QMessageBox.Icon.Question, "Switch branch",
                              f"You have uncommitted changes that conflict with '{name}'.", parent=self.win)
            box.setInformativeText("Stash them (save aside) and switch? You can bring them back from the Stashes "
                                   "tab (Pop) on any branch.")
            b_stash = box.addButton("Stash and Switch", QMessageBox.ButtonRole.AcceptRole)
            box.addButton(QMessageBox.StandardButton.Cancel)
            box.exec()
            if box.clickedButton() is b_stash:
                g.stash_save(f"before switching to {name}")
                code, text = g.switch(name, remote)
        self.do((code, text), f"Switch to {name}")

    def checkout_ref(self, ref: str):
        g = self.repo()
        if g and _ask_yes(self.win, "Checkout", f"Checkout {ref[:12]}?\n\nYou will be in 'detached HEAD' state: "
                          "create a branch there if you want to keep new commits."):
            self.do(g.run("checkout", ref), f"Checkout {ref[:12]}")

    def delete_branch(self, b: go.Branch):
        g = self.repo()
        if g is None:
            return
        if b.head:
            QMessageBox.information(self.win, "Delete branch", "You cannot delete the current branch. "
                                    "Switch to another branch first.")
            return
        if b.remote:
            remote, _, br = b.name.partition("/")
            if _ask_yes(self.win, "Delete remote branch", f"Delete '{br}' on the server '{remote}'?"):
                self.run_net(["push", remote, "--delete", br], f"Delete {b.name}")
            return
        if not _ask_yes(self.win, "Delete branch", f"Delete the local branch '{b.name}'?"):
            return
        code, text = g.delete_branch(b.name)
        if code != 0 and "not fully merged" in text:
            if _ask_yes(self.win, "Delete branch", f"'{b.name}' has commits that are not merged anywhere.\n"
                        "Delete it anyway (those commits will be lost)?"):
                code, text = g.delete_branch(b.name, force=True)
            else:
                return
        self.do((code, text), f"Delete {b.name}")

    def _pick_ref(self, title: str, label: str) -> str:
        g = self.repo()
        if g is None:
            return ""
        cur = g.branch()
        refs = [b.name for b in g.branches() if b.name != cur]
        if not refs:
            QMessageBox.information(self.win, title, "There is no other branch.")
            return ""
        ref, ok = QInputDialog.getItem(self.win, title, label, refs, 0, True)
        return ref.strip() if ok else ""

    def merge(self, ref: str | None):
        g = self.repo()
        if g is None:
            return
        ref = ref or self._pick_ref("Merge", f"Merge which branch into '{g.branch()}'?")
        if not ref:
            return
        try:
            self.win.save_all()
        except Exception:  # noqa: BLE001
            pass
        with Busy():
            code, text = g.merge(ref)
        self._after_op(g, code, text, f"Merge {ref}")

    def rebase(self, ref: str | None):
        g = self.repo()
        if g is None:
            return
        ref = ref or self._pick_ref("Rebase", f"Rebase '{g.branch()}' onto which branch?")
        if not ref or not _ask_yes(self.win, "Rebase", f"Replay the commits of '{g.branch()}' on top of '{ref}'?\n"
                                   "(Do not rebase commits that you already pushed and others use.)"):
            return
        with Busy():
            code, text = g.rebase(ref)
        self._after_op(g, code, text, f"Rebase onto {ref}")

    def _after_op(self, g: go.GitX, code: int, text: str, what: str):
        if code != 0 and g.conflicts():
            self.win.log(f"[git] {what}: conflicts\n{clean(text)}")
            self.refresh_all()
            if _ask_yes(self.win, what, f"{what} stopped because of conflicts in {len(g.conflicts())} file(s).\n"
                        "Resolve them now?"):
                self.resolve_conflicts()
            return
        self.do((code, text), what)

    def resolve_conflicts(self):
        g = self.repo()
        if g is None:
            return
        files = g.conflicts()
        if not files:
            QMessageBox.information(self.win, "Conflicts", "There are no conflicts.")
            self.refresh_all()
            return
        if len(files) == 1:
            path = files[0]
        else:
            path, ok = QInputDialog.getItem(self.win, "Resolve conflicts", f"{len(files)} files have conflicts. "
                                            "Resolve:", files, 0, False)
            if not ok:
                return
        if resolve_file(self.win, g, path):
            self.win.statusBar().showMessage(f"{path}: resolved", 4000)
        self.refresh_all()
        left = g.conflicts()
        if left and _ask_yes(self.win, "Conflicts", f"{len(left)} file(s) still have conflicts. Resolve the next?"):
            self.resolve_conflicts()
        elif not left and g.state():
            if _ask_yes(self.win, "Conflicts", f"All conflicts are resolved. Finish the {g.state()} now?"):
                self.continue_op()

    def continue_op(self):
        g = self.repo()
        if g is None:
            return
        st = g.state()
        if st == "merge" and self.panel.msg.toPlainText().strip():
            code, text = g.commit(self.panel.msg.toPlainText().strip())
            if code == 0:
                self.panel.msg.clear()
            self.do((code, text), "Finish merge")
            return
        with Busy():
            code, text = g.continue_()
        self._after_op(g, code, text, f"Continue {st or 'operation'}")

    def abort_op(self):
        g = self.repo()
        if g and g.state() and _ask_yes(self.win, "Abort", f"Abort the {g.state()} and go back to how things "
                                        "were before it started?"):
            self.do(g.abort(), f"Abort {g.state()}")

    # ---------------------------------------------------------------- commits
    def _on_amend(self, on: bool):
        g = self.gx()
        if on and g and not self.panel.msg.toPlainText().strip():
            self.panel.msg.setPlainText(g.last_message())
        self.panel.b_commit.setText("Amend Commit" if on else "Commit")

    def commit_override(self, message: str | None):
        if not self.amend.isChecked():
            return None
        g = self.gx()
        if g is None or not g.has_commits():
            return None
        if g.head_is_pushed() and not _ask_yes(self.win, "Amend", "The last commit is already pushed. Amending "
                                               "rewrites it and you will need a force push.\nAmend anyway?"):
            return False
        try:
            self.win.save_all()
        except Exception:  # noqa: BLE001
            pass
        msg = (message if message is not None else self.panel.msg.toPlainText()).strip()
        ok = self.do(g.commit_amend(msg), "Amend commit")
        if ok:
            self.panel.msg.clear()
            self.amend.setChecked(False)
        return ok

    def undo_commit(self):
        g = self.repo()
        if g and g.has_commits() and _ask_yes(self.win, "Undo last commit",
                                              f"Undo '{g.last_message().splitlines()[0][:60]}'?\n"
                                              "Its changes stay in your files (staged)."):
            self.do(g.undo_last_commit(), "Undo last commit")

    def cherry_pick(self, sha: str):
        g = self.repo()
        if g and _ask_yes(self.win, "Cherry-pick", f"Apply commit {sha[:8]} to '{g.branch()}'?"):
            code, text = g.cherry_pick(sha)
            self._after_op(g, code, text, f"Cherry-pick {sha[:8]}")

    def revert(self, sha: str):
        g = self.repo()
        if g and _ask_yes(self.win, "Revert", f"Create a new commit that undoes {sha[:8]}?"):
            code, text = g.revert(sha)
            self._after_op(g, code, text, f"Revert {sha[:8]}")

    def reset(self, sha: str, mode: str):
        g = self.repo()
        if g is None:
            return
        warn = "\n\nAll uncommitted changes will be DELETED." if mode == "hard" else ""
        if _ask_yes(self.win, "Reset", f"Move '{g.branch()}' to {sha[:8]} ({mode})?{warn}"):
            self.do(g.reset(sha, mode), f"Reset to {sha[:8]}")

    def new_tag(self, commit: str = ""):
        g = self.repo()
        if g is None or not g.has_commits():
            return
        dlg = QDialog(self.win)
        dlg.setWindowTitle("New tag")
        form = QFormLayout(dlg)
        name = QLineEdit()
        name.setPlaceholderText("v1.0")
        msg = QLineEdit()
        msg.setPlaceholderText("optional message (makes an annotated tag)")
        form.addRow("Tag name:", name)
        form.addRow("Commit:", QLabel(commit[:10] if commit else "HEAD (current commit)"))
        form.addRow("Message:", msg)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)
        if dlg.exec() == QDialog.DialogCode.Accepted and name.text().strip():
            self.do(g.create_tag(name.text().strip(), commit, msg.text().strip()), "Create tag")
            self.tags.reload()

    def stash_save(self):
        g = self.repo()
        if g is None:
            return
        if not g.status():
            QMessageBox.information(self.win, "Stash", "There are no changes to stash.")
            return
        try:
            self.win.save_all()
        except Exception:  # noqa: BLE001
            pass
        msg, ok = QInputDialog.getText(self.win, "Stash all changes", "Message (optional):")
        if ok:
            self.do(g.stash_save(msg.strip()), "Stash")
            self.stashes.reload()

    # ---------------------------------------------------------------- network
    def fetch(self):
        self.run_net(["fetch", "--all", "--prune"], "Fetch")

    def sync(self):
        self.network("pull", after=lambda ok: ok and self.network("push", confirm=False))

    def force_push(self):
        self.push(force=True)

    def network(self, op: str, rebase: bool = False, after=None, confirm: bool = True):
        if op == "push":
            return self.push(confirm=confirm, after=after)
        g = self.repo()
        if g is None:
            return
        if not g.remotes():
            QMessageBox.information(self.win, "Pull", "This repository has no remote. Add one in Git > Remotes.")
            return
        if not g.upstream():
            QMessageBox.information(self.win, "Pull", f"'{g.branch()}' does not track a remote branch yet. "
                                    "Push it first, or set its upstream in Branches > Track.")
            return
        try:
            self.win.save_all()
        except Exception:  # noqa: BLE001
            pass
        self.run_net(["pull"] + (["--rebase"] if rebase else []), "Pull", after)

    def push(self, branch: str = "", force: bool = False, confirm: bool = True, after=None):
        g = self.repo()
        if g is None:
            return
        remotes = g.remotes()
        if not remotes:
            QMessageBox.information(self.win, "Push", "This repository has no remote. Add one in Git > Remotes "
                                    "(for GitHub: create an empty repository there and paste its URL).")
            return
        cur = g.branch()
        branch = branch or cur
        up = g.upstream() if branch == cur else next((b.upstream for b in g.branches()
                                                      if b.name == branch and not b.remote), "")
        if up:
            remote, _, rbranch = up.partition("/")
            args = ["push", remote, f"{branch}:{rbranch}"]
        else:
            remote = remotes[0]
            if len(remotes) > 1:
                remote, ok = QInputDialog.getItem(self.win, "Push", "Remote:", remotes, 0, False)
                if not ok:
                    return
            args = ["push", "-u", remote, branch]
        if force:
            args.insert(1, "--force-with-lease")
            if not _ask_yes(self.win, "Force push", f"Overwrite '{branch}' on {remote} with your version?\n"
                            "(--force-with-lease refuses if someone else pushed meanwhile.)"):
                return
        elif confirm and not _ask_yes(self.win, "Push", f"Push '{branch}' to {remote}"
                                      f"{'' if up else ' (publish: creates the branch there)'}?"):
            return
        self.run_net(args, "Push", after)

    def run_net(self, args: list[str], what: str, after=None):
        g = self.repo()
        if g is None:
            return
        if self.proc is not None:
            QMessageBox.information(self.win, "Git", "Another git command is still running.")
            return
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.setWorkingDirectory(str(g.folder))
        env = QProcessEnvironment.systemEnvironment()
        env.insert("GIT_TERMINAL_PROMPT", "0")
        env.insert("GIT_EDITOR", "true")
        env.insert("GIT_MERGE_AUTOEDIT", "no")
        p.setProcessEnvironment(env)
        self.proc = p
        self._net_out = ""
        full = ["-c", "color.ui=never", args[0], "--progress", *args[1:]]
        self.prog.setRange(0, 0)
        self.prog.setFormat(what)
        self.prog.show()
        self.b_cancel.show()
        for b in (self.panel.b_pull, self.panel.b_push, self.b_fetch, self.b_sync):
            b.setEnabled(False)
        self.win.log(f"[git] git {' '.join(args)}")
        self.win.statusBar().showMessage(f"git {args[0]}...")

        def read():
            chunk = bytes(p.readAll()).decode("utf-8", errors="replace")
            self._net_out += chunk
            pr = go.parse_progress(chunk)
            if pr:
                self.prog.setRange(0, 100)
                self.prog.setValue(pr[1])
                self.prog.setFormat(f"{pr[0]} %p%")

        def done(code, _st):
            read()
            self.proc = None
            p.deleteLater()
            self.prog.hide()
            self.b_cancel.hide()
            for b in (self.panel.b_pull, self.panel.b_push, self.b_fetch, self.b_sync):
                b.setEnabled(True)
            text = "\n".join(l.split("\r")[-1] for l in self._net_out.replace("\r\n", "\n").split("\n"))
            ok = self.report(code, text, what)
            if not ok and g.conflicts():
                self.refresh_all()
                if _ask_yes(self.win, what, "The pull produced conflicts. Resolve them now?"):
                    self.resolve_conflicts()
            self.refresh_all()
            if after:
                after(ok)
        p.readyRead.connect(read)
        p.finished.connect(done)
        p.start(g.exe, full)
        self.last_args = full

    def cancel_net(self):
        if self.proc is not None:
            self.proc.kill()

    # ---------------------------------------------------------------- remotes / settings / ignore
    def manage_remotes(self):
        g = self.repo()
        if g is None:
            return
        dlg = QDialog(self.win)
        dlg.setWindowTitle("Remotes")
        lst = QTreeWidget()
        lst.setHeaderLabels(["Name", "URL"])
        lst.setRootIsDecorated(False)
        lst.setColumnWidth(0, 100)

        def fill():
            lst.clear()
            for n, u in g.remote_urls().items():
                QTreeWidgetItem(lst, [n, u])

        def add():
            name, ok = QInputDialog.getText(dlg, "Add remote", "Name:", text="origin" if not g.remotes() else "")
            if not ok or not name.strip():
                return
            url, ok = QInputDialog.getText(dlg, "Add remote", "URL (https://github.com/you/repo.git):")
            if ok and url.strip():
                self.report(*g.add_remote(name.strip(), url.strip()), "Add remote")
                fill()

        def remove():
            it = lst.currentItem()
            if it and _ask_yes(dlg, "Remove remote", f"Remove '{it.text(0)}'? (Nothing is deleted on the server.)"):
                self.report(*g.remove_remote(it.text(0)), "Remove remote")
                fill()

        def edit():
            it = lst.currentItem()
            if it is None:
                return
            url, ok = QInputDialog.getText(dlg, "Change URL", f"URL of '{it.text(0)}':", text=it.text(1))
            if ok and url.strip():
                self.report(*g.run("remote", "set-url", it.text(0), url.strip()), "Change URL")
                fill()
        bar = QHBoxLayout()
        for text, slot in (("Add...", add), ("Change URL...", edit), ("Remove", remove)):
            bar.addWidget(_btn(text, text, slot))
        bar.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(dlg.reject)
        lay = QVBoxLayout(dlg)
        lay.addLayout(bar)
        lay.addWidget(lst, 1)
        lay.addWidget(bb)
        dlg.resize(620, 300)
        fill()
        dlg.exec()
        self.refresh_all()

    def settings_dialog(self):
        g = self.gx()
        if g is None:
            QMessageBox.information(self.win, "Git", "git was not found.")
            return
        repo = g.is_repo()
        dlg = QDialog(self.win)
        dlg.setWindowTitle("Git Settings")
        form = QFormLayout(dlg)
        scope = QComboBox()
        scope.addItems(["Global (all repositories)"] + (["This repository only"] if repo else []))
        name, email = QLineEdit(), QLineEdit()
        pull = QComboBox()
        pull.addItems(["merge (default)", "rebase"])
        default_branch = QLineEdit()

        def load():
            flag = "--global" if scope.currentIndex() == 0 else "--local"
            name.setText(g.stdout("config", flag, "user.name").strip())
            email.setText(g.stdout("config", flag, "user.email").strip())
            pull.setCurrentIndex(1 if g.stdout("config", flag, "pull.rebase").strip() == "true" else 0)
            default_branch.setText(g.stdout("config", "--global", "init.defaultBranch").strip() or "main")
        scope.currentIndexChanged.connect(lambda _i: load())
        form.addRow("Scope:", scope)
        form.addRow("User name:", name)
        form.addRow("E-mail:", email)
        form.addRow("Pull:", pull)
        form.addRow("Default branch for new repositories:", default_branch)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)
        load()
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        flag = "--global" if scope.currentIndex() == 0 else "--local"
        for key, val in (("user.name", name.text().strip()), ("user.email", email.text().strip()),
                         ("pull.rebase", "true" if pull.currentIndex() == 1 else "false")):
            if val:
                g.run("config", flag, key, val)
        if default_branch.text().strip():
            g.run("config", "--global", "init.defaultBranch", default_branch.text().strip())
        self.win.statusBar().showMessage("Git settings saved", 4000)

    def edit_gitignore(self, extra: list[str] | None = None):
        g = self.repo()
        if g is not None:
            GitignoreDialog(self, g, extra).exec()
            self.refresh_all()

    # ---------------------------------------------------------------- changes context menu
    def _changes_double(self, item, _col=0):
        data = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        if data and item.text(1) == "Conflict":
            g = self.gx()
            if g and resolve_file(self.win, g, data[0]):
                self.refresh_all()

    def _changes_menu(self, pos):
        p = self.panel
        it = p.tree.itemAt(pos)
        data = it.data(0, Qt.ItemDataRole.UserRole) if it else None
        if not data:
            return
        sel = p.selected() or [data]
        path, staged, untracked = data
        g = self.gx()
        top = g.toplevel() or g.folder
        m = QMenu(p)
        if it.text(1) == "Conflict":
            m.addAction("Resolve conflict...", lambda: self._changes_double(it))
            m.addAction("Keep current (ours)", lambda: self.do((g.run("checkout", "--ours", "--", str(top / path))[0]
                                                               or g.stage([path])[0], ""), "Take ours"))
            m.addAction("Keep incoming (theirs)", lambda: self.do((g.run("checkout", "--theirs", "--",
                                                                         str(top / path))[0]
                                                                  or g.stage([path])[0], ""), "Take theirs"))
            m.addSeparator()
        if staged:
            m.addAction("Unstage", p.unstage_selected)
        else:
            m.addAction("Stage", p.stage_selected)
            m.addAction("Discard changes...", lambda: self.discard(sel))
        m.addSeparator()
        m.addAction("Open", lambda: p._open_file(it))
        if not untracked:
            m.addAction("Blame", lambda: self.blame_path(top / path))
            m.addAction("Compare with commit...", lambda: self.compare_path(top / path))
        m.addSeparator()
        ext = Path(path).suffix
        m.addAction(f"Ignore this file ({path})", lambda: self.edit_gitignore(["/" + path]))
        if ext:
            m.addAction(f"Ignore all *{ext} files", lambda: self.edit_gitignore([f"*{ext}"]))
        m.addAction("Copy path", lambda: QApplication.clipboard().setText(str(top / path)))
        m.exec(p.tree.viewport().mapToGlobal(pos))

    def discard(self, sel):
        g = self.repo()
        if g is None:
            return
        tracked = [p for p, staged, u in sel if not staged and not u]
        new = [p for p, staged, u in sel if not staged and u]
        names = "\n".join(tracked + new)[:800]
        if not (tracked or new) or not _ask_yes(self.win, "Discard changes",
                                                f"Throw away the changes in:\n{names}\n\nThis cannot be undone."):
            return
        if tracked:
            self.report(*g.discard(tracked), "Discard changes")
        if new:
            self.report(*g.discard(new, untracked=True), "Delete new files")
        self.refresh_all()

    # ---------------------------------------------------------------- blame / compare
    def _current_file(self) -> tuple[Path | None, object, int]:
        v = self.win._current_code()
        ed = getattr(v, "editor", None) if v is not None else None
        path = getattr(ed, "path", None) or getattr(v, "path", None)
        line = 0
        try:
            line = ed.getCursorPosition()[0]
        except Exception:  # noqa: BLE001
            pass
        if path is None:
            QMessageBox.information(self.win, "Git", "Open a code file in the editor first.")
            return None, None, 0
        return Path(path), ed, line

    def _git_for(self, path: Path) -> tuple[go.GitX | None, str]:
        g = go.GitX(path.parent, self.panel.git.exe if self.panel.git else None)
        top = g.toplevel()
        if top is None:
            QMessageBox.information(self.win, "Git", f"{path.name} is not in a git repository.")
            return None, ""
        try:
            rel = path.resolve().relative_to(top.resolve()).as_posix()
        except ValueError:
            return None, ""
        g.folder = top
        if not g.stdout("ls-files", "--", rel).strip():
            QMessageBox.information(self.win, "Git", f"{path.name} is not committed to git yet.")
            return None, ""
        return g, rel

    def blame_current(self):
        path, ed, line = self._current_file()
        if path:
            self.blame_path(path, ed, line)

    def blame_path(self, path: Path, ed=None, line: int = 0):
        g, rel = self._git_for(Path(path))
        if g is None:
            return
        contents = ed.text() if ed is not None and hasattr(ed, "text") else None
        with Busy():
            lines = g.blame(rel, contents)
        if not lines:
            QMessageBox.information(self.win, "Blame", "git blame returned nothing for this file.")
            return
        dlg = BlameDialog(self, g, Path(path), lines, line)
        dlg.show()
        self._blame_dlg = dlg

    def toggle_inline_blame(self):
        path, ed, _line = self._current_file()
        if path is None:
            return
        if not hasattr(ed, "_js"):
            self.blame_path(path, ed, _line)          # classic editor: the blame window
            return
        key = id(ed)
        if key in self._inline_on:
            self._inline_on.discard(key)
            ed._js("if(window.radEditor){window._radBlame=window.radEditor.deltaDecorations(window._radBlame||[],[]);}")
            self.win.statusBar().showMessage("Inline blame off", 3000)
            return
        g, rel = self._git_for(path)
        if g is None:
            return
        with Busy():
            lines = g.blame(rel, ed.text())
        ed._js(inline_blame_js(lines))
        self._inline_on.add(key)
        self.win.statusBar().showMessage("Inline blame on (Git > Toggle inline blame to hide)", 4000)

    def compare_current(self):
        path, _ed, _line = self._current_file()
        if path:
            self.compare_path(path)

    def compare_path(self, path: Path):
        g, rel = self._git_for(Path(path))
        if g is not None:
            dlg = CompareDialog(self, g, rel)
            dlg.show()
            self._compare_dlg = dlg

    def compare_commit_worktree(self, sha: str):
        g = self.gx()
        if g:
            self.show_text(f"{sha[:8]} vs working copy", g.run("diff", "--stat", "-p", sha)[1])


def inline_blame_js(lines: list[go.BlameLine]) -> str:
    """JavaScript that shows 'author, date - summary' after the first line of every blame chunk in Monaco."""
    import json
    data = []
    for i, l in enumerate(lines):
        if i and lines[i - 1].sha == l.sha:
            continue
        j = i                              # annotate the first non-blank line of the chunk
        while j < len(lines) and lines[j].sha == l.sha and not lines[j].text.strip():
            j += 1
        if j >= len(lines) or lines[j].sha != l.sha:
            continue
        i = j
        label = "You - not committed yet" if l.uncommitted else f"{l.author}, {l.date} • {l.summary[:60]}"
        hover = "Not committed yet" if l.uncommitted else f"**{l.sha[:10]}** {l.author} {l.date}\n\n{l.summary}"
        data.append([i + 1, "    " + label, hover])
    colour = theme.color("muted")
    return ("(function(){const ed=window.radEditor;if(!ed)return;"
            "let s=document.getElementById('rad-blame-css');if(!s){s=document.createElement('style');"
            "s.id='rad-blame-css';document.head.appendChild(s);}"
            f"s.textContent='.rad-blame-after{{color:{colour};opacity:.75;font-style:italic;}}';"
            f"const D={json.dumps(data)};const m=ed.getModel();"
            "window._radBlame=ed.deltaDecorations(window._radBlame||[],D.filter(d=>d[0]<=m.getLineCount()).map(d=>{"
            "const c=m.getLineMaxColumn(d[0]);return {range:new monaco.Range(d[0],1,d[0],c),"
            "options:{after:{content:d[1],inlineClassName:'rad-blame-after'},hoverMessage:{value:d[2]}}};}));})();")


# ===================================================================== install
def attach(win) -> GitFull | None:
    panel = getattr(win, "git_panel", None)
    if panel is None or getattr(win, "git_full", None) is not None:
        return getattr(win, "git_full", None)
    ctl = GitFull(win, panel)
    win.git_full = ctl
    return ctl


def install(win) -> None:
    # git_full sorts before git_panel: attach right after the Git Changes panel is installed
    from . import git_panel
    if getattr(win, "git_panel", None) is not None:
        attach(win)
        return
    orig = git_panel.install
    if getattr(orig, "_git_full_wrapped", False):
        return

    def wrapped(w):
        orig(w)
        try:
            attach(w)
        except Exception:  # noqa: BLE001 - never break the IDE
            import traceback
            w.log(f"[git] full client failed to load:\n{traceback.format_exc()}")
    wrapped._git_full_wrapped = True
    git_panel.install = wrapped


__all__ = ["GitFull", "MergeResolver", "BlameDialog", "CompareDialog", "GitignoreDialog", "GraphView",
           "BranchesView", "StashView", "TagsView", "GitHubView", "resolve_file", "inline_blame_js", "attach"]
