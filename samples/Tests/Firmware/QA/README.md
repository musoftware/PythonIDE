# Firmware & ECU - end-to-end QA

`qa_firmware_e2e.py` uses the real RAD IDE window the way a user would (qh.py harness: QSettings org `RADIDE-TEST`,
`RADIDE_NO_BROWSER=1`, screenshots only through `widget.grab()` into `%TEMP%\radide-qa\shots\fwe2e_*.png`).

    python samples\Tests\Firmware\QA\qa_firmware_e2e.py
    set QA_LANG=ar & set QA_THEME=dark & python samples\Tests\Firmware\QA\qa_firmware_e2e.py
    set QA_GHIDRA=1 & python samples\Tests\Firmware\QA\qa_firmware_e2e.py      (Ghidra headless on rusEFI, minutes)

Data:

- a synthetic ARM Cortex-M image written by RAD IDE (`radide/firmware/analysis/synth.py`: Thumb code, vector table,
  calibration maps with axes, identification strings) with two generic checksum blocks added by the test;
- rusEFI firmware (GPL-3.0 with rusEFI's additional terms), downloaded only from github.com/rusefi/rusefi releases by
  `../Formats/download_rusefi.py` into `%TEMP%\radide-fw-data` (skipped when offline). Nothing downloaded is committed.

No manufacturer firmware is used. The test also checks the regression paths: a `.nes` and an ordinary `.bin` still
open in the retro hex editor, `go.mod` stays text, Python / C files open in the code editor.
