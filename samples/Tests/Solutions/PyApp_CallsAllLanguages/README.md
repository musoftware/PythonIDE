# PyApp_CallsAllLanguages

**Solution: python-tk app + 19 libraries** - One Python app references libraries written in C#, VB6, Ring, JavaScript, TypeScript, C, C++, Rust, Fortran, Perl, Dart, Java, PHP, PowerShell, Python, Python-Qt, Go, Lua and Ruby (Add Reference -> generated proxy modules CsLib.py, RustLib.py ...).

**Try it:** Open `QaSol.radsln`, press F5 (startup = App). `pymain.py` calls `Add`/`Greet` in every library through the RAD Hub. Go/Lua/Ruby need their toolchains (they failed in the original run because they were not installed yet).

*Origin:* agents2 QA `t_py_consumer.py` (16/19 OK in that run) (copied from the IDE's test runs, build output removed).
