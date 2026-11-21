; Emu8086Mistakes - classic 8086 / DOS course mistakes. Open the project in RAD IDE: every "MISTAKE" line is
; underlined and explained in Arabic or English (the IDE language), with a quick fix where one exists.
.model small
.stack 100h

.data
msg     db 'Hello, 8086!', 13, 10       ; MISTAKE ASM605: AH=09h prints until a '$'
nums    db 1, 2, 3, 4, 5

.code
start:
    mov ah, 09h                 ; MISTAKE ASM601: DS still points to the PSP
    mov dx, offset msg
    int 21h

    mov cx, 5
    lea si, nums
    xor al, al
again:
    add al, [si]
    inc si
    call show_dot               ; show_dot changes CX ...
    loop again                  ; MISTAKE ASM402: ... so LOOP counts with a wrong CX

    push 7                      ; HINT ASM118: not on a real 8086
    pop bx
    mov al, [ax]                ; MISTAKE ASM106: AX cannot address memory
                                ; MISTAKE ASM602: no exit to DOS (mov ah, 4Ch / int 21h)

show_dot proc
    mov ah, 02h
    mov dl, '.'
    mov cx, 1
    int 21h
    ret
show_dot endp

end start
