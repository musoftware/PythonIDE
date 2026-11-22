; (c) 2026 Musoftware - https://musoftwares.com - MIT License
;
; NesStarCatcher - a small NES game (ca65 + ld65, mapper 0), written with RAD IDE.
; Stars fall from the sky; move the basket with Left / Right (hold B to run) and catch them. The score
; (two BCD digits) is drawn into the background name table during vblank; every 5 stars the stars fall faster.
; Shows: iNES header, PPU warm-up, palettes, a whole name table + attribute table drawn at reset, OAM DMA in the
; NMI, a 16-pixel metasprite (two 8x8 sprites), controller reading, an 8-bit LFSR random generator, collision
; tests and safe VRAM updates in vblank. All the tiles are original (tiles.inc).
; F5 builds NesStarCatcher.nes and runs it in Mesen (Tools > Retro > Emulators downloads it).

.include "nes.inc"

PLAYER_Y   = 200                ; basket row (sprite Y)
GROUND_Y   = 206                ; a star lower than this is lost
TILE_LEFT  = $04
TILE_RIGHT = $05
TILE_STAR  = $06
TILE_DIGIT = $10                ; tiles $10..$19 = 0..9
SCORE_ADDR = $2048              ; name table row 2, column 8

.segment "HEADER"
        .byte "NES", $1A        ; iNES magic
        .byte 2                 ; 2 x 16K PRG ROM
        .byte 1                 ; 1 x 8K CHR ROM
        .byte $01               ; mapper 0, vertical mirroring
        .byte $00
        .res 8, 0

.segment "ZEROPAGE"
buttons:    .res 1
player_x:   .res 1
star_x:     .res 1
star_y:     .res 1
speed:      .res 1
score:      .res 1              ; BCD: high nibble = tens, low nibble = units
caught:     .res 1              ; stars caught since the last speed-up
misses:     .res 1
seed:       .res 1              ; LFSR state (never 0)
dirty:      .res 1              ; 1 = the NMI must redraw the score
nmi_count:  .res 1
ptr:        .res 2

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
        txa
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

        jsr load_palettes
        jsr draw_background

        lda #120
        sta player_x
        lda #$A5
        sta seed
        lda #1
        sta speed
        jsr new_star
        lda #1
        sta dirty
        lda #%10000000          ; NMI on, sprites and background from pattern table 0
        sta PPUCTRL
        lda #%00011110          ; show background and sprites (also in the leftmost 8 pixels)
        sta PPUMASK

main_loop:
        lda nmi_count
@wait:
        cmp nmi_count           ; one game step per frame
        beq @wait
        jsr read_pad
        jsr move_player
        jsr move_star
        jsr draw_sprites
        jmp main_loop

; ---------------------------------------------------------------- game logic
move_player:
        ldx #1                  ; speed 1, or 2 while B is held
        lda buttons
        and #BTN_B
        beq :+
        ldx #2
:       lda buttons
        and #BTN_RIGHT
        beq @left
        txa
        clc
        adc player_x
        cmp #233                ; keep the 16-pixel basket on screen
        bcs @left
        sta player_x
@left:
        lda buttons
        and #BTN_LEFT
        beq @done
        stx ptr
        lda player_x
        sec
        sbc ptr
        cmp #8
        bcc @done
        sta player_x
@done:
        rts

move_star:
        lda star_y
        clc
        adc speed
        sta star_y
        cmp #PLAYER_Y - 6       ; high enough to touch the basket?
        bcc @done
        cmp #GROUND_Y
        bcs @lost
        lda star_x              ; star centre (x + 4) inside the basket (player_x .. player_x + 15)?
        clc
        adc #4
        sec
        sbc player_x
        cmp #16
        bcs @done
        jsr add_point
        jmp new_star
@lost:
        inc misses
        jmp new_star
@done:
        rts

add_point:
        lda score               ; BCD increment (the 2A03 has no decimal mode)
        clc
        adc #1
        tax
        and #$0F
        cmp #10
        bcc @store
        txa
        clc
        adc #6                  ; 9 + 1 -> carry into the tens
        tax
        cmp #$A0
        bcc @store
        ldx #0                  ; 99 -> 00
@store:
        stx score
        lda #1
        sta dirty
        inc caught
        lda caught
        cmp #5
        bcc @done
        lda #0
        sta caught
        lda speed
        cmp #3
        bcs @done
        inc speed
@done:
        rts

; new_star: a star at the top, X from the random generator (16 .. 239)
new_star:
        jsr random
        and #$DF                ; 0 .. 223
        clc
        adc #16
        sta star_x
        lda #16
        sta star_y
        rts

