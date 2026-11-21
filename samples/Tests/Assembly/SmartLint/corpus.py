"""Good and bad assembly snippets for radide/asm_lint with the rule ids each one must produce.

Every BAD entry: (name, options, code, expected rule ids). Options: dialect / bits / abi / project_lang passed to
radide.asm_lint.lint. GOOD entries must produce no error or warning (hints are allowed).
"""

W64 = {"dialect": "nasm"}
X86 = {"dialect": "nasm", "bits": 32, "abi": "x86"}
SYSV = {"dialect": "nasm", "bits": 64, "abi": "sysv"}
EMU = {"dialect": "masm", "bits": 16, "abi": "dos16", "project_lang": "emu8086"}
MASM32 = {"dialect": "masm", "bits": 32, "abi": "x86"}
FASM64 = {"dialect": "fasm"}
GAS = {"dialect": "gas"}


def nasm64(body: str, extra_data: str = "", head: str = "default rel\n") -> str:
    return (head + "global main\nextern printf, puts, MessageBoxA, ExitProcess, Sleep\n"
            "section .data\n    msg db 'hi', 0\n    val dd 5\n    arr dw 1, 2, 3\n" + extra_data +
            "section .text\nmain:\n    sub rsp, 40\n" + body + "\n    xor eax, eax\n    add rsp, 40\n    ret\n")


def nasm32(body: str) -> str:
    return ("global _main\nextern _printf, _MessageBoxA@16, _Sleep@4\nsection .data\n    msg db 'hi', 0\n"
            "section .text\n_main:\n" + body + "\n    xor eax, eax\n    ret\n")


def com(body: str, data: str = "msg db 'hello$'") -> str:
    return "org 100h\n\nstart:\n" + body + "\n" + data + "\n"


def sysv(body: str) -> str:
    return ("default rel\nglobal main\nextern printf\nsection .data\n    msg db 'hi %d', 10, 0\nsection .text\n"
            "main:\n    push rbp\n" + body + "\n    pop rbp\n    xor eax, eax\n    ret\n")


