# Retro games course (Arabic)

`course.json` + 10 lessons (`NN-slug.md`). Everything in the lessons is original code (CC0); no commercial ROM is
used or downloaded.

Block kinds besides the usual `python run` / `exercise` / `solution`, `text output` and `quiz`:

| Fence | Checked by `tools/check_lessons.py` |
|---|---|
| `dasm run` / `dasm exercise` / `dasm solution` | Atari 2600 program -> main.asm of a new "Atari 2600 Game (DASM)" project, built with DASM, then run in `tools/sim2600.py` (6502 + 2600 bus): `scanlines: N`, `$80 = V`, `$81 = $XX`, `COLUBK = $XX` |
| `ca65 run` | NES program -> main.s of a new "NES Game (ca65 assembly)" project; prints the iNES header |
| `rgbds run` | Game Boy program -> main.asm of a new "Game Boy Game (RGBDS)" project; prints title, logo and checksums |

A hidden `<!-- test: {"frames": 10, "hold": "right", "ram": ["$80"], "ramhex": ["$82"], "tia": ["COLUBK"]} -->`
right before a `dasm` block says what the simulator prints. The lesson viewer shows these blocks as code (the
learner pastes them into a project and presses F5).

    python radide/tutorials/retro-games/tools/check_lessons.py [-v] [lesson-id-prefix ...]
    python tools/build_chm.py retro-games --verify
