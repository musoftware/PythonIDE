; FasmLoose - a FASM program that builds an .exe directly (no linker).
format PE64 console
entry start

include 'win64a.inc'

section '.text' code readable executable
start:
    sub rsp, 8
    invoke printf, msg
    invoke exit, 0

section '.data' data readable writeable
msg db 'FASM loose folder', 13, 10, 0

section '.idata' import data readable
library msvcrt, 'msvcrt.dll'
import msvcrt, printf, 'printf', exit, 'exit'
