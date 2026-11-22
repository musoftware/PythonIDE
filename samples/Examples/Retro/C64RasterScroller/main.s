; (c) 2026 Musoftware - https://musoftwares.com - MIT License
;
; C64RasterScroller - a Commodore 64 demo (ca65 + ld65), written with RAD IDE.
; * raster bars: the background colour changes on every second raster line behind the title (busy-waiting on
;   $D012, no interrupts needed),
; * a smooth scroller on the bottom text row: the VIC-II fine X scroll ($D016) is set just for that row and the
;   characters move one cell every eight frames,
; * a hardware sprite (an original balloon drawing, copied to $0340 = sprite block 13) moved with joystick 2 or
;   W A S D; the border flashes while fire / space is held; Q returns to BASIC.
; F5 builds C64RasterScroller.prg and runs it in VICE (Tools > Retro > Emulators downloads it).

EXTCOL  = $D020         ; border colour
BGCOL0  = $D021         ; background colour
SP0X    = $D000         ; sprite 0 position
SP0Y    = $D001
SPMSB   = $D010         ; bit 8 of the sprite X positions
SCROLX  = $D016         ; bit 3 = 40 columns, bits 0-2 = fine X scroll
SPENA   = $D015         ; sprite enable
SP0COL  = $D027         ; sprite 0 colour
RASTER  = $D012
CIAPRA  = $DC00         ; joystick 2 (0 = pressed): bit 0 up, 1 down, 2 left, 3 right, 4 fire
CHROUT  = $FFD2         ; KERNAL: print the character in A
GETIN   = $FFE4         ; KERNAL: key from the keyboard buffer (0 = none)
SCREEN  = $0400
COLRAM  = $D800
SPRPTR  = SCREEN + $03F8 ; sprite pointers (block number = address / 64)
SPRDATA = $0340         ; block 13
ROW24   = SCREEN + 24 * 40
BAR_TOP = 58            ; first raster line of the bars

.segment "LOADADDR"
        .word $0801

.segment "EXEHDR"               ; 10 SYS 2061
        .word @next, 10
        .byte $9E, "2061", 0
@next:  .word 0

.segment "ZEROPAGE"
ptr:    .res 2

.segment "BSS"
spritex: .res 1
spritey: .res 1
fine:    .res 1         ; fine scroll 7..0
textpos: .res 1         ; next character of the scroll text
frame:   .res 1
moves:   .res 1         ; how many frames the balloon moved (read by the test through the VICE monitor)

.segment "CODE"
start:
        lda #0
        sta EXTCOL
        sta BGCOL0
        sta frame
        sta moves
        sta textpos
        lda #7
        sta fine
        lda #147                ; clear the screen
        jsr CHROUT
        lda #5                  ; white text
        jsr CHROUT
        ldx #0
@print: lda title,x
        beq @printed
        jsr CHROUT
        inx
        bne @print
@printed:
        ldx #39                 ; the scroller row: spaces in light blue
@row:   lda #32
        sta ROW24,x
        lda #14
        sta COLRAM + 24 * 40,x
        dex
        bpl @row
        ldx #62                 ; the balloon -> sprite block 13
@spr:   lda balloon,x
        sta SPRDATA,x
        dex
        bpl @spr
        lda #SPRDATA / 64
        sta SPRPTR
        lda #10                 ; light red
        sta SP0COL
        lda #160
        sta spritex
        lda #140
        sta spritey
        lda #0
        sta SPMSB
        lda #1
        sta SPENA

loop:
        ; ---- raster bars behind the title
        lda #BAR_TOP
@top:   cmp RASTER
        bne @top
        ldx #0
@bar:   lda bars,x
        ldy RASTER
@line:  cpy RASTER              ; wait for the next raster line
        beq @line
        iny
@line2: cpy RASTER              ; ... and the one after it (each colour is two lines high)
        beq @line2
        sta BGCOL0
        inx
        cpx #BARS
        bne @bar
        lda #0
        sta BGCOL0

        ; ---- fine scroll only for the bottom text row (it starts at raster line 243)
        lda #241
@w1:    cmp RASTER
        bne @w1
        lda fine
        and #7                  ; 38 columns (bit 3 = 0) hide the characters entering / leaving
        sta SCROLX
        lda #251
@w2:    cmp RASTER
        bne @w2
        lda #%00001000          ; back to 40 columns, no scroll, for the rest of the screen
        sta SCROLX

        ; ---- once per frame, below the screen
        inc frame
        jsr scroll_text
        jsr GETIN               ; a key from the keyboard buffer (0 = none)
        sta ptr
        cmp #'Q'
        beq quit
        jsr move_sprite
        jmp loop

