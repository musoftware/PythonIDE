"""New Project templates of the retro systems (no Qt in here). All code here was written for RAD IDE.

``TEMPLATES[plugin id]`` = list of ``Template(id, title, description, icon, files, settings)``; "{name}" in file
names / contents is replaced by the project name.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Template:
    id: str
    title: str
    description: str
    icon: str
    files: list = field(default_factory=list)          # [(file name, text)]
    settings: dict = field(default_factory=dict)       # project.extra["retro"]
    modules: list = field(default_factory=list)        # files listed as project modules (default: sources)


# ============================================================================================ Atari 2600
A2600_H = """; atari2600.h - Atari 2600 hardware registers (written for RAD IDE)
; TIA write registers
VSYNC   = $00   ; vertical sync on/off (bit 1)
VBLANK  = $01   ; vertical blank on/off (bit 1), paddle / trigger latches
WSYNC   = $02   ; wait for the end of the scanline
RSYNC   = $03
NUSIZ0  = $04   ; player / missile 0 size and copies
NUSIZ1  = $05
COLUP0  = $06   ; player 0 colour
COLUP1  = $07
COLUPF  = $08   ; playfield / ball colour
COLUBK  = $09   ; background colour
CTRLPF  = $0A   ; playfield control
REFP0   = $0B   ; reflect player 0
REFP1   = $0C
PF0     = $0D   ; playfield bits
PF1     = $0E
PF2     = $0F
RESP0   = $10   ; reset positions (at the current beam position)
RESP1   = $11
RESM0   = $12
RESM1   = $13
RESBL   = $14
AUDC0   = $15   ; sound
AUDC1   = $16
AUDF0   = $17
AUDF1   = $18
AUDV0   = $19
AUDV1   = $1A
GRP0    = $1B   ; player graphics
GRP1    = $1C
ENAM0   = $1D   ; enable missiles / ball
ENAM1   = $1E
ENABL   = $1F
HMP0    = $20   ; horizontal motion
HMP1    = $21
HMM0    = $22
HMM1    = $23
HMBL    = $24
VDELP0  = $25
VDELP1  = $26
VDELBL  = $27
RESMP0  = $28
RESMP1  = $29
HMOVE   = $2A   ; apply the motion registers
HMCLR   = $2B
CXCLR   = $2C
; TIA read registers
CXM0P   = $00
CXM1P   = $01
CXP0FB  = $02
CXP1FB  = $03
CXM0FB  = $04
CXM1FB  = $05
CXBLPF  = $06
CXPPMM  = $07
INPT0   = $08
INPT1   = $09
INPT2   = $0A
INPT3   = $0B
INPT4   = $0C   ; joystick 0 fire (bit 7 = 0 when pressed)
INPT5   = $0D
; RIOT
SWCHA   = $280  ; joysticks: bit 7 right, 6 left, 5 down, 4 up (player 0), 0 = pressed
SWACNT  = $281
SWCHB   = $282  ; console switches
SWBCNT  = $283
INTIM   = $284  ; timer value
TIMINT  = $285
TIM1T   = $294
TIM8T   = $295
TIM64T  = $296  ; start the timer, 64 cycles per tick
T1024T  = $297
"""

A2600_MAIN = """; {name} - an Atari 2600 game kernel (DASM), written with RAD IDE
;
; One NTSC frame = 3 lines VSYNC + 37 lines VBLANK + 192 visible lines + 30 lines overscan.
; The joystick moves the smiley (player 0), the fire button changes its colour.
; F5 builds {name}.bin with DASM and runs it in the emulator (Stella).

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
"""

# ============================================================================================ NES
NES_CFG = """# {name}: memory map of an NROM (mapper 0) cartridge: 32K PRG ROM + 8K CHR ROM. Written for RAD IDE.
MEMORY {
    ZP:     start = $0000, size = $0100, type = rw, file = "";
    OAM:    start = $0200, size = $0100, type = rw, file = "";
    RAM:    start = $0300, size = $0500, type = rw, file = "";
    HDR:    start = $0000, size = $0010, type = ro, file = %O, fill = yes;
    PRG:    start = $8000, size = $8000, type = ro, file = %O, fill = yes, fillval = $FF;
    CHR:    start = $0000, size = $2000, type = ro, file = %O, fill = yes, fillval = $00;
}
SEGMENTS {
    ZEROPAGE: load = ZP,  type = zp;
    OAM:      load = OAM, type = bss, align = $100;
    BSS:      load = RAM, type = bss;
    HEADER:   load = HDR, type = ro;
    CODE:     load = PRG, type = ro, start = $8000;
    RODATA:   load = PRG, type = ro;
    VECTORS:  load = PRG, type = ro, start = $FFFA;
    CHARS:    load = CHR, type = ro;
}
"""

NES_INC = """; nes.inc - NES hardware registers (written for RAD IDE)
PPUCTRL   = $2000   ; NMI enable, sprite size, pattern tables, VRAM increment
PPUMASK   = $2001   ; show background / sprites
PPUSTATUS = $2002   ; bit 7 = vblank (reading clears it and the address latch)
OAMADDR   = $2003
OAMDATA   = $2004
PPUSCROLL = $2005
PPUADDR   = $2006
PPUDATA   = $2007
SQ1_VOL   = $4000
SQ1_SWEEP = $4001
SQ1_LO    = $4002
SQ1_HI    = $4003
DMC_FREQ  = $4010
OAMDMA    = $4014   ; write the page of the sprite table ($02 -> $0200-$02FF)
SND_CHN   = $4015
JOY1      = $4016   ; controller 1 (write 1/0 to latch, read 8 times)
JOY2      = $4017   ; controller 2 / APU frame counter

