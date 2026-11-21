"""The beginner programs of the student QA: expected findings, the edits the student does by hand after the quick
fixes, the expected output, and helpers shared by test_student.py and test_student_ide.py."""
from __future__ import annotations

from pathlib import Path

from radide.asm_lint import apply_edits, lint

HERE = Path(__file__).resolve().parent

def lint_at(text, folder):
    return lint(text, str(folder / "main.asm"))


def problems(issues):
    return [i for i in issues if i.severity in ("error", "warning")]


# program -> (expected (rule, 1-based line) pairs, manual edits after the quick fixes, expected program output)
PROGRAMS = {
    "NasmHello": dict(
        expect=[("ASM509", 14), ("ASM501", 15), ("ASM502", 15), ("ASM101", 18), ("ASM102", 21)],
        manual=[],
        output=["My name is Ahmed", "a + b = 12"],
        sim_half={"sim.bad_pointer_arg", "sim.misaligned_call", "sim.no_shadow_space"},
    ),
    "NasmAverage": dict(
        expect=[("ASM503", 18), ("ASM403", 24), ("ASM402", 33)],
        # ASM402 has no automatic fix: as the explanation says, keep the counter in a register printf keeps
        # (RBX, saved with push / pop), and do not use RBX for the array (ASM503) - use R10 instead.
        manual=[("    push rbp\n    mov rbp, rsp\n    sub rsp, 32\n",
                 "    push rbp\n    mov rbp, rsp\n    push rbx\n    sub rsp, 40\n"),
                ("    lea rbx, [nums]\n.sum:\n    add eax, [rbx]\n    add rbx, 4\n",
                 "    lea r10, [nums]\n.sum:\n    add eax, [r10]\n    add r10, 4\n"),
                ("    mov ecx, 3\n.again:\n    mov edx, ecx\n", "    mov ebx, 3\n.again:\n    mov edx, ebx\n"),
                ("    call printf\n    dec ecx\n", "    call printf\n    dec ebx\n"),
                ("    mov rsp, rbp\n    pop rbp\n", "    add rsp, 40\n    pop rbx\n    pop rbp\n")],
        output=["avg = 30", "i = 3", "i = 2", "i = 1"],
        sim_half=None,
    ),
    "MasmSum": dict(
        expect=[("ASM304", 20), ("ASM507", 28), ("ASM104", 29)],
        manual=[("    mov al, 300\n", "")],          # ASM104: 300 does not fit in AL - the line was not needed
        output=["sum = 55"],
        sim_half=None,                                  # MASM is not emulated (documented)
    ),
    "Emu8086Grade": dict(
        expect=[("ASM601", 12), ("ASM605", 24), ("ASM602", 26), ("ASM102", 26)],
        # after "word ptr" the analyzer says BX never got a value (ASM401): the line was a mistake, delete it
        manual=[("    mov word ptr [bx], 0\n", "")],
        output=["Enter grade", "Pass"],
        sim_half=None,
    ),
}


def apply_quick_fixes(text, folder, log):
    """Apply the first quick fix of the first fixable error / warning until none is left (max 20 rounds)."""
    for _ in range(20):
        fixable = [i for i in problems(lint_at(text, folder)) if i.fixes]
        if not fixable:
            return text
        it = fixable[0]
        log.append(f"{it.rule} L{it.line + 1}: {it.fixes[0].title('ar')}")
        text = apply_edits(text, it.fixes[0].edits)
    return text


def apply_manual(text, manual):
    for old, new in manual:
        if old not in text:
            return None, old
        text = text.replace(old, new, 1)
    return text, ""


def fixed_text(name: str, log=None) -> str:
    """The program after the quick fixes and the hand edits."""
    folder = HERE / name
    text = apply_quick_fixes((folder / "main.asm").read_text(encoding="utf-8"), folder, [] if log is None else log)
    return apply_manual(text, PROGRAMS[name]["manual"])[0]
