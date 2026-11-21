; Correct Windows x64 program: procedures that keep the stack balanced, save RBX, stay inside their buffers.
default rel
global main
extern printf

section .data
    nums   dd 4, 8, 15, 16, 23, 42
    COUNT  equ ($ - nums) / 4
    fmt    db "sum = %d, average = %d, copy[5] = %d", 10, 0

section .bss
    copy   resd COUNT

section .text
; int sum(int *a /*rcx*/, int n /*edx*/)
sum:
    push rbx
    xor eax, eax
    xor ebx, ebx
.next:
    cmp ebx, edx
    jge .done
    add eax, [rcx + rbx*4]
    inc ebx
    jmp .next
.done:
    pop rbx
    ret

; void copy_array(int *dst /*rcx*/, int *src /*rdx*/, int n /*r8d*/)
copy_array:
    xor r9d, r9d
.loop:
    cmp r9d, r8d
    jae .end
    mov eax, [rdx + r9*4]
    mov [rcx + r9*4], eax
    inc r9d
    jmp .loop
.end:
    ret

main:
    push rbp
    mov rbp, rsp
    sub rsp, 48
    lea rcx, [nums]
    mov edx, COUNT
    call sum
    mov [rbp-4], eax            ; sum
    cdq                         ; sign-extend before idiv
    mov ecx, COUNT
    idiv ecx
    mov [rbp-8], eax            ; average
    lea rcx, [copy]
    lea rdx, [nums]
    mov r8d, COUNT
    call copy_array
    lea rcx, [fmt]
    mov edx, [rbp-4]
    mov r8d, [rbp-8]
    lea rax, [copy]
    mov r9d, [rax + 5*4]
    call printf
    xor eax, eax
    leave
    ret
