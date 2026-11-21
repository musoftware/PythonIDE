"""New Project templates of the Assembly languages (original code written for RAD IDE).

Every console template shows the same three things: Hello World, the C runtime (printf / scanf / puts) and a
Win32 API call (GetComputerNameA). "Win32 API" shows MessageBoxA; "Windows Forms" is a form drawn in the
designer whose events are handled in assembly (GUI Bridge, radide/asm/formgen.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------------------------- NASM x64
NASM_X64 = r"""; {name} - an x64 Windows console program written with NASM.
; Ctrl+F5 runs it (the Output window shows what it prints; type the input in the Program Input bar),
; F5 debugs it (breakpoints by line, registers, step instruction).
;
; Microsoft x64 calling convention (used by the C runtime and the Win32 API):
;   * the first four arguments go in RCX, RDX, R8, R9 (more arguments on the stack), the result comes in RAX;
;   * the caller reserves 32 bytes of "shadow space" and RSP is 16-byte aligned at every CALL;
;   * RAX, RCX, RDX, R8-R11 may be changed by the called function; RBX, RBP, RSI, RDI, R12-R15 are kept.
default rel                         ; [label] = RIP-relative addressing (needed for 64-bit Windows programs)

global main                         ; the C runtime calls main
extern printf, scanf, puts, fflush  ; C runtime
extern GetComputerNameA             ; Win32 API (kernel32.dll)

section .data
    hello       db "Hello from assembly!", 0
    ask         db "Enter a number: ", 0
    fmt_in      db "%lld", 0
    fmt_square  db "%lld squared is %lld", 10, 0
    fmt_sum     db "1 + 2 + ... + %lld = %lld", 10, 0
    fmt_pc      db "This computer is called %s", 10, 0
    pc_size     dd 64

section .bss
    number      resq 1
    pc_name     resb 64

section .text
main:
    push rbp                        ; RSP was 8 mod 16 on entry: now it is aligned
    mov rbp, rsp
    sub rsp, 32                     ; shadow space for the calls below

    lea rcx, [hello]                ; puts(hello)
    call puts

    lea rcx, [ask]                  ; printf(ask) then fflush(NULL): show the prompt before scanf waits
    call printf
    xor ecx, ecx
    call fflush

    lea rcx, [fmt_in]               ; scanf("%lld", &number)
    lea rdx, [number]
    call scanf

    mov rax, [number]               ; number * number
    imul rax, rax
    lea rcx, [fmt_square]
    mov rdx, [number]
    mov r8, rax
    call printf

    xor eax, eax                    ; sum = 0
    mov rcx, [number]               ; i = number
.add_next:
    cmp rcx, 0                      ; while (i > 0) { sum += i; i--; }
    jle .add_done
    add rax, rcx
    dec rcx
    jmp .add_next
.add_done:
    lea rcx, [fmt_sum]
    mov rdx, [number]
    mov r8, rax
    call printf

    lea rcx, [pc_name]              ; GetComputerNameA(pc_name, &pc_size)
    lea rdx, [pc_size]
    call GetComputerNameA
    lea rcx, [fmt_pc]
    lea rdx, [pc_name]
    call printf

    xor eax, eax                    ; return 0
    leave
    ret
"""

# ---------------------------------------------------------------------------------------------- NASM x86
NASM_X86 = r"""; {name} - a 32-bit (x86) Windows console program written with NASM.
; Ctrl+F5 runs it; type the input in the Program Input bar.
;
; 32-bit conventions:
;   * cdecl (C runtime): arguments are pushed right to left, the caller removes them (add esp, 4*n);
;   * stdcall (Win32 API): the same order, but the called function removes them;
;   * the linker names C functions with a leading underscore (_printf) and Win32 functions with the size of
;     their arguments (_GetComputerNameA@8);
;   * the result comes in EAX; EAX, ECX, EDX may be changed, EBX, ESI, EDI, EBP are kept.
; The program is linked directly against msvcrt.dll / kernel32.dll (no C runtime start-up code): _main is the
; entry point and it ends with ExitProcess.

