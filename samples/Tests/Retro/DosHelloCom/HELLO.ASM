; HELLO.ASM - an 8086 .COM program for DOS (original sample, CC0)
; RAD IDE: F5 assembles it with NASM on Windows and runs HELLO.COM in DOSBox-X.
        org 100h

start:  mov ah, 09h             ; DOS: print the $-terminated string at DS:DX
        mov dx, msg
        int 21h
        mov cx, 8               ; draw a row of coloured blocks with BIOS teletype
        mov bl, 1
row:    mov ah, 0Eh
        mov al, 0DBh            ; full block character
        int 10h
        inc bl
        loop row
        mov ah, 09h
        mov dx, bye
        int 21h
        mov ah, 00h             ; BIOS: wait for a key
        int 16h
        mov ax, 4C00h           ; DOS: exit with code 0
        int 21h

msg     db 'Hello from RAD IDE in DOSBox-X!', 13, 10, '$'
bye     db 13, 10, 'Press a key...', 13, 10, '$'
