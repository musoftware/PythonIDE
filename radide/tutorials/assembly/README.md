# Assembly course (assembly): block format and tests

16 Arabic lessons (`NN-slug.md`, listed in `course.json`) for x86-64 Windows assembly with NASM, plus one lesson
on the 8086 teaching emulator. The runner code is `radide/tutorials/asm_support.py`.

| Info string | Meaning | "جرّبه" / "تحقق" |
|---|---|---|
| ```` ```asm run ```` | NASM x64 console program (`global main`, C runtime with `extern`) | asm-nasm project (template `nasm_console_x64`, our `main.asm`); checked with `nasm -f win64` + gcc (MinGW-w64), stdin from the following ```` ```text input ```` |
| ```` ```asm form run ```` | `Form1.asm` of a GUI Bridge form (`%include "radgui.inc"`, `handler btnX_Click` ... `endhandler`) | asm-nasm Windows Forms project (template `nasm_forms`); Form1 gets the controls the code names (`rad_* lblX,` / `handler btnX_...`), laid out in a column; checked by building it with `python -m radide.asm.build` |
| ```` ```asm16 run ```` | 8086 / DOS program (MASM / TASM / emu8086 syntax, `org 100h`, `int 21h`, `include 'emu8086.inc'`) | checked with the headless emulator `radide.emu8086.run_source(text, keys=stdin)`; "جرّبه" writes `main.asm` (an 8086 emulator project when that plugin is installed, else the folder opens in place and the 8086 target runs in the emulator) |
| ```` ```asm exercise ```` / ```` ```asm solution ```` (also `form`, `asm16`) | starter code / hidden solution | exercises must assemble; checked against the solution's output |
| ```` ```asm ```` | snippet, not run | display only |

`; #file: name.asm` lines split a block into several files (lesson 15: `main.asm` + `stats.asm`).

Hidden `<!-- test: {...} -->` before a block:

* `"norun": true`: assemble and link only (MessageBoxA).
* `"form"`: `{"Text": ..., "controls": {"btnAdd": {"Text": "A + B"}}}` - captions of the generated form.

## Testing

    python radide/tutorials/assembly/tools/check_lessons.py          # all lessons
    python radide/tutorials/assembly/tools/check_lessons.py 09 -v    # one lesson, list every block

The checker runs every `run` / `solution` block (NASM + gcc, or the 8086 emulator), assembles every exercise,
validates the quiz JSON and creates the "جرّبه" project of every block with `make_project()`. Blocks whose tool
is missing are reported (8086 blocks as UNCHECKED when `radide/emu8086` is not installed).

## Facts the lessons rely on

- NASM 3.x (downloaded by the IDE to `%LOCALAPPDATA%\RADIDE\tools\nasm`) + the MinGW-w64 UCRT gcc of the C support.
- `default rel` is required: without it the link fails with `relocation truncated to fit: IMAGE_REL_AMD64_ADDR32`.
  `[label + reg*4]` cannot be RIP-relative and fails the same way: load the address with `lea` first.
- NASM 3 accepts `mov [mem], imm` without a size and stores a BYTE (older versions: "operation size not specified").
- `printf` output is buffered: programs return from `main` (ExitProcess right after printf may lose output).
- The 8086 emulator's `SCAN_NUM` echoes the Enter key as CR LF; `int 21h` / `ah = 01h` echoes the key.
