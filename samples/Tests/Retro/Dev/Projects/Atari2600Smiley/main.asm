; Atari2600Smiley - an Atari 2600 game kernel (DASM), written with RAD IDE
;
; One NTSC frame = 3 lines VSYNC + 37 lines VBLANK + 192 visible lines + 30 lines overscan.
; The joystick moves the smiley (player 0), the fire button changes its colour.
; F5 builds Atari2600Smiley.bin with DASM and runs it in the emulator (Stella).

        processor 6502
        include "atari2600.h"

; ---------------------------------------------------------------- RAM ($80-$FF)
PlayerX         = $80           ; 0..152
PlayerY         = $81           ; scanline counter value of the sprite's bottom line
Joy             = $82           ; copy of SWCHA
Colour          = $83

SPRITE_HEIGHT   = 8

        seg code
        org $F000

Reset:
        sei
        cld
        ldx #0
        txa
ClearMem:
        sta $00,x               ; clears the TIA registers and the 128 bytes of RAM
        inx
        bne ClearMem
        dex                     ; X = $FF
        txs

        lda #76
        sta PlayerX
        lda #90
        sta PlayerY
        lda #$1E                ; yellow
        sta Colour
        lda #$84                ; blue
        sta COLUBK

; ---------------------------------------------------------------- frame
StartFrame:
        lda #2
        sta VBLANK              ; beam off
        sta VSYNC               ; 3 lines of vertical sync
        sta WSYNC
        sta WSYNC
        sta WSYNC
        lda #0
        sta VSYNC
        lda #43                 ; 37 lines * 76 cycles / 64
        sta TIM64T

        ; ---- game logic while the beam is off
        lda SWCHA
        sta Joy
        and #%10000000          ; right
        bne NoRight
        lda PlayerX
        cmp #152
        bcs NoRight
        inc PlayerX
NoRight:
        lda Joy
        and #%01000000          ; left
        bne NoLeft
        lda PlayerX
        beq NoLeft
        dec PlayerX
NoLeft:
        lda Joy
        and #%00010000          ; up
        bne NoUp
        lda PlayerY
        cmp #192 - SPRITE_HEIGHT
        bcs NoUp
        inc PlayerY
NoUp:
        lda Joy
        and #%00100000          ; down
        bne NoDown
        lda PlayerY
        cmp #2
        bcc NoDown
        dec PlayerY
NoDown:
        lda INPT4               ; fire: bit 7 = 0 when pressed
        bmi NoFire
        inc Colour
NoFire:
        lda Colour
        sta COLUP0

        lda PlayerX             ; horizontal position of player 0
        ldx #0
        jsr SetHorizPos
        sta WSYNC
        sta HMOVE

WaitVBlank:
        lda INTIM
        bne WaitVBlank
        sta WSYNC
        sta VBLANK              ; A = 0: beam on

; ---------------------------------------------------------------- 192 visible lines
        ldy #192
ScanLoop:
        tya
        sec
        sbc PlayerY             ; line of the sprite = Y - PlayerY
        cmp #SPRITE_HEIGHT
        bcc DrawLine
        lda #0
        beq StoreLine           ; (always)
DrawLine:
        tax
        lda Sprite,x
StoreLine:
        sta WSYNC
        sta GRP0
        dey
        bne ScanLoop

; ---------------------------------------------------------------- overscan
        lda #2
        sta VBLANK
        lda #0
        sta GRP0
        lda #35                 ; 30 lines * 76 / 64
        sta TIM64T
Overscan:
        lda INTIM
        bne Overscan
        jmp StartFrame

; ---------------------------------------------------------------- subroutines
; SetHorizPos: A = X position (0-159), X = object (0 player 0, 1 player 1, 2/3 missiles, 4 ball).
; Waits for a new line, counts down in steps of 15 pixels (5 cycles each), then fine-tunes with HMxx.
SetHorizPos:
        sta WSYNC
        sec
Div15:
        sbc #15
        bcs Div15
        eor #7
        asl
        asl
        asl
        asl
        sta HMP0,x
        sta RESP0,x
        rts

; ---------------------------------------------------------------- graphics
; The kernel draws the sprite from its last byte (top line) down to byte 0 (bottom line).
Sprite:
        .byte %00111100
        .byte %01000010
        .byte %10011001
        .byte %10100101
        .byte %10000001
        .byte %10100101
        .byte %01000010
        .byte %00111100

; ---------------------------------------------------------------- vectors
        org $FFFC
        .word Reset             ; reset
        .word Reset             ; IRQ / BRK
