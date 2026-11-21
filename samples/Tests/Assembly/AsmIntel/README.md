# AsmIntel - assembly editor intelligence test files

Curated test sources for the assembly IntelliSense of RAD IDE (`radide/asm_intel`, `radide/features/asm_ide.py`,
documented in `docs/ASSEMBLY.md`, section "Editor intelligence"). They are loose files (no project.radproj), so
they also exercise the dialect detection from the file extension and the text.

| Folder | File | Dialect | What it exercises |
|---|---|---|---|
| `nasm/` | `main.asm` + `mathlib.inc` | NASM, Win64 | `%include`, macros from the include file, `extern` Win32 APIs, `equ` constants, `struc`, local labels (`.loop`), Win64 calls with shadow space |
| `masm/` | `hello32.asm` | MASM, 32-bit | `PROC` / `ENDP` with parameters, `PROTO`, `INVOKE`, `LOCAL`, `STRUCT`, `.IF` |
| `fasm/` | `hello.fasm` | FASM, 32-bit | `format` / `entry` / `section '...'`, `import` / `library`, `proc` / `endp`, `macro { }` |
| `gas/` | `hello_linux.s` | GNU as AT&T, Linux x86-64 | `.macro` with `\arg`, `.equ`, `%` registers, `$` immediates, `.L` local labels |
| `gas/` | `hello_win.S` | GNU as Intel, Win64 (MinGW) | `.intel_syntax noprefix`, `#define`, `printf` from the CRT |

## Tests

```
python samples/Tests/Assembly/AsmIntel/tests/test_asm_intel.py       # unit tests: tables, parser, completions,
                                                                     # hover, signature help, F12, references,
                                                                     # outline, folding, Monaco grammar, overlay
python samples/Tests/Assembly/AsmIntel/tests/test_core_templates.py  # every Assembly New Project template
python samples/Tests/Assembly/AsmIntel/tests/test_ide_asm.py         # the real IDE (offscreen, RADIDE-TEST settings):
                                                                     # Monaco grammar + colours, completions, hover,
                                                                     # signature help, outline, Ctrl+click, overlay
```

Screenshots of the IDE test (editor widget only) go to `%TEMP%\radide-asm-intel`.
