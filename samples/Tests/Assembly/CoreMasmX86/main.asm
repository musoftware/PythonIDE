; CoreMasmX86 - a 32-bit Windows console program written with MASM (ml, Visual Studio).
; In 32-bit MASM, INVOKE pushes the arguments for you; PROTO declares a function's parameters.
.386
.model flat, c
.stack 4096

printf      proto c :ptr byte, :vararg
scanf       proto c :ptr byte, :vararg
puts        proto c :ptr byte
fflush      proto c :ptr
GetComputerNameA proto stdcall :ptr byte, :ptr dword

.data
hello       db "Hello from 32-bit MASM!", 0
ask         db "Enter a number: ", 0
fmt_in      db "%d", 0
fmt_cube    db "%d cubed is %d", 10, 0
fmt_pc      db "This computer is called %s", 10, 0
pc_size     dd 64
number      dd 0
pc_name     db 64 dup (0)

.code
main proc
    invoke puts, addr hello
    invoke printf, addr ask
    invoke fflush, 0
    invoke scanf, addr fmt_in, addr number
    mov eax, number
    imul eax, eax
    imul eax, number
    invoke printf, addr fmt_cube, number, eax
    invoke GetComputerNameA, addr pc_name, addr pc_size
    invoke printf, addr fmt_pc, addr pc_name
    xor eax, eax
    ret
main endp

end
