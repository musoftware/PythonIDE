"""Pure checks of radide/asm_intel/cpuview (no Qt window): source jump arrows, register reads / writes, procedure
ranges, inline values, conditional jumps, capstone decoding / re-synchronisation, stack annotations, the one-line
assemblers, the notes file and the 8086 backend on a headless Machine.

Run:  python samples/Tests/Assembly/SmartCpuView/test_cpu_analysis.py
"""
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

from radide.asm_intel.cpuview import analysis as A  # noqa: E402
from radide.asm_intel.cpuview.notes import CpuNotes  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"), flush=True)


nasm = (HERE / "NasmLoop" / "main.asm").read_text(encoding="utf-8")
lines = nasm.splitlines()


def ln(text, src=lines):
    return next(i for i, x in enumerate(src) if text in x)


# ---------------------------------------------------------------- source analysis
jumps = A.source_jumps(nasm, "nasm")
loop = [j for j in jumps if j.mnemonic == "jnz"]
check("jump arrow for the loop: jnz .next -> .next:", loop and loop[0].src == ln("jnz  .next") and
      loop[0].dst == ln(".next:") and loop[0].kind == "jcc", jumps)
check("call arrow: call show -> show:", any(j.kind == "call" and j.dst == ln("show:") for j in jumps), jumps)
check("call printf (extern) has no arrow", not any(j.label == "printf" for j in jumps))
lanes = A.arrow_lanes(jumps)
check("arrow lanes assigned", len(lanes) == len(jumps) and all(k >= 0 for _j, k in lanes))

emu = (HERE / "Emu8086Loop" / "main.asm").read_text(encoding="utf-8")
el = emu.splitlines()
ej = A.source_jumps(emu, "masm")
check("MASM loop arrow: loop add_next", any(j.kind == "loop" and j.src == ln("loop add_next", el) and
                                            j.dst == ln("add_next:", el) for j in ej), ej)
check("MASM call arrow: call show -> show proc", any(j.kind == "call" and j.dst == ln("show proc", el) for j in ej))

refs = A.register_refs(nasm, "nasm")
on = lambda text: [r for r in refs if r.line == ln(text)]  # noqa: E731
check("xor eax, eax = write only (zeroing idiom)", [r.kind for r in on("xor  eax, eax")] == ["w", "w"])
check("add rax, [rbx]: rax read+write, rbx read (address)",
      [(r.name, r.kind) for r in on("add  rax, [rbx]")] == [("rax", "rw"), ("rbx", "r")], on("add  rax, [rbx]"))
check("mov ecx, count: ecx written (family rcx)", [(r.family, r.kind) for r in on("mov  ecx, count")] == [("rcx", "w")])
check("dec rcx: read+write", [r.kind for r in on("dec  rcx")] == ["rw"])
procs = A.proc_ranges(nasm, "nasm")
main_p = A.proc_at(procs, ln("add  rax, [rbx]"))
check("procedure range of main ends before show:", main_p[0] == ln("main:") and main_p[1] < ln("show:"), procs)
fam_rax = A.refs_in_range(refs, "rax", *main_p)
check("rax references inside main only", fam_rax and all(main_p[0] <= r.line <= main_p[1] for r in fam_rax))
att = "movq %rax, %rbx\naddq $1, %rbx\n"
ar = A.register_refs(att, "gas")
check("AT&T: destination is the last operand", [(r.name, r.kind) for r in ar] ==
      [("rax", "r"), ("rbx", "w"), ("rbx", "rw")], ar)

fam = A.normalize_registers({"rax": 5, "rbx": 0x7, "eflags": 0x246, "rcx": 3})
iv = A.inline_values("    add  rax, [rbx]   ; total", "nasm", fam, 0x246)
check("inline value text: rax / rbx / flags", iv.startswith("rax=0x5  rbx=0x7") and "ZF=1" in iv, iv)
check("inline value of a sub-register (cl)", A.inline_values("mov cl, 1", "nasm", fam, None) == "cl=0x3")
check("inline value: label line without instruction is empty", A.inline_values(".next:", "nasm", fam, 0) == "")

# ---------------------------------------------------------------- conditional jumps
ZF = 1 << 6
check("jnz taken with ZF=0", A.jump_taken("jnz", 0) is True)
check("jnz not taken with ZF=1", A.jump_taken("jnz", ZF) is False)
check("jl taken when SF != OF", A.jump_taken("jl", 1 << 7) is True and A.jump_taken("jge", 1 << 7) is False)
check("loop with CX=1 is not taken, CX=2 taken", A.jump_taken("loop", 0, {"rcx": 1}, 16) is False and
      A.jump_taken("loop", 0, {"rcx": 2}, 16) is True)
check("jmp is not conditional", A.jump_taken("jmp", 0) is None)

