; (c) 2026 Musoftware - https://musoftwares.com - MIT License
; atari2600.h - Atari 2600 hardware registers (written for RAD IDE)
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