quit:   lda #0
        sta SPENA
        lda #%00001000
        sta SCROLX
        lda #14
        sta EXTCOL
        lda #6
        sta BGCOL0
        rts                     ; back to BASIC

; scroll_text: one pixel per frame; every 8 pixels the row moves one character to the left
scroll_text:
        dec fine
        bpl @done
        lda #7
        sta fine
        ldx #0
@shift: lda ROW24 + 1,x
        sta ROW24,x
        inx
        cpx #39
        bne @shift
        ldx textpos
        lda scrolltext,x
        bne @char
        ldx #0                  ; end of the text: start again
        stx textpos
        lda scrolltext
@char:  and #$3F                ; PETSCII letters / digits -> screen codes
        sta ROW24 + 39
        inc textpos
@done:  rts

; move_sprite: joystick 2 (and W A S D, space = fire); ptr = the key read by the main loop
move_sprite:
        lda CIAPRA
        eor #$FF                ; 1 = pressed
        sta ptr+1
        lda ptr
        cmp #'W'
        bne :+
        lda ptr+1
        ora #1
        sta ptr+1
:       lda ptr
        cmp #'S'
        bne :+
        lda ptr+1
        ora #2
        sta ptr+1
:       lda ptr
        cmp #'A'
        bne :+
        lda ptr+1
        ora #4
        sta ptr+1
:       lda ptr
        cmp #'D'
        bne :+
        lda ptr+1
        ora #8
        sta ptr+1
:       lda ptr
        cmp #' '
        bne :+
        lda ptr+1
        ora #16
        sta ptr+1
:       lda ptr+1
        and #15
        beq @nomove
        inc moves
@nomove:
        lda ptr+1
        lsr a
        bcc :+
        ldx spritey
        cpx #52
        bcc :+
        dec spritey
        dec spritey
:       lsr a
        bcc :+
        ldx spritey
        cpx #228
        bcs :+
        inc spritey
        inc spritey
:       lsr a
        bcc :+
        ldx spritex
        cpx #26
        bcc :+
        dec spritex
        dec spritex
:       lsr a
        bcc :+
        ldx spritex
        cpx #252
        bcs :+
        inc spritex
        inc spritex
:       lsr a                   ; fire: flash the border
        lda #0
        bcc :+
        lda frame
:       sta EXTCOL
        lda spritex
        sta SP0X
        lda spritey
        sta SP0Y
        rts

.segment "RODATA"
title:  .byte 13, "    RAD IDE  *  C64 RASTER SCROLLER", 13, 13
        .byte "   JOYSTICK 2 OR W A S D MOVES THE BALLOON", 13
        .byte "   FIRE / SPACE FLASHES, Q QUITS", 0
bars:   .byte 6, 14, 3, 1, 3, 14, 6, 0, 2, 10, 7, 1, 7, 10, 2, 0
BARS = * - bars
scrolltext:
        .byte "HELLO FROM RAD IDE ... THIS TEXT SCROLLS WITH THE VIC-II FINE SCROLL REGISTER ... "
        .byte "WRITTEN IN 6502 ASSEMBLY WITH CA65 ...      ", 0
balloon:                        ; 24 x 21 pixels, 3 bytes per row (original drawing)
        .byte %00000000, %01111100, %00000000   ; .........11111..........
        .byte %00000001, %11111111, %00000000   ; .......111111111........
        .byte %00000011, %11111111, %10000000   ; ......11111111111.......
        .byte %00000111, %11111111, %11000000   ; .....1111111111111......
        .byte %00000111, %11001111, %11000000   ; .....11111..111111......
        .byte %00001111, %10000111, %11100000   ; ....11111....111111.....
        .byte %00001111, %10000111, %11100000   ; ....11111....111111.....
        .byte %00001111, %11001111, %11100000   ; ....111111..1111111.....
        .byte %00001111, %11111111, %11100000   ; ....111111111111111.....
        .byte %00000111, %11111111, %11000000   ; .....1111111111111......
        .byte %00000111, %11111111, %11000000   ; .....1111111111111......
        .byte %00000011, %11111111, %10000000   ; ......11111111111.......
        .byte %00000001, %11111111, %00000000   ; .......111111111........
        .byte %00000000, %11111110, %00000000   ; ........1111111.........
        .byte %00000000, %00111000, %00000000   ; ..........111...........
        .byte %00000000, %00010000, %00000000   ; ...........1............
        .byte %00000000, %00010000, %00000000   ; ...........1............
        .byte %00000000, %00100000, %00000000   ; ..........1.............
        .byte %00000000, %00010000, %00000000   ; ...........1............
        .byte %00000000, %00001000, %00000000   ; ............1...........
        .byte %00000000, %00010000, %00000000   ; ...........1............
