; NasmMistakes - a program full of typical beginner mistakes. Open it in RAD IDE and watch the editor explain
; each one (hover the squiggles, press Ctrl+. for a quick fix, View > Problems Explained for the details).
; Every line marked "MISTAKE" is found by the assembly analyzer (radide/asm_lint).
default rel
global main
extern printf

section .data
    fmt     db "sum = %d", 10, 0
    numbers dd 10, 20, 30, 40
    count   dd 4

section .text
main:
    sub rsp, 40

    mov eax, bl                 ; MISTAKE ASM101: 32-bit register and 8-bit register
    mov [count], 4              ; MISTAKE ASM102: dword? word? byte?

    xor eax, eax
    mov ecx, [count]
    lea rbx, [numbers]
.next:
    add eax, [rbx]
    add rbx, 4
    loop .next

    mov ecx, 3
    div ecx                     ; MISTAKE ASM403: EDX holds argv, not part of the number

    mov ecx, 5
    lea rcx, [fmt]
    mov edx, eax
    call printf
    mov eax, ecx                ; MISTAKE ASM402: printf changed RCX

    mov eax, [count]
    jz .done                    ; MISTAKE ASM307: MOV does not set the flags
    jmp .done
    mov eax, 1                  ; MISTAKE ASM301: never runs
.done:
    xor eax, eax
    add rsp, 40
    ret
