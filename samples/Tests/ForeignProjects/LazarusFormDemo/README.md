# LazarusFormDemo - Lazarus LCL form application (test fixture)

`tempconv.lpi` / `tempconv.lpr` + `mainunit.pas/.lfm` (UTF-8, label, edit, button, radio group with LCL
`ChildSizing.*` properties the RAD IDE designer does not know - kept verbatim) + `convert.pas`.

Open `tempconv.lpi` in RAD IDE (File > Open Project...). F5 builds it with `lazbuild` from the portable
Lazarus toolchain (downloaded on demand into `%LOCALAPPDATA%\RADIDE\toolchains\lazarus`) and runs it.
`tempconv.exe --selftest` converts 100 C, writes `SELFTEST 212.0 °F` to `tempconv.selftest.txt` next to the exe and quits.
