; CoreNasmConsoleX86 - a 32-bit (x86) Windows console program written with NASM.
; Ctrl+F5 runs it; type the input in the Program Input bar.
;
; 32-bit conventions:
;   * cdecl (C runtime): arguments are pushed right to left, the caller removes them (add esp, 4*n);
;   * stdcall (Win32 API): the same order, but the called function removes them;
;   * the linker names C functions with a leading underscore (_printf) and Win32 functions with the size of
;     their arguments (_GetComputerNameA@8);
;   * the result comes in EAX; EAX, ECX, EDX may be changed, EBX, ESI, EDI, EBP are kept.
; The program is linked directly against msvcrt.dll / kernel32.dll (no C runtime start-up code): _main is the
; entry point and it ends with ExitProcess.

global _main
extern _printf, _scanf, _puts, _fflush             ; C runtime (msvcrt.dll)
extern _GetComputerNameA@8, _ExitProcess@4          ; Win32 API (kernel32.dll)

section .data
    hello       db "Hello from 32-bit assembly!", 0
    ask         db "Enter a number: ", 0
    fmt_in      db "%d", 0
    fmt_square  db "%d squared is %d", 10, 0
    fmt_sum     db "1 + 2 + ... + %d = %d", 10, 0
    fmt_pc      db "This computer is called %s", 10, 0
    pc_size     dd 64

section .bss
    number      resd 1
    pc_name     resb 64

section .text
_main:
    push hello                      ; puts(hello)
    call _puts
    add esp, 4

    push ask                        ; printf(ask); fflush(NULL)
    call _printf
    add esp, 4
    push 0
    call _fflush
    add esp, 4

    push number                     ; scanf("%d", &number)
    push fmt_in
    call _scanf
    add esp, 8

    mov eax, [number]               ; number * number
    imul eax, eax
    push eax
    push dword [number]
    push fmt_square
    call _printf
    add esp, 12

    xor eax, eax                    ; sum = 1 + 2 + ... + number
    mov ecx, [number]
.add_next:
    cmp ecx, 0
    jle .add_done
    add eax, ecx
    dec ecx
    jmp .add_next
.add_done:
    push eax
    push dword [number]
    push fmt_sum
    call _printf
    add esp, 12

    push pc_size                    ; GetComputerNameA(pc_name, &pc_size) - stdcall: no add esp
    push pc_name
    call _GetComputerNameA@8
    push pc_name
    push fmt_pc
    call _printf
    add esp, 8

    push 0                          ; fflush(NULL); ExitProcess(0)
    call _fflush
    add esp, 4
    push 0
    call _ExitProcess@4
