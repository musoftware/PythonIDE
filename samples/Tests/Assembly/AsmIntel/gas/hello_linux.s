# hello_linux.s - GNU as, AT&T syntax, Linux x86-64 (as hello_linux.s -o h.o && ld h.o -o h)
# RAD IDE IntelliSense test: .macro, .equ, .globl, % registers, $ immediates, local .L labels.

    .equ SYS_WRITE, 1
    .equ SYS_EXIT, 60

    .macro syscall3 num, a, b, c
        movq    $\num, %rax
        movq    \a, %rdi
        movq    \b, %rsi
        movq    \c, %rdx
        syscall
    .endm

    .section .rodata
msg:
    .ascii  "Hello from GAS!\n"
    .equ msg_len, . - msg

    .text
    .globl _start
    .type _start, @function
_start:
    movl    $3, %ebx            # repeat counter
.Lagain:
    syscall3 SYS_WRITE, $1, $msg, $msg_len
    decl    %ebx
    jnz     .Lagain
    call    finish

finish:
    movq    $SYS_EXIT, %rax
    xorq    %rdi, %rdi
    syscall
