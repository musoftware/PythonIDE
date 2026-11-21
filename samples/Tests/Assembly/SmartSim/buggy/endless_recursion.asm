; Bug: count_down calls itself with no base case, so the stack overflows.
default rel
global main

section .text
count_down:
    sub rsp, 40
    dec ecx
    call count_down             ; EXPECT: sim.stack_overflow
    add rsp, 40
    ret

main:
    sub rsp, 40
    mov ecx, 10
    call count_down
    add rsp, 40
    ret
