"""Reference Manager like Visual Studio 2022.

Left: the category tree (Assemblies > Framework / Extensions / Recent, Projects > Solution, Shared Projects,
COM > Type Libraries / Recent, Browse > Recent).  Right: the search box (Ctrl+E), a checkable list per page and
the details of the selected entry.  Bottom: Browse..., OK, Cancel.  OK writes every checked / unchecked
entry to the project file (radide/dotnet/refs/edits.py) and reloads the project and its language server.

    dlg = reference_manager(win, project, "com", exec_=False)
    dlg.check("com", "Microsoft Scripting Runtime"); dlg.apply()
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                             QPushButton, QSplitter, QStackedWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)

from . import catalog as CAT
from . import edits as ED

ROLE = Qt.ItemDataRole.UserRole
OFFSCREEN = os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"
RECENT_BROWSE = "dotnet/refs/recentBrowse"
RECENT_ASM = "dotnet/refs/recentAssemblies"
RECENT_COM = "dotnet/refs/recentCom"
MAX_RECENT = 25

# page id, tree path, list columns
PAGES = [
    ("framework", ("Assemblies", "Framework"), ["Name", "Version"]),
    ("extensions", ("Assemblies", "Extensions"), ["Name", "Version"]),
    ("asm_recent", ("Assemblies", "Recent"), ["Name", "Path"]),
    ("projects", ("Projects", "Solution"), ["Name", "Path"]),
    ("shared", ("Shared Projects",), ["Name", "Path"]),
    ("com", ("COM", "Type Libraries"), ["Name", "Version"]),
    ("com_recent", ("COM", "Recent"), ["Name", "Version"]),
    ("browse", ("Browse", "Recent"), ["Name", "Path"]),
]
TAB_ALIASES = {0: "projects", 1: "framework", 2: "browse", 3: "com", 4: "shared", "assemblies": "framework",
               "solution": "projects", "typelibs": "com", "recent": "browse"}


def _settings() -> QSettings:
    return QSettings()


def recent(key: str) -> list[str]:
    try:
        v = _settings().value(key, []) or []
    except Exception:  # noqa: BLE001
        return []
    return [str(x) for x in (v if isinstance(v, list) else [v]) if x]


def remember(key: str, value: str) -> None:
    items = [x for x in recent(key) if x.lower() != value.lower()]
    _settings().setValue(key, [value] + items[: MAX_RECENT - 1])


def _log(win, text: str) -> None:
    try:
        win.log(text)
    except Exception:  # noqa: BLE001
        print(text)


class ReferenceManager(QDialog):
    def __init__(self, win, project, page: str = "framework"):
        super().__init__(win)
        self.win, self.project, self.ms = win, project, project.ms
        self.sln = getattr(win, "sln", None)
        self.setWindowTitle(f"Reference Manager - {project.name}")
        self.resize(900, 560)
        self.pages: dict[str, QTreeWidget] = {}
        self.page_widgets: dict[str, QWidget] = {}
        self.notes: dict[str, QLabel] = {}
        self._loaded: set[str] = set()
        self._initial: dict[tuple[str, str], bool] = {}
        self.changes: list[str] = []
        self.netfx = self.ms.is_netframework
        cpp = self.ms.language == "C++"

        lay = QVBoxLayout(self)
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split, 1)
        self.nav = QTreeWidget()
        self.nav.setHeaderHidden(True)
        self.nav.setMinimumWidth(170)
        self.nav.setMaximumWidth(240)
        split.addWidget(self.nav)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 0, 0, 0)
        top = QHBoxLayout()
        self.heading = QLabel()
        self.heading.setStyleSheet("font-weight: bold;")
        top.addWidget(self.heading, 1)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search (Ctrl+E)")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(260)
        self.search.textChanged.connect(lambda _t: self._filter())
        top.addWidget(self.search)
        rl.addLayout(top)
        body = QSplitter(Qt.Orientation.Horizontal)
        self.stack = QStackedWidget()
        body.addWidget(self.stack)
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.details.setMinimumWidth(200)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.details.setProperty("radRole", "help")
        body.addWidget(self.details)
        body.setStretchFactor(0, 3)
        body.setStretchFactor(1, 1)
        rl.addWidget(body, 1)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        split.setSizes([190, 710])
        QShortcut(QKeySequence("Ctrl+E"), self, activated=lambda: (self.search.setFocus(), self.search.selectAll()))

        groups: dict[str, QTreeWidgetItem] = {}
        for pid, path, cols in PAGES:
            if cpp and pid not in ("projects", "shared", "browse"):
                continue
            parent = None
            for depth, label in enumerate(path[:-1]):
                key = "/".join(path[: depth + 1])
                if key not in groups:
                    it = QTreeWidgetItem([label])
                    (parent.addChild(it) if parent else self.nav.addTopLevelItem(it))
                    it.setData(0, ROLE, "")
                    groups[key] = it
                parent = groups[key]
            node = QTreeWidgetItem([path[-1]])
            node.setData(0, ROLE, pid)
            (parent.addChild(node) if parent else self.nav.addTopLevelItem(node))
            self._make_page(pid, cols)
        self.nav.expandAll()
        self.nav.currentItemChanged.connect(lambda cur, _p: self._nav_changed(cur))

        bottom = QHBoxLayout()
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse)
        bottom.addStretch(1)
        bottom.addWidget(self.browse_btn)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        bottom.addWidget(box)
        lay.addLayout(bottom)
        self.select_page(TAB_ALIASES.get(page, page) if page is not None else "framework")

    # ------------------------------------------------------------ pages
    def _make_page(self, pid: str, cols: list[str]) -> None:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        note = QLabel()
        note.setWordWrap(True)
        note.setVisible(False)
        note.setProperty("radRole", "help")
        v.addWidget(note)
        t = QTreeWidget()
        t.setColumnCount(len(cols))
        t.setHeaderLabels(cols)
        t.setRootIsDecorated(False)
        t.setColumnWidth(0, 300)
        t.setSortingEnabled(True)
        t.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        t.currentItemChanged.connect(lambda cur, _p: self._show_details(cur))
        t.itemDoubleClicked.connect(lambda it, _c: it.setCheckState(0, Qt.CheckState.Unchecked if
                                                                     it.checkState(0) == Qt.CheckState.Checked
                                                                     else Qt.CheckState.Checked)
                                    if it.flags() & Qt.ItemFlag.ItemIsUserCheckable else None)
        v.addWidget(t, 1)
        self.pages[pid] = t
        self.notes[pid] = note
        self.page_widgets[pid] = w
        self.stack.addWidget(w)

    def select_page(self, pid: str) -> None:
        it = self._nav_item(pid)
        if it is None:
            it = self._nav_item("projects") or self.nav.topLevelItem(0)
        self.nav.setCurrentItem(it)
        self._nav_changed(it)

    def _nav_item(self, pid: str):
        stack = [self.nav.topLevelItem(i) for i in range(self.nav.topLevelItemCount())]
        while stack:
            it = stack.pop()
            if it.data(0, ROLE) == pid:
                return it
            stack.extend(it.child(i) for i in range(it.childCount()))
        return None

    def _nav_changed(self, item) -> None:
        if item is None:
            return
        pid = item.data(0, ROLE)
        if not pid:
            if item.childCount():
                self.nav.setCurrentItem(item.child(0))
            return
        self.current = pid
        self._ensure(pid)
        self.stack.setCurrentWidget(self.page_widgets[pid])
        path = next(p for i, p, _c in PAGES if i == pid)
        self.heading.setText(" > ".join(path))
        self.browse_btn.setVisible(True)
        self._filter()
        t = self.pages[pid]
        self._show_details(t.currentItem())

    def _note(self, pid: str, text: str) -> None:
        n = self.notes[pid]
        n.setText(text)
        n.setVisible(bool(text))

    def _row(self, pid: str, key: str, cols: list[str], checked: bool, data: dict, enabled: bool = True,
             tip: str = "") -> QTreeWidgetItem:
        t = self.pages[pid]
        t.setSortingEnabled(False)
        it = QTreeWidgetItem(cols)
        flags = it.flags() | Qt.ItemFlag.ItemIsUserCheckable
        if not enabled:
            flags &= ~Qt.ItemFlag.ItemIsEnabled
        it.setFlags(flags)
        it.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        data = dict(data, key=key, page=pid)
        it.setData(0, ROLE, data)
        if tip:
            it.setToolTip(0, tip)
        t.addTopLevelItem(it)
        t.setSortingEnabled(True)
        if enabled:
            self._initial[(pid, key)] = checked
        return it

    def _ensure(self, pid: str) -> None:
        if pid in self._loaded:
            return
        self._loaded.add(pid)
        try:
            getattr(self, f"_load_{pid}")()
        except Exception as e:  # noqa: BLE001
            self._note(pid, f"Could not list the entries of this page: {e}")
        t = self.pages[pid]
        if t.topLevelItemCount() and t.currentItem() is None:
            t.setCurrentItem(t.topLevelItem(0))

    # ----- Assemblies
    def _load_framework(self) -> None:
        if self.netfx:
            ver = CAT.project_netfx_version(self.ms)
            entries = CAT.framework_assemblies(ver)
            if not entries:
                self._note("framework", f"The reference assemblies of .NET Framework {ver.lstrip('v')} are not "
                                        "installed (Visual Studio Installer > .NET Framework targeting pack, or "
                                        "the Microsoft.NETFramework.ReferenceAssemblies NuGet package).")
            else:
                self._note("framework", f"Targeting: .NET Framework {ver.lstrip('v')}")
            for e in entries:
                self._row("framework", e.name.lower(), [e.name, e.version], ED.has_assembly(self.ms, e.name),
                          {"kind": "assembly", "name": e.name, "path": e.path, "version": e.version})
            return
        tfm = ", ".join(self.ms.target_frameworks) or "?"
        self._note("framework", f"All Framework assemblies are already referenced for {tfm}: an SDK-style project "
                                "references its shared frameworks implicitly. Please use the Object Browser to "
                                "explore the references in the Framework. Below, a shared framework can be added "
                                "with a FrameworkReference.")
        implicit = CAT.implicit_frameworks(self.ms)
        explicit = {it.include.lower() for it in self.ms.explicit("FrameworkReference")}
        for name, desc, _pack in CAT.SHARED_FRAMEWORKS:
            is_implicit = name in implicit and name.lower() not in explicit
            self._row("framework", name.lower(), [name, "implicit" if is_implicit else ""],
                      name in implicit or name.lower() in explicit,
                      {"kind": "frameworkref", "name": name, "desc": desc},
                      enabled=not is_implicit, tip=desc)

    def _load_extensions(self) -> None:
        entries = CAT.extension_assemblies()
        if not entries:
            self._note("extensions", "No extension assemblies are registered (AssemblyFoldersEx).")
        elif not self.netfx:
            self._note("extensions", "Extension assemblies target the .NET Framework; an SDK-style project can "
                                     "reference one with a HintPath (it may not run on .NET).")
        for e in entries:
            self._row("extensions", e.name.lower(), [e.name, e.version], ED.has_assembly(self.ms, e.name),
                      {"kind": "browse", "name": e.name, "path": e.path, "source": e.source})

    def _load_asm_recent(self) -> None:
        for p in recent(RECENT_ASM):
            if Path(p).is_file():
                self._row("asm_recent", p.lower(), [Path(p).stem, p], ED.has_assembly(self.ms, Path(p).stem),
                          {"kind": "browse", "name": Path(p).stem, "path": p})

    # ----- Projects
    def _project_refs(self) -> set[str]:
        return {os.path.normcase(str((self.ms.folder / ED.xml_unescape(i.include).replace("\\", "/")).resolve()))
                for i in self.ms.project_references}

    def _load_projects(self) -> None:
        sln = self.sln
        others = [p for p in (sln.all_projects() if sln is not None and hasattr(sln, "all_projects") else [])
                  if p is not self.project]
        have = self._project_refs()
        if not others:
            self._note("projects", "There are no other projects in this solution.")
        for other in others:
            key = os.path.normcase(str(other.ms.path))
            name = sln.name_of(other) if hasattr(sln, "name_of") else other.name
            self._row("projects", key, [name, str(other.ms.path)], key in have,
                      {"kind": "project", "name": name, "project": other, "path": str(other.ms.path)})

    def _shared_projects(self) -> list[Path]:
        """.shproj files of the solution (the shared-projects module first, then the .sln, then the folder)."""
        found: dict[str, Path] = {}
        SM = _shared_model()
        model = getattr(self.sln, "model", None)
        if SM is not None and model is not None:
            try:
                for sp in SM.solution_shared_projects(model):
                    ok, _why = SM.can_reference(self.ms.path, sp)
                    if ok:
                        found[os.path.normcase(str(sp.path))] = Path(sp.path)
            except Exception:  # noqa: BLE001
                pass
        if model is not None and SM is None:
            for e in getattr(model, "entries", []):
                if str(e.path).lower().endswith(".shproj"):
                    p = (model.folder / e.path).resolve()
                    found[os.path.normcase(str(p))] = p
        base = getattr(self.sln, "folder", None) or self.ms.folder.parent
        try:
            for p in Path(base).glob("*/*.shproj"):
                found.setdefault(os.path.normcase(str(p.resolve())), p.resolve())
            for p in Path(base).glob("*.shproj"):
                found.setdefault(os.path.normcase(str(p.resolve())), p.resolve())
        except OSError:
            pass
        return sorted(found.values(), key=lambda p: p.stem.lower())

    def _load_shared(self) -> None:
        imports = {os.path.normcase(str((self.ms.folder / ED.xml_unescape(i).replace("\\", "/")).resolve()))
                   for i in ED.shared_imports(self.ms)}
        shp = self._shared_projects()
        if not shp:
            self._note("shared", "No shared projects found in this solution (Add > New Project > Shared Project).")
        for p in shp:
            items, why = p.with_suffix(".projitems"), ""
            try:
                from ..shared import model as shared_model
                sp = shared_model.SharedProject(p)
                items = Path(sp.projitems_path)
                ok, why = shared_model.can_reference(self.ms.path, sp)
                if ok:
                    why = ""
            except Exception:  # noqa: BLE001 - shared module missing: plain <Name>.projitems next to it
                pass
            if not items.is_file():
                why = f"{items.name} not found"
            key = os.path.normcase(str(items))
            self._row("shared", key, [p.stem, str(p)], key in imports,
                      {"kind": "shared", "name": p.stem, "path": str(items), "shproj": str(p)},
                      enabled=not why, tip=why)

    # ----- COM
    def _com_have(self) -> set[str]:
        return {it.metadata.get("Guid", "").strip("{}").lower() for it in self.ms.explicit("COMReference")}

    def _com_note(self, pid: str) -> None:
        from ...foreign.msbuild import find_msbuild, msbuild_is_full
        msb = find_msbuild()
        if self.ms.is_sdk and not (msb and msbuild_is_full(msb)):
            self._note(pid, "COM references are built by tlbimp (ResolveComReference), which 'dotnet build' "
                            "does not support: building this project needs Visual Studio's MSBuild.")
        elif self.ms.is_sdk:
            self._note(pid, "COM references are built with Visual Studio's MSBuild (found).")

    def _load_com(self) -> None:
        have = self._com_have()
        self._com_note("com")
        for e in CAT.com_type_libraries():
            key = f"{e.guid}|{e.major}.{e.minor}"
            self._row("com", key, [e.name, e.version_text], e.guid in have,
                      {"kind": "com", "name": e.name, "entry": e, "path": e.path})

    def _load_com_recent(self) -> None:
        have = self._com_have()
        self._com_note("com_recent")
        libs = None
        for rec in recent(RECENT_COM):
            guid, _, ver = rec.partition("|")
            if libs is None:
                libs = CAT.com_type_libraries()
            e = next((x for x in libs if x.guid == guid and f"{x.major}.{x.minor}" == ver), None)
            if e is not None:
                self._row("com_recent", rec, [e.name, e.version_text], e.guid in have,
                          {"kind": "com", "name": e.name, "entry": e, "path": e.path})

    # ----- Browse
    def _load_browse(self) -> None:
        refs = {os.path.normcase(str((self.ms.folder / ED.xml_unescape(i.metadata.get("HintPath", ""))
                                      .replace("\\", "/")).resolve()))
                for i in self.ms.explicit("Reference") if i.metadata.get("HintPath")}
        for p in recent(RECENT_BROWSE):
            if Path(p).is_file():
                self._row("browse", os.path.normcase(p), [Path(p).name, p], os.path.normcase(p) in refs,
                          {"kind": "browse", "name": Path(p).stem, "path": p})

    def add_browse_file(self, path, checked: bool = True) -> QTreeWidgetItem | None:
        """Browse... picked a file: validate it and list it checked on the Browse page."""
        p = Path(path).resolve()
        self._ensure("browse")
        try:
            info = ED.browse_reference_check(p)
        except ED.BrowseError as e:
            self._warn(str(e))
            return None
        if not info["managed"]:
            msg = (f"'{p.name}' is a native DLL, not a .NET assembly, so it cannot be referenced.\n\n"
                   ".NET code calls functions of a native DLL with [DllImport(\"" + p.name + "\")] (P/Invoke), "
                   "and the DLL must be next to the program at run time.\n\n"
                   "Copy it to the output directory (adds it to the project with "
                   "CopyToOutputDirectory=PreserveNewest)?")
            if self._ask(msg):
                if ED.add_native_copy(self.ms, p):
                    self.changes.append(f"+{p.name} (copy to output)")
            return None
        key = os.path.normcase(str(p))
        t = self.pages["browse"]
        for i in range(t.topLevelItemCount()):
            it = t.topLevelItem(i)
            if (it.data(0, ROLE) or {}).get("key") == key:
                it.setCheckState(0, Qt.CheckState.Checked)
                return it
        it = self._row("browse", key, [p.name, str(p)], False,
                       {"kind": "browse", "name": info["identity"].get("name", p.stem), "path": str(p)})
        if checked:
            it.setCheckState(0, Qt.CheckState.Checked)
        return it

    def browse(self) -> list[str]:
        files, _ = QFileDialog.getOpenFileNames(self, "Select the files to reference...", str(self.ms.folder),
                                                "Component Files (*.dll;*.tlb;*.olb;*.ocx;*.exe;*.manifest;*.winmd)"
                                                ";;All Files (*.*)")
        for f in files:
            if f.lower().endswith((".tlb", ".olb", ".ocx")):
                self._warn("Type library files are added from the COM page (registered type libraries).")
                continue
            self.add_browse_file(f)
        if files:
            self.select_page("browse")
        return files

    # ------------------------------------------------------------ helpers
    def _warn(self, text: str) -> None:
        _log(self.win, f"*** Reference Manager: {text}")
        QMessageBox.warning(self, "Reference Manager", text)

    def _ask(self, text: str) -> bool:
        return QMessageBox.question(self, "Reference Manager", text) == QMessageBox.StandardButton.Yes

    def _filter(self) -> None:
        pid = getattr(self, "current", None)
        if pid is None:
            return
        q = self.search.text().strip().lower()
        t = self.pages[pid]
        first = None
        for i in range(t.topLevelItemCount()):
            it = t.topLevelItem(i)
            text = " ".join(it.text(c) for c in range(t.columnCount())).lower()
            it.setHidden(bool(q) and q not in text)
            if first is None and not it.isHidden():
                first = it
        cur = t.currentItem()
        if cur is None or cur.isHidden():
            t.setCurrentItem(first)
            self._show_details(first)

    def _show_details(self, it) -> None:
        if it is None:
            self.details.setText("")
            return
        d = it.data(0, ROLE) or {}
        lines = [f"<b>Name:</b><br>{d.get('name', it.text(0))}"]
        path = d.get("path", "")
        kind = d.get("kind")
        if kind in ("assembly", "browse") and path:
            try:
                from .metadata import assembly_identity
                ident = assembly_identity(path)
                lines.append(f"<b>Version:</b><br>{ident['version']}")
                if ident.get("framework"):
                    lines.append(f"<b>Target framework:</b><br>{ident['framework']}")
                lines.append(f"<b>Strong name:</b><br>{'Yes' if ident.get('token') else 'No'}")
                if not it.text(1) and self.pages.get(d.get("page")) is not None and d.get("page") == "extensions":
                    it.setText(1, ident["version"])
            except Exception:  # noqa: BLE001
                pass
        elif kind == "com":
            e = d["entry"]
            lines.append(f"<b>Version:</b><br>{e.version_text}")
            lines.append(f"<b>Guid:</b><br>{{{e.guid}}}")
        elif kind == "frameworkref":
            lines.append(d.get("desc", ""))
        if d.get("source"):
            lines.append(f"<b>Created by:</b><br>{d['source']}")
        if path:
            lines.append(f"<b>File:</b><br>{path}")
        self.details.setText("<br><br>".join(lines))

    def check(self, pid: str, name: str, on: bool = True) -> bool:
        """Tick an entry by its name (or key) - for tests and automation."""
        self._ensure(pid)
        t = self.pages[pid]
        low = name.lower()
        for i in range(t.topLevelItemCount()):
            it = t.topLevelItem(i)
            d = it.data(0, ROLE) or {}
            if it.text(0).lower() == low or str(d.get("key", "")).lower() == low or \
                    str(d.get("name", "")).lower() == low:
                if not it.flags() & Qt.ItemFlag.ItemIsEnabled:
                    return False
                it.setCheckState(0, Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
                return True
        return False

    # ------------------------------------------------------------ apply
    def apply(self) -> list[str]:
        ms = self.ms
        changes = list(self.changes)
        for pid in list(self._loaded):
            t = self.pages[pid]
            for i in range(t.topLevelItemCount()):
                it = t.topLevelItem(i)
                if not it.flags() & Qt.ItemFlag.ItemIsEnabled:
                    continue
                d = it.data(0, ROLE) or {}
                on = it.checkState(0) == Qt.CheckState.Checked
                was = self._initial.get((pid, d.get("key")), False)
                if on == was:
                    continue
                try:
                    msg = self._apply_one(d, on)
                except ED.BrowseError as e:
                    self._warn(str(e))
                    continue
                if msg:
                    changes.append(msg)
        self.changes = []
        if changes:
            ED.commit(self.win, self.project)
            _log(self.win, f"{self.project.name}: references {' '.join(changes)} ({ms.path.name} updated)")
        return changes

    def _apply_one(self, d: dict, on: bool) -> str:
        kind, name, ms = d.get("kind"), d.get("name", ""), self.ms
        if kind == "assembly":
            if on and ED.add_framework_assembly(ms, name):
                return f"+{name}"
            if not on and ED.remove_assembly(ms, name):
                return f"-{name}"
        elif kind == "frameworkref":
            if on and ED.add_framework_reference(ms, name):
                return f"+{name}"
            if not on and ED.remove_framework_reference(ms, name):
                return f"-{name}"
        elif kind == "browse":
            if on:
                changed, _inc = ED.add_browse_reference(ms, d["path"])
                remember(RECENT_BROWSE, str(Path(d["path"]).resolve()))
                remember(RECENT_ASM, str(Path(d["path"]).resolve()))
                return f"+{Path(d['path']).name}" if changed else ""
            if ED.remove_assembly(ms, name):
                return f"-{name}"
        elif kind == "project":
            other = d["project"]
            if on:
                if self._circular(other):
                    self._warn(f"A reference to '{other.name}' could not be added. Adding this project as a "
                               "reference would cause a circular dependency.")
                    return ""
                ok = ms.add_project_reference(other.ms.path, other.ms.prop("ProjectGuid"), other.ms.name)
                return f"+{other.name}" if ok else ""
            for r in ms.project_references:
                target = os.path.normcase(str((ms.folder / ED.xml_unescape(r.include).replace("\\", "/")).resolve()))
                if target == os.path.normcase(str(other.ms.path)) and ms.remove_item("ProjectReference", r.include):
                    return f"-{other.name}"
        elif kind == "shared":
            SM = _shared_model()
            if SM is not None and d.get("shproj"):         # the Shared Projects module writes the import
                sp = SM.SharedProject(Path(d["shproj"]))
                ED.retry_io(ms.save)
                try:
                    ok = ED.retry_io(SM.add_shared_reference if on else SM.remove_shared_reference, ms.path, sp)
                except ValueError as e:
                    raise ED.BrowseError(str(e)) from None
                ms.reload()
                return f"{'+' if on else '-'}{name} (shared)" if ok else ""
            if on and ED.add_shared_import(ms, d["path"]):
                return f"+{name} (shared)"
            if not on:
                inc = next((i for i in ED.shared_imports(ms)
                            if os.path.normcase(str((ms.folder / ED.xml_unescape(i).replace("\\", "/")).resolve()))
                            == os.path.normcase(d["path"])), None)
                if inc and ED.remove_shared_import(ms, inc):
                    return f"-{name} (shared)"
        elif kind == "com":
            e = d["entry"]
            if on:
                changed, inc = ED.add_com_reference(ms, e)
                remember(RECENT_COM, f"{e.guid}|{e.major}.{e.minor}")
                return f"+{inc} (COM)" if changed else ""
            inc = next((it.include for it in ms.explicit("COMReference")
                        if it.metadata.get("Guid", "").strip("{}").lower() == e.guid), None)
            if inc and ED.remove_com_reference(ms, inc):
                return f"-{inc} (COM)"
        return ""

    def _circular(self, other) -> bool:
        mine = os.path.normcase(str(self.ms.path))
        seen, stack = set(), [other]
        while stack:
            p = stack.pop()
            key = os.path.normcase(str(p.ms.path))
            if key in seen:
                continue
            seen.add(key)
            for r in p.ms.project_references:
                target = os.path.normcase(str((p.ms.folder / ED.xml_unescape(r.include).replace("\\", "/")).resolve()))
                if target == mine:
                    return True
                nxt = None
                for q in (self.sln.all_projects() if self.sln is not None and hasattr(self.sln, "all_projects")
                          else []):
                    if os.path.normcase(str(q.ms.path)) == target:
                        nxt = q
                if nxt is not None:
                    stack.append(nxt)
        return False


def _shared_model():
    """radide/dotnet/shared/model.py (the Shared Projects slice) or None."""
    try:
        from ..shared import model as SM
        return SM
    except Exception:  # noqa: BLE001
        return None


def reference_manager(win, project, tab=0, exec_: bool = True):
    """vs_ui.add_reference_dialog: the dialog (exec_=False) or the list of changes after OK."""
    dlg = ReferenceManager(win, project, TAB_ALIASES.get(tab, tab))
    if not exec_:
        return dlg
    if dlg.exec():
        return dlg.apply()
    if dlg.changes:                  # a native DLL copied before Cancel: keep the project consistent
        dlg.changes = []
        ED.commit(win, project)
    return None


__all__ = ["ReferenceManager", "reference_manager", "recent", "remember", "PAGES"]
