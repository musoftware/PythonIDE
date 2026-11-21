; KeyGame - catch the stars: move the @ with the arrow keys, Esc quits.
; Uses INT 16h (keyboard), INT 10h (cursor / characters) and a simple pseudo-random generator.
org 100h

    mov ax, 0003h
    int 10h
    mov ah, 01h                 ; hide the cursor
    mov cx, 2000h
    int 10h
    mov word ptr seed, 1234h
    call new_star
    call draw_player
    call show_score

game_loop:
    mov ah, 00h                 ; wait for a key: AH = scan code, AL = ASCII
    int 16h
    cmp al, 27                  ; Esc
    je game_over
    push ax                     ; keep the scan code: put_at_player changes AH
    mov al, ' '                 ; erase the player
    call put_at_player
    pop ax
    cmp ah, 48h                 ; up
    jne not_up
    cmp prow, 1
    jbe moved
    dec prow
not_up:
    cmp ah, 50h                 ; down
    jne not_down
    cmp prow, 24
    jae moved
    inc prow
not_down:
    cmp ah, 4Bh                 ; left
    jne not_left
    cmp pcol, 0
    je moved
    dec pcol
not_left:
    cmp ah, 4Dh                 ; right
    jne moved
    cmp pcol, 79
    je moved
    inc pcol
moved:
    call draw_player
    mov al, prow
    cmp al, srow
    jne game_loop
    mov al, pcol
    cmp al, scol
    jne game_loop
    inc score                   ; caught it
    call show_score
    call new_star
    call draw_player
    jmp game_loop

game_over:
    mov ah, 02h
    mov bh, 0
    mov dx, 0C1Eh
    int 10h
    mov ah, 09h
    mov dx, offset bye
    int 21h
    mov ax, 4C00h
    int 21h

; ---------------------------------------------------------------- helpers
draw_player:
    mov al, '@'
put_at_player:                  ; character AL at (prow, pcol), white
    mov dh, prow
    mov dl, pcol
    mov bl, 0Fh
put_char:                       ; AL at row DH column DL with attribute BL
    push ax
    mov ah, 02h
    mov bh, 0
    int 10h
    pop ax
    mov ah, 09h
    mov cx, 1
    int 10h
    ret

new_star:                       ; a star at a pseudo-random place (rows 1..24)
    call random
    xor dx, dx
    mov bx, 80
    div bx
    mov scol, dl
    call random
    xor dx, dx
    mov bx, 24
    div bx
    inc dl
    mov srow, dl
    mov dh, srow
    mov dl, scol
    mov al, '*'
    mov bl, 0Eh                 ; yellow
    jmp put_char

random:                         ; AX = next value of a linear congruential generator
    mov ax, seed
    mov dx, 25173
    mul dx
    add ax, 13849
    mov seed, ax
    ret

show_score:
    mov ah, 02h
    mov bh, 0
    mov dx, 0000h
    int 10h
    mov ah, 09h
    mov dx, offset score_txt
    int 21h
    mov al, score
    add al, '0'
    mov ah, 0Eh
    int 10h
    ret

prow      db 12
pcol      db 40
srow      db 0
scol      db 0
score     db 0
seed      dw 0
score_txt db 'Score: $'
bye       db 'Game over$'
