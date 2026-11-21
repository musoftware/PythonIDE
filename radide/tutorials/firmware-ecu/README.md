# Firmware & ECU course (Arabic)

`course.json` + 8 lessons (`NN-slug.md`) about control-unit / firmware files (the ".bin of a Mercedes and others"):
what they are and the legal / safety side, raw / Intel HEX / S-record, memory maps and CPU + base detection,
disassembly and Ghidra, calibration maps and the map finder, editing with physical units and A2L, checksums, and a
full ECU project with versions, reports and an IPS patch.

Scope: general analysis and calibration editing for repair, research, education and lawful tuning. The course has
no immobiliser, emissions-system, odometer or VIN / security-access content. Every example uses synthetic firmware
written by RAD IDE (radide/firmware/*/synth.py); no manufacturer file is used or downloaded.

Block kinds besides the usual `python run` / `exercise` / `solution`, `text output` and `quiz`:

| Fence | Checked by `tools/check_lessons.py` |
|---|---|
| `fwpy run` | Python that uses RAD IDE's firmware library (`radide.firmware.*`), run in a fresh folder with the repository on PYTHONPATH; output = the following `text output` block. The lesson viewer shows it as code. |

    python radide/tutorials/firmware-ecu/tools/check_lessons.py [-v] [lesson-id-prefix ...]
    python radide/tutorials/firmware-ecu/tools/check_lessons.py --fill     # maintainer: fill "TODO" outputs
    python tools/build_chm.py firmware-ecu --verify
