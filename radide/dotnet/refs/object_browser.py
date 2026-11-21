"""Object Browser (View > Object Browser, Ctrl+Alt+J) like Visual Studio.

Browse: My Solution (every assembly the solution's projects reference: framework / extension / browsed
assemblies, project outputs, NuGet package assemblies, the SDK shared frameworks) or Custom Component Set
(assemblies added with "..." ).  Left: assemblies > namespaces > types (> nested types); right top: members;
right bottom: the declaration and the XML documentation summary (from the .xml next to the dll).  Search
(Enter) lists matching types and members.  Go To Definition (F12 / double-click) opens the decompiled type
(ilspycmd, installed from nuget.org on request) or a metadata-as-source stub.
"""
from __future__ import annotations

import html
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (QApplication, QComboBox, QDockWidget, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMenu, QMessageBox, QSplitter, QStyle, QTextBrowser,
                             QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import catalog as CAT
from . import metadata as MD

ROLE = Qt.ItemDataRole.UserRole
OFFSCREEN = os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"
CUSTOM_KEY = "dotnet/objectBrowser/custom"
KIND_BADGE = {"Class": ("C", "#C27D1A"), "Interface": ("I", "#1C6FB8"), "Struct": ("S", "#2E8B57"),
              "Enum": ("E", "#B8860B"), "Delegate": ("D", "#8E44AD"), "Method": ("M", "#6A3D9A"),
              "Constructor": ("M", "#6A3D9A"), "Property": ("P", "#4F5B66"), "Field": ("F", "#1F7AB8"),
              "Event": ("Ev", "#D49A00"), "Constant": ("K", "#1F7AB8"), "EnumValue": ("e", "#B8860B"),
              "Operator": ("+", "#6A3D9A"), "Namespace": ("{}", "#555555"), "Assembly": ("A", "#6B6B6B"),
              "Framework": ("Fx", "#512BD4")}
_POOL = ThreadPoolExecutor(max_workers=1)


# ====================================================================== what "My Solution" contains
def solution_assemblies(sln) -> list[tuple[str, str]]:
    """(group, path): referenced assemblies of every project, de-duplicated, framework packs last."""
    out: dict[str, tuple[str, str]] = {}
    frameworks: dict[str, tuple[str, str]] = {}
    projects = sln.all_projects() if sln is not None and hasattr(sln, "all_projects") else []
    for p in projects:
        ms = getattr(p, "ms", None)
        if ms is None or ms.language == "C++":
            continue
        out.update(_project_assemblies(p, frameworks))
    res = sorted(out.values(), key=lambda gp: Path(gp[1]).stem.lower())
    return res + sorted(frameworks.values())


def _project_assemblies(project, frameworks: dict) -> dict[str, tuple[str, str]]:
    ms = project.ms
    out: dict[str, tuple[str, str]] = {}

    def add(group, path):
        if path and Path(path).is_file() and Path(path).suffix.lower() in (".dll", ".exe", ".winmd"):
            out.setdefault(os.path.normcase(str(Path(path).resolve())), (group, str(Path(path).resolve())))
    for it in ms.explicit("Reference"):
        add("Assemblies", CAT.resolve_reference_path(ms, "Reference", it.include, it.metadata))
    for it in ms.explicit("COMReference"):                 # the interop assembly after a build
        for cand in (ms.folder / "obj").rglob(f"Interop.{it.include}.dll") if (ms.folder / "obj").is_dir() else []:
            add("COM", str(cand))
            break
    for it in ms.explicit("ProjectReference"):
        target = (ms.folder / it.include.replace("\\", "/")).resolve()
        try:
            from ...foreign.msbuild import MSBuildProject, guess_target_path
            other = MSBuildProject.load(target)
            add("Projects", str(guess_target_path(other)))
        except Exception:  # noqa: BLE001
            pass
    try:
        from ...foreign.msbuild import guess_target_path
        add("Projects", str(guess_target_path(ms)))                 # the project's own output, when built
    except Exception:  # noqa: BLE001
        pass
    for it in ms.explicit("PackageReference"):
        for dll in package_assemblies(it.include, it.metadata.get("Version", ""), ms.target_frameworks):
            add("Packages", dll)
    if ms.is_netframework:
        d = CAT.netfx_folder(CAT.project_netfx_version(ms))
        if d is not None:
            add("Assemblies", str(d / "mscorlib.dll"))
    else:
        tfm = (ms.target_frameworks or [""])[0]
        for fw in CAT.implicit_frameworks(ms):
            pack = next((pk for n, _d, pk in CAT.SHARED_FRAMEWORKS if n == fw), fw + ".Ref")
            d = CAT.ref_pack_folder(pack, tfm)
            if d is not None:
                frameworks.setdefault(os.path.normcase(str(d)), ("Framework", str(d)))
    return out


def package_assemblies(name: str, version: str, tfms: list[str]) -> list[str]:
    root = Path(os.environ.get("NUGET_PACKAGES") or Path.home() / ".nuget" / "packages") / name.lower()
    if not root.is_dir():
        return []
    vdir = root / version if version and (root / version).is_dir() else None
    if vdir is None:
        vers = sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: CAT._vkey(p.name), reverse=True)
        vdir = vers[0] if vers else None
    if vdir is None:
        return []
    for sub in ("ref", "lib"):
        base = vdir / sub
        if not base.is_dir():
            continue
        dirs = sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: p.name)
        if not dirs:
            continue
        pick = None
        for tfm in tfms or []:
            pick = next((d for d in dirs if d.name == tfm), None) or \
                next((d for d in dirs if tfm.startswith(d.name)), None)
            if pick:
                break
        pick = pick or next((d for d in reversed(dirs) if d.name.startswith(("net8", "net9", "net6", "netstandard2"))),
                            dirs[-1])
        dlls = [str(p) for p in sorted(pick.glob("*.dll"))]
        if dlls:
            return dlls
    return []


