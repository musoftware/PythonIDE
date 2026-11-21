; main.asm - NASM, Windows x64 console + message box.
; IntelliSense test file for RAD IDE (radide/asm_intel): labels, local labels, macros from
; mathlib.inc, Win32 API externs, data, constants and a structure.
;
; Build:  nasm -f win64 main.asm -o main.obj
;         gcc main.obj -o main.exe        (or: link main.obj kernel32.lib user32.lib /entry:main)

bits 64
default rel

%include "mathlib.inc"

extern ExitProcess
extern GetStdHandle
extern WriteConsoleA
extern MessageBoxA

STD_OUTPUT_HANDLE equ -11
MB_ICONINFORMATION equ 40h

struc POINT
    .x  resd 1
    .y  resd 1
endstruc

section .data
    title       db "RAD IDE", 0
    message     db "Hello from NASM!", 0
    line        db "Counting: 0", 13, 10
    line_len    equ $ - line

section .bss
    written     resd 1
    origin      resb POINT_size

section .text
global main

; Program entry point: prints a few lines, shows a message box and exits.
main:
    sub     rsp, 40                 ; shadow space (32) + alignment (8)
    mov     ecx, STD_OUTPUT_HANDLE
    call    GetStdHandle
    mov     rbx, rax                ; console handle
    xor     esi, esi                ; counter
.loop:
    lea     eax, [rsi + '0']
    mov     [line + line_len - 3], al
    mov     rcx, rbx
    lea     rdx, [line]
    mov     r8d, line_len
    lea     r9, [written]
    mov     qword [rsp + 32], 0
    call    WriteConsoleA
    inc     esi
    cmp     esi, 3
    jl      .loop

    SQUARE  eax, esi                ; macro from mathlib.inc
    call    show_message
    xor     ecx, ecx
    call    ExitProcess

; Shows the greeting in a message box.
show_message:
    sub     rsp, 40
    xor     ecx, ecx
    lea     rdx, [message]
    lea     r8, [title]
    mov     r9d, MB_ICONINFORMATION
    call    MessageBoxA
    add     rsp, 40
    ret
