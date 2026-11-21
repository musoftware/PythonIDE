"""DOS program development (slice "dosdev" of radide/retro, docs/RETRO.md "DOS programs").

Project kinds (radide/languages/dos_*.py, New Project > DOS):

    qbasic   QBasic / QuickBASIC program   FreeBASIC ``-lang qb`` (its DOS build, run inside DOSBox-X) -> real DOS
             EXE; optionally the user's own QBASIC.EXE / QB.EXE runs the source in DOSBox-X
    pascal   Turbo Pascal-style program    Free Pascal i8086-msdos cross compiler ({$mode tp}, Crt / Dos / Graph)
    c        Turbo C-style program         OpenWatcom v2 wcl (16-bit small / large model), conio / graph;
                                           DJGPP (32-bit protected mode) when the user configured one
    asm      DOS Assembly (MASM syntax)    JWasm -> MZ .EXE or .COM; F5 can step it in RAD IDE's 8086 emulator
    batch    DOS Batch (.BAT)              runs in DOSBox-X

Modules (no Qt except where noted)::

    toolchain.py   download / find the free compilers (official sources, SHA-256 pinned) + the user's own
                   QBasic / Turbo Pascal / Turbo C folders
    dosbox.py      DOSBox-X adapter: .conf per run, mount, cycles presets, headless runs, debugger
    helpers.py     tiny original DOS helper programs (key stuffer, screen dump, mode 13h capture)
    build.py       ``python -m radide.retro.dos.build <folder>``: one build, Error List rows in _build/diags.json
    run.py         ``python -m radide.retro.dos.run <folder> [--debug] [--qbasic]``: build + start DOSBox-X
    errors.py      compiler message parsers (FreeBASIC, Free Pascal, OpenWatcom, JWasm, TP, TC, BC, DJGPP)
    compat.py      old source compatibility (line numbers, BGI, TP units without source, ...)
    templates.py   New Project templates (hello, menu, mode 13h, PC speaker, mouse) for every kind
    reference.py   IntelliSense data: DOS / BIOS interrupts, QBasic, Crt / Dos / Graph, conio / dos.h
    plugin.py      DosPluginBase shared by the language plugins
"""
from __future__ import annotations

KINDS = ("qbasic", "pascal", "c", "asm", "batch")
