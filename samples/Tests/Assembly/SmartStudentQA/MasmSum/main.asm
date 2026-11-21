; Student program 3: sum 1..10 with a procedure (MASM, 32-bit)
.386
.model flat, c
.stack 4096

printf proto c :ptr byte, :vararg

.data
fmt     db "sum = %d", 10, 0
total   dd 0

.code
sum_to proc
    push ebx
    xor eax, eax
    mov ecx, 10
next_n:
    add eax, ecx
    loop next_n
    ret
sum_to endp

main proc
    call sum_to
    mov total, eax
    push total
    push offset fmt
    call printf
    mov al, 300
    xor eax, eax
    ret
main endp

end