# ====================================================================== the tool window
class ObjectBrowser(QWidget):
    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win = win
        self.show_private = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Browse:"))
        self.scope = QComboBox()
        self.scope.addItems(["My Solution", "Custom Component Set"])
        self.scope.currentIndexChanged.connect(lambda _i: self.reload())
        bar.addWidget(self.scope)
        self.add_btn = QToolButton(text="...")
        self.add_btn.setToolTip("Edit Custom Component Set (add assemblies)")
        self.add_btn.clicked.connect(self.add_custom)
        bar.addWidget(self.add_btn)
        self.settings_btn = QToolButton(text="Settings")
        menu = QMenu(self.settings_btn)
        self.a_private = menu.addAction("Show Private Members", self._toggle_private)
        self.a_private.setCheckable(True)
        self.settings_btn.setMenu(menu)
        self.settings_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        bar.addWidget(self.settings_btn)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search <Ctrl+K>")
        self.search.setClearButtonEnabled(True)
        self.search.returnPressed.connect(self.do_search)
        self.search.textChanged.connect(lambda t: (not t) and self._show_tree())
        bar.addWidget(self.search, 1)
        lay.addLayout(bar)
        QShortcut(QKeySequence("Ctrl+K"), self, activated=lambda: (self.search.setFocus(), self.search.selectAll()))

        split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemExpanded.connect(self._expand)
        self.tree.currentItemChanged.connect(lambda cur, _p: self._select(cur))
        self.tree.itemDoubleClicked.connect(lambda it, _c: self.goto_definition(it))
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(lambda pos: self._menu(self.tree, pos))
        self.results = QListWidget()
        self.results.setVisible(False)
        self.results.currentItemChanged.connect(lambda cur, _p: self._select_result(cur))
        self.results.itemDoubleClicked.connect(lambda it: self.goto_definition(it))
        ll.addWidget(self.tree)
        ll.addWidget(self.results)
        split.addWidget(left)
        rsplit = QSplitter(Qt.Orientation.Vertical)
        self.members = QListWidget()
        self.members.currentItemChanged.connect(lambda cur, _p: self._select_member(cur))
        self.members.itemDoubleClicked.connect(lambda it: self.goto_definition(it))
        self.members.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.members.customContextMenuRequested.connect(lambda pos: self._menu(self.members, pos))
        rsplit.addWidget(self.members)
        self.desc = QTextBrowser()
        self.desc.setOpenLinks(False)
        rsplit.addWidget(self.desc)
        rsplit.setStretchFactor(0, 3)
        rsplit.setStretchFactor(1, 2)
        split.addWidget(rsplit)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 3)
        lay.addWidget(split, 1)
        QShortcut(QKeySequence("F12"), self, activated=lambda: self.goto_definition(self._current_node()))
        self.reload()

    # ------------------------------------------------------------ assemblies
    def _icon(self, kind: str):
        try:
            from ...icons import badge
            text, colour = KIND_BADGE.get(kind, ("?", "#777777"))
            return badge(text, colour, 16)
        except Exception:  # noqa: BLE001
            return self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)

    def custom(self) -> list[str]:
        v = QSettings().value(CUSTOM_KEY, []) or []
        return [str(x) for x in (v if isinstance(v, list) else [v]) if x]

    def add_custom(self, files: list[str] | None = None) -> None:
        if files is None:
            files, _ = QFileDialog.getOpenFileNames(self, "Add to Custom Component Set", "",
                                                    "Assemblies (*.dll *.exe *.winmd)")
        cur = self.custom()
        for f in files or []:
            if f not in cur and MD.is_managed(f):
                cur.append(f)
        QSettings().setValue(CUSTOM_KEY, cur)
        self.scope.setCurrentIndex(1)
        self.reload()

    def assemblies(self) -> list[tuple[str, str]]:
        if self.scope.currentIndex() == 1:
            return [("Custom", p) for p in self.custom() if Path(p).is_file()]
        return solution_assemblies(getattr(self.win, "sln", None))

    def reload(self) -> None:
        self.tree.clear()
        self.members.clear()
        self.desc.clear()
        for group, path in self.assemblies():
            p = Path(path)
            if p.is_dir():                                    # a shared framework reference pack
                fw = p.parent.parent.parent.name.replace(".Ref", "")
                it = QTreeWidgetItem([f"{fw} ({p.parent.parent.name})"])
                it.setIcon(0, self._icon("Framework"))
                it.setData(0, ROLE, ("framework", str(p)))
                it.setToolTip(0, str(p))
                it.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
                self.tree.addTopLevelItem(it)
                continue
            self._assembly_item(None, str(p), group)

    def _assembly_item(self, parent, path: str, group: str = ""):
        it = QTreeWidgetItem([Path(path).stem])
        it.setIcon(0, self._icon("Assembly"))
        it.setData(0, ROLE, ("assembly", path))
        it.setToolTip(0, f"{path}" + (f"\n{group}" if group else ""))
        it.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        (parent.addChild(it) if parent is not None else self.tree.addTopLevelItem(it))
        return it

    def _expand(self, it) -> None:
        d = it.data(0, ROLE)
        if not d or it.childCount():
            return
        kind = d[0]
        if kind == "framework":
            for dll in sorted(Path(d[1]).glob("*.dll")):
                self._assembly_item(it, str(dll))
        elif kind == "assembly":
            try:
                asm = MD.read_assembly(d[1])
            except Exception as e:  # noqa: BLE001
                bad = QTreeWidgetItem([f"(cannot read: {e})"])
                it.addChild(bad)
                return
            for ns, types in asm.namespaces(not self.show_private).items():
                n = QTreeWidgetItem([ns or "-"])
                n.setIcon(0, self._icon("Namespace"))
                n.setData(0, ROLE, ("namespace", d[1], ns))
                it.addChild(n)
                for t in types:
                    self._type_item(n, t)
        elif kind == "type":
            pass
        it.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicatorWhenChildless)

    def _type_item(self, parent, t: MD.TypeMeta):
        ti = QTreeWidgetItem([t.display])
        ti.setIcon(0, self._icon(t.kind))
        ti.setData(0, ROLE, ("type", t))
        ti.setToolTip(0, t.cs_name)
        parent.addChild(ti)
        for nt in sorted(t.nested, key=lambda x: x.display.lower()):
            if self.show_private or nt.is_public:
                self._type_item(ti, nt)
        return ti

    def _toggle_private(self) -> None:
        self.show_private = self.a_private.isChecked()
        self.reload()

    # ------------------------------------------------------------ selection
    def _select(self, it) -> None:
        if it is None:
            return
        d = it.data(0, ROLE)
        if not d:
            return
        if d[0] == "type":
            self.show_type(d[1])
        elif d[0] == "assembly":
            self.members.clear()
            try:
                a = MD.read_assembly(d[1])
                refs = ", ".join(r.name for r in a.references[:12]) + (" ..." if len(a.references) > 12 else "")
                self.desc.setHtml(f"<b>Assembly {html.escape(a.name)}</b><br>{html.escape(a.path.as_posix())}"
                                  f"<br><br>{html.escape(a.identity)}"
                                  + (f"<br>Target framework: {html.escape(a.target_framework)}"
                                     if a.target_framework else "")
                                  + f"<br>Runtime: {html.escape(a.runtime_version)} | {html.escape(a.machine)}"
                                  + (f"<br><br>References: {html.escape(refs)}" if refs else ""))
            except Exception as e:  # noqa: BLE001
                self.desc.setPlainText(str(e))
        elif d[0] == "namespace":
            self.members.clear()
            self.desc.setHtml(f"namespace <b>{html.escape(d[2])}</b><br>Member of {html.escape(Path(d[1]).stem)}")
        elif d[0] == "framework":
            self.members.clear()
            self.desc.setHtml(f"<b>{html.escape(it.text(0))}</b><br>{html.escape(d[1])}<br><br>"
                              "The reference assemblies of a shared framework (implicit in SDK-style projects).")

    def show_type(self, t: MD.TypeMeta) -> None:
        self.members.clear()
        for m in t.members(self.show_private):
            label = m.signature.split("(")[0].split()[-1] if m.kind not in ("EnumValue",) else m.name
            if m.kind in ("Method", "Constructor", "Operator"):
                inside = m.signature[m.signature.find("(") + 1: m.signature.rfind(")")]
                types = ", ".join(" ".join(x.strip().split(" ")[:-1]) for x in inside.split(",") if x.strip())
                label = f"{t.name if m.kind == 'Constructor' else label}({types})"
                if m.kind == "Method":
                    ret = m.signature.split("(")[0].split()[-2] if len(m.signature.split("(")[0].split()) > 1 else ""
                    label += f" : {ret}" if ret and ret != "void" else ""
            elif m.kind in ("Property", "Field", "Event", "Constant"):
                typ = m.signature.split("{")[0].split()
                label = f"{m.name} : {typ[-2]}" if len(typ) >= 2 else m.name
            item = QListWidgetItem(self._icon(m.kind), label)
            item.setData(ROLE, ("member", m))
            item.setToolTip(m.signature)
            self.members.addItem(item)
        self._describe(t.asm, t.doc_id, t.declaration(), f"Member of {t.namespace or t.asm.name}"
                       + (f" | base: {t.base_short}" if t.base_short and t.kind == "Class" else ""))

    def _select_member(self, it) -> None:
        if it is None:
            return
        d = it.data(ROLE)
        if d and d[0] == "member":
            m = d[1]
            self._describe(m.owner.asm, m.doc_id, m.signature, f"Member of {m.owner.cs_name}")

    def _describe(self, asm, doc_id: str, decl: str, member_of: str) -> None:
        doc = MD.doc_for(asm.path, doc_id) if doc_id else {}
        parts = [f"<p style='font-family:Consolas,monospace'>{_colour(decl)}</p>",
                 f"<p>{html.escape(member_of)}</p>"]
        if doc.get("summary"):
            parts.append(f"<p><b>Summary:</b><br>{html.escape(doc['summary'])}</p>")
        if doc.get("params"):
            ps = "".join(f"<br><i>{html.escape(k)}</i>: {html.escape(v)}" for k, v in doc["params"].items())
            parts.append(f"<p><b>Parameters:</b>{ps}</p>")
        if doc.get("returns"):
            parts.append(f"<p><b>Returns:</b><br>{html.escape(doc['returns'])}</p>")
        if doc.get("remarks"):
            parts.append(f"<p><b>Remarks:</b><br>{html.escape(doc['remarks'])}</p>")
        self.desc.setHtml("".join(parts))

    # ------------------------------------------------------------ search
    def do_search(self, text: str | None = None) -> int:
        q = (text if text is not None else self.search.text()).strip()
        if text is not None:
            self.search.setText(q)
        if not q:
            self._show_tree()
            return 0
        low = q.lower()
        self.results.clear()
        n = 0
        paths: list[str] = []
        for _g, p in self.assemblies():
            pp = Path(p)
            paths += [str(x) for x in sorted(pp.glob("*.dll"))] if pp.is_dir() else [str(pp)]
        for p in paths:
            try:
                a = MD.read_assembly(p)
            except Exception:  # noqa: BLE001
                continue
            for t in a.types:
                if not (self.show_private or t.is_public) or t.name == "<Module>":
                    continue
                if low in t.name.lower():
                    it = QListWidgetItem(self._icon(t.kind), f"{t.cs_name}   [{a.name}]")
                    it.setData(ROLE, ("type", t))
                    self.results.addItem(it)
                    n += 1
                if n >= 400:
                    break
                if len(low) >= 3 and low in " ".join(m.name.lower() for m in t.members(self.show_private)):
                    for m in t.members(self.show_private):
                        if low in m.name.lower():
                            it = QListWidgetItem(self._icon(m.kind), f"{t.cs_name}.{m.name}   [{a.name}]")
                            it.setData(ROLE, ("member", m))
                            it.setToolTip(m.signature)
                            self.results.addItem(it)
                            n += 1
            if n >= 400:
                break
        self.tree.setVisible(False)
        self.results.setVisible(True)
        if self.results.count():
            self.results.setCurrentRow(0)
        return n

    def _show_tree(self) -> None:
        self.results.setVisible(False)
        self.tree.setVisible(True)

    def _select_result(self, it) -> None:
        if it is None:
            return
        d = it.data(ROLE)
        if d[0] == "type":
            self.show_type(d[1])
        else:
            self.show_type(d[1].owner)
            self._select_member(it)

    # ------------------------------------------------------------ navigation
    def select_assembly(self, path: str) -> bool:
        key = os.path.normcase(str(Path(path).resolve()))
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            d = it.data(0, ROLE) or ()
            if d and d[0] == "assembly" and os.path.normcase(d[1]) == key:
                self.tree.setCurrentItem(it)
                it.setExpanded(True)
                return True
            if d and d[0] == "framework" and key.startswith(os.path.normcase(d[1])):
                it.setExpanded(True)
                for j in range(it.childCount()):
                    c = it.child(j)
                    if os.path.normcase(c.data(0, ROLE)[1]) == key:
                        self.tree.setCurrentItem(c)
                        c.setExpanded(True)
                        return True
        if Path(path).is_file() and MD.is_managed(path):      # not in the set: show it anyway
            it = self._assembly_item(None, str(Path(path).resolve()), "Opened")
            self.tree.setCurrentItem(it)
            it.setExpanded(True)
            return True
        return False

    def select_type(self, full_name: str) -> bool:
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            d = top.data(0, ROLE) or ()
            if not d or d[0] != "assembly":
                continue
            try:
                t = MD.read_assembly(d[1]).find_type(full_name)
            except Exception:  # noqa: BLE001
                continue
            if t is None:
                continue
            top.setExpanded(True)
            for j in range(top.childCount()):
                ns = top.child(j)
                for k in range(ns.childCount()):
                    ti = ns.child(k)
                    if ti.data(0, ROLE)[1] is t:
                        ns.setExpanded(True)
                        self.tree.setCurrentItem(ti)
                        return True
        return False

    def _current_node(self):
        w = QApplication.focusWidget()
        if w is self.members and self.members.currentItem() is not None:
            return self.members.currentItem()
        if self.results.isVisible() and self.results.currentItem() is not None:
            return self.results.currentItem()
        return self.tree.currentItem()

    def _menu(self, widget, pos) -> None:
        it = widget.itemAt(pos)
        if it is None:
            return
        m = QMenu(self)
        m.addAction("Go To Definition", lambda: self.goto_definition(it))
        m.addAction("Copy", lambda: QApplication.clipboard().setText(self._full_name(it)))
        m.addSeparator()
        m.addAction("Decompile with ILSpy...", lambda: self.goto_definition(it, install=True))
        m.exec(widget.viewport().mapToGlobal(pos))

    @staticmethod
    def _data(it):
        if isinstance(it, QTreeWidgetItem):
            return it.data(0, ROLE)
        return it.data(ROLE) if it is not None else None

    def _full_name(self, it) -> str:
        d = self._data(it)
        if not d:
            return ""
        if d[0] == "type":
            return d[1].cs_name
        if d[0] == "member":
            return f"{d[1].owner.cs_name}.{d[1].name}"
        return str(d[-1])

    def goto_definition(self, it, install: bool = False):
        """Open the type (of a member) decompiled, or as metadata-as-source. Returns the file opened."""
        d = self._data(it)
        if not d or d[0] not in ("type", "member"):
            return None
        t = d[1] if d[0] == "type" else d[1].owner
        member = d[1].name if d[0] == "member" else ""
        return open_definition(self.win, t, member, install=install)


