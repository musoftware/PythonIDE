# SmartCpuView - the OllyDbg-style CPU view and the live assembly editor

| Item | What it is |
|---|---|
| `NasmLoop/` | x64 Windows console program (NASM): a loop over a table, a call, a string - F5 shows the CPU view at the first stop |
| `Emu8086Loop/` | the same idea for RAD IDE's 8086 emulator (`.model small`, LOOP, CALL, INT 21h) |
| `test_cpu_analysis.py` | 40 pure checks: source jump arrows, register reads / writes, procedure ranges, inline values, jcc / LOOP evaluation, capstone decoding, stack annotations, the NASM / 8086 one-line assemblers, notes file, 8086 backend |
| `test_cpu_view.py` | 55 checks in the IDE (qh.py, QSettings `RADIDE-TEST`): panes filled and in sync after F7 / F8, F2 + F9, F4, Ctrl+F9, Ctrl+G, Assemble (`mov r9, 1` really runs), binary edit, comment + label persistence, searches, stack return address, flag click, editor arrows / register highlighting / inline values / hover data; Arabic + dark screenshots |

Run:

    python samples/Tests/Assembly/SmartCpuView/test_cpu_analysis.py
    python samples/Tests/Assembly/SmartCpuView/test_cpu_view.py          # QA_LANG=en QA_THEME= for English / light
    set QA_REAL=1 & python samples/Tests/Assembly/SmartCpuView/test_cpu_view.py   # also renders the Monaco editor

Part 1 of `test_cpu_view.py` needs the WinLibs toolchain (nasm, gcc, gdb >= 14 in
`%LOCALAPPDATA%\RADIDE\toolchains\mingw64`); it is skipped without it. Screenshots go to `%TEMP%\radide-qa\shots`.
See docs/ASSEMBLY.md, "CPU view (OllyDbg style) and the live assembly editor".
