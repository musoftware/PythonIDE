; RADSCR.COM - save the current screen to the root of drive C:
;   text modes 0-3 and 7  -> C:\_SCREEN.TXT  (one line per screen row, trailing spaces removed, CP437)
;   mode 13h (320x200x256) -> C:\_SCR13.RAW  (64000 pixel bytes + 768 palette bytes, 6-bit VGA DAC values)
; Written for RAD IDE (original code). Build: jwasm -bin -Fo=RADSCR.COM RADSCR.ASM
        .model tiny
        .8086
        .code
        org 100h
start:  mov ax, 40h                 ; BIOS data area
        mov es, ax
        mov al, es:[49h]            ; current video mode
        mov vmode, al
        mov ax, es:[4Ah]            ; columns
        mov cols, ax
        mov al, es:[84h]            ; rows - 1 (EGA / VGA BIOS)
        or al, al
        jnz r_ok
        mov al, 24
r_ok:   inc al
        mov rows, al
        cmp vmode, 13h
        je gfx
        cmp vmode, 7
        je mono
        cmp vmode, 3
        ja quit
        mov dx, 0B800h
        jmp short txt
mono:   mov dx, 0B000h
txt:    mov si, es:[4Eh]            ; start of the visible page
        mov es, dx
        mov di, offset buf
        mov bl, rows
row_lp: mov cx, cols
        mov bp, di                  ; first byte of this row in buf
col_lp: mov al, es:[si]
        add si, 2
        mov [di], al
        inc di
        loop col_lp
trim:   cmp di, bp
        je trimmed
        mov al, [di-1]
        cmp al, ' '
        je tr_dec
        or al, al
        jnz trimmed
tr_dec: dec di
        jmp trim
trimmed:
        mov word ptr [di], 0A0Dh
        add di, 2
        dec bl
        jnz row_lp
        mov cx, di
        sub cx, offset buf
        mov ah, 3Ch                 ; create C:\_SCREEN.TXT
        push cx
        xor cx, cx
        mov dx, offset fn_txt
        int 21h
        pop cx
        jc quit
        mov bx, ax
        mov ah, 40h
        mov dx, offset buf
        int 21h
        mov ah, 3Eh
        int 21h
        jmp short quit

gfx:    mov dx, 3C7h                ; read the VGA palette from colour 0
        xor al, al
        out dx, al
        mov dx, 3C9h
        mov di, offset pal
        mov cx, 768
pal_lp: in al, dx
        mov [di], al
        inc di
        loop pal_lp
        mov ah, 3Ch
        xor cx, cx
        mov dx, offset fn_gfx
        int 21h
        jc quit
        mov bx, ax
        push ds
        mov ax, 0A000h
        mov ds, ax
        xor dx, dx
        mov cx, 64000
        mov ah, 40h
        int 21h
        pop ds
        mov ah, 40h
        mov cx, 768
        mov dx, offset pal
        int 21h
        mov ah, 3Eh
        int 21h
quit:   mov ax, 4C00h
        int 21h

fn_txt  db 'C:\_SCREEN.TXT', 0
fn_gfx  db 'C:\_SCR13.RAW', 0
vmode   db 0
rows    db 0
cols    dw 0
pal     label byte                  ; 768 bytes, then the text buffer (free memory of the COM segment)
buf     equ pal + 768
        end start
