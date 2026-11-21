# SmartLint - the assembly editor that explains your mistakes

Test material of the static assembly analyzer `radide/asm_lint` and its editor integration
`radide/features/asm_smart_lint.py` (overview: [docs/ASSEMBLY.md](../../../../docs/ASSEMBLY.md), "Smart editor checks").

| Item | What it is |
|---|---|
| [NasmMistakes](NasmMistakes/) | an x64 NASM project full of beginner mistakes (sizes, memory size, DIV without EDX, RCX after a call, JZ after MOV, unreachable code). Open it: every `MISTAKE` line is underlined, hover it for the explanation, Ctrl+. for the quick fix. |
| [Emu8086Mistakes](Emu8086Mistakes/) | an 8086 (emulator) project: DS not loaded, a string without `$`, CX changed by a procedure inside LOOP, `[ax]`, no DOS exit, `push 7` on a real 8086. |
| `corpus.py` | 88 bad snippets (NASM, MASM, FASM, GNU as AT&T / Intel, emu8086, x64 Windows, x86, System V, DOS) with the rule ids each must produce, and 14 correct snippets that must stay clean. |
| `test_lint_corpus.py` | headless (66 checks): the corpus, every rule's English / Arabic texts, 19 quick fixes applied and re-checked, no errors / warnings on the 48 sample sources, the project templates and the 89 runnable course blocks, assembler message translation, configuration + suppression comments, a 5 515-line file re-analysed after an edit in < 200 ms. |
| `test_lint_ide.py` | the real IDE (qh.py, QSettings `RADIDE-TEST`, in Arabic then English, 38 checks): squiggles + gutter icons, the hover explanation (also the Monaco hover widget), Ctrl+. (light bulb menu + applying a fix), the Problems Explained panel (Fix, Learn more, lesson), Error List rows and the merge with an assembler message, the emu8086 project. `QA_REAL=1` also captures the editor pictures. |

Run:

    python samples/Tests/Assembly/SmartLint/test_lint_corpus.py
    python samples/Tests/Assembly/SmartLint/test_lint_ide.py
