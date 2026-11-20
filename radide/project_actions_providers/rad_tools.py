"""Project actions for Godot projects (open in the Godot editor, run, export presets), Ring (run, Build EXE with
ring2exe, ringpm) and Visual Basic projects (VB6 .vbp projects opened in place, RAD IDE BASIC projects):
Run, Build EXE (the IDE's Publish), Project Properties."""
from __future__ import annotations

import re
from pathlib import Path

from ..project_actions import Action, Field, Provider, Separator, Submenu, read_text


def _publish(ctx):
    pub = getattr(ctx.win, "publisher", None)
    if pub is None:
        ctx.log("*** Publish is not available in this window")
        return
    pub.open_dialog()


def _run_project(ctx, debug=False):
    try:
        ctx.win.run_project(debug)
    except Exception as e:  # noqa: BLE001
        ctx.log(f"*** run: {e}")


def _start_detached(ctx, argv, cwd) -> bool:
    from PyQt6.QtCore import QProcess
    ok = QProcess.startDetached(argv[0], argv[1:], str(cwd))
    ok = ok[0] if isinstance(ok, tuple) else ok
    ctx.log(("Started: " if ok else "*** cannot start: ") + " ".join(argv))
    return bool(ok)


# ============================================================================ Godot
def godot() -> str:
    try:
        from ..games.godot_export import godot_exe
        return godot_exe() or ""
    except Exception:  # noqa: BLE001
        return ""


def export_presets(folder: Path) -> list[tuple[str, str]]:
    """(name, export_path) of every preset of export_presets.cfg."""
    text = read_text(Path(folder) / "export_presets.cfg")
    out = []
    for block in re.split(r"^\[preset\.\d+\]\s*$", text, flags=re.M)[1:]:
        block = block.split("\n[", 1)[0]
        n = re.search(r'^name="([^"]*)"', block, re.M)
        p = re.search(r'^export_path="([^"]*)"', block, re.M)
        if n:
            out.append((n.group(1), p.group(1) if p else ""))
    return out


class Godot(Provider):
    id, title, priority, icon = "godot", "Godot", 40, ("Gd", "#478CBF")
    markers = ("project.godot", "export_presets.cfg")

    def detect(self, folder, project):
        return (folder / "project.godot").is_file() or \
            getattr(project, "language", "") in ("godot", "godot3d")

    @staticmethod
    def is_rad(ctx) -> bool:
        return getattr(ctx.project, "language", "") in ("godot", "godot3d") and any(ctx.folder.glob("*.scene"))

    def enabled(self, ctx) -> bool:
        return bool(godot()) and (ctx.folder / "project.godot").is_file()

    def actions(self, ctx):
        items = [Action("editor", "Open in Godot Editor", self._editor, opens="none", toolbar=True,
                        icon=("Gd", "#478CBF"), enabled=self.enabled),
                 Action("run", "Run the Game in Godot", lambda c: c.run_cli([godot(), "--path", str(c.folder)],
                                                                            title="Godot: run"),
                        opens="none", enabled=self.enabled),
                 Separator(),
                 Submenu("Export", self.export_items(ctx)),
                 Action("import", "Re-import Assets (headless)",
                        lambda c: c.run_cli([godot(), "--headless", "--path", str(c.folder), "--editor", "--quit"],
                                            title="Godot: import"), opens="none", enabled=self.enabled)]
        if self.is_rad(ctx):
            items[2:2] = [Separator(),
                          Action("export-project", "Write the Godot Project (project.godot + .tscn)", self._export_rad,
                                 opens="none", refresh=True,
                                 tip="Turn the RAD IDE scenes into a Godot project in this folder")]
        if not godot():
            items.append(Action("no-godot", "(Godot was not found - install it: winget install GodotEngine)",
                                lambda c: None, enabled=lambda c: False, palette=False))
        return items

    def export_items(self, ctx) -> list:
        presets = export_presets(ctx.folder)
        if not presets:
            return [Action("no-presets", "(no export presets - add them in the Godot editor: Project > Export)",
                           lambda c: None, enabled=lambda c: False, palette=False)]
        out = []
        for name, path in presets:
            out.append(Action(f"export.{name}", f"Export '{name}'",
                              lambda c, n=name, p=path: self._export(c, n, p, "--export-release"),
                              opens="none", enabled=self.enabled, tip=path))
            out.append(Action(f"export-debug.{name}", f"Export '{name}' (debug)",
                              lambda c, n=name, p=path: self._export(c, n, p, "--export-debug"),
                              opens="none", enabled=self.enabled, tip=path))
        return out

    def _export(self, ctx, name, path, flag):
        if not path:
            ctx.log(f"*** the preset '{name}' has no export path - set one in the Godot editor (Project > Export)")
            return
        out = ctx.folder / path
        out.parent.mkdir(parents=True, exist_ok=True)
        ctx.run_cli([godot(), "--headless", "--path", str(ctx.folder), flag, name, str(out)],
                    title=f"Godot export '{name}'")

    def _editor(self, ctx):
        _start_detached(ctx, [godot(), "--editor", "--path", str(ctx.folder)], ctx.folder)

    def _export_rad(self, ctx):
        from ..games.godot_export import export_project
        try:
            files = export_project(ctx.folder)
        except Exception as e:  # noqa: BLE001
            ctx.log(f"*** Godot export: {e}")
            return
        ctx.log("Godot project written: " + ", ".join(ctx.rel(p) for p in files))
        ctx.refresh_tree()

    def folder_actions(self, ctx, rel_folder):
        return self.actions(ctx) if rel_folder == "" else []

    def file_actions(self, ctx, rel_file):
        if rel_file.endswith(".tscn") and self.enabled(ctx):
            return [Action("run-scene", "Run This Scene",
                           lambda c: c.run_cli([godot(), "--path", str(c.folder), f"res://{rel_file}"],
                                               title=f"Godot: {rel_file}"), opens="none")]
        return []


