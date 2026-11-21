"""DOS projects in the IDE (radide/retro/dos, radide/languages/dos_*.py, docs/RETRO.md "DOS programs").

* Tools > Retro > DOS Programming: Build DOS Program, Run in DOSBox-X, Run in DOSBox-X Debugger, Run in My QBasic,
  Run with Captured Output, Show Last DOS Screen, Open Symbol Map, DOS Toolchains..., DOS Interrupt Reference...
* Project > DOS Project Settings...: compiler, memory model, EXE / COM, output name, main file, CPU cycles preset,
  machine, memory, keep the window, program arguments, debugger (8086 emulator / DOSBox-X).
* Error List: the rows of the last DOS build (compiler messages with file:line, compatibility warnings).
* File > Open Folder: old QBasic / Turbo Pascal / Turbo C / MASM / batch sources are offered as a DOS project.
F5 / Ctrl+F5 run ``python -m radide.retro.dos.run`` (build when needed, then DOSBox-X).
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                             QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox,
                             QSplitter, QTableWidget, QTableWidgetItem, QTextBrowser, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout)

DOS_LANGS = ("dos-qbasic", "dos-pascal", "dos-c", "dos-asm", "dos-batch")


def is_dos_project(project) -> bool:
    return project is not None and getattr(project, "language", "") in DOS_LANGS


def _english(a) -> str:
    t = a.text().replace("&", "")
    try:
        from ..i18n import english
        return english(a, t) or t
    except Exception:  # noqa: BLE001
        return t


def _menu(win, title: str):
    for a in win.menuBar().actions():
        if a.menu() is not None and _english(a) == title:
            return a.menu()
    return None


def _need_project(win, title: str) -> bool:
    if is_dos_project(getattr(win, "project", None)):
        return True
    QMessageBox.information(win, title, "Open a DOS project first (New Project > DOS: QBasic, Turbo Pascal-style, "
                                        "Turbo C-style, DOS Assembly or DOS Batch).")
    return False


# ============================================================================ Open Folder detector
KIND_TITLES = {"qbasic": "QBasic / QuickBASIC program", "pascal": "Turbo Pascal program", "c": "Turbo C program",
               "asm": "16-bit DOS assembly program", "batch": "DOS batch files"}


def detect_dos_sources(folder: Path) -> list:
    """project_detect detector: old DOS sources (.BAS / .PAS / .C / .ASM / .BAT) -> a DOS project."""
    from ..project_detect import Candidate
    from ..retro.dos import compat
    from ..retro.dos.build import LANGUAGE_OF_KIND
    from ..retro.dos.templates import dos_name
    folder = Path(folder)
    found: dict[str, list] = {}
    try:
        files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in compat.EXT_KIND]
    except OSError:
        return []
    texts = {}
    for p in files[:400]:
        try:
            text = p.read_bytes()[:200_000].decode("cp437", "replace")
        except OSError:
            continue
        kind = compat.detect_kind(p, text)
        if kind and p.suffix.lower() in (".bas", ".pas", ".c", ".asm", ".bat", ".pp"):
            found.setdefault(kind, []).append(p)
            texts[p] = text
    if not found:
        return []
    order = sorted(found, key=lambda k: (k == "batch", -len(found[k])))
    out = []
    for kind in order[:2]:
        fl = sorted(found[kind], key=lambda p: p.name.lower())
        main = _guess_main(kind, fl, texts)
        strong = any(_strong(kind, texts[p]) for p in fl)
        conf = 0.8 if strong and kind != "batch" else (0.5 if kind == "batch" else 0.62)
        c = Candidate(f"dos-{kind}", f"DOS {KIND_TITLES[kind]} ({len(fl)} file{'s' if len(fl) != 1 else ''}, main "
                      f"{main.name})", LANGUAGE_OF_KIND[kind], "app", folder, conf, [p.name for p in fl[:3]],
                      startup=main.stem, modules=[p.name for p in fl][:300])
        c.extra["dos"] = {"kind": kind, "main": main.name, "exe": dos_name(main.stem if main.stem.upper() != "MAIN"
                                                                             else folder.name)}
        comp = {"qbasic": "FreeBASIC (-lang qb)", "pascal": "Free Pascal (TP mode)", "c": "Open Watcom C",
                "asm": "JWasm"}.get(kind, "")
        c.notes.append(f"Builds with the free {comp} compiler into a real DOS program and runs in DOSBox-X; your "
                       "sources are not changed." if comp else "Runs in DOSBox-X; your files are not changed.")
        for n in compat.scan(main, texts[main], kind, folder)[:4]:
            c.notes.append(n.message)
        out.append(c)
    return out


def _strong(kind: str, text: str) -> bool:
    import re
    from ..retro.dos import compat
    if kind == "qbasic":
        return compat.has_line_numbers(text) or bool(re.search(r"(?im)^\s*(DECLARE\s+SUB|DEFINT|SCREEN\s+\d+)", text))
    if kind == "pascal":
        return bool(re.search(r"(?i)uses\s+[^;]*\b(crt|dos|graph)\b", text))
    if kind == "c":
        return bool(re.search(r"#\s*include\s*<(conio|dos|graphics|bios)\.h>", text))
    if kind == "asm":
        return bool(re.search(r"(?im)^\s*(\.model\s+(tiny|small|large|medium|compact)|org\s+100h)", text) and
                    re.search(r"(?i)\bint\s+21h", text))
    return False


def _guess_main(kind: str, files: list, texts: dict):
    import re
    rx = {"qbasic": None, "pascal": r"(?im)^\s*program\s+\w+", "c": r"\bmain\s*\(", "asm": r"(?im)^\s*end\s+\w+",
          "batch": None}[kind]
    named = [p for p in files if p.stem.upper() in ("MAIN", "GAME", "START", "PROGRAM")]
    if named:
        return named[0]
    if rx:
        hits = [p for p in files if re.search(rx, texts.get(p, ""))]
        if hits:
            return hits[0]
    return max(files, key=lambda p: len(texts.get(p, "")))


def register_detector() -> None:
    try:
        from .. import project_detect
    except Exception:  # noqa: BLE001
        return
    if detect_dos_sources not in project_detect.DETECTORS:
        project_detect.DETECTORS.append(detect_dos_sources)


# ============================================================================ Error List
def diag_provider(win) -> list:
    project = getattr(win, "project", None)
    if not is_dos_project(project):
        return []
    from ..retro.dos.build import read_diagnostics
    from ..tools import Diag
    data = read_diagnostics(Path(project.folder))
    return [Diag(x["severity"] if x["severity"] in ("Error", "Warning") else "Message", x["message"],
                 x.get("file", ""), max(1, int(x.get("line") or 1))) for x in data.get("diags", [])]


def refresh_errors(win) -> None:
    try:
        from ..tools import run_checks
        run_checks(win)
    except Exception:  # noqa: BLE001
        pass


# ============================================================================ running the CLI tools
class _Relay(QObject):
    line = pyqtSignal(str)
    done = pyqtSignal(int)


def run_tool(win, args: list[str], title: str, on_done=None) -> QProcess | None:
    """Run ``python -m radide.retro.dos.<args>`` with its output in the Output window."""
    project = getattr(win, "project", None)
    if project is None:
        return None
    try:
        win.save_all()
    except Exception:  # noqa: BLE001
        pass
    proc = QProcess(win)
    from ..retro.dos.plugin import DosPluginBase
    env = proc.processEnvironment()
    for k, v in DosPluginBase()._env().items():
        env.insert(k, v)
    proc.setProcessEnvironment(env)
    proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

    def out():
        text = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
        try:
            win.log(text.rstrip("\n"))
        except Exception:  # noqa: BLE001
            pass

    def fin(code, _status=None):
        refresh_errors(win)
        if on_done is not None:
            on_done(code)
    proc.readyReadStandardOutput.connect(out)
    proc.finished.connect(fin)
    try:
        win.dock_output.show()
        win.dock_output.raise_()
        win.log(f"------ {title} ------")
    except Exception:  # noqa: BLE001
        pass
    proc.start(sys.executable, ["-u", "-m"] + args)
    win._dos_proc = proc
    return proc


def build_program(win):
    if not _need_project(win, "Build DOS Program"):
        return None
    return run_tool(win, ["radide.retro.dos.build", str(win.project.folder)], "Build DOS Program")


def run_variant(win, extra: list[str], title: str):
    if not _need_project(win, title):
        return None
    return run_tool(win, ["radide.retro.dos.run", str(win.project.folder)] + extra, title)


def run_captured(win):
    if not _need_project(win, "Run with Captured Output"):
        return
    from PyQt6.QtWidgets import QInputDialog
    keys, ok = QInputDialog.getText(win, "Run with Captured Output",
                                    "Keys to type for the program (~ = Enter, ` = Esc, _ = Space, ^U ^D ^L ^R = "
                                    "arrows; leave empty for none):")
    if not ok:
        return
    extra = ["--capture", "--timeout", "20"] + (["--keys", keys] if keys.strip() else [])
    run_tool(win, ["radide.retro.dos.run", str(win.project.folder)] + extra, "Run with Captured Output",
             on_done=lambda _c: show_last_screen(win, quiet=True))


def show_last_screen(win, quiet: bool = False):
    """The text screen (_SCREEN.TXT) and mode 13h frame (_SCR13.RAW) of the last captured run."""
    project = getattr(win, "project", None)
    if not is_dos_project(project):
        if not quiet:
            _need_project(win, "Show Last DOS Screen")
        return None
    folder = Path(project.folder)
    raw, txt = folder / "_SCR13.RAW", folder / "_SCREEN.TXT"
    if not raw.is_file() and not txt.is_file():
        if not quiet:
            QMessageBox.information(win, "Show Last DOS Screen", "No captured screen yet: use Run with Captured "
                                                                 "Output first.")
        return None
    dlg = DosScreenDialog(win, txt if txt.is_file() else None, raw if raw.is_file() else None)
    dlg.show()
    win._dos_screen = dlg
    return dlg


def open_map(win):
    if not _need_project(win, "Open Symbol Map"):
        return
    from ..retro.dos.build import read_diagnostics
    mp = read_diagnostics(Path(win.project.folder)).get("map") or ""
    if not mp or not Path(mp).is_file():
        QMessageBox.information(win, "Open Symbol Map", "Build the program first: the build writes _build\\PROG.MAP.")
        return
    opener = getattr(win, "open_any_file", None) or getattr(win, "open_file", None)
    if opener is not None:
        opener(Path(mp))


# ============================================================================ dialogs
class DosScreenDialog(QDialog):
    def __init__(self, win, txt: Path | None, raw: Path | None):
        super().__init__(win)
        self.setWindowTitle("Last DOS Screen")
        self.resize(760, 560)
        lay = QVBoxLayout(self)
        if raw is not None:
            from PyQt6.QtGui import QImage, QPixmap
            from ..retro.dos.helpers import read_mode13
            pixels, pal = read_mode13(raw)
            img = QImage(320, 200, QImage.Format.Format_RGB32)
            for y in range(200):
                row = pixels[y * 320:(y + 1) * 320]
                for x, c in enumerate(row):
                    r, g, b = pal[c]
                    img.setPixel(x, y, (0xFF << 24) | (r << 16) | (g << 8) | b)
            self.image = img
            lab = QLabel()
            lab.setPixmap(QPixmap.fromImage(img).scaled(640, 400, Qt.AspectRatioMode.KeepAspectRatio,
                                                        Qt.TransformationMode.FastTransformation))
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(QLabel("Mode 13h frame (320 x 200), saved when the program left graphics mode:"))
            lay.addWidget(lab)
        if txt is not None:
            from PyQt6.QtGui import QFont
            view = QPlainTextEdit()
            view.setReadOnly(True)
            view.setFont(QFont("Consolas", 10))
            view.setPlainText(txt.read_bytes().decode("cp437", "replace").rstrip())
            view.setStyleSheet("QPlainTextEdit { background: #000; color: #c0c0c0; }")
            lay.addWidget(QLabel("Text screen (80 x 25):"))
            lay.addWidget(view, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


class DosSettingsDialog(QDialog):
    """Project > DOS Project Settings... (the "dos" entry of project.radproj)."""

    def __init__(self, win, project):
        super().__init__(win)
        from ..retro.dos import build as B
        from ..retro.dos import dosbox
        self.win, self.project = win, project
        self.setWindowTitle("DOS Project Settings")
        self.resize(560, 520)
        s = B.settings_for(project)
        self.kind = s["kind"]
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.main = QComboBox()
        self.main.setEditable(True)
        for p in B.sources(Path(project.folder), self.kind):
            self.main.addItem(p.name)
        self.main.setCurrentText(s["main"])
        form.addRow("Main file:", self.main)
        self.exe = QLineEdit(s["exe"])
        self.exe.setMaxLength(8)
        self.exe.setToolTip("DOS 8.3 name of the program (at most 8 letters / digits)")
        form.addRow("Program name (8.3):", self.exe)
        self.compiler = QComboBox()
        titles = {"freebasic": "FreeBASIC -lang qb (free, downloaded)", "quickbasic": "QuickBASIC 4.5 BC.EXE (your copy)",
                  "fpc": "Free Pascal i8086-msdos (free, downloaded)", "turbopascal": "Turbo Pascal TPC.EXE (your copy)",
                  "openwatcom": "Open Watcom C 16-bit (free, downloaded)",
                  "djgpp": "DJGPP 32-bit protected mode (your installation)", "turboc": "Turbo C TCC.EXE (your copy)",
                  "jwasm": "JWasm (free, downloaded)", "": "(no compiler: batch files run as they are)"}
        for c in B.COMPILERS[self.kind]:
            self.compiler.addItem(titles.get(c, c), c)
        self.compiler.setCurrentIndex(max(0, self.compiler.findData(s["compiler"])))
        form.addRow("Compiler:", self.compiler)
        self.model = QComboBox()
        for m in B.MODELS:
            self.model.addItem(m, m)
        self.model.setCurrentIndex(max(0, self.model.findData(s["model"])))
        form.addRow("Memory model:", self.model)
        self.output = QComboBox()
        self.output.addItem("EXE (MZ executable)", "exe")
        self.output.addItem("COM (tiny, 64 KB, org 100h)", "com")
        self.output.setCurrentIndex(max(0, self.output.findData(s.get("output", "exe"))))
        form.addRow("Output:", self.output)
        self.cycles = QComboBox()
        for k, (title, _v) in dosbox.CYCLES.items():
            self.cycles.addItem(title, k)
        idx = self.cycles.findData(s["cycles"])
        if idx < 0:
            self.cycles.addItem(str(s["cycles"]), s["cycles"])
            idx = self.cycles.count() - 1
        self.cycles.setCurrentIndex(idx)
        form.addRow("CPU speed (cycles):", self.cycles)
        self.machine = QComboBox()
        for k, title in dosbox.MACHINES.items():
            self.machine.addItem(title, k)
        self.machine.setCurrentIndex(max(0, self.machine.findData(s["machine"])))
        form.addRow("Machine:", self.machine)
        self.memsize = QSpinBox()
        self.memsize.setRange(1, 256)
        self.memsize.setSuffix(" MB")
        self.memsize.setValue(int(s.get("memsize", 16) or 16))
        form.addRow("Memory:", self.memsize)
        self.args = QLineEdit(str(s.get("args", "")))
        form.addRow("Program arguments:", self.args)
        self.keep = QCheckBox("Keep the DOSBox-X window open after the program ends")
        self.keep.setChecked(bool(s.get("keep_window", True)))
        form.addRow("", self.keep)
        self.debugger = QComboBox()
        self.debugger.addItem("Automatic (8086 emulator when it understands the code)", "auto")
        self.debugger.addItem("RAD IDE 8086 emulator", "emu8086")
        self.debugger.addItem("DOSBox-X debugger", "dosbox")
        self.debugger.setCurrentIndex(max(0, self.debugger.findData(s.get("debugger", "auto"))))
        form.addRow("Debugger (F5):", self.debugger)
        self.warnings = QCheckBox("Show compiler warnings")
        self.warnings.setChecked(bool(s.get("warnings", True)))
        form.addRow("", self.warnings)
        lay.addLayout(form)
        for w in (self.model, self.output):
            w.setEnabled(self.kind in ("pascal", "c", "asm"))
        self.debugger.setEnabled(self.kind == "asm")
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def values(self) -> dict:
        from ..retro.dos.templates import dos_name
        return {"kind": self.kind, "main": self.main.currentText().strip(), "exe": dos_name(self.exe.text()),
                "compiler": self.compiler.currentData(), "model": self.model.currentData(),
                "output": self.output.currentData(), "cycles": self.cycles.currentData(),
                "machine": self.machine.currentData(), "memsize": self.memsize.value(),
                "args": self.args.text().strip(), "keep_window": self.keep.isChecked(),
                "debugger": self.debugger.currentData(), "warnings": self.warnings.isChecked()}

    def save(self):
        self.project.extra["dos"] = self.values()
        main = self.project.extra["dos"]["main"]
        if main:
            self.project.startup = Path(main).stem
        self.project.save()
        self.accept()


class DosToolchainsDialog(QDialog):
    """Tools > Retro > DOS Programming > DOS Toolchains...: download the free compilers, set your own copies."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("DOS Toolchains")
        self.resize(900, 560)
        lay = QVBoxLayout(self)
        intro = QLabel("Free DOS compilers are downloaded from their official sites into the IDE's tools folder "
                       "(SHA-256 checked, no admin rights). Microsoft QBasic / QuickBASIC and Borland Turbo Pascal / "
                       "Turbo C are not free: RAD IDE never downloads them, but you can point it at your own copy.")
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Tool", "Version", "Path", ""])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        lay.addWidget(self.table, 1)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(140)
        lay.addWidget(self.log)
        self.relay = _Relay()
        self.relay.line.connect(self.log.appendPlainText)
        self.relay.done.connect(lambda _c: self.fill())
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.fill()

    def fill(self):
        from ..retro.dos import toolchain as T
        rows = T.status()
        rows.append({"key": "dosbox-x-emu", "title": "DOSBox-X (Tools > Retro > Emulators...)", "version": "",
                     "path": T.dosbox_exe(), "user": False, "emu": True})
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["title"]))
            self.table.setItem(i, 1, QTableWidgetItem(r.get("version", "")))
            self.table.setItem(i, 2, QTableWidgetItem(r["path"] or ("not installed" if not r["user"] else
                                                                    "not set")))
            if r.get("emu"):
                b = QPushButton("Download" if not r["path"] else "Installed")
                b.setEnabled(not r["path"])
                b.clicked.connect(self._download_dosbox)
            elif r["user"]:
                b = QPushButton("Browse...")
                b.clicked.connect(lambda _c=False, k=r["key"]: self._browse(k))
            else:
                b = QPushButton(f"Download ({r['size_mb']} MB)" if not r["path"] else "Reinstall")
                b.clicked.connect(lambda _c=False, k=r["key"]: self._download(k))
            self.table.setCellWidget(i, 3, b)
        self.table.resizeColumnToContents(0)

    def _download(self, key: str):
        from ..retro.dos import toolchain as T

        def work():
            ok = T.install(key, log=self.relay.line.emit)
            self.relay.done.emit(0 if ok else 1)
        threading.Thread(target=work, daemon=True).start()

    def _download_dosbox(self):
        def work():
            try:
                from ..retro.emu import manager
                manager.install("dosbox-x", log=self.relay.line.emit)
            except Exception as e:  # noqa: BLE001
                self.relay.line.emit(f"DOSBox-X: {e}")
            self.relay.done.emit(0)
        threading.Thread(target=work, daemon=True).start()

    def _browse(self, key: str):
        from ..retro.dos import toolchain as T
        title, names = T.USER_TOOLS[key]
        path, _ = QFileDialog.getOpenFileName(self, title, "", f"{' '.join(names)};;Programs (*.exe *.com);;All (*)")
        if path:
            T.set_user_path(key, path)
            self.fill()


