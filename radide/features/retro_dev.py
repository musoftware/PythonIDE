"""Retro game development in the IDE (radide/retro/dev, radide/languages/retro_*.py, docs/RETRO.md).

* Error List: after Build / F5 the rows of the last build (DASM, ca65 / ld65 / cc65, RGBDS, sjasmplus messages,
  radide/retro/dev/errors.py) replace the old ones; double-click opens file:line.
* Editors of retro sources keep their own IntelliSense (6502 / SM83 / Z80): the x86 assembly overlay of
  radide/features/asm_ide.py is kept away from them.
* Tools > Retro > Retro Development: Disassemble ROM into Project..., Re-disassemble with Hints, Rebuild Check,
  Import Labels into Hints..., Retro Toolchains... (DASM, cc65, RGBDS, sjasmplus: status and one-click download).
* Disassembly projects: hints.json shows in Solution Explorer (open, re-disassemble, import labels from a ca65
  .dbg / RGBDS .sym / Mesen .mlb / FCEUX .nl file); the source editor's and the hex editor's context menus have
  "Disassembly Hints" (mark as code / data / jump table / RTS jump table, add a label or comment) - the hint goes
  into hints.json and the ROM is disassembled again.
"""
from __future__ import annotations

import threading
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)


def _is_retro(project) -> bool:
    try:
        from ..retro.dev.systems import is_retro_project
        return is_retro_project(project)
    except Exception:  # noqa: BLE001
        return False


def _tr(text: str) -> str:
    try:
        from .. import i18n
        return i18n.tr(text)
    except Exception:  # noqa: BLE001
        return text


# ============================================================================ editor overlay guard
def keep_retro_plugin(plugin, path):
    """MonacoEditor.plugin_overlays entry (first in the list): a retro plugin stays itself, so the x86 assembly
    overlay that comes after it never replaces its 6502 / SM83 / Z80 IntelliSense."""
    if plugin is not None and getattr(plugin, "retro_dev", False):
        return plugin
    return None


# ============================================================================ Error List
def diag_provider(win) -> list:
    project = getattr(win, "project", None)
    if not _is_retro(project):
        return []
    from ..retro.dev.build import read_diagnostics
    from ..tools import Diag
    data = read_diagnostics(Path(project.folder))
    if not data or data.get("ok"):
        return []
    return [Diag(x["severity"], x["message"], x.get("file", ""), max(1, int(x.get("line") or 1)))
            for x in data.get("diags", [])]


def render_build_rows(win) -> None:
    from PyQt6.QtWidgets import QTreeWidgetItem
    project = getattr(win, "project", None)
    el = getattr(win, "error_list", None)
    if el is None or not _is_retro(project):
        return
    from ..retro.dev.build import read_diagnostics
    data = read_diagnostics(Path(project.folder))
    if not data:
        return
    for i in reversed(range(el.topLevelItemCount())):
        it = el.topLevelItem(i)
        if it.text(0) in ("Error", "Warning"):
            el.takeTopLevelItem(i)
    for x in data.get("diags", []):
        it = QTreeWidgetItem([x["severity"], x["message"], x.get("file", ""), str(max(1, int(x.get("line") or 1)))])
        colour = {"Error": Qt.GlobalColor.darkRed, "Warning": Qt.GlobalColor.darkYellow}.get(x["severity"])
        if colour is not None:
            it.setForeground(0, colour)
        el.addTopLevelItem(it)
    errors = sum(x["severity"] == "Error" for x in data.get("diags", []))
    warnings = sum(x["severity"] == "Warning" for x in data.get("diags", []))
    try:
        win.dock_errors.setWindowTitle(f"{_tr('Error List')} ({errors} errors, {warnings} warnings)")
        if not data.get("ok"):
            win.dock_errors.show()
            win.dock_errors.raise_()
    except Exception:  # noqa: BLE001
        pass


def _attach_session(win, s) -> None:
    state = {"buf": "", "done": False}

    def on_output(text: str) -> None:
        if state["done"]:
            return
        state["buf"] = (state["buf"] + text)[-4000:]
        if "Build succeeded" in state["buf"] or "Build failed" in state["buf"]:
            state["done"] = True
            QTimer.singleShot(0, lambda: render_build_rows(win))

    try:
        s.output.connect(on_output)
        s.finished.connect(lambda *_a: None if state["done"] else render_build_rows(win))
    except Exception:  # noqa: BLE001 - another kind of session
        pass


