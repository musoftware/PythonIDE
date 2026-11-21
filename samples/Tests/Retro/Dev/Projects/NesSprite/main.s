; NesSprite - an NES game (ca65 + ld65), written with RAD IDE
; The D-pad moves the sprite, A changes its palette. F5 builds NesSprite.nes and runs it (Mesen).

.include "nes.inc"

.segment "HEADER"
        .byte "NES", $1A        ; iNES magic
        .byte 2                 ; 2 x 16K PRG ROM
        .byte 1                 ; 1 x 8K CHR ROM
        .byte $01               ; mapper 0, vertical mirroring
        .byte $00
        .res 8, 0

.segment "ZEROPAGE"
buttons:    .res 1
pressed:    .res 1              ; buttons that went down this frame
player_x:   .res 1
player_y:   .res 1
attr:       .res 1
nmi_count:  .res 1

.segment "OAM"
oam:        .res 256            ; sprite table, copied to the PPU every frame (OAM DMA)

.segment "CODE"
reset:
        sei
        cld
        ldx #$40
        stx JOY2                ; no APU frame IRQ
        ldx #$FF
        txs
        inx                     ; X = 0
        stx PPUCTRL             ; no NMI yet
        stx PPUMASK             ; rendering off
        stx DMC_FREQ
        bit PPUSTATUS
@vblank1:
        bit PPUSTATUS           ; wait for the PPU to warm up (1st vblank)
        bpl @vblank1

        lda #0
@clear:
        sta $0000,x
        sta $0100,x
        sta $0300,x
        sta $0400,x
        sta $0500,x
        sta $0600,x
        sta $0700,x
        inx
        bne @clear
        lda #$FF                ; Y = $FF hides a sprite
@hide:
        sta oam,x
        inx
        bne @hide

@vblank2:
        bit PPUSTATUS
        bpl @vblank2

        lda #$3F                ; palettes at PPU $3F00
        sta PPUADDR
        lda #$00
        sta PPUADDR
        ldx #0
@palette:
        lda palettes,x
        sta PPUDATA
        inx
        cpx #32
        bne @palette

        lda #124
        sta player_x
        lda #112
        sta player_y
        lda #%10000000          ; NMI on, sprites from pattern table 0
        sta PPUCTRL
        lda #%00011110          ; show background and sprites
        sta PPUMASK

main_loop:
        lda nmi_count
@wait:
        cmp nmi_count           ; wait for the next frame
        beq @wait

        jsr read_pad
        lda buttons
        and #BTN_RIGHT
        beq :+
        inc player_x
:       lda buttons
        and #BTN_LEFT
        beq :+
        dec player_x
:       lda buttons
        and #BTN_DOWN
        beq :+
        inc player_y
:       lda buttons
        and #BTN_UP
        beq :+
        dec player_y
:       lda pressed
        and #BTN_A
        beq :+
        lda attr
        clc
        adc #1
        and #%00000011          ; sprite palette 0..3
        sta attr
:
        lda player_y            ; sprite 0: Y, tile, attributes, X
        sta oam+0
        lda #1
        sta oam+1
        lda attr
        sta oam+2
        lda player_x
        sta oam+3
        jmp main_loop

; read_pad: buttons = A B Select Start Up Down Left Right (bit 7 .. bit 0), pressed = new ones
read_pad:
        lda buttons
        pha
        lda #1
        sta JOY1
        lda #0
        sta JOY1
        ldx #8
@bit:
        lda JOY1
        lsr a                   ; bit 0 -> carry
        rol buttons
        dex
        bne @bit
        pla
        eor #$FF
        and buttons
        sta pressed
        rts

nmi:
        pha
        lda #0
        sta OAMADDR
        lda #>oam
        sta OAMDMA              ; copy the sprite table
        inc nmi_count
        pla
irq:
        rti

.segment "RODATA"
palettes:
        .byte $0F, $00, $10, $30,  $0F, $01, $21, $31,  $0F, $06, $16, $26,  $0F, $09, $19, $29
        .byte $0F, $28, $16, $30,  $0F, $2A, $1A, $30,  $0F, $21, $11, $30,  $0F, $14, $24, $30

.segment "VECTORS"
        .word nmi, reset, irq

.segment "CHARS"
        .res 16, $00            ; tile 0: empty
        ; tile 1: a smiley - 8 bytes plane 0, 8 bytes plane 1 (colour 1 where plane 0 is set)
        .byte %00111100, %01000010, %10100101, %10000001, %10100101, %10011001, %01000010, %00111100
        .byte %00000000, %00000000, %00000000, %00000000, %00000000, %00000000, %00000000, %00000000
