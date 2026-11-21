; Nasm32Loose - a loose 32-bit NASM program (no project file). RAD IDE assembles it with nasm -f win32 and links
; it with GNU ld -m i386pe straight against msvcrt.dll / kernel32.dll (the MinGW-w64 gcc has no 32-bit libraries).
bits 32
global _main
extern _printf, _GetTickCount@0

section .data
    fmt db "NASM 32-bit loose folder: 6 * 7 = %d", 10, 0

section .text
_main:
    call _GetTickCount@0            ; stdcall: the callee removes its arguments (none here)
    mov eax, 6
    imul eax, eax, 7
    push eax                        ; cdecl: arguments pushed right to left ...
    push fmt
    call _printf
    add esp, 8                      ; ... and removed by the caller
    xor eax, eax
    ret