# ============================================================================ Ring
def ring() -> str:
    try:
        from ..languages import get_plugin
        return get_plugin("ring-qt").find_interpreter("") or ""
    except Exception:  # noqa: BLE001
        return ""


def ring_tool(name: str) -> str:
    r = ring()
    if not r:
        return ""
    p = Path(r).with_name(name + (".exe" if r.lower().endswith(".exe") else ""))
    return str(p) if p.exists() else ""


class Ring(Provider):
    id, title, priority, icon = "ring", "Ring", 40, ("Ri", "#2C6EB5")

    def detect(self, folder, project):
        lang = str(getattr(project, "language", "") or "")
        return lang.startswith("ring") or (not getattr(project, "forms", None) and any(folder.glob("*.ring")))

    @staticmethod
    def is_rad(ctx) -> bool:
        """A RAD IDE Ring project (forms designed in the IDE): Run / Publish go through the IDE."""
        return str(getattr(ctx.project, "language", "") or "").startswith("ring") and             (ctx.folder / "project.radproj").is_file()

    @staticmethod
    def main_file(ctx) -> str:
        for rel in ("main.ring", "app.ring", "start.ring"):
            if ctx.path(rel).is_file():
                return rel
        files = sorted(p.name for p in ctx.folder.glob("*.ring") if not p.name.startswith("_rad"))
        return files[0] if files else ""

    def ring2exe(self, ctx, rel: str, gui: bool):
        exe = ring_tool("ring2exe")
        if not exe:
            ctx.log("*** ring2exe was not found next to ring.exe (install Ring from ring-lang.net)")
            return None
        argv = [exe, Path(rel).name, "-dist", "-allruntime"] + (["-gui", "-qt"] if gui else [])
        return ctx.run_cli(argv, cwd=ctx.path(rel).parent, title=f"ring2exe {Path(rel).name}", opens="none")

    def actions(self, ctx):
        items = []
        if self.is_rad(ctx):
            items += [Action("run", "Run", lambda c: _run_project(c), opens="none", icon="SP_MediaPlay"),
                      Action("build-exe", "Build EXE (Publish)...", _publish, opens="none", toolbar=True,
                             icon="SP_DriveHDIcon", tip="ring2exe -dist -allruntime -gui -qt, then an installer")]
        else:
            main = self.main_file(ctx)
            items += [Action("run", f"Run {main}", lambda c: c.run_cli([ring(), main], title=f"ring {main}"),
                             opens="none", icon="SP_MediaPlay", enabled=lambda c: bool(main and ring())),
                      Action("build-exe", f"Build EXE ({main}, ring2exe)", lambda c: self.ring2exe(c, main, False),
                             opens="none", toolbar=True, enabled=lambda c: bool(main)),
                      Action("build-exe-gui", f"Build GUI EXE ({main}, ring2exe -gui -qt)",
                             lambda c: self.ring2exe(c, main, True), opens="none", enabled=lambda c: bool(main))]
        items += [Separator(),
                  Action("ringpm-install", "Install Package (ringpm)...",
                         lambda c: c.run_cli([ring_tool("ringpm") or "ringpm", "install", c.values["package"]]),
                         ask=[Field("package", "Package", placeholder="weblib")], opens="none"),
                  Action("ringpm-list", "Installed Packages (ringpm list)",
                         lambda c: c.run_cli([ring_tool("ringpm") or "ringpm", "list"]), opens="none")]
        return items

    def folder_actions(self, ctx, rel_folder):
        return self.actions(ctx) if rel_folder == "" else []

    def file_actions(self, ctx, rel_file):
        if not rel_file.endswith(".ring") or Path(rel_file).name.startswith("_rad"):
            return []
        return [Action("run-file", "Run This File", lambda c: c.run_cli([ring(), rel_file], title=f"ring {rel_file}",
                                                                        cwd=c.path(rel_file).parent), opens="none"),
                Action("exe-file", "Build EXE from This File (ring2exe)", lambda c: self.ring2exe(c, rel_file, False),
                       opens="none"),
                Action("exe-file-gui", "Build GUI EXE from This File (ring2exe -gui -qt)",
                       lambda c: self.ring2exe(c, rel_file, True), opens="none")]