# ============================================================================ worker relay
class _Relay(QObject):
    log = pyqtSignal(str)
    done = pyqtSignal(object)


# ============================================================================ Disassemble ROM dialog
class DisassembleDialog(QDialog):
    """Pick a ROM (the user's own file), the system, where the project goes; disassemble + rebuild check."""

    SYSTEM_ITEMS = [("", "Detect from the file"), ("atari2600", "Atari 2600 (.bin / .a26)"),
                    ("nes", "NES (.nes)"), ("gameboy", "Game Boy (.gb / .gbc)"), ("c64", "Commodore 64 (.prg)"),
                    ("zx", "ZX Spectrum (.tap, or raw code + load address)")]

    def __init__(self, win, rom: str = ""):
        super().__init__(win)
        self.win = win
        self.result_obj = None
        self.setWindowTitle(_tr("Disassemble ROM into Project"))
        self.resize(720, 560)
        lay = QVBoxLayout(self)
        intro = QLabel(_tr("Turns a ROM or program file that you own into a project you can edit and rebuild: "
                           "the code is traced from the reset / interrupt vectors, hardware registers get their "
                           "names, and the new source is assembled again and compared with the original byte "
                           "for byte."))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        form = QFormLayout()
        self.rom = QLineEdit(rom)
        b = QPushButton(_tr("Browse..."))
        b.clicked.connect(self.browse)
        row = QHBoxLayout()
        row.addWidget(self.rom, 1)
        row.addWidget(b)
        w = QWidget()
        w.setLayout(row)
        form.addRow(_tr("ROM file:"), w)
        self.system = QComboBox()
        for sid, title in self.SYSTEM_ITEMS:
            self.system.addItem(_tr(title), sid)
        form.addRow(_tr("System:"), self.system)
        self.base = QLineEdit()
        self.base.setPlaceholderText(_tr("raw ZX code only, e.g. 8000"))
        form.addRow(_tr("Load address (hex):"), self.base)
        self.entry = QLineEdit()
        self.entry.setPlaceholderText(_tr("optional, hex"))
        form.addRow(_tr("Entry point (hex):"), self.entry)
        self.undoc = QCheckBox(_tr("Follow undocumented 6502 opcodes"))
        form.addRow("", self.undoc)
        self.folder = QLineEdit()
        fb = QPushButton(_tr("Browse..."))
        fb.clicked.connect(self.browse_folder)
        row2 = QHBoxLayout()
        row2.addWidget(self.folder, 1)
        row2.addWidget(fb)
        w2 = QWidget()
        w2.setLayout(row2)
        form.addRow(_tr("Project folder:"), w2)
        lay.addLayout(form)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        lay.addWidget(self.log, 1)
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.summary)
        self.buttons = QDialogButtonBox()
        self.go = self.buttons.addButton(_tr("Disassemble"), QDialogButtonBox.ButtonRole.ActionRole)
        self.open_btn = self.buttons.addButton(_tr("Open Project"), QDialogButtonBox.ButtonRole.AcceptRole)
        self.open_btn.setEnabled(False)
        self.buttons.addButton(QDialogButtonBox.StandardButton.Close)
        self.go.clicked.connect(self.run)
        self.open_btn.clicked.connect(self.open_project)
        self.buttons.rejected.connect(self.reject)
        lay.addWidget(self.buttons)
        self.relay = _Relay()
        self.relay.log.connect(self.log.appendPlainText)
        self.relay.done.connect(self.finished)
        if rom:
            self._suggest_folder()

    def browse(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, _tr("ROM file"), "", "ROM / program files (*.bin *.a26 *.nes *.gb "
                                           "*.gbc *.prg *.tap);;All files (*)")
        if f:
            self.rom.setText(f)
            self._suggest_folder()

    def browse_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(self, _tr("Project folder"), self.folder.text())
        if d:
            self.folder.setText(d)

    def _suggest_folder(self) -> None:
        p = Path(self.rom.text())
        if p.name and not self.folder.text():
            try:
                from ..dialogs import default_location
                base = default_location()
            except Exception:  # noqa: BLE001
                base = Path.home()
            self.folder.setText(str(base / f"{p.stem}_disasm"))
        try:
            from ..retro.cpu.romfmt import detect
            sid = detect(p, p.read_bytes() if p.is_file() and p.stat().st_size < 16_000_000 else b"")
            i = self.system.findData(sid)
            if i >= 0 and self.system.currentIndex() == 0:
                self.system.setCurrentIndex(i)
        except OSError:
            pass

    @staticmethod
    def _hex(text: str):
        t = text.strip().lstrip("$").replace("0x", "")
        return int(t, 16) if t else None

    def run(self) -> None:
        rom, folder = self.rom.text().strip(), self.folder.text().strip()
        if not rom or not Path(rom).is_file() or not folder:
            QMessageBox.warning(self, self.windowTitle(), _tr("Choose a ROM file and a project folder."))
            return
        try:
            base, entry = self._hex(self.base.text()), self._hex(self.entry.text())
        except ValueError:
            QMessageBox.warning(self, self.windowTitle(), _tr("Addresses are hexadecimal numbers, e.g. 8000."))
            return
        system = self.system.currentData() or None
        undoc = self.undoc.isChecked()
        self.go.setEnabled(False)
        self.log.clear()
        self.summary.setText(_tr("Working..."))

        def work():
            from ..retro.dev.fromrom import create_project
            try:
                res = create_project(rom, folder, None, system, base, entry, undoc, log=self.relay.log.emit)
            except Exception as e:  # noqa: BLE001 - shown to the user
                res = e
            self.relay.done.emit(res)
        threading.Thread(target=work, daemon=True).start()

    def finished(self, res) -> None:
        self.go.setEnabled(True)
        if isinstance(res, Exception):
            self.summary.setText(f"{_tr('Could not disassemble')}: {res}")
            return
        self.result_obj = res
        txt = res.summary()
        same = (res.identical or {}).get("same")
        colour = "#1B7F1B" if same else "#B00020"
        self.summary.setText(f"<span style='color:{colour}'>" + txt.replace("\n", "<br>") + "</span>")
        self.open_btn.setEnabled(True)

    def open_project(self) -> None:
        if self.result_obj is not None:
            folder = self.result_obj.folder
            self.accept()
            try:
                self.win.open_project(folder)
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(self.win, _tr("Open Project"), str(e))


