# sum_gas.s - the same sum in GNU assembler (Intel syntax); "gcc -g" gives DWARF line information,
# so gdb sets the breakpoints of this file itself (no line table needed).
        .intel_syntax noprefix
        .data
values: .quad 11, 22, 33, 44
fmt:    .asciz "Sum = %d\n"
        .text
        .globl main
main:
        sub  rsp, 40
        xor  rax, rax
        lea  rbx, [rip + values]
        mov  rcx, 4
next:
        add  rax, [rbx]
        add  rbx, 8
        dec  rcx
        jnz  next
        lea  rcx, [rip + fmt]
        mov  rdx, rax
        call printf
        xor  eax, eax
        add  rsp, 40
        ret
