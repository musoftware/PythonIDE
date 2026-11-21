; C64Ball - a Commodore 64 program (ca65 + ld65), written with RAD IDE
; Prints a message, cycles the border colour and moves a ball with joystick 2 (or W A S D); Q quits.

EXTCOL  = $D020         ; border colour
BGCOL0  = $D021         ; background colour
CIAPRA  = $DC00         ; joystick 2 (0 = pressed): bit 0 up, 1 down, 2 left, 3 right, 4 fire
CHROUT  = $FFD2         ; KERNAL: print the character in A
GETIN   = $FFE4         ; KERNAL: key from the keyboard buffer (0 = none)
SCREEN  = $0400
COLRAM  = $D800
RASTER  = $D012

.segment "LOADADDR"
        .word $0801

.segment "EXEHDR"               ; 10 SYS 2061
        .word @next, 10
        .byte $9E, "2061", 0
@next:  .word 0

.segment "ZEROPAGE"
ptr:    .res 2

.segment "BSS"
ballx:  .res 1
bally:  .res 1
frame:  .res 1

.segment "CODE"
start:
        lda #0
        sta BGCOL0
        lda #147                ; clear screen
        jsr CHROUT
        ldx #0
@print: lda message,x
        beq @printed
        jsr CHROUT
        inx
        bne @print
@printed:
        lda #20
        sta ballx
        lda #12
        sta bally

loop:
        lda #251                ; wait for the raster line below the screen: one move per frame
@wait:  cmp RASTER
        bne @wait
        inc frame
        lda frame
        lsr a
        lsr a
        lsr a
        sta EXTCOL              ; border colour cycle

        jsr erase_ball
        lda CIAPRA
        lsr a
        bcs :+
        dec bally
:       lsr a
        bcs :+
        inc bally
:       lsr a
        bcs :+
        dec ballx
:       lsr a
        bcs :+
        inc ballx
:       jsr GETIN
        cmp #'Q'
        beq quit
        cmp #'W'
        bne :+
        dec bally
:       cmp #'S'
        bne :+
        inc bally
:       cmp #'A'
        bne :+
        dec ballx
:       cmp #'D'
        bne :+
        inc ballx
:       jsr clamp
        jsr draw_ball
        jmp loop

quit:   rts                     ; back to BASIC

clamp:  lda ballx
        bpl :+
        lda #0
:       cmp #40
        bcc :+
        lda #39
:       sta ballx
        lda bally
        cmp #3
        bcs :+
        lda #3
:       cmp #25
        bcc :+
        lda #24
:       sta bally
        rts

; ptr = SCREEN + bally * 40 + ballx
locate: lda #<SCREEN
        sta ptr
        lda #>SCREEN
        sta ptr+1
        ldx bally
        beq @col
@row:   clc
        lda ptr
        adc #40
        sta ptr
        bcc :+
        inc ptr+1
:       dex
        bne @row
@col:   ldy ballx
        rts

erase_ball:
        jsr locate
        lda #32                 ; space
        sta (ptr),y
        rts

draw_ball:
        jsr locate
        lda #81                 ; screen code of the ball
        sta (ptr),y
        lda ptr+1               ; colour RAM: same offset at $D800
        clc
        adc #>(COLRAM - SCREEN)
        sta ptr+1
        lda #7                  ; yellow
        sta (ptr),y
        rts

.segment "RODATA"
message:
        .byte "HELLO FROM C64BALL!", 13, "JOYSTICK 2 OR W A S D MOVES, Q QUITS", 0
