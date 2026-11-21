; Bug (8086): the procedure pushes AX and returns without popping it.
org 100h
    call show
    mov ah, 4Ch
    int 21h
show proc
    push ax
    mov dl, 'A'
    mov ah, 2
    int 21h
    ret                         ; EXPECT: sim.stack_imbalance
show endp
