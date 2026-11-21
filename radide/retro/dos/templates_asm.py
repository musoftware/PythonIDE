"""DOS Assembly templates (16-bit MASM syntax, JWasm -> MZ .EXE or .COM). Original RAD IDE code."""

HELLO = """; {name} - 16-bit DOS assembly, MASM syntax (RAD IDE)
; Build: JWasm -mz -> a real DOS .EXE.  Run: Ctrl+F5 (DOSBox-X).  F5: step it in RAD IDE's 8086 emulator.
        .model small
        .stack 200h

        .data
hello   db 'Hello from {name}!', 13, 10, '$'
ask     db 'Press a key: $'
youhit  db 13, 10, 'You pressed: $'
crlf    db 13, 10, '$'

        .code
main    proc
        mov ax, @data           ; DS -> our data segment
        mov ds, ax

        mov ah, 09h             ; DOS: print the $-terminated string at DS:DX
        mov dx, offset hello
        int 21h
        mov ah, 09h
        mov dx, offset ask
        int 21h
        mov ah, 01h             ; DOS: read a key with echo -> AL
        int 21h
        mov bl, al
        mov ah, 09h
        mov dx, offset youhit
        int 21h
        mov ah, 02h             ; DOS: print the character in DL
        mov dl, bl
        int 21h
        mov ah, 09h
        mov dx, offset crlf
        int 21h

        mov ax, 4C00h           ; DOS: exit with code 0
        int 21h
main    endp
        end main
"""

MENU = """; {name} - a text-mode menu with the video BIOS (INT 10h) and the keyboard BIOS (INT 16h).
; Arrow keys / 1-4 / Enter choose, Esc quits.
        .model small
        .stack 200h

        .data
title_  db 'RAD IDE  -  DOS MENU', 0
item1   db ' 1  Say hello             ', 0
item2   db ' 2  Beep                  ', 0
item3   db ' 3  Count to nine         ', 0
item4   db ' 4  Quit                  ', 0
items   dw offset item1, offset item2, offset item3, offset item4
msg1    db 'Hello! This menu was written in assembly.', 0
msg3    db '1 2 3 4 5 6 7 8 9', 0
blank   db '                                                  ', 0
bye     db 'Goodbye!', 13, 10, '$'
sel     dw 0

        .code
; print the 0-terminated string DS:SI at row DH, column DL with attribute BL
print_at proc
        push ax
        push cx
pa_next:
        mov ah, 02h             ; set cursor
        mov bh, 0
        int 10h
        lodsb
        or al, al
        jz pa_done
        mov ah, 09h             ; write character AL with attribute BL
        mov cx, 1
        int 10h
        inc dl
        jmp pa_next
pa_done:
        pop cx
        pop ax
        ret
print_at endp

show_menu proc
        xor cx, cx
sm_loop:
        mov bx, cx
        shl bx, 1
        mov si, items[bx]
        mov dh, 7
        add dh, cl
        mov dl, 27
        mov bl, 1Fh             ; white on blue
        cmp cx, sel
        jne sm_draw
        mov bl, 30h             ; black on cyan
sm_draw:
        call print_at
        inc cx
        cmp cx, 4
        jb sm_loop
        ret
show_menu endp

run_item proc
        mov si, offset blank
        mov dx, 0F0Ah           ; row 15, column 10
        mov bl, 1Fh
        call print_at
        mov ax, sel
        cmp ax, 0
        jne ri_2
        mov si, offset msg1
        jmp ri_print
ri_2:   cmp ax, 1
        jne ri_3
        mov ax, 0E07h           ; teletype BEL
        int 10h
        ret
ri_3:   cmp ax, 2
        jne ri_4
        mov si, offset msg3
        jmp ri_print
ri_4:   mov sel, 0FFFFh         ; quit
        ret
ri_print:
        mov dx, 0F0Ah
        mov bl, 1Eh             ; yellow on blue
        call print_at
        ret
run_item endp

main    proc
        mov ax, @data
        mov ds, ax
        mov ax, 0003h           ; 80x25 colour text mode
        int 10h
        mov ax, 0600h           ; clear the screen to blue
        mov bh, 1Fh
        xor cx, cx
        mov dx, 184Fh
        int 10h
        mov si, offset title_
        mov dx, 011Ch           ; row 1, column 28
        mov bl, 1Fh
        call print_at
key_loop:
        call show_menu
        mov ah, 00h             ; wait for a key: AH = scan code, AL = ASCII
        int 16h
        cmp al, 27
        je quit
        cmp al, 13
        je enter_
        cmp al, '1'
        jb arrows
        cmp al, '4'
        ja arrows
        sub al, '1'
        mov ah, 0
        mov sel, ax
        call show_menu
enter_: call run_item
        cmp sel, 0FFFFh
        je quit
        jmp key_loop
arrows: cmp ah, 48h             ; up
        jne down_
        dec sel
        jns key_loop
        mov sel, 3
        jmp key_loop
down_:  cmp ah, 50h             ; down
        jne key_loop
        inc sel
        cmp sel, 4
        jb key_loop
        mov sel, 0
        jmp key_loop
quit:   mov ax, 0003h
        int 10h
        mov ah, 09h
        mov dx, offset bye
        int 21h
        mov ax, 4C00h
        int 21h
main    endp
        end main
"""

