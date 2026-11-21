"""Code snippets for assembly (VS Code snippet syntax: $1, ${1:name}, $0) per dialect and ABI.

``snippets(dialect, abi)`` -> [(prefix, description, body)]. Bodies are original templates written for RAD IDE.
"""
from __future__ import annotations


def _nasm(abi: str) -> list[tuple[str, str, str]]:
    out = [
        ("proc", "Procedure with stack frame (prologue / epilogue)",
         "; ${1:name}: ${2:what it does}\n${1:name}:\n    push    rbp\n    mov     rbp, rsp\n    sub     rsp, ${3:32}\n"
         "    $0\n    mov     rsp, rbp\n    pop     rbp\n    ret" if abi in ("win64", "sysv") else
         "; ${1:name}: ${2:what it does}\n${1:name}:\n    push    ebp\n    mov     ebp, esp\n    sub     esp, ${3:8}\n"
         "    $0\n    mov     esp, ebp\n    pop     ebp\n    ret"),
        ("loop", "Counted loop (counter in ECX)",
         "    mov     ecx, ${1:10}\n.${2:loop}:\n    push    rcx\n    $0\n    pop     rcx\n    dec     ecx\n"
         "    jnz     .${2:loop}" if abi in ("win64", "sysv") else
         "    mov     ecx, ${1:10}\n.${2:loop}:\n    $0\n    loop    .${2:loop}"),
        ("ifcmp", "if (a < b) ... else ... with CMP + Jcc",
         "    cmp     ${1:eax}, ${2:ebx}\n    j${3|ge,le,ne,e,g,l,ae,be,a,b|}     .${4:else}\n    ; then\n    $0\n"
         "    jmp     .${5:endif}\n.${4:else}:\n    ; else\n.${5:endif}:"),
        ("while", "while loop (test at the top)",
         ".${1:while}:\n    cmp     ${2:ecx}, ${3:0}\n    je      .${4:wend}\n    $0\n    jmp     .${1:while}\n.${4:wend}:"),
        ("section", "Code / data sections", "section .data\n    $1\n\nsection .bss\n    $2\n\nsection .text\n    $0"),
        ("str", "Zero-terminated string", "${1:msg}    db \"${2:text}\", ${3:13, 10, }0"),
        ("strlen", "String with its length constant",
         "${1:msg}     db \"${2:text}\", 13, 10\n${1:msg}_len equ \\$ - ${1:msg}"),
        ("macro", "Multi-line macro", "%macro ${1:name} ${2:1}\n    $0\n%endmacro"),
        ("struc", "Structure definition", "struc ${1:NAME}\n    .${2:field}  resd 1\n    $0\nendstruc"),
    ]
    if abi == "win64":
        out += [
            ("winmain", "Win64 console program skeleton (NASM)",
             "bits 64\ndefault rel\n\nextern ExitProcess\n\nsection .data\n    $1\n\nsection .text\nglobal main\n\n"
             "main:\n    sub     rsp, 40                 ; shadow space + alignment\n    $0\n    xor     ecx, ecx\n"
             "    call    ExitProcess"),
            ("call64", "Win64 call: arguments in RCX RDX R8 R9 + 32-byte shadow space",
             "    sub     rsp, ${1:40}                 ; shadow space (32) + keep RSP 16-byte aligned\n"
             "    mov     rcx, ${2:arg1}\n    mov     rdx, ${3:arg2}\n    mov     r8, ${4:arg3}\n"
             "    mov     r9, ${5:arg4}\n    call    ${6:Function}\n    add     rsp, ${1:40}\n$0"),
            ("msgbox", "MessageBoxA (Win64)",
             "    sub     rsp, 40\n    xor     ecx, ecx                ; hWnd = NULL\n    lea     rdx, [${1:text}]\n"
             "    lea     r8, [${2:caption}]\n    mov     r9d, ${3:0}             ; MB_OK\n    call    MessageBoxA\n"
             "    add     rsp, 40\n$0"),
            ("exit", "ExitProcess (Win64)", "    mov     ecx, ${1:0}\n    call    ExitProcess"),
            ("print", "WriteConsoleA to standard output (Win64)",
             "    mov     ecx, -11                ; STD_OUTPUT_HANDLE\n    call    GetStdHandle\n    mov     rcx, rax\n"
             "    lea     rdx, [${1:msg}]\n    mov     r8d, ${2:msg_len}\n    lea     r9, [${3:written}]\n"
             "    mov     qword [rsp + 32], 0\n    call    WriteConsoleA\n$0"),
        ]
    elif abi == "sysv":
        out += [
            ("start", "Linux x86-64 program skeleton (NASM)",
             "bits 64\nsection .data\n    ${1:msg} db \"Hello\", 10\n    ${1:msg}_len equ \\$ - ${1:msg}\n\n"
             "section .text\nglobal _start\n_start:\n    $0\n    mov     eax, 60                 ; sys_exit\n"
             "    xor     edi, edi\n    syscall"),
            ("write", "sys_write (Linux x86-64)",
             "    mov     eax, 1                  ; sys_write\n    mov     edi, 1                  ; stdout\n"
             "    lea     rsi, [rel ${1:msg}]\n    mov     edx, ${2:msg_len}\n    syscall\n$0"),
            ("exit", "sys_exit (Linux x86-64)", "    mov     eax, 60\n    mov     edi, ${1:0}\n    syscall"),
        ]
    elif abi == "x86":
        out += [
            ("call32", "stdcall / cdecl call: push arguments right to left",
             "    push    ${3:arg2}\n    push    ${2:arg1}\n    call    ${1:Function}\n${4:    add     esp, 8      ; cdecl only}\n$0"),
            ("msgbox", "MessageBoxA (32-bit stdcall)",
             "    push    ${3:0}                  ; MB_OK\n    push    ${2:caption}\n    push    ${1:text}\n"
             "    push    0                       ; hWnd\n    call    _MessageBoxA@16\n$0"),
        ]
    elif abi == "dos16":
        out += [
            ("com", "DOS .COM program skeleton",
             "org 100h\n\nstart:\n    mov     dx, ${1:msg}\n    mov     ah, 09h\n    int     21h\n    $0\n"
             "    mov     ax, 4C00h\n    int     21h\n\n${1:msg} db \"${2:Hello}\", 13, 10, '\\$'"),
            ("print", "DOS print string (int 21h / AH=09h)", "    mov     dx, ${1:msg}\n    mov     ah, 09h\n    int     21h"),
        ]
    return out


