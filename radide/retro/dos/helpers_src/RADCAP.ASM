; RADCAP.COM - resident helper: when a program leaves video mode 13h (INT 10h AH=00h while the current mode is
; 13h), the last 320x200 frame and its palette are written to C:\_SCR13.RAW first (64000 + 768 bytes).
; RAD IDE loads it before a captured run so that a graphics demo can be checked after it returned to text mode.
; Written for RAD IDE (original code). Build: jwasm -bin -Fo=RADCAP.COM RADCAP.ASM
        .model tiny
        .8086
        .code
        org 100h
start:  jmp install

old10   dd 0
busy    db 0
fname   db 'C:\_SCR13.RAW', 0

new10:  cmp ah, 0
        jne chain
        cmp cs:busy, 0
        jne chain
        push ax
        push ds
        mov ax, 40h
        mov ds, ax
        mov al, ds:[49h]
        pop ds
        cmp al, 13h
        pop ax
        jne chain
        call dump
chain:  jmp cs:old10

dump:   mov cs:busy, 1
        push ax
        push bx
        push cx
        push dx
        push di
        push ds
        push cs
        pop ds
        mov dx, 3C7h
        xor al, al
        out dx, al
        mov dx, 3C9h
        mov di, offset palbuf
        mov cx, 768
p_lp:   in al, dx
        mov [di], al
        inc di
        loop p_lp
        mov ah, 3Ch
        xor cx, cx
        mov dx, offset fname
        int 21h
        jc d_done
        mov bx, ax
        push ds
        mov ax, 0A000h
        mov ds, ax
        xor dx, dx
        mov cx, 64000
        mov ah, 40h
        int 21h
        pop ds
        mov ah, 40h
        mov cx, 768
        mov dx, offset palbuf
        int 21h
        mov ah, 3Eh
        int 21h
d_done: pop ds
        pop di
        pop dx
        pop cx
        pop bx
        pop ax
        mov cs:busy, 0
        ret

palbuf  db 768 dup (0)

install:
        mov ax, 3510h               ; old INT 10h vector -> ES:BX
        int 21h
        mov word ptr old10, bx
        mov word ptr old10 + 2, es
        mov ax, 2510h
        mov dx, offset new10
        int 21h
        mov dx, offset install + 15 ; keep everything up to here resident
        mov cl, 4
        shr dx, cl
        mov ax, 3100h
        int 21h
        end start
