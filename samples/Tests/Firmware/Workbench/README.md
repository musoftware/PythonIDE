# Firmware & ECU workbench tests

The workbench is `radide/firmware/ui` plus `radide/features/firmware_ide.py`. See docs/FIRMWARE.md, section
"Workbench (UI)".

| Script | What it checks |
|---|---|
| `test_workbench_core.py` | No Qt. The synthetic demo image is checked against its known maps and checksums. The map finder is tested twice, once through the maps slice and once with the built-in fallback. Checksum verify and fix are run through the checksum slice and compared with the built-in code. Intel HEX and S-record files must load at their address. EEPROM chip sizes are recognised and the swap views are checked. The ECU project adapter goes from create to map pack to build with corrected checksums. Finally, an A2L file goes out and back through the maps slice. |
| `test_workbench_ide.py` | The real IDE through `qh.py`: QSettings org `RADIDE-TEST`, screenshots only with `widget.grab()`. It covers the menus and the one-time notice. It checks that `.ori` opens in the workbench and that an ordinary `.bin` does not. It opens an Intel HEX file and an EEPROM dump: read-only, with the 24C16 / 93C86 / 95160 chip names and the 16-bit swap view. Then it walks the project workflow:<br>1. New ECU Project, then load a checksum profile.<br>2. Find Maps, then add a map to the project.<br>3. Edit with `+` and `Page Up`, then Ctrl+Z / Ctrl+Y and a % change.<br>4. 2D and 3D views.<br>5. Verify (now wrong), Correct, Compare.<br>6. F7 Build: the output must have valid checksums and the original must be untouched.<br>7. Save Version, then compare with that version.<br>8. Analyze (PowerPC), Disassembly (`stwu` at 0x200), and the full maps / analysis views.<br>9. Import an A2L file, Save All, edit in Properties, then Solution Explorer > Open With.<br>An Arabic catalog check runs when `QA_LANG=ar`. |

Run them:

```
python samples\Tests\Firmware\Workbench\test_workbench_core.py
python samples\Tests\Firmware\Workbench\test_workbench_ide.py
set QA_LANG=ar& set QA_THEME=dark& python samples\Tests\Firmware\Workbench\test_workbench_ide.py
```

The screenshots go to `%TEMP%\radide-qa\shots\fw_<lang>[_dark]_NN_*.png`.

**Test data.** Everything is synthetic and is written at run time by `radide/firmware/ui/demo.py` (RAD IDE's own
code, with no manufacturer software and no vehicle data). No firmware is downloaded or committed.

**Try it by hand:**

1. Open *Tools > Firmware & ECU > New ECU Project (Demo Firmware)...*.
2. Press Ctrl+M, double-click a potential map, change cells with `+`, then press F7.
