"""Banded reports in the IDE (radide/reports):

* Project > Add Report... (wizard or blank) creates ``<Name>.rpt.json`` and opens the Report Designer;
* .rpt.json files open in the designer (Solution Explorer "Reports" node, File > Open, Ctrl+P ...);
* the ReportViewer control (Toolbox) shows a report on a form; its design-time preview draws the report;
* Save All saves open reports and copies the runtime ``radreport.py`` into projects that use reports.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QMessageBox, QTreeWidgetItem

from ..reports import REPORT_EXT, copy_runtime, list_reports, radreport, uses_reports

ROLE = Qt.ItemDataRole.UserRole


# ------------------------------------------------------------------ ReportViewer design-time preview
def _viewer_preview(parent):
    w = QLabel(parent)
    w.setAlignment(Qt.AlignmentFlag.AlignCenter)
    w.setWordWrap(True)
    return w


def _viewer_props(w, p: dict, ctrl) -> None:
    """Design time: the first page of the report, scaled into the control (or a placeholder)."""
    from PyQt6.QtGui import QPixmap
    rf = str(p.get("ReportFile") or "")
    root = w.property("rad_root") or ""
    w.setStyleSheet("")
    if rf:
        path = Path(rf) if Path(rf).is_absolute() else Path(root) / rf
        try:
            rpt = radreport.Report(str(path))
            rpt.Run()
            if rpt.pages:
                img = rpt.RenderPage(0, 0.6)
                pm = QPixmap.fromImage(img).scaled(max(10, int(p["Width"]) - 8), max(10, int(p["Height"]) - 8),
                                                   Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation)
                w.setPixmap(pm)
                w.setToolTip(f"{rf}: {len(rpt.pages)} page(s)")
                return
        except Exception as e:  # noqa: BLE001 - design time only
            w.setText(f"ReportViewer\n{rf}\n({e})")
            return
    w.setText(f"ReportViewer\n{rf or '(set ReportFile)'}")


def register_preview() -> None:
    """Nothing to register any more: the built-in ReportViewer package's designer.py
    (radide/components/builtin/ReportViewer) uses _viewer_preview / _viewer_props."""


# ------------------------------------------------------------------ manager
class ReportManager:
    def __init__(self, win):
        self.win = win
        self.editors: dict[str, object] = {}

    # data for the dialogs
    def connections(self) -> list[dict]:
        out = []
        try:
            from ..web_site.databases import ConnectionManager
            for prj in self._projects():
                for c in ConnectionManager(prj).connections:
                    out.append(c.to_dict())
        except Exception:  # noqa: BLE001
            pass
        return out

    def datasets(self) -> list[dict]:
        out = []
        prj = self.win.project
        if prj is None:
            return out
        try:
            from ..model import Form
            for n in prj.forms:
                try:
                    f = Form.load(prj.form_path(n))
                except Exception:  # noqa: BLE001
                    continue
                for ds in f.extra.get("datasources") or []:
                    if ds.get("file"):
                        out.append({**ds, "form": n})
        except Exception:  # noqa: BLE001
            pass
        return out

    def _projects(self):
        st = getattr(self.win, "_pstates", {}) or {}
        prjs = [s["project"] for s in st.values() if s.get("project") is not None]
        if self.win.project is not None and self.win.project not in prjs:
            prjs.append(self.win.project)
        return prjs

    @staticmethod
    def _alive(ed) -> bool:
        try:
            ed.isVisible()
            return True
        except RuntimeError:
            return False

    # editors
    def open_report(self, path):
        from ..reports.designer import ReportDesigner
        win = self.win
        path = Path(path).resolve()
        key = str(path).lower()
        ed = self.editors.get(key)
        if ed is not None and (not self._alive(ed) or win.tabs.indexOf(ed) < 0):
            self.editors.pop(key, None)
            ed = None
        if ed is None:
            try:
                ed = ReportDesigner(path, self.connections, self.datasets)
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(win, "Report", f"Cannot open {path.name}:\n{e}")
                return None
            ed.setToolTip(str(path))
            ed.modifiedChanged.connect(lambda _m, e=ed: self._title(e))
            ed.saved.connect(lambda: copy_runtime(path.parent))
            self.editors[key] = ed
        win._show_tab(ed, path.name)
        self._title(ed)
        return ed

    def _title(self, ed):
        i = self.win.tabs.indexOf(ed)
        if i >= 0:
            self.win.tabs.setTabText(i, ed.path.name + ("*" if ed.is_modified() else ""))

    def save_reports(self):
        for ed in list(self.editors.values()):
            if self._alive(ed) and ed.is_modified():
                ed.save()

    def any_modified(self) -> bool:
        return any(self._alive(e) and e.is_modified() for e in self.editors.values())

    def sync_runtime(self):
        """radreport.py into every open project that has reports or a ReportViewer on a form."""
        for prj in self._projects():
            try:
                forms = []
                st = next((s for s in (getattr(self.win, "_pstates", {}) or {}).values()
                           if s.get("project") is prj), None)
                docs = (st or {}).get("docs") or (self.win.docs if prj is self.win.project else {})
                forms = [d.form for d in docs.values() if hasattr(d, "form")]
                if not forms:
                    from ..model import Form
                    for n in prj.forms:
                        try:
                            forms.append(Form.load(prj.form_path(n)))
                        except Exception:  # noqa: BLE001
                            pass
                if uses_reports(prj.folder, forms):
                    copy_runtime(prj.folder)
            except Exception as e:  # noqa: BLE001
                self.win.log(f"[reports] {e}")

    # commands
    def add_report(self):
        win = self.win
        if win.project is None:
            QMessageBox.information(win, "Add Report", "Open or create a project first.")
            return
        from ..reports.designer import AddReportDialog
        folder = Path(win.project.folder)
        i = 1
        while (folder / f"Report{i}{REPORT_EXT}").exists():
            i += 1
        dlg = AddReportDialog(win, folder, self.connections(), self.datasets(), f"Report{i}")
        if not dlg.exec():
            return
        d = dlg.definition()
        path = folder / f"{d['name']}{REPORT_EXT}"
        radreport.save_definition(d, path)
        copy_runtime(folder)
        try:
            win._fill_solution()
        except Exception:  # noqa: BLE001
            pass
        win.log(f"[reports] created {path.name} (runtime radreport.py copied into the project)")
        return self.open_report(path)

    # solution explorer
    def add_tree_nodes(self):
        win = self.win
        try:
            from .solution_ui import PROJECT_ROLE
        except ImportError:
            return
        tree = win.solution
        stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
        while stack:
            it = stack.pop()
            stack.extend(it.child(i) for i in range(it.childCount()))
            data = it.data(0, ROLE)
            if not data or data[0] != "project":
                continue
            key = it.data(0, PROJECT_ROLE)
            st = getattr(win, "_pstates", {}).get(key)
            prj = st["project"] if st else win.project
            if prj is None:
                continue
            reps = list_reports(prj.folder)
            if not reps or any((it.child(i).data(0, ROLE) or ("",))[0] == "reports" for i in range(it.childCount())):
                continue
            node = QTreeWidgetItem(it, ["Reports"])
            node.setData(0, ROLE, ("reports", str(prj.folder)))
            node.setData(0, PROJECT_ROLE, key)
            node.setIcon(0, win.style().standardIcon(win.style().StandardPixmap.SP_DirIcon))
            for p in reps:
                ri = QTreeWidgetItem(node, [p.name])
                ri.setData(0, ROLE, ("report", str(p)))
                ri.setData(0, PROJECT_ROLE, key)
                ri.setToolTip(0, "Report - double-click to open the Report Designer")
                ri.setIcon(0, win.style().standardIcon(win.style().StandardPixmap.SP_FileDialogDetailedView))
            node.setExpanded(True)

    def on_tree_dclick(self, item, _col):
        data = item.data(0, ROLE)
        if data and data[0] == "report":
            self.open_report(Path(data[1]))

    # DocumentProvider (radide/extension_points.py): File > Open, Solution Explorer, Save All, closing question
    def can_open(self, path: Path) -> bool:
        return str(path).lower().endswith(REPORT_EXT)

    def open_document(self, path: Path):
        return self.open_report(Path(path))

    def save_documents(self) -> None:
        self.save_reports()

    def has_modified_documents(self) -> bool:
        return self.any_modified()

    def wrap(self):
        win = self.win
        win.extension_points.add_document_provider(self)
        win.extension_points.add_save_listener(lambda _ok: self.sync_runtime(), "reports")         # radreport.py where needed
        win.extension_points.add_solution_contributor(self.add_tree_nodes, "reports")
        win.open_report = self.open_report
        win.add_report = self.add_report
        win.report_editors = self.editors
        win.reports = self


def _project_menu(win):
    for a in win.menuBar().actions():
        if a.text().replace("&", "") == "Project" and a.menu() is not None:
            return a.menu()
    return None


def install(win) -> None:
    register_preview()
    mgr = ReportManager(win)
    mgr.wrap()
    m = _project_menu(win)
    if m is not None:
        acts = m.actions()
        before = next((a for a in acts if a.text().replace("&", "").startswith("Add Existing")), None)
        from PyQt6.QtGui import QAction
        act = QAction("Add &Report...", win)
        act.triggered.connect(lambda _c=False: mgr.add_report())
        m.insertAction(before, act) if before is not None else m.addAction(act)
    try:
        win.solution.itemDoubleClicked.connect(mgr.on_tree_dclick)
    except Exception:  # noqa: BLE001
        pass
    try:
        from .command_palette import register_command
        register_command("reports.add", "Project: Add Report...", mgr.add_report, "Project")
    except Exception:  # noqa: BLE001
        pass
