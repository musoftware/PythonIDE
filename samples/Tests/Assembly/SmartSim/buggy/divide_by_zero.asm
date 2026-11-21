; Bug: the divisor is zero.
default rel
global main
extern printf

section .data
    fmt db "%d", 10, 0
    count dd 0

section .text
main:
    sub rsp, 40
    mov eax, 100
    xor edx, edx
    mov ecx, [count]
    div ecx                     ; EXPECT: sim.div_zero
    lea rcx, [fmt]
    mov edx, eax
    call printf
    add rsp, 40
    ret