def _masm(abi: str) -> list[tuple[str, str, str]]:
    out = [
        ("proc", "PROC ... ENDP", "${1:Name} PROC ${2:uses ebx esi} ${3:arg1:DWORD}\n    $0\n    ret\n${1:Name} ENDP"),
        ("ifcmp", "if with CMP + Jcc",
         "    cmp     ${1:eax}, ${2:ebx}\n    j${3|ge,le,ne,e,g,l,ae,be,a,b|}     ${4:L_else}\n    $0\n"
         "    jmp     ${5:L_end}\n${4:L_else}:\n${5:L_end}:"),
        (".if", "High-level .IF / .ELSE / .ENDIF", ".if ${1:eax} == ${2:0}\n    $0\n.else\n.endif"),
        (".while", "High-level .WHILE loop", ".while ${1:ecx} > 0\n    $0\n    dec ecx\n.endw"),
        ("loop", "Counted loop", "    mov     ecx, ${1:10}\n${2:L_loop}:\n    $0\n    loop    ${2:L_loop}"),
        ("struct", "STRUCT", "${1:NAME} STRUCT\n    ${2:field} DWORD ?\n    $0\n${1:NAME} ENDS"),
        ("macro", "MACRO", "${1:name} MACRO ${2:arg}\n    $0\nENDM"),
        ("str", "Zero-terminated string", "${1:szText} BYTE \"${2:text}\", 0"),
    ]
    if abi == "x86":
        out += [
            ("program32", "MASM 32-bit Windows program skeleton",
             ".386\n.model flat, stdcall\noption casemap:none\n\nincludelib kernel32.lib\nincludelib user32.lib\n\n"
             "ExitProcess PROTO :DWORD\nMessageBoxA PROTO :DWORD, :DWORD, :DWORD, :DWORD\n\n.data\n"
             "    szTitle BYTE \"${1:RAD IDE}\", 0\n    szText  BYTE \"${2:Hello}\", 0\n\n.code\nstart:\n"
             "    $0\n    invoke  ExitProcess, 0\nEND start"),
            ("msgbox", "INVOKE MessageBoxA", "invoke  MessageBoxA, 0, addr ${1:szText}, addr ${2:szTitle}, ${3:MB_OK}"),
        ]
    else:
        out += [
            ("program64", "ml64 Windows program skeleton",
             "extern ExitProcess:proc\nextern MessageBoxA:proc\n\n.data\n    szTitle BYTE \"${1:RAD IDE}\", 0\n"
             "    szText  BYTE \"${2:Hello}\", 0\n\n.code\nmain PROC\n    sub     rsp, 28h\n    $0\n"
             "    xor     ecx, ecx\n    call    ExitProcess\nmain ENDP\nEND"),
            ("call64", "Win64 call with shadow space",
             "    sub     rsp, 28h\n    mov     rcx, ${1:arg1}\n    mov     rdx, ${2:arg2}\n    mov     r8, ${3:arg3}\n"
             "    mov     r9, ${4:arg4}\n    call    ${5:Function}\n    add     rsp, 28h\n$0"),
            ("msgbox", "MessageBoxA (ml64)",
             "    sub     rsp, 28h\n    xor     ecx, ecx\n    lea     rdx, ${1:szText}\n    lea     r8, ${2:szTitle}\n"
             "    mov     r9d, ${3:0}\n    call    MessageBoxA\n    add     rsp, 28h\n$0"),
            ("frame", "PROC FRAME with unwind info (ml64)",
             "${1:Name} PROC FRAME\n    push    rbp\n    .pushreg rbp\n    sub     rsp, ${2:20h}\n    .allocstack ${2:20h}\n"
             "    mov     rbp, rsp\n    .setframe rbp, 0\n    .endprolog\n    $0\n    add     rsp, ${2:20h}\n"
             "    pop     rbp\n    ret\n${1:Name} ENDP"),
        ]
    return out


