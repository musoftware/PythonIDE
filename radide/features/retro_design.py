"""Retro game designers in the IDE (radide/retro/design/game): Atari 2600 screens, NES screens / levels, Game Boy
maps and DOS mode 13h screens, drawn visually and turned into code for the retro toolchains.

* Tools > Retro > Game Designers > New Atari 2600 Screen / New NES Screen or Level / New Game Boy Map /
  New DOS Mode 13h Screen, Open Game Design...
* ``.a26scr`` / ``.nesscr`` / ``.gbmap`` / ``.m13scr`` files open in the designer (File > Open, Solution Explorer).
* With a project open, new designs are saved in ``<project>/Designs`` and the generated code goes to
  ``Designs/gen/<name>/`` every time the design is saved (File > Save, Save All).
* Build && Run (designer tool bar) builds with DASM / ca65 / RGBDS / NASM / FreeBASIC / OpenWatcom and starts
  Stella / Mesen / mGBA / DOSBox-X through the retro emulator manager.
"""
from __future__ import annotations

from pathlib import Path

NEW_ITEMS = [("a2600", "New Atari 2600 Screen..."), ("nes", "New NES Screen / Level..."),
             ("gb", "New Game Boy Map..."), ("dos13h", "New DOS Mode 13h Screen...")]


