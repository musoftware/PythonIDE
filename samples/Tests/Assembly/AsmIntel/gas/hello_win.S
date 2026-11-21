/* hello_win.S - GNU as, Intel syntax, Windows x64 (MinGW: gcc hello_win.S -o hello.exe)
   RAD IDE IntelliSense test: .intel_syntax noprefix, C preprocessor (#define), printf from the CRT. */

#define ITEMS 3

    .intel_syntax noprefix
    .section .rdata,"dr"
fmt:
    .asciz "Item %d of %d\n"

    .text
    .globl main
main:
    push    rbx
    sub     rsp, 32                 # shadow space
    xor     ebx, ebx
.Lloop:
    inc     ebx
    lea     rcx, fmt[rip]
    mov     edx, ebx
    mov     r8d, ITEMS
    call    printf
    cmp     ebx, ITEMS
    jl      .Lloop
    xor     eax, eax
    add     rsp, 32
    pop     rbx
    ret
