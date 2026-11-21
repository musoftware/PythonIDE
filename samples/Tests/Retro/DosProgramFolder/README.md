# DosProgramFolder - "Open Folder" on a DOS program

This folder stands in for the folder of an old DOS game or application **you own**. It contains only these files:
* `PLAY.COM`: the 8086 homebrew program from `../Emulators/homebrew.py` (original, CC0). It prints `RADIDE DOS OK`.
* `SETUP.BAT`: a batch file.

Do **not** add commercial games you do not own to this repository.

* File > Open Folder on this folder: RAD IDE offers "DOS program (DOSBox-X, 1 DOS executable, start PLAY.COM)". Accept
  it and RAD IDE writes only `project.radproj`, with a `"dos"` block.
* Press F5: DOSBox-X starts `PLAY.COM`, using the configuration RAD IDE generates in `.radide/dosbox-x.conf`.
* Project > DOS Settings... sets these options:
  * the program to start
  * CPU cycles (`auto`, `max`, `fixed 3000` for 8088-era games ...)
  * machine and memory
  * sound card (SB16, SB Pro 2, GUS, none)
  * a DOS toolchain folder
  * close DOSBox-X when the program ends
