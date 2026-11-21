# DOS development + DOS / retro designers: end-to-end QA

`qa_dos_e2e.py` drives the real IDE (qh.py harness: QSettings org `RADIDE-TEST`, offscreen, screenshots with
`widget.grab()` only) the way a user works:

| phase | what |
|---|---|
| `dos` | File > New Project (the real dialog) for QBasic, Pascal, C, assembly .COM and batch -> Tools > Retro > DOS Programming > Build DOS Program (real MZ / COM) -> Run with Captured Output (keys typed) -> Show Last DOS Screen; a windowed `python -m radide.retro.dos.run` that ends by itself |
| `old` | File > Open Folder on `../DOSOldSources` (MoonLander, TurboPascalSort, TurboCStars) -> DOS project -> build without changing the sources -> run |
| `tui` | DOS Text-Mode Forms App for FreeBASIC, Pascal, C, asm: the designer, a TextBox and a Button drawn with the toolbox, a handler from a double-click, user code, build, keyboard and a mouse click (RADMOUSE) in DOSBox-X = simulator; Build && Run in a DOSBox-X window (stopped again); the QuickBASIC 4.5 dialect without BC.EXE explains why it cannot build |
| `ansi` | the ANSI editor: box, text and fill with mouse / keys, .ANS (SAUCE) and .BIN round trips, PNG, File > Open |
| `game` | Tools > Retro > Game Designers: Atari 2600, NES (2 screens), Game Boy, DOS mode 13h -> Build && Run with the checks -> Stella / Mesen / mGBA / DOSBox-X started and stopped |
| `i18n` | the DOS / designer menus are translated (Arabic run) and no DOS / designer string seen on screen is missing from ar.json (`missing_<lang>.txt` lists everything untranslated) |

    python samples/Tests/Retro/DOSQA/qa_dos_e2e.py [phases]
    set QA_LANG=ar & set QA_THEME=dark & python samples/Tests/Retro/DOSQA/qa_dos_e2e.py

Needs the DOS toolchains and DOSBox-X already installed (`../DOSDev/test_dos_toolchains.py` downloads them) and the
retro toolchains / emulators for the game phase. Results on the development machine: English 87/87, Arabic + dark
see the final report of the QA run.