class InterruptReference(QDialog):
    """Tools > Retro > DOS Programming > DOS Interrupt Reference...: INT 21h / 10h / 16h / 33h / 1Ah."""

    def __init__(self, win):
        super().__init__(win)
        from ..retro.dos import reference as R
        self.setWindowTitle("DOS Interrupt Reference")
        self.resize(900, 600)
        lay = QVBoxLayout(self)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter (e.g. print, mouse, 4Ch, video mode)")
        lay.addWidget(self.filter)
        split = QSplitter()
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Interrupt / function", "Name"])
        self.view = QTextBrowser()
        split.addWidget(self.tree)
        split.addWidget(self.view)
        split.setSizes([420, 480])
        lay.addWidget(split, 1)
        arabic = R.arabic_ui()
        for n, it in sorted(R.INTERRUPTS.items()):
            top = QTreeWidgetItem([f"INT {n:02X}h", it.ar if arabic else it.title])
            top.setData(0, Qt.ItemDataRole.UserRole, (n, None))
            for k, f in sorted(it.functions.items()):
                ch = QTreeWidgetItem([f"{it.selector}={k:02X}h", f.name])
                ch.setData(0, Qt.ItemDataRole.UserRole, (n, k))
                top.addChild(ch)
            self.tree.addTopLevelItem(top)
        self.tree.expandAll()
        self.tree.resizeColumnToContents(0)
        self.tree.currentItemChanged.connect(self._show)
        self.filter.textChanged.connect(self._filter)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _show(self, it, _prev=None):
        if it is None:
            return
        from ..retro.dos import reference as R
        n, k = it.data(0, Qt.ItemDataRole.UserRole)
        md = R.interrupt_doc(n, k, R.arabic_ui())
        self.view.setMarkdown(md.replace("  \n", "\n\n"))

    def _filter(self, text: str):
        t = text.lower().strip()
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            any_shown = False
            for j in range(top.childCount()):
                ch = top.child(j)
                show = not t or t in (ch.text(0) + " " + ch.text(1)).lower()
                ch.setHidden(not show)
                any_shown |= show
            top.setHidden(not any_shown and bool(t) and t not in top.text(0).lower() + top.text(1).lower())


