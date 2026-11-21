; Hello.asm - main file of the RadASM project Hello.rap (NASM x64 here).
default rel
global main
extern puts

section .data
    msg db "RadASM project opened in place", 0

section .text
main:
    sub rsp, 40
    lea rcx, [msg]
    call puts
    xor eax, eax
    add rsp, 40
    ret
