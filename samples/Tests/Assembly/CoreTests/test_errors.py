"""Error parsing: break each template on a known line, build, check the Error List rows (file + line)."""
import shutil
import sys
import tempfile
from pathlib import Path

WORK = Path(tempfile.gettempdir()) / "radide-asm-tests"     # projects are created here

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))      # the RAD IDE folder
from radide.asm import errors
from radide.asm.build import Builder
from radide.languages import get_plugin

root = WORK / "errprojects"
CASES = [  # template, file, (after line containing, inserted bad line), expected kind
    ("nasm_console_x64", "main.asm", "call puts", "    movzx eax, 12345678h, 3", "asm"),
    ("nasm_console_x64", "main.asm", "call puts", "    call no_such_function", "link"),
    ("nasm_console_x86", "main.asm", "call _puts", "    call _no_such_function", "link"),
    ("gas_console_x64", "main.s", "call    puts", "        movq    %rax, %rbx, %rcx", "asm"),
    ("gas_console_x64", "main.s", "call    puts", "        call    no_such_function", "link"),
    ("fasm_console_x64", "main.asm", "cinvoke puts, hello", "    mov rax, rbx, rcx", "asm"),
    ("masm_console_x64", "main.asm", "call puts", "    mov rax, rbx, rcx", "asm"),
    ("masm_console_x64", "main.asm", "call puts", "    call no_such_function", "link"),
    ("nasm_forms", "Form1.asm", "inc rax", "    rad_set noSuchControl, \"Text\", \"x\"", "asm"),
]
ok_all = True
for tid, fname, after, bad, kind in CASES:
    folder = root / f"{tid}_{kind}"
    shutil.rmtree(folder, ignore_errors=True)
    from radide.asm.templates import BY_ID
    get_plugin(BY_ID[tid].plugin).create_new_project(folder, "Err", tid)
    p = folder / fname
    lines = p.read_text(encoding="utf-8").splitlines()
    i = next(n for n, l in enumerate(lines) if after in l) + 1
    if kind == "link" and tid.startswith("masm"):
        # MASM needs the declaration at the top
        lines.insert(0, "extern no_such_function : proc")
        i += 1
    if kind == "link" and tid.startswith("nasm") and "x86" in tid:
        lines.insert(0, "extern _no_such_function")
        i += 1
    elif kind == "link" and tid.startswith("nasm"):
        lines.insert(0, "extern no_such_function")
        i += 1
    lines.insert(i, bad)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    expect_line = i + 1
    logs = []
    b = Builder(folder, log=logs.append)
    built = b.build()
    from radide.asm.build import read_diagnostics
    diags = [errors.AsmDiag(**x) for x in read_diagnostics(folder)["diags"]]
    hit = [d for d in diags if d.severity == "Error" and Path(d.file).name == fname and d.line == expect_line]
    chk = b.check() if kind == "asm" else []
    chk_hit = [d for d in chk if d.line == expect_line] if kind == "asm" else [True]
    ok = (not built) and bool(hit) and bool(chk_hit)
    ok_all &= ok
    print(f"{'OK  ' if ok else 'FAIL'} {tid:22} {kind:4} line {expect_line}: "
          + "; ".join(f"{d.file}:{d.line} {d.message[:70]}" for d in diags[:2])
          + (f"   [check: {len(chk)} rows]" if kind == "asm" else ""))
    if not ok:
        print("\n".join(logs[-12:]))

# parser unit cases for the formats not produced above
sample = """main.asm(12) : error A2008:syntax error : eax
main.obj : error LNK2019: unresolved external symbol foo referenced in function main
main.asm [7]:
        mov eax,
processed: mov eax,
error: invalid operand.
D:/p/main.asm:13:(.text+0x11): undefined reference to `foo'
main.s:4: Warning: missing operand; zero assumed
radgui.c:10:5: error: expected ';' before '}' token
"""
d = errors.parse(sample)
want = {("main.asm", 12), ("main.asm", 0), ("main.asm", 7), ("D:/p/main.asm", 13), ("main.s", 4), ("radgui.c", 10)}
got = {(x.file, x.line) for x in d}
print("parser formats:", "OK" if want <= got else f"FAIL {got}")
ok_all &= want <= got
print("RESULT", "OK" if ok_all else "FAIL")
