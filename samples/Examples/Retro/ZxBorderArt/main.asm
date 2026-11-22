; (c) 2026 Musoftware - https://musoftwares.com - MIT License
;
; ZxBorderArt - a ZX Spectrum program (sjasmplus), written with RAD IDE.
; * attribute art: the 32 x 24 colour cells (22528..23295) are filled with diagonal rainbow stripes that move
;   one cell per frame (PAPER colours, BRIGHT on alternate rows) - no pixels are drawn, only colour;
; * border stripes: after HALT the border colour ($FE port, bits 0-2) is changed in a counted loop, so the
;   border shows moving bands;
; * the keyboard is read directly from the ports: 1 - 4 choose the stripe width, P pauses the animation,
;   Space returns to BASIC. The title is printed with the ROM (RST $10, AT control codes).
; F5 builds ZxBorderArt.tap (a BASIC loader + this code at 32768) and runs it in your ZX emulator
; (RADIDE_ZX_EMULATOR, Fuse or ZEsarUX).

ROM_CLS         EQU $0D6B       ; ROM: clear the screen
ROM_CHAN_OPEN   EQU $1601       ; ROM: open a channel (A = 2: upper screen)
ATTR            EQU 22528       ; attribute memory: 768 bytes, FLASH BRIGHT PAPER(3) INK(3)
FIRST_ROW       EQU 4           ; rows 0..3 keep the title

        ORG $8000

start:
        call ROM_CLS
        ld a, 2
        call ROM_CHAN_OPEN
        ld hl, message
        call print
        ld a, 1
        ld (width), a
        xor a
        ld (paused), a

main_loop:
        halt                    ; wait for the frame interrupt (50 Hz)
        call border_bands
        ld a, (paused)
        or a
        jr nz, .keys
        ld a, (phase)
        inc a
        ld (phase), a
        call paint_attributes
.keys:
        ld bc, $7FFE            ; half-row B N M Symbol Space: bit 0 = Space
        in a, (c)
        bit 0, a
        jr z, quit
        ld bc, $F7FE            ; half-row 1 2 3 4 5: bits 0..4
        in a, (c)
        cpl
        and %00001111
        jr z, .noWidth
        ld b, 1                 ; width = number of the key (1..4)
.which:
        rrca
        jr c, .found
        inc b
        jr .which
.found:
        ld a, b
        ld (width), a
.noWidth:
        ld bc, $DFFE            ; half-row Y U I O P: bit 0 = P (toggles on key down)
        in a, (c)
        cpl
        and 1
        ld b, a
        ld a, (p_down)
        cp b
        ld a, b
        ld (p_down), a
        jr z, main_loop         ; no change
        or a
        jr z, main_loop         ; released
        ld a, (paused)
        xor 1
        ld (paused), a
        jr main_loop

quit:
        xor a                   ; black border, back to BASIC
        out ($FE), a
        ret

; border_bands: eight colour bands down the border, shifted by the frame phase
border_bands:
        ld a, (phase)
        ld e, a
        ld d, 8
.band:
        ld a, e
        and 7
        out ($FE), a
        ld b, 0                 ; a short delay = the band height
.wait:
        djnz .wait
        inc e
        dec d
        jr nz, .band
        xor a
        out ($FE), a
        ret

; paint_attributes: cell (row, col) gets PAPER = ((row + col + phase) / width) mod 8, INK = white
paint_attributes:
        ld hl, ATTR + FIRST_ROW * 32
        ld c, FIRST_ROW         ; row
.row:
        ld b, 0                 ; column
.col:
        ld a, c
        add a, b
        ld d, a
        ld a, (phase)
        add a, d                ; row + col + phase
        ld d, a
        ld a, (width)
        ld e, a
        ld a, d
        call divide             ; A = A / E
        and 7
        rlca                    ; PAPER is bits 3-5
        rlca
        rlca
        or 7                    ; INK white
        bit 0, c
        jr z, .dim
        or %01000000            ; BRIGHT on odd rows
.dim:
        ld (hl), a
        inc hl
        inc b
        ld a, b
        cp 32
        jr nz, .col
        inc c
        ld a, c
        cp 24
        jr nz, .row
        ret

; divide: A = A / E (E = 1..4, by repeated subtraction)
divide:
        ld d, 0
.loop:
        cp e
        jr c, .done
        sub e
        inc d
        jr .loop
.done:
        ld a, d
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
        db 22, 0, 2, "ZX BORDER ART - RAD IDE"
        db 22, 1, 2, "Keys 1-4: stripe width"
        db 22, 2, 2, "P: pause   Space: BASIC", 0
width:
        db 1
phase:
        db 0
paused:
        db 0
p_down:
        db 0