def show_settings(win):
    if not _need_project(win, "DOS Project Settings"):
        return None
    d = DosSettingsDialog(win, win.project)
    d.exec()
    return d


def show_toolchains(win):
    d = DosToolchainsDialog(win)
    d.show()
    win._dos_toolchains = d
    return d


def show_reference(win):
    d = InterruptReference(win)
    d.show()
    win._dos_reference = d
    return d


# ============================================================================ install
def install(win) -> None:
    register_detector()
    providers = win.__dict__.setdefault("diag_providers", [])
    if diag_provider not in providers:
        providers.append(diag_provider)
    orig = getattr(win, "_make_session", None)
    if callable(orig):
        def make_session(spec, debug, plugin, interp, startup=None):
            s = orig(spec, debug, plugin, interp, startup)
            try:
                if s is not None and getattr(plugin, "id", "") in DOS_LANGS:
                    s.finished.connect(lambda *_a: refresh_errors(win))
            except Exception:  # noqa: BLE001 - never stop F5
                pass
            return s
        win._make_session = make_session
    win.dos_build = lambda: build_program(win)
    win.dos_settings = lambda: show_settings(win)
    win.dos_toolchains = lambda: show_toolchains(win)
    try:
        try:
            from ..retro.menu import section
            m = section(win, "DOS Programming")
        except Exception:  # noqa: BLE001
            tools = _menu(win, "Tools")
            m = tools.addMenu("DOS Programming") if tools is not None else None
        if m is not None:
            m.addAction("Build DOS Program", lambda: build_program(win))
            m.addAction("Run in DOSBox-X", lambda: run_variant(win, [], "Run in DOSBox-X"))
            m.addAction("Run in DOSBox-X Debugger", lambda: run_variant(win, ["--debug"], "Run in DOSBox-X Debugger"))
            m.addAction("Run in My QBasic", lambda: run_variant(win, ["--qbasic"], "Run in My QBasic"))
            m.addAction("Run with Captured Output...", lambda: run_captured(win))
            m.addAction("Show Last DOS Screen", lambda: show_last_screen(win))
            m.addAction("Open Symbol Map", lambda: open_map(win))
            m.addSeparator()
            m.addAction("DOS Project Settings...", lambda: show_settings(win))
            m.addAction("DOS Toolchains...", lambda: show_toolchains(win))
            m.addAction("DOS Interrupt Reference...", lambda: show_reference(win))
            win.dos_menu = m
        project = _menu(win, "Project")
        if project is not None:
            project.addAction("DOS Project Settings...", lambda: show_settings(win))
    except Exception as e:  # noqa: BLE001 - menus are optional
        try:
            win.log(f"[dos] menus: {e}")
        except Exception:  # noqa: BLE001
            pass
