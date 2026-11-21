; MasmLoose - a MASM x64 program (ml64 comes with Visual Studio's C++ workload; it is never downloaded).
includelib kernel32.lib
includelib ucrt.lib
includelib legacy_stdio_definitions.lib
extern printf : proc

.data
fmt db "MASM loose folder: %d", 10, 0

.code
main PROC
    sub rsp, 40
    lea rcx, fmt
    mov edx, 42
    call printf
    xor eax, eax
    add rsp, 40
    ret
main ENDP
END
