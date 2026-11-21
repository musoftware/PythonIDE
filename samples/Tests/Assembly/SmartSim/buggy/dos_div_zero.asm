; Bug (8086): divide by a zero variable.
org 100h
    mov ax, 50
    mov bl, [zero]
    div bl                      ; EXPECT: sim.div_zero
    mov ah, 4Ch
    int 21h
zero db 0