BTN_A      = %10000000
BTN_B      = %01000000
BTN_SELECT = %00100000
BTN_START  = %00010000
BTN_UP     = %00001000
BTN_DOWN   = %00000100
BTN_LEFT   = %00000010
BTN_RIGHT  = %00000001
"""

NES_MAIN = """; {name} - an NES game (ca65 + ld65), written with RAD IDE
; The D-pad moves the sprite, A changes its palette. F5 builds {name}.nes and runs it (Mesen).

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
"""

NES_C_MAIN = """/* {name} - an NES program in C (cc65), written with RAD IDE.
   The D-pad moves the '@', Start clears the screen. F5 builds {name}.nes with cl65 -t nes. */
#include <conio.h>
#include <nes.h>
#include <joystick.h>

int main(void)
{
    unsigned char x = 14, y = 12, ox, oy, pad;

    joy_install(joy_static_stddrv);
    clrscr();
    gotoxy(5, 2);
    cprintf("Hello from %s!", "{name}");
    gotoxy(5, 4);
    cputs("Move with the D-pad");

    for (;;) {
        ox = x;
        oy = y;
        waitvsync();
        pad = joy_read(JOY_1);
        if (JOY_RIGHT(pad) && x < 29) ++x;
        if (JOY_LEFT(pad) && x > 1) --x;
        if (JOY_DOWN(pad) && y < 26) ++y;
        if (JOY_UP(pad) && y > 6) --y;
        if (x != ox || y != oy) {
            cputcxy(ox, oy, ' ');
        }
        cputcxy(x, y, '@');
    }
}
"""

# ============================================================================================ Game Boy
GB_INC = """; gb.inc - Game Boy hardware registers (written for RAD IDE)
DEF rP1   EQU $FF00   ; joypad
DEF rDIV  EQU $FF04
DEF rIF   EQU $FF0F
DEF rNR52 EQU $FF26   ; sound on/off
DEF rLCDC EQU $FF40   ; LCD control
DEF rSTAT EQU $FF41
DEF rSCY  EQU $FF42
DEF rSCX  EQU $FF43
DEF rLY   EQU $FF44   ; current scanline (144-153 = vertical blank)
DEF rDMA  EQU $FF46
DEF rBGP  EQU $FF47   ; background palette
DEF rOBP0 EQU $FF48   ; sprite palette 0
DEF rOBP1 EQU $FF49
DEF rWY   EQU $FF4A
DEF rWX   EQU $FF4B
DEF rIE   EQU $FFFF

DEF _VRAM     EQU $8000
DEF _SCRN0    EQU $9800
DEF _OAMRAM   EQU $FE00

