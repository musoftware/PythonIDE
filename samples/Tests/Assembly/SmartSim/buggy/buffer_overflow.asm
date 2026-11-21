; Bug: the loop writes 12 bytes into an 8-byte buffer and destroys 'limit' after it.
default rel
global main
extern printf

section .data
    buf   times 8 db 0
    limit dd 1000
    fmt   db "limit = %d", 10, 0

section .bss
    result resb 4

section .text
main:
    sub rsp, 40
    lea rdi, [buf]
    xor ecx, ecx
.fill:
    mov byte [rdi + rcx], 'A'   ; EXPECT: sim.buffer_overflow
    inc ecx
    cmp ecx, 12
    jb .fill
    lea rcx, [fmt]
    mov edx, [limit]
    call printf
    xor eax, eax
    add rsp, 40
    ret