# ---------------------------------------------------------------- capstone
code = bytes.fromhex("4801d8" "4883c308" "48ffc9" "75f4" "e800000000" "c3")
ins = A.decode(code, 0x140001000, 64)
check("decode x64: 6 instructions, kinds", [i.kind for i in ins] == ["", "", "", "jcc", "call", "ret"],
      [(hex(i.address), i.text, i.kind) for i in ins])
check("jcc target computed", ins[3].target == 0x140001000 + 0xA + 2 - 12, hex(ins[3].target or 0))
win = A.decode_window(b"\x90\x90" + code, 0x140000FFE, 0x140001003, 64)
check("decode_window lands on the pc", any(i.address == 0x140001003 for i in win))
m16 = A.decode(bytes.fromhex("e2fb"), 0x7105, 16, 0x7000)
check("16-bit loop target is linear", m16 and m16[0].kind == "loop" and m16[0].target == 0x7000 + 0x102, m16)
ea = A.effective_address(A.decode(bytes.fromhex("488b4308"), 0x1000, 64)[0], {"rbx": 0x2000}, 64)
check("effective address [rbx+8]", ea == 0x2008, ea)
check("return address detection (call rel32 before)", A.is_return_address(bytes.fromhex("9090e8 10000000")[-8:], 64))
check("not a return address", not A.is_return_address(b"\x00" * 8, 64))
check("string_at ASCII / UNICODE", A.string_at(b"Sum of the table\0")[0] == "ASCII" and
      A.string_at("Hello".encode("utf-16-le") + b"\0\0")[0] == "UNICODE")

# ---------------------------------------------------------------- assemblers
b, err = A.assemble_native("mov r9, 1", 0x140001000, 64)
check("NASM one-line assembler: mov r9, 1", b == bytes.fromhex("41b901000000") or (b and b[:3] == b"\x49\xc7\xc1"),
      f"{b!r} {err}")
b, err = A.assemble_native("mov r9, QWORD PTR [rip+0x10]", 0x1000, 64)
check("gdb syntax accepted (PTR removed)", b is not None, err)
b, err = A.assemble_native("mov rax, nosuchlabel", 0x1000, 64)
check("assembler error is reported", b is None and "nosuchlabel" in err, err)
b, err = A.assemble_8086("mov ax, 5", 0x700, 0x105)
check("8086 one-line assembler", b == b"\xb8\x05\x00", f"{b!r} {err}")

# ---------------------------------------------------------------- notes
p = Path(tempfile.mkdtemp()) / ".radide" / "cpu_notes.json"
n = CpuNotes(p, "a.exe")
n.set_comment(0x140001010, "loop body")
n.set_label(0x140001010, "my_loop")
n2 = CpuNotes(p, "a.exe")
check("notes persist (comment + label)", n2.comments.get(0x140001010) == "loop body" and
      n2.labels.get(0x140001010) == "my_loop" and n2.label_address("my_loop") == 0x140001010)
check("notes are per program", not CpuNotes(p, "b.exe").comments)

# ---------------------------------------------------------------- 8086 backend on a headless machine
from radide.emu8086.assembler import assemble  # noqa: E402
from radide.emu8086.machine import Machine  # noqa: E402
from radide.asm_intel.cpuview.backend import EmuBackend  # noqa: E402


class FakeSession:
    def __init__(self, prog):
        self.program = prog
        self.machine = Machine()
        self.machine.load(prog)
        self.folder = str(HERE / "Emu8086Loop")
        self.startup_file = "main.asm"
        self.paused = True


prog = assemble(emu, "main.asm")
fs = FakeSession(prog)
be = EmuBackend(None, fs)
snap = []
be.snapshot(snap.append)
check("8086 snapshot: pc / regs / 16 bits", snap and snap[0].bits == 16 and snap[0].pc == fs.machine.linear_ip())
rows = []
be.disasm(snap[0].pc, 30, rows.append)
rows = rows[0] if rows else []
check("8086 disassembly starts at the pc with 'mov ax, ...'", rows and rows[0].address == snap[0].pc and
      rows[0].mnemonic == "mov", [(hex(r.address), r.text) for r in rows[:4]])
lp = next((r for r in rows if r.kind == "loop"), None)
check("8086 loop target = label add_next", lp is not None and be.labels().get(lp.target) == "add_next",
      lp and hex(lp.target or 0))
got = []
be.eval("total", lambda a, e: got.append(a))
check("8086 Ctrl+G expression: variable name", got and got[0] == next(v.linear for v in prog.variables if
                                                                        v.name == "total"), got)
got = []
be.eval("ds:0", lambda a, e: got.append((a, e)))
be.eval("ip+2", lambda a, e: got.append((a, e)))
check("8086 expressions ip+2", got[-1][0] == snap[0].pc + 2, got)

ok = sum(1 for _n, c in RESULTS if c)
print(f"{ok}/{len(RESULTS)} passed")
sys.exit(0 if ok == len(RESULTS) else 1)
