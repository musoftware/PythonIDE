; Student program 2: average of an array, count down with a loop (NASM, Windows x64)
default rel
global main
extern printf

section .data
    nums    dd 10, 20, 30, 40, 50
    fmt     db "avg = %d", 10, 0
    line    db "i = %d", 10, 0

section .text
main:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    xor eax, eax
    mov ecx, 5
    lea rbx, [nums]
.sum:
    add eax, [rbx]
    add rbx, 4
    loop .sum
    mov ecx, 5
    div ecx
    lea rcx, [fmt]
    mov edx, eax
    call printf
    mov ecx, 3
.again:
    mov edx, ecx
    lea rcx, [line]
    call printf
    dec ecx
    jnz .again
    mov rsp, rbp
    pop rbp
    xor eax, eax
    ret
