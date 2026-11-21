; NasmLooseInput - a loose NASM x64 program (no project file) that reads a number with scanf.
; File > Open Folder opens it in place; Ctrl+F5 and F5 read the number from the Program Input bar.
default rel
global main
extern printf, scanf

section .data
    ask     db "Number? ", 0
    infmt   db "%d", 0
    outfmt  db "Twice %d is %d", 10, 0

section .bss
    value   resd 1

section .text
main:
    sub rsp, 40                 ; shadow space + alignment
    lea rcx, [ask]
    call printf
    lea rcx, [infmt]
    lea rdx, [value]
    call scanf
    mov edx, [value]
    mov r8d, edx
    add r8d, r8d                ; r8 = 2 * value
    lea rcx, [outfmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
