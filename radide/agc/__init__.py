"""Apollo Guidance Computer support for RAD IDE (docs/RETRO.md, section "Apollo AGC").

* isa.py          - instructions, pseudo-ops, interpretive opcodes, registers, channels, DSKY verbs / nouns
* assembler.py    - the built-in "mini-YUL" assembler (basic instructions + extracodes, yaYUL syntax)
* cpu.py          - an original Block II CPU emulator (A L Q Z, banks, channels, timers, interrupts)
* dsky_model.py   - the DSKY decoded from channels 10 / 11 / 163
* machine.py      - CPU + DSKY + program; ``python -m radide.agc MAIN.agc --keys V35E``
* intel.py        - editor support: highlighting (Monarch), IntelliSense, hover, F12 across files, outline
* toolchain.py    - Virtual AGC (yaYUL / yaAGC): download the official source and build it with MinGW
* yaagc.py        - the yaAGC socket protocol (DSKY packets) and the yaAGC debugger driver
* apollo_source.py- download the public-domain Comanche055 / Luminary099 source on request
* ui.py / session.py - the DSKY panel, registers / erasable memory windows and the F5 session
* detect.py       - File > Open Folder recognition of AGC programs
* examples/       - the original "Hello DSKY" program (New Project template, CC0)
"""