def _fasm(abi: str) -> list[tuple[str, str, str]]:
    out = [
        ("proc", "proc ... endp (macro package)", "proc ${1:Name} ${2:arg1}, ${3:arg2}\n    $0\n    ret\nendp"),
        ("macro", "macro { }", "macro ${1:name} ${2:arg}\n{\n    $0\n}"),
        ("ifcmp", "if with CMP + Jcc",
         "    cmp     ${1:eax}, ${2:ebx}\n    j${3|ge,le,ne,e,g,l,ae,be,a,b|}     .${4:else}\n    $0\n"
         "    jmp     .${5:endif}\n  .${4:else}:\n  .${5:endif}:"),
        ("loop", "Counted loop", "    mov     ecx, ${1:10}\n  .${2:loop}:\n    $0\n    loop    .${2:loop}"),
        ("struct", "struct ... ends", "struct ${1:NAME}\n    ${2:field} dd ?\n    $0\nends"),
        ("str", "Zero-terminated string", "${1:msg} db '${2:text}', 0"),
    ]
    if abi == "win64":
        out += [
            ("pe64", "FASM Win64 GUI program skeleton",
             "format PE64 GUI 5.0\nentry start\n\ninclude 'win64a.inc'\n\nsection '.data' data readable writeable\n"
             "    caption db '${1:RAD IDE}', 0\n    message db '${2:Hello}', 0\n\nsection '.text' code readable executable\n"
             "start:\n    sub     rsp, 8\n    $0\n    invoke  MessageBox, 0, message, caption, MB_OK\n"
             "    invoke  ExitProcess, 0\n\nsection '.idata' import data readable writeable\n"
             "    library kernel32, 'KERNEL32.DLL', user32, 'USER32.DLL'\n    include 'api\\\\kernel32.inc'\n"
             "    include 'api\\\\user32.inc'"),
            ("msgbox", "invoke MessageBox", "invoke  MessageBox, 0, ${1:message}, ${2:caption}, ${3:MB_OK}"),
        ]
    elif abi == "sysv":
        out += [("elf64", "FASM Linux ELF64 executable skeleton",
                 "format ELF64 executable 3\nentry start\n\nsegment readable executable\nstart:\n    $0\n"
                 "    mov     eax, 60\n    xor     edi, edi\n    syscall\n\nsegment readable writeable\n"
                 "    ${1:msg} db '${2:Hello}', 10")]
    else:
        out += [
            ("pe32", "FASM Win32 GUI program skeleton",
             "format PE GUI 4.0\nentry start\n\ninclude 'win32a.inc'\n\nsection '.data' data readable writeable\n"
             "    caption db '${1:RAD IDE}', 0\n    message db '${2:Hello}', 0\n\nsection '.text' code readable executable\n"
             "start:\n    $0\n    invoke  MessageBox, HWND_DESKTOP, message, caption, MB_OK\n    invoke  ExitProcess, 0\n\n"
             "section '.idata' import data readable writeable\n    library kernel32, 'KERNEL32.DLL', user32, 'USER32.DLL'\n"
             "    import  kernel32, ExitProcess, 'ExitProcess'\n    import  user32, MessageBox, 'MessageBoxA'"),
            ("msgbox", "invoke MessageBox", "invoke  MessageBox, HWND_DESKTOP, ${1:message}, ${2:caption}, ${3:MB_OK}"),
        ]
    return out


