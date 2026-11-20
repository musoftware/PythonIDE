# Debug_Python_Expand

**python-tk: expandable Locals/Watch, hit counts, logpoints, Threads** - works with both Python engines
(Tools > Options: debugpy, or the built-in agent `radide/debug/pyagent.py`).

**Try it:** line 23 (`total += square(numbers[i])`) > Debug > Breakpoint Settings... > hit count equal to 3;
line 10 (`result = n * n`) > logpoint `sq n={n}`. F5: Output shows `sq n=3`, `sq n=1`, then it stops with `i = 2`.
Expand `p` (x, y, label), `numbers`, `info` (a dict with a nested list); Watch `p.label` and `info` (expandable).
F10 steps over `square()` without stopping at the logpoint.
