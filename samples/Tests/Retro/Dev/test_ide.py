"""Retro dev slice - IDE test (QSettings org RADIDE-TEST, screenshots with widget.grab() only).

New Project dialog (Retro Games group), a 2600 project opened in the IDE (editor keeps the 6502 plugin, no x86
overlay), Tools > Retro > Retro Development menu, Rebuild Check, Error List rows of a broken build,
"Disassemble ROM into Project" dialog end to end (byte-identical), Retro Toolchains dialog, Arabic strings.

    python samples/Tests/Retro/Dev/test_ide.py
"""
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QA_NAME", "retro_dev")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, shot, wait  # noqa: E402

from radide.languages import get_plugin  # noqa: E402


def main():
    w = qh.window()
    work = Path(qh.WORK) / "retro_dev"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    # ---- New Project dialog: Retro Games group
    from radide.dialogs import NewProjectDialog
    dlg = NewProjectDialog(w)
    groups = {}
    for i in range(dlg.langs.topLevelItemCount()):
        g = dlg.langs.topLevelItem(i)
        groups[g.text(0)] = [g.child(j).text(0) for j in range(g.childCount())]
    retro = groups.get("Retro Games", [])
    check("New Project: Retro Games group with 5 systems", len(retro) == 5 and any("2600" in x for x in retro) and
          any("ZX" in x for x in retro), groups.keys())
    dlg.show()
    pump(0.5)
    shot(dlg, "retro_dev_new_project")
    dlg.close()

    # ---- a 2600 project in the IDE
    plugin = get_plugin("retro-atari2600")
    folder = work / "Smiley2600"
    plugin.create_new_project(folder, "Smiley2600", "a2600_kernel")
    w.open_project(folder, ask=False)
    pump(2)
    check("project opened", w.project is not None and w.project.language == "retro-atari2600",
          getattr(w.project, "language", None))
    w.open_any_file(folder / "main.asm")
    pump(3)
    ed = w.tabs.currentWidget()
    edp = getattr(ed, "plugin", None) or getattr(getattr(ed, "editor", None), "plugin", None)
    check("editor of main.asm keeps the 6502 retro plugin (no x86 overlay)",
          edp is not None and getattr(edp, "retro_dev", False), repr(edp))
    shot(w, "retro_dev_editor")

    # ---- menus
    retro_menu = getattr(w, "retro_menu", None)
    titles = []
    if retro_menu is not None:
        for a in retro_menu.actions():
            if a.menu() is not None and "Development" in a.text():
                titles = [x.text() for x in a.menu().actions()]
    check("Tools > Retro > Retro Development menu", any("Disassemble ROM" in t for t in titles) and
          any("Toolchains" in t for t in titles), titles)

    # ---- rebuild check (build) and Error List
    from radide.features import retro_dev
    qh.MSGS.clear()
    retro_dev.rebuild_check(w)
    pump(0.5)
    check("Rebuild Check builds the project", (folder / "Smiley2600.bin").is_file() and
          any("Built" in str(m) for m in qh.MSGS), qh.MSGS)
    main_asm = folder / "main.asm"
    good = main_asm.read_text(encoding="utf-8")
    main_asm.write_text(good + "        ldq #1\n", encoding="utf-8")
    retro_dev.rebuild_check(w)
    pump(0.5)
    el = w.error_list
    rows = [(el.topLevelItem(i).text(0), el.topLevelItem(i).text(2), el.topLevelItem(i).text(3))
            for i in range(el.topLevelItemCount())]
    want_line = str(good.count("\n") + 1)
    check("Error List row for the DASM error (main.asm + line)", ("Error", "main.asm", want_line) in rows, rows)
    shot(w, "retro_dev_error_list")
    main_asm.write_text(good, encoding="utf-8")
    retro_dev.rebuild_check(w)

    # ---- Disassemble ROM into Project dialog
    rom = work / "Smiley2600.bin"
    shutil.copy2(folder / "Smiley2600.bin", rom)
    d = retro_dev.DisassembleDialog(w, str(rom))
    d.folder.setText(str(work / "Smiley_disasm"))
    d.show()
    d.run()
    check("disassembly finished", wait(lambda: d.result_obj is not None or "Could not" in d.summary.text(), 120),
          d.summary.text())
    check("dialog shows byte-identical rebuild", "byte-identical" in d.summary.text(), d.summary.text())
    pump(0.3)
    shot(d, "retro_dev_disassemble")
    d.open_project()
    pump(2)
    check("disassembled project opens", w.project is not None and Path(w.project.folder).name == "Smiley_disasm")
    qh.MSGS.clear()
    retro_dev.rebuild_check(w)
    check("Rebuild Check on the disassembly: byte-identical", any("Byte-identical" in str(m) for m in qh.MSGS),
          qh.MSGS)

    # ---- toolchains dialog
    t = retro_dev.RetroToolchainsDialog(w)
    t.show()
    pump(0.3)
    rows = [t.table.item(i, 0).text() for i in range(t.table.rowCount())]
    check("Retro Toolchains dialog lists DASM / cc65 / RGBDS / sjasmplus", len(rows) == 5 and
          any("DASM" in r for r in rows))
    shot(t, "retro_dev_toolchains")
    t.close()

    # ---- Arabic
    import json
    ar = json.loads((Path(qh.ROOT) / "radide" / "i18n" / "ar.json").read_text(encoding="utf-8"))["strings"]
    needed = ["Disassemble ROM into Project", "Retro Toolchains", "Rebuild Check", "Re-disassemble with Hints",
              "Retro Games", "Retro &Development", "Disassemble ROM into Project...", "Byte-identical to the original ROM."]
    missing = [s for s in needed if s not in ar]
    check("Arabic strings for the retro dev UI", not missing, missing)
    qh.finish(w)


if __name__ == "__main__":
    main()
