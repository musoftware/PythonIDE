# Car service functions - tests

- `test_service_core.py` - the service core against the Demo car simulator (no Qt, simulated clock): routines,
  NRCs in Arabic, timeout, actuator tests with return control, adaptations, security plug-in, clearing a specific
  fault, pack import (JSON / CSV / ODX) and the policy filter, audit log and vehicle history.
- `qa_service_ide.py` - the real IDE (`samples/Tests/QA/Integration/qh.py`, QSettings org RADIDE-TEST,
  screenshots with `widget.grab()`), English then Arabic.
- `demo_seedkey.py` - seed/key plug-in for the **Demo car simulator only** (shows the plug-in interface; RAD IDE
  contains no security algorithms).
- `sample_service.odx` - a synthetic ODX 2.2 file with the simulator's identifiers (plus one service the policy
  skips) for the ODX import.

Try it by hand: Tools > Car Service Functions... > Demo car > "Cooling system bleed": tick the two manual
preconditions, Run, watch the progress; set the coolant to 70 °C in "Demo car conditions" and run again.
