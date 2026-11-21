@echo off
rem Builds the three test programs with the RAD IDE toolchain (WinLibs: gcc, nasm, gdb).
set TC=%LOCALAPPDATA%\RADIDE\toolchains\mingw64\bin
set PATH=%TC%;%PATH%
nasm -f win64 -o sum.obj sum.asm || exit /b 1
gcc -o sum.exe sum.obj || exit /b 1
gcc -g -O0 -o sum_gas.exe sum_gas.s || exit /b 1
gcc -g -O0 -o arrays.exe arrays.c || exit /b 1
echo Built sum.exe, sum_gas.exe and arrays.exe
