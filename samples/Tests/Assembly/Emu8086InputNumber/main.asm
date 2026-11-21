; InputNumber - read a decimal number digit by digit, then print it doubled and in binary.
; Shows macros: PRINT_STR prints a $-string, NEWLINE moves to the next line.

PRINT_STR macro text
    push ax
    push dx
    mov dx, offset text
    mov ah, 09h
    int 21h
    pop dx
    pop ax
endm

NEWLINE macro
    mov dl, 13
    mov ah, 02h
    int 21h
    mov dl, 10
    int 21h
endm

org 100h

    PRINT_STR ask
    xor bx, bx                  ; BX = the number
read_digit:
    mov ah, 01h                 ; read a key with echo -> AL
    int 21h
    cmp al, 13                  ; Enter ends the number
    je got_number
    cmp al, '0'
    jb read_digit               ; ignore keys that are not digits
    cmp al, '9'
    ja read_digit
    sub al, '0'
    mov ah, 0
    push ax
    mov ax, bx                  ; BX = BX * 10 + digit
    mov cx, 10
    mul cx
    mov bx, ax
    pop ax
    add bx, ax
    jmp read_digit

got_number:
    NEWLINE
    PRINT_STR twice
    mov ax, bx
    shl ax, 1                   ; multiply by 2
    call print_unsigned
    NEWLINE
    PRINT_STR binary
    mov cx, 16
next_bit:
    shl bx, 1                   ; the top bit goes into CF
    mov dl, '0'
    adc dl, 0                   ; '0' + CF
    mov ah, 02h
    int 21h
    loop next_bit
    NEWLINE
    ret                         ; a COM program may end with RET (back to INT 20h in the PSP)

print_unsigned proc
    mov si, 10
    xor cx, cx
pu_div:
    xor dx, dx
    div si
    push dx
    inc cx
    or ax, ax
    jnz pu_div
pu_out:
    pop dx
    add dl, '0'
    mov ah, 02h
    int 21h
    loop pu_out
    ret
print_unsigned endp

ask    db 'Enter a number (0-32767): $'
twice  db 'Twice  = $'
binary db 'Binary = $'
