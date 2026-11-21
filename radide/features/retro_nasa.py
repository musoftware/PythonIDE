"""Apollo AGC and legacy Fortran in the IDE (docs/RETRO.md, sections "Apollo AGC" and "Legacy Fortran").

Tools > Retro > Apollo AGC:
    Open Apollo Source...           download Comanche055 / Luminary099 (public domain) into a chosen folder
    Virtual AGC Toolchain...        download the official yaYUL / yaAGC source and build it with MinGW
    Build with yaYUL                assemble the current AGC project with yaYUL (errors -> Error List)
    DSKY Panel                      the "Apollo AGC" dock (DSKY, registers, erasable memory)
    DSKY Verbs, Nouns and Programs  reference table
    Assembly Listing                the built-in assembler's listing of the current project
Tools > Retro > Legacy Fortran:
    Card Deck View / Convert to Free Form... / Explain Legacy Constructs / Compiler Preset...

Also: assembly errors of AGC projects and gfortran errors of fixed-form projects in the Error List after every
save (``win.diag_providers``), and the fixed-form editor guides (rulers, greyed sequence field) in Monaco.
"""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QLabel, QMessageBox,
                             QPlainTextEdit, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout)


def _menu(win, title: str):
    for a in win.menuBar().actions():
        if a.text().replace("&", "") == title and a.menu() is not None:
            return a.menu()
    return None


def _current_editor(win):
    w = win.tabs.currentWidget() if hasattr(win, "tabs") else None
    if w is None:
        return None
    return getattr(w, "editor", None) or (w if hasattr(w, "text") and hasattr(w, "path") else None)


def _project_of(win, language: str):
    p = getattr(win, "project", None)
    return p if p is not None and getattr(p, "language", "") == language else None


class _Relay(QObject):
    line = pyqtSignal(str)
    done = pyqtSignal(bool, object)


def _background(win, title: str, job, on_done=None) -> None:
    """Run job(log) in a thread; log lines go to the Output window."""
    relay = _Relay(win)
    relay.line.connect(lambda s: win.log(f"[{title}] {s}"))
    if on_done is not None:
        relay.done.connect(on_done)
    win._retro_relays = getattr(win, "_retro_relays", []) + [relay]

    def run():
        try:
            res = job(relay.line.emit)
            relay.done.emit(True, res)
        except Exception as e:  # noqa: BLE001 - shown to the user
            relay.line.emit(f"*** {e}")
            relay.done.emit(False, None)
    threading.Thread(target=run, daemon=True).start()
    try:
        win.dock_output.show()
        win.dock_output.raise_()
    except Exception:  # noqa: BLE001
        pass


# ============================================================================ Apollo AGC actions
def open_apollo_source(win) -> None:
    from ..agc.apollo_source import PROGRAMS
    dlg = QDialog(win)
    dlg.setWindowTitle("Open Apollo Source")
    lay = QVBoxLayout(dlg)
    lay.addWidget(QLabel("Download the Apollo 11 flight software (public domain, transcribed by the Virtual AGC "
                         "project) into a folder you choose. Nothing is bundled with RAD IDE."))
    combo = QComboBox()
    for name, (title, _ar) in PROGRAMS.items():
        combo.addItem(f"{name} - {title}", name)
    lay.addWidget(combo)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addWidget(box)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return
    name = combo.currentData()
    dest = QFileDialog.getExistingDirectory(win, "Folder for the Apollo source", str(Path.home() / "Documents"))
    if not dest:
        return

    def job(log):
        from ..agc.apollo_source import download
        log(f"Downloading {name} ...")
        return download(name, Path(dest), log)

    def done(ok, folder):
        if ok and folder:
            win.log(f"[Apollo] {name} is in {folder} (README_RADIDE.txt has the licence note).")
            opener = getattr(win, "open_project", None)
            if callable(opener):
                try:
                    opener(Path(folder))
                except Exception as e:  # noqa: BLE001
                    win.log(f"[Apollo] open the project from File > Open Project: {e}")
    _background(win, "Apollo", job, done)


