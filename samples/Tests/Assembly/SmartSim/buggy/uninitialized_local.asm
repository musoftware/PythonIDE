; Bug: the local variable [rbp-8] is read before anything is stored in it.
default rel
global main

section .text
main:
    push rbp
    mov rbp, rsp
    sub rsp, 48
    mov eax, [rbp-8]            ; EXPECT: sim.uninit_read
    add eax, 1
    mov [rbp-8], eax
    leave
    ret
