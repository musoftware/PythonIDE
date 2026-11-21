; Hello - the first 8086 program: a COM file printed with DOS INT 21h.
; F5: the emulator opens paused on the first line. Press F10 and watch AH / DX change.

org 100h                        ; COM programs start at offset 100h

start:
    mov ah, 09h                 ; DOS function 09h: print a string that ends with '$'
    mov dx, offset greeting     ; DS:DX = the address of the string
    int 21h

    mov cx, 3                   ; print three stars with function 02h (character in DL)
stars:
    mov dl, '*'
    mov ah, 02h
    int 21h
    loop stars                  ; CX = CX - 1, jump while CX <> 0

    mov ah, 4Ch                 ; exit to DOS, exit code in AL
    mov al, 0
    int 21h

greeting db 'Hello, 8086 world!', 13, 10, '$'
