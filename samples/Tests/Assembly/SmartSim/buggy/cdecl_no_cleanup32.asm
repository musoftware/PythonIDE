; Bug (32-bit cdecl): the caller must remove printf's arguments ('add esp, 8'); it does not.
global _main
extern _printf

section .data
    fmt db "value %d", 10, 0

section .text
_main:
    push 42
    push fmt
    call _printf
    xor eax, eax
    ret                         ; EXPECT: sim.stack_imbalance