def install_toolchain(win) -> None:
    from ..agc import toolchain
    st = toolchain.status()
    have = st["yaYUL"] and st["yaAGC"]
    text = ("Virtual AGC (yaYUL assembler, yaAGC emulator; GPL v2, https://www.ibiblio.org/apollo) is built from "
            f"the official source at github.com/{toolchain.REPO} (commit {toolchain.COMMIT[:10]}) with the MinGW "
            f"gcc of RAD IDE into\n{toolchain.root()}\n\n")
    text += (f"Installed:\n  yaYUL: {st['yaYUL']}\n  yaAGC: {st['yaAGC']}\n\nRebuild?" if have else
             "Download (~1.5 MB of source) and build now?")
    if QMessageBox.question(win, "Virtual AGC Toolchain", text) != QMessageBox.StandardButton.Yes:
        return
    _background(win, "Virtual AGC", lambda log: toolchain.install(log),
                lambda ok, res: win.log("[Virtual AGC] ready." if ok and res else
                                        "[Virtual AGC] *** not installed - see the messages above."))


def build_with_yayul(win) -> None:
    from ..agc import toolchain
    from ..agc.session import show_diagnostics
    p = _project_of(win, "agc-yul")
    if p is None:
        win.log("Build with yaYUL: open an Apollo AGC project first.")
        return
    try:
        win.save_all()
    except Exception:  # noqa: BLE001
        pass
    from ..languages import get_plugin
    startup = get_plugin("agc-yul").startup_file(Path(p.folder), p.startup)
    argv = toolchain.yayul_command(startup)
    if not argv:
        win.log("yaYUL is not installed: Tools > Retro > Apollo AGC > Virtual AGC Toolchain...")
        return

    def job(log):
        r = subprocess.run(argv, cwd=str(p.folder), capture_output=True, text=True, errors="replace",
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for line in r.stdout.splitlines()[-5:]:
            log(line)
        return r.returncode, toolchain.parse_yayul_output(r.stderr)

    def done(ok, res):
        if not ok or res is None:
            return
        code, diags = res
        show_diagnostics(win, [(s, m, f, ln) for s, f, ln, m in diags])
        win.log(f"[yaYUL] exit code {code}, {sum(d[0] == 'Error' for d in diags)} error(s)")
    _background(win, "yaYUL", job, done)


def show_dsky(win) -> None:
    from ..agc.session import ensure_panel
    ensure_panel(win)
    dock = getattr(win, "_agc_dock", None)
    if dock is not None:
        dock.show()
        dock.raise_()


def dsky_reference(win) -> None:
    from ..agc import isa
    try:
        from ..i18n import language
        ar = language() == "ar"
    except Exception:  # noqa: BLE001
        ar = False
    dlg = QDialog(win)
    dlg.setWindowTitle("DSKY Verbs, Nouns and Programs")
    lay = QVBoxLayout(dlg)
    lay.addWidget(QLabel("Typical Colossus / Comanche (command module) meanings; the lunar module's Luminary "
                         "differs for some numbers. Type VERB nn NOUN nn ENTR on the DSKY."))
    tabs = QTabWidget()
    for title, table, prefix in (("Verbs", isa.VERBS, "V"), ("Nouns", isa.NOUNS, "N"),
                                 ("Programs", isa.PROGRAMS, "P")):
        tree = QTreeWidget()
        tree.setHeaderLabels(["", "Meaning"])
        tree.setRootIsDecorated(False)
        tree.setProperty("i18n_skip_items", True)
        for n, (en, arabic) in sorted(table.items()):
            tree.addTopLevelItem(QTreeWidgetItem([f"{prefix}{n:02d}", arabic if ar else en]))
        tree.resizeColumnToContents(0)
        tabs.addTab(tree, title)
    keys = QTreeWidget()
    keys.setHeaderLabels(["Key", "Code (octal)"])
    keys.setRootIsDecorated(False)
    for k, v in isa.KEY_CODES.items():
        keys.addTopLevelItem(QTreeWidgetItem([k, f"{v:02o}"]))
    keys.addTopLevelItem(QTreeWidgetItem(["PRO", "channel 32 bit 14"]))
    tabs.addTab(keys, "Keys")
    lay.addWidget(tabs, 1)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    box.rejected.connect(dlg.reject)
    lay.addWidget(box)
    dlg.resize(620, 520)
    dlg.exec()


def assembly_listing(win) -> None:
    from ..agc import assembler
    from ..agc.session import editor_texts
    p = _project_of(win, "agc-yul")
    if p is None:
        win.log("Assembly Listing: open an Apollo AGC project first.")
        return
    from ..languages import get_plugin
    startup = get_plugin("agc-yul").startup_file(Path(p.folder), p.startup)
    prog = assembler.assemble_file(Path(p.folder) / startup, editor_texts(win))
    _text_dialog(win, "AGC Assembly Listing", prog.listing_text() +
                 f"\n{prog.words()} words, {len(prog.errors)} error(s), {len(prog.warnings)} warning(s)\n")


def _text_dialog(win, title: str, text: str) -> None:
    from PyQt6.QtGui import QFont
    dlg = QDialog(win)
    dlg.setWindowTitle(title)
    lay = QVBoxLayout(dlg)
    view = QPlainTextEdit(text)
    view.setReadOnly(True)
    view.setFont(QFont("Consolas", 9))
    view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    view.setProperty("i18n_skip", True)
    lay.addWidget(view, 1)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    box.rejected.connect(dlg.reject)
    lay.addWidget(box)
    dlg.resize(900, 600)
    dlg.exec()


# ============================================================================ legacy Fortran actions
def _fixed_editor(win):
    from ..retro.legacy_fortran import FIXED_EXT
    ed = _current_editor(win)
    path = Path(str(getattr(ed, "path", "") or ""))
    if ed is None or path.suffix.lower() not in FIXED_EXT:
        win.log("Open a fixed-form Fortran file (.f / .for / .f77) first.")
        return None, None
    return ed, path


def card_deck(win) -> None:
    from ..retro.legacy_fortran import card_deck_dialog
    ed, path = _fixed_editor(win)
    if ed is None:
        return
    try:
        line = ed.getCursorPosition()[0]
    except Exception:  # noqa: BLE001
        line = 0
    card_deck_dialog(win, ed.text(), line).exec()


def convert_free_form(win) -> None:
    from ..retro.legacy_fortran import conversion_dialog
    ed, path = _fixed_editor(win)
    if ed is None:
        return
    conversion_dialog(win, path, ed.text()).exec()


def explain_legacy(win) -> None:
    from ..retro.legacy_fortran import analyze
    ed, path = _fixed_editor(win)
    if ed is None:
        return
    try:
        from ..i18n import language
        ar = language() == "ar"
    except Exception:  # noqa: BLE001
        ar = False
    rows = analyze(ed.text())
    win.log(f"------ Legacy constructs in {path.name}: {len(rows)} ------")
    for line, kind, en, arabic in rows:
        win.log(f"{path.name}({line + 1}): {kind}: {arabic if ar else en}")
    win.dock_output.show()


def compiler_preset(win) -> None:
    from ..retro.legacy_fortran import PRESETS, project_settings
    p = _project_of(win, "fortran-legacy")
    if p is None:
        win.log("Compiler Preset: open a Fortran 66/77 project first.")
        return
    cur = project_settings(p)
    dlg = QDialog(win)
    dlg.setWindowTitle("Fortran Compiler Preset")
    lay = QVBoxLayout(dlg)
    combo = QComboBox()
    for key, (title, flags, _note) in PRESETS.items():
        combo.addItem(f"{title}   ({' '.join(flags)})", key)
        if key == cur["preset"]:
            combo.setCurrentIndex(combo.count() - 1)
    note = QLabel()
    note.setWordWrap(True)
    combo.currentIndexChanged.connect(lambda _i: note.setText(PRESETS[combo.currentData()][2]))
    note.setText(PRESETS[combo.currentData()][2])
    lay.addWidget(combo)
    lay.addWidget(note)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addWidget(box)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        p.extra["fortran"] = {"preset": combo.currentData(), "flags": cur.get("flags", "")}
        p.save()
        win.log(f"Fortran preset: {PRESETS[combo.currentData()][0]}")


# ============================================================================ Error List providers
def agc_diagnostics(win):
    p = _project_of(win, "agc-yul")
    if p is None:
        return []
    from ..languages.agc_yul import agc_settings
    if str(agc_settings(p).get("assembler")).lower() == "yayul":
        return []
    from ..agc import assembler
    from ..agc.session import editor_texts
    from ..tools import Diag
    from ..languages import get_plugin
    try:
        from ..i18n import language
        lang = language()
    except Exception:  # noqa: BLE001
        lang = "en"
    startup = get_plugin("agc-yul").startup_file(Path(p.folder), p.startup)
    if not (Path(p.folder) / startup).exists():
        return []
    prog = assembler.assemble_file(Path(p.folder) / startup, editor_texts(win))
    if any(d.code == "interp" for d in prog.errors):
        return [Diag("Warning", "Interpretive code: this program builds with yaYUL (Tools > Retro > Apollo AGC)",
                     startup, 1)]
    return [Diag(d.severity, d.text(lang), Path(d.file).name, d.line) for d in (prog.errors + prog.warnings)[:200]]


def fortran_diagnostics(win):
    p = _project_of(win, "fortran-legacy")
    if p is None:
        return []
    from ..retro import legacy_fortran as lf
    from ..tools import Diag
    s = lf.project_settings(p)
    srcs = lf.sources_of(Path(p.folder))
    argv = lf.compile_command(srcs, "", s["preset"], s.get("flags", ""), syntax_only=True)
    if not argv or not srcs:
        return []
    try:
        r = subprocess.run(argv, cwd=str(p.folder), capture_output=True, text=True, errors="replace", timeout=20,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [Diag(sev, msg, Path(f).name, line) for sev, f, line, msg in lf.parse_gfortran(r.stderr)][:200]


def _fixed_form_ready(editor) -> None:
    from ..retro.legacy_fortran import FIXED_EXT, editor_js
    try:
        if Path(str(editor.path)).suffix.lower() in FIXED_EXT:
            editor._js(editor_js())
    except Exception:  # noqa: BLE001 - editor decorations are optional
        pass


# ============================================================================ install
def install(win) -> None:
    try:                                    # the shared Tools > Retro menu (docs/CONTRACTS.md section 11)
        from ..retro.menu import section
        agc, ff = section(win, "Apollo AGC"), section(win, "Legacy Fortran")
    except Exception:  # noqa: BLE001 - fall back to Tools
        tools = _menu(win, "Tools")
        agc = ff = None
        if tools is not None:
            agc, ff = tools.addMenu("Apollo AGC"), tools.addMenu("Legacy Fortran")
    if agc is not None and ff is not None:
        agc.addAction("Open Apollo Source...", lambda: open_apollo_source(win))
        agc.addAction("Virtual AGC Toolchain...", lambda: install_toolchain(win))
        agc.addAction("Build with yaYUL", lambda: build_with_yayul(win))
        agc.addSeparator()
        agc.addAction("DSKY Panel", lambda: show_dsky(win))
        agc.addAction("DSKY Verbs, Nouns and Programs", lambda: dsky_reference(win))
        agc.addAction("Assembly Listing", lambda: assembly_listing(win))
        ff.addAction("Card Deck View", lambda: card_deck(win))
        ff.addAction("Convert to Free Form...", lambda: convert_free_form(win))
        ff.addAction("Explain Legacy Constructs", lambda: explain_legacy(win))
        ff.addAction("Compiler Preset...", lambda: compiler_preset(win))
        win._retro_nasa_menus = (agc, ff)
    providers = getattr(win, "diag_providers", None)
    if providers is None:
        win.diag_providers = providers = []
    for fn in (agc_diagnostics, fortran_diagnostics):
        if fn not in providers:
            providers.append(fn)
    try:
        from ..monaco_editor import MonacoEditor
        if _fixed_form_ready not in MonacoEditor.ready_hooks:
            MonacoEditor.ready_hooks.append(_fixed_form_ready)
    except Exception:  # noqa: BLE001 - no QtWebEngine
        pass


__all__ = ["install", "agc_diagnostics", "fortran_diagnostics", "card_deck", "convert_free_form",
           "dsky_reference", "open_apollo_source", "install_toolchain", "build_with_yayul", "show_dsky"]

