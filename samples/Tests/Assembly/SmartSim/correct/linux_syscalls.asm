; Correct Linux x86-64 program (no C library): write + exit system calls.
global _start

section .data
    msg db "Hello from Linux!", 10
    len equ $ - msg

section .text
_start:
    mov eax, 1                  ; sys_write(1, msg, len)
    mov edi, 1
    lea rsi, [rel msg]
    mov edx, len
    syscall
    mov eax, 60                 ; sys_exit(0)
    xor edi, edi
    syscall
