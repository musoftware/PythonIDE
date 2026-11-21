; CoreMasmX64 - an x64 Windows console program written with MASM (ml64, Visual Studio).
; ml64 has no INVOKE: call functions as C does - arguments in RCX, RDX, R8, R9, 32 bytes of shadow space,
; RSP 16-byte aligned at every CALL. Ctrl+F5 runs it; type the input in the Program Input bar.
; Debugging MASM programs needs the Visual Studio debugger (ml64 writes CodeView / PDB information).

extern printf : proc
extern scanf : proc
extern puts : proc
extern fflush : proc
extern GetComputerNameA : proc

.data
hello       db "Hello from MASM!", 0
ask         db "Enter a number: ", 0
fmt_in      db "%lld", 0
fmt_cube    db "%lld cubed is %lld", 10, 0
fmt_pc      db "This computer is called %s", 10, 0
pc_size     dd 64
number      dq 0
pc_name     db 64 dup (0)

.code
main proc
    sub rsp, 40                     ; shadow space + 8: RSP is now 16-byte aligned

    lea rcx, hello
    call puts

    lea rcx, ask
    call printf
    xor ecx, ecx
    call fflush

    lea rcx, fmt_in
    lea rdx, number
    call scanf

    mov rax, number                 ; number * number * number
    imul rax, rax
    imul rax, number
    lea rcx, fmt_cube
    mov rdx, number
    mov r8, rax
    call printf

    lea rcx, pc_name
    lea rdx, pc_size
    call GetComputerNameA
    lea rcx, fmt_pc
    lea rdx, pc_name
    call printf

    xor eax, eax
    add rsp, 40
    ret
main endp

end
