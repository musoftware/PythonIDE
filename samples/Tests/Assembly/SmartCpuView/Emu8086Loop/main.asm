; Emu8086Loop - the 8086 emulator under the CPU view: a loop, a procedure call and a string.
.model small
.stack 100h

.data
values  dw 10, 20, 30, 40
count   equ 4
total   dw ?
msg     db 'Total = $'

.code
main proc
    mov ax, @data
    mov ds, ax

    xor ax, ax                  ; AX = running total
    mov cx, count
    mov si, offset values
add_next:
    add ax, [si]
    add si, 2
    loop add_next               ; CX = CX - 1, jump while CX <> 0
    mov total, ax
    call show
    mov ax, 4C00h
    int 21h
main endp

show proc
    mov ah, 09h
    mov dx, offset msg
    int 21h
    ret
show endp

end main
