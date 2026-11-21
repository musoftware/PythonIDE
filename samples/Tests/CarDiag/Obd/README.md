# OBD-II scan tool - tests

- `test_obd_core.py` - the OBD layer without Qt: every mode 01 PID formula against hand-computed values,
  supported-PID bitmaps, multi-ECU answers, DTCs (03 / 07 / 0A), clear (04), freeze frames (02), readiness,
  mode 06 limits, mode 09, CSV logging and playback, end to end against the Demo vehicle and the ELM327 simulator.
- `qa_scan_ide.py` - the real IDE (`samples/Tests/QA/Integration/qh.py`, QSettings org RADIDE-TEST, screenshots
  with `widget.grab()`); run again with `QA_LANG=ar QA_THEME=dark` for Arabic + dark.

Try it by hand: Tools > Car Diagnostics... > Demo car > Read Codes, select P0301 for the explanation, Live Data >
Start, then Clear Codes... to see the confirmation (readiness monitors reset, the permanent code stays).