global _main
extern _printf, _scanf, _puts, _fflush             ; C runtime (msvcrt.dll)
extern _GetComputerNameA@8, _ExitProcess@4          ; Win32 API (kernel32.dll)

section .data
    hello       db "Hello from 32-bit assembly!", 0
    ask         db "Enter a number: ", 0
    fmt_in      db "%d", 0
    fmt_square  db "%d squared is %d", 10, 0
    fmt_sum     db "1 + 2 + ... + %d = %d", 10, 0
    fmt_pc      db "This computer is called %s", 10, 0
    pc_size     dd 64

section .bss
    number      resd 1
    pc_name     resb 64

section .text
_main:
    push hello                      ; puts(hello)
    call _puts
    add esp, 4

    push ask                        ; printf(ask); fflush(NULL)
    call _printf
    add esp, 4
    push 0
    call _fflush
    add esp, 4

    push number                     ; scanf("%d", &number)
    push fmt_in
    call _scanf
    add esp, 8

    mov eax, [number]               ; number * number
    imul eax, eax
    push eax
    push dword [number]
    push fmt_square
    call _printf
    add esp, 12

    xor eax, eax                    ; sum = 1 + 2 + ... + number
    mov ecx, [number]
.add_next:
    cmp ecx, 0
    jle .add_done
    add eax, ecx
    dec ecx
    jmp .add_next
.add_done:
    push eax
    push dword [number]
    push fmt_sum
    call _printf
    add esp, 12

    push pc_size                    ; GetComputerNameA(pc_name, &pc_size) - stdcall: no add esp
    push pc_name
    call _GetComputerNameA@8
    push pc_name
    push fmt_pc
    call _printf
    add esp, 8

    push 0                          ; fflush(NULL); ExitProcess(0)
    call _fflush
    add esp, 4
    push 0
    call _ExitProcess@4
"""

# ---------------------------------------------------------------------------------------------- NASM Win32 API
NASM_WINAPI = r"""; {name} - calling the Win32 API from x64 assembly (NASM): two message boxes.
; Ctrl+F5 runs it. The Win32 functions use the same x64 convention as C: RCX, RDX, R8, R9 + shadow space.
default rel

global main
extern MessageBoxA, MessageBeep, printf     ; user32.dll / msvcrt

MB_OK               equ 0x00
MB_YESNO            equ 0x04
MB_ICONQUESTION     equ 0x20
MB_ICONINFORMATION  equ 0x40
IDYES               equ 6

section .data
    caption     db "{name}", 0
    question    db "Do you like assembly language?", 0
    said_yes    db "Great! The CPU likes you too.", 0
    said_no     db "Give it a chance: every program ends up as machine code.", 0
    fmt_answer  db "MessageBoxA returned %d", 10, 0

section .text
main:
    push rbp
    mov rbp, rsp
    push rbx                        ; RBX is kept by the functions we call: it holds the answer
    sub rsp, 40                     ; shadow space (32) + 8 to keep RSP 16-byte aligned

    xor ecx, ecx                    ; MessageBoxA(NULL, question, caption, MB_YESNO | MB_ICONQUESTION)
    lea rdx, [question]
    lea r8, [caption]
    mov r9d, MB_YESNO | MB_ICONQUESTION
    call MessageBoxA
    mov ebx, eax

    lea rcx, [fmt_answer]           ; printf("... %d", answer)
    mov edx, ebx
    call printf

    mov ecx, MB_ICONINFORMATION     ; MessageBeep(MB_ICONINFORMATION)
    call MessageBeep

    lea rdx, [said_no]              ; text = (answer == IDYES) ? said_yes : said_no
    lea rax, [said_yes]
    cmp ebx, IDYES
    cmove rdx, rax
    xor ecx, ecx
    lea r8, [caption]
    mov r9d, MB_OK | MB_ICONINFORMATION
    call MessageBoxA

    xor eax, eax
    add rsp, 40
    pop rbx
    pop rbp
    ret
