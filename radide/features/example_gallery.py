# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Example Projects gallery (Help > Example Projects..., Start Page "Example Projects").

Lists the complete example projects in samples/Examples/<Language>/<Name> (every folder with a project.radproj or a
Cargo.toml - any language: C, C++, C#, Java, Go, Rust, Fortran, Python, JavaScript, PHP, Ring, ...), shows the
example's README.md, and opens it as a project (in place, or a copy in a folder the user chooses).
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                             QPushButton, QSplitter, QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout)

try:
    from ..i18n import tr
except Exception:  # noqa: BLE001
    def tr(text, menubar=False):  # type: ignore
        return text

# language folder -> shown name (others are shown as they are)
LANGUAGE_NAMES = {"C": "C", "Cpp": "C++", "CSharp": "C#", "Java": "Java", "Go": "Go", "Rust": "Rust",
                  "Fortran": "Fortran", "VBNet": "VB.NET", "Python": "Python", "PythonQt": "Python (Qt)",
                  "PythonWeb": "Python web", "PythonGames": "Python games", "JavaScript": "JavaScript",
                  "TypeScript": "TypeScript", "NodeWeb": "Node.js web", "PHP": "PHP", "PHPWeb": "PHP web",
                  "Ruby": "Ruby", "RubyWeb": "Ruby web", "Perl": "Perl", "Lua": "Lua", "PowerShell": "PowerShell",
                  "Ring": "Ring", "Dart": "Dart", "Flutter": "Flutter", "Assembly": "Assembly", "DOS": "DOS",
                  "Retro": "Retro", "Web": "Web", "Mobile": "Mobile", "Godot": "Godot"}
SKIP = {"node_modules", "target", "_build", "bin", "obj", "Publish", "__pycache__", ".radide", "build", "dist"}


def examples_root() -> Path | None:
    """samples/Examples next to the IDE (source tree or installed release)."""
    cands = []
    try:
        from ..paths import install_dir, resource_root
        cands += [install_dir() / "samples" / "Examples", resource_root() / "samples" / "Examples"]
    except Exception:  # noqa: BLE001
        pass
    cands.append(Path(__file__).resolve().parents[2] / "samples" / "Examples")
    return next((c for c in cands if c.is_dir()), None)


def readme_summary(folder: Path) -> str:
    """The first paragraph of README.md (without the heading)."""
    p = folder / "README.md"
    if not p.is_file():
        return ""
    lines = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if s.startswith("#") or (not s and not lines):
            continue
        if not s:
            break
        lines.append(s)
    return " ".join(lines)


def discover(root: Path | None = None) -> dict[str, list[Path]]:
    """{language folder: [example project folders]} - folders with project.radproj or Cargo.toml."""
    root = root or examples_root()
    out: dict[str, list[Path]] = {}
    if root is None:
        return out
    for lang in sorted(p for p in root.iterdir() if p.is_dir() and p.name not in SKIP):
        found = [p for p in sorted(lang.iterdir()) if p.is_dir() and p.name not in SKIP
                 and ((p / "project.radproj").is_file() or (p / "Cargo.toml").is_file()
                      or any(p.glob("*.ipynb"))           # notebooks open as a folder (project_detect)
                      or any(p.glob("*.vbproj")) or any(p.glob("*.csproj")))]     # .NET SDK projects (in place)
        if found:
            out[lang.name] = found
    return out


