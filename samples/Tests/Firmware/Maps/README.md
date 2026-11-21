# Calibration maps - tests and sample data

| File | What |
|---|---|
| `test_maps_core.py` | No Qt: map finder, data types, editing operations, differences, compare / copy, JSON / CSV, A2L, TunerStudio ini / msq. |
| `qa_maps_ide.py` | The real IDE through `samples/Tests/QA/Integration/qh.py` (QSettings org `RADIDE-TEST`), screenshots in `%TEMP%\radide-qa\shots\maps_*.png`. |
| `sample_ecu.a2l` | An original ASAP2 file written for these tests (no real ECU data). |
| `sample_ecu.py` | Builds the 64 KB synthetic image that `sample_ecu.a2l` describes (`python sample_ecu.py` writes `sample_ecu.bin`). |
| `download_rusefi.py` | Downloads the rusEFI TunerStudio ini and two `.msq` tunes from the official repository github.com/rusefi/rusefi (GPL-3.0) into `%TEMP%\radide-qa\rusefi` (or `RUSEFI_DIR`). Nothing downloaded is committed. |

All firmware images here are synthetic (`radide/firmware/maps/synth.py`, `sample_ecu.py`). No manufacturer firmware
is downloaded or used.

Try it: Tools > Firmware & ECU > Calibration Maps > Open Binary in Map Editor..., open `sample_ecu.bin`, then
Import > ASAP2 / A2L... and choose `sample_ecu.a2l`.