DEF LCDC_ON      EQU %10000000
DEF LCDC_BG8000  EQU %00010000
DEF LCDC_OBJ_ON  EQU %00000010
DEF LCDC_BG_ON   EQU %00000001
"""

GB_MAIN = """; {name} - a Game Boy game (RGBDS), written with RAD IDE
; The D-pad moves the smiley sprite. F5 builds {name}.gb (rgbasm, rgblink, rgbfix) and runs it (mGBA).

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
"""

# ============================================================================================ C64
C64_CFG = """# {name}: a C64 program with a BASIC "SYS" line (written for RAD IDE)
MEMORY {
    ZP:       start = $00FB, size = 4,     type = rw, file = "";     # 4 zero-page bytes BASIC leaves free
    LOADADDR: start = $07FF, size = 2,     file = %O;
    MAIN:     start = $0801, size = $97FF, file = %O;
}
SEGMENTS {
    ZEROPAGE: load = ZP, type = zp;
    LOADADDR: load = LOADADDR, type = ro;
    EXEHDR:   load = MAIN, type = ro;
    CODE:     load = MAIN, type = ro;
    RODATA:   load = MAIN, type = ro;
    DATA:     load = MAIN, type = rw;
    BSS:      load = MAIN, type = bss, define = yes;
}
"""

C64_MAIN = """; {name} - a Commodore 64 program (ca65 + ld65), written with RAD IDE
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
        .byte "HELLO FROM {uname}!", 13, "JOYSTICK 2 OR W A S D MOVES, Q QUITS", 0
"""

C64_C_MAIN = """/* {name} - a Commodore 64 program in C (cc65), written with RAD IDE.
   Prints with conio, moves a ball with the cursor keys / W A S D; Q quits. F5 builds {name}.prg. */
#include <conio.h>
#include <c64.h>

int main(void)
{
    unsigned char x = 20, y = 12, key;

    bordercolor(COLOR_BLUE);
    bgcolor(COLOR_BLACK);
    textcolor(COLOR_YELLOW);
    clrscr();
    cputsxy(2, 1, "Hello from {name}!");
    cputsxy(2, 2, "W A S D moves the ball, Q quits");
    for (;;) {
        cputcxy(x, y, 'O');
        key = cgetc();
        cputcxy(x, y, ' ');
        if ((key == 'd' || key == CH_CURS_RIGHT) && x < 39) ++x;
        if ((key == 'a' || key == CH_CURS_LEFT) && x > 0) --x;
        if ((key == 's' || key == CH_CURS_DOWN) && y < 24) ++y;
        if ((key == 'w' || key == CH_CURS_UP) && y > 4) --y;
        if (key == 'q') break;
    }
    clrscr();
    return 0;
}
"""

C64_ACME_MAIN = """; {name} - a Commodore 64 program for the ACME assembler, written with RAD IDE
; Build: acme -f cbm -o {name}.prg main.a  (ACME must be in PATH)
        !to "{name}.prg", cbm
        * = $0801
        !word next, 10          ; 10 SYS 2061
        !byte $9e
        !text "2061"
        !byte 0
next    !word 0

CHROUT  = $FFD2
EXTCOL  = $D020

start   ldx #0
-       lda message,x
        beq +
        jsr CHROUT
        inx
        bne -
+       inc EXTCOL
        jmp +
+       rts

message !text "HELLO FROM ACME!", 13, 0
"""

# ============================================================================================ ZX Spectrum
ZX_MAIN = """; {name} - a ZX Spectrum program (sjasmplus), written with RAD IDE
; Prints a message, then O / P move a block along row 12; the border shows the frame count. Space quits.
; F5 builds {name}.tap (a BASIC loader + this code at 32768) and runs it.

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
        db 22, 2, 2, "Hello from {name}!"
        db 22, 4, 2, "O / P move the block"
        db 22, 5, 2, "Space returns to BASIC", 0
column:
        db 0
frames:
        db 0
