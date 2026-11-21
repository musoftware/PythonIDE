; Student program 1: print my name and the sum of two numbers (NASM, Windows x64)
default rel
global main
extern printf

section .data
    msg     db "My name is Ahmed", 10, 0
    fmt     db "a + b = %d", 10, 0
    a       dd 7
    b       dd 5

section .text
main:
    mov rcx, [msg]
    call printf
    mov eax, [a]
    add eax, [b]
    mov rdx, eax
    lea rcx, [fmt]
    call printf
    mov [a], 0
    xor eax, eax
    ret
