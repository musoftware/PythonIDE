"""Component packages in the IDE (radide/components, docs/COMPONENTS.md).

* loads the packages at start-up and the active project's ``.radide/components`` when a project opens;
* Tools > Component Packages... (install .radcomp, uninstall, export, new package, user control -> package),
  Toolbox > Choose Items...;
* Save All / Run copy the runtime files of the components the forms use into the project and show the
  generator warnings (a target without a runtime gets a placeholder label);
* language plugins without component support generate placeholders instead of failing;
* hot reload while developing a package: a changed component.json / designer.py / editors.py / runtime is
  picked up at once (Toolbox, designers, Properties window). On by default when RADIDE_COMPONENT_PATH is set,
  otherwise Tools > Component Packages > Hot Reload.
"""
from __future__ import annotations

import os

from PyQt6.QtCore import QFileSystemWatcher, QSettings, QTimer
from PyQt6.QtGui import QAction

from ..components import REGISTRY, codegen, copy_runtimes, used_packages

HOT_KEY = "components/hot_reload"


class ComponentsFeature:
    def __init__(self, win):
        self.win = win
        self.watcher = None
        self._timer = QTimer(win)
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self.hot_reload)
        self._warned = 0

    # ------------------------------------------------------------ loading
    def load(self) -> None:
        prj = getattr(self.win, "project", None)
        REGISTRY.set_project(getattr(prj, "folder", None) if prj is not None else None)
        for c in REGISTRY.conflicts:
            self.win.log(f"[components] {c}")
        for folder, err in REGISTRY.broken:
            self.win.log(f"[components] cannot read {folder}: {err}")
        for p in REGISTRY.all(include_builtin=False):
            for e in p.errors:
                self.win.log(f"[components] {p.name}: {e}")

    def on_registry_changed(self) -> None:
        """Packages changed: designers redraw, the Properties window shows the new schema."""
        for v in list(getattr(self.win, "designers", {}).values()):
            try:
                v.rebuild()
            except Exception:  # noqa: BLE001
                pass
        props = getattr(self.win, "properties", None)
        if props is not None:
            try:
                props.refresh()
            except Exception:  # noqa: BLE001
                pass
        self._watch()

    # ------------------------------------------------------------ hot reload
    def hot_enabled(self) -> bool:
        v = QSettings().value(HOT_KEY, None)
        if v is None:
            return bool(os.environ.get("RADIDE_COMPONENT_PATH"))
        return str(v).lower() in ("1", "true")

    def set_hot(self, on: bool) -> None:
        QSettings().setValue(HOT_KEY, bool(on))
        self._watch()

    def _watch(self) -> None:
        if not self.hot_enabled():
            if self.watcher is not None:
                self.watcher.deleteLater()
                self.watcher = None
            return
        if self.watcher is None:
            self.watcher = QFileSystemWatcher(self.win)
            self.watcher.fileChanged.connect(lambda _p: self._timer.start())
            self.watcher.directoryChanged.connect(lambda _p: self._timer.start())
        old = set(self.watcher.files()) | set(self.watcher.directories())
        new = set(REGISTRY.watch_paths())
        if old - new:
            self.watcher.removePaths(sorted(old - new))
        if new - old:
            self.watcher.addPaths(sorted(new - old))

    def hot_reload(self) -> bool:
        if REGISTRY.reload_if_changed():
            self.win.log("[components] packages reloaded (hot reload)")
            return True
        self._watch()                      # files replaced by editors are watched again
        return False

    # ------------------------------------------------------------ save / run
    def after_save(self) -> None:
        prj = getattr(self.win, "project", None)
        if prj is None:
            return
        forms = [d.form for d in getattr(self.win, "docs", {}).values() if hasattr(d, "form")]
        if not used_packages(forms):
            from ..model import Form
            forms = []
            for n in getattr(prj, "forms", []):
                try:
                    forms.append(Form.load(prj.form_path(n)))
                except Exception:  # noqa: BLE001
                    pass
        if used_packages(forms):
            names = {id(f): f.name for f in forms}

            def target(f):
                try:
                    return self.win.plugin_for_form(names[id(f)]).id
                except Exception:  # noqa: BLE001
                    return getattr(prj, "language", "")
            copied = copy_runtimes(prj.folder, forms, target)
            if copied:
                self.win.log(f"[components] runtime copied into the project: {', '.join(copied)}")
        new = codegen.WARNINGS[self._warned:]
        for w in new:
            self.win.log(f"[components] warning: {w}")
        self._warned = len(codegen.WARNINGS)


def _tools_menu(win):
    for a in win.menuBar().actions():
        if a.text().replace("&", "") == "Tools" and a.menu() is not None:
            return a.menu()
    return win.menuBar().addMenu("&Tools")


def install(win) -> None:
    feat = ComponentsFeature(win)
    win.components = feat
    try:
        from ..languages import all_plugins
        for p in all_plugins():
            codegen.wrap_plugin(p)
    except Exception as e:  # noqa: BLE001
        win.log(f"[components] {e}")
    REGISTRY.on_change(feat.on_registry_changed)
    try:
        from .. import extensions
        extensions.on_change(lambda: QTimer.singleShot(0, REGISTRY.discover))
    except Exception:  # noqa: BLE001
        pass
    feat.load()
    feat._watch()

    orig_activate = win.activate_project

    def activate_project(project, *a, **kw):
        r = orig_activate(project, *a, **kw)
        try:
            REGISTRY.set_project(getattr(win.project, "folder", None) if win.project is not None else None)
        except Exception as e:  # noqa: BLE001
            win.log(f"[components] {e}")
        return r
    win.activate_project = activate_project

    orig_save_all = win.save_all

    def save_all(*a, **kw):
        r = orig_save_all(*a, **kw)
        try:
            feat.after_save()
        except Exception as e:  # noqa: BLE001
            win.log(f"[components] {e}")
        return r
    win.save_all = save_all

    m = _tools_menu(win).addMenu("Component &Packages")
    win.menu_components = m

    def manager():
        from ..components.ui import ComponentManagerDialog
        dlg = ComponentManagerDialog(win, win)
        win._components_dialog = dlg
        dlg.exec()

    def choose():
        tb = getattr(win, "toolbox", None)
        if tb is not None and hasattr(tb, "choose_items"):
            tb.choose_items()

    def install_pkg():
        from ..components.ui import install_package_dialog
        install_package_dialog(win)

    a = QAction("&Manage Component Packages...", win)
    a.setStatusTip("Install, uninstall, export and create Toolbox component packages")
    a.triggered.connect(manager)
    m.addAction(a)
    win.a_components = a
    a = QAction("&Install Component Package (.radcomp)...", win)
    a.triggered.connect(install_pkg)
    m.addAction(a)
    a = QAction("Choose Toolbox &Items...", win)
    a.triggered.connect(choose)
    m.addAction(a)
    m.addSeparator()
    hot = QAction("&Hot Reload (package development)", win)
    hot.setCheckable(True)
    hot.setChecked(feat.hot_enabled())
    hot.toggled.connect(feat.set_hot)
    m.addAction(hot)
    a = QAction("&Reload Packages", win)
    a.triggered.connect(REGISTRY.discover)
    m.addAction(a)
