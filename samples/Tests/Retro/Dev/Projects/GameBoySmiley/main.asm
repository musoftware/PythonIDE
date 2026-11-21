; GameBoySmiley - a Game Boy game (RGBDS), written with RAD IDE
; The D-pad moves the smiley sprite. F5 builds GameBoySmiley.gb (rgbasm, rgblink, rgbfix) and runs it (mGBA).

INCLUDE "gb.inc"

SECTION "Header", ROM0[$100]
        nop
        jp Start
        ds $150 - @, 0          ; the cartridge header: rgbfix writes the logo, title and checksums

SECTION "Main", ROM0

Start:
        di
        ld sp, $FFFE
        call WaitVBlank
        xor a
        ldh [rLCDC], a          ; LCD off (only allowed during vertical blank)
        ldh [rNR52], a          ; sound off

        ld hl, _VRAM            ; tiles 0 and 1
        ld de, Tiles
        ld bc, TilesEnd - Tiles
        call Copy
        ld hl, _SCRN0           ; background map: all tile 0
        ld bc, 32 * 32
        xor a
        call Fill
        ld hl, _OAMRAM          ; no sprites
        ld bc, 160
        xor a
        call Fill

        ld a, 80 + 16
        ld [wPlayerY], a
        ld a, 84 + 8
        ld [wPlayerX], a
        ld a, %11100100         ; shades 3 2 1 0
        ldh [rBGP], a
        ldh [rOBP0], a
        ld a, LCDC_ON | LCDC_BG8000 | LCDC_OBJ_ON | LCDC_BG_ON
        ldh [rLCDC], a

MainLoop:
        call WaitVBlank
        call ReadPad            ; B = pressed directions: bit 0 right, 1 left, 2 up, 3 down
        ld hl, wPlayerX
        bit 0, b
        jr z, .noRight
        inc [hl]
.noRight:
        bit 1, b
        jr z, .noLeft
        dec [hl]
.noLeft:
        ld hl, wPlayerY
        bit 2, b
        jr z, .noUp
        dec [hl]
.noUp:
        bit 3, b
        jr z, .noDown
        inc [hl]
.noDown:
        ld hl, _OAMRAM          ; sprite 0: Y, X, tile, attributes
        ld a, [wPlayerY]
        ld [hl+], a
        ld a, [wPlayerX]
        ld [hl+], a
        ld a, 1
        ld [hl+], a
        xor a
        ld [hl], a
        jr MainLoop

; wait until the next vertical blank starts
WaitVBlank:
.inBlank:
        ldh a, [rLY]
        cp 144
        jr nc, .inBlank
.waitBlank:
        ldh a, [rLY]
        cp 144
        jr c, .waitBlank
        ret

; B = the D-pad (1 = pressed)
ReadPad:
        ld a, %00100000         ; select the direction keys
        ldh [rP1], a
        ldh a, [rP1]
        ldh a, [rP1]            ; (read twice: the lines need a moment)
        cpl
        and %00001111
        ld b, a
        ld a, %00110000
        ldh [rP1], a
        ret

; copy BC bytes from DE to HL
Copy:
        ld a, [de]
        ld [hl+], a
        inc de
        dec bc
        ld a, b
        or c
        jr nz, Copy
        ret

; fill BC bytes at HL with A
Fill:
        ld d, a
.loop:
        ld a, d
        ld [hl+], a
        dec bc
        ld a, b
        or c
        jr nz, .loop
        ret

SECTION "Tiles", ROM0
Tiles:
        ds 16, 0                ; tile 0: empty
        ; tile 1: smiley, 2 bits per pixel (low byte, high byte per row)
        db %00111100, %00111100
        db %01000010, %01000010
        db %10100101, %10100101
        db %10000001, %10000001
        db %10100101, %10100101
        db %10011001, %10011001
        db %01000010, %01000010
        db %00111100, %00111100
TilesEnd:

SECTION "Variables", WRAM0
wPlayerX: db
wPlayerY: db
