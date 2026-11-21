; Correct: show() ends with a tail call (jmp puts) - puts returns straight to show's caller.
default rel
global main
extern puts

section .data
    msg db "tail call", 0

section .text
show:
    lea rcx, [msg]
    jmp puts

main:
    sub rsp, 40
    call show
    xor eax, eax
    add rsp, 40
    ret
