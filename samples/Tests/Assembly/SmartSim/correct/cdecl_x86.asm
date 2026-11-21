; Correct 32-bit program: cdecl calls clean their arguments, stdcall ExitProcess ends the program.
global _main
extern _printf, _ExitProcess@4

section .data
    fmt db "%d * %d = %d", 10, 0

section .text
_square:                        ; int square(int x)  (cdecl)
    push ebp
    mov ebp, esp
    mov eax, [ebp+8]
    imul eax, eax
    pop ebp
    ret

_main:
    push 12
    call _square
    add esp, 4
    push eax
    push 12
    push 12
    push fmt
    call _printf
    add esp, 16
    push 0
    call _ExitProcess@4
