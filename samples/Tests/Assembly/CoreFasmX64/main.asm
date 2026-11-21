; CoreFasmX64 - an x64 Windows console program written with FASM (flat assembler).
; FASM writes the .exe itself (format PE64): there is no separate link step. The 'invoke' / 'cinvoke' macros
; and the import macros come from win64a.inc (FASM's INCLUDE folder - RAD IDE sets it for you).
; Ctrl+F5 runs it; type the input in the Program Input bar.
format PE64 console
entry start

include 'win64a.inc'

section '.data' data readable writeable
    hello       db 'Hello from FASM!', 0
    ask         db 'Enter a number: ', 0
    fmt_in      db '%lld', 0
    fmt_twice   db '%lld + %lld = %lld', 10, 0
    fmt_pc      db 'This computer is called %s', 10, 0
    number      dq 0
    pc_size     dd 64
    pc_name     rb 64

section '.text' code readable executable
start:
    sub rsp, 8                      ; RSP was 8 mod 16 at the entry point: align it for the calls
    cinvoke puts, hello
    cinvoke printf, ask
    cinvoke fflush, 0
    cinvoke scanf, fmt_in, number
    mov rax, [number]
    add rax, rax
    cinvoke printf, fmt_twice, [number], [number], rax
    invoke GetComputerNameA, pc_name, pc_size
    cinvoke printf, fmt_pc, pc_name
    invoke ExitProcess, 0

section '.idata' import data readable writeable
    library kernel32, 'KERNEL32.DLL', msvcrt, 'MSVCRT.DLL'
    import kernel32, GetComputerNameA, 'GetComputerNameA', ExitProcess, 'ExitProcess'
    import msvcrt, printf, 'printf', scanf, 'scanf', puts, 'puts', fflush, 'fflush'
