@echo off
rem Build the attach target with debug information (WinLibs gcc from %LOCALAPPDATA%\RADIDE\toolchains\mingw64, or any MinGW gcc on PATH)
set GCC=%LOCALAPPDATA%\RADIDE\toolchains\mingw64\bin\gcc.exe
if not exist "%GCC%" set GCC=gcc
"%GCC%" -g -O0 -o worker.exe worker.c
