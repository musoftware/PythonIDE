# HelloDSKY - an original Apollo Guidance Computer program

Licence: public domain (CC0). Written for RAD IDE; it does not contain NASA / MIT code.

| File | What |
|---|---|
| `MAIN.agc` | interrupt vectors at 4000, start-up, main loop (touches NEWJOB, ends with TCF), the clock (TICK) |
| `ERASABLE.agc` | register names, NEWJOB, variables at 100 (bank E0), the 25-cell display buffer |
| `INTERRUPTS.agc` | T3RUPT every centisecond (100 = one second), KEYRUPT1 reads channel 15 |
| `DISPLAY.agc` | SHOWVN, SHOWCLK, PUTNUM (decimal digits by subtraction), FLUSH (11 relay words to channel 10) |
| `KEYBOARD.agc` | VERB nn / NOUN nn / ENTR / RSET: V35E lamp test, V16N36E clock, anything else OPR ERR |
| `CONSTANTS.agc` | constants, powers of ten, DSKY digit codes, the relay-word table |

## Try it

1. File > Open Project > this folder, press **F5**. The "Apollo AGC" dock shows the DSKY: VERB 16 NOUN 36 and the time
   since start (R1 hours, R2 minutes, R3 seconds x 100).
2. Click the DSKY and type `V35` Enter (VERB 3 5 ENTR): lamp test. `V16N36` Enter: the clock again. `V21` Enter: OPR ERR,
   `R` (RSET) clears it.
3. Put a breakpoint on `TICK` in MAIN.agc: it stops once a second; Locals shows A L Q Z and SECS / MINS / HOURS; F10.
4. With Virtual AGC installed (Tools > Retro > Apollo AGC > Virtual AGC Toolchain...), set `"agc": {"assembler": "yayul",
   "run": "yaagc"}` in project.radproj: yaYUL builds the same rope (word for word) and yaAGC runs it with the same DSKY.

Headless: `python -m radide.agc samples/Tests/Retro/AGC/HelloDSKY/MAIN.agc --keys V35E`.
Tests: `samples/Tests/Retro/AGC/test_agc_core.py`, `test_ide_nasa.py`.
