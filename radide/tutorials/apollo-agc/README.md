# Apollo AGC course (Arabic)

`course.json` + 8 lessons. The AGC programs are original (CC0); the short quotation from Comanche055 in lesson 6
is public domain (US government work, transcribed by the Virtual AGC project).

| Fence | Checked by `tools/check_lessons.py` |
|---|---|
| `agc run` / `agc exercise` / `agc solution` | assembled by RAD IDE's assembler and run in its emulator (radide.agc); a hidden `<!-- test: {...} -->` chooses what is printed (symbols, DSKY line, DSKY at given times, restarts, keys, alarms). With Virtual AGC installed, every block is also assembled by yaYUL and the ropes must match word for word |
| `fortran run` / `exercise` / `solution` | gfortran through radide.tutorials.native; `! #file: name.f` keeps the fixed form |

    python radide/tutorials/apollo-agc/tools/check_lessons.py [-v] [lesson-id-prefix ...]
    python tools/build_chm.py apollo-agc --verify
