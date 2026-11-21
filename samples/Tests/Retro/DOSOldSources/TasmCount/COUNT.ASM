; COUNT.ASM - MASM / TASM style 16-bit DOS program: DOSSEG, .MODEL SMALL, a counting loop
; (original RAD IDE sample)
        DOSSEG
        .MODEL SMALL
        .STACK 100h
        .DATA
Title_  DB 'Counting from 0 to 9: $'
Done_   DB 13, 10, 'Done.', 13, 10, '$'
        .CODE
Start:  mov ax, @data
        mov ds, ax
        mov ah, 9
        mov dx, OFFSET Title_
        int 21h
        mov cx, 10
        mov dl, '0'
Again:  mov ah, 2
        int 21h
        inc dl
        loop Again
        mov ah, 9
        mov dx, OFFSET Done_
        int 21h
        mov ax, 4C00h
        int 21h
        END Start
