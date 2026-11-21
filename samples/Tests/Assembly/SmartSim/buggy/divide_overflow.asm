; Bug: EDX still holds a big value, so EDX:EAX / 2 does not fit in EAX (missing 'xor edx, edx').
default rel
global main

section .text
main:
    sub rsp, 40
    mov edx, 7
    mov eax, 100
    mov ecx, 2
    div ecx                     ; EXPECT: sim.div_overflow
    add rsp, 40
    ret
