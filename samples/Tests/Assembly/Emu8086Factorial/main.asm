; Factorial - a recursive procedure: parameters and results on the stack with BP.
; Step Into (F11) the CALL and watch the Stack view grow, then Step Out (Shift+F11).
.model small
.stack 200h

.data
n       dw 7
result  dw ?
msg1    db '7! = $'

.code
main proc
    mov ax, @data
    mov ds, ax

    push n                      ; argument
    call factorial              ; AX = n!
    add sp, 2                   ; remove the argument
    mov result, ax

    lea dx, msg1
    mov ah, 09h
    int 21h
    mov ax, result
    call print_ax

    mov ax, 4C00h
    int 21h
main endp

; factorial(n) - the argument is at [bp+4]
factorial proc
    push bp
    mov bp, sp
    mov ax, [bp+4]
    cmp ax, 1
    jbe fact_one
    dec ax
    push ax
    call factorial              ; AX = (n-1)!
    add sp, 2
    mul word ptr [bp+4]         ; DX:AX = AX * n
    jmp fact_done
fact_one:
    mov ax, 1
fact_done:
    pop bp
    ret
factorial endp

print_ax proc
    mov bx, 10
    xor cx, cx
p_div:
    xor dx, dx
    div bx
    push dx
    inc cx
    cmp ax, 0
    jne p_div
p_out:
    pop dx
    add dl, 30h
    mov ah, 02h
    int 21h
    loop p_out
    ret
print_ax endp

end main
