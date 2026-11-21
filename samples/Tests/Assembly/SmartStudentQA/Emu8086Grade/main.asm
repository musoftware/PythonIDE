; Student program 4: read a grade digit and print pass/fail (emu8086 style)
.model small
.stack 100h
.data
    ask   db "Enter grade (0-9): $"
    pass  db 13, 10, "Pass"
    fail  db 13, 10, "Fail$"
.code
main proc
    mov dx, offset ask
    mov ah, 9
    int 21h
    mov ah, 1
    int 21h
    cmp al, '5'
    jae ok
    mov dx, offset fail
    mov ah, 9
    int 21h
    jmp done
ok:
    mov dx, offset pass
    mov ah, 9
    int 21h
done:
    mov [bx], 0
main endp
end main
