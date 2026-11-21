"""Properties window for a selected reference (Solution Explorer > Dependencies / References > item).

Like Visual Studio: "<name> Reference Properties" with Aliases, Copy Local, Embed Interop Types, Specific
Version (editable, written back to the project file as Aliases / Private / EmbedInteropTypes /
SpecificVersion metadata) and Path, Version, Identity, Culture, Runtime Version, Strong Name (read-only).

    rows = reference_rows(project, kind, include)      # [(label, value, editor, metadata)] - no Qt
    apply_value(project, kind, include, metadata, value)
    install(win)                                       # the Properties panel shows them on selection
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QHeaderView, QLabel, QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget)

from . import catalog as CAT
from . import edits as ED

ROLE = Qt.ItemDataRole.UserRole
ITEM = {"assembly": "Reference", "com": "COMReference", "project": "ProjectReference", "package": "PackageReference",
        "framework": "FrameworkReference", "shared": "Import"}

DESCRIPTIONS = {
    "Aliases": "A comma-delimited list of aliases to this reference.",
    "Copy Local": "Indicates whether the reference will be copied to the output directory.",
    "Embed Interop Types": "Indicates whether types defined in this assembly will be embedded into the target "
                           "assembly.",
    "Specific Version": "Indicates whether this assembly can be resolved without regard to multi-targeting rules "
                        "for assembly resolution.",
    "Path": "Location of the file being referenced.",
    "Version": "Version of the reference.",
    "Identity": "Security identity of the referenced assembly (see System.Reflection.Assembly.FullName).",
    "Runtime Version": "Version of the .NET runtime this assembly was compiled against.",
    "Strong Name": "True indicates that the reference has been signed with a key pair.",
    "Isolated": "Indicates whether the COM component should be isolated (registration-free COM).",
    "Reference Output Assembly": "Indicates whether the output of the referenced project is passed to the "
                                 "compiler.",
    "Wrapper Tool": "The tool used to generate the interop assembly of the COM component.",
}


def _bool(v: str | None, default: bool) -> bool:
    if v is None or v == "":
        return default
    return str(v).strip().lower() == "true"


def _item(project, kind: str, include: str):
    ms = project.ms
    low = ED.xml_unescape(include).lower()
    for it in ms.explicit(ITEM.get(kind, "")):
        if ED.xml_unescape(it.include).lower() == low:
            return it
    return None


def reference_rows(project, kind: str, include: str) -> list[tuple[str, str, str, str]]:
    """(label, value, editor, metadata) - editor: '' read-only, 'text', 'bool'."""
    ms = project.ms
    it = _item(project, kind, include)
    md = dict(it.metadata) if it is not None else {}
    inc = ED.xml_unescape(include)
    name = inc.split(",")[0].strip() if kind not in ("project", "shared") else Path(inc.replace("\\", "/")).stem
    rows: list[tuple[str, str, str, str]] = [("(Name)", name, "", "")]
    if kind == "assembly":
        path = CAT.resolve_reference_path(project, "Reference", include, md)
        framework = bool(path) and ("Reference Assemblies" in path or "\\packs\\" in path.lower()
                                    or "\\dotnet\\packs" in path.lower())
        ident = {}
        if path and Path(path).is_file():
            try:
                from .metadata import assembly_identity
                ident = assembly_identity(path)
            except Exception:  # noqa: BLE001
                ident = {}
        copy_default = not framework
        spec_default = "version=" in inc.lower()
        rows += [
            ("Aliases", md.get("Aliases", "global"), "text", "Aliases"),
            ("Copy Local", str(_bool(md.get("Private"), copy_default)), "bool", "Private"),
            ("Culture", ident.get("culture", ""), "", ""),
            ("Embed Interop Types", str(_bool(md.get("EmbedInteropTypes"), False)), "bool", "EmbedInteropTypes"),
            ("File Type", "Assembly", "", ""),
            ("Identity", ident.get("identity", inc) if ident else inc, "", ""),
            ("Path", path, "", ""),
            ("Resolved", str(bool(path) and Path(path).exists()), "", ""),
            ("Runtime Version", ident.get("runtime", ""), "", ""),
            ("Specific Version", str(_bool(md.get("SpecificVersion"), spec_default)), "bool", "SpecificVersion"),
            ("Strong Name", str(bool(ident.get("token"))), "", ""),
            ("Version", ident.get("version", ""), "", ""),
        ]
    elif kind == "com":
        path = CAT.resolve_reference_path(project, "COMReference", include, md)
        rows += [
            ("Copy Local", str(_bool(md.get("Private"), False)), "bool", "Private"),
            ("Embed Interop Types", str(_bool(md.get("EmbedInteropTypes"), False)), "bool", "EmbedInteropTypes"),
            ("File Type", "ActiveX", "", ""),
            ("Guid", "{" + md.get("Guid", "").strip("{}") + "}", "", ""),
            ("Isolated", str(_bool(md.get("Isolated"), False)), "bool", "Isolated"),
            ("Lcid", md.get("Lcid", "0"), "", ""),
            ("Path", path, "", ""),
            ("Version", f"{md.get('VersionMajor', '?')}.{md.get('VersionMinor', '0')}", "", ""),
            ("Wrapper Tool", md.get("WrapperTool", "tlbimp"), "", ""),
        ]
    elif kind == "project":
        path = CAT.resolve_reference_path(project, "ProjectReference", include, md)
        rows += [
            ("Aliases", md.get("Aliases", "global"), "text", "Aliases"),
            ("Copy Local", str(_bool(md.get("Private"), True)), "bool", "Private"),
            ("Path", path, "", ""),
            ("Reference Output Assembly", str(_bool(md.get("ReferenceOutputAssembly"), True)), "bool",
             "ReferenceOutputAssembly"),
        ]
    elif kind == "package":
        ver = md.get("Version", "")
        root = Path.home() / ".nuget" / "packages" / name.lower() / ver
        rows += [("Version", ver, "", ""), ("Path", str(root) if root.is_dir() else "", "", "")]
    elif kind == "framework":
        path = CAT.resolve_reference_path(project, "FrameworkReference", include, md)
        ver = Path(path).parent.parent.name if path else ""
        rows += [("Path", path, "", ""), ("Version", ver, "", "")]
    elif kind == "shared":
        rows += [("Path", str((ms.folder / inc.replace("\\", "/")).resolve()), "", "")]
    return rows


def apply_value(project, kind: str, include: str, metadata: str, value: str) -> str:
    """Write one edited value (bools as True/False; Aliases 'global' = remove). Returns the reference's
    Include after the change ('' when nothing changed): Specific Version = True turns a simple name into the
    full assembly identity, like Visual Studio (MSBuild cannot resolve a specific version from a bare name)."""
    item = ITEM.get(kind)
    if not item or not metadata:
        return ""
    it = _item(project, kind, include)
    if it is None:
        return ""
    inc = it.include
    if metadata == "Aliases":
        v = ",".join(a.strip() for a in value.split(",") if a.strip())
        return inc if ED.set_metadata(project, item, inc, "Aliases", None if v in ("", "global") else v) else ""
    on = str(value).lower() == "true"
    renamed = False
    if kind == "assembly" and metadata == "SpecificVersion" and on and "," not in ED.xml_unescape(inc):
        path = CAT.resolve_reference_path(project, "Reference", inc, it.metadata)
        if path and Path(path).is_file():
            try:
                full = ED.full_identity(path)
            except Exception:  # noqa: BLE001
                full = ""
            if full and ED.rename_include(project, item, inc, full):
                inc, renamed = full, True
    changed = ED.set_metadata(project, item, inc, metadata, "True" if on else "False")
    return inc if (changed or renamed) else ""


# ====================================================================== the view
class ReferencePropertiesView(QWidget):
    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win = win
        self.project = None
        self.kind = self.include = ""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel()
        self.title.setStyleSheet("font-weight: bold; padding: 2px;")
        lay.addWidget(self.title)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Property", "Value"])
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(20)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemChanged.connect(self._text_changed)
        self.table.currentCellChanged.connect(lambda r, *_: self._describe(r))
        lay.addWidget(self.table, 1)
        self.help = QLabel()
        self.help.setWordWrap(True)
        self.help.setMinimumHeight(54)
        self.help.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.help.setProperty("radRole", "help")
        lay.addWidget(self.help)
        self._filling = False

    def show_reference(self, project, kind: str, include: str) -> None:
        self.project, self.kind, self.include = project, kind, include
        self.refresh()

    def refresh(self) -> None:
        if self.project is None:
            return
        rows = reference_rows(self.project, self.kind, self.include)
        name = rows[0][1] if rows else self.include
        label = {"package": "Package", "framework": "Framework", "shared": "Shared Project",
                 "project": "Project Reference", "com": "COM Reference"}.get(self.kind, "Reference")
        self.title.setText(f"{name}  {label} Properties")
        self._filling = True
        self.table.clearContents()
        self.table.setRowCount(len(rows))
        for r, (lab, val, editor, md) in enumerate(rows):
            li = QTableWidgetItem(lab)
            li.setFlags(li.flags() & ~Qt.ItemFlag.ItemIsEditable)
            li.setData(ROLE, md)
            self.table.setItem(r, 0, li)
            vi = QTableWidgetItem(val)
            vi.setData(ROLE, (editor, md))
            if editor != "text":
                vi.setFlags(vi.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if not editor:
                vi.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(r, 1, vi)
            if editor == "bool":
                cb = QComboBox()
                cb.addItems(["True", "False"])
                cb.setCurrentText(val)
                cb.setFrame(False)
                cb.currentTextChanged.connect(lambda v, m=md: self._set(m, v))
                self.table.setCellWidget(r, 1, cb)
        self._filling = False

    def _describe(self, row: int) -> None:
        it = self.table.item(row, 0)
        if it is not None:
            self.help.setText(f"<b>{it.text()}</b><br>{DESCRIPTIONS.get(it.text(), '')}")

    def _text_changed(self, item: QTableWidgetItem) -> None:
        if self._filling or item.column() != 1:
            return
        editor, md = item.data(ROLE) or ("", "")
        if editor == "text":
            self._set(md, item.text())

    def _set(self, metadata: str, value: str) -> None:
        if self._filling or self.project is None:
            return
        new_inc = apply_value(self.project, self.kind, self.include, metadata, value)
        if new_inc:
            project, kind, include = self.project, self.kind, ED.xml_unescape(new_inc)
            self.include = include
            ED.commit(self.win, project)
            try:
                self.win.log(f"{project.name}: {metadata}={value} for {ED.xml_unescape(include).split(',')[0]} "
                             f"({project.ms.path.name} updated)")
            except Exception:  # noqa: BLE001
                pass
            QTimer.singleShot(0, lambda: _reselect(self.win, project, kind, include))

    def value(self, label: str) -> str:
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).text() == label:
                w = self.table.cellWidget(r, 1)
                return w.currentText() if isinstance(w, QComboBox) else self.table.item(r, 1).text()
        return ""

    def set_value(self, label: str, value: str) -> bool:
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).text() == label:
                w = self.table.cellWidget(r, 1)
                if isinstance(w, QComboBox):
                    w.setCurrentText(value)
                else:
                    self.table.item(r, 1).setText(value)
                return True
        return False


# ====================================================================== Properties panel hook
def _dep_of(win, item):
    """(project, kind, include) for a Dependencies / References item of a VS project, else None."""
    if item is None:
        return None
    data = item.data(0, ROLE) or ("",)
    if not isinstance(data, tuple) or len(data) < 2 or data[0] != "foreign_dep":
        return None
    kind, _, inc = str(data[1]).partition("|")
    try:
        from ...features.solution_ui import PROJECT_ROLE
        key = item.data(0, PROJECT_ROLE)
    except Exception:  # noqa: BLE001
        key = None
    project = None
    try:
        sln = win.sln
        for p in sln.all_projects():
            if key is not None and win._pkey(p) == key:
                project = p
                break
    except Exception:  # noqa: BLE001
        project = None
    if project is None or not hasattr(project, "ms"):
        return None
    if kind == "framework" and inc.startswith(".NET Framework"):
        return None
    return project, kind, inc


def _reselect(win, project, kind: str, include: str) -> None:
    tree = getattr(win, "solution", None)
    if tree is None:
        return
    want = f"{kind}|{ED.xml_unescape(include)}".lower()
    stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    while stack:
        it = stack.pop()
        d = it.data(0, ROLE) or ("",)
        if isinstance(d, tuple) and len(d) > 1 and d[0] == "foreign_dep" and str(d[1]).lower() == want:
            tree.setCurrentItem(it)
            return
        stack.extend(it.child(i) for i in range(it.childCount()))


def install(win) -> None:
    panel = getattr(win, "properties", None)
    tree = getattr(win, "solution", None)
    if panel is None or tree is None or getattr(win, "ref_props_view", None) is not None:
        return
    view = ReferencePropertiesView(win, panel)
    view.setVisible(False)
    try:
        panel.layout().insertWidget(1, view, 1)
    except Exception:  # noqa: BLE001
        return
    win.ref_props_view = view
    normal = [w for w in (getattr(panel, "selector", None), getattr(panel, "btn_cat", None),
                          getattr(panel, "btn_alpha", None), getattr(panel, "tabs", None), getattr(panel, "help", None))
              if w is not None]

    def show(on: bool) -> None:
        if view.isHidden() != on:                  # already in that state
            return
        for w in normal:
            w.setVisible(not on)
        view.setVisible(on)
    win.ref_props_show = show

    def changed(cur, _prev=None) -> None:
        dep = _dep_of(win, cur)
        if dep is None:
            show(False)
            return
        view.show_reference(*dep)
        show(True)
        try:
            win.dock_props.raise_()
        except Exception:  # noqa: BLE001
            pass
    tree.currentItemChanged.connect(changed)
    win.show_reference_properties = lambda item=None: changed(item or tree.currentItem())

    orig = panel.set_document

    def set_document(doc, plugin):                 # a designer became active: the form's properties again
        show(False)
        return orig(doc, plugin)
    panel.set_document = set_document


__all__ = ["reference_rows", "apply_value", "ReferencePropertiesView", "install"]
