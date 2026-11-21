; add3.asm - long long add3(long long a, long long b, long long c): RCX + RDX + R8 (MASM x64, ml64)
.code
add3 PROC
    lea rax, [rcx + rdx]
    add rax, r8
    ret
add3 ENDP
END
