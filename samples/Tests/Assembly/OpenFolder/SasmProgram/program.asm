; SasmProgram - a program written in the style of the SASM IDE: its io64.inc macros (PRINT_STRING, NEWLINE ...)
; come with SASM; RAD IDE adds SASM's include folder when SASM is installed.
%include "io64.inc"

section .data
    msg db "SASM style program", 0

section .text
global CMAIN
CMAIN:
    mov rbp, rsp
    PRINT_STRING msg
    NEWLINE
    xor rax, rax
    ret
