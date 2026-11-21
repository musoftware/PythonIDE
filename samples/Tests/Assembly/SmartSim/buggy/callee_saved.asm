; Bug: main changes RBX (a register the caller owns) and does not restore it.
default rel
global main

section .text
main:
    sub rsp, 40
    mov ebx, 5
    imul ebx, ebx
    mov eax, ebx
    add rsp, 40
    ret                         ; EXPECT: sim.callee_saved
