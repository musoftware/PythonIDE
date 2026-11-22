; (c) 2026 Musoftware - https://musoftwares.com - MIT License
;
; GameBoyGarden - a Game Boy program (RGBDS), written with RAD IDE.
; Walk the gardener around the garden with the D-pad and press A to plant a flower on the grass under him.
; The number of flowers is shown at the top (two BCD digits made with DAA). Start clears the garden.
; Shows: the cartridge header (rgbfix fills the logo and the checksums), LCD off/on only in vblank, copying tiles
; to VRAM, building a background map from code (fence, path, grass with tufts), a sprite in OAM, reading both
; joypad groups (directions + buttons) with edge detection for A / Start, and map writes in vertical blank.
; F5 builds GameBoyGarden.gb (rgbasm, rgblink, rgbfix) and runs it (mGBA / Mesen).

INCLUDE "gb.inc"

DEF T_GRASS   EQU $00
DEF T_TUFT    EQU $01
DEF T_FLOWER  EQU $02
DEF T_PATH    EQU $03
DEF T_FENCE   EQU $04
DEF T_PLAYER  EQU $05
DEF T_DIGIT   EQU $10              ; $10..$19 = 0..9
DEF T_LETTERS EQU $1A              ; F L O W E R S
DEF COUNT_MAP EQU _SCRN0 + 9       ; row 0, columns 9 and 10

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

        ld hl, _VRAM            ; the tiles
        ld de, Tiles
        ld bc, TilesEnd - Tiles
        call Copy
        call DrawGarden
        ld hl, _OAMRAM          ; no sprites
        ld bc, 160
        xor a
        call Fill

        ld a, 72 + 16           ; OAM Y = screen Y + 16, OAM X = screen X + 8
        ld [wPlayerY], a
        ld a, 40 + 8
        ld [wPlayerX], a
        xor a
        ld [wFlowers], a
        ld [wPlant], a
        dec a                   ; $FF: keys already held at power-on are not "pressed"
        ld [wOldKeys], a
        ld a, %11100100         ; shades 3 2 1 0
        ldh [rBGP], a
        ldh [rOBP0], a
        ld a, LCDC_ON | LCDC_BG8000 | LCDC_OBJ_ON | LCDC_BG_ON
        ldh [rLCDC], a

MainLoop:
        call WaitVBlank
        call DrawSprite         ; OAM and map writes first, while the vertical blank lasts
        call DrawCount
        ld a, [wPlant]
        or a
        call nz, PlantFlower
        call ReadPad            ; B = keys held: 0 right 1 left 2 up 3 down 4 A 5 B 6 Select 7 Start
        ld a, [wOldKeys]
        cpl
        and b
        ld c, a                 ; C = keys pressed this frame
        ld a, b
        ld [wOldKeys], a
        bit 4, c
        jr z, .noA
        ld a, 1
        ld [wPlant], a          ; planted at the next vertical blank
.noA:
        bit 7, c
        jr z, .noStart
        call ClearGarden
.noStart:
        call MovePlayer
        jr MainLoop

; ---------------------------------------------------------------- the player
MovePlayer:
        ld hl, wPlayerX
        bit 0, b
        jr z, .noRight
        ld a, [hl]
        cp 160                  ; screen X 152 = the right edge
        jr nc, .noRight
        inc [hl]
.noRight:
        bit 1, b
        jr z, .noLeft
        ld a, [hl]
        cp 9
        jr c, .noLeft
        dec [hl]
.noLeft:
        ld hl, wPlayerY
        bit 2, b
        jr z, .noUp
        ld a, [hl]
        cp 16 + 17              ; not over the fence / the title rows
        jr c, .noUp
        dec [hl]
.noUp:
        bit 3, b
        jr z, .noDown
        ld a, [hl]
        cp 16 + 136
        jr nc, .noDown
        inc [hl]
.noDown:
        ret