MODE13 = """; {name} - mode 13h graphics (320 x 200, 256 colours): pixels straight into A000:0000. Any key quits.
        .model small
        .stack 200h

        .data
done_   db 'Back in text mode.', 13, 10, '$'

        .code
main    proc
        mov ax, @data
        mov ds, ax
        mov ax, 0013h           ; video mode 13h
        int 10h
        mov ax, 0A000h
        mov es, ax

        ; colour bars: rows 150..199, columns 32..287, colour = column - 32
        mov dx, 150
bar_row:
        mov ax, dx
        mov bx, 320
        push dx
        mul bx                  ; AX = row * 320
        pop dx
        add ax, 32
        mov di, ax
        xor al, al
        mov cx, 256
bar_px: stosb
        inc al
        loop bar_px
        inc dx
        cmp dx, 200
        jb bar_row

        ; a red box 60 x 40 at (20, 20)
        mov dx, 20
box_row:
        mov ax, dx
        mov bx, 320
        push dx
        mul bx
        pop dx
        add ax, 20
        mov di, ax
        mov al, 4
        mov cx, 60
        rep stosb
        inc dx
        cmp dx, 60
        jb box_row

        ; a diagonal pattern: colour 32 + ((x xor y) and 15) in a 100 x 100 square at (110, 20)
        xor bx, bx              ; BX = y
pat_row:
        mov ax, bx
        add ax, 20
        mov cx, 320
        mul cx
        add ax, 110
        mov di, ax
        xor si, si              ; SI = x
pat_px: mov ax, si
        xor ax, bx
        and al, 15
        add al, 32
        stosb
        inc si
        cmp si, 100
        jb pat_px
        inc bx
        cmp bx, 100
        jb pat_row

        mov ah, 00h             ; wait for a key
        int 16h
        mov ax, 0003h           ; back to text mode
        int 10h
        mov ah, 09h
        mov dx, offset done_
        int 21h
        mov ax, 4C00h
        int 21h
main    endp
        end main
"""

SPEAKER = """; {name} - PC speaker music: the timer chip (PIT channel 2, ports 42h / 43h) and port 61h.
        .model small
        .stack 200h

        .data
playing db 'Playing a little tune on the PC speaker...', 13, 10, '$'
fin     db 'Finished.', 13, 10, '$'
; frequency (Hz), length (BIOS ticks of 55 ms); 0 ends the tune
tune    dw 523, 3, 587, 3, 659, 3, 698, 3, 784, 6, 784, 6, 880, 3, 880, 3, 880, 3, 880, 3, 784, 9, 0, 0

        .code
; wait CX timer ticks (BIOS tick counter at 0040:006Ch)
wait_ticks proc
        push ax
        push es
        mov ax, 40h
        mov es, ax
wt_next:
        mov ax, es:[6Ch]
wt_same:
        cmp ax, es:[6Ch]
        je wt_same
        loop wt_next
        pop es
        pop ax
        ret
wait_ticks endp

; play the frequency in BX (Hz) for CX ticks
tone    proc
        mov al, 0B6h            ; channel 2, lobyte/hibyte, square wave
        out 43h, al
        mov dx, 12h             ; DX:AX = 1193180 = PIT clock
        mov ax, 34DCh
        div bx                  ; AX = divisor
        out 42h, al
        mov al, ah
        out 42h, al
        in al, 61h              ; speaker on (bits 0 and 1)
        or al, 3
        out 61h, al
        call wait_ticks
        in al, 61h              ; speaker off
        and al, 0FCh
        out 61h, al
        ret
tone    endp

main    proc
        mov ax, @data
        mov ds, ax
        mov ah, 09h
        mov dx, offset playing
        int 21h
        mov si, offset tune
next_note:
        mov bx, [si]
        mov cx, [si + 2]
        or bx, bx
        jz finished
        call tone
        add si, 4
        jmp next_note
finished:
        mov ah, 09h
        mov dx, offset fin
        int 21h
        mov ax, 4C00h
        int 21h
main    endp
        end main
"""

