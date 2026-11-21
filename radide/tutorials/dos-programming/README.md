# DOS programming course (dos-programming): block format and tests

11 Arabic lessons (`NN-slug.md`, listed in `course.json`): DOS and DOSBox-X, QBasic with FreeBASIC, Pascal with
Crt, C with Open Watcom and the B800 screen, 16-bit assembly and interrupts, the text-mode form designer, events
and code, ANSI art, mode 13h graphics and the game designers, running old programs and games you own, and a final
project. The CHM book is `docs/chm/RADIDE_DOS_PROGRAMMING_ar.chm` (`python tools/build_chm.py dos-programming
--verify`).

| Info string | Meaning |
|---|---|
| ```` ```dos-qbasic run ```` | a whole `MAIN.BAS` (New Project > DOS > QBasic / QuickBASIC), built with FreeBASIC for DOS (`-lang qb`) |
| ```` ```dos-pascal run ```` | a whole `MAIN.PAS` (Turbo Pascal-style), Free Pascal i8086-msdos `-Mtp` |
| ```` ```dos-c run ```` | a whole `MAIN.C` (Turbo C-style), Open Watcom 16-bit; `tcconio.h` added for conio calls |
| ```` ```dos-asm run ```` | a whole `MAIN.ASM` (DOS Assembly, MASM syntax), JWasm |
| ```` ```dos-batch run ```` | a whole `MAIN.BAT` |
| ```` ```text output ```` after it | must appear line for line in what the program wrote to standard output, or on its text screen |
| ```` ```qb ````, ```` ```dos-pascal ```` (no `run`), ```` ```text ```` | snippets, not run |

The tutorial engine does not know these languages: it shows the blocks as plain code without a "جرّبه" button
(the lessons tell the learner to paste them into the project's main file).

Hidden `<!-- test: {...} -->` right before a block:

* `"keys"`: typed for the program before it starts (RADKEYS syntax: `~` Enter, `` ` `` Esc, `_` Space);
* `"screen": true`: standard output is not redirected and only the text screen is compared (programs that draw
  with `LOCATE` / `COLOR`, or whose typed input must show);
* `"mode13": true`: a mode 13h frame must be captured (RADCAP) when the program returns to text mode;
* `"com": true`: build a `.COM`;
* `"error_line": N`: the build must fail with an Error List row at line N of the main file;
* `"build_only": true`, `"timeout": seconds`.

## Testing

    python radide/tutorials/dos-programming/tools/check_lessons.py          # all lessons
    python radide/tutorials/dos-programming/tools/check_lessons.py 03 -v    # one lesson, list every block

Every runnable block is written into a fresh DOS project (`radide.retro.dos` plugin), built with the free compiler
(downloaded on first use) and run headless in DOSBox-X (`radide.retro.dos.dosbox.capture_text`). Missing tools
are reported as UNCHECKED. Quiz JSON is validated.

## Facts the lessons rely on

- FreeBASIC `-lang qb` prints a space before positive numbers, and after integers only (QBasic prints it after
  every number): lesson 10 uses `STR$` so that the output is the same in both.
- With standard output redirected, FreeBASIC programs write nothing to the screen (`LOCATE` / `COLOR` are lost),
  and DOS input echo is not in the file: such blocks use `"screen": true`.
- Crt (Free Pascal), conio and direct B800 writes (Open Watcom) always reach the screen.
- FreeBASIC graphics (`SCREEN 13`) frames are not captured; the QBasic graphics block is checked by its text output
  after `SCREEN 0`.
