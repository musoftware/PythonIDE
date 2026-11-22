; (c) 2026 Musoftware - https://musoftwares.com - MIT License
;
; NasmBaseConverter - an x64 Windows console tool written with NASM.
; Reads whole numbers (one per line) until 'q', end of input or an invalid line, and prints each one in
; decimal, hexadecimal, octal and binary, plus the number of 1 bits and whether it is a power of two.
; The binary text and the bit count are produced by our own loops (SHL / ADC / POPCNT-free counting); the C
; runtime (printf / scanf) does the decimal, hex and octal formatting.
;
; Ctrl+F5 runs it: type numbers in the Program Input bar (or the console). F5 debugs it with gdb (breakpoints by
; line - the IDE generates DWARF line information for NASM objects).
;
; Microsoft x64 calling convention: arguments in RCX, RDX, R8, R9, 32 bytes of shadow space, RSP 16-byte aligned
; at every CALL; RBX, RSI, RDI, R12-R15 survive calls.
default rel

global main
extern printf, scanf, fflush

section .data
    title       db "Number base converter (NASM x64). Enter numbers, q to quit.", 10, 0
    prompt      db "> ", 0
    fmt_in      db "%lld", 0
    fmt_dec     db "  decimal : %lld", 10, 0
    fmt_hex     db "  hex     : 0x%llX", 10, 0
    fmt_oct     db "  octal   : 0%llo", 10, 0
    fmt_bin     db "  binary  : %s", 10, 0
    fmt_bits    db "  1 bits  : %d", 10, 0
    yes_pow2    db "  power of two: yes", 10, 0
    no_pow2     db "  power of two: no", 10, 0
    bye         db "Converted %d number(s). Bye!", 10, 0

section .bss
    number      resq 1
    binbuf      resb 72                         ; up to 64 digits + terminator

section .text

; to_binary: RCX = value -> binbuf = its binary digits without leading zeros ("0" for 0); EAX = number of 1 bits
to_binary:
    lea rdi, [binbuf]
    xor eax, eax                                ; 1-bit counter
    xor r8d, r8d                                ; 1 once the first 1 digit was written
    mov r9d, 64                                 ; 64 bits, most significant first
.next_bit:
    shl rcx, 1                                  ; CF = the bit that was shifted out
    jc .one
    test r8d, r8d                               ; a 0: skip it while it is a leading zero
    jz .skip
    mov byte [rdi], '0'
    inc rdi
    jmp .skip
.one:
    mov byte [rdi], '1'
    inc rdi
    inc eax
    mov r8d, 1
.skip:
    dec r9d
    jnz .next_bit
    test r8d, r8d
    jnz .terminate
    mov byte [rdi], '0'                         ; the value was 0
    inc rdi
.terminate:
    mov byte [rdi], 0
    ret

main:
    push rbp
    mov rbp, rsp
    push rbx                                    ; RBX = how many numbers were converted
    push r12                                    ; R12 = 1-bit count of the current number
    sub rsp, 32                                 ; shadow space (RSP stays 16-byte aligned: 8+8+8+8+32)
    xor ebx, ebx

    lea rcx, [title]
    call printf

.loop:
    lea rcx, [prompt]
    call printf
    xor ecx, ecx
    call fflush                                 ; show the prompt before scanf waits

    lea rcx, [fmt_in]                           ; scanf returns 1 when a number was read
    lea rdx, [number]
    call scanf
    cmp eax, 1
    jne .finish                                 ; 'q', anything that is not a number, or end of input

    inc ebx
    lea rcx, [fmt_dec]
    mov rdx, [number]
    call printf
    lea rcx, [fmt_hex]
    mov rdx, [number]
    call printf
    lea rcx, [fmt_oct]
    mov rdx, [number]
    call printf

    mov rcx, [number]
    call to_binary
    mov r12d, eax
    lea rcx, [fmt_bin]
    lea rdx, [binbuf]
    call printf
    lea rcx, [fmt_bits]
    mov edx, r12d
    call printf

    ; a power of two has exactly one 1 bit (x != 0 and x & (x - 1) == 0)
    mov rax, [number]
    test rax, rax
    jz .not_pow2
    lea rcx, [rax - 1]
    test rax, rcx
    jnz .not_pow2
    lea rcx, [yes_pow2]
    jmp .print_pow2
.not_pow2:
    lea rcx, [no_pow2]
.print_pow2:
    call printf
    jmp .loop

.finish:
    lea rcx, [bye]
    mov edx, ebx
    call printf
    xor eax, eax
    add rsp, 32
    pop r12
    pop rbx
    pop rbp
    ret
