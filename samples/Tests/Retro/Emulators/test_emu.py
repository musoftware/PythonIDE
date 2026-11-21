"""Tests of the retro emulators slice (radide/retro/emu) - see README.md.

    python samples/Tests/Retro/Emulators/test_emu.py [--download] [--no-ide]

Only homebrew programs written by homebrew.py are used. Every emulator process is started by this test and
stopped by it (RetroProcess.stop); nothing else is killed. The IDE part uses QSettings "RADIDE-TEST".
"""
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import homebrew  # noqa: E402

DOWNLOAD = "--download" in sys.argv
NO_IDE = "--no-ide" in sys.argv
WORK = Path(os.environ.get("QA_OUT") or Path(tempfile.gettempdir()) / "radide-qa") / "retro-emu"
WORK.mkdir(parents=True, exist_ok=True)
RESULTS = []
STARTED = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)
    return bool(cond)


def core_tests():
    from radide.retro.emu import detect_system, find_emulator, manager, run_rom
    from radide.retro.emu.catalog import EMULATORS, PREFERRED
    from radide.retro.emu.dos import (DosSettings, guess_start, is_dos_mz, looks_like_dos_program, make_conf,
                                      scan_dos_folder)
    from radide.retro.emu.launch import EmuError, command_for
    from radide.retro.emu.vice_monitor import ViceMonitor, load_labels
    from radide.retro.emu.gdb_rsp import frame, unescape

    roms = homebrew.write_all(WORK / "roms")
    # ---------------------------------------------------------------- detection
    for sysid, path in roms.items():
        check(f"detect {Path(path).name} -> {sysid}", detect_system(path) == sysid, detect_system(path))
    raw = WORK / "roms" / "cart.bin"
    raw.write_bytes(homebrew.atari2600())
    check("detect raw 4K .bin -> a2600 (reset vector)", detect_system(raw) == "a2600", detect_system(raw))
    check("folder -> dos", detect_system(WORK / "roms") == "dos")
    check("catalog: 7 emulators, official GitHub URLs, SHA-256 pinned",
          len(EMULATORS) == 7 and all(e.url.startswith("https://github.com/") and len(e.sha256) == 64
                                      for e in EMULATORS.values()))
    check("preferred: nes -> mesen, fceux; gba -> mgba; c64 -> vice",
          PREFERRED["nes"][:2] == ["mesen", "fceux"] and PREFERRED["gba"][0] == "mgba" and PREFERRED["c64"] == ["vice"])
    if DOWNLOAD:
        for eid in EMULATORS:
            if not manager.find(eid):
                check(f"download {eid}", manager.install(eid))
    st = {r["id"]: r for r in manager.status()}
    print("installed:", {k: bool(v["path"]) for k, v in st.items()})
    check("status() lists every emulator", set(st) == set(EMULATORS))

    # ---------------------------------------------------------------- protocol framing (offline)
    pkt = ViceMonitor.encode(7, 0x81)
    check("VICE request framing", pkt == bytes([2, 2, 0, 0, 0, 0, 7, 0, 0, 0, 0x81]))
    resp, rest = ViceMonitor.decode(bytes([2, 2, 2, 0, 0, 0, 0x01, 0, 7, 0, 0, 0, 0xAB, 0xCD, 9]))
    check("VICE response decoding", resp is not None and resp.request_id == 7 and resp.body == b"\xab\xcd"
          and rest == b"\x09")
    check("GDB RSP framing", frame("g") == b"$g#67" and unescape(b"a}\x03") == b"a#")
    lab = WORK / "roms" / "test.lbl"
    check("VICE label file", load_labels(lab).get(0x080D) == "loop")

    # ---------------------------------------------------------------- command lines (no start)
    if manager.find("vice"):
        p = command_for(roms["c64"], debug=True, symbols=str(lab))
        check("VICE command: binary monitor + autostart + moncommands + portable config",
              "-binarymonitor" in p.args and "-autostart" in p.args and "-moncommands" in p.args
              and "-config" in p.args and p.monitor_port > 0, p.args)
    if manager.find("stella"):
        sym = WORK / "roms" / "game_build.sym"
        sym.write_text("loop F019\n", encoding="ascii")
        p = command_for(roms["a2600"], debug=True, symbols=str(sym), breakpoints=[0xF019])
        check("Stella command: -debug, -break, -basedir, symbols copied next to the ROM",
              "-debug" in p.args and "$F019" in p.args and "-basedir" in p.args
              and (WORK / "roms" / "test.sym").is_file(), p.args)
    if manager.find("mgba"):
        p = command_for(roms["gba"], debug=True)
        check("mGBA command: -g GDB stub", "-g" in p.args and p.gdb_port == 2345, p.args)
    try:
        command_for(WORK / "roms" / "test.lbl")
        check("unknown file -> EmuError", False)
    except EmuError:
        check("unknown file -> EmuError", True)

    # ---------------------------------------------------------------- DOS helpers
    check("is_dos_mz: MZ yes, PE no", is_dos_mz(b"MZ" + bytes(62)) and
          not is_dos_mz(b"MZ" + bytes(58) + (0x40).to_bytes(4, "little") + b"PE\0\0"))
    check("guess_start prefers GAME.EXE over INSTALL.EXE",
          guess_start(["INSTALL.EXE", "GAME.EXE", "SETUP.EXE"]) == "GAME.EXE"
          and guess_start(["INSTALL.EXE", "TETRIS.EXE"]) == "TETRIS.EXE")
    game = WORK / "dosgame"
    game.mkdir(exist_ok=True)
    (game / "INSTALL.EXE").write_bytes(b"MZ" + bytes(200))
    (game / "PLAY.COM").write_bytes(homebrew.dos_com())
    conf, info = looks_like_dos_program(game)
    check("DOS folder scan", conf >= 0.7 and info["start"] == "PLAY.COM", (conf, info))
    s = DosSettings(program="SUB/GAME.EXE", cycles="fixed 3000", sound="none",
                    mounts=[{"drive": "D", "path": str(game), "type": "cdrom"}])
    text = make_conf(game, s)
    check("DOSBox-X conf: mount, cycles, sound, cd, program, exit",
          'mount c "' in text and "cycles=fixed 3000" in text and "sbtype=none" in text and "-t cdrom" in text
          and "cd \\SUB" in text and "GAME.EXE" in text and text.rstrip().endswith("exit"), text)
    check("scan_dos_folder finds the .COM", "PLAY.COM" in scan_dos_folder(game)["coms"])

    # ---------------------------------------------------------------- launch every installed emulator
    for sysid, rom in [("a2600", roms["a2600"]), ("nes", roms["nes"]), ("gb", roms["gb"]), ("gba", roms["gba"]),
                       ("a8", roms["a8"]), ("c64", roms["c64"])]:
        eid, exe = find_emulator(sysid)
        if not exe:
            print(f"SKIP launch {sysid}: no emulator installed")
            continue
        proc = run_rom(rom, minimized=True, quiet=True)
        STARTED.append(proc)
        time.sleep(4)
        alive = proc.alive()
        proc.stop()
        check(f"launch {eid} with homebrew {Path(rom).name} for 4 s, then stop it", alive and not proc.alive(),
              proc.command)
    if manager.find("fceux"):
        proc = run_rom(roms["nes"], emulator="fceux", minimized=True, quiet=True)
        STARTED.append(proc)
        time.sleep(4)
        alive = proc.alive()
        proc.stop()
        check("launch fceux (NES fallback)", alive and not proc.alive())

    # ---------------------------------------------------------------- VICE binary monitor (live)
    if manager.find("vice"):
        proc = run_rom(roms["c64"], debug=True, symbols=str(lab), minimized=True, quiet=True)
        STARTED.append(proc)
        try:
            m = proc.monitor(retry_for=25)
            m.timeout = 15
            check("VICE: connect + ping", m.ping())
            check("VICE: info (version)", m.info().startswith("3."), m.info())
            m.exit_monitor()
            time.sleep(2.5)
            m.pause()
            regs = m.registers()
            check("VICE: registers (PC in the loop)", regs.get("PC") in (0x080D, 0x0810), regs)
            mem = m.memory_get(0x0801, 0x0812)
            check("VICE: memory read = the .prg bytes", mem == homebrew.c64()[2:], mem.hex())
            n = m.checkpoint_set(0x080D)
            m.exit_monitor()
            ev = m.wait_stopped(6)
            check("VICE: breakpoint hit at $080D", ev is not None and ev.pc == 0x080D, ev)
            m.step(1)
            ev = m.wait_stopped(4)
            check("VICE: step -> $0810", ev is not None and ev.pc == 0x0810 and m.registers()["PC"] == 0x0810, ev)
            m.memory_set(0xC000, b"\x42\x43")
            check("VICE: memory write", m.memory_get(0xC000, 0xC001) == b"\x42\x43")
            m.checkpoint_delete(n)
            proc.reload(roms["c64"])
            check("VICE: hot reload in place (autostart, same process)", proc.alive() and proc.can_hot_reload())
        except Exception as e:  # noqa: BLE001
            check("VICE monitor session", False, repr(e))
        finally:
            proc.stop()
        check("VICE stopped", not proc.alive())

    # ---------------------------------------------------------------- mGBA GDB stub (live)
    if manager.find("mgba"):
        proc = run_rom(roms["gba"], debug=True, minimized=True, quiet=True)
        STARTED.append(proc)
        try:
            g = proc.gdb(retry_for=25)
            check("mGBA: GDB stub halt reason", g.halt_reason().startswith(("S", "T")))
            check("mGBA: 16 registers + cpsr", len(g.registers()) >= 16)
            check("mGBA: memory read = ROM code", g.read_memory(0x080000C0, 8) == homebrew.gba()[0xC0:0xC8])
            check("mGBA: breakpoint", g.set_breakpoint(homebrew.GBA_LOOP))
            g.cont()
            r = g.wait_stop(6)
            check("mGBA: breakpoint hit at the loop", r is not None and g.registers()["pc"] == homebrew.GBA_LOOP, r)
            g.step()
            check("mGBA: step", g.registers()["pc"] == homebrew.GBA_LOOP + 4)
            g.clear_breakpoint(homebrew.GBA_LOOP)
            check("mGBA: DISPCNT = mode 3 + BG2", g.read_memory(0x04000000, 2) == b"\x03\x04")
        except Exception as e:  # noqa: BLE001
            check("mGBA GDB session", False, repr(e))
        finally:
            proc.stop()

    # ---------------------------------------------------------------- DOSBox-X runs a .COM
    if manager.find("dosbox-x"):
        out = WORK / "roms" / "OUT.TXT"
        out.unlink(missing_ok=True)
        com = roms["dos"]
        try:
            from radide.retro.emu.dos import build_com_with_nasm
            built = build_com_with_nasm(WORK / "roms" / "HELLO.ASM", log=lambda *_: None)
            if built:
                com = built
                check("NASM assembled HELLO.ASM to HELLO.COM", Path(built).read_bytes()[:2] == b"\xb4\x09")
        except Exception as e:  # noqa: BLE001
            print("NASM not used:", e)
        proc = run_rom(com, minimized=True, redirect="OUT.TXT", silent=True, time_limit=40)
        STARTED.append(proc)
        rc = proc.wait(60)
        if rc is None:
            proc.stop()
        txt = out.read_text(errors="replace") if out.is_file() else ""
        check("DOSBox-X ran HELLO.COM (output captured)", homebrew.DOS_TEXT in txt, (rc, txt))

    # ---------------------------------------------------------------- DOS Program plugin + Open Folder
    from radide.languages import get_plugin
    plug = get_plugin("retro-dos")
    for tmpl, fname in (("dos_asm", "HELLO.ASM"), ("dos_existing", "README.txt")):
        d = WORK / "projects" / tmpl
        if (d / "project.radproj").exists():
            (d / "project.radproj").unlink()
        pr = plug.create_new_project(d, "DosTest", tmpl)
        check(f"New Project template {tmpl}", (d / fname).is_file() and pr.language == "retro-dos"
              and "dos" in pr.extra)
    spec = plug.run_spec(WORK / "projects" / "dos_asm", "HELLO.ASM", "")
    check("run_spec = python -m radide.retro.emu dos <file>", spec.args[:3] == ["-m", "radide.retro.emu", "dos"]
          and "PYTHONPATH" in (spec.env or {}))
    if manager.find("dosbox-x"):
        import subprocess
        d = WORK / "projects" / "dos_asm"
        (d / "HELLO.ASM").write_text(homebrew.DOS_ASM, encoding="ascii")
        import json
        pj = json.loads((d / "project.radproj").read_text(encoding="utf-8"))
        pj["dos"]["args"] = ""
        (d / "project.radproj").write_text(json.dumps(pj), encoding="utf-8")
        env = dict(os.environ, **(spec.env or {}))
        try:
            from radide.asm.toolchain import find as asm_find
            has_nasm = bool(asm_find("nasm"))
        except Exception:  # noqa: BLE001
            has_nasm = False
        if has_nasm:
            r = subprocess.run([sys.executable, "-m", "radide.retro.emu", "dos", str(d / "HELLO.ASM")], cwd=str(d),
                               env=env, capture_output=True, text=True, timeout=90)
            check("F5 of a DOS .COM project: NASM build + DOSBox-X run", r.returncode == 0
                  and "Built HELLO.COM" in r.stdout and (d / "HELLO.COM").is_file(), r.stdout + r.stderr)
    from radide import project_detect
    from radide.features.retro_emu import register_detector
    register_detector()
    det = project_detect.detect(game)
    cands = det.candidates()
    check("Open Folder: DOS program detected", any(c.kind == "dos-program" and c.language == "retro-dos"
                                                    for c in cands), [c.title for c in cands])


