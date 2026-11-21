"""Follow-ups of the retro / DOS testers (see README.md here):

  mesen      the portable Mesen 2 settings RAD IDE creates have controller port 1 + keys (NES / SNES / Game Boy);
             an old RAD-created config without a controller gets a one-time "Apply Controller Defaults" bar
  handoff    a second Mesen start in single-instance mode is followed to the window that took the ROM
  i18n       every New Project row is translated in Arabic ("NES  (cc65 / ca65)" = ar.json "NES (cc65 / ca65)")
  tutorial   DOS lesson blocks are highlighted, have Try it / Check, Try it runs captured in DOSBox-X

    python samples/Tests/Retro/FollowUps/test_retro_followups.py [phases]
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ.setdefault("QA_NAME", "retro_followups")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "QA" / "Integration"))
import qh  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

check, pump, wait = qh.check, qh.pump, qh.wait
WORK = Path(qh.WORK) / "retro_followups"
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True, exist_ok=True)
PHASES = [a for a in sys.argv[1:] if not a.startswith("-")] or ["mesen", "handoff", "tutorial", "i18n"]


# ====================================================================== Mesen controller defaults
def phase_mesen(w):
    from radide.retro.emu import inputs
    sp = WORK / "mesen" / "settings.json"
    sp.parent.mkdir(parents=True, exist_ok=True)
    check("new portable Mesen settings are written", inputs.write_new_mesen_settings(sp))
    d = json.loads(sp.read_text(encoding="utf-8"))
    nes = d["Nes"]["Port1"]
    check("NES port 1 = NesController, arrows / X / Z / Enter / Right Shift",
          nes["Type"] == "NesController" and nes["Mapping1"]["Up"] == inputs.K_UP and nes["Mapping1"]["A"] ==
          inputs.K_X and nes["Mapping1"]["B"] == inputs.K_Z and nes["Mapping1"]["Start"] == inputs.K_ENTER and
          nes["Mapping1"]["Select"] == inputs.K_RSHIFT, nes)
    check("Backspace / Left Shift = Select too, Xbox pad in Mapping2",
          nes["Mapping3"]["Select"] == inputs.K_BACK and nes["Mapping4"]["Select"] == inputs.K_LSHIFT and
          nes["Mapping2"]["Start"] == 4101)
    check("SNES port 1 and Game Boy controller set", d["Snes"]["Port1"]["Type"] == "SnesController" and
          d["Gameboy"]["Controller"]["Type"] == "GameboyController")
    check("one Mesen window per Run (SingleInstance off) in a new config", d["Preferences"]["SingleInstance"] is False)
    sp.write_text('{"Nes": {"Port1": {"Type": "Zapper"}}}', encoding="utf-8")
    check("an existing settings.json is never overwritten", not inputs.write_new_mesen_settings(sp) and
          json.loads(sp.read_text(encoding="utf-8")) == {"Nes": {"Port1": {"Type": "Zapper"}}})
    # an old RAD-created config (Mesen wrote the whole file: port 1 "None", every key 0), SNES customised
    old = {"Version": "2.1.1", "Nes": {"Port1": {"Type": "None", "Mapping1": {"A": 0, "B": 0, "Up": 0}},
                                       "Region": "Auto"},
           "Snes": {"Port1": {"Type": "SnesController", "Mapping1": {"A": 44}}},
           "Gameboy": {"Controller": {"Type": "None", "Mapping1": {"A": 0}}}, "Preferences": {"SingleInstance": True}}
    sp.write_text(json.dumps(old), encoding="utf-8")
    check("an old config without controller needs defaults (NES, Game Boy; not the customised SNES)",
          inputs.needs_mesen_defaults(sp) == ["Nes", "Gameboy"], inputs.needs_mesen_defaults(sp))
    # the IDE offer (once), pointed at this file
    from radide.features import retro_emu
    from radide.retro.emu import manager
    real = manager.mesen_settings_file
    manager.mesen_settings_file = lambda: sp
    try:
        w.settings.remove(retro_emu.MESEN_OFFER_KEY)
        bar = retro_emu.mesen_input_offer(w)
        pump(0.3)
        check("the IDE offers the defaults in a bar (non-blocking) + Output", bar is not None and bar.isVisible()
              and "Apply Controller Defaults" in w.output.toPlainText())
        if bar is not None:
            qh.shot(w.statusBar(), "retro_mesen_offer_bar")
            from PyQt6.QtWidgets import QPushButton
            bar.findChild(QPushButton, "MesenInputApply").click()
            pump(0.3)
        d = json.loads(sp.read_text(encoding="utf-8"))
        check("Apply sets NES + Game Boy port 1, keeps SNES, Region and SingleInstance",
              d["Nes"]["Port1"]["Type"] == "NesController" and d["Nes"]["Port1"]["Mapping1"]["A"] == inputs.K_X
              and d["Gameboy"]["Controller"]["Type"] == "GameboyController"
              and d["Snes"]["Port1"] == {"Type": "SnesController", "Mapping1": {"A": 44}}
              and d["Nes"]["Region"] == "Auto" and d["Preferences"]["SingleInstance"] is True, d)
        sp.write_text(json.dumps(old), encoding="utf-8")
        check("the offer is shown only once", retro_emu.mesen_input_offer(w) is None)
    finally:
        manager.mesen_settings_file = real
    for name, ok in emulator_input_verified():
        check(name, ok)


def emulator_input_verified():
    """FCEUX / mGBA / Stella start with input: built-in keyboard defaults (verified once, see README)."""
    from radide.retro.emu import manager
    rows = []
    stella_db = manager.local_root() / "retro" / "stella" / "stella.sqlite3"
    if stella_db.is_file():
        import sqlite3
        con = sqlite3.connect(f"file:{stella_db}?mode=ro", uri=True)
        try:
            keys = dict(con.execute("select setting, value from settings where setting like 'keymap%'"))
        except sqlite3.Error:
            keys = {}
        finally:
            con.close()
        rows.append(("Stella's portable config has keyboard joystick mappings", any(v not in ("", "[]")
                                                                                     for v in keys.values())))
    return rows


# ====================================================================== single-instance handoff
def phase_handoff(_w):
    import psutil
    from radide.retro.emu import manager, run_rom
    exe = manager.find("mesen")
    rom = Path(__file__).resolve().parents[1] / "GameMod_DABG" / "original" / "dabg.nes"
    if not exe or not rom.is_file():
        print("SKIP handoff: Mesen or the test ROM missing")
        return
    if any((p.info["name"] or "").lower() == "mesen.exe" for p in psutil.process_iter(["name"])):
        print("SKIP handoff: a Mesen is already open (not ours)")
        return
    a = run_rom(str(rom), system="nes", emulator="mesen", minimized=True, quiet=True)
    try:
        wait(lambda: time.time() > a.started_at + 3, 10)
        b = run_rom(str(rom), system="nes", emulator="mesen", minimized=True, quiet=True)
        wait(lambda: b.popen.poll() is not None, 6)
        single = b.popen.poll() is not None
        if single:
            check("second Mesen start hands off: RetroProcess follows the open window", b.alive() and b.handed_off
                  and b.real_pid == a.pid, b.exit_info())
        else:
            check("Mesen in multi-instance mode keeps its own window", b.alive())
        b.stop()
        check("stop() never closes the window that took the ROM", a.alive() and not b.alive(), b.exit_info())
    finally:
        for p in (locals().get("b"), a):
            if p is not None:
                p.stop()
    check("first Mesen stopped", not a.alive())


# ====================================================================== DOS tutorials
def phase_tutorial(w):
    from radide import tutorials as T
    from radide.features import tutorials as TU
    from radide.tutorials.html import block_html
    course = T.course("dos-programming")
    blocks = [(les, b) for les in course.lessons for b in les.blocks() if b.lang in T.DOSL]
    langs = {b.lang for _l, b in blocks}
    check("dos-qbasic / pascal / c / asm / batch blocks are recognised", langs == set(T.DOSL), langs)
    for lang in sorted(langs):
        les, b = next((x, y) for x, y in blocks if y.lang == lang and y.role == "run")
        h = block_html(b)
        check(f"{lang}: highlighted, Try it and Check buttons", '<span class="' in h and "radAct('try'" in h
              and "radAct('check'" in h and f'id="res{b.index}"' in h, h[:300])
    les = course.lesson("02-qbasic")
    b = next(x for x in les.blocks() if x.lang == "dos-qbasic" and x.role == "run" and x.expected)
    r = T.check(b, work=WORK / "check_ok")
    check("Check: the example builds, runs in DOSBox-X and matches its output", r.ok, (r.problems, r.output[-400:]))
    r2 = T.check(b, code=b.code.replace("Hello", "Bye"), work=WORK / "check_bad")
    check("Check: a changed program is reported as not matching", not r2.ok and r2.problems, r2.problems)
    # the IDE: Try it creates the QBasic DOS project and runs it captured (Output shows the program output)
    panel = TU.show_tutorials(w, "dos-programming", "02-qbasic")
    pump(2)
    w.output.clear()
    panel.dos_proc = None
    ok = panel.try_block(b.index)
    check("Try it opens a QBasic DOS project", ok and w.project is not None and w.project.language == "dos-qbasic",
          w.project and w.project.language)
    wait(lambda: panel.dos_proc is not None, 10)
    proc = panel.dos_proc
    done = wait(lambda: proc is not None and proc.state() == proc.ProcessState.NotRunning, 240)
    out = w.output.toPlainText()
    from radide.tutorials.dos_support import lines_of
    first = next(x for x in lines_of(b.expected) if x.strip())
    check("Try it runs it captured in DOSBox-X and shows the output", done and "program output" in out and
          first in out, out[-800:])
    qh.shot(w, "retro_dos_tutorial_try")
    panel.last_check = None
    panel.check_block(b.index, None)
    wait(lambda: getattr(panel, "last_check", None) is not None, 240)
    r = getattr(panel, "last_check", None)
    check("Check button in the lesson: ✓ (opened project checked)", r is not None and r.ok, r and r.problems)


# ====================================================================== New Project in Arabic
def phase_i18n(_w):
    import re
    from PyQt6.QtCore import Qt
    from radide import i18n
    from radide.dialogs import NewProjectDialog
    i18n.set_language(qh.app, "ar")
    try:
        check("lookup tolerates layout spaces", i18n.tr("NES  (cc65 / ca65)") == i18n.tr("NES (cc65 / ca65)") !=
              "NES (cc65 / ca65)")
        d = NewProjectDialog()
        d.show()
        pump(0.5)
        i18n.translate_widget(d)
        pump(0.3)
        rows, untranslated = [], []
        for i in range(d.langs.topLevelItemCount()):
            g = d.langs.topLevelItem(i)
            for j in range(g.childCount()):
                it = g.child(j)
                shown = it.data(0, Qt.ItemDataRole.DisplayRole)
                rows.append(shown)
                if i18n.tr(i18n.english(it, shown) if hasattr(i18n, "english") else shown) == shown and \
                        not re.search(r"[؀-ۿ]", shown) and re.sub(r" {2,}", " ", shown) not in i18n._strings:
                    untranslated.append(shown)
        for want in ("أتاري 2600", "نينتندو NES", "جيم بوي", "لغة التجميع (MASM)"):
            check(f"New Project row shown in Arabic: {want}", any(want in r for r in rows))
        check("every New Project row has an Arabic catalog entry", not untranslated, untranslated)
        qh.shot(d, "retro_newproject_ar")
        d.close()
    finally:
        i18n.set_language(qh.app, "en")


def main():
    w = qh.window()
    for ph in PHASES:
        try:
            globals()["phase_" + ph](w)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            check(f"phase {ph} ran", False, e)
    qh.finish(w)


if __name__ == "__main__":
    main()
