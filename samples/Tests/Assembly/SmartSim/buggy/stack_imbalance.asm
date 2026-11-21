; Bug: sum_to pushes RBX but never pops it, so 'ret' finds RBX's old value instead of the return address.
default rel
global main
extern printf

section .data
    fmt db "sum = %d", 10, 0

section .text
sum_to:                         ; ecx = n -> eax = 1 + 2 + ... + n
    push rbx
    xor eax, eax
.next:
    add eax, ecx
    loop .next
    ret                         ; EXPECT: sim.stack_imbalance

main:
    sub rsp, 40
    mov ecx, 10
    call sum_to
    lea rcx, [fmt]
    mov edx, eax
    call printf
    xor eax, eax
    add rsp, 40
    ret