DrawSprite:
        ld hl, _OAMRAM          ; sprite 0: Y, X, tile, attributes
        ld a, [wPlayerY]
        ld [hl+], a
        ld a, [wPlayerX]
        ld [hl+], a
        ld a, T_PLAYER
        ld [hl+], a
        xor a
        ld [hl], a
        ret

; PlantFlower: the map cell under the centre of the sprite becomes a flower (only on grass)
PlantFlower:
        xor a
        ld [wPlant], a
        ld a, [wPlayerY]
        sub 16 - 4              ; screen Y + 4 (centre)
        srl a
        srl a
        srl a                   ; row
        ld l, a
        ld h, 0
        add hl, hl              ; row * 32
        add hl, hl
        add hl, hl
        add hl, hl
        add hl, hl
        ld a, [wPlayerX]
        sub 8 - 4
        srl a
        srl a
        srl a                   ; column
        ld e, a
        ld d, 0
        add hl, de
        ld de, _SCRN0
        add hl, de              ; HL = the map cell
        ld a, [hl]
        cp T_TUFT + 1           ; grass or tuft?
        ret nc
        ld [hl], T_FLOWER
        ld a, [wFlowers]        ; BCD + 1
        add 1
        daa
        ld [wFlowers], a
        ret

; DrawCount: the two digits of wFlowers at COUNT_MAP
DrawCount:
        ld a, [wFlowers]
        swap a
        and $0F
        add T_DIGIT
        ld [COUNT_MAP], a
        ld a, [wFlowers]
        and $0F
        add T_DIGIT
        ld [COUNT_MAP + 1], a
        ret

; ClearGarden: LCD off, redraw the map, count = 0
ClearGarden:
        call WaitVBlank
        xor a
        ldh [rLCDC], a
        ld [wFlowers], a
        call DrawGarden
        ld a, LCDC_ON | LCDC_BG8000 | LCDC_OBJ_ON | LCDC_BG_ON
        ldh [rLCDC], a
        ret

; ---------------------------------------------------------------- the background (LCD off)
DrawGarden:
        ld hl, _SCRN0
        ld b, 0                 ; row 0..31
.row:
        ld c, 0                 ; column 0..31
.col:
        ld a, b
        or a
        jr nz, .notTitle
        ld a, T_GRASS           ; row 0: the title (written below)
        jr .put
.notTitle:
        cp 1
        jr nz, .notFence
        ld a, T_FENCE
        jr .put
.notFence:
        ld a, c
        cp 9
        jr nz, .grass
        ld a, T_PATH            ; a path down column 9
        jr .put
.grass:
        ld a, b                 ; tufts where (row * 3 + column) mod 8 = 0
        add a
        add b
        add c
        and %00000111
        ld a, T_GRASS
        jr nz, .put
        ld a, T_TUFT
.put:
        ld [hl+], a
        inc c
        ld a, c
        cp 32
        jr nz, .col
        inc b
        ld a, b
        cp 32
        jr nz, .row
        ld hl, _SCRN0 + 1       ; "FLOWERS" at row 0, column 1
        ld a, T_LETTERS
        ld b, 7
.text:
        ld [hl+], a
        inc a
        dec b
        jr nz, .text
        jp DrawCount

; ---------------------------------------------------------------- helpers
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

; B = the keys held (1 = pressed): bits 0-3 Right Left Up Down, bits 4-7 A B Select Start
ReadPad:
        ld a, %00100000         ; select the direction keys
        ldh [rP1], a
        ldh a, [rP1]
        ldh a, [rP1]            ; (read twice: the lines need a moment)
        cpl
        and %00001111
        ld b, a
        ld a, %00010000         ; select the buttons
        ldh [rP1], a
        ldh a, [rP1]
        ldh a, [rP1]
        ldh a, [rP1]
        cpl
        and %00001111
        swap a
        or b
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

INCLUDE "tiles.inc"

SECTION "Variables", WRAM0
wPlayerX: db
wPlayerY: db
wFlowers: db
wOldKeys: db
wPlant:   db
