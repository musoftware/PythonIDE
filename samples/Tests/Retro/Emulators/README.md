# Retro emulators - tests (slice "emu")

These tests cover `radide/retro/emu`, `radide/features/retro_emu.py` and `radide/languages/retro_dos.py`. The details
are in [docs/RETRO.md](../../../../docs/RETRO.md#emulators-slice-emu-radideretroemu-radidefeaturesretro_emupy-radidelanguagesretro_dospy).

```
python samples/Tests/Retro/Emulators/test_emu.py            # core + IDE tests (QSettings RADIDE-TEST, offscreen)
python samples/Tests/Retro/Emulators/test_emu.py --no-ide   # without the IDE window
python samples/Tests/Retro/Emulators/test_emu.py --download # install missing emulators first (official builds)
python samples/Tests/Retro/Emulators/homebrew.py <folder>   # just write the homebrew test programs
```

* **Licences.** `homebrew.py` writes every test program byte by byte. They are original work, released as CC0:
  * a 2600 frame loop
  * an NES (NROM) colour cycler
  * a Game Boy palette loop
  * a GBA mode-3 loop at `0x080000D0`
  * a C64 `10 SYS 2061` border flasher, with a VICE label file
  * an Atari 8-bit XEX
  * a DOS `HELLO.COM`, with its NASM source

  No commercial ROM, BIOS or game data is used. The emulators are not part of the repository. On request they are
  downloaded from their official GitHub release pages into `%LOCALAPPDATA%\RADIDE\tools`, with pinned SHA-256:
  * Stella (GPL-2.0)
  * Mesen 2 (GPL-3.0)
  * FCEUX (GPL-2.0)
  * mGBA (MPL-2.0)
  * VICE (GPL-2.0)
  * Atari800 (GPL-2.0)
  * DOSBox-X (GPL-2.0)
* **Processes.** The test stops only the emulator processes it started itself (`RetroProcess.stop`).
* **What is checked:**
  * system detection
  * the catalogue
  * VICE monitor and GDB RSP framing
  * command lines: Stella `-debug -break -basedir` with symbols copied next to the ROM; VICE `-binarymonitor
    -moncommands -config`; mGBA `-g`
  * DOSBox-X `.conf` generation and DOS folder scan
  * each installed emulator launched minimised for about 4 s and then stopped
  * **VICE binary monitor** live: ping, info, registers, memory read and write, breakpoint hit, step, hot reload by
    autostart
  * **mGBA GDB stub** live: halt reason, registers, memory, breakpoint hit, step, I/O register
  * **DOSBox-X** running `HELLO.COM`, assembled by NASM, with its output captured to `OUT.TXT`
  * the DOS Program templates and `python -m radide.retro.emu dos` (F5)
  * Open Folder detection of a DOS program folder
  * in the IDE:
    * the Tools > Retro menu
    * the Emulators dialog (screenshot)
    * the Retro Debugger attached to VICE: registers, breakpoint by label, stop, step, hot reload (screenshot)
    * Project > DOS Settings saving `project.radproj`

Last run (2026-11-21): 67/67 passed, with all seven emulators installed.
