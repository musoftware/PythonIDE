; CoreErrorList - a program with mistakes on purpose, to see the Error List of an Assembly project.
; Save the file: line 15 appears in the Error List (NASM syntax check on save).
; Fix line 15 (delete ", 6") and press Ctrl+F5: now the linker reports line 18 - "undefined reference to
; `print_line'" - because print_line is declared extern but defined nowhere. Double-click a row to go there.
default rel
global main
extern puts, print_line

section .data
    msg db "Fix the two mistakes and run me again.", 0

section .text
main:
    sub rsp, 40
    movzx rax, 5, 6                 ; mistake 1: movzx takes two operands, and not an immediate
    lea rcx, [msg]
    call puts
    call print_line                 ; mistake 2: no such function (delete this line)
    xor eax, eax
    add rsp, 40
    ret
