; CoreFasmX86 - a 32-bit Windows console program written with FASM (flat assembler).
; FASM writes the .exe itself (format PE). 'cinvoke' calls a C (cdecl) function, 'invoke' a Win32 (stdcall) one;
; the macros come from win32a.inc (FASM's INCLUDE folder - RAD IDE sets it for you).
format PE console
entry start

include 'win32a.inc'

section '.data' data readable writeable
    hello       db 'Hello from 32-bit FASM!', 0
    ask         db 'Enter a number: ', 0
    fmt_in      db '%d', 0
    fmt_twice   db '%d + %d = %d', 10, 0
    fmt_pc      db 'This computer is called %s', 10, 0
    number      dd 0
    pc_size     dd 64
    pc_name     rb 64

section '.text' code readable executable
start:
    cinvoke puts, hello
    cinvoke printf, ask
    cinvoke fflush, 0
    cinvoke scanf, fmt_in, number
    mov eax, [number]
    add eax, eax
    cinvoke printf, fmt_twice, [number], [number], eax
    invoke GetComputerNameA, pc_name, pc_size
    cinvoke printf, fmt_pc, pc_name
    cinvoke fflush, 0
    invoke ExitProcess, 0

section '.idata' import data readable writeable
    library kernel32, 'KERNEL32.DLL', msvcrt, 'MSVCRT.DLL'
    import kernel32, GetComputerNameA, 'GetComputerNameA', ExitProcess, 'ExitProcess'
    import msvcrt, printf, 'printf', scanf, 'scanf', puts, 'puts', fflush, 'fflush'
