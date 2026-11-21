# SmartSim - "Check by running", "Explain this line", What-if

Tests and sample programs of the runtime checks (`radide/asm_sim`, docs: [docs/ASSEMBLY.md](../../../../docs/ASSEMBLY.md),
"Smart checks").

* `buggy/` - one mistake per program; `; EXPECT: sim.rule` marks the line where the check must report it.
  Open one in the IDE and press **Ctrl+Shift+F5** (Debug > Assembly Checks > Check by Running), then put the
  cursor on a line and press **Ctrl+Shift+F1** (Explain This Line).
* `correct/` - clean programs (Windows x64 procedures, 32-bit cdecl, Linux system calls, 8086): no findings.
* `tests/test_sim.py` - headless (NASM + `pip install unicorn capstone`):
  `python samples/Tests/Assembly/SmartSim/tests/test_sim.py`
* `tests/test_ide_sim.py` - the real IDE, offscreen, QSettings "RADIDE-TEST" (screenshots in
  `%TEMP%/radide-qa/shots/asm_sim_*.png`): `python samples/Tests/Assembly/SmartSim/tests/test_ide_sim.py`