def _colour(decl: str) -> str:
    kws = r"\b(public|private|protected|internal|static|abstract|sealed|virtual|override|readonly|const|class|" \
          r"interface|struct|enum|delegate|event|void|int|string|bool|object|double|float|long|short|byte|char|" \
          r"uint|ulong|ushort|sbyte|decimal|get|set|ref|operator|implicit|explicit|nint|nuint)\b"
    return re.sub(kws, lambda m: f"<span style='color:#0000ff'>{m.group(1)}</span>", html.escape(decl))


# ====================================================================== Go To Definition
def metadata_source_file(t: MD.TypeMeta) -> Path:
    from ..tools import sdk
    a = t.asm
    st = a.path.stat()
    folder = sdk.cache_dir("metadata-as-source", f"{a.name}-{sdk.short_hash(f'{a.path}|{st.st_size}|{st.st_mtime_ns}')}")
    f = folder / (re.sub(r"[^\w.`-]", "_", t.full_name) + ".cs")
    f.write_text(MD.metadata_as_source(t), encoding="utf-8")
    return f


def _open_file(win, path: Path, member: str = ""):
    ed = None
    try:
        ed = win.open_any_file(Path(path))
    except Exception as e:  # noqa: BLE001
        try:
            win.log(f"*** cannot open {path}: {e}")
        except Exception:  # noqa: BLE001
            pass
    if ed is not None:
        try:
            ed.setReadOnly(True)
        except Exception:  # noqa: BLE001
            pass
        if member:
            try:
                lines = Path(path).read_text(encoding="utf-8").splitlines()
                rx = re.compile(rf"\b{re.escape(member)}\b\s*(?:<[^>]*>)?\s*[(;{{\[]")
                for i, ln in enumerate(lines):
                    if rx.search(ln) and not ln.lstrip().startswith("//"):
                        ed.goto_line(i)
                        break
            except Exception:  # noqa: BLE001
                pass
    return path


