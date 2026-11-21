; ZxBlock - a ZX Spectrum program (sjasmplus), written with RAD IDE
; Prints a message, then O / P move a block along row 12; the border shows the frame count. Space quits.
; F5 builds ZxBlock.tap (a BASIC loader + this code at 32768) and runs it.

ROM_CLS         EQU $0D6B       ; ROM: clear the screen
ROM_CHAN_OPEN   EQU $1601       ; ROM: open a channel (A = 2: upper screen)
ROW             EQU 12

        ORG $8000

start:
        call ROM_CLS
        ld a, 2
        call ROM_CHAN_OPEN
        ld hl, message
        call print
        ld a, 15
        ld (column), a

main_loop:
        halt                    ; 50 frames per second
        ld a, (frames)
        inc a
        ld (frames), a
        rrca
        rrca
        rrca
        and 7
        out ($FE), a            ; border colour

        ld bc, $7FFE            ; half-row B N M Symbol Space: bit 0 = Space
        in a, (c)
        bit 0, a
        ret z                   ; Space: back to BASIC

        ld bc, $DFFE            ; half-row Y U I O P: bit 0 = P, bit 1 = O
        in a, (c)
        ld e, a
        ld a, (column)
        ld d, a
        bit 0, e
        jr nz, .noRight
        cp 31
        jr nc, .noRight
        inc a
.noRight:
        bit 1, e
        jr nz, .noLeft
        or a
        jr z, .noLeft
        dec a
.noLeft:
        ld (column), a
        cp d
        jr z, main_loop         ; did not move
        ld a, d                 ; erase the old block
        ld c, ' '
        call put_at
        ld a, (column)
        ld c, $8F               ; a full graphics block
        call put_at
        jr main_loop

; put_at: print character C at row ROW, column A
put_at:
        ld b, a
        ld a, 22                ; AT control code
        rst $10
        ld a, ROW
        rst $10
        ld a, b
        rst $10
        ld a, c
        rst $10
        ret

; print: HL = zero-terminated text (rst $10 prints the character in A)
print:
        ld a, (hl)
        or a
        ret z
        rst $10
        inc hl
        jr print

message:
        db 22, 2, 2, "Hello from ZxBlock!"
        db 22, 4, 2, "O / P move the block"
        db 22, 5, 2, "Space returns to BASIC", 0
column:
        db 0
frames:
        db 0
