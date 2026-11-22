"""Git integration (View > Git Changes): init, status with file states, stage /
unstage, commit, diff viewer, history, pull / push (only when a remote exists and
only when the user clicks), current branch in the status bar and changed files
coloured in the Solution Explorer. Uses the git command line."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QBrush, QColor, QFont, QKeySequence, QSyntaxHighlighter, QTextCharFormat
from PyQt6.QtWidgets import (QDockWidget, QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPlainTextEdit,
                             QPushButton, QSplitter, QTabWidget, QToolButton, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

GIT_HINTS = [r"C:\Program Files\Git\cmd\git.exe", r"C:\Program Files (x86)\Git\cmd\git.exe"]
GITIGNORE = """# RAD IDE
__pycache__/
*.pyc
.radide_backup/
_deleted/
build/
dist/
target/
.venv/
"""
STATE_NAMES = {"M": "Modified", "A": "Added", "D": "Deleted", "R": "Renamed", "C": "Copied",
               "U": "Conflict", "?": "Untracked", "T": "Type changed", "!": "Ignored"}
STATE_COLORS = {"Modified": "#1F5FBF", "Added": "#2E8B57", "Untracked": "#2E8B57", "Deleted": "#C0392B",
                "Renamed": "#8E44AD", "Copied": "#8E44AD", "Conflict": "#D35400", "Type changed": "#1F5FBF"}
ORIG_BRUSH = int(Qt.ItemDataRole.UserRole) + 77
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def find_git() -> str:
    found = shutil.which("git")
    if found:
        return found
    return next((h for h in GIT_HINTS if Path(h).exists()), "")


@dataclass
class FileStatus:
    path: str            # relative to the repository root, forward slashes
    index: str           # X of "XY"
    work: str            # Y of "XY"
    orig: str = ""       # rename source

    @property
    def staged(self) -> bool:
        if "U" in (self.index, self.work) or (self.index == self.work and self.index in "AD"):
            return False                  # a conflict is listed once, under Changes
        return self.index not in (" ", "?", "!")

    @property
    def unstaged(self) -> bool:
        return self.work != " "

    def state(self, staged: bool) -> str:
        if self.index == "?":
            return "Untracked"
        if "U" in (self.index, self.work) or (self.index == self.work and self.index in "AD"):
            return "Conflict"
        return STATE_NAMES.get(self.index if staged else self.work, "Changed")


class Git:
    """Thin wrapper around the git CLI for one working folder."""

    def __init__(self, folder: Path, exe: str | None = None):
        self.folder = Path(folder)
        self.exe = exe or find_git()

    def run(self, *args: str, stdin: str | None = None, timeout: int = 20) -> tuple[int, str]:
        if not self.exe:
            return -1, "git was not found"
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C.UTF-8")
        try:
            r = subprocess.run([self.exe, "-c", "core.quotepath=false", "-c", "color.ui=never", *args],
                               cwd=str(self.folder), input=stdin.encode("utf-8") if stdin is not None else None,
                               capture_output=True, timeout=timeout, env=env, creationflags=NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired) as e:
            return -1, str(e)
        out = (r.stdout + (b"\n" + r.stderr if r.stderr else b"")).decode("utf-8", errors="replace")
        return r.returncode, out.replace("\r\n", "\n")

    def out(self, *args: str) -> str:
        code, text = self.run(*args)
        return text.strip() if code == 0 else ""

    # ------------------------------------------------------------ queries
    def toplevel(self) -> Path | None:
        if not self.folder.exists():
            return None
        code, text = self.run("rev-parse", "--show-toplevel")
        if code != 0:
            return None
        return Path(text.strip().splitlines()[0])

    def is_repo(self) -> bool:
        return self.toplevel() is not None

    def branch(self) -> str:
        b = self.out("rev-parse", "--abbrev-ref", "HEAD")
        if b == "HEAD":
            return "(detached " + self.out("rev-parse", "--short", "HEAD") + ")"
        if not b:                                   # no commits yet
            b = self.out("symbolic-ref", "--short", "HEAD")
        return b

    def remotes(self) -> list[str]:
        return [r for r in self.out("remote").splitlines() if r.strip()]

    def upstream(self) -> str:
        return self.out("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")

    def status(self, untracked: str = "normal") -> list[FileStatus]:
        """git status. *untracked* = "normal" (default: an untracked folder is one entry, fast with
        thousands of new files), "all" (every file) or "no"."""
        code, text = self.run("status", "--porcelain=v1", "-z", f"--untracked-files={untracked}", timeout=60)
        if code != 0:
            return []
        parts = text.split("\0")
        out: list[FileStatus] = []
        i = 0
        while i < len(parts):
            entry = parts[i]
            i += 1
            if len(entry) < 4:
                continue
            x, y, path = entry[0], entry[1], entry[3:]
            orig = ""
            if x in "RC":
                orig = parts[i] if i < len(parts) else ""
                i += 1
            out.append(FileStatus(path, x, y, orig))
        return out

    def log(self, n: int = 200) -> list[tuple[str, str, str, str]]:
        code, text = self.run("log", f"-n{n}", "--date=format:%Y-%m-%d %H:%M",
                              "--pretty=format:%h%x1f%ad%x1f%an%x1f%s")
        if code != 0:
            return []
        return [tuple(l.split("\x1f", 3)) for l in text.splitlines() if l.count("\x1f") == 3]

    def diff(self, path: str, staged: bool, untracked: bool = False) -> str:
        if untracked:
            top = self.toplevel() or self.folder
            p = top / path
            if p.is_dir():                          # --untracked-files=normal: a whole new folder
                files = []
                for f in p.rglob("*"):
                    if f.is_file():
                        files.append(f.relative_to(top).as_posix())
                        if len(files) > 500:
                            break
                more = "\n..." if len(files) > 500 else ""
                return f"new folder: {path}\n@@ untracked @@\n" + "".join(f"+{f}\n" for f in files[:500]) + more
            try:
                body = p.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                return str(e)
            return f"new file: {path}\n@@ untracked @@\n" + "".join(f"+{l}\n" for l in body.splitlines())
        args = ["diff", "--cached"] if staged else ["diff"]
        top = self.toplevel() or self.folder
        return self.run(*args, "--", str(top / path))[1]

    # ------------------------------------------------------------ actions
    def init(self) -> tuple[int, str]:
        code, text = self.run("init")
        gi = self.folder / ".gitignore"
        if code == 0 and not gi.exists():
            gi.write_text(GITIGNORE, encoding="utf-8")
        return code, text

    def _abs(self, paths: list[str]) -> list[str]:
        top = self.toplevel() or self.folder
        return [str(top / p) for p in paths]

    def stage(self, paths: list[str]) -> tuple[int, str]:
        return self.run("add", "--", *self._abs(paths))

    def stage_all(self) -> tuple[int, str]:
        return self.run("add", "-A", "--", str(self.folder))

    def unstage(self, paths: list[str]) -> tuple[int, str]:
        if not self.out("rev-parse", "--verify", "-q", "HEAD"):        # before the first commit
            return self.run("rm", "--cached", "-q", "--", *self._abs(paths))
        return self.run("reset", "-q", "HEAD", "--", *self._abs(paths))

    def commit(self, message: str) -> tuple[int, str]:
        return self.run("commit", "-F", "-", stdin=message)


# ===================================================================== diff colouring
class DiffHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        self.fmts = {}
        for key, colour in (("+", "#22863A"), ("-", "#C0392B"), ("@", "#6F42C1"), ("h", "#555555")):
            f = QTextCharFormat()
            f.setForeground(QColor(colour))
            if key in ("@", "h"):
                f.setFontWeight(QFont.Weight.Bold)
            self.fmts[key] = f

    def highlightBlock(self, text: str):
        if text.startswith(("+++", "---", "diff ", "index ", "commit ", "Author:", "Date:", "new file")):
            self.setFormat(0, len(text), self.fmts["h"])
        elif text.startswith("+"):
            self.setFormat(0, len(text), self.fmts["+"])
        elif text.startswith("-"):
            self.setFormat(0, len(text), self.fmts["-"])
        elif text.startswith("@@"):
            self.setFormat(0, len(text), self.fmts["@"])


# ===================================================================== panel
class GitPanel(QWidget):
    refreshed = pyqtSignal()
    MAX_TREE_ITEMS = 1000            # per group (Staged / Changes); the rest is summarised

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.git: Git | None = None
        self.statuses: list[FileStatus] = []
        self._net: QProcess | None = None

        def tb(text, tip, slot):
            b = QToolButton(text=text)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            return b
        self.branch = QLabel()
        self.branch.setStyleSheet("font-weight:bold;")
        self.b_init = tb("Init Repository", "git init in the project folder", self.init_repo)
        self.b_refresh = tb("Refresh", "Refresh the status", self.refresh)
        self.b_stage = tb("Stage", "Stage the selected files (git add)", self.stage_selected)
        self.b_unstage = tb("Unstage", "Unstage the selected files", self.unstage_selected)
        self.b_stage_all = tb("Stage All", "Stage every change", self.stage_all)
        self.b_pull = tb("Pull", "git pull from the remote", lambda: self.network("pull"))
        self.b_push = tb("Push", "git push to the remote", lambda: self.network("push"))
        bar = QHBoxLayout()
        bar.setContentsMargins(2, 2, 2, 0)
        for w in (self.branch, self.b_init, self.b_refresh, self.b_stage, self.b_unstage, self.b_stage_all,
                  self.b_pull, self.b_push):
            bar.addWidget(w)
        bar.addStretch(1)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["File", "State"])
        self.tree.setColumnWidth(0, 260)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.currentItemChanged.connect(lambda it, _p: self.show_diff(it))
        self.tree.itemDoubleClicked.connect(self._open_file)
        self.msg = QPlainTextEdit()
        self.msg.setPlaceholderText("Commit message (Ctrl+Enter to commit)")
        self.msg.setMaximumHeight(70)
        self.b_commit = QPushButton("Commit")
        self.b_commit.clicked.connect(self.commit)
        from PyQt6.QtGui import QShortcut
        QShortcut(QKeySequence("Ctrl+Return"), self.msg, self.commit)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(self.tree, 1)
        ll.addWidget(self.msg)
        ll.addWidget(self.b_commit)

        self.diff = QPlainTextEdit()
        self.diff.setReadOnly(True)
        self.diff.setFont(QFont("Consolas", 9))
        self.diff.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._hl = DiffHighlighter(self.diff.document())
        self.history = QTreeWidget()
        self.history.setHeaderLabels(["Commit", "Date", "Author", "Message"])
        self.history.setRootIsDecorated(False)
        self.history.setColumnWidth(0, 70)
        self.history.setColumnWidth(1, 120)
        self.history.itemDoubleClicked.connect(self._show_commit)
        self.right = QTabWidget()
        self.right.addTab(self.diff, "Diff")
        self.right.addTab(self.history, "History")
        self.right.currentChanged.connect(lambda i: i == 1 and self.refresh_log())
        split = QSplitter()
        split.addWidget(left)
        split.addWidget(self.right)
        split.setSizes([300, 500])
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(bar)
        lay.addWidget(split, 1)
        self.status_label = QLabel()
        win.statusBar().addPermanentWidget(self.status_label)
        self._update_buttons(False)

    # ------------------------------------------------------------ state
    def set_project(self, background: bool = False):
        p = self.win.project
        self.git = Git(p.folder) if p is not None else None
        self._prefix_cache = None
        self.diff.clear()
        self.history.clear()
        if background:
            self.refresh_async()
        else:
            self.refresh()

    # ---- background refresh: git runs in a worker thread, the UI is filled when it answers.
    # Opening a project, the 5 s timer, Save and showing the dock use it (never block the IDE).
    def untracked_mode(self) -> str:
        """--untracked-files value: "normal" (new folders collapsed, the default) or "all"
        (Tools > Options key git/untracked_all)."""
        try:
            v = self.win.settings.value("git/untracked_all", False)
        except Exception:  # noqa: BLE001
            v = False
        return "all" if v in (True, "true", "1", 1) else "normal"

    def _query(self, g: "Git", untracked: str) -> dict:
        """Everything _apply needs, computed without touching widgets (thread safe)."""
        top = g.toplevel()
        if top is None:
            return {"top": None, "folder": g.folder}
        gd = g.out("rev-parse", "--absolute-git-dir")      # git_full.py's merge / rebase banner reads it
        return {"top": top, "branch": g.branch(), "statuses": g.status(untracked), "remotes": g.remotes(),
                "git_dir": Path(gd.splitlines()[0]) if gd else None, "folder": g.folder}

    def refresh_async(self):
        g = self.git
        if g is None or not g.exe:
            self.refresh()
            return
        if getattr(self, "_bg_busy", False):
            self._bg_again = True                 # one more pass when the running one ends
            return
        self._bg_busy, self._bg_again = True, False
        self._bg_gen = getattr(self, "_bg_gen", 0) + 1
        gen, mode = self._bg_gen, self.untracked_mode()
        if not hasattr(self, "_bg_sig"):
            from PyQt6.QtCore import QObject

            class _Sig(QObject):
                done = pyqtSignal(object, object, int)
            self._bg_sig = _Sig(self)
            self._bg_sig.done.connect(self._bg_done)

        def work():
            try:
                res = self._query(g, mode)
            except Exception as e:  # noqa: BLE001
                res = {"error": str(e)}
            try:
                self._bg_sig.done.emit(g, res, gen)
            except RuntimeError:                  # the panel was deleted
                pass
        import threading
        threading.Thread(target=work, daemon=True, name="radide-git-status").start()

    def _bg_done(self, g, res: dict, gen: int):
        self._bg_busy = False
        if g is self.git and gen == getattr(self, "_bg_gen", 0) and "error" not in res:
            try:
                self._apply(g, res)
            finally:
                self.refreshed.emit()
        if getattr(self, "_bg_again", False):
            self._bg_again = False
            self.refresh_async()

    def is_refreshing(self) -> bool:
        return bool(getattr(self, "_bg_busy", False))

    def _update_buttons(self, repo: bool, remote: bool = False):
        has_git = self.git is not None and bool(self.git.exe)
        self.b_init.setVisible(has_git and not repo)
        for b in (self.b_refresh, self.b_stage, self.b_unstage, self.b_stage_all, self.b_commit, self.msg):
            b.setEnabled(repo)
        busy = self._net is not None
        for b in (self.b_pull, self.b_push):
            b.setVisible(repo and remote)
            b.setEnabled(not busy)

    def refresh(self):
        try:
            self._refresh()
        finally:
            self.refreshed.emit()        # git_full.py (branches, conflicts banner, ...) listens

    def _refresh(self):
        g = self.git
        if g is None or not g.exe:
            self.branch.setText("" if g is None else "git not found")
            self.status_label.setText("")
            self.statuses = []
            self.tree.clear()
            self._update_buttons(False)
            self.colour_solution({})
            return
        self._bg_gen = getattr(self, "_bg_gen", 0) + 1      # a running background pass is now stale
        self._apply(g, self._query(g, self.untracked_mode()))

    def _apply(self, g: "Git", res: dict):
        self.last_query = res               # what git said, for the refreshed listeners (no git on the UI thread)
        top = res.get("top")
        if top is None:
            self.branch.setText("Not a git repository")
            self.status_label.setText("")
            self.statuses = []
            self.tree.clear()
            self._update_buttons(False)
            self.colour_solution({})
            return
        if top != getattr(self, "top", None):
            self._prefix_cache = None
        self.top = top
        br = res["branch"]
        self.statuses = res["statuses"]
        remotes = res["remotes"]
        self._update_buttons(True, bool(remotes))
        dirty = bool(self.statuses)
        self.branch.setText(f"Branch: {br}")
        self.status_label.setText(f"  Git: {br}{' *' if dirty else ''}  ")
        self.status_label.setToolTip(f"{top}\n{len(self.statuses)} changed file(s)"
                                     + (f"\nremotes: {', '.join(remotes)}" if remotes else ""))
        self._fill_tree()
        self.colour_solution(self._project_states())

    def _rel(self, repo_path: str) -> str:
        """Repo-relative path -> path relative to the project folder (if inside). The project's
        prefix inside the repository is resolved once (no file system call per path: thousands of
        untracked files made this take a minute)."""
        cache = getattr(self, "_prefix_cache", None)
        proj = self.win.project
        if proj is None:
            return repo_path
        if cache is None or cache[0] != (str(self.top), str(proj.folder)):
            try:
                pre = Path(proj.folder).resolve().relative_to(Path(self.top).resolve()).as_posix()
                pre = "" if pre == "." else pre + "/"
            except (ValueError, OSError):
                pre = None                        # the project is not inside this repository
            cache = self._prefix_cache = ((str(self.top), str(proj.folder)), pre)
        pre = cache[1]
        if pre is None:
            return repo_path
        if not pre:
            return repo_path
        if repo_path.lower().startswith(pre.lower()):
            return repo_path[len(pre):]
        return repo_path

    def _fill_tree(self):
        cur = self.tree.currentItem()
        keep = (cur.data(0, Qt.ItemDataRole.UserRole) if cur else None)
        self.tree.clear()
        staged = QTreeWidgetItem(self.tree, ["Staged Changes", ""])
        changes = QTreeWidgetItem(self.tree, ["Changes", ""])
        bold = QFont()
        bold.setBold(True)
        for top in (staged, changes):
            top.setFont(0, bold)
            top.setFlags(top.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        restore = None
        shown = {id(staged): 0, id(changes): 0}
        hidden = {id(staged): 0, id(changes): 0}
        for st in self.statuses:
            for is_staged, parent in ((True, staged), (False, changes)):
                if (st.staged if is_staged else st.unstaged):
                    if shown[id(parent)] >= self.MAX_TREE_ITEMS:   # thousands of files: list the first ones
                        hidden[id(parent)] += 1
                        continue
                    shown[id(parent)] += 1
                    state = st.state(is_staged)
                    label = self._rel(st.path) + (f"  (from {st.orig})" if st.orig else "")
                    it = QTreeWidgetItem(parent, [label, state])
                    it.setData(0, Qt.ItemDataRole.UserRole, (st.path, is_staged, st.index == "?"))
                    it.setForeground(1, QBrush(QColor(STATE_COLORS.get(state, "#000000"))))
                    if keep == (st.path, is_staged, st.index == "?"):
                        restore = it
        for parent in (staged, changes):
            if hidden[id(parent)]:
                more = QTreeWidgetItem(parent, [f"... {hidden[id(parent)]} more file(s) not listed "
                                                "(Stage All / the command line handle them)", ""])
                more.setFlags(more.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                more.setForeground(0, QBrush(QColor("#808080")))
        staged.setText(0, f"Staged Changes ({shown[id(staged)] + hidden[id(staged)]})")
        changes.setText(0, f"Changes ({shown[id(changes)] + hidden[id(changes)]})")
        self.tree.expandAll()
        if restore is not None:
            self.tree.setCurrentItem(restore)

    def _project_states(self) -> dict[str, str]:
        """project-relative path (lower case) -> state of files with changes."""
        out = {}
        for st in self.statuses:
            state = st.state(st.staged and not st.unstaged)
            out[self._rel(st.path).lower()] = state
        return out

    def selected(self) -> list[tuple[str, bool, bool]]:
        return [it.data(0, Qt.ItemDataRole.UserRole) for it in self.tree.selectedItems()
                if it.data(0, Qt.ItemDataRole.UserRole)]

    # ------------------------------------------------------------ actions
    def _report(self, code: int, text: str, what: str) -> bool:
        if code != 0:
            self.win.log(f"[git] {what} failed:\n{text}")
            QMessageBox.warning(self, "Git", f"{what} failed:\n\n{text.strip()[:1500]}")
            return False
        if text.strip():
            self.win.log(f"[git] {text.strip()}")
        return True

    def init_repo(self):
        if self.git is None:
            return
        if self._report(*self.git.init(), "git init"):
            self.win.statusBar().showMessage("Git repository created", 4000)
        self.refresh()

    def stage_selected(self):
        paths = [p for p, staged, _u in self.selected() if not staged]
        if paths and self.git:
            self._report(*self.git.stage(paths), "Stage")
            self.refresh()

    def unstage_selected(self):
        paths = [p for p, staged, _u in self.selected() if staged]
        if paths and self.git:
            self._report(*self.git.unstage(paths), "Unstage")
            self.refresh()

    def stage_all(self):
        if self.git:
            self._report(*self.git.stage_all(), "Stage all")
            self.refresh()

    def commit(self, message: str | None = None):
        if self.git is None or not self.git.is_repo():
            return False
        override = getattr(self, "commit_override", None)      # git_full.py: "Amend" checkbox
        if callable(override):
            r = override(message if isinstance(message, str) else None)
            if r is not None:
                return r
        msg = (message if isinstance(message, str) else self.msg.toPlainText()).strip()
        if not msg:
            QMessageBox.information(self, "Git", "Enter a commit message first.")
            self.msg.setFocus()
            return False
        try:
            self.win.save_all()
        except Exception:  # noqa: BLE001
            pass
        self.statuses = self.git.status()
        if not any(s.staged for s in self.statuses):
            if not self.statuses:
                QMessageBox.information(self, "Git", "There are no changes to commit.")
                return False
            if QMessageBox.question(self, "Git", "No changes are staged.\nStage all changes and commit them?") \
                    != QMessageBox.StandardButton.Yes:
                return False
            self.git.stage_all()
        ok = self._report(*self.git.commit(msg), "Commit")
        if ok:
            self.msg.clear()
            self.win.statusBar().showMessage("Committed", 4000)
        self.refresh()
        if self.right.currentIndex() == 1:
            self.refresh_log()
        return ok

    def show_diff(self, item):
        data = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        if not data or self.git is None:
            return
        path, staged, untracked = data
        self.diff.setPlainText(self.git.diff(path, staged, untracked) or "(no textual changes)")
        self.right.setCurrentIndex(0)

    def _open_file(self, item, _col=0):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and self.win.project:
            try:
                self.win._editor_for_file(Path(data[0]).name)
            except Exception:  # noqa: BLE001
                pass

    def refresh_log(self):
        self.history.clear()
        if self.git is None:
            return
        for h, date, author, subject in self.git.log():
            QTreeWidgetItem(self.history, [h, date, author, subject])

    def _show_commit(self, item, _col=0):
        if self.git:
            self.diff.setPlainText(self.git.run("show", "--stat", "-p", item.text(0))[1])
            self.right.setCurrentIndex(0)

    def network(self, op: str):
        """Pull / push - started only by the user, asynchronously."""
        if self.git is None or self._net is not None:
            return
        remotes = self.git.remotes()
        if not remotes:
            return
        args = [op]
        if op == "push":
            branch = self.git.branch()
            if not self.git.upstream():
                remote = remotes[0]
                if len(remotes) > 1:
                    remote, ok = QInputDialog.getItem(self, "Push", "Remote:", remotes, 0, False)
                    if not ok:
                        return
                args = ["push", "-u", remote, branch]
            if QMessageBox.question(self, "Push", f"Push branch '{branch}' to {' '.join(args[1:]) or 'its upstream'}?") \
                    != QMessageBox.StandardButton.Yes:
                return
        p = QProcess(self)
        p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        p.setWorkingDirectory(str(self.git.folder))
        env = QProcessEnvironment.systemEnvironment()
        env.insert("GIT_TERMINAL_PROMPT", "0")
        p.setProcessEnvironment(env)
        self._net = p
        self._update_buttons(True, True)
        self.win.log(f"[git] {' '.join(args)} ...")
        self.win.statusBar().showMessage(f"git {op}...")

        def done(code, _st):
            text = bytes(p.readAll()).decode("utf-8", errors="replace")
            self._net = None
            p.deleteLater()
            self._report(code, text, f"git {op}")
            self.win.statusBar().showMessage(f"git {op} {'finished' if code == 0 else 'failed'}", 5000)
            self.refresh()
        p.finished.connect(done)
        from .. import progress
        progress.track_process(p, f"git {op}", self.win)       # status-bar progress (radide/progress.py)
        p.start(self.git.exe, args)

    # ------------------------------------------------------------ solution explorer
    def colour_solution(self, states: dict[str, str]):
        """Colour Solution Explorer items whose files have git changes."""
        sol = getattr(self.win, "solution", None)
        if sol is None:
            return
        stack = [sol.topLevelItem(i) for i in range(sol.topLevelItemCount())]
        while stack:
            it = stack.pop()
            stack.extend(it.child(i) for i in range(it.childCount()))
            if not it.data(0, Qt.ItemDataRole.UserRole):
                continue
            fname = it.text(0).split("  ")[0].strip().lower()
            state = states.get(fname)
            if state is None and it.data(0, Qt.ItemDataRole.UserRole)[0] == "design":
                state = states.get(f"{it.data(0, Qt.ItemDataRole.UserRole)[1]}.form".lower())
            orig = it.data(0, ORIG_BRUSH)
            if state:
                if orig is None:
                    it.setData(0, ORIG_BRUSH, it.foreground(0))
                it.setForeground(0, QBrush(QColor(STATE_COLORS.get(state, "#1F5FBF"))))
                it.setToolTip(0, f"git: {state}")
            elif orig is not None:
                it.setForeground(0, orig)
                it.setData(0, ORIG_BRUSH, None)
                it.setToolTip(0, "")


def show_git(win):
    win.dock_git.show()
    win.dock_git.raise_()
    win.git_panel.refresh_async()


def install(win) -> None:
    panel = GitPanel(win)
    win.git_panel = panel
    d = QDockWidget("Git Changes", win)
    d.setObjectName("Git Changes")
    # in a scroll area: the panel's own minimum height (~260 px) made the tabbed bottom area - and the
    # whole VS layout - taller than a 800 px screen; a short dock now scrolls instead
    from PyQt6.QtWidgets import QFrame, QScrollArea
    scroll = QScrollArea()
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidgetResizable(True)
    scroll.setWidget(panel)
    scroll.setMinimumHeight(60)
    d.setWidget(scroll)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, d)
    win.tabifyDockWidget(win.dock_output, d)
    win.dock_output.raise_()
    win.dock_git = d
    a = QAction("&Git Changes", win)
    a.setShortcut(QKeySequence("Ctrl+Alt+G"))
    a.triggered.connect(lambda: show_git(win))
    win.a_git = a
    view = next((x.menu() for x in win.menuBar().actions() if x.text().replace("&", "") == "View"), None)
    if view is not None:
        view.addAction(a)

    def safe(fn):
        def inner(*a, **k):
            try:
                fn(*a, **k)
            except Exception as e:  # noqa: BLE001 - git problems must never break the IDE
                try:
                    win.log(f"[git] {e}")
                except Exception:  # noqa: BLE001
                    pass
        return inner

    orig_open = win.open_project

    def open_project(*args, **kw):
        r = orig_open(*args, **kw)
        safe(panel.set_project)(background=True)      # git status in a worker thread: never blocks the open
        return r
    win.open_project = open_project

    win.extension_points.add_solution_contributor(       # git colours after every refill
        lambda: safe(lambda: panel.colour_solution(panel._project_states() if panel.git and panel.statuses
                                                   else {}))(), "git")
    win.a_save.triggered.connect(lambda: QTimer.singleShot(300, safe(panel.refresh_async)))
    d.visibilityChanged.connect(lambda vis: vis and safe(panel.refresh_async)())
    # keep the branch / colours current while the IDE is in use (one git status, in the background)
    timer = QTimer(win, interval=5000)
    timer.timeout.connect(lambda: win.isActiveWindow() and panel.git is not None and not panel.is_refreshing()
                          and safe(panel.refresh_async)())
    timer.start()
    win._git_timer = timer


__all__ = ["Git", "GitPanel", "FileStatus", "find_git", "show_git"]