BAD = [
    # ------------------------------------------------------------------ operands (NASM, x64 Windows)
    ("size mismatch", W64, nasm64("    mov eax, bl"), {"ASM101"}),
    ("size mismatch alu", W64, nasm64("    add ecx, dx"), {"ASM101"}),
    ("ambiguous size", W64, nasm64("    mov [val], 1"), {"ASM102"}),
    ("ambiguous inc", W64, nasm64("    inc [val]"), {"ASM102"}),
    ("memory to memory", W64, nasm64("    mov [val], [msg]"), {"ASM103"}),
    ("immediate too big", W64, nasm64("    mov al, 300"), {"ASM104"}),
    ("imm64 in add", W64, nasm64("    add rax, 0x1FFFFFFFF"), {"ASM104"}),
    ("bad scale", W64, nasm64("    lea rbx, [arr]\n    mov eax, [rbx+rax*3]"), {"ASM105"}),
    ("esp index", W64, nasm64("    mov eax, [rax+rsp*2]"), {"ASM105"}),
    ("mixed address", W64, nasm64("    lea rax, [arr]\n    mov eax, [rax+ebx]"), {"ASM107"}),
    ("64-bit reg in 32-bit", X86, nasm32("    mov rax, 1"), {"ASM108"}),
    ("immediate destination", W64, nasm64("    mov 5, eax"), {"ASM109"}),
    ("movzx same size", W64, nasm64("    movzx eax, ebx"), {"ASM111"}),
    ("movsx 32 to 64", W64, nasm64("    movsx rax, ecx"), {"ASM111"}),
    ("lea without brackets", W64, nasm64("    lea rcx, msg\n    call puts"), {"ASM112"}),
    ("high byte with rex", W64, nasm64("    mov ah, sil"), {"ASM113"}),
    ("push 32-bit in 64", W64, nasm64("    mov eax, 1\n    push rax\n    push eax\n    pop rax\n    pop rax"),
     {"ASM114"}),
    ("push byte", W64, nasm64("    mov al, 1\n    push al"), {"ASM114"}),
    ("pusha in 64", W64, nasm64("    pusha"), {"ASM115"}),
    ("missing operand", W64, nasm64("    mov eax"), {"ASM116"}),
    ("extra operand", W64, nasm64("    inc eax, 1"), {"ASM116"}),
    ("div immediate", W64, nasm64("    mov eax, 7\n    xor edx, edx\n    div 10"), {"ASM117"}),
    ("32-bit address in 64", W64, nasm64("    lea rbx, [arr]\n    mov eax, [ebx]"), {"ASM119"}),
    ("address in 32-bit reg", W64, nasm64("    mov ecx, msg\n    call puts"), {"ASM120"}),
    ("segment override in 64", W64, nasm64("    lea rbx, [arr]\n    mov eax, [es:rbx]"), {"ASM121"}),
    ("shift too far", W64, nasm64("    mov eax, 1\n    shl eax, 40"), {"ASM123"}),
    ("useless mov", W64, nasm64("    mov rbx, rbx"), {"ASM124"}),
    ("dos int in windows", W64, nasm64("    mov ah, 9\n    int 21h"), {"ASM125"}),
    # ------------------------------------------------------------------ symbols
    ("undefined label", W64, nasm64("    mov ecx, 3\nagain:\n    dec ecx\n    jnz agian"), {"ASM201"}),
    ("missing extern", W64, nasm64("    lea rcx, [msg]\n    call strlen"), {"ASM202"}),
    ("duplicate label", W64, nasm64("    jmp x1\nx1:\n    nop\nx1:\n    nop"), {"ASM203"}),
    ("jump to data", W64, nasm64("    jmp msg"), {"ASM204"}),
    ("write to code", W64, nasm64("    mov byte [code_byte], 1\n    jmp go_on\ncode_byte db 0\ngo_on:"), {"ASM205"}),
    ("write to rodata", W64, nasm64("    mov dword [table], 1", "section .rodata\n    table dd 1, 2\n"),
     {"ASM205"}),
    ("no default rel", W64, nasm64("    mov eax, [val]", head=""), {"ASM206"}),
    ("executes data", EMU, com("    mov ah, 2\n    mov dl, 'A'\n    int 21h", "letter db 'B'"), {"ASM207"}),
    # ------------------------------------------------------------------ control flow
    ("unreachable", W64, nasm64("    jmp .done\n    mov eax, 1\n.done:"), {"ASM301"}),
    ("missing ret", W64, nasm64("    call helper") + "helper:\n    mov eax, 1\n", {"ASM302"}),
    ("falls into next", W64, nasm64("    call f1\n    call f2") + "f1:\n    inc rbx\nf2:\n    xor eax, eax\n"
                                                                      "    ret\n", {"ASM303"}),
    ("stack not balanced", W64, nasm64("    call f") + "f:\n    push rbx\n    mov ebx, 1\n    ret\n",
     {"ASM304"}),
    ("stack differs", W64, nasm64("    call f") + "f:\n    test ecx, ecx\n    jz .skip\n    push rbx\n.skip:\n"
                                                 "    ret\n", {"ASM305"}),
    ("pop without push", W64, nasm64("    call f") + "f:\n    pop rax\n    ret\n", {"ASM306"}),
    ("jz after mov", W64, nasm64("    mov eax, [val]\n    jz .zero\n.zero:"), {"ASM307"}),
    ("jz after mul", W64, nasm64("    mov eax, 3\n    mov ecx, 4\n    mul ecx\n    jz .z\n.z:"), {"ASM308"}),
    ("signed jump on addresses", W64, nasm64("    lea rsi, [msg]\n    lea rdi, [msg+2]\n    cmp rsi, rdi\n"
                                             "    jl .x\n.x:"), {"ASM309"}),
    ("jc after inc", W64, nasm64("    mov ecx, 1\n    inc ecx\n    jc .x\n.x:"), {"ASM310"}),
    # ------------------------------------------------------------------ data flow
    ("used before set", W64, nasm64("    add eax, ebx"), {"ASM401"}),
    ("clobbered by call", W64, nasm64("    mov ecx, 5\n    lea rcx, [msg]\n    call puts\n    mov eax, ecx"),
     {"ASM402"}),
    ("loop counter clobbered by helper", EMU,
     com("    mov cx, 3\nl1:\n    call show\n    loop l1\n    mov ah, 4Ch\n    int 21h\nshow:\n    mov ah, 2\n"
         "    mov dl, '*'\n    mov cx, 1\n    int 21h\n    ret"), {"ASM402"}),
    ("div without edx", W64, nasm64("    mov eax, 100\n    mov ecx, 3\n    div ecx"), {"ASM403"}),
    ("div by zero", W64, nasm64("    mov eax, 1\n    xor edx, edx\n    xor ecx, ecx\n    div ecx"), {"ASM404"}),
    ("divide overflow", W64, nasm64("    mov edx, 7\n    mov eax, 1\n    mov ecx, 2\n    div ecx"), {"ASM409"}),
    ("loop counter never set", EMU, com("l1:\n    loop l1\n    ret"), {"ASM405"}),
    ("std left set", W64, nasm64("    lea rsi, [msg]\n    lea rdi, [arr]\n    std\n    mov ecx, 2\n    rep movsb"),
     {"ASM406"}),
    ("idiv after xor", W64, nasm64("    mov eax, -7\n    xor edx, edx\n    mov ecx, 2\n    idiv ecx"),
     {"ASM408"}),
    # ------------------------------------------------------------------ calling conventions
    ("no shadow space", W64, nasm64("    call f") + "f:\n    lea rcx, [msg]\n    call puts\n    ret\n",
     {"ASM501", "ASM502"}),
    ("misaligned", W64, "default rel\nglobal main\nextern puts\nsection .data\n    msg db 'x', 0\nsection .text\n"
                        "main:\n    sub rsp, 32\n    lea rcx, [msg]\n    call puts\n    add rsp, 32\n    ret\n",
     {"ASM502"}),
    ("callee saved", W64, "default rel\nglobal helper\nsection .text\nhelper:\n    mov rbx, rcx\n    lea rax, [rbx+1]\n"
                          "    ret\n", {"ASM503"}),
    ("api argument missing", W64, nasm64("    xor ecx, ecx\n    lea rdx, [msg]\n    lea r8, [msg]\n"
                                         "    call MessageBoxA"), {"ASM504"}),
    ("x86 push count", X86, nasm32("    push 0\n    push msg\n    push msg\n    call _MessageBoxA@16"), {"ASM505"}),
    ("stdcall double cleanup", X86, nasm32("    push 100\n    call _Sleep@4\n    add esp, 4"), {"ASM506"}),
    ("cdecl not cleaned", X86, "global _f\nextern _printf\nsection .data\n    msg db 'x', 0\nsection .text\n_f:\n"
                               "    push msg\n    call _printf\n    ret\n", {"ASM507"}),
    ("sysv variadic al", SYSV, sysv("    lea rdi, [msg]\n    mov esi, 5\n    call printf"), {"ASM508"}),
    ("value instead of address", W64, nasm64("    mov rcx, [msg]\n    call puts"), {"ASM509"}),
    # ------------------------------------------------------------------ DOS / 8086 (emu8086 style)
    ("16-bit bad address", EMU, com("    mov bx, 0\n    mov al, [ax]\n    ret"), {"ASM106"}),
    ("32-bit reg on 8086", EMU, com("    mov eax, 1\n    ret"), {"ASM108"}),
    ("immediate into ds", EMU, com("    mov ds, 1234h\n    ret"), {"ASM110"}),
    ("segment to segment", EMU, com("    mov es, ds\n    ret"), {"ASM110"}),
    ("push immediate 8086", EMU, com("    push 5\n    pop ax\n    ret"), {"ASM118"}),
    ("shift by 3 on 8086", EMU, com("    mov ax, 1\n    shl ax, 3\n    ret"), {"ASM118"}),
    ("bp uses ss", EMU, ".model small\n.data\narr db 1, 2, 3\n.code\nstart:\n    mov ax, @data\n    mov ds, ax\n"
                        "    mov bp, 1\n    mov al, arr[bp]\n    mov ah, 4Ch\n    int 21h\nend start\n", {"ASM122"}),
    ("ds not initialised", EMU, ".model small\n.stack 100h\n.data\nmsg db 'hi$'\n.code\nstart:\n    mov ah, 9\n"
                                "    mov dx, offset msg\n    int 21h\n    mov ah, 4Ch\n    int 21h\nend start\n",
     {"ASM601"}),
    ("missing dos exit", EMU, "org 100h\n    mov ah, 2\n    mov dl, 'A'\n    int 21h\n", {"ASM602"}),
    ("ah not set", EMU, com("    mov dx, offset msg\n    int 21h\n    ret"), {"ASM603"}),
    ("unknown dos function", EMU, com("    mov ah, 99h\n    int 21h\n    ret"), {"ASM604"}),
    ("missing dollar", EMU, com("    mov ah, 9\n    mov dx, offset text\n    int 21h\n    ret", "text db 'hello'"),
     {"ASM605"}),
    ("dx not set", EMU, com("    mov ah, 9\n    int 21h\n    ret"), {"ASM606"}),
    ("string op without cld", EMU, com("    call copy\n    ret\ncopy:\n    mov cx, 3\n    rep movsb\n    ret"),
     {"ASM407"}),
    # ------------------------------------------------------------------ other dialects
    ("gas att suffix", GAS, "    .text\n    .globl main\nmain:\n    subq $40, %rsp\n    movl %rax, %rbx\n"
                            "    addq $40, %rsp\n    ret\n", {"ASM101"}),
    ("gas att no suffix", GAS, "    .text\n    .globl main\nmain:\n    subq $40, %rsp\n    leaq buf(%rip), %rbx\n"
                               "    mov $1, (%rbx)\n    addq $40, %rsp\n    ret\n    .data\nbuf: .long 0\n",
     {"ASM102"}),
    ("gas att mem mem", GAS, "    .text\n    .globl main\nmain:\n    movq x(%rip), y(%rip)\n    ret\n    .data\n"
                             "x: .quad 1\ny: .quad 2\n", {"ASM103"}),
    ("gas att imm", GAS, "    .text\n    .globl main\nmain:\n    movb $300, %al\n    ret\n", {"ASM104"}),
    ("gas intel size", GAS, "    .intel_syntax noprefix\n    .text\n    .globl main\nmain:\n    mov eax, bl\n"
                            "    ret\n", {"ASM101"}),
    ("gas intel ambiguous", GAS, "    .intel_syntax noprefix\n    .text\n    .globl main\nmain:\n"
                                 "    lea rbx, [rip+buf]\n    mov [rbx], 1\n    ret\n    .data\nbuf: .long 0\n",
     {"ASM102"}),
    ("masm typed variable", MASM32, ".386\n.model flat, stdcall\n.data\nb1 BYTE 1\n.code\nmain PROC\n"
                                    "    mov eax, b1\n    ret\nmain ENDP\nEND main\n", {"ASM101"}),
    ("masm ambiguous", MASM32, ".386\n.model flat, stdcall\n.code\nmain PROC\n    mov ebx, 0\n    mov [ebx], 1\n"
                               "    ret\nmain ENDP\nEND main\n", {"ASM102"}),
    ("fasm ambiguous register address", FASM64, "format PE64 console\nentry start\nsection '.text' code readable "
                                                "executable\nstart:\n    sub rsp, 40\n    xor ebx, ebx\n"
                                                "    mov [rbx], 1\n    add rsp, 40\n    ret\n", {"ASM102"}),
    ("fasm size mismatch", FASM64, "format PE64 console\nentry start\nsection '.data' data readable writeable\n"
                                   "    x db 1\nsection '.text' code readable executable\nstart:\n"
                                   "    mov eax, [x]\n    ret\n", {"ASM101"}),
]