"""


TEMPLATES: dict[str, list[Template]] = {
    "retro-atari2600": [
        Template("a2600_kernel", "Atari 2600 Game (DASM)",
                 "A complete NTSC frame kernel: VSYNC / VBLANK / 192 lines / overscan with the RIOT timer, a "
                 "smiley sprite moved with the joystick (horizontal positioning with RESP0 / HMOVE), fire "
                 "changes the colour. Builds a 4K cartridge with DASM.", "SP_MediaPlay",
                 [("main.asm", A2600_MAIN), ("atari2600.h", A2600_H)],
                 {"system": "atari2600", "lang": "asm", "main": "main.asm"}, ["main.asm", "atari2600.h"]),
    ],
    "retro-nes": [
        Template("nes_asm", "NES Game (ca65 assembly)",
                 "NROM cartridge (32K PRG + 8K CHR): PPU warm-up, palettes, a sprite through OAM DMA in the NMI, "
                 "controller reading, the D-pad moves the sprite. ca65 + ld65 with its own nes.cfg.",
                 "SP_MediaPlay", [("main.s", NES_MAIN), ("nes.inc", NES_INC), ("nes.cfg", NES_CFG)],
                 {"system": "nes", "lang": "asm", "main": "main.s", "cfg": "nes.cfg"},
                 ["main.s", "nes.inc", "nes.cfg"]),
        Template("nes_c", "NES Game (cc65 C)",
                 "An NES program in C with cc65's NES library: conio text, the joystick driver, waitvsync(). "
                 "Built with cl65 -t nes.", "SP_FileIcon", [("main.c", NES_C_MAIN)],
                 {"system": "nes", "lang": "c", "main": "main.c"}, ["main.c"]),
    ],
    "retro-gameboy": [
        Template("gb_asm", "Game Boy Game (RGBDS)",
                 "A Game Boy ROM: header, LCD off/on in vertical blank, tiles copied to VRAM, a sprite in OAM "
                 "moved with the D-pad. rgbasm + rgblink + rgbfix (logo, title, checksums).", "SP_MediaPlay",
                 [("main.asm", GB_MAIN), ("gb.inc", GB_INC)],
                 {"system": "gameboy", "lang": "asm", "main": "main.asm", "fix": True, "title": "{uname15}"},
                 ["main.asm", "gb.inc"]),
    ],
    "retro-c64": [
        Template("c64_asm", "Commodore 64 (ca65 assembly)",
                 "A .prg with a BASIC SYS line: KERNAL printing, raster-synchronised loop, border colours, "
                 "a ball moved with joystick 2 or W A S D. ca65 + ld65 with its own c64.cfg.", "SP_MediaPlay",
                 [("main.s", C64_MAIN), ("c64.cfg", C64_CFG)],
                 {"system": "c64", "lang": "asm", "main": "main.s", "cfg": "c64.cfg"}, ["main.s", "c64.cfg"]),
        Template("c64_c", "Commodore 64 (cc65 C)",
                 "A C program with cc65's C64 library: conio, colours, keyboard. Built with cl65 -t c64.",
                 "SP_FileIcon", [("main.c", C64_C_MAIN)], {"system": "c64", "lang": "c", "main": "main.c"},
                 ["main.c"]),
        Template("c64_acme", "Commodore 64 (ACME)",
                 "The same idea for the ACME cross assembler (needs acme.exe in PATH; not downloaded).",
                 "SP_FileDialogContentsView", [("main.a", C64_ACME_MAIN)],
                 {"system": "c64", "lang": "acme", "main": "main.a"}, ["main.a"]),
    ],
    "retro-zx": [
        Template("zx_asm", "ZX Spectrum (sjasmplus)",
                 "A Z80 program at 32768: ROM CLS / channel 2 / rst $10 printing, HALT-synchronised loop, border "
                 "colours with OUT ($FE), keyboard half-rows. Builds a .tap with a BASIC loader.", "SP_MediaPlay",
                 [("main.asm", ZX_MAIN)], {"system": "zx", "lang": "asm", "main": "main.asm", "org": 32768,
                                           "entry": "start"}, ["main.asm"]),
    ],
}

BY_ID = {t.id: t for ts in TEMPLATES.values() for t in ts}


def render(text: str, name: str) -> str:
    import re
    ident = re.sub(r"\W", "_", name)
    up = name.upper()
    return (text.replace("{name}", name).replace("{uname15}", re.sub(r"[^A-Z0-9 ]", "", up)[:15])
            .replace("{uname}", re.sub(r"[^A-Z0-9 ]", " ", up)).replace("{ident}", ident))
