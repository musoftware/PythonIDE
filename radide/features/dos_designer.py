"""Text-Mode Designer and ANSI Art Editor in the IDE (radide/retro/design/textmode, docs/RETRO.md
"DOS text-mode designer").

* New Project > DOS > DOS Text-Mode Forms App (QBasic / FreeBASIC, Pascal, C, 16-bit assembly): screens are
  drawn in the designer (.tform) and the main source (MAIN.BAS / .PAS / .C / .ASM) is generated every time a
  screen is saved; the user's code lives in its USER CODE regions. The project is a normal DOS project of the
  dosdev slice (dos-qbasic / dos-pascal / dos-c / dos-asm), so Build / Run (F5) build it with the free compiler
  and run it in DOSBox-X.
* Tools > Retro > Text-Mode: New Screen, New ANSI Art, Open, Generate Code, Build && Run, Test Run, Use as
  Splash Screen. ``.tform`` opens in the designer; ``.ans`` / ``.asc`` / ``.nfo`` (and ``.bin`` art) in the ANSI
  editor (File > Open, Solution Explorer).
* Double-click a control (or an event in the Properties window) -> the code editor at its handler.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment
from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog, QLineEdit, QMessageBox, QPlainTextEdit

TFORM = ".tform"


def _alive(w) -> bool:
    try:
        w.isVisible()
        return True
    except RuntimeError:
        return False


class DosDesignerFeature:
    def __init__(self, win):
        self.win = win
        self.docs: dict[str, object] = {}
        self.proc: QProcess | None = None
        self._menus()
        self._wrap()

    # ------------------------------------------------------------ menus
    def _menus(self) -> None:
        win = self.win
        try:
            from ..retro.menu import section
            m = section(win, "Text-&Mode (DOS)")
        except Exception:  # noqa: BLE001 - the shared retro menu belongs to another slice
            tools = next((a.menu() for a in win.menuBar().actions() if a.menu() is not None and
                          a.text().replace("&", "") == "Tools"), None)
            m = (tools or win.menuBar()).addMenu("Text-&Mode (DOS)")
        self.menu = m
        m.addAction("New Text-Mode &Screen...", self.new_screen)
        m.addAction("New &ANSI Art...", self.new_art)
        m.addAction("&Open Screen or Art...", self.open_dialog)
        m.addSeparator()
        m.addAction("&Generate Code", lambda: self.generate(ask=True))
        m.addAction("&Build && Run in DOSBox-X", self.build_run)
        m.addAction("&Test Run (simulator)", self.test_run)
        m.addAction("&View Code", self.view_code)
        m.addSeparator()
        m.addAction("Use Current Art as &Splash Screen", lambda: self.use_as_splash(None))

    # ------------------------------------------------------------ window wrapping
    def _wrap(self) -> None:
        win = self.win
        orig_open_any = win.open_any_file
        orig_open_module = getattr(win, "open_module", None)
        orig_save_all = win.save_all
        orig_any_modified = win._any_modified

        def open_any_file(path, *a, **k):
            if self.handles(path):
                return self.open(Path(path))
            return orig_open_any(path, *a, **k)

        def open_module(filename, *a, **k):
            if win.project is not None and self.handles(Path(win.project.folder) / filename):
                return self.open(Path(win.project.folder) / filename)
            return orig_open_module(filename, *a, **k)

        def save_all(*a, **k):
            self.save_documents()
            return orig_save_all(*a, **k)

        def any_modified(*a, **k):
            return any(d.is_modified() for d in self._docs()) or orig_any_modified(*a, **k)

        win.open_any_file = open_any_file
        # editor_extras (generic hex view) and retro_rom wrap the openers after this feature is installed (and
        # retro_rom one event-loop turn later): wrap again, outermost, so .tform / art files reach their editors
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: QTimer.singleShot(0, self._wrap_outer))
        if orig_open_module is not None:
            win.open_module = open_module
        win.save_all = save_all
        win._any_modified = any_modified
        win.dos_designer = self
        for attr, op in (("a_undo", "undo"), ("a_redo", "redo"), ("a_cut", "cut"), ("a_copy", "copy"),
                         ("a_paste", "paste"), ("a_delete", "delete"), ("a_select_all", "select_all")):
            act = getattr(win, attr, None)
            if act is not None:
                act.triggered.connect(lambda _c=False, op=op: self._edit(op))
        if getattr(win, "a_save", None) is not None:
            win.a_save.triggered.connect(lambda _c=False: self._save_current())

    def _wrap_outer(self) -> None:
        win = self.win
        for attr in ("open_any_file", "open_file"):
            orig = getattr(win, attr, None)
            if not callable(orig) or getattr(orig, "_rad_tui", False):
                continue

            def opener(path, *a, _orig=orig, **k):
                p = Path(path)
                if not p.is_absolute() and getattr(win, "project", None) is not None:
                    p = Path(win.project.folder) / p
                if self.handles(p) and p.is_file():
                    return self.open(p)
                return _orig(path, *a, **k)
            opener._rad_tui = True
            setattr(win, attr, opener)

    @staticmethod
    def handles(path) -> bool:
        p = Path(path)
        if p.suffix.lower() == TFORM:
            return True
        from ..retro.design.textmode.ansieditor import is_art_file
        return is_art_file(p)

    def _docs(self) -> list:
        return [d for d in self.docs.values() if _alive(d)]

    def current(self):
        try:
            w = self.win.tabs.currentWidget()
        except RuntimeError:
            return None
        return w if w in self._docs() else None

    def _edit(self, op: str) -> None:
        d = self.current()
        if d is None or isinstance(QApplication.focusWidget(), (QLineEdit, QPlainTextEdit)):
            return
        d.edit_op(op)

    def _save_current(self) -> None:
        d = self.current()
        if d is not None and d.is_modified():
            d.save()

    def save_documents(self) -> None:
        for d in self._docs():
            if d.is_modified() and getattr(d, "doc_path", True) is not None:
                d.save()

    # ------------------------------------------------------------ documents
    def _title(self, d) -> None:
        i = self.win.tabs.indexOf(d)
        if i >= 0:
            self.win.tabs.setTabText(i, d.path.name + ("*" if d.is_modified() else ""))

    def _register(self, d, key: str):
        d.modifiedChanged.connect(lambda _m, x=d: self._title(x))
        self.docs[key] = d
        return d

    def open(self, path: Path):
        path = Path(path).resolve()
        key = str(path).lower()
        d = self.docs.get(key)
        if d is not None and (not _alive(d) or self.win.tabs.indexOf(d) < 0):
            self.docs.pop(key, None)
            d = None
        if d is None:
            try:
                d = self._make(path)
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(self.win, "Text-Mode Designer", f"Cannot open {path.name}:\n{e}")
                return None
            d.setToolTip(str(path))
            self._register(d, key)
        self.win._show_tab(d, path.name)
        self._title(d)
        return d

    def _make(self, path: Path):
        if path.suffix.lower() == TFORM:
            from ..retro.design.textmode.designer import TuiDesigner
            d = TuiDesigner(path)
            d.saved.connect(lambda x=d: self._after_screen_save(x))
            d.codeRequested.connect(lambda key, x=d: self.show_code(x, key))
            d.actionRequested.connect(lambda act, x=d: self._designer_action(x, act))
            return d
        from ..retro.design.textmode.ansieditor import AnsiEditor
        d = AnsiEditor(path)
        d.splashRequested.connect(lambda _p, x=d: self.use_as_splash(x))
        return d

    def open_dialog(self) -> None:
        start = str(self.win.project.folder) if self.win.project is not None else ""
        f, _ = QFileDialog.getOpenFileName(self.win, "Open Screen or Art", start,
                                           "Text-mode screens and art (*.tform *.ans *.asc *.nfo *.bin);;"
                                           "All files (*)")
        if f:
            self.open(Path(f))

    # ------------------------------------------------------------ forms projects
    def project_folder(self, path: Path | None = None) -> Path | None:
        """The forms project of *path* (or of the active project): a folder whose project.radproj has "tui"."""
        from ..retro.design.textmode.project import _radproj
        cands = []
        if path is not None:
            cands.append(Path(path).parent)
        if self.win.project is not None:
            cands.append(Path(self.win.project.folder))
        for c in cands:
            if (c / "project.radproj").exists() and _radproj(c).get("tui"):
                return c
        return None

    def new_screen(self) -> None:
        from ..retro.design.textmode.designer import ask_new_screen
        from ..retro.design.textmode.model import new_screen
        folder = self.project_folder()
        if folder is None and self.win.project is not None:
            folder = Path(self.win.project.folder)
        names = {p.stem.lower() for p in folder.glob("*.tform")} if folder else set()
        i = 1
        while f"screen{i}" in names:
            i += 1
        got = ask_new_screen(self.win, f"Screen{i}")
        if got is None:
            return
        name, cols, rows = got
        s = new_screen(name, cols, rows)
        if folder is None:
            f, _ = QFileDialog.getSaveFileName(self.win, "New Text-Mode Screen", f"{name}.tform",
                                               "Text-mode screens (*.tform)")
            if not f:
                return
            path = Path(f)
        else:
            path = folder / f"{name}.tform"
            if path.exists():
                QMessageBox.information(self.win, "New Screen", f"{path.name} already exists.")
                return
        s.save(path)
        self._add_to_project(path)
        self.open(path)
        self._regenerate(path)

    def _add_to_project(self, path: Path) -> None:
        p = self.win.project
        if p is None:
            return
        try:
            rel = Path(path).resolve().relative_to(Path(p.folder).resolve()).as_posix()
        except ValueError:
            return
        if rel not in p.modules:
            p.modules.append(rel)
            p.save()
            try:
                self.win._fill_solution()
            except Exception:  # noqa: BLE001
                pass

    def new_art(self) -> None:
        from ..retro.design.textmode.ansieditor import AnsiEditor
        d = AnsiEditor()
        self._register(d, f"untitled:{id(d)}")
        self.win._show_tab(d, d.path.name)
        self._title(d)

    def _after_screen_save(self, d) -> None:
        self._title(d)
        if self._regenerate(d.screen.path):
            try:
                self.win.statusBar().showMessage(f"Saved {d.path.name} - code regenerated", 3000)
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------ code generation
    def _module_view(self, path: Path):
        for w in (self.win.tabs.widget(i) for i in range(self.win.tabs.count())):
            if getattr(w, "editor", None) is not None and getattr(w, "path", None) is not None:
                try:
                    if Path(w.path).resolve() == Path(path).resolve():
                        return w
                except OSError:
                    continue
        return None

    def _regenerate(self, screen_path: Path | None) -> bool:
        """Rewrite the main source of the forms project of *screen_path* (keeping the user's code)."""
        from ..retro.design.textmode import project as tp
        folder = self.project_folder(screen_path)
        if folder is None:
            return False
        main = tp.main_file(folder)
        mv = self._module_view(main)
        if mv is not None and mv.editor.isModified():          # the user's unsaved code first
            tp.write_dos_text(main, mv.editor.text())
            mv.editor.setModified(False)
        try:
            tp.generate(folder, self.win.log)
        except Exception as e:  # noqa: BLE001
            self.win.log(f"[text-mode designer] {e}")
            return False
        if mv is not None:
            line = mv.editor.getCursorPosition()[0] if hasattr(mv.editor, "getCursorPosition") else 0
            mv.editor.setText(tp.read_dos_text(main))
            mv.editor.setModified(False)
            try:
                mv.editor.goto_line(line)
            except Exception:  # noqa: BLE001
                pass
        return True

    def generate(self, ask: bool = False) -> None:
        d = self.current()
        from ..retro.design.textmode import project as tp
        if d is not None and hasattr(d, "screen") and d.is_modified():
            d.save()
        path = d.screen.path if d is not None and hasattr(d, "screen") else None
        if self._regenerate(path):
            folder = self.project_folder(path)
            self.win.log(f"[text-mode designer] generated {tp.main_file(folder).name}")
            return
        if d is None or not hasattr(d, "screen"):
            QMessageBox.information(self.win, "Generate Code", "Open a text-mode screen (.tform) first.")
            return
        # a screen outside a forms project: write <name>.<ext> next to it
        targets = list(tp.TARGETS)
        t, ok = QInputDialog.getItem(self.win, "Generate Code", "Language:",
                                     [tp.TARGETS[k][3] for k in targets], 0, False)
        if not ok:
            return
        target = targets[[tp.TARGETS[k][3] for k in targets].index(t)]
        ext = Path(tp.TARGETS[target][1]).suffix
        out = (d.screen.path.parent if d.screen.path else Path.cwd()) / (d.screen.name.upper()[:8] + ext)
        text, warnings = tp.generate_text([d.screen], target, tp.read_dos_text(out))
        tp.write_dos_text(out, text)
        for w in warnings:
            self.win.log(f"{out.name}: warning: {w}")
        self.win.open_any_file(out)

    def show_code(self, d, key: str) -> None:
        """The code of a handler: save the screen (records the event), regenerate, open the editor there."""
        from ..retro.design.textmode import project as tp
        if d.screen.path is not None:
            d.save()
        folder = self.project_folder(d.screen.path)
        if folder is None:
            self.generate()
            return
        settings = tp.settings(folder)
        main = tp.main_file(folder, settings["target"])
        line = tp.generator(settings["target"]).handler_line(tp.read_dos_text(main), key)
        ed = self._open_code(main)
        if ed is not None and line >= 0:
            ed.goto_line(line + 2)

    def _open_code(self, main: Path):
        p = self.win.project
        if p is not None:
            try:
                rel = main.resolve().relative_to(Path(p.folder).resolve()).as_posix()
                if callable(getattr(self.win, "open_module", None)):
                    self.win.open_module(rel)
                    mv = self._module_view(main)
                    if mv is not None:
                        return mv.editor
            except ValueError:
                pass
        return self.win.open_any_file(main)

    def view_code(self) -> None:
        from ..retro.design.textmode import project as tp
        d = self.current()
        folder = self.project_folder(d.screen.path if d is not None and hasattr(d, "screen") else None)
        if folder is None:
            QMessageBox.information(self.win, "View Code", "Open a DOS Text-Mode Forms App project first.")
            return
        self._open_code(tp.main_file(folder))

    def _designer_action(self, d, act: str) -> None:
        if act == "generate":
            self.generate()
        elif act == "build_run":
            self.build_run()
        elif act == "view_code":
            self.view_code()
        elif act == "add_screen":
            self.new_screen()

    def test_run(self) -> None:
        d = self.current()
        if d is None or not hasattr(d, "test_run"):
            QMessageBox.information(self.win, "Test Run", "Open a text-mode screen (.tform) first.")
            return
        d.test_run()

    # ------------------------------------------------------------ build && run
    def build_run(self) -> None:
        d = self.current()
        folder = self.project_folder(d.screen.path if d is not None and hasattr(d, "screen") else None)
        if folder is None:
            QMessageBox.information(self.win, "Build && Run", "Open a DOS Text-Mode Forms App project first "
                                                             "(New Project > DOS > DOS Text-Mode Forms App).")
            return
        self.save_documents()
        try:
            self.win.save_all()
        except Exception:  # noqa: BLE001
            pass
        if self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.information(self.win, "Build && Run", "The program is still running.")
            return
        import os
        root = str(Path(__file__).resolve().parents[2])
        self.proc = QProcess(self.win)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONPATH", root + os.pathsep + env.value("PYTHONPATH", ""))
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        self.proc.setProcessEnvironment(env)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read_proc)
        self.proc.finished.connect(lambda code, _s: self.win.log(f"[text-mode designer] finished ({code})"))
        self.win.log(f"[text-mode designer] build && run {folder}")
        self.proc.start(sys.executable, ["-u", "-m", "radide.retro.design.textmode.project", "run", str(folder)])

    def _read_proc(self) -> None:
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        for line in data.splitlines():
            if line.strip():
                self.win.log(line)

    # ------------------------------------------------------------ splash
    def use_as_splash(self, art) -> None:
        art = art if art is not None else self.current()
        if art is None or not hasattr(art, "splashRequested"):
            QMessageBox.information(self.win, "Splash Screen", "Open an ANSI art document first.")
            return
        if art.doc_path is None or art.is_modified():
            if not art.save():
                return
        folder = self.project_folder(art.doc_path)
        if folder is None:
            QMessageBox.information(self.win, "Splash Screen", "Open a DOS Text-Mode Forms App project first.")
            return
        from ..retro.design.textmode.model import load_project_screens
        screens = load_project_screens(folder)
        if not screens:
            return
        s = screens[0]
        try:
            rel = Path(art.doc_path).resolve().relative_to(folder.resolve()).as_posix()
        except ValueError:
            import shutil
            dest = folder / Path(art.doc_path).name
            shutil.copy2(art.doc_path, dest)
            rel = dest.name
        sec, ok = QInputDialog.getInt(self.win, "Splash Screen", "Seconds (0 = until a key is pressed):",
                                      int(s.get("splash_seconds") or 0), 0, 60)
        if not ok:
            return
        s.set("splash", rel)
        s.set("splash_seconds", sec)
        s.save()
        d = self.docs.get(str(Path(s.path).resolve()).lower())
        if d is not None and _alive(d):
            d.screen.props["splash"], d.screen.props["splash_seconds"] = rel, sec
            d._clean = d.screen.to_json()
        self._regenerate(s.path)
        self.win.log(f"[text-mode designer] {s.name}: splash screen = {rel} ({sec or 'key'} s)")


def install(win) -> None:
    win.dos_designer_feature = DosDesignerFeature(win)
