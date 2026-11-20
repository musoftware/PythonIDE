# Attach_C_gdb

**Debug > Attach to Process (native, gdb `-i dap`)** - `worker.c` prints a tick every half second forever.

**Try it:**
1. `build.bat` (gcc `-g -O0`), then run `worker.exe`.
2. In the IDE open `worker.c` (File > Open File) and F9 on line 15 (`int sum = p.x + p.y;`) - or attach first and
   set the breakpoint after.
3. Debug > Attach to Process..., pick `worker.exe` (Automatic = gdb; Go programs get Delve, `dotnet` netcoredbg), Attach.
   It stops on line 15: Locals `count`, `sum` and `p` (expand: x, y). Stop detaches; the program keeps running.

Needs gdb (WinLibs in `%LOCALAPPDATA%\RADIDE\toolchains\mingw64`). Programs built with MSVC (PDB) cannot be
debugged by gdb.
