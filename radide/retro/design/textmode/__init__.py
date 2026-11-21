"""DOS text-mode designer (slice "tuidesign", docs/RETRO.md "DOS text-mode designer").

    cp437.py      the IBM PC character set, box-drawing table, the 16 text-mode colours
    buffer.py     CellBuffer: cols x rows cells of (character, attribute), the B800 layout
    model.py      TScreen / TControl, the .tform JSON format, validation
    render.py     TScreen -> CellBuffer: exactly what the generated program shows
    codegen/      program generators (basic.py, pascal.py, c.py, asm.py) and their run-times; common.py
    sim.py        the generated run-time's event loop in Python (Test Run, tests)
    ansi.py       .ANS (SAUCE) / .BIN / .TXT art files
    project.py    DOS Text-Mode Forms App projects: generate, build (dosdev Builder), run / capture in DOSBox-X
    glyphs.py, canvas.py, designer.py, ansieditor.py   the Qt views (designer, ANSI art editor)

No Qt in the core modules (cp437, buffer, model, render, codegen, sim, ansi, project).
"""