"""

# ---------------------------------------------------------------------------------------------- NASM forms
NASM_FORM = r"""; Event handlers of {form} (NASM, x64). The IDE draws the form (GUI Bridge); this code reacts to its
; events and changes the controls with the macros of radgui.inc: rad_set, rad_get, rad_get_int, rad_set_int,
; rad_msgbox, rad_input, rad_call ... (see the top of radgui.inc).
;
; A handler is a block   handler <Control>_<Event> ... endhandler   - double-click a control in the designer
; to add one. Inside a handler RBX, RSI, RDI and R12 are yours (they are saved); do not change RBP or RSP.
%include "radgui.inc"
%include "{form}.inc"           ; generated: the names of the controls of {form} (lblMessage, btnAdd ...)

section .data
    clicks      dq 0

section .text

handler {form}_Load
    rad_set lblMessage, "Text", "Hello from assembly! Type a number and press Add 1."
endhandler

handler btnAdd_Click
    rad_get_int txtNumber, "Text"   ; RAX = the number in the text box
    inc rax
    mov rbx, rax                    ; RBX survives the next macro calls
    rad_set_int txtNumber, "Text", rbx
    inc qword [clicks]
    rad_set_int lblClicks, "Text", [clicks]
    rad_set lblMessage, "Text", "The assembly handler added 1."
endhandler

handler btnHello_Click
    rad_input "What is your name?"  ; RAX = the text typed (a C string)
    mov rbx, rax
    rad_set lblMessage, "Text", rbx
    rad_msgbox "Hello from x64 assembly!"