class RetroDesignFeature:
    def __init__(self, win):
        self.win = win
        self.editors: dict[str, object] = {}
        self._menus()
        self._wrap()

    # ------------------------------------------------------------ menus
    def _menus(self) -> None:
        win = self.win
        try:
            from ..retro.menu import section
            m = section(win, "Game &Designers")
        except Exception:  # noqa: BLE001 - the shared retro menu is another slice
            tools = next((a.menu() for a in win.menuBar().actions() if a.menu() is not None and
                          a.text().replace("&", "") == "Tools"), None)
            m = (tools or win.menuBar()).addMenu("Game &Designers")
        self.menu = m
        for system, text in NEW_ITEMS:
            m.addAction(text, lambda s=system: self.new_design(s))
        m.addSeparator()
        self.a_for_project = m.addAction("New Design for This Project", self.new_for_project)
        m.addAction("Open Game Design...", self.open_dialog)
        m.aboutToShow.connect(lambda: self.a_for_project.setEnabled(self.project_system() is not None))

    # DocumentProvider (radide/extension_points.py): File > Open, Save All, closing question
    def can_open(self, path: Path) -> bool:
        from ..retro.design.game import is_design_file
        return is_design_file(path)

    def open_document(self, path: Path):
        return self.open_design(Path(path))

    def save_documents(self) -> None:
        self.save_all()

    def has_modified_documents(self) -> bool:
        return any(e.is_modified() for e in self._alive())

    def _wrap(self) -> None:
        self.win.extension_points.add_document_provider(self)
        self.win.retro_designs = self

    # ------------------------------------------------------------ documents
    def _alive(self) -> list:
        out = []
        for k, e in list(self.editors.items()):
            try:
                e.isVisible()
                out.append(e)
            except RuntimeError:
                self.editors.pop(k, None)
        return out

    def _log(self, msg: str) -> None:
        try:
            self.win.log(msg)
        except Exception:  # noqa: BLE001
            print(msg)

    def _register(self, ed, key: str) -> None:
        self.editors[key] = ed
        ed.modifiedChanged.connect(lambda _m, e=ed: self._title(e))
        ed.saved.connect(lambda e=ed: self._after_save(e))

    def _title(self, ed) -> None:
        try:
            i = self.win.tabs.indexOf(ed)
            if i >= 0:
                self.win.tabs.setTabText(i, ed.title())
        except RuntimeError:
            pass

    def _after_save(self, ed) -> None:
        old = next((k for k, v in self.editors.items() if v is ed), None)
        new = str(Path(ed.path).resolve()).lower()
        if old != new:
            self.editors.pop(old, None)
            self.editors[new] = ed
        ed.setToolTip(str(ed.path))
        self._title(ed)
        try:
            from ..retro.filebus import file_changed
            file_changed(self.win, ed.path, ed)
        except Exception:  # noqa: BLE001
            pass

    def open_design(self, path: Path):
        from PyQt6.QtWidgets import QMessageBox
        from ..retro.design.game import load
        from ..retro.design.game.ui import GameDesigner
        path = Path(path).resolve()
        key = str(path).lower()
        ed = self.editors.get(key)
        if ed is not None and ed not in self._alive():
            ed = None
        if ed is None:
            try:
                design = load(path)
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(self.win, "Game Designer", f"Cannot open {path.name}:\n{e}")
                return None
            ed = GameDesigner(design, path, log=self._log)
            ed.setToolTip(str(path))
            ed.retro_path = str(path)
            self._register(ed, key)
        self.win._show_tab(ed, ed.title())
        return ed

    def project_system(self) -> str | None:
        """The designer that fits the open project: retro-* projects by their system, DOS projects -> mode 13h."""
        p = getattr(self.win, "project", None)
        lang = str(getattr(p, "language", "") or "") if p is not None else ""
        if lang.startswith("dos-"):
            return "dos13h"
        try:
            from ..languages import get_plugin
            system = getattr(get_plugin(lang), "system", "") if lang else ""
        except Exception:  # noqa: BLE001
            system = ""
        return system if system in ("a2600", "nes", "gb") else None

    def new_for_project(self):
        system = self.project_system()
        return self.new_design(system) if system else None

    def designs_folder(self) -> Path | None:
        p = getattr(self.win, "project", None)
        return Path(p.folder) / "Designs" if p is not None else None

    def new_design(self, system: str, name: str | None = None, folder: Path | None = None, ask: bool = True,
                   **opts):
        """A new design of *system*. In a project it is saved straight into <project>/Designs (and its code
        generated); without a project it stays untitled until File > Save."""
        import os
        from PyQt6.QtWidgets import QInputDialog
        from ..retro.design.game import EXTS, TITLES, new_design
        from ..retro.design.game.ui import GameDesigner
        ext = next(e for e, s in EXTS.items() if s == system)
        folder = folder or self.designs_folder()
        default = {"a2600": "Screen", "nes": "Level", "gb": "Map", "dos13h": "Screen"}[system]
        if name is None:
            n = 1
            while folder is not None and (folder / f"{default}{n}{ext}").exists():
                n += 1
            name = f"{default}{n}"
            if ask and os.environ.get("QT_QPA_PLATFORM", "") != "offscreen":
                text, ok = QInputDialog.getText(self.win, TITLES[system], "Name:", text=name)
                if not ok or not text.strip():
                    return None
                name = text.strip()
        if system == "nes" and ask and "screens" not in opts and os.environ.get("QT_QPA_PLATFORM", "") != "offscreen":
            n, ok = QInputDialog.getInt(self.win, TITLES[system], "Screens (side by side):", 2, 1, 8)
            if not ok:
                return None
            opts["screens"] = n
        design = new_design(system, name, **opts)
        lang = str(getattr(getattr(self.win, "project", None), "language", "") or "")
        if system == "dos13h" and lang in ("dos-qbasic", "dos-c", "dos-asm"):
            design.settings["target"] = {"dos-qbasic": "freebasic", "dos-c": "watcom", "dos-asm": "nasm"}[lang]
        path = (folder / f"{name}{ext}") if folder is not None else None
        ed = GameDesigner(design, path, log=self._log)
        key = str(path.resolve()).lower() if path else f"untitled:{id(ed)}"
        self._register(ed, key)
        if path is not None:
            ed.save()
            ed.retro_path = str(path)
            try:
                self.win._fill_solution()
            except Exception:  # noqa: BLE001
                pass
        self.win._show_tab(ed, ed.title())
        return ed

    def open_dialog(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        from ..retro.design.game import EXTS
        start = str(self.designs_folder() or "")
        pats = " ".join(f"*{e}" for e in EXTS)
        f, _ = QFileDialog.getOpenFileName(self.win, "Open Game Design", start, f"Game designs ({pats})")
        if f:
            self.open_design(Path(f))

    def save_all(self) -> None:
        for e in self._alive():
            if e.is_modified() and e.path is not None:
                e.save()


def install(win) -> None:
    if getattr(win, "retro_designs", None) is None:
        RetroDesignFeature(win)