MOUSE = """; {name} - the mouse driver (INT 33h) in text mode: shows the position, right button or a key quits.
        .model small
        .stack 200h

        .data
nomouse db 'No mouse driver found.', 13, 10, '$'
found   db 'Mouse found. Move it; right button or a key quits.', 13, 10, '$'
posmsg  db 'Column ', 0
rowmsg  db '  Row ', 0
bye     db 13, 10, 'Mouse demo finished.', 13, 10, '$'

        .code
; print AX (0..99) as two digits with teletype output
print2  proc
        push ax
        push bx
        mov bl, 10
        div bl                  ; AL = tens, AH = ones
        add ax, 3030h
        push ax
        mov ah, 0Eh
        int 10h
        pop ax
        mov al, ah
        mov ah, 0Eh
        int 10h
        pop bx
        pop ax
        ret
print2  endp

puts0   proc                    ; DS:SI 0-terminated string, teletype
pz_next:
        lodsb
        or al, al
        jz pz_done
        mov ah, 0Eh
        mov bh, 0
        int 10h
        jmp pz_next
pz_done:
        ret
puts0   endp

main    proc
        mov ax, @data
        mov ds, ax
        mov ax, 0003h
        int 10h
        xor ax, ax              ; reset the driver: AX = FFFFh when present
        int 33h
        cmp ax, 0FFFFh
        je have_mouse
        mov ah, 09h
        mov dx, offset nomouse
        int 21h
        jmp exit_
have_mouse:
        mov ah, 09h
        mov dx, offset found
        int 21h
        mov ax, 1               ; show the cursor
        int 33h
poll:   mov ax, 3               ; CX = x, DX = y (pixels), BX = buttons
        int 33h
        push bx
        push cx
        push dx
        mov ax, 2               ; hide while writing
        int 33h
        mov ah, 02h             ; cursor to row 24, column 0
        mov bh, 0
        mov dx, 1800h
        int 10h
        mov si, offset posmsg
        call puts0
        pop dx
        pop cx
        push dx
        mov ax, cx
        mov cl, 3
        shr ax, cl              ; pixels / 8 = column
        call print2
        mov si, offset rowmsg
        call puts0
        pop ax
        mov cl, 3
        shr ax, cl
        call print2
        mov ax, 1
        int 33h
        pop bx
        test bx, 2              ; right button
        jnz done_
        mov ah, 01h             ; key waiting?
        int 16h
        jz poll
        mov ah, 00h
        int 16h
done_:  mov ax, 2
        int 33h
        mov ah, 09h
        mov dx, offset bye
        int 21h
exit_:  mov ax, 4C00h
        int 21h
main    endp
        end main
"""

COM = """; {name} - a tiny .COM program (code, data and stack in one 64 KB segment, starts at 100h).
; Project > DOS Settings > Output = COM.  F5 steps it in RAD IDE's 8086 emulator.
        .model tiny
        .code
        org 100h
start:  mov ah, 09h
        mov dx, offset msg
        int 21h
        mov ax, 4C00h
        int 21h
msg     db 'Hello from a .COM program!', 13, 10, '$'
        end start
"""

TEMPLATES = [
    ("dosasm_hello", "Hello (.EXE, .model small)", "INT 21h string output and key input. JWasm builds an MZ .EXE; "
     "F5 steps it in the 8086 emulator.", {"MAIN.ASM": HELLO}, {}),
    ("dosasm_com", "Tiny .COM Program", "org 100h, one segment: the smallest DOS program.", {"MAIN.ASM": COM},
     {"output": "com"}),
    ("dosasm_menu", "Text-Mode Menu", "INT 10h colour text and INT 16h keys: a boxed menu with arrow keys.",
     {"MAIN.ASM": MENU}, {}),
    ("dosasm_mode13", "Mode 13h Graphics", "Mode 13h with stosb / rep stosb into A000:0000.", {"MAIN.ASM": MODE13},
     {}),
    ("dosasm_speaker", "PC Speaker Music", "The 8253 timer (ports 42h / 43h) and port 61h, timed with the BIOS "
     "tick counter.", {"MAIN.ASM": SPEAKER}, {}),
    ("dosasm_mouse", "Mouse (INT 33h)", "Reset, show and read the mouse driver.", {"MAIN.ASM": MOUSE}, {}),
]