endhandler
"""

# ---------------------------------------------------------------------------------------------- FASM
FASM_X64 = r"""; {name} - an x64 Windows console program written with FASM (flat assembler).
; FASM writes the .exe itself (format PE64): there is no separate link step. The 'invoke' / 'cinvoke' macros
; and the import macros come from win64a.inc (FASM's INCLUDE folder - RAD IDE sets it for you).
; Ctrl+F5 runs it; type the input in the Program Input bar.
format PE64 console
entry start

include 'win64a.inc'

section '.data' data readable writeable
    hello       db 'Hello from FASM!', 0
    ask         db 'Enter a number: ', 0
    fmt_in      db '%lld', 0
    fmt_twice   db '%lld + %lld = %lld', 10, 0
    fmt_pc      db 'This computer is called %s', 10, 0
    number      dq 0
    pc_size     dd 64
    pc_name     rb 64

section '.text' code readable executable
start:
    sub rsp, 8                      ; RSP was 8 mod 16 at the entry point: align it for the calls
    cinvoke puts, hello
    cinvoke printf, ask
    cinvoke fflush, 0
    cinvoke scanf, fmt_in, number
    mov rax, [number]
    add rax, rax
    cinvoke printf, fmt_twice, [number], [number], rax
    invoke GetComputerNameA, pc_name, pc_size
    cinvoke printf, fmt_pc, pc_name
    invoke ExitProcess, 0

section '.idata' import data readable writeable
    library kernel32, 'KERNEL32.DLL', msvcrt, 'MSVCRT.DLL'
    import kernel32, GetComputerNameA, 'GetComputerNameA', ExitProcess, 'ExitProcess'
    import msvcrt, printf, 'printf', scanf, 'scanf', puts, 'puts', fflush, 'fflush'
"""

FASM_X86 = r"""; {name} - a 32-bit Windows console program written with FASM (flat assembler).
; FASM writes the .exe itself (format PE). 'cinvoke' calls a C (cdecl) function, 'invoke' a Win32 (stdcall) one;
; the macros come from win32a.inc (FASM's INCLUDE folder - RAD IDE sets it for you).
format PE console
entry start

include 'win32a.inc'

section '.data' data readable writeable
    hello       db 'Hello from 32-bit FASM!', 0
    ask         db 'Enter a number: ', 0
    fmt_in      db '%d', 0
    fmt_twice   db '%d + %d = %d', 10, 0
    fmt_pc      db 'This computer is called %s', 10, 0
    number      dd 0
    pc_size     dd 64
    pc_name     rb 64

section '.text' code readable executable
start:
    cinvoke puts, hello
    cinvoke printf, ask
    cinvoke fflush, 0
    cinvoke scanf, fmt_in, number
    mov eax, [number]
    add eax, eax
    cinvoke printf, fmt_twice, [number], [number], eax
    invoke GetComputerNameA, pc_name, pc_size
    cinvoke printf, fmt_pc, pc_name
    cinvoke fflush, 0
    invoke ExitProcess, 0

section '.idata' import data readable writeable
    library kernel32, 'KERNEL32.DLL', msvcrt, 'MSVCRT.DLL'
    import kernel32, GetComputerNameA, 'GetComputerNameA', ExitProcess, 'ExitProcess'
    import msvcrt, printf, 'printf', scanf, 'scanf', puts, 'puts', fflush, 'fflush'
"""

# ---------------------------------------------------------------------------------------------- MASM
MASM_X64 = r"""; {name} - an x64 Windows console program written with MASM (ml64, Visual Studio).
; ml64 has no INVOKE: call functions as C does - arguments in RCX, RDX, R8, R9, 32 bytes of shadow space,
; RSP 16-byte aligned at every CALL. Ctrl+F5 runs it; type the input in the Program Input bar.
; Debugging MASM programs needs the Visual Studio debugger (ml64 writes CodeView / PDB information).

extern printf : proc
extern scanf : proc
extern puts : proc
extern fflush : proc
extern GetComputerNameA : proc

.data
hello       db "Hello from MASM!", 0
ask         db "Enter a number: ", 0
fmt_in      db "%lld", 0
fmt_cube    db "%lld cubed is %lld", 10, 0
fmt_pc      db "This computer is called %s", 10, 0
pc_size     dd 64
number      dq 0
pc_name     db 64 dup (0)

.code
main proc
    sub rsp, 40                     ; shadow space + 8: RSP is now 16-byte aligned

    lea rcx, hello
    call puts

    lea rcx, ask
    call printf
    xor ecx, ecx
    call fflush

    lea rcx, fmt_in
    lea rdx, number
    call scanf

    mov rax, number                 ; number * number * number
    imul rax, rax
    imul rax, number
    lea rcx, fmt_cube
    mov rdx, number
    mov r8, rax
    call printf

    lea rcx, pc_name
    lea rdx, pc_size
    call GetComputerNameA
    lea rcx, fmt_pc
    lea rdx, pc_name
    call printf

    xor eax, eax
    add rsp, 40
    ret
main endp

end
"""

MASM_X86 = r"""; {name} - a 32-bit Windows console program written with MASM (ml, Visual Studio).
; In 32-bit MASM, INVOKE pushes the arguments for you; PROTO declares a function's parameters.
.386
.model flat, c
.stack 4096

printf      proto c :ptr byte, :vararg
scanf       proto c :ptr byte, :vararg
puts        proto c :ptr byte
fflush      proto c :ptr
GetComputerNameA proto stdcall :ptr byte, :ptr dword

.data
hello       db "Hello from 32-bit MASM!", 0
ask         db "Enter a number: ", 0
fmt_in      db "%d", 0
fmt_cube    db "%d cubed is %d", 10, 0
fmt_pc      db "This computer is called %s", 10, 0
pc_size     dd 64
number      dd 0
pc_name     db 64 dup (0)

.code
main proc
    invoke puts, addr hello
    invoke printf, addr ask
    invoke fflush, 0
    invoke scanf, addr fmt_in, addr number
    mov eax, number
    imul eax, eax
    imul eax, number
    invoke printf, addr fmt_cube, number, eax
    invoke GetComputerNameA, addr pc_name, addr pc_size
    invoke printf, addr fmt_pc, addr pc_name
    xor eax, eax
    ret
main endp

end
"""

# ---------------------------------------------------------------------------------------------- GNU as
GAS_ATT = r"""# {name} - an x64 Windows console program written for the GNU assembler (AT&T syntax).
# AT&T syntax: the source comes first, the destination last (movq %rax, %rbx copies RAX into RBX), registers
# start with %, constants with $, and the size is in the mnemonic (movq = 64 bits, movl = 32 bits).
# x64 Windows convention: arguments in %rcx, %rdx, %r8, %r9, 32 bytes of shadow space, %rsp 16-byte aligned.
# Ctrl+F5 runs it, F5 debugs it (gdb understands the line information that  as -g  writes).
        .data
hello:      .asciz "Hello from GNU as!"
ask:        .asciz "Enter a number: "
fmt_in:     .asciz "%lld"
fmt_out:    .asciz "%lld + 100 = %lld\n"
fmt_pc:     .asciz "This computer is called %s\n"
        .p2align 3
number:     .quad 0
pc_size:    .long 64
pc_name:    .space 64

        .text
        .globl main
main:
        pushq   %rbp
        movq    %rsp, %rbp
        subq    $32, %rsp               # shadow space

        leaq    hello(%rip), %rcx       # puts(hello)
        call    puts

        leaq    ask(%rip), %rcx         # printf(ask); fflush(NULL)
        call    printf
        xorl    %ecx, %ecx
        call    fflush

        leaq    fmt_in(%rip), %rcx      # scanf("%lld", &number)
        leaq    number(%rip), %rdx
        call    scanf

        movq    number(%rip), %rdx      # printf(fmt_out, number, number + 100)
        leaq    100(%rdx), %r8
        leaq    fmt_out(%rip), %rcx
        call    printf

        leaq    pc_name(%rip), %rcx     # GetComputerNameA(pc_name, &pc_size)
        leaq    pc_size(%rip), %rdx
        call    GetComputerNameA
        leaq    fmt_pc(%rip), %rcx
        leaq    pc_name(%rip), %rdx
        call    printf

        xorl    %eax, %eax
        leave
        ret
"""

GAS_INTEL = r"""# {name} - an x64 Windows console program for the GNU assembler in Intel syntax
# (.intel_syntax noprefix: destination first, no % or $ - the same order as NASM and MASM).
# Ctrl+F5 runs it, F5 debugs it (gdb understands the line information that  as -g  writes).
        .intel_syntax noprefix
        .data
hello:      .asciz "Hello from GNU as (Intel syntax)!"
ask:        .asciz "Enter a number: "
fmt_in:     .asciz "%lld"
fmt_out:    .asciz "%lld - 1 = %lld\n"
fmt_pc:     .asciz "This computer is called %s\n"
        .p2align 3
number:     .quad 0
pc_size:    .long 64
pc_name:    .space 64

        .text
        .globl main
main:
        push    rbp
        mov     rbp, rsp
        sub     rsp, 32                 # shadow space

        lea     rcx, [rip + hello]
        call    puts

        lea     rcx, [rip + ask]
        call    printf
        xor     ecx, ecx
        call    fflush

        lea     rcx, [rip + fmt_in]
        lea     rdx, [rip + number]
        call    scanf

        mov     rdx, [rip + number]
        lea     r8, [rdx - 1]
        lea     rcx, [rip + fmt_out]
        call    printf

        lea     rcx, [rip + pc_name]
        lea     rdx, [rip + pc_size]
        call    GetComputerNameA
        lea     rcx, [rip + fmt_pc]
        lea     rdx, [rip + pc_name]
        call    printf

        xor     eax, eax
        leave
        ret
"""


@dataclass(frozen=True)
class AsmTemplate:
    id: str
    plugin: str                 # asm-nasm | asm-fasm | asm-masm | asm-gas
    title: str
    description: str
    icon: str                   # QStyle standard icon name or rad:<icon>
    settings: dict = field(default_factory=dict)    # project.radproj "asm" entry
    files: tuple = ()           # ((file name, source), ...) - {name} is the project name
    forms: bool = False         # a GUI Bridge form project


TEMPLATES: list[AsmTemplate] = [
    AsmTemplate("nasm_console_x64", "asm-nasm", "Assembly Console (x64 Windows, NASM)",
                "A 64-bit console program: Hello World, printf / scanf from the C runtime and a Win32 API call. "
                "Assembled with NASM, linked with gcc (MinGW-w64). F5 debugs it with gdb (breakpoints by line, "
                "registers, step instruction).", "rad:console",
                {"assembler": "nasm", "arch": "x64", "linker": "gcc", "entry": "main"}, (("main.asm", NASM_X64),)),
    AsmTemplate("nasm_console_x86", "asm-nasm", "Assembly Console (x86 Windows, NASM)",
                "A 32-bit console program (cdecl / stdcall, _printf, _GetComputerNameA@8): linked directly against "
                "msvcrt.dll and kernel32.dll with GNU ld (or GoLink).", "rad:console",
                {"assembler": "nasm", "arch": "x86", "linker": "ld", "entry": "_main"}, (("main.asm", NASM_X86),)),
    AsmTemplate("nasm_winapi_x64", "asm-nasm", "Win32 API (x64, NASM)",
                "Calls MessageBoxA and MessageBeep from user32.dll and shows the answer: the Win32 API from "
                "assembly.", "SP_MessageBoxInformation",
                {"assembler": "nasm", "arch": "x64", "linker": "gcc", "entry": "main", "libs": ["user32"]},
                (("main.asm", NASM_WINAPI),)),
    AsmTemplate("nasm_forms", "asm-nasm", "Assembly Windows Forms (NASM + GUI Bridge)",
                "Design the form in the designer, double-click a control and write the event handler in x64 "
                "assembly (handler btnAdd_Click ... endhandler). The macros rad_set / rad_get_int / rad_msgbox "
                "talk to the form.", "SP_TitleBarNormalButton",
                {"assembler": "nasm", "arch": "x64", "linker": "gcc", "entry": "main"}, (), forms=True),
    AsmTemplate("fasm_console_x64", "asm-fasm", "FASM Console (x64)",
                "A 64-bit console program written with the flat assembler: FASM writes the .exe itself "
                "(format PE64 console, imports with the win64a.inc macros, cinvoke / invoke).", "rad:console",
                {"assembler": "fasm", "arch": "x64", "linker": "none", "entry": "start"}, (("main.asm", FASM_X64),)),
    AsmTemplate("fasm_console_x86", "asm-fasm", "FASM Console (x86)",
                "A 32-bit console program written with the flat assembler (format PE console, win32a.inc).",
                "rad:console", {"assembler": "fasm", "arch": "x86", "linker": "none", "entry": "start"},
                (("main.asm", FASM_X86),)),
    AsmTemplate("masm_console_x64", "asm-masm", "MASM Console (x64)",
                "A 64-bit console program for Microsoft's ml64 (needs Visual Studio with the C++ tools). Linked "
                "with link.exe against the C runtime.", "rad:console",
                {"assembler": "masm", "arch": "x64", "linker": "link", "entry": "main"}, (("main.asm", MASM_X64),)),
    AsmTemplate("masm_console_x86", "asm-masm", "MASM Console (x86)",
                "A 32-bit console program for Microsoft's ml (.model flat, INVOKE / PROTO). Needs Visual Studio "
                "with the C++ tools.", "rad:console",
                {"assembler": "masm", "arch": "x86", "linker": "link", "entry": "main"}, (("main.asm", MASM_X86),)),
    AsmTemplate("gas_console_x64", "asm-gas", "GNU as Console (x64, AT&T syntax)",
                "A 64-bit console program for the GNU assembler in AT&T syntax (as from MinGW-w64), linked with "
                "gcc. F5 debugs it with gdb.", "rad:console",
                {"assembler": "gas", "arch": "x64", "linker": "gcc", "entry": "main"}, (("main.s", GAS_ATT),)),
    AsmTemplate("gas_console_x64_intel", "asm-gas", "GNU as Console (x64, Intel syntax)",
                "The same program with .intel_syntax noprefix: GNU as with the operand order of NASM / MASM.",
                "rad:console", {"assembler": "gas", "arch": "x64", "linker": "gcc", "entry": "main"},
                (("main.s", GAS_INTEL),)),
]

BY_ID = {t.id: t for t in TEMPLATES}


def for_plugin(plugin_id: str) -> list[AsmTemplate]:
    return [t for t in TEMPLATES if t.plugin == plugin_id]


def form_code(form_name: str) -> str:
    return NASM_FORM.replace("{form}", form_name)
