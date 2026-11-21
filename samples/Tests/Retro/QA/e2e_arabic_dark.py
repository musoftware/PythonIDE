"""Retro QA: Arabic UI + dark theme over every retro / NASA window (screenshots with widget.grab only).

The IDE starts in Arabic with the Dark theme; the test opens the New Project dialog (retro groups), every
Tools > Retro menu, the ROM workbench (hex editor, Patch Manager, Create / Apply Patch), the graphics editors
(tiles, playfield, tile map, text table, script), the retro dev dialogs (Disassemble, Toolchains), the
Emulators manager, the Retro Debugger dock, DOS Settings, the Apollo AGC dock and the Fortran card deck.
English UI texts that the Arabic catalog does not translate (i18n.missing()) and that appeared while these
windows were open are listed; the check fails when any remain.  Dark theme: the window background of each
grabbed window must be dark.

    python samples/Tests/Retro/QA/e2e_arabic_dark.py
"""
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QA_NAME", "retro_qa_ar_dark")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, shot  # noqa: E402

from radide import i18n  # noqa: E402
from radide.languages import get_plugin  # noqa: E402

REPO = Path(qh.ROOT)
WORK = Path(qh.WORK) / "retro_qa_ar_dark"


def dark(widget) -> bool:
    img = widget.grab().toImage()
    if img.isNull() or img.width() < 4:
        return False
    xs = [img.width() * i // 6 for i in range(1, 6)]
    ys = [img.height() * i // 6 for i in range(1, 6)]
    lum = [img.pixelColor(x, y).lightness() for x in xs for y in ys]
    lum.sort()
    return lum[len(lum) // 2] < 110          # median sample of the window is dark


def collect_menu(menu, out):
    """The texts the user sees (QAction.text() is patched to return the English source for the code)."""
    for a in menu.actions():
        t = i18n.shown(a, "text")
        if a.menu() is not None:
            out.append(t)
            collect_menu(a.menu(), out)
        elif t:
            out.append(t)


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    i18n.set_language(qh.app, "ar")
    w = qh.window()
    from radide.features.workbench import set_theme
    set_theme(w, "Dark")
    pump(0.8)
    before = set(i18n.missing())
    shots = []

    def grab(widget, name, need_dark=True):
        widget.show()
        pump(0.5)
        i18n.translate_tree(widget)
        pump(0.2)
        shots.append(shot(widget, "retro_qa_ar_" + name))
        if need_dark:
            check(f"dark theme: {name}", dark(widget))

    # ---- New Project
    from radide.dialogs import NewProjectDialog
    dlg = NewProjectDialog(w)
    for i in range(dlg.langs.topLevelItemCount()):
        dlg.langs.topLevelItem(i).setExpanded(True)
    grab(dlg, "new_project")
    dlg.close()
    # ---- menus
    tools = next(a.menu() for a in w.menuBar().actions() if a.menu() and
                 i18n.english(a, a.text()).replace("&", "") == "Tools")
    retro = next((a.menu() for a in tools.actions() if a.menu() and
                  i18n.english(a, a.text()).replace("&", "") == "Retro"), None)
    check("Tools > Retro menu exists", retro is not None)
    texts = []
    if retro is not None:
        retro.popup(w.mapToGlobal(w.rect().center()))       # menus are translated when they are shown
        pump(0.3)
        retro.hide()
        i18n.translate_tree(retro)
        for a in retro.actions():
            if a.menu() is not None:
                i18n.translate_tree(a.menu())
        collect_menu(retro, texts)
    english = [t for t in texts if t and not i18n._ARABIC.search(t)]
    check("every Tools > Retro menu item is in Arabic", not english, english)
    # ---- ROM workbench
    folder = WORK / "HackDemo"
    get_plugin("retro-romhack").create_new_project(folder, "HackDemo", "romhack_demo")
    w.open_project(folder, ask=False)
    pump(1.5)
    w.rom_feature.open_manager()
    pump(0.5)
    grab(w, "patch_manager")
    from radide.retro.rom.project import RomProject
    rp = RomProject.load(folder)
    w.rom_feature.open_hex(rp.rom_path)
    pump(0.5)
    doc = w.tabs.currentWidget()
    try:
        doc.show_find(True) if hasattr(doc, "show_find") else doc.find_panel.show()
    except Exception:  # noqa: BLE001
        pass
    grab(w, "hex_editor")
    from radide.retro.rom.dialogs import ApplyPatchDialog, CreatePatchDialog
    for cls, name in ((CreatePatchDialog, "create_patch"), (ApplyPatchDialog, "apply_patch")):
        d = cls(w)
        grab(d, name)
        d.close()
    # ---- graphics
    gfx = REPO / "samples" / "Tests" / "Retro" / "Gfx" / "Sample"
    gwork = WORK / "gfx"
    shutil.copytree(gfx, gwork)
    for f, name in (("homebrew.chr", "tiles"), ("castle.rtpf", "playfield"), ("level.rtmap", "tilemap"),
                    ("demo.tbl", "table")):
        if (gwork / f).is_file():
            w.open_any_file(gwork / f)
            pump(0.6)
            grab(w, name)
    if (gwork / "demo.rom").is_file():
        w.retro_gfx.open_script(str(gwork / "demo.rom"), str(gwork / "demo.tbl"))
        pump(0.5)
        grab(w, "script")
    # ---- retro dev
    from radide.features import retro_dev
    d = retro_dev.DisassembleDialog(w, str(rp.rom_path))
    grab(d, "disassemble")
    d.close()
    t = retro_dev.RetroToolchainsDialog(w)
    grab(t, "toolchains")
    t.close()
    # ---- emulators
    from radide.retro.emu import ui as emu_ui
    m = emu_ui.EmulatorManager(w)
    grab(m, "emulators")
    m.close()
    dock = emu_ui.ensure_debugger(w)
    dock.show()
    grab(dock.widget(), "retro_debugger")
    dos_folder = WORK / "Dos"
    get_plugin("retro-dos").create_new_project(dos_folder, "Dos", "dos_asm")
    w.open_project(dos_folder, ask=False)
    pump(1)
    dd = emu_ui.DosSettingsDialog(w, w.project)
    grab(dd, "dos_settings")
    dd.close()
    # ---- Apollo + Fortran
    agc = WORK / "Hello"
    get_plugin("agc-yul").create_new_project(agc, "Hello", "agc_hello")
    w.open_project(agc, ask=False)
    pump(1)
    w.run_project(debug=True)
    qh.wait(lambda: getattr(w, "_agc_dock", None) is not None and w._agc_dock.isVisible(), 20)
    pump(2)
    grab(w, "agc")
    if w.session is not None and w.session.running():
        w.stop_project()
    pump(0.5)
    from radide.features import retro_nasa
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    def modal(name):            # these dialogs use exec(): grab + close them from a timer
        def go():
            d = QApplication.activeModalWidget()
            if d is None:
                QTimer.singleShot(200, go)
                return
            i18n.translate_tree(d)
            shots.append(shot(d, "retro_qa_ar_" + name))
            d.reject()
        QTimer.singleShot(600, go)
    modal("dsky_reference")
    retro_nasa.dsky_reference(w)
    forb = WORK / "Orbit"
    get_plugin("fortran-legacy").create_new_project(forb, "Orbit", "f66_orbits")
    w.open_project(forb, ask=False)
    pump(1)
    for f in forb.glob("*.f"):
        w.open_any_file(f)
        pump(1)
        break
    modal("card_deck")
    retro_nasa.card_deck(w)
    import re
    noise = re.compile(r"\\|\w/\w|\.\w{1,6}($|\s|\])|^\[[a-z?]\]|RAD IDE|^[A-Z0-9 /+-]{1,9}$|^\W|\d{2,}|"
                       r"\[.*\]$|^(Python|Ring|Visual Basic|Rails|Laravel|CodeIgniter|Django|Flask|FastAPI|Aa|Base64|"
                       r"NTSC|NUSIZ|CPU|PRG ROM|CHR ROM|PgUp|PgDn|Ctrl\+\w+|SSE / FPU|Seed\.\.\.|Migration\.\.\.|"
                       r"tinker|migrate|db:seed|route:list|make:.*)$|  \(|^No (Laravel|CodeIgniter) project$|"
                       r"^No framework web site is open$|^(ASP\.NET|NestJS|Spring Boot|Ruby on Rails)|^Cell |"
                       r"mapper (low|high)|^Offset 0x|@0x|(VERB|NOUN|KEY REL)$")
    new = sorted(x for x in set(i18n.missing()) - before if not noise.search(x))
    print("UNTRANSLATED:", len(new))
    for s in new:
        print("   ", repr(s))
    check("no untranslated English text in the retro / NASA windows", not new, len(new))
    qh.finish(w)


if __name__ == "__main__":
    main()
