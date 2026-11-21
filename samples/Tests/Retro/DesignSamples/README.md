# Retro game design samples

All art is original (CC0), drawn by `make_samples.py` (run it again to recreate the files; `--gen` also writes
the generated code into `gen/<name>/`).

| file | designer | what |
|---|---|---|
| `Castle.a26scr` | Atari 2600 Screen | castle towers in the playfield (mirrored), sunset colour bands per scan line, a knight (player 0) and a double-size dragon (player 1), the ball |
| `Meadow.nesscr` | NES Screen / Level | a 3-screen level: ground with gaps, brick platforms with coins, pipes, clouds, a title; hero metasprite + 3 enemies; D-pad scrolls |
| `Town.gbmap` | Game Boy Map | houses and a road on the background, a HUD (HP / GOLD) in the window at the bottom, two sprites |
| `Cave.m13scr` | DOS Mode 13h Screen | stone tiles over a dark gradient, a water pool, the player (arrow keys) and two slimes |

Open one with Tools > Retro > Game Designers > Open Game Design... (or File > Open), then **Build && Run**:
DASM + Stella, ca65 / ld65 + Mesen, RGBDS + mGBA, NASM / FreeBASIC / OpenWatcom + DOSBox-X (the Properties grid's
`target` chooses the DOS language when nothing is selected). Saving regenerates the code in `gen/<name>/`.
