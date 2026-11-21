"""Assembly language support (docs/ASSEMBLY.md).

    toolchain   find / download the assemblers and linkers (NASM, FASM, GNU as, MASM, gcc/ld, GoLink)
    build       assemble + link a project (``python -m radide.asm.build <folder>``), used by Build / Run
    errors      parse nasm / fasm / as / ml / ld / gcc messages into Error List rows
    templates   source of the New Project templates
    formgen     GUI Bridge: the include file with the form's objects and the generated event dispatch

The language plugins are radide/languages/asm_nasm.py, asm_fasm.py, asm_masm.py and asm_gas.py.
"""
