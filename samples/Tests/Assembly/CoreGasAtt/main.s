# CoreGasAtt - an x64 Windows console program written for the GNU assembler (AT&T syntax).
# AT&T syntax: the source comes first, the destination last (movq %rax, %rbx copies RAX into RBX), registers
# start with %, constants with $, and the size is in the mnemonic (movq = 64 bits, movl = 32 bits).
# x64 Windows convention: arguments in %rcx, %rdx, %r8, %r9, 32 bytes of shadow space, %rsp 16-byte aligned.
# Ctrl+F5 runs it, F5 debugs it (gdb understands the line information that  as -g  writes).
        .data
hello:      .asciz "Hello from GNU as!"
ask:        .asciz "Enter a number: "
fmt_in:     .asciz "%lld"
fmt_out:    .asciz "%lld + 100 = %lld\n"
fmt_pc:     .asciz "This computer is called %s\n"
        .p2align 3
number:     .quad 0
pc_size:    .long 64
pc_name:    .space 64

        .text
        .globl main
main:
        pushq   %rbp
        movq    %rsp, %rbp
        subq    $32, %rsp               # shadow space

        leaq    hello(%rip), %rcx       # puts(hello)
        call    puts

        leaq    ask(%rip), %rcx         # printf(ask); fflush(NULL)
        call    printf
        xorl    %ecx, %ecx
        call    fflush

        leaq    fmt_in(%rip), %rcx      # scanf("%lld", &number)
        leaq    number(%rip), %rdx
        call    scanf

        movq    number(%rip), %rdx      # printf(fmt_out, number, number + 100)
        leaq    100(%rdx), %r8
        leaq    fmt_out(%rip), %rcx
        call    printf

        leaq    pc_name(%rip), %rcx     # GetComputerNameA(pc_name, &pc_size)
        leaq    pc_size(%rip), %rdx
        call    GetComputerNameA
        leaq    fmt_pc(%rip), %rcx
        leaq    pc_name(%rip), %rdx
        call    printf

        xorl    %eax, %eax
        leave
        ret
