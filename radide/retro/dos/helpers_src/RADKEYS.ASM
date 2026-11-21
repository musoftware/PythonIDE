; RADKEYS.COM - put keys into the BIOS keyboard buffer (INT 16h AH=05h), so that the next program reads them.
; Written for RAD IDE (original code). Build: jwasm -bin -Fo=RADKEYS.COM RADKEYS.ASM
;
; Usage: RADKEYS keys      (at most 15 keys fit in the BIOS buffer; spaces between keys are ignored)
;   |  Enter      `  Esc      _  Space      ^U ^D ^L ^R  arrow keys      any other character: itself
        .model tiny
        .8086
        .code
        org 100h
start:  mov si, 81h
        mov bl, byte ptr ds:[80h]
        xor bh, bh
        lea di, [si+bx]             ; DI = end of the command tail
next:   cmp si, di
        jae done
        lodsb
        cmp al, ' '
        je next
        cmp al, 9
        je next
        cmp al, '|'
        jne n1
        mov cx, 1C0Dh               ; Enter (scan 1Ch, ASCII 0Dh)
        jmp push_key
n1:     cmp al, '`'
        jne n2
        mov cx, 011Bh               ; Esc
        jmp push_key
n2:     cmp al, '_'
        jne n3
        mov cx, 3920h               ; Space
        jmp push_key
n3:     cmp al, '^'
        jne plain
        cmp si, di
        jae done
        lodsb
        and al, 0DFh                ; upper case
        mov cx, 4800h               ; Up
        cmp al, 'U'
        je push_key
        mov cx, 5000h               ; Down
        cmp al, 'D'
        je push_key
        mov cx, 4B00h               ; Left
        cmp al, 'L'
        je push_key
        mov cx, 4D00h               ; Right
        cmp al, 'R'
        je push_key
        jmp next
plain:  mov cl, al
        xor ch, ch
push_key:
        mov ah, 05h                 ; BIOS: store key CH = scan code, CL = ASCII
        int 16h
        jmp next
done:   mov ax, 4C00h
        int 21h
        end start
