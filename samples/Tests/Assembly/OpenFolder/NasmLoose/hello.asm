; NasmLoose - a loose NASM x64 program (no project file): File > Open Folder detects NASM and opens it in place.
default rel
global main
extern printf
%include "macros.inc"

section .data
    fmt db "NASM loose folder: 6 * 7 = %d", 10, 0

section .text
main:
    sub rsp, 40
    mov eax, 6
    TIMES7 eax
    lea rcx, [fmt]
    mov edx, eax
    call printf
    xor eax, eax
    add rsp, 40
    ret