def show_disassemble(win, rom: str = "") -> None:
    DisassembleDialog(win, rom).exec()


def redisassemble(win, ask: bool = True):
    project = getattr(win, "project", None)
    s = ((getattr(project, "extra", {}) or {}).get("retro") or {}) if project is not None else {}
    if not s.get("disassembly"):
        QMessageBox.information(win, _tr("Re-disassemble with Hints"),
                                _tr("The active project was not made with 'Disassemble ROM into Project'."))
        return None
    if ask and QMessageBox.question(win, _tr("Re-disassemble with Hints"),
                                    _tr("Disassemble the original ROM again with hints.json? The main source is "
                                        "saved as a .bak file first and then replaced.")) != \
            QMessageBox.StandardButton.Yes:
        return None
    try:
        from ..retro.dev.fromrom import redisassemble as redo
        res = redo(project.folder, log=win.log)
    except Exception as e:  # noqa: BLE001
        QMessageBox.warning(win, _tr("Re-disassemble with Hints"), str(e))
        return None
    win.log(res.summary())
    try:
        for i in range(win.tabs.count()):
            w = win.tabs.widget(i)
            if hasattr(w, "path") and Path(str(w.path)).name == res.main and hasattr(w, "setText"):
                w.setText((Path(project.folder) / res.main).read_text(encoding="utf-8"))
                if hasattr(w, "setModified"):
                    w.setModified(False)
    except Exception:  # noqa: BLE001
        pass
    QMessageBox.information(win, _tr("Re-disassemble with Hints"), res.summary())
    return res