def ide_tests():
    os.environ.setdefault("QA_NAME", "retro-emu")
    sys.path.insert(0, str(ROOT / "samples" / "Tests" / "QA" / "Integration"))
    import qh
    from radide.retro.emu import manager
    from radide.retro.emu import ui
    w = qh.window()
    tools = next(a.menu() for a in w.menuBar().actions() if a.text().replace("&", "") == "Tools")
    retro = next((a.menu() for a in tools.actions() if a.menu() is not None and a.text().replace("&", "") == "Retro"),
                 None)
    names = [a.text().replace("&", "") for a in retro.actions()] if retro else []
    qh.check("Tools > Retro menu with the emulator commands",
             all(n in names for n in ("Emulators...", "Run ROM in Emulator...", "Debug ROM in Emulator...",
                                      "Reload ROM in Emulator")), names)
    dlg = ui.show_manager(w)
    qh.pump(0.5)
    qh.check("Retro Emulators dialog lists 7 emulators", dlg.table.rowCount() == 7)
    qh.shot(dlg, "retro_emulators_manager")
    dlg.close()
    from radide.dialogs import LANGUAGE_GROUPS
    qh.check("New Project: Retro group has DOS Program", any(g == "Retro" and "retro-dos" in ids
                                                            for g, ids in LANGUAGE_GROUPS))
    roms = homebrew.write_all(WORK / "roms")
    if manager.find("vice"):
        proc = ui.start_rom(w, roms["c64"], debug=True)
        STARTED.append(proc)
        dock = getattr(w, "_retro_debug_dock", None)
        dbg = dock.widget() if dock else None
        ok = dbg is not None and dbg.client is not None
        qh.check("Debug ROM: Retro Debugger attached to VICE", ok, dbg.status.text() if dbg else "no dock")
        if ok:
            qh.check("Retro Debugger shows registers", dbg.regs.topLevelItemCount() >= 6)
            dbg.bp_edit.setText("loop")
            dbg.add_breakpoint()
            qh.check("breakpoint by label", dbg.bps.topLevelItemCount() == 1 and "080D" in dbg.bps.topLevelItem(0).text(0))
            dbg.do_continue()
            qh.check("stops at the breakpoint", qh.wait(lambda: "$080D" in dbg.status.text(), 10), dbg.status.text())
            qh.check("memory view shows the .prg", "0801" in dbg.mem.toPlainText() or "080D" in dbg.mem.toPlainText()
                     or dbg.mem.toPlainText().strip() != "")
            dbg.do_step()
            qh.check("step", "$0810" in dbg.status.text(), dbg.status.text())
            dock.resize(1100, 380)
            qh.shot(dock, "retro_debugger_vice")
            ui.hot_reload(w)
            qh.check("Reload ROM in Emulator (VICE hot reload)", proc.alive())
        proc.stop()
    from radide.languages import get_plugin
    d = WORK / "projects" / "ide_dos"
    (d / "project.radproj").unlink(missing_ok=True)
    pr = get_plugin("retro-dos").create_new_project(d, "IdeDos", "dos_existing")
    (d / "GAME.EXE").write_bytes(b"MZ" + bytes(100))
    dlg = ui.DosSettingsDialog(w, pr)
    dlg.program.setCurrentText("GAME.EXE")
    dlg.cycles.setCurrentText("fixed 8000")
    dlg.accept()
    from radide.model import Project
    pr2 = Project.load(d)
    qh.check("DOS Settings saved into project.radproj", pr2.extra["dos"]["program"] == "GAME.EXE"
             and pr2.extra["dos"]["cycles"] == "fixed 8000")
    for n, c in RESULTS:
        qh.RESULTS.append((n, c))
    qh.finish(w)


if __name__ == "__main__":
    try:
        core_tests()
    finally:
        for p in STARTED:
            try:
                p.stop()
            except Exception:  # noqa: BLE001
                pass
    if NO_IDE:
        ok = sum(1 for _, c in RESULTS if c)
        print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
        sys.exit(0 if ok == len(RESULTS) else 1)
    try:
        ide_tests()
    finally:
        for p in STARTED:
            try:
                p.stop()
            except Exception:  # noqa: BLE001
                pass
