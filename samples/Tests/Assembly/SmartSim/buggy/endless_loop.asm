; Bug: the counter is never decremented, so the loop never ends.
default rel
global main

section .text
main:
    sub rsp, 40
    mov ecx, 10
    xor eax, eax
.again:
    add eax, 2
    cmp ecx, 0
    jne .again                  ; EXPECT: sim.infinite_loop
    add rsp, 40
    ret