# ============================================================================ disassembly hints
def disasm_project_folder(path) -> Path | None:
    """The folder of the disassembly project that *path* (its source, hints.json or rom/ copy) belongs to."""
    import json
    try:
        p = Path(path).resolve()
    except (OSError, TypeError):
        return None
    for d in [p] + list(p.parents)[:3]:
        rp = d / "project.radproj"
        if rp.is_file():
            try:
                data = json.loads(rp.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
            return d if ((data.get("retro") or {}).get("disassembly")) else None
    return None


def _activate_folder(win, folder: Path) -> None:
    proj = getattr(win, "project", None)
    try:
        if proj is not None and Path(proj.folder).resolve() == folder.resolve():
            return
        for st in getattr(win, "_pstates", {}).values():
            pr = st.get("project") if isinstance(st, dict) else None
            if pr is not None and Path(pr.folder).resolve() == folder.resolve():
                win.activate_project(pr)
                return
    except Exception:  # noqa: BLE001
        pass


def redisassemble_folder(win, folder, ask: bool = True):
    """Re-disassemble the project in *folder*: through the IDE when it is the active project (open editors are
    refreshed), else directly."""
    folder = Path(folder)
    _activate_folder(win, folder)
    proj = getattr(win, "project", None)
    try:
        active = proj is not None and Path(proj.folder).resolve() == folder.resolve()
    except OSError:
        active = False
    if active:
        return redisassemble(win, ask=ask)
    if ask and QMessageBox.question(win, _tr("Re-disassemble with Hints"),
                                    _tr("Disassemble the original ROM again with hints.json? The main source is "
                                        "saved as a .bak file first and then replaced.")) !=             QMessageBox.StandardButton.Yes:
        return None
    from ..retro.dev.fromrom import redisassemble as redo
    try:
        res = redo(folder, log=win.log)
    except Exception as e:  # noqa: BLE001
        QMessageBox.warning(win, _tr("Re-disassemble with Hints"), str(e))
        return None
    win.log(res.summary())
    QMessageBox.information(win, _tr("Re-disassemble with Hints"), res.summary())
    return res


def apply_hint(win, folder, kind: str, start: int, end: int | None = None, text: str = "",
               redo: bool = True):
    """Write one hint into hints.json and (by default) disassemble again."""
    from ..retro.dev.fromrom import add_hint
    folder = Path(folder)
    try:
        add_hint(folder, kind, start, end, text)
    except (OSError, ValueError) as e:
        QMessageBox.warning(win, _tr("Disassembly Hints"), str(e))
        return None
    what = {"code": "code", "data": "data", "word_table": "jump table", "rts_table": "RTS jump table",
            "label": f"label {text}", "comment": "comment"}[kind]
    rng = f"${start:04X}" + (f"-${end:04X}" if end is not None and end != start else "")
    win.log(f"[disassembly] hint: {rng} = {what} (hints.json)")
    try:
        win._fill_solution()
    except Exception:  # noqa: BLE001
        pass
    if not redo:
        return True
    return redisassemble_folder(win, folder, ask=False)


def _ask_text(win, title: str, label: str) -> str:
    from PyQt6.QtWidgets import QInputDialog
    text, ok = QInputDialog.getText(win, title, label)
    return text.strip() if ok else ""


def _hint_submenu(win, menu, folder: Path, start: int | None, end: int | None, where: str):
    sub = menu.addMenu(_tr("Disassembly Hints"))
    if start is None:
        a = sub.addAction(_tr("(no address on this line)"))
        a.setEnabled(False)
    else:
        rng = f"${start:04X}" + (f"-${end:04X}" if end is not None and end != start else "")
        sub.addAction(f"{_tr('Mark as Code')} ({rng[:5]})", lambda: apply_hint(win, folder, "code", start))
        sub.addAction(f"{_tr('Mark as Data')} ({rng})", lambda: apply_hint(win, folder, "data", start, end))
        sub.addAction(f"{_tr('Mark as Jump Table (addresses)')} ({rng})",
                      lambda: apply_hint(win, folder, "word_table", start, end))
        sub.addAction(f"{_tr('Mark as RTS Jump Table (address-1)')} ({rng})",
                      lambda: apply_hint(win, folder, "rts_table", start, end))
        sub.addSeparator()

        def label():
            t = _ask_text(win, _tr("Add Label"), f"{_tr('Label name for')} ${start:04X}:")
            if t:
                apply_hint(win, folder, "label", start, text=t)

        def comment():
            t = _ask_text(win, _tr("Add Comment"), f"{_tr('Comment above')} ${start:04X}:")
            if t:
                apply_hint(win, folder, "comment", start, text=t)
        sub.addAction(_tr("Add Label..."), label)
        sub.addAction(_tr("Add Comment..."), comment)
    sub.addSeparator()
    sub.addAction(_tr("Re-disassemble with Hints"), lambda: redisassemble_folder(win, folder))
    sub.addAction(_tr("Open hints.json"), lambda: win.open_any_file(folder / "hints.json"))
    sub.setProperty("radHintWhere", where)
    return sub


def editor_hint_range(ed) -> tuple[int | None, int | None]:
    """(first, last) address of the selected lines (or the current line) of a disassembly source."""
    from ..retro.dev.fromrom import address_of_line
    l1 = l2 = None
    sel = getattr(ed, "_selection", None)
    if isinstance(sel, tuple) and len(sel) == 4 and (sel[0], sel[1]) != (sel[2], sel[3]):
        l1, l2 = min(sel[0], sel[2]), max(sel[0], sel[2])
    else:
        try:
            c = ed.textCursor()
            if c.hasSelection() and hasattr(ed, "document"):
                doc = ed.document()
                l1 = doc.findBlock(c.selectionStart()).blockNumber()
                l2 = doc.findBlock(max(c.selectionStart(), c.selectionEnd() - 1)).blockNumber()
        except Exception:  # noqa: BLE001
            pass
    if l1 is None:
        l1 = l2 = ed.getCursorPosition()[0]
    n = ed.lines()
    start = None
    for ln in range(l1, min(n, l1 + 4)):                 # a label line: the address is on the next line
        start = address_of_line(ed.text(ln))
        if start is not None:
            break
    if start is None:
        return None, None
    end = start
    for ln in range(l2 + 1, min(n, l2 + 6)):             # the next line's address - 1 = the last byte
        a = address_of_line(ed.text(ln))
        if a is not None:
            end = max(start, a - 1)
            break
    return start, end


def editor_hint_menu(win, ed, menu):
    """Context menu of a source editor: "Disassembly Hints" when the file belongs to a disassembly project."""
    path = getattr(ed, "path", None)
    if path is None or Path(path).suffix.lower() not in (".s", ".asm"):
        return None
    folder = disasm_project_folder(path)
    if folder is None:
        return None
    start, end = editor_hint_range(ed)
    menu.addSeparator()
    return _hint_submenu(win, menu, folder, start, end, "editor")


_IMAGES: dict = {}


def _rom_image(path: Path):
    from ..retro.cpu import romfmt
    key = (str(path).lower(), path.stat().st_mtime_ns)
    img = _IMAGES.get(key)
    if img is None:
        img = romfmt.load(path)
        _IMAGES.clear()
        _IMAGES[key] = img
    return img


def hex_hint_menu(win, doc, menu, offset: int, sel):
    """HexDocument.menu_hooks entry: hints from file offsets of a disassembly project's ROM (rom/<file>)."""
    path = getattr(doc, "path", None)
    if path is None:
        return None
    folder = disasm_project_folder(path)
    if folder is None:
        return None
    from ..retro.cpu.romfmt import file_to_cpu
    try:
        img = _rom_image(Path(path))
    except (OSError, ValueError):
        return None
    s0, n = sel
    first = s0 if n else offset
    last = s0 + n - 1 if n else offset
    a = file_to_cpu(img, first)
    b = file_to_cpu(img, last)
    menu.addSeparator()
    return _hint_submenu(win, menu, folder, a[0] if a else None, b[0] if b else (a[0] if a else None), "hex")


def import_labels_dialog(win, folder=None, path: str | None = None):
    project = getattr(win, "project", None)
    folder = Path(folder) if folder else (Path(project.folder) if project is not None else None)
    if folder is None or disasm_project_folder(folder / "project.radproj") is None:
        QMessageBox.information(win, _tr("Import Labels"),
                                _tr("The active project was not made with 'Disassemble ROM into Project'."))
        return None
    if path is None:
        from ..retro.cpu.labels import LABEL_FILTER
        path, _ = QFileDialog.getOpenFileName(win, _tr("Import Labels into Hints"), str(folder), LABEL_FILTER)
        if not path:
            return None
    from ..retro.dev.fromrom import import_labels
    try:
        n, kind = import_labels(folder, path)
    except (OSError, ValueError) as e:
        QMessageBox.warning(win, _tr("Import Labels"), str(e))
        return None
    win.log(f"[disassembly] {n} labels imported from {Path(path).name} ({kind}) into hints.json")
    res = redisassemble_folder(win, folder, ask=True) if n else None
    return n, res


# ---------------------------------------------------------------------------- Solution Explorer node
def _add_hint_nodes(win) -> None:
    from PyQt6.QtWidgets import QTreeWidgetItem
    try:
        from .solution_ui import PROJECT_ROLE
    except ImportError:
        return
    role = Qt.ItemDataRole.UserRole
    tree = win.solution
    stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    while stack:
        it = stack.pop()
        stack.extend(it.child(i) for i in range(it.childCount()))
        data = it.data(0, role)
        if not data or data[0] != "project":
            continue
        key = it.data(0, PROJECT_ROLE)
        st = getattr(win, "_pstates", {}).get(key)
        project = st["project"] if st else None
        s = ((getattr(project, "extra", {}) or {}).get("retro") or {}) if project is not None else {}
        if not s.get("disassembly"):
            continue
        if any((it.child(i).data(0, role) or ("",))[0] == "retro_hints" for i in range(it.childCount())):
            continue
        hp = Path(project.folder) / "hints.json"
        n = QTreeWidgetItem(["hints.json  (disassembly hints)"])
        n.setData(0, role, ("retro_hints", str(hp)))
        n.setData(0, PROJECT_ROLE, key)
        n.setToolTip(0, _tr("Code / data / jump table hints and labels for Re-disassemble with Hints "
                            "(double-click: open; right-click: re-disassemble, import labels)"))
        n.setIcon(0, win.style().standardIcon(win.style().StandardPixmap.SP_FileDialogInfoView))
        it.insertChild(0, n)


def _tree_dclick(win, item, _col) -> None:
    data = item.data(0, Qt.ItemDataRole.UserRole)
    if data and data[0] == "retro_hints":
        win.open_any_file(Path(data[1]))


def hints_tree_menu(win, item, m) -> None:
    data = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
    if not data or data[0] != "retro_hints":
        return
    folder = Path(data[1]).parent
    m.addSeparator()
    m.addAction(_tr("Open hints.json"), lambda: win.open_any_file(Path(data[1])))
    m.addAction(_tr("Re-disassemble with Hints"), lambda: redisassemble_folder(win, folder))
    m.addAction(_tr("Import Labels (.dbg / .sym / .mlb / .nl)..."), lambda: import_labels_dialog(win, folder))


def rebuild_check(win) -> None:
    project = getattr(win, "project", None)
    if not _is_retro(project):
        QMessageBox.information(win, _tr("Rebuild Check"), _tr("Open a retro game project first."))
        return
    from ..retro.dev.build import Builder
    lines: list[str] = []
    from .. import progress

    def work(r):                           # worker thread: assembler run (+ a toolchain download the first time)
        def say(t):
            lines.append(t)
            r.log(t)
        b = Builder(Path(project.folder), project, log=say)
        return b, b.build()
    b, ok = progress.run_blocking(win, "Rebuild Check", work)
    render_build_rows(win)
    for ln in lines:
        win.log(ln)
    if not ok:
        QMessageBox.warning(win, _tr("Rebuild Check"), _tr("The build failed - see the Error List."))
        return
    if not b.s.get("original"):
        QMessageBox.information(win, _tr("Rebuild Check"), f"{_tr('Built')} {b.out_path.name}")
        return
    from ..retro.dev.build import read_diagnostics
    same = (read_diagnostics(Path(project.folder)) or {}).get("identical") or {}
    msg = (_tr("Byte-identical to the original ROM.") if same.get("same") else
           f"{_tr('Different from the original ROM')}: {same.get('reason', '')}")
    QMessageBox.information(win, _tr("Rebuild Check"), msg)


# ============================================================================ toolchains dialog
class RetroToolchainsDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.setWindowTitle(_tr("Retro Toolchains"))
        self.resize(780, 420)
        lay = QVBoxLayout(self)
        intro = QLabel(_tr("Assemblers of the retro game projects. They are downloaded from their official "
                           "release pages into the IDE's tools folder (no admin rights, no PATH change); the "
                           "SHA-256 of each archive is checked and recorded."))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([_tr("Tool"), _tr("Path"), ""])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        lay.addWidget(self.table, 1)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(130)
        lay.addWidget(self.log)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.relay = _Relay()
        self.relay.log.connect(self.log.appendPlainText)
        self.relay.done.connect(lambda _r: self.refresh())
        self.refresh()

    def refresh(self) -> None:
        from ..retro.dev import toolchain as tc
        rows = tc.status()
        self.table.setRowCount(len(rows))
        for i, (tool, title, path) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(title))
            self.table.setItem(i, 1, QTableWidgetItem(path or _tr("not found")))
            if not path and tool in tc.RELEASES:
                b = QPushButton(_tr("Download"))
                b.clicked.connect(lambda _c=False, t=tool: self.download(t))
                self.table.setCellWidget(i, 2, b)
            else:
                self.table.setCellWidget(i, 2, None)
                self.table.setItem(i, 2, QTableWidgetItem(_tr("ready") if path else "-"))
        self.table.resizeColumnToContents(0)

    def download(self, tool: str) -> None:
        from ..retro.dev import toolchain as tc

        def work():
            tc.install(tool, self.relay.log.emit)
            self.relay.done.emit(None)
        threading.Thread(target=work, daemon=True).start()


