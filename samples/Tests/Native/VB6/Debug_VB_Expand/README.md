# Debug_VB_Expand

**vb-basic: VB debugger extras** - expandable Locals/Watch for arrays, user Types and Collections, hit counts and
logpoints (the VB runtime `radide/runtimes/vbrun.py`).

**Try it:** line 19 (`total = total + numbers(i) * numbers(i)`) > Debug > Breakpoint Settings... > hit count equal
to 3; line 21 > logpoint `log total={total}`. F5: stops with `i = 3`; expand `numbers` ((1)..(5)), `p` (x, y, label)
and `c` ((1) "first", (2) 42); Watch `p.Label`. F5 again: the Output shows `log total=52` (no stop there).
