"""Hardware registers, ROM routines and system variables of the retro systems, with descriptions written for
RAD IDE. The names are the conventional ones programmers use for these addresses (TIA / RIOT, NES PPU / APU,
Game Boy I/O, VIC-II / SID / CIA, KERNAL, ZX Spectrum system variables) so disassemblies read like the books.

``REGS[system]`` = list of ``Reg(addr, name, access, text)``; access "r", "w" or "rw" decides which name an
instruction gets when two registers share one address (the 2600 TIA reads collision latches at the addresses it
writes video registers to). ``lookup(system, addr, access)`` -> Reg | None.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reg:
    addr: int
    name: str
    access: str          # "r" | "w" | "rw" | "call" (a ROM routine) | "var" (a RAM variable)
    text: str


def _mk(rows, access="rw"):
    out = []
    for row in rows:
        addr, name, text = row[:3]
        acc = row[3] if len(row) > 3 else access
        out.append(Reg(addr, name, acc, text))
    return out


ATARI2600 = _mk([
    (0x00, "VSYNC", "Vertical sync: write %00000010 to start the 3 VSYNC lines, 0 to end them.", "w"),
    (0x01, "VBLANK", "Vertical blank: bit 1 turns the beam off; bits 6/7 control the paddle / trigger latches.", "w"),
    (0x02, "WSYNC", "Wait for the end of the scanline: any write halts the CPU until the next line starts.", "w"),
    (0x03, "RSYNC", "Reset the horizontal sync counter (rarely used).", "w"),
    (0x04, "NUSIZ0", "Player 0 copies / size and missile 0 width.", "w"),
    (0x05, "NUSIZ1", "Player 1 copies / size and missile 1 width.", "w"),
    (0x06, "COLUP0", "Colour-luminance of player 0 and missile 0.", "w"),
    (0x07, "COLUP1", "Colour-luminance of player 1 and missile 1.", "w"),
    (0x08, "COLUPF", "Colour-luminance of the playfield and the ball.", "w"),
    (0x09, "COLUBK", "Background colour-luminance.", "w"),
    (0x0A, "CTRLPF", "Playfield control: bit 0 reflect, bit 1 score mode, bit 2 priority, bits 4-5 ball size.", "w"),
    (0x0B, "REFP0", "Reflect player 0 (bit 3) - draw the sprite mirrored.", "w"),
    (0x0C, "REFP1", "Reflect player 1 (bit 3).", "w"),
    (0x0D, "PF0", "Playfield register 0 (bits 4-7, drawn first).", "w"),
    (0x0E, "PF1", "Playfield register 1 (bits 7-0).", "w"),
    (0x0F, "PF2", "Playfield register 2 (bits 0-7).", "w"),
    (0x10, "RESP0", "Reset player 0: it is placed at the current beam position.", "w"),
    (0x11, "RESP1", "Reset player 1 position.", "w"),
    (0x12, "RESM0", "Reset missile 0 position.", "w"),
    (0x13, "RESM1", "Reset missile 1 position.", "w"),
    (0x14, "RESBL", "Reset ball position.", "w"),
    (0x15, "AUDC0", "Audio control (waveform) of channel 0.", "w"),
    (0x16, "AUDC1", "Audio control (waveform) of channel 1.", "w"),
    (0x17, "AUDF0", "Audio frequency divider of channel 0 (0-31).", "w"),
    (0x18, "AUDF1", "Audio frequency divider of channel 1.", "w"),
    (0x19, "AUDV0", "Audio volume of channel 0 (0-15).", "w"),
    (0x1A, "AUDV1", "Audio volume of channel 1.", "w"),
    (0x1B, "GRP0", "Graphics of player 0: the 8 pixels of the current line.", "w"),
    (0x1C, "GRP1", "Graphics of player 1.", "w"),
    (0x1D, "ENAM0", "Enable missile 0 (bit 1).", "w"),
    (0x1E, "ENAM1", "Enable missile 1 (bit 1).", "w"),
    (0x1F, "ENABL", "Enable the ball (bit 1).", "w"),
    (0x20, "HMP0", "Horizontal motion of player 0 (high nibble, -8..+7), applied by HMOVE.", "w"),
    (0x21, "HMP1", "Horizontal motion of player 1.", "w"),
    (0x22, "HMM0", "Horizontal motion of missile 0.", "w"),
    (0x23, "HMM1", "Horizontal motion of missile 1.", "w"),
    (0x24, "HMBL", "Horizontal motion of the ball.", "w"),
    (0x25, "VDELP0", "Vertical delay of player 0 (bit 0).", "w"),
    (0x26, "VDELP1", "Vertical delay of player 1.", "w"),
    (0x27, "VDELBL", "Vertical delay of the ball.", "w"),
    (0x28, "RESMP0", "Lock missile 0 to player 0 (bit 1).", "w"),
    (0x29, "RESMP1", "Lock missile 1 to player 1.", "w"),
    (0x2A, "HMOVE", "Apply the horizontal motion registers (write right after WSYNC).", "w"),
    (0x2B, "HMCLR", "Clear all horizontal motion registers.", "w"),
    (0x2C, "CXCLR", "Clear all collision latches.", "w"),
    (0x00, "CXM0P", "Collisions: missile 0 with player 1 (bit 7) / player 0 (bit 6).", "r"),
    (0x01, "CXM1P", "Collisions: missile 1 with player 0 / player 1.", "r"),
    (0x02, "CXP0FB", "Collisions: player 0 with playfield (bit 7) / ball (bit 6).", "r"),
    (0x03, "CXP1FB", "Collisions: player 1 with playfield / ball.", "r"),
    (0x04, "CXM0FB", "Collisions: missile 0 with playfield / ball.", "r"),
    (0x05, "CXM1FB", "Collisions: missile 1 with playfield / ball.", "r"),
    (0x06, "CXBLPF", "Collision: ball with playfield (bit 7).", "r"),
    (0x07, "CXPPMM", "Collisions: player 0 with player 1 (bit 7), missile 0 with missile 1 (bit 6).", "r"),
    (0x08, "INPT0", "Paddle 0 input (bit 7).", "r"),
    (0x09, "INPT1", "Paddle 1 input.", "r"),
    (0x0A, "INPT2", "Paddle 2 input.", "r"),
    (0x0B, "INPT3", "Paddle 3 input.", "r"),
    (0x0C, "INPT4", "Joystick 0 fire button (bit 7 = 0 when pressed).", "r"),
    (0x0D, "INPT5", "Joystick 1 fire button.", "r"),
    (0x280, "SWCHA", "Joystick directions: bits 7-4 player 0 (right, left, down, up), 0 = pressed.", "rw"),
    (0x281, "SWACNT", "Data direction of port A (SWCHA).", "rw"),
    (0x282, "SWCHB", "Console switches: bit 0 Reset, bit 1 Select, bit 3 Colour/BW, bits 6/7 difficulty.", "rw"),
    (0x283, "SWBCNT", "Data direction of port B.", "rw"),
    (0x284, "INTIM", "RIOT timer value (read it to know how long until the timer ends).", "r"),
    (0x285, "TIMINT", "RIOT timer interrupt flag (bit 7 = timer expired).", "r"),
    (0x294, "TIM1T", "Start the RIOT timer, 1 cycle per tick.", "w"),
    (0x295, "TIM8T", "Start the RIOT timer, 8 cycles per tick.", "w"),
    (0x296, "TIM64T", "Start the RIOT timer, 64 cycles per tick (the usual VBLANK / overscan timer).", "w"),
    (0x297, "T1024T", "Start the RIOT timer, 1024 cycles per tick.", "w"),
])

NES = _mk([
    (0x2000, "PPUCTRL", "PPU control: NMI enable (bit 7), sprite size, pattern tables, VRAM increment, nametable.", "w"),
    (0x2001, "PPUMASK", "PPU mask: show background / sprites, left 8 pixels, greyscale, colour emphasis.", "w"),
    (0x2002, "PPUSTATUS", "PPU status: bit 7 vblank, bit 6 sprite 0 hit; reading resets the PPUADDR latch.", "r"),
    (0x2003, "OAMADDR", "Sprite memory (OAM) address.", "w"),
    (0x2004, "OAMDATA", "Sprite memory data.", "rw"),
    (0x2005, "PPUSCROLL", "Scroll position: write X, then Y.", "w"),
    (0x2006, "PPUADDR", "VRAM address: write the high byte, then the low byte.", "w"),
    (0x2007, "PPUDATA", "VRAM data at PPUADDR (the address then moves by 1 or 32).", "rw"),
    (0x4000, "SQ1_VOL", "Pulse 1: duty, loop, constant volume, volume.", "w"),
    (0x4001, "SQ1_SWEEP", "Pulse 1 sweep unit.", "w"),
    (0x4002, "SQ1_LO", "Pulse 1 timer low byte.", "w"),
    (0x4003, "SQ1_HI", "Pulse 1 length counter / timer high bits.", "w"),
    (0x4004, "SQ2_VOL", "Pulse 2: duty, loop, constant volume, volume.", "w"),
    (0x4005, "SQ2_SWEEP", "Pulse 2 sweep unit.", "w"),
    (0x4006, "SQ2_LO", "Pulse 2 timer low byte.", "w"),
    (0x4007, "SQ2_HI", "Pulse 2 length counter / timer high bits.", "w"),
    (0x4008, "TRI_LINEAR", "Triangle linear counter.", "w"),
    (0x400A, "TRI_LO", "Triangle timer low byte.", "w"),
    (0x400B, "TRI_HI", "Triangle length counter / timer high bits.", "w"),
    (0x400C, "NOISE_VOL", "Noise volume / envelope.", "w"),
    (0x400E, "NOISE_LO", "Noise mode and period.", "w"),
    (0x400F, "NOISE_HI", "Noise length counter.", "w"),
    (0x4010, "DMC_FREQ", "DMC (sample) IRQ, loop, rate.", "w"),
    (0x4011, "DMC_RAW", "DMC direct 7-bit output level.", "w"),
    (0x4012, "DMC_START", "DMC sample address ($C000 + n*64).", "w"),
    (0x4013, "DMC_LEN", "DMC sample length (n*16 + 1 bytes).", "w"),
    (0x4014, "OAMDMA", "Sprite DMA: write the page number ($02 copies $0200-$02FF to OAM).", "w"),
    (0x4015, "SND_CHN", "Sound channels enable / status.", "rw"),
    (0x4016, "JOY1", "Controller 1: write 1 then 0 to latch the buttons, then read 8 times (A B Select Start Up "
                     "Down Left Right).", "rw"),
    (0x4017, "JOY2", "Controller 2 (read); APU frame counter (write).", "rw"),
])

GAMEBOY = _mk([
    (0xFF00, "rP1", "Joypad: select the button row (bits 4/5), read the 4 buttons (0 = pressed)."),
    (0xFF01, "rSB", "Serial transfer data."), (0xFF02, "rSC", "Serial transfer control."),
    (0xFF04, "rDIV", "Divider register (counts up at 16384 Hz; any write resets it)."),
    (0xFF05, "rTIMA", "Timer counter (interrupt on overflow)."), (0xFF06, "rTMA", "Timer reload value."),
    (0xFF07, "rTAC", "Timer control: enable and speed."), (0xFF0F, "rIF", "Interrupt flags (requests)."),
    (0xFF10, "rNR10", "Sound channel 1 sweep."), (0xFF11, "rNR11", "Channel 1 duty / length."),
    (0xFF12, "rNR12", "Channel 1 volume envelope."), (0xFF13, "rNR13", "Channel 1 period low."),
    (0xFF14, "rNR14", "Channel 1 period high / trigger."), (0xFF16, "rNR21", "Channel 2 duty / length."),
    (0xFF17, "rNR22", "Channel 2 volume envelope."), (0xFF18, "rNR23", "Channel 2 period low."),
    (0xFF19, "rNR24", "Channel 2 period high / trigger."), (0xFF1A, "rNR30", "Channel 3 (wave) on/off."),
    (0xFF1B, "rNR31", "Channel 3 length."), (0xFF1C, "rNR32", "Channel 3 output level."),
    (0xFF1D, "rNR33", "Channel 3 period low."), (0xFF1E, "rNR34", "Channel 3 period high / trigger."),
    (0xFF20, "rNR41", "Channel 4 (noise) length."), (0xFF21, "rNR42", "Channel 4 volume envelope."),
    (0xFF22, "rNR43", "Channel 4 frequency / randomness."), (0xFF23, "rNR44", "Channel 4 trigger."),
    (0xFF24, "rNR50", "Master volume."), (0xFF25, "rNR51", "Sound panning (left / right per channel)."),
    (0xFF26, "rNR52", "Sound on/off (bit 7) and channel status."),
    (0xFF40, "rLCDC", "LCD control: bit 7 LCD on, bit 1 sprites on, bit 0 background on, tile maps / data."),
    (0xFF41, "rSTAT", "LCD status: mode and STAT interrupt sources."),
    (0xFF42, "rSCY", "Background scroll Y."), (0xFF43, "rSCX", "Background scroll X."),
    (0xFF44, "rLY", "Current scanline (0-153; 144-153 = vertical blank)."),
    (0xFF45, "rLYC", "Scanline compare (STAT interrupt when LY = LYC)."),
    (0xFF46, "rDMA", "OAM DMA: write the high byte of the source ($C1 copies $C100-$C19F)."),
    (0xFF47, "rBGP", "Background palette (4 shades, 2 bits each)."),
    (0xFF48, "rOBP0", "Sprite palette 0."), (0xFF49, "rOBP1", "Sprite palette 1."),
    (0xFF4A, "rWY", "Window Y position."), (0xFF4B, "rWX", "Window X position + 7."),
    (0xFF4D, "rKEY1", "CGB speed switch."), (0xFF4F, "rVBK", "CGB VRAM bank."),
    (0xFF51, "rHDMA1", "CGB VRAM DMA source high."), (0xFF52, "rHDMA2", "CGB VRAM DMA source low."),
    (0xFF53, "rHDMA3", "CGB VRAM DMA destination high."), (0xFF54, "rHDMA4", "CGB VRAM DMA destination low."),
    (0xFF55, "rHDMA5", "CGB VRAM DMA length / mode / start."), (0xFF56, "rRP", "CGB infrared port."),
    (0xFF68, "rBCPS", "CGB background palette index."), (0xFF69, "rBCPD", "CGB background palette data."),
    (0xFF6A, "rOCPS", "CGB sprite palette index."), (0xFF6B, "rOCPD", "CGB sprite palette data."),
    (0xFF70, "rSVBK", "CGB WRAM bank."), (0xFFFF, "rIE", "Interrupt enable: VBlank, STAT, Timer, Serial, Joypad."),
    (0x0000, "rRAMG", "MBC: write $0A to enable cartridge RAM, $00 to disable it.", "w"),
    (0x2000, "rROMB0", "MBC: select the ROM bank mapped at $4000-$7FFF.", "w"),
    (0x3000, "rROMB1", "MBC5: ROM bank bit 8.", "w"),
    (0x4000, "rRAMB", "MBC: select the cartridge RAM bank.", "w"),
])

C64 = _mk(
    [(0xD000 + 2 * i, f"SP{i}X", f"Sprite {i} X position (low 8 bits).") for i in range(8)] +
    [(0xD001 + 2 * i, f"SP{i}Y", f"Sprite {i} Y position.") for i in range(8)] + [
        (0xD010, "MSIGX", "Bit 8 of the X positions of the 8 sprites."),
        (0xD011, "SCROLY", "VIC control 1: vertical scroll, 24/25 rows, screen on, bitmap mode, raster bit 8."),
        (0xD012, "RASTER", "Current raster line (read) / raster interrupt line (write)."),
        (0xD013, "LPENX", "Light pen X."), (0xD014, "LPENY", "Light pen Y."),
        (0xD015, "SPENA", "Sprite enable bits."),
        (0xD016, "SCROLX", "VIC control 2: horizontal scroll, 38/40 columns, multicolour mode."),
        (0xD017, "YXPAND", "Sprite double height bits."),
        (0xD018, "VMCSB", "Screen and character memory addresses."),
        (0xD019, "VICIRQ", "VIC interrupt flags (write 1 to acknowledge)."),
        (0xD01A, "IRQMSK", "VIC interrupt enable."),
        (0xD01B, "SPBGPR", "Sprite-background priority."), (0xD01C, "SPMC", "Sprite multicolour bits."),
        (0xD01D, "XXPAND", "Sprite double width bits."),
        (0xD01E, "SPSPCL", "Sprite-sprite collisions (reading clears)."),
        (0xD01F, "SPBGCL", "Sprite-background collisions (reading clears)."),
        (0xD020, "EXTCOL", "Border colour."), (0xD021, "BGCOL0", "Background colour."),
        (0xD022, "BGCOL1", "Background colour 1 (multicolour / ECM)."), (0xD023, "BGCOL2", "Background colour 2."),
        (0xD024, "BGCOL3", "Background colour 3."), (0xD025, "SPMC0", "Sprite multicolour 0."),
        (0xD026, "SPMC1", "Sprite multicolour 1."),
    ] + [(0xD027 + i, f"SP{i}COL", f"Sprite {i} colour.") for i in range(8)] +
    [row for v in range(3) for row in (
        (0xD400 + 7 * v, f"FRELO{v + 1}", f"SID voice {v + 1} frequency low."),
        (0xD401 + 7 * v, f"FREHI{v + 1}", f"SID voice {v + 1} frequency high."),
        (0xD402 + 7 * v, f"PWLO{v + 1}", f"SID voice {v + 1} pulse width low."),
        (0xD403 + 7 * v, f"PWHI{v + 1}", f"SID voice {v + 1} pulse width high."),
        (0xD404 + 7 * v, f"VCREG{v + 1}", f"SID voice {v + 1} control: gate (bit 0), waveform (bits 4-7)."),
        (0xD405 + 7 * v, f"ATDCY{v + 1}", f"SID voice {v + 1} attack / decay."),
        (0xD406 + 7 * v, f"SUREL{v + 1}", f"SID voice {v + 1} sustain / release."))] + [
        (0xD415, "CUTLO", "SID filter cutoff low bits."), (0xD416, "CUTHI", "SID filter cutoff high byte."),
        (0xD417, "RESON", "SID filter resonance and routing."),
        (0xD418, "SIGVOL", "SID volume (bits 0-3) and filter mode."),
        (0xD419, "POTX", "Paddle X."), (0xD41A, "POTY", "Paddle Y."),
        (0xD41B, "RANDOM", "Voice 3 oscillator output (a random number source with noise)."),
        (0xD41C, "ENV3", "Voice 3 envelope output."),
        (0xDC00, "CIAPRA", "CIA 1 port A: keyboard column select / joystick 2 (0 = pressed)."),
        (0xDC01, "CIAPRB", "CIA 1 port B: keyboard row read / joystick 1."),
        (0xDC02, "CIDDRA", "CIA 1 data direction A."), (0xDC03, "CIDDRB", "CIA 1 data direction B."),
        (0xDC04, "TIMALO", "CIA 1 timer A low."), (0xDC05, "TIMAHI", "CIA 1 timer A high."),
        (0xDC06, "TIMBLO", "CIA 1 timer B low."), (0xDC07, "TIMBHI", "CIA 1 timer B high."),
        (0xDC0D, "CIAICR", "CIA 1 interrupt control (write $7F to stop the timer IRQs)."),
        (0xDC0E, "CIACRA", "CIA 1 control A."), (0xDC0F, "CIACRB", "CIA 1 control B."),
        (0xDD00, "CI2PRA", "CIA 2 port A: VIC bank (bits 0-1), serial bus."),
        (0xDD01, "CI2PRB", "CIA 2 port B: user port."), (0xDD02, "C2DDRA", "CIA 2 data direction A."),
        (0xDD03, "C2DDRB", "CIA 2 data direction B."), (0xDD0D, "CI2ICR", "CIA 2 interrupt control (NMI)."),
        (0x0001, "R6510", "Processor port: memory configuration (BASIC / KERNAL / I/O visible) and tape."),
        (0xFFD2, "CHROUT", "KERNAL: print the character in A.", "call"),
        (0xFFE4, "GETIN", "KERNAL: get a key from the keyboard buffer into A (0 = none).", "call"),
        (0xFFCF, "CHRIN", "KERNAL: read a character from the input channel.", "call"),
        (0xFFBA, "SETLFS", "KERNAL: set logical file, device, secondary address.", "call"),
        (0xFFBD, "SETNAM", "KERNAL: set the file name (A = length, X/Y = address).", "call"),
        (0xFFC0, "OPEN", "KERNAL: open a logical file.", "call"),
        (0xFFC3, "CLOSE", "KERNAL: close a logical file.", "call"),
        (0xFFD5, "LOAD", "KERNAL: load a file into memory.", "call"),
        (0xFFD8, "SAVE", "KERNAL: save memory to a file.", "call"),
        (0xFFE1, "STOP", "KERNAL: test the RUN/STOP key.", "call"),
        (0xFFF0, "PLOT", "KERNAL: read / set the cursor position (C = 1 read).", "call"),
        (0xFF81, "CINT", "KERNAL: initialise the screen editor and VIC.", "call"),
        (0xE544, "CLRSCR", "KERNAL: clear the screen.", "call"),
        (0xEA31, "IRQ_KERNAL", "The KERNAL's own IRQ handler (jump here at the end of your IRQ).", "call"),
    ])

ZX = _mk([
    (0x0D6B, "ROM_CLS", "ROM: clear the screen.", "call"),
    (0x0DAF, "ROM_CL_ALL", "ROM: clear the whole display and reset the print position.", "call"),
    (0x1601, "ROM_CHAN_OPEN", "ROM: open a channel (A = 2: upper screen) before printing with rst $10.", "call"),
    (0x203C, "ROM_PR_STRING", "ROM: print BC characters from DE.", "call"),
    (0x03B5, "ROM_BEEPER", "ROM: beep - HL = period, DE = duration.", "call"),
    (0x2D2B, "ROM_STACK_BC", "ROM: put BC on the calculator stack.", "call"),
    (0x2DE3, "ROM_PRINT_FP", "ROM: print the number on top of the calculator stack.", "call"),
    (0x5C08, "LAST_K", "System variable: the last key pressed.", "var"),
    (0x5C36, "CHARS", "System variable: address of the character set - 256.", "var"),
    (0x5C48, "BORDCR", "System variable: border colour * 8 (+ the lower screen attributes).", "var"),
    (0x5C78, "FRAMES", "System variable: frame counter (3 bytes, +1 every 1/50 s).", "var"),
    (0x5C7B, "UDG", "System variable: address of the user-defined graphics.", "var"),
    (0x5C8D, "ATTR_P", "System variable: permanent colours (ink / paper / bright / flash).", "var"),
    (0x5C8F, "ATTR_T", "System variable: temporary colours.", "var"),
    (0x4000, "SCREEN", "Display file: 6144 bytes of bitmap ($4000-$57FF, in thirds of 8 character rows).", "var"),
    (0x5800, "ATTRS", "Attribute file: 768 colour cells ($5800-$5AFF): flash, bright, paper, ink.", "var"),
])

# I/O ports (Z80 in / out): hover documentation only
ZX_PORTS = {0xFE: "ULA port $FE - out: border colour (bits 0-2), MIC (bit 3), speaker (bit 4); in: keyboard "
                  "half-row selected by the high byte of the address (bits 0-4, 0 = pressed), EAR (bit 6)",
            0x1F: "Kempston joystick port $1F - bits: right, left, down, up, fire (1 = pressed)",
            0xFD: "AY sound chip on the 128K: $FFFD register select, $BFFD data; $7FFD memory paging"}

REGS: dict[str, list[Reg]] = {"atari2600": ATARI2600, "nes": NES, "gameboy": GAMEBOY, "c64": C64, "zx": ZX}

# zero-page RAM that gets "ram_XX" names in a disassembly (system -> (first, last))
ZP_RAM = {"atari2600": (0x80, 0xFF)}

_INDEX: dict[str, dict[tuple[int, str], Reg]] = {}


def _index(system: str) -> dict[tuple[int, str], Reg]:
    if system not in _INDEX:
        d: dict[tuple[int, str], Reg] = {}
        for r in REGS.get(system, []):
            for acc in ("r", "w"):
                if acc in r.access or r.access in ("rw", "call", "var"):
                    d.setdefault((r.addr, acc), r)
        _INDEX[system] = d
    return _INDEX[system]


def lookup(system: str, addr: int, access: str = "r") -> Reg | None:
    """The register / routine at *addr* for a read ("r"), a write ("w"), "rw" (write name first) or a call."""
    idx = _index(system)
    if access in ("call", ""):
        access = "r"
    if access == "rw":
        return idx.get((addr, "w")) or idx.get((addr, "r"))
    return idx.get((addr, access))


def by_name(system: str) -> dict[str, Reg]:
    return {r.name: r for r in REGS.get(system, [])}


def all_names() -> dict[str, tuple[str, Reg]]:
    """name (lower case) -> (system, Reg) over every system."""
    out: dict[str, tuple[str, Reg]] = {}
    for sysname, regs in REGS.items():
        for r in regs:
            out.setdefault(r.name.lower(), (sysname, r))
    return out