GOOD = [
    ("win64 function", W64, "default rel\nglobal main\nextern printf\nsection .data\n    fmt db '%d', 10, 0\n"
                            "section .text\nmain:\n    push rbx\n    sub rsp, 32\n    mov ebx, 3\n.next:\n"
                            "    lea rcx, [fmt]\n    mov edx, ebx\n    call printf\n    dec ebx\n    jnz .next\n"
                            "    add rsp, 32\n    pop rbx\n    xor eax, eax\n    ret\n"),
    ("push digits / pop digits", EMU, com("    mov ax, 1234\n    call print_ax\n    mov ah, 4Ch\n    int 21h\n"
                                          "print_ax:\n    mov bx, 10\n    xor cx, cx\np_div:\n    xor dx, dx\n"
                                          "    div bx\n    push dx\n    inc cx\n    test ax, ax\n    jnz p_div\n"
                                          "p_out:\n    pop dx\n    add dl, '0'\n    mov ah, 2\n    int 21h\n"
                                          "    loop p_out\n    ret", "")),
    ("dos exe", EMU, ".model small\n.stack 100h\n.data\nmsg db 'hi$'\n.code\nstart:\n    mov ax, @data\n"
                     "    mov ds, ax\n    mov ah, 9\n    mov dx, offset msg\n    int 21h\n    mov ax, 4C00h\n"
                     "    int 21h\nend start\n"),
    ("x86 stdcall and cdecl", X86, "global _main\nextern _printf, _Sleep@4\nsection .data\n    msg db 'x', 0\n"
                                   "section .text\n_main:\n    push 10\n    call _Sleep@4\n    push msg\n"
                                   "    call _printf\n    add esp, 4\n    xor eax, eax\n    ret\n"),
    ("sysv printf", SYSV, sysv("    lea rdi, [msg]\n    mov esi, 5\n    xor eax, eax\n    call printf")),
    ("flags kept across mov", W64, nasm64("    mov eax, [val]\n    cmp eax, 5\n    mov ecx, 1\n    jz .eq\n"
                                          "    mov ecx, 2\n.eq:")),
    ("zero extension idiom", W64, nasm64("    mov eax, [val]\n    mov eax, eax")),
    ("shared tail", EMU, com("    call draw\n    ret\ndraw:\n    mov al, '@'\nput:\n    mov ah, 0Eh\n    int 10h\n"
                             "    ret", "")),
    ("cdq idiv", W64, nasm64("    mov eax, -7\n    cdq\n    mov ecx, 2\n    idiv ecx")),
    ("loop with counter", EMU, com("    mov cx, 3\nl1:\n    mov ah, 2\n    mov dl, '*'\n    int 21h\n    loop l1\n"
                                   "    ret", "")),
    ("masm proc locals", MASM32, ".386\n.model flat, stdcall\n.code\ncount PROC uses ebx n:DWORD\n"
                                 "    LOCAL tmp:DWORD\n    mov tmp, 0\n    mov ebx, n\n    inc tmp\n    mov eax, tmp\n"
                                 "    ret\ncount ENDP\nEND\n"),
    ("fasm sized label", FASM64, "format PE64 console\nentry start\nsection '.data' data readable writeable\n"
                                 "    x db 1\nsection '.text' code readable executable\nstart:\n    mov [x], 5\n"
                                 "    ret\n"),
    ("gas att", GAS, "    .text\n    .globl main\nmain:\n    subq $40, %rsp\n    movl $1, %eax\n    addq $40, %rsp\n"
                     "    ret\n"),
    ("suppressed by comment", W64, nasm64("    mov eax, bl          ; asmlint-disable-line ASM101")),
]
