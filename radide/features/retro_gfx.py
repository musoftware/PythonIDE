"""Retro graphics and game-text tools in the IDE (radide/retro/gfx, docs/RETRO.md):

* Tools > Retro > Graphics && Text: Tile Editor (open any ROM / binary), Atari 2600 Playfield Editor,
  Tile Map Editor, Text Table Editor, Script Dump / Insert;
* opening a ``.chr`` file shows the Tile Editor, ``.tbl`` the Text Table Editor, ``.rtmap`` the Tile Map
  Editor and ``.rtpf`` the Playfield Editor (File > Open File, Solution Explorer);
* the documents join File > Save / Save All and the "save changes?" prompts; writing into a ROM refreshes
  the other open editors of that file (radide/retro/filebus.py).
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QFileDialog

OPEN_EXTS = {".chr": "tiles", ".tbl": "table", ".rtmap": "map", ".rtpf": "playfield"}
ROM_FILTER = ("ROMs and binaries (*.nes *.chr *.gb *.gbc *.gba *.sfc *.smc *.md *.gen *.bin *.a26 *.prg *.spr "
              "*.64c *.rom);;All files (*)")


class RetroGfx:
    def __init__(self, win):
        self.win = win
        self.docs: list = []
        self._menus()
        self._wrap()

    # ------------------------------------------------------------ menus
    def _menus(self) -> None:
        from ..retro.menu import section
        m = section(self.win, "&Graphics && Text")
        self.menu = m
        m.addAction("Tile Editor (Open ROM / Binary)...", self.open_tiles_dialog)
        m.addAction("New Tile Sheet (8 KB CHR)", lambda: self.open_tiles(None))
        m.addAction("View Current File as Tiles", self.tiles_from_current)
        m.addSeparator()
        m.addAction("Atari 2600 Playfield Editor", lambda: self.open_playfield(None))
        m.addAction("Tile Map Editor", lambda: self.open_map(None))
        m.addSeparator()
        m.addAction("Text Table Editor (.tbl)...", self.open_table_dialog)
        m.addAction("New Text Table", lambda: self.open_table(None))
        m.addAction("Script Dump / Insert", lambda: self.open_script())

    # ------------------------------------------------------------ window wrapping
    # DocumentProvider (radide/extension_points.py, priority EDITOR - before the hex views): .chr / .tbl /
    # .rtmap / .rtpf from File > Open, Save All, closing question
    def can_open(self, path: Path) -> bool:
        return Path(path).suffix.lower() in OPEN_EXTS

    def open_document(self, path: Path):
        return self.open_path(Path(path), OPEN_EXTS[Path(path).suffix.lower()])

    def has_modified_documents(self) -> bool:
        return any(self._alive(d) and d.is_modified() for d in self.docs)

    def save_documents(self) -> bool:
        ok = True
        for d in list(self.docs):
            if self._alive(d) and d.is_modified() and d.retro_path is not None:
                try:
                    d.save()
                except Exception as e:  # noqa: BLE001 - reported; the other documents still save
                    self.win.log(f"[retro graphics] saving {d.title()} failed: {e}")
                    ok = False
        return ok

    def _wrap(self) -> None:
        self.win.extension_points.add_document_provider(self)
        # win.open_file (web_workspace) is wrapped by the hex views from a 0 ms timer: wrap it again after
        # them so .chr / .tbl / .rtmap / .rtpf reach these editors there too.
        # TODO(stage B): one way to open files in MainWindow; then this wrapper goes as well.
        QTimer.singleShot(0, self._wrap_late)

    def _wrap_late(self) -> None:
        win = self.win
        for name in ("open_file",):
            orig = getattr(win, name, None)
            if not callable(orig) or getattr(orig, "_retro_gfx", False):
                continue

            def opener(path, *a, _orig=orig, **k):
                p = Path(path)
                if not p.is_absolute() and getattr(win, "project", None) is not None:
                    p = Path(win.project.folder) / p
                kind = OPEN_EXTS.get(p.suffix.lower())
                if kind is not None and p.is_file():
                    return self.open_path(p, kind)
                return _orig(path, *a, **k)
            opener._retro_gfx = True
            setattr(win, name, opener)

    @staticmethod
    def _alive(w) -> bool:
        try:
            w.objectName()
            return True
        except RuntimeError:
            return False

    # ------------------------------------------------------------ documents
    def _find(self, path: Path | None, cls):
        if path is None:
            return None
        for d in self.docs:
            if self._alive(d) and isinstance(d, cls) and d.retro_path is not None:
                try:
                    if d.retro_path.resolve() == path.resolve():
                        return d
                except OSError:
                    pass
        return None

    def _show(self, doc):
        self.docs = [d for d in self.docs if self._alive(d)]
        if doc not in self.docs:
            self.docs.append(doc)
            doc.modifiedChanged.connect(lambda _m, d=doc: self._retitle(d))
        if doc.retro_path is not None:
            doc.setToolTip(str(doc.retro_path))
        self.win._show_tab(doc, self._tab_title(doc))
        return doc

    @staticmethod
    def _tab_title(doc) -> str:
        return doc.title() + ("*" if doc.is_modified() else "")

    def _retitle(self, doc) -> None:
        i = self.win.tabs.indexOf(doc)
        if i >= 0:
            self.win.tabs.setTabText(i, self._tab_title(doc))

    def open_path(self, path: Path, kind: str):
        return {"tiles": self.open_tiles, "table": self.open_table, "map": self.open_map,
                "playfield": self.open_playfield}[kind](path)

    def open_tiles(self, path, fmt: str | None = None):
        from ..retro.gfx.ui_tiles import TileEditor
        path = Path(path) if path else None
        doc = self._find(path, TileEditor)
        if doc is None:
            try:
                doc = TileEditor(self.win, path, fmt=fmt)
            except OSError as e:
                self.win.log(f"[tile editor] cannot open {path}: {e}")
                return None
        return self._show(doc)

    def open_playfield(self, path):
        from ..retro.gfx.ui_playfield import PlayfieldEditor
        path = Path(path) if path else None
        return self._show(self._find(path, PlayfieldEditor) or PlayfieldEditor(self.win, path))

    def open_map(self, path):
        from ..retro.gfx.ui_tilemap import TilemapEditor
        path = Path(path) if path else None
        return self._show(self._find(path, TilemapEditor) or TilemapEditor(self.win, path))

    def open_table(self, path):
        from ..retro.gfx.ui_text import TableEditor
        path = Path(path) if path else None
        return self._show(self._find(path, TableEditor) or TableEditor(self.win, path))

    def open_script(self, rom=None, table=None):
        from ..retro.gfx.ui_text import ScriptEditor
        return self._show(ScriptEditor(self.win, rom, table))

    def tiles_from_current(self):
        """The file of the current tab (e.g. a hex editor of a ROM) in the Tile Editor, at its cursor offset."""
        w = self.win.tabs.currentWidget()
        path = getattr(w, "retro_path", None) or getattr(w, "path", None)
        if path is None or not Path(path).is_file():
            self.win.statusBar().showMessage("The current tab is not a file", 4000)
            return None
        cursor = getattr(getattr(w, "view", None), "cursor", None)
        doc = self.open_tiles(Path(path))
        if doc is not None and isinstance(cursor, int):
            doc.set_offset(cursor)
        return doc

    def _start_dir(self) -> str:
        p = getattr(self.win, "project", None)
        return str(p.folder) if p is not None else ""

    def open_tiles_dialog(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self.win, "Open ROM / Binary in the Tile Editor", self._start_dir(),
                                           ROM_FILTER)
        if f:
            self.open_tiles(Path(f))

    def open_table_dialog(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self.win, "Open Text Table", self._start_dir(),
                                           "Tables (*.tbl);;All files (*)")
        if f:
            self.open_table(Path(f))


def install(win) -> None:
    win.retro_gfx = RetroGfx(win)
