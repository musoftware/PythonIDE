# CoreGasIntel - an x64 Windows console program for the GNU assembler in Intel syntax
# (.intel_syntax noprefix: destination first, no % or $ - the same order as NASM and MASM).
# Ctrl+F5 runs it, F5 debugs it (gdb understands the line information that  as -g  writes).
        .intel_syntax noprefix
        .data
hello:      .asciz "Hello from GNU as (Intel syntax)!"
ask:        .asciz "Enter a number: "
fmt_in:     .asciz "%lld"
fmt_out:    .asciz "%lld - 1 = %lld\n"
fmt_pc:     .asciz "This computer is called %s\n"
        .p2align 3
number:     .quad 0
pc_size:    .long 64
pc_name:    .space 64

        .text
        .globl main
main:
        push    rbp
        mov     rbp, rsp
        sub     rsp, 32                 # shadow space

        lea     rcx, [rip + hello]
        call    puts

        lea     rcx, [rip + ask]
        call    printf
        xor     ecx, ecx
        call    fflush

        lea     rcx, [rip + fmt_in]
        lea     rdx, [rip + number]
        call    scanf

        mov     rdx, [rip + number]
        lea     r8, [rdx - 1]
        lea     rcx, [rip + fmt_out]
        call    printf

        lea     rcx, [rip + pc_name]
        lea     rdx, [rip + pc_size]
        call    GetComputerNameA
        lea     rcx, [rip + fmt_pc]
        lea     rdx, [rip + pc_name]
        call    printf

        xor     eax, eax
        leave
        ret
