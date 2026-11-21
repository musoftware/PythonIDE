; Colors - the 80x25 colour text screen: INT 10h services and direct writes to video memory (B800:0000).
org 100h

    mov ax, 0003h               ; video mode 3: 80x25, 16 colours (also clears the screen)
    int 10h

    ; a blue window with INT 10h function 06h (scroll up = clear a rectangle)
    mov ax, 0600h
    mov bh, 1Fh                 ; white on blue
    mov cx, 0205h               ; top-left: row 2, column 5
    mov dx, 0A40h               ; bottom-right: row 10, column 64
    int 10h

    ; a title with INT 10h function 13h (write string ES:BP)
    mov ax, 1300h
    mov bx, 001Eh               ; page 0, yellow on blue
    mov cx, title_len
    mov dx, 0310h               ; row 3, column 16
    push cs
    pop es
    mov bp, offset title_
    int 10h

    ; the 16 foreground colours, written straight into the video memory
    mov ax, 0B800h
    mov es, ax
    mov di, (6 * 80 + 8) * 2    ; row 6, column 8 (2 bytes per cell)
    mov cx, 16
    mov ah, 10h                 ; attribute: blue background, colour 0
    mov al, 'A'
paint:
    stosw                       ; [ES:DI] = AX (character + attribute), DI += 2
    mov byte ptr es:[di], ' '
    inc di
    mov es:[di], ah
    inc di
    inc ah
    inc al
    loop paint

    mov ah, 02h                 ; park the cursor below the window
    mov bh, 0
    mov dx, 0C00h
    int 10h
    mov ax, 4C00h
    int 21h

title_     db 'Text mode colours on the 8086'
title_len  equ $ - title_
