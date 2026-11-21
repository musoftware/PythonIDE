; Correct 8086 program: a procedure that saves and restores its registers, array sum in bounds.
org 100h
    lea si, arr
    mov cx, 5
    call sum
    mov total, ax
    mov ah, 4Ch
    int 21h

sum proc                        ; si = array, cx = count -> ax = sum
    push si
    push cx
    xor ax, ax
next:
    add ax, [si]
    add si, 2
    loop next
    pop cx
    pop si
    ret
sum endp

arr   dw 10, 20, 30, 40, 50
total dw 0
