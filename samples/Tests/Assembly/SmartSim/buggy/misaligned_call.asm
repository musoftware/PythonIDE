; Bug: no 'sub rsp, 40' before calling printf: RSP is not aligned and there is no shadow space.
default rel
global main
extern printf

section .data
    fmt db "hi", 10, 0

section .text
main:
    lea rcx, [fmt]
    call printf                 ; EXPECT: sim.misaligned_call sim.no_shadow_space
    xor eax, eax
    ret
