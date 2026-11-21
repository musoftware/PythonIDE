; sum.asm - adds the numbers of a table and prints the total (NASM, Windows x64)
; Used by the native debugger test: breakpoints on .asm lines, instruction stepping,
; the Registers window (rax grows), the Memory window (the bytes of "values").
default rel
global main
extern printf

section .data
msg     db "Sum = %d", 10, 0
values  dq 11, 22, 33, 44          ; four 64-bit numbers: 0B 00 00 00 00 00 00 00 16 ...
count   equ 4

section .bss
total   resq 1

section .text
main:
    sub  rsp, 40                   ; shadow space + alignment (Windows x64 calling convention)
    xor  rax, rax                  ; rax = running total
    lea  rbx, [values]             ; rbx -> current number
    mov  rcx, count
.next:
    add  rax, [rbx]                ; breakpoint here: watch rax grow 11, 33, 66, 110
    add  rbx, 8
    dec  rcx
    jnz  .next
    mov  [total], rax
    lea  rcx, [msg]
    mov  rdx, rax
    call printf
    xor  eax, eax
    add  rsp, 40
    ret
