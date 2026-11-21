; nes.inc - NES hardware registers (written for RAD IDE)
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
