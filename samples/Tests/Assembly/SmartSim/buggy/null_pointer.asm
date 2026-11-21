; Bug: RBX is cleared and then used as an address.
default rel
global main

section .text
main:
    sub rsp, 40
    xor ebx, ebx                ; rbx = 0 ("no address")
    mov eax, [rbx]              ; EXPECT: sim.null_deref
    add rsp, 40
    ret
