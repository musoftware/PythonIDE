"""Firmware & ECU workbench (Qt): one WinOLS-like layout over the firmware sub-packages (docs/FIRMWARE.md "UI").

* ``adapters``  - thin bridge to radide/firmware/{formats,cpu,disasm,maps,checksum,project}; every call falls back
                  to a small built-in implementation while a sub-package is missing (no Qt).
* ``eeprom``    - generic serial-EEPROM dump recognition (24Cxx / 93Cxx / 95xxx sizes) + byte/word-swap views.
* ``demo``      - synthetic firmware images with known calibration maps and checksums (tests, demo projects).
* ``workbench`` - FirmwareWorkbench: project tree, hex / map / 2D / disassembly / analysis tabs, properties,
                  potential maps / differences / checksum report / output panels, toolbar (Qt).
* ``mapview``   - map table editor and the 2D curve view (Qt).
"""