def _gas(abi: str, att: bool) -> list[tuple[str, str, str]]:
    if att:
        out = [
            ("proc", "Function with stack frame (AT&T)",
             "    .globl ${1:name}\n${1:name}:\n    pushq   %rbp\n    movq    %rsp, %rbp\n    subq    \\$${2:32}, %rsp\n"
             "    $0\n    movq    %rbp, %rsp\n    popq    %rbp\n    ret"),
            ("loop", "Counted loop (AT&T)",
             "    movl    \\$${1:10}, %ecx\n.L${2:loop}:\n    $0\n    decl    %ecx\n    jnz     .L${2:loop}"),
            ("ifcmp", "if with CMP + Jcc (AT&T: cmp src, dst compares dst with src)",
             "    cmpl    ${2:%ebx}, ${1:%eax}\n    j${3|ge,le,ne,e,g,l,ae,be,a,b|}     .L${4:else}\n    $0\n"
             "    jmp     .L${5:endif}\n.L${4:else}:\n.L${5:endif}:"),
        ]
    else:
        out = [
            ("proc", "Function with stack frame (Intel syntax)",
             "    .globl ${1:name}\n${1:name}:\n    push    rbp\n    mov     rbp, rsp\n    sub     rsp, ${2:32}\n    $0\n"
             "    mov     rsp, rbp\n    pop     rbp\n    ret"),
            ("loop", "Counted loop", "    mov     ecx, ${1:10}\n.L${2:loop}:\n    $0\n    dec     ecx\n    jnz     .L${2:loop}"),
            ("ifcmp", "if with CMP + Jcc",
             "    cmp     ${1:eax}, ${2:ebx}\n    j${3|ge,le,ne,e,g,l,ae,be,a,b|}     .L${4:else}\n    $0\n"
             "    jmp     .L${5:endif}\n.L${4:else}:\n.L${5:endif}:"),
        ]
    out += [
        ("macro", ".macro ... .endm", ".macro ${1:name} ${2:arg}\n    $0\n.endm"),
        ("str", "Zero-terminated string", "${1:msg}:\n    .asciz \"${2:text}\""),
    ]
    if abi == "sysv":
        out.append(("start", "Linux x86-64 program skeleton (GAS AT&T)" if att else "Linux program skeleton",
                    "    .section .rodata\nmsg:\n    .ascii \"${1:Hello}\\\\n\"\n    .equ msg_len, . - msg\n\n    .text\n"
                    "    .globl _start\n_start:\n    $0\n    movq    \\$60, %rax\n    xorq    %rdi, %rdi\n    syscall"
                    if att else
                    "    .intel_syntax noprefix\n    .text\n    .globl _start\n_start:\n    $0\n    mov     eax, 60\n"
                    "    xor     edi, edi\n    syscall"))
    elif abi == "win64":
        out.append(("call64", "Win64 call with shadow space",
                    "    subq    \\$40, %rsp\n    movq    ${1:arg1}, %rcx\n    movq    ${2:arg2}, %rdx\n    call    ${3:Function}\n"
                    "    addq    \\$40, %rsp\n$0" if att else
                    "    sub     rsp, 40\n    mov     rcx, ${1:arg1}\n    mov     rdx, ${2:arg2}\n    call    ${3:Function}\n"
                    "    add     rsp, 40\n$0"))
        out.append(("winmain", "MinGW main skeleton (Intel syntax)",
                    "    .intel_syntax noprefix\n    .section .rdata,\"dr\"\nfmt:\n    .asciz \"${1:Hello %d}\\\\n\"\n\n"
                    "    .text\n    .globl main\nmain:\n    sub     rsp, 40\n    lea     rcx, fmt[rip]\n    mov     edx, 42\n"
                    "    call    printf\n    $0\n    xor     eax, eax\n    add     rsp, 40\n    ret"))
    return out


def snippets(dialect: str, abi: str, att: bool = False) -> list[tuple[str, str, str]]:
    if dialect == "masm":
        return _masm(abi)
    if dialect == "fasm":
        return _fasm(abi)
    if dialect == "gas":
        return _gas(abi, att)
    return _nasm(abi)