def show_toolchains(win) -> None:
    RetroToolchainsDialog(win).exec()


# ============================================================================ install
def install(win) -> None:
    try:
        from ..monaco_editor import MonacoEditor
        if keep_retro_plugin not in MonacoEditor.plugin_overlays:
            MonacoEditor.plugin_overlays.insert(0, keep_retro_plugin)
    except Exception:  # noqa: BLE001 - the plain editor has no overlays
        pass
    providers = getattr(win, "diag_providers", None)
    if providers is None:
        win.diag_providers = providers = []
    providers.append(diag_provider)

    orig = getattr(win, "_make_session", None)
    if callable(orig):
        def make_session(spec, debug, plugin, interp, startup=None):
            s = orig(spec, debug, plugin, interp, startup)
            try:
                if s is not None and getattr(plugin, "retro_dev", False):
                    _attach_session(win, s)
            except Exception:  # noqa: BLE001 - never stop F5
                pass
            return s
        win._make_session = make_session

    win.show_retro_disassemble = lambda rom="": show_disassemble(win, rom)
    win.show_retro_toolchains = lambda: show_toolchains(win)
    _install_hints_ui(win)
    try:
        from ..retro.menu import section
        m = section(win, "Retro &Development")
    except Exception:  # noqa: BLE001
        m = None
    if m is None:
        return
    a = m.addAction("Disassemble ROM into Project...")
    a.setStatusTip("Turn a ROM you own (2600, NES, Game Boy, C64, ZX) into a project that rebuilds byte-identical")
    a.triggered.connect(lambda: show_disassemble(win))
    win.a_retro_disassemble = a
    m.addAction("Re-disassemble with Hints").triggered.connect(lambda: redisassemble(win))
    m.addAction("Rebuild Check (compare with the original)").triggered.connect(lambda: rebuild_check(win))
    m.addAction("Import Labels into Hints...").triggered.connect(lambda: import_labels_dialog(win))
    m.addSeparator()
    m.addAction("Retro Toolchains...").triggered.connect(lambda: show_toolchains(win))