class ExampleGallery(QDialog):
    def __init__(self, win, language: str = ""):
        super().__init__(win)
        self.win = win
        self.setWindowTitle(tr("Example Projects"))
        self.resize(900, 560)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel(tr("Search:")))
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Notepad, Calculator, C#, game ..."))
        self.search.textChanged.connect(self._filter)
        top.addWidget(self.search, 1)
        lay.addLayout(top)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("Example"), tr("Language")])
        self.tree.setColumnWidth(0, 230)
        self.tree.currentItemChanged.connect(self._show)
        self.tree.itemDoubleClicked.connect(lambda it, _c: self._open(copy=False) if it.data(0, 256) else None)
        split.addWidget(self.tree)
        self.readme = QTextBrowser()
        self.readme.setOpenExternalLinks(True)
        split.addWidget(self.readme)
        split.setSizes([320, 580])
        lay.addWidget(split, 1)
        buttons = QDialogButtonBox()
        self.b_open = QPushButton(tr("Open Project"))
        self.b_copy = QPushButton(tr("Copy to... and Open"))
        self.b_folder = QPushButton(tr("Open Folder"))
        for b in (self.b_open, self.b_copy, self.b_folder):
            buttons.addButton(b, QDialogButtonBox.ButtonRole.ActionRole)
            b.setEnabled(False)
        buttons.addButton(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        self.b_open.clicked.connect(lambda: self._open(copy=False))
        self.b_copy.clicked.connect(lambda: self._open(copy=True))
        self.b_folder.clicked.connect(self._open_folder)
        lay.addWidget(buttons)
        self._fill(language)

    def _fill(self, language: str):
        self.tree.clear()
        first = None
        for lang, folders in discover().items():
            top = QTreeWidgetItem([LANGUAGE_NAMES.get(lang, lang), ""])
            top.setFlags(top.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.tree.addTopLevelItem(top)
            for f in folders:
                it = QTreeWidgetItem([tr(f.name), LANGUAGE_NAMES.get(lang, lang)])
                it.setData(0, 256, str(f))
                it.setToolTip(0, readme_summary(f) or str(f))
                top.addChild(it)
                if first is None and (not language or lang.lower() == language.lower()):
                    first = it
            top.setExpanded(not language or lang.lower() == language.lower())
        if first is not None:
            self.tree.setCurrentItem(first)

    def _filter(self, text: str):
        words = text.lower().split()
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            any_shown = False
            for j in range(top.childCount()):
                it = top.child(j)
                hay = " ".join([it.text(0), it.text(1), Path(it.data(0, 256)).name, it.toolTip(0)]).lower()
                show = all(w in hay for w in words)
                it.setHidden(not show)
                any_shown |= show
            top.setHidden(not any_shown)
            top.setExpanded(bool(words) or top.isExpanded())
        cur = self.tree.currentItem()
        if cur is None or cur.isHidden() or (cur.parent() is not None and cur.parent().isHidden()):
            first = next((top.child(j) for i in range(self.tree.topLevelItemCount())
                          for top in [self.tree.topLevelItem(i)] if not top.isHidden()
                          for j in range(top.childCount()) if not top.child(j).isHidden()), None)
            self.tree.setCurrentItem(first)
            if first is None:
                self._show()

    def _current(self) -> Path | None:
        it = self.tree.currentItem()
        return Path(it.data(0, 256)) if it is not None and it.data(0, 256) else None

    def _show(self, *_a):
        f = self._current()
        for b in (self.b_open, self.b_copy, self.b_folder):
            b.setEnabled(f is not None)
        if f is None:
            self.readme.clear()
            return
        p = f / "README.md"
        if p.is_file():
            self.readme.setMarkdown(p.read_text(encoding="utf-8", errors="replace"))
        else:
            self.readme.setPlainText(str(f))

    def _open(self, copy: bool):
        f = self._current()
        if f is None:
            return
        if copy:
            dest_root = QFileDialog.getExistingDirectory(self, tr("Copy the example to"))
            if not dest_root:
                return
            dest = Path(dest_root) / f.name
            if dest.exists():
                QMessageBox.warning(self, tr("Example Projects"), tr("The folder already exists:") + f"\n{dest}")
                return
            shutil.copytree(f, dest, ignore=shutil.ignore_patterns(*SKIP, "*.pyc"))
            f = dest
        self.accept()
        if not (f / "project.radproj").is_file() and not (f / "Cargo.toml").is_file():
            from ..single_instance import open_target      # e.g. a Jupyter notebook folder
            open_target(self.win, f)
            return
        self.win.open_project(f)

    def _open_folder(self):
        f = self._current()
        if f is not None:
            import os
            os.startfile(str(f))  # noqa: S606 - the user asked to see the folder


def show_example_gallery(win, language: str = "") -> None:
    ExampleGallery(win, language).exec()


def _start_page_links(win) -> None:
    try:
        from ..app import StartPage
    except Exception:  # noqa: BLE001
        return
    langs = list(discover())
    if not langs:
        return
    for i in range(win.tabs.count()):
        page = win.tabs.widget(i)
        if isinstance(page, StartPage) and not getattr(page, "_rad_examples", False) and hasattr(page, "add_section"):
            sec = page.add_section(tr("Example Projects"))
            page.add_link(sec, tr("Browse all example projects..."), lambda _=False: show_example_gallery(win),
                          tr("Complete programs (Notepad, Calculator, Contacts, chart, game, settings, console tool) "
                             "in many languages"))
            for lang in [x for x in ("C", "Cpp", "CSharp", "Java", "Go", "Rust", "Fortran") if x in langs]:
                page.add_link(sec, LANGUAGE_NAMES[lang], lambda _=False, l=lang: show_example_gallery(win, l))
            page._rad_examples = True


def install(win) -> None:
    win.show_example_gallery = lambda language="": show_example_gallery(win, language)
    help_menu = next((a.menu() for a in win.menuBar().actions() if a.menu() is not None
                      and a.text().replace("&", "") in ("Help", tr("Help"))), None)
    if help_menu is None:
        help_menu = win.menuBar().addMenu("&Help")
    act = QAction(tr("&Example Projects..."), win)
    act.setToolTip(tr("Complete example projects in every language: open, run (F5) and publish them"))
    act.triggered.connect(lambda: show_example_gallery(win))
    acts = help_menu.actions()
    help_menu.insertAction(acts[3] if len(acts) > 3 else None, act)
    win.a_example_gallery = act
    try:
        _start_page_links(win)
        win.tabs.currentChanged.connect(lambda _i: _start_page_links(win))
    except Exception as e:  # noqa: BLE001
        win.log(f"[Example Projects] start page: {e}")


__all__ = ["ExampleGallery", "discover", "examples_root", "install", "readme_summary", "show_example_gallery"]
