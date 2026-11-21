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
        m.addSeparator()
        m.addAction("Atari 2600 Playfield Editor", lambda: self.open_playfield(None))
        m.addAction("Tile Map Editor", lambda: self.open_map(None))
        m.addSeparator()
        m.addAction("Text Table Editor (.tbl)...", self.open_table_dialog)
        m.addAction("New Text Table", lambda: self.open_table(None))
        m.addAction("Script Dump / Insert", lambda: self.open_script())

    # ------------------------------------------------------------ window wrapping
    def _wrap(self) -> None:
        win = self.win
        orig_open_any = win.open_any_file
        orig_any_modified = win._any_modified
        orig_save_all = win.save_all

        def open_any_file(path, *a, **k):
            kind = OPEN_EXTS.get(Path(path).suffix.lower())
            if kind is not None:
                return self.open_path(Path(path), kind)
            return orig_open_any(path, *a, **k)

        def any_modified(*a, **k):
            return any(self._alive(d) and d.is_modified() for d in self.docs) or orig_any_modified(*a, **k)

        def save_all(*a, **k):
            for d in list(self.docs):
                if self._alive(d) and d.is_modified() and d.retro_path is not None:
                    try:
                        d.save()
                    except Exception as e:  # noqa: BLE001
                        win.log(f"[retro graphics] saving {d.title()} failed: {e}")
            return orig_save_all(*a, **k)

        win.open_any_file = open_any_file
        win._any_modified = any_modified
        win.save_all = save_all
        # the hex editor (editor_extras) and web_workspace wrap the openers from a 0 ms timer: wrap again
        # after them so .chr / .tbl / .rtmap / .rtpf reach these editors first
        QTimer.singleShot(0, self._wrap_late)

    def _wrap_late(self) -> None:
        win = self.win
        for name in ("open_any_file", "open_file"):
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
