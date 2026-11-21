; CoreNasmConsoleX64 - an x64 Windows console program written with NASM.
; Ctrl+F5 runs it (the Output window shows what it prints; type the input in the Program Input bar),
; F5 debugs it (breakpoints by line, registers, step instruction).
;
; Microsoft x64 calling convention (used by the C runtime and the Win32 API):
;   * the first four arguments go in RCX, RDX, R8, R9 (more arguments on the stack), the result comes in RAX;
;   * the caller reserves 32 bytes of "shadow space" and RSP is 16-byte aligned at every CALL;
;   * RAX, RCX, RDX, R8-R11 may be changed by the called function; RBX, RBP, RSI, RDI, R12-R15 are kept.
default rel                         ; [label] = RIP-relative addressing (needed for 64-bit Windows programs)

global main                         ; the C runtime calls main
extern printf, scanf, puts, fflush  ; C runtime
extern GetComputerNameA             ; Win32 API (kernel32.dll)

section .data
    hello       db "Hello from assembly!", 0
    ask         db "Enter a number: ", 0
    fmt_in      db "%lld", 0
    fmt_square  db "%lld squared is %lld", 10, 0
    fmt_sum     db "1 + 2 + ... + %lld = %lld", 10, 0
    fmt_pc      db "This computer is called %s", 10, 0
    pc_size     dd 64

section .bss
    number      resq 1
    pc_name     resb 64

section .text
main:
    push rbp                        ; RSP was 8 mod 16 on entry: now it is aligned
    mov rbp, rsp
    sub rsp, 32                     ; shadow space for the calls below

    lea rcx, [hello]                ; puts(hello)
    call puts

    lea rcx, [ask]                  ; printf(ask) then fflush(NULL): show the prompt before scanf waits
    call printf
    xor ecx, ecx
    call fflush

    lea rcx, [fmt_in]               ; scanf("%lld", &number)
    lea rdx, [number]
    call scanf

    mov rax, [number]               ; number * number
    imul rax, rax
    lea rcx, [fmt_square]
    mov rdx, [number]
    mov r8, rax
    call printf

    xor eax, eax                    ; sum = 0
    mov rcx, [number]               ; i = number
.add_next:
    cmp rcx, 0                      ; while (i > 0) { sum += i; i--; }
    jle .add_done
    add rax, rcx
    dec rcx
    jmp .add_next
.add_done:
    lea rcx, [fmt_sum]
    mov rdx, [number]
    mov r8, rax
    call printf

    lea rcx, [pc_name]              ; GetComputerNameA(pc_name, &pc_size)
    lea rdx, [pc_size]
    call GetComputerNameA
    lea rcx, [fmt_pc]
    lea rdx, [pc_name]
    call printf

    xor eax, eax                    ; return 0
    leave
    ret