def open_definition(win, t: MD.TypeMeta, member: str = "", install: bool = False):
    """Decompiled (ilspycmd) when available - or after installing it when *install* - else metadata."""
    if member == ".ctor":
        member = t.name
    elif member.startswith("op_"):
        member = "operator"
    try:
        from .. import decompile as DC
    except Exception:  # noqa: BLE001
        DC = None
    exe = DC.find_ilspycmd() if DC is not None else ""
    if DC is not None and (exe or install):
        if install and not exe and not OFFSCREEN:
            ans = QMessageBox.question(win, "Decompile", "ILSpy's command line (ilspycmd) is not installed.\n\n"
                                       "Install it now from nuget.org (dotnet tool install ilspycmd, into "
                                       "%LOCALAPPDATA%\\RADIDE\\tools, no admin)?")
            if ans != QMessageBox.StandardButton.Yes:
                return _open_file(win, metadata_source_file(t), member)
        fut = _POOL.submit(DC.decompiled_file, t.asm.path, t.full_name.replace("+", "."))
        try:
            win.statusBar().showMessage(f"Decompiling {t.cs_name} ...", 8000)
        except Exception:  # noqa: BLE001
            pass

        def poll():
            if not fut.done():
                QTimer.singleShot(200, poll)
                return
            try:
                _open_file(win, fut.result(), member)
            except Exception as e:  # noqa: BLE001
                try:
                    win.log(f"[Object Browser] decompiler: {e} - showing metadata instead")
                except Exception:  # noqa: BLE001
                    pass
                _open_file(win, metadata_source_file(t), member)
        QTimer.singleShot(100, poll)
        return fut
    return _open_file(win, metadata_source_file(t), member)


# ====================================================================== dock
def show_object_browser(win, assembly: str | None = None, type_name: str | None = None) -> ObjectBrowser:
    dock = getattr(win, "dock_object_browser", None)
    if dock is None:
        ob = ObjectBrowser(win)
        dock = QDockWidget("Object Browser", win)
        dock.setObjectName("Object Browser")
        dock.setWidget(ob)
        win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        try:
            win.tabifyDockWidget(win.dock_output, dock)
        except Exception:  # noqa: BLE001
            pass
        win.dock_object_browser = dock
        win.object_browser = ob
    else:
        dock.widget().reload()
    dock.show()
    dock.raise_()
    ob = dock.widget()
    if assembly:
        ob.select_assembly(assembly)
    if type_name:
        ob.select_type(type_name)
    return ob


__all__ = ["ObjectBrowser", "show_object_browser", "solution_assemblies", "open_definition", "metadata_source_file",
           "package_assemblies"]
