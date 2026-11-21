# GasLoose - a GNU as program in AT&T syntax (built by gcc).
    .globl main
    .data
fmt:
    .asciz "GNU as loose folder: %d\n"
    .text
main:
    subq $40, %rsp
    leaq fmt(%rip), %rcx
    movl $2026, %edx
    call printf
    xorl %eax, %eax
    addq $40, %rsp
    ret
