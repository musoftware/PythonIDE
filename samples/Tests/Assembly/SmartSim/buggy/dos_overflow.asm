; Bug (8086): 6 bytes are written into a 4-byte array and 'total' is damaged.
org 100h
    lea si, arr
    mov cx, 6
fill:
    mov byte ptr [si], 1        ; EXPECT: sim.buffer_overflow
    inc si
    loop fill
    mov ah, 4Ch
    int 21h
arr   db 4 dup(0)
total dw 1234
