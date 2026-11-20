# Debug_PythonTk

**python-tk: debugger** - Breakpoints, Watch, Immediate eval, conditional breakpoints.

**Try it:** Open MainForm.py, set a breakpoint on line 9 (`print("load done", nX)`), F5: it stops; Watch `nX` = 42, Immediate `nX + 1`. Then put a breakpoint on line 14, Debug > Breakpoint Condition... `i == 5`, click Hello: it stops once with i = 5.

*Origin:* fix_shell `reg_ui_dbg.py` (loop added for conditional breakpoints) (copied from the IDE's test runs, build output removed).
