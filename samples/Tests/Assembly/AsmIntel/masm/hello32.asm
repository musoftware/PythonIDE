; hello32.asm - MASM 32-bit (ml /c /coff hello32.asm, link /subsystem:windows).
; RAD IDE IntelliSense test: PROC / ENDP, PROTO, INVOKE, LOCAL, STRUCT, high-level .IF.

.386
.model flat, stdcall
option casemap:none

includelib kernel32.lib
includelib user32.lib

ExitProcess PROTO :DWORD
MessageBoxA PROTO :DWORD, :DWORD, :DWORD, :DWORD

MB_OK       equ 0
MAX_TRIES   = 3

RECT2 STRUCT
    left    DWORD ?
    top     DWORD ?
RECT2 ENDS

.data
    szTitle     BYTE "RAD IDE", 0
    szText      BYTE "Hello from MASM!", 0
    counter     DWORD 0
    area        RECT2 <>

.code
; Adds two numbers: returns a + b in EAX.
AddTwo PROC a:DWORD, b:DWORD
    mov     eax, a
    add     eax, b
    ret
AddTwo ENDP

start:
    invoke  AddTwo, 2, 3
    mov     counter, eax
    .if counter == 5
        invoke  MessageBoxA, 0, addr szText, addr szTitle, MB_OK
    .endif
    call    ShowTwice
    invoke  ExitProcess, 0

ShowTwice PROC uses ebx
    LOCAL tries:DWORD
    mov     tries, 0
again:
    invoke  MessageBoxA, 0, offset szText, offset szTitle, MB_OK
    inc     tries
    cmp     tries, 2
    jb      again
    ret
ShowTwice ENDP

END start
