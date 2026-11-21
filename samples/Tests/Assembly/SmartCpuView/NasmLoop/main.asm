; NasmLoop - a small x64 Windows console program for the CPU view (OllyDbg style) and the live editor.
; Debug it with F5: the CPU view (Debug > Windows > CPU, Alt+C) shows the disassembly with jump arrows,
; the registers (flags as clickable bits), the dump and the stack. In the editor: jump arrows in the gutter,
; inline values after each executed line, a hover with the live value of a register.
default rel
global main
extern printf

section .data
greeting    db "Sum of the table", 0
fmt         db "%s = %lld (r9 = %lld)", 10, 0
table       dq 3, 5, 7, 9
count       equ 4

section .bss
total       resq 1

section .text
main:
    sub  rsp, 40                    ; shadow space + alignment (Windows x64)
    xor  eax, eax                   ; rax = running total
    lea  rbx, [table]               ; rbx -> current number
    mov  ecx, count                 ; rcx = numbers left
.next:
    add  rax, [rbx]                 ; total += *rbx
    add  rbx, 8
    dec  rcx
    jnz  .next                      ; loop while numbers are left
    mov  [total], rax
    mov  r9, 0                      ; the CPU view test assembles "mov r9, 1" here
    call show
    xor  eax, eax
    add  rsp, 40
    ret

show:                               ; printf(fmt, greeting, total, r9)
    sub  rsp, 40
    lea  rcx, [fmt]
    lea  rdx, [greeting]
    mov  r8, [total]
    call printf
    add  rsp, 40
    ret
