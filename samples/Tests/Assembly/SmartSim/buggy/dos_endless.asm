; Bug (8086): CX is reloaded inside the loop, so it never reaches 0.
org 100h
again:
    mov cx, 5
    dec cx
    jnz again                   ; EXPECT: sim.infinite_loop
    mov ah, 4Ch
    int 21h
