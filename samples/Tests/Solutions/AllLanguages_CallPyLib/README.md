# AllLanguages_CallPyLib

**Solution: 15 apps -> 1 Python library** - Reverse direction: an app in every GUI language (C#, VB6, Ring, JS, TS, PHP, Java, PowerShell, C, C++, Rust, Fortran, Perl, Dart, Python) references the same PyLib and calls PyLib.Add / PyLib.Greet.

**Try it:** Open `RevSol.radsln`, right-click an App_* project > Set as StartUp Project, F5. Each App_*'s module (CsCons.cs, CCons.c, ...) calls PyLib.

*Origin:* agents2 QA `t_reverse.py` (all OK) (copied from the IDE's test runs, build output removed).
