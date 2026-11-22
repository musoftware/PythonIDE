; (c) 2026 Musoftware - https://musoftwares.com - MIT License
;
; Atari2600Runner - a tiny endless-runner for the Atari 2600 (DASM), written with RAD IDE.
; The runner (player 0) stands on the ground; cacti (player 1) come from the right. Press fire to jump
; (simple gravity with a signed velocity). Every cactus that leaves the screen scores a point - the score is the
; yellow bar at the top (playfield PF1 / PF2); touching a cactus (hardware collision CXPPMM) flashes the sky
; red and resets the score. The cacti get faster after 8 points.
;
; One NTSC frame = 3 lines VSYNC + 37 lines VBLANK + 192 visible lines + 30 lines overscan; the visible part is
; three loops: 8 lines score bar, 168 lines sky with the two sprites, 16 lines ground (playfield).
; F5 builds Atari2600Runner.bin with DASM and runs it in Stella (Tools > Retro > Emulators downloads it).

        processor 6502
        include "atari2600.h"

; ---------------------------------------------------------------- RAM ($80-$FF)
RunnerY         = $80           ; bottom line of the runner (scanline counter value)
VelY            = $81           ; signed vertical speed (+ = up)
ObstX           = $82           ; cactus X 0..159
Speed           = $83           ; cactus speed (pixels per frame)
Score           = $84           ; 0..16
Flash           = $85           ; frames of red sky left
Temp            = $86
Frame           = $87

RUNNER_X        = 30
GROUND_Y        = 17            ; lowest RunnerY (just above the 16 ground lines)
CACTUS_Y        = 17            ; the cactus stands on the ground
HEIGHT          = 10            ; both sprites are 10 lines high
SKY             = $84           ; blue
RED             = $42

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
        lda #GROUND_Y
        sta RunnerY
        lda #150
        sta ObstX
        lda #1
        sta Speed
        lda #$0E                ; runner: white
        sta COLUP0
        lda #$C6                ; cactus: green
        sta COLUP1

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
        inc Frame
        lda CXPPMM              ; bit 7: player 0 touched player 1 during the last frame
        bpl NoHit
        lda #0
        sta Score
        lda #1
        sta Speed
        lda #150
        sta ObstX
        lda #30
        sta Flash
NoHit:
        sta CXCLR               ; clear the collision latches

        lda INPT4               ; fire (bit 7 = 0) on the ground: jump
        bmi NoJump
        lda RunnerY
        cmp #GROUND_Y
        bne NoJump
        lda #6
        sta VelY
NoJump:
        lda RunnerY             ; RunnerY += VelY
        clc
        adc VelY
        sta RunnerY
        lda Frame               ; gravity: VelY -= 1 every second frame
        and #1
        bne NoGravity
        dec VelY
NoGravity:
        lda RunnerY             ; landed?
        cmp #GROUND_Y
        bcs InAir
        lda #GROUND_Y
        sta RunnerY
        lda #0
        sta VelY
InAir:
        lda ObstX               ; move the cactus to the left
        sec
        sbc Speed
        bcs ObstOk
        lda Score               ; it left the screen: a point
        cmp #16
        bcs Wrap
        inc Score
        lda Score
        cmp #8
        bne Wrap
        inc Speed
Wrap:
        lda #152
ObstOk:
        sta ObstX

        lda #SKY
        ldx Flash
        beq SkyColour
        dec Flash
        lda #RED
SkyColour:
        sta COLUBK

        lda #RUNNER_X           ; horizontal positions of both players
        ldx #0
        jsr SetHorizPos
        lda ObstX
        ldx #1
        jsr SetHorizPos
        sta WSYNC
        sta HMOVE

        ldx Score               ; score bar patterns
        cpx #9
        bcc LowScore
        ldx #8
LowScore:
        lda BarPF1,x
        sta Temp
WaitVBlank:
        lda INTIM
        bne WaitVBlank
        sta WSYNC
        sta VBLANK              ; A = 0: beam on

; ---------------------------------------------------------------- 8 lines: the score bar
        lda #$1E                ; yellow
        sta COLUPF
        lda Temp
        sta PF1
        lda Score
        sec
        sbc #8
        bcs HighScore
        lda #0
HighScore:
        tax
        lda BarPF2,x
        sta PF2
        ldy #8
BarLoop:
        sta WSYNC
        dey
        bne BarLoop
        lda #0
        sta PF1
        sta PF2

; ---------------------------------------------------------------- 168 lines: sky with the two sprites
        ldy #184                ; scanline counter 184 .. 17
SkyLoop:
        tya
        sec
        sbc RunnerY             ; line inside the runner = Y - RunnerY
        cmp #HEIGHT
        bcc RunnerLine
        lda #0
        beq RunnerDone          ; (always)
RunnerLine:
        tax
        lda RunnerGfx,x
RunnerDone:
        sta Temp
        tya
        sec
        sbc #CACTUS_Y
        cmp #HEIGHT
        bcc CactusLine
        lda #0
        beq CactusDone          ; (always)
CactusLine:
        tax
        lda CactusGfx,x
CactusDone:
        sta WSYNC
        sta GRP1
        lda Temp
        sta GRP0
        dey
        cpy #16
        bne SkyLoop

; ---------------------------------------------------------------- 16 lines: the ground
        lda #0
        sta WSYNC
        sta GRP0
        sta GRP1
        lda #$D4                ; dark green
        sta COLUPF
        lda #$FF
        sta PF0
        sta PF1
        sta PF2
        ldy #15
GroundLoop:
        sta WSYNC
        dey
        bne GroundLoop

; ---------------------------------------------------------------- overscan
        lda #2
        sta VBLANK
        lda #0
        sta PF0
        sta PF1
        sta PF2
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

; ---------------------------------------------------------------- graphics (bottom line first)
RunnerGfx:
        .byte %01000100         ; feet
        .byte %00101000
        .byte %00010000
        .byte %00111000
        .byte %01010100
        .byte %10111010
        .byte %00111000
        .byte %00010000
        .byte %00111000
        .byte %00111000         ; head
CactusGfx:
        .byte %00011000
        .byte %00011000
        .byte %00011000
        .byte %01011010
        .byte %01011010
        .byte %01111110
        .byte %00011000
        .byte %00011000
        .byte %00011000
        .byte %00010000
BarPF1:                         ; PF1 draws bit 7 first (left to right)
        .byte %00000000, %10000000, %11000000, %11100000, %11110000
        .byte %11111000, %11111100, %11111110, %11111111
BarPF2:                         ; PF2 draws bit 0 first
        .byte %00000000, %00000001, %00000011, %00000111, %00001111
        .byte %00011111, %00111111, %01111111, %11111111

; ---------------------------------------------------------------- vectors
        org $FFFC
        .word Reset             ; reset
        .word Reset             ; IRQ / BRK
