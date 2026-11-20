# Debug_Java_JDWP

**java-bridge: Java debugger (JDWP, `radide/jdwp_engine.py`)** - breakpoints, steps, expandable Locals/Watch,
hit counts, logpoints, Threads window. Needs a JDK (javac/java); nothing else is downloaded.

**Try it:**
1. Open `Form1.java`, put the caret on line 21 (`total += square(numbers[i]);`), Debug > Breakpoint Settings...
   > "When the hit count is equal to" 3 > OK.
2. Put a breakpoint on line 11 (`int result = n * n;`), Breakpoint Settings... > tick "Log a message" and type
   `sq n={n}`.
3. F5: the Output shows `sq n=3`, `sq n=1`, then it stops on line 21 with `i = 2`.
   In Locals expand `p` (x, y, label) and `numbers` ([0]..[4]). Add Watch `p.label` and `p` (expandable).
   Debug > Windows > Threads lists `main`, `Finalizer` ...; F10 steps, F5 continues (`total=52 RAD corner`).

Watch / Immediate / conditions understand variables, fields (`p.label`, `this.x`), array items, `.length`,
arithmetic and comparisons (no method calls).
