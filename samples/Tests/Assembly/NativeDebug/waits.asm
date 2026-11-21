; waits.asm - waits for Enter, then counts (NASM, Windows x64).
; Used by the native debugger test to attach gdb to a running assembly program (like a GUI Bridge
; program is debugged): the breakpoint on the "add" line is set through the .asm line table.
default rel
global main
extern getchar
extern printf

section .data
fmt     db "n = %d", 10, 0

section .text
main:
    sub  rsp, 40
    call getchar                   ; the test attaches while the program waits here
    mov  rcx, 3
    xor  rax, rax
.again:
    add  rax, rcx                  ; breakpoint: rax = 3, 5, 6
    dec  rcx
    jnz  .again
    lea  rcx, [fmt]
    mov  rdx, rax
    call printf
    xor  eax, eax
    add  rsp, 40
    ret
