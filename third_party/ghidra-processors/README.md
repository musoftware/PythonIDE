# Ghidra SLEIGH processor modules (vendored)

Community SLEIGH processor specifications for CPUs that upstream Ghidra / pypcode do not ship. RAD IDE compiles
them on first use with the SLEIGH compiler inside the `pypcode` wheel and disassembles / lifts to p-code through
pypcode (`radide/firmware/analysis/sleigh.py`). Each folder keeps its own `LICENSE` and a `README.md` with the
source URL and commit.

| Folder | CPU | Source | License |
| --- | --- | --- | --- |
| `C166/` | Infineon C166 / C167 / ST10 / XC16x | https://github.com/keyhana/c166-ghidra-module | MIT |
| `RL78/` | Renesas RL78 | https://github.com/xyzz/ghidra-rl78 | MIT |

Processors that pypcode already bundles (8051, V850 / RH850, PowerPC VLE, HC08 / HCS08, HCS12(X), M16C / R8C,
M32C, SH-2A, TriCore, MCS-96, 68000 / CPU32 ...) come from Ghidra itself (Apache-2.0) inside the pypcode wheel and
are not copied here.
