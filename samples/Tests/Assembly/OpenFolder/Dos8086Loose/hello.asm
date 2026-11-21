; Dos8086Loose - a 16-bit DOS .COM program: it runs in RAD IDE's 8086 emulator.
org 100h

    mov ah, 09h
    lea dx, msg
    int 21h
    ret

msg db '8086 loose folder$'
