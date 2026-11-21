# Retro / NASA - end-to-end QA

User-level checks across the retro slices (ROM workbench, retro development, graphics & text, emulators, Apollo
AGC + legacy Fortran). They drive the real IDE (offscreen, QSettings "RADIDE-TEST" via
`samples/Tests/QA/Integration/qh.py`), start the real emulators and stop only the processes they started.
Screenshots: `widget.grab()` only, in `%TEMP%\radide-qa\shots\retro_qa_*.png`. No ROM is downloaded; every
program used is original homebrew from the retro templates / samples (CC0), and Comanche055 is the public-domain
Apollo 11 source fetched from the official Virtual AGC GitHub repository into the work folder (not the repo).

| Script | What it checks |
|---|---|
| `e2e_projects.py` | New Project for every retro type (2600, NES asm/C, Game Boy, C64 asm/C, ZX, DOS .COM, ROM Hacking, AGC, Fortran 66/77) -> Build Project -> F5 in the real emulator (Stella, Mesen, mGBA, VICE, DOSBox-X) -> Stop closes the emulator too; AGC F5 = DSKY dock; Fortran output |
| `e2e_workflows.py` | ROM hacking chain (hex edit -> IPS capture -> Tile Editor -> file bus refresh -> Script Dump/Insert -> BPS capture -> build == working copy, original untouched, Create/Apply Patch dialogs, F5 with the patched ROM); Disassemble ROM into Project byte-identical for NES, Game Boy and the ROM slice's synthetic NES ROM; Hello DSKY V35E by clicking the DSKY; Comanche055 download -> Build with yaYUL 0 errors -> F5 in yaAGC answers V35E -> Stop ends yaAGC; OrbitTable output |
| `e2e_arabic_dark.py` | Arabic UI + Dark theme over every retro / NASA window: all Tools > Retro menu items in Arabic, no untranslated UI text (i18n.missing()), dark backgrounds |
| `e2e_regression.py` | Existing languages unaffected: Python Tk, C, NASM, Fortran, VB create + run; Open Folder detection of the old samples; .asm / .f90 / .py routing; python.exe not taken for a ROM |

    python samples/Tests/Retro/QA/e2e_projects.py [template words ...]
    python samples/Tests/Retro/QA/e2e_workflows.py [rom] [disasm] [agc] [fortran] [--no-net]
    python samples/Tests/Retro/QA/e2e_arabic_dark.py
    python samples/Tests/Retro/QA/e2e_regression.py

Needs the toolchains and emulators the slices download on request (Tools > Retro > Emulators..., Retro
Toolchains, Virtual AGC Toolchain); missing ones make the matching checks fail with the IDE's own message.
