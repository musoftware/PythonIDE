; Bug: main has no 'ret' at the end, so the CPU runs past the last instruction.
default rel
global main

section .text
main:
    sub rsp, 40
    mov eax, 1
    add rsp, 40                 ; EXPECT: sim.ran_off_end
