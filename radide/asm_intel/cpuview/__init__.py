"""OllyDbg-style CPU view for RAD IDE (the engine side; the IDE glue is radide/features/asm_cpu_view.py).

    analysis   pure helpers (no Qt): source jump arrows, register reads / writes, procedure ranges, conditional
               jump evaluation, inline-value text, capstone decoding with re-synchronisation, stack annotations,
               one-line assemblers (NASM / the 8086 emulator's assembler), value formatting
    backend    one interface over the two debuggers: NativeBackend (gdb over DAP: asm, C, C++, Rust - imports
               radide/nativedbg.py) and EmuBackend (radide/emu8086's Machine / Emu8086Session)
    notes      user comments and labels per project (``.radide/cpu_notes.json``)
    texts      English / Arabic texts of the view (follows the IDE language)
    panes      the Qt widgets: disassembly, registers, dump, stack and the CpuView that keeps them in sync
    editor_live  the source editor while debugging: inline values, jump arrows in the gutter, read / write
               highlighting of the register under the cursor, register hover with the live value

See docs/ASSEMBLY.md ("CPU view").
"""
