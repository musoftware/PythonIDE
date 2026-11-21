# SmartStudentQA - the smart assembly editor seen by a beginner

Four programs written the way a beginner writes them, each with the usual mistakes. Open one in RAD IDE
(Arabic UI recommended) and watch the editor warn while you type, explain why in Arabic, and offer the fix.

| Project | Dialect | Mistakes (rule) |
|---|---|---|
| `NasmHello` | NASM, Windows x64 | `mov rcx, [msg]` instead of `lea` (ASM509), no shadow space / RSP not aligned before `call printf` (ASM501 / ASM502, quick fix "reserve shadow space"), `mov rdx, eax` (ASM101), `mov [a], 0` without a size (ASM102) |
| `NasmAverage` | NASM, Windows x64 | `div` without clearing EDX (ASM403), the loop counter in ECX after `call printf` (ASM402), RBX changed in main (ASM503 hint) |
| `MasmSum` | MASM, 32-bit | `push ebx` with no `pop` before `ret` (ASM304, quick fix "pop ebx"), `printf` arguments not removed (ASM507), `mov al, 300` (ASM104) |
| `Emu8086Grade` | emu8086 / DOS | DS not loaded (ASM601), string without `'$'` (ASM605), no DOS exit at the end of `main proc` (ASM602), `mov [bx], 0` without a size (ASM102), then BX never set (ASM401) |

`student_programs.py` lists the expected findings, the edits the student does by hand (the explanation says how)
and the output of the fixed program.

* `test_student.py` (headless): expected rule ids on the right lines with Arabic message / why / fix + link; the quick
  fixes applied one by one; no errors / warnings left; the fixed program is built with the real toolchain
  (NASM + gcc, ml + link) and run, or run in the 8086 emulator; "Check by running" finds the runtime problems in the
  half-fixed program and is clean on the fixed one; Explain this line and What-if.
* `test_student_ide.py` (real IDE, qh.py harness, QSettings `RADIDE-TEST`, Arabic + dark by default, `QA_LANG=` /
  `QA_THEME=` for English / light, `QA_REAL=1` to render Monaco in the screenshots): typing line by line shows the
  squiggle before the program is finished, hover, Ctrl+., Problems Explained, Check by running, Ctrl+F5 output,
  Explain this line, What-if, F5 with the CPU view ("jump is taken", inline values, arrows) and the 8086 emulator.
  Screenshots: `%TEMP%/radide-qa/shots/student_*.png` (widget.grab only).

These programs are wrong on purpose: `SmartLint/test_lint_corpus.py` skips this folder in its no-false-positive scan.
