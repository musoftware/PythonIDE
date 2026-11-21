; StringReverse - read a line with DOS function 0Ah and print it backwards.
; Full segment definitions (the classic MASM / TASM style).

data segment
    prompt  db 'Type a word and press Enter: $'
    result  db 13, 10, 'Reversed: $'
    buffer  db 40               ; byte 0: maximum length (with the Enter)
            db ?                ; byte 1: DOS stores the count here
            db 40 dup(?)        ; the characters
data ends

stack segment stack
    dw 64 dup(?)
stack ends

code segment
    assume cs:code, ds:data, ss:stack
start:
    mov ax, data
    mov ds, ax

    lea dx, prompt
    mov ah, 09h
    int 21h

    lea dx, buffer              ; buffered keyboard input
    mov ah, 0Ah
    int 21h

    lea dx, result
    mov ah, 09h
    int 21h

    mov cl, buffer[1]           ; number of characters typed
    xor ch, ch
    jcxz done
    lea si, buffer + 2
    add si, cx
    dec si                      ; SI -> the last character
print_back:
    mov dl, [si]
    mov ah, 02h
    int 21h
    dec si
    loop print_back
done:
    mov ax, 4C00h
    int 21h
code ends
end start
