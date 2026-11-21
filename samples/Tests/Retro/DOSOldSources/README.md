# Old-style DOS sources (original RAD IDE samples)

Programs written the way 1980s / 1990s DOS programs were written, to try **File > Open Folder** on old sources:

* `MoonLander/MOONLAND.BAS` - line-numbered BASIC (GOTO, GOSUB, INPUT); FreeBASIC `-lang qb` builds it.
* `TurboCStars/STARS.C` - Turbo C: `clrscr`, `gotoxy`, `textcolor`, `cprintf`, `<graphics.h>` with
  `initgraph(&gd, &gm, "C:\TC\BGI")`, `random`, `randomize`. Open Watcom builds it with RAD IDE's `tcconio.h`
  and BGI subset (`graphics.h` -> `tcgraph.h`, no .BGI driver needed); the build lists what was replaced.
* `TurboPascalSort/SORTDEMO.PAS` - Turbo Pascal: records, typed constants, `Crt`, `Dos.GetTime`; Free Pascal (TP mode).
* `TasmCount/COUNT.ASM` - MASM / TASM: `DOSSEG`, `.MODEL SMALL`, `INT 21h`; JWasm.

All files are CRLF / plain ASCII like the originals would be. `../DOSDev/test_dos_compat.py` builds and runs them.
