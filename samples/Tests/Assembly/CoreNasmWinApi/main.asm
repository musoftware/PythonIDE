; CoreNasmWinApi - calling the Win32 API from x64 assembly (NASM): two message boxes.
; Ctrl+F5 runs it. The Win32 functions use the same x64 convention as C: RCX, RDX, R8, R9 + shadow space.
default rel

global main
extern MessageBoxA, MessageBeep, printf     ; user32.dll / msvcrt

MB_OK               equ 0x00
MB_YESNO            equ 0x04
MB_ICONQUESTION     equ 0x20
MB_ICONINFORMATION  equ 0x40
IDYES               equ 6

section .data
    caption     db "CoreNasmWinApi", 0
    question    db "Do you like assembly language?", 0
    said_yes    db "Great! The CPU likes you too.", 0
    said_no     db "Give it a chance: every program ends up as machine code.", 0
    fmt_answer  db "MessageBoxA returned %d", 10, 0

section .text
main:
    push rbp
    mov rbp, rsp
    push rbx                        ; RBX is kept by the functions we call: it holds the answer
    sub rsp, 40                     ; shadow space (32) + 8 to keep RSP 16-byte aligned

    xor ecx, ecx                    ; MessageBoxA(NULL, question, caption, MB_YESNO | MB_ICONQUESTION)
    lea rdx, [question]
    lea r8, [caption]
    mov r9d, MB_YESNO | MB_ICONQUESTION
    call MessageBoxA
    mov ebx, eax

    lea rcx, [fmt_answer]           ; printf("... %d", answer)
    mov edx, ebx
    call printf

    mov ecx, MB_ICONINFORMATION     ; MessageBeep(MB_ICONINFORMATION)
    call MessageBeep

    lea rdx, [said_no]              ; text = (answer == IDYES) ? said_yes : said_no
    lea rax, [said_yes]
    cmp ebx, IDYES
    cmove rdx, rax
    xor ecx, ecx
    lea r8, [caption]
    mov r9d, MB_OK | MB_ICONINFORMATION
    call MessageBoxA

    xor eax, eax
    add rsp, 40
    pop rbx
    pop rbp
    ret
