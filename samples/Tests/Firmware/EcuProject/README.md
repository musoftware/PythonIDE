# ECU / Firmware project tests

`radide/firmware/project`, the `firmware-ecu` language plugin and `radide/features/firmware_project.py`
(docs/FIRMWARE.md "ECU projects"). The tests use only synthetic firmware: the 64 KB demo image written by
`radide/firmware/project/synth.py`, which has no vehicle data, three checksum blocks and three maps.

```
python samples/Tests/Firmware/EcuProject/test_ecu_project_core.py    # no Qt
python samples/Tests/Firmware/EcuProject/qa_ecu_project_ide.py       # the IDE (qh.py, offscreen, widget.grab())
```

## Core test

* The original is copied into the project, made read-only on disk and recorded with SHA-256.
* The project refuses to write the original. A changed original stops the build.
* A map edit breaks only the calibration CRC.
* Versions with notes, and a map-level diff (cells changed, largest change in physical units).
* Build to `.bin`, `.hex` and `.s19`, with the recalculated block named in the report.
* HTML report.
* Restore and delete versions.
* A BPS / IPS export imported into a fresh project gives the same bytes as the built image.
* An Intel HEX original at 0x80000000 builds back to HEX at the same address.
* The command line.
* The New Project templates.
* The workbench adapter reads the project.

Last run: 46/46 passed.

## IDE test

* The New Project dialog has the Firmware group.
* The safety notice is shown exactly once.
* Solution Explorer node and the Project > ECU Project menu.
* A hex-editor save recalculates the checksum on save.
* The original opens read-only.
* The finder thread locates the three demo checksums.
* A candidate is added as a block, and the profile is exported.
* Versions with a map-level diff.
* Build, Build Settings -> Intel HEX, HTML report, BPS export / import.
* The Checksum Toolkit.
* Arabic UI.

The screenshots are saved in `shots/`.
