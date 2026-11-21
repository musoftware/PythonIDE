# Retro development (slice "dev")

Tests and sample projects of the retro game projects: Atari 2600 (DASM), NES (cc65 / ca65), Game Boy (RGBDS),
Commodore 64 (cc65 / ca65, ACME) and ZX Spectrum (sjasmplus), the 6502 / SM83 / Z80 disassemblers and
"Disassemble ROM into Project". Details: [docs/RETRO.md](../../../../docs/RETRO.md), section "Retro development".

## Licences

Every program, ROM and byte in this folder was written for RAD IDE (original homebrew) and may be used freely
(CC0). No commercial ROM is used or needed. The toolchains are downloaded by the IDE from their official release
pages on first use: DASM (GPL-2.0), cc65 (zlib), RGBDS (MIT), sjasmplus (BSD-3-Clause); they run as external
programs.

## Tests

| Script | What it checks |
|---|---|
| `check_disasm.py` | (no Qt) decoders vs hand-assembled bytes (6502 incl. undocumented opcodes, SM83, Z80 with CB / ED / DD / FD / DDCB prefixes and undocumented forms), cycle counts, the Error List parsers of DASM / ca65 / ld65 / cc65 / RGBDS / sjasmplus / ACME, the TAP writer, and **round trips** of synthetic ROMs written for the test: 2600 4K / 2K (mirror addresses) / F8 8K bank switching, NES NROM-128 with CHR ROM, C64 PRG with a BASIC SYS line, Game Boy 32K (ldh vs ld [$FF44], banks), ZX .tap (with and without undocumented Z80 code) - disassemble, reassemble with the real assembler, compare byte for byte; hints.json (code / label / comment) with Re-disassemble. 137 checks. |
| `check_templates.py` | (no Qt) every New Project template: create, build with no warnings, output format (iNES header, Game Boy logo and checksums, PRG load address, TAP blocks), an injected mistake gives an Error List row with the right file and line, the built ROM disassembles back into a byte-identical project; editor support (completions, hover with opcodes / cycles / flags and hardware registers, numbers, go to definition across files, references, outline, signature help, Monarch grammars). 52 checks (ACME skipped unless acme.exe is in PATH). |
| `test_ide.py` | (IDE, QSettings `RADIDE-TEST`, `widget.grab()` screenshots) New Project > Retro Games, a 2600 project opened with the editor keeping the 6502 plugin (no x86 overlay), Tools > Retro > Retro Development menu, Rebuild Check, Error List row of a DASM error, the Disassemble ROM dialog end to end (byte-identical), Retro Toolchains dialog, Arabic strings. 13 checks. |

`--offline` makes the first two skip (with a reason) whatever needs a toolchain that is not installed yet.

## Sample projects (`Projects/`)

| Folder | System / toolchain | What it shows |
|---|---|---|
| `Atari2600Smiley` | Atari 2600, DASM | NTSC kernel (VSYNC / VBLANK with TIM64T / 192 lines / overscan), joystick-moved sprite, horizontal positioning with RESP0 + HMOVE. |
| `NesSprite` | NES, ca65 + ld65 | NROM cartridge with its own nes.cfg, PPU warm-up, palette, OAM DMA in the NMI, controller reading, CHR tiles. |
| `NesHelloC` | NES, cc65 C | conio text + joystick driver of cc65's NES library. |
| `GameBoySmiley` | Game Boy, RGBDS | Header, LCD off/on in vblank, tile copy to VRAM, sprite in OAM moved with the D-pad, rgbfix. |
| `C64Ball` | C64, ca65 + ld65 | BASIC SYS line, KERNAL printing, raster-synchronised loop, joystick 2 / W A S D, colour RAM. |
| `C64HelloC` | C64, cc65 C | conio, colours, keyboard. |
| `ZxBlock` | ZX Spectrum, sjasmplus | ROM CLS / channel 2 / rst $10, HALT loop, border with OUT ($FE), keyboard half-rows; a .tap with a BASIC loader. |
| `Disasm2600Smiley` | Atari 2600, DASM | "Disassemble ROM into Project" of the Atari2600Smiley ROM (rom/Smiley2600.bin, our own): labels, TIA / RIOT names, `ram_XX`, vectors; F5 rebuilds it byte-identical. |

Open a folder with File > Open Project and press F5: the IDE downloads the assembler the first time, builds
the ROM (errors in the Error List) and runs it in the emulator chosen by the emulator slice (Tools > Retro >
Emulators...). Build output (`_build/`, the ROM) is not kept here.