; random: 8-bit Galois LFSR (taps $B8) -> A
random:
        lda seed
        lsr a
        bcc :+
        eor #$B8
:       sta seed
        rts

draw_sprites:
        lda #PLAYER_Y - 1       ; sprite 0 / 1: the basket (OAM Y is one line above the sprite)
        sta oam+0
        sta oam+4
        lda #TILE_LEFT
        sta oam+1
        lda #TILE_RIGHT
        sta oam+5
        lda #0                  ; sprite palette 0
        sta oam+2
        sta oam+6
        lda player_x
        sta oam+3
        clc
        adc #8
        sta oam+7
        lda star_y              ; sprite 2: the star, palette 1
        sec
        sbc #1
        sta oam+8
        lda #TILE_STAR
        sta oam+9
        lda #1
        sta oam+10
        lda star_x
        sta oam+11
        rts

; read_pad: buttons = A B Select Start Up Down Left Right (bit 7 .. bit 0)
read_pad:
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
        rts

; ---------------------------------------------------------------- PPU set-up (rendering off)
load_palettes:
        lda #$3F
        sta PPUADDR
        lda #$00
        sta PPUADDR
        ldx #0
@loop:
        lda palettes,x
        sta PPUDATA
        inx
        cpx #32
        bne @loop
        rts

; draw_background: name table 0 from the row descriptions + the attribute table
draw_background:
        lda #$20
        sta PPUADDR
        lda #$00
        sta PPUADDR
        ldy #0                  ; row 0..29
@row:
        ldx #0                  ; column 0..31
@col:
        lda #$00                ; sky
        cpy #26
        bcc @not_grass
        bne @earth
        lda #$02                ; row 26: grass
        bne @put
@earth:
        lda #$03                ; rows 27..29: earth
        bne @put
@not_grass:
        cpy #5                  ; clouds in rows 5 and 8
        bne @row8
        txa
        and #%00001100          ; columns 4..7, 20..23
        cmp #%00000100
        bne @sky
        lda #$01
        bne @put
@row8:
        cpy #8
        bne @sky
        txa
        and #%00001100
        cmp #%00001000          ; columns 8..11, 24..27
        bne @sky
        lda #$01
        bne @put
@sky:
        lda #$00
@put:
        sta PPUDATA
        inx
        cpx #32
        bne @col
        iny
        cpy #30
        bne @row
        ldx #0                  ; attribute table: rows 26..29 use background palette 1
@attr:
        lda attributes,x
        sta PPUDATA
        inx
        cpx #64
        bne @attr
        lda #$20                ; the word SCORE at row 2, column 2
        sta PPUADDR
        lda #$42
        sta PPUADDR
        ldx #0
@text:
        lda score_text,x
        sta PPUDATA
        inx
        cpx #5
        bne @text
        rts

; ---------------------------------------------------------------- vblank
nmi:
        pha
        txa
        pha
        lda #0
        sta OAMADDR
        lda #>oam
        sta OAMDMA              ; copy the sprite table
        lda dirty
        beq @scroll
        lda #>SCORE_ADDR        ; two digit tiles of the BCD score
        sta PPUADDR
        lda #<SCORE_ADDR
        sta PPUADDR
        lda score
        lsr a
        lsr a
        lsr a
        lsr a
        clc
        adc #TILE_DIGIT
        sta PPUDATA
        lda score
        and #$0F
        clc
        adc #TILE_DIGIT
        sta PPUDATA
        lda #0
        sta dirty
@scroll:
        lda #0                  ; PPUADDR writes moved the scroll: reset it
        sta PPUSCROLL
        sta PPUSCROLL
        lda #%10000000
        sta PPUCTRL
        inc nmi_count
        pla
        tax
        pla
irq:
        rti

.segment "RODATA"
palettes:
        ; background: 0 sky / clouds / text,  1 grass / earth
        .byte $21, $30, $10, $0F,  $21, $2A, $17, $07,  $21, $30, $10, $0F,  $21, $30, $10, $0F
        ; sprites: 0 basket,  1 star
        .byte $21, $27, $17, $07,  $21, $28, $27, $30,  $21, $30, $10, $0F,  $21, $30, $10, $0F
attributes:
        .res 48, $00            ; rows 0..23: palette 0
        .res 8, $50             ; rows 24..27: top half palette 0, bottom half (26, 27) palette 1
        .res 8, $05             ; rows 28..29: palette 1
score_text:
        .byte $1A, $1B, $1C, $1D, $1E   ; S C O R E

.segment "VECTORS"
        .word nmi, reset, irq

.include "tiles.inc"