# ============================================================================ Visual Basic (VB6 / BASIC)
def _vb6_mirror(folder) -> bool:
    try:
        from ..foreign.vb6_project import is_mirror
        return is_mirror(folder)
    except Exception:  # noqa: BLE001
        return False


class VB6(Provider):
    id, title, priority, icon = "vb6", "VB6", 40, ("VB", "#5C2D91")

    def detect(self, folder, project):
        return _vb6_mirror(folder)

    def actions(self, ctx):
        return [Action("run", "Run (F5)", lambda c: _run_project(c), opens="none", icon="SP_MediaPlay"),
                Action("build-exe", "Make EXE (Publish)...", _publish, opens="none", toolbar=True,
                       icon="SP_DriveHDIcon"),
                Separator(),
                Action("properties", "VB6 Project Properties...", self._properties, opens="none"),
                Action("open-vbp", "Open the .vbp File", self._open_vbp, opens="none")]

    @staticmethod
    def _properties(ctx):
        from ..foreign.vb6_project import project_properties_dialog
        project_properties_dialog(ctx.win)

    @staticmethod
    def _open_vbp(ctx):
        from ..foreign.vb6_project import native_project_file
        p = native_project_file(ctx.folder)
        if p is not None:
            ctx.open_file(p)

    def folder_actions(self, ctx, rel_folder):
        return self.actions(ctx) if rel_folder == "" else []


class Basic(Provider):
    id, title, priority, icon = "basic", "BASIC", 40, ("B", "#2E5C9A")

    def detect(self, folder, project):
        return getattr(project, "language", "") == "vb-basic" and not _vb6_mirror(folder)

    def actions(self, ctx):
        return [Action("run", "Run (F5)", lambda c: _run_project(c), opens="none", icon="SP_MediaPlay"),
                Action("build-exe", "Build EXE (Publish)...", _publish, opens="none", toolbar=True,
                       icon="SP_DriveHDIcon"),
                Separator(),
                Action("add-form", "Add Form...", lambda c: c.win.add_form(), opens="none"),
                Action("properties", "Project Properties...", lambda c: c.win.project_properties(), opens="none")]

    def folder_actions(self, ctx, rel_folder):
        return self.actions(ctx) if rel_folder == "" else []

    def file_actions(self, ctx, rel_file):
        return []


PROVIDERS = [Godot(), Ring(), VB6(), Basic()]
