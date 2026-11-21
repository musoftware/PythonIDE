; SumArray - add the elements of a word array and print the total (.model small EXE)
.model small
.stack 100h

.data
values  dw 120, 45, 300, 7, 528, 1000
count   equ ($ - values) / 2    ; number of elements, computed by the assembler
total   dw ?
label1  db 'Total = $'

.code
main proc
    mov ax, @data
    mov ds, ax

    xor ax, ax                  ; AX = running total
    mov cx, count
    mov si, offset values
sum_loop:
    add ax, [si]
    add si, 2                   ; next word
    loop sum_loop
    mov total, ax

    mov ah, 09h
    mov dx, offset label1
    int 21h
    mov ax, total
    call print_dec

    mov ax, 4C00h
    int 21h
main endp

; print_dec: print AX as an unsigned decimal number
print_dec proc
    push ax
    push bx
    push cx
    push dx
    mov bx, 10
    xor cx, cx
pd_div:
    xor dx, dx
    div bx                      ; DX:AX / 10 -> AX quotient, DX remainder
    push dx
    inc cx
    test ax, ax
    jnz pd_div
pd_out:
    pop dx
    add dl, '0'
    mov ah, 02h
    int 21h
    loop pd_out
    pop dx
    pop cx
    pop bx
    pop ax
    ret
print_dec endp

end main