def _install_hints_ui(win) -> None:
    """Disassembly hints in the source editor, the hex editor and Solution Explorer."""
    try:
        from .. import editor as editor_mod

        def hook(ed):
            if getattr(ed, "contextMenuAboutToShow", None) is not None:
                ed.contextMenuAboutToShow.connect(lambda m, e=ed: editor_hint_menu(win, e, m))
        hook._rad_retro_hints = True
        if not any(getattr(h, "_rad_retro_hints", False) for h in editor_mod.EDITOR_HOOKS):
            editor_mod.EDITOR_HOOKS.append(hook)
    except Exception as e:  # noqa: BLE001
        win.log(f"[retro dev] editor hints menu: {e}")
    try:
        from ..retro.rom.hexdoc import HexDocument

        def hex_hook(doc, menu, offset, sel):
            hex_hint_menu(win, doc, menu, offset, sel)
        hex_hook._rad_retro_hints = True
        HexDocument.menu_hooks[:] = [h for h in HexDocument.menu_hooks if not getattr(h, "_rad_retro_hints", False)]
        HexDocument.menu_hooks.append(hex_hook)
    except Exception as e:  # noqa: BLE001
        win.log(f"[retro dev] hex hints menu: {e}")
    try:
        from . import solution_ui
        solution_ui.MENU_HOOKS.append(lambda w, item, m: hints_tree_menu(win, item, m) if w is win else None)
    except Exception:  # noqa: BLE001
        pass
    orig_fill = getattr(win, "_fill_solution", None)
    if callable(orig_fill):
        def fill_solution(*a, **k):
            r = orig_fill(*a, **k)
            try:
                _add_hint_nodes(win)
            except Exception as e:  # noqa: BLE001 - never break Solution Explorer
                win.log(f"[retro dev] {e}")
            return r
        win._fill_solution = fill_solution
    try:
        win.solution.itemDoubleClicked.connect(lambda item, col: _tree_dclick(win, item, col))
    except Exception:  # noqa: BLE001
        pass
