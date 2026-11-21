; RADMOUSE.COM - resident scripted mouse for captured runs: a stand-in INT 33h driver that clicks the left button
; at the text cells given on the command line, then saves the text screen and types Esc keys.
;
;   RADMOUSE 12,5 30,7       click at column 12 row 5, then at column 30 row 7 (0-based text cells)
;
; INT 33h AX=0 (reset) answers "mouse present, 2 buttons"; AX=1 / 2 (show / hide) draw nothing, so the saved
; screen holds no pointer; AX=3 (status) is the script: for every click the pointer waits WAITP polls over the
; cell, the button is down for DOWNP polls, then up. WAITP polls after the last click the text screen
; (B800:0000, columns from 40:4A, rows from 40:84 + 1) is written to C:\_MOUSE.BIN and four Esc keys are put
; into the keyboard buffer (INT 16h AH=05h) so that the program can end.  AX=0Ch (event handler, used by Free
; Pascal's Mouse unit) is kept and called on the same changes (moved / left down / left up) during AX=3 polls.
; Every other function is ignored.
; Written for RAD IDE (original code). Build: jwasm -bin -Fo=RADMOUSE.COM RADMOUSE.ASM
        .model tiny
        .8086
        .code
        org 100h
start:  jmp install

WAITP   equ 40
DOWNP   equ 4
MAXC    equ 16

nclick  dw 0
idx     dw 0
cnt     dw 0
done    db 0
curx    dw 0
cury    dw 0
clicks  dw MAXC * 2 dup (0)
fname   db 'C:\_MOUSE.BIN', 0
hmask   dw 0                        ; AX=0Ch event mask and handler
hproc   dd 0
lastb   dw 0
lastx   dw 0FFFFh
lasty   dw 0FFFFh

new33:  cmp ax, 0
        jne n_1
        mov ax, 0FFFFh              ; reset: driver present, two buttons
        mov bx, 2
        iret
n_1:    cmp ax, 3
        je status
        cmp ax, 0Ch
        jne n_ret
        mov cs:hmask, cx            ; set the event handler (mask 0 = none)
        mov word ptr cs:hproc, dx
        mov word ptr cs:hproc + 2, es
n_ret:  iret                        ; show / hide / anything else: nothing to do

status: push ax
        push si
        push ds
        push cs
        pop ds
        xor bx, bx                  ; buttons up
        mov si, idx
        cmp si, nclick
        jae after
        shl si, 1
        shl si, 1
        mov ax, clicks[si]
        mov curx, ax
        mov ax, clicks[si + 2]
        mov cury, ax
        inc cnt
        cmp cnt, WAITP
        jbe s_pos
        cmp cnt, WAITP + DOWNP
        ja s_next
        mov bx, 1                   ; left button down
        jmp s_pos
s_next: inc idx
        mov cnt, 0
        jmp s_pos
after:  cmp done, 0
        jne s_pos
        inc cnt
        cmp cnt, WAITP
        jb s_pos
        mov done, 1
        call dump
s_pos:  mov cx, curx                ; text cell -> pixel coordinates (8 x 8 cells)
        shl cx, 1
        shl cx, 1
        shl cx, 1
        mov dx, cury
        shl dx, 1
        shl dx, 1
        shl dx, 1
        call event
        pop ds
        pop si
        pop ax
        iret

; ---- BX buttons, CX / DX pixels: call the AX=0Ch handler for what changed since the last poll (DS = CS)
event:  push ax
        xor ax, ax
        cmp cx, lastx
        jne ev_mv
        cmp dx, lasty
        je ev_btn
ev_mv:  or ax, 1                    ; moved
ev_btn: cmp bx, lastb
        je ev_go
        or ax, 4                    ; left up
        test bx, 1
        jz ev_go
        xor ax, 6                   ; left down
ev_go:  mov lastb, bx
        mov lastx, cx
        mov lasty, dx
        and ax, hmask
        jz ev_ret
        push bx
        push cx
        push dx
        push si
        push di
        push bp
        push ds
        push es
        xor si, si
        xor di, di
        call dword ptr hproc
        pop es
        pop ds
        pop bp
        pop di
        pop si
        pop dx
        pop cx
        pop bx
ev_ret: pop ax
        ret

dump:   push ax
        push bx
        push cx
        push dx
        push ds
        mov ax, 40h
        mov ds, ax
        mov ax, ds:[4Ah]            ; columns
        mov cl, ds:[84h]            ; rows - 1 (EGA / VGA BIOS)
        xor ch, ch
        inc cx
        cmp cx, 60
        jbe d_rows
        mov cx, 25
d_rows: mul cx
        shl ax, 1
        push ax                     ; bytes to write
        push cs
        pop ds
        mov ah, 3Ch
        xor cx, cx
        mov dx, offset fname
        int 21h
        pop cx
        jc d_keys
        mov bx, ax
        push ds
        mov ax, 0B800h
        mov ds, ax
        xor dx, dx
        mov ah, 40h
        int 21h
        pop ds
        mov ah, 3Eh
        int 21h
d_keys: mov si, 4
k_lp:   mov ah, 05h
        mov cx, 011Bh               ; Esc
        int 16h
        dec si
        jnz k_lp
        pop ds
        pop dx
        pop cx
        pop bx
        pop ax
        ret

; ---- transient part: read "col,row col,row ..." from the command tail, hook INT 33h, stay resident
number: xor ax, ax                  ; DS:SI -> AX = decimal number, SI after it
nb_lp:  mov bl, [si]
        cmp bl, '0'
        jb nb_end
        cmp bl, '9'
        ja nb_end
        sub bl, '0'
        xor bh, bh
        mov dx, 10
        mul dx
        add ax, bx
        inc si
        jmp nb_lp
nb_end: ret

install:
        mov si, 81h
        mov di, offset clicks
p_skip: mov al, [si]
        cmp al, 0Dh
        je p_done
        cmp al, '0'
        jb p_nxt
        cmp al, '9'
        ja p_nxt
        cmp nclick, MAXC
        jae p_done
        call number
        mov [di], ax
        cmp byte ptr [si], ','
        jne p_done
        inc si
        call number
        mov [di + 2], ax
        add di, 4
        inc nclick
        jmp p_skip
p_nxt:  inc si
        jmp p_skip
p_done: mov ax, 2533h
        mov dx, offset new33
        int 21h
        mov dx, offset number + 15  ; keep everything up to here resident
        mov cl, 4
        shr dx, cl
        mov ax, 3100h
        int 21h
        end start
