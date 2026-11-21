; محلّل الأعداد - مكتبة الدوال (كلها ورقية: rax, rcx, rdx, r8-r10 فقط)
default rel
global arr_sum, arr_min, arr_max, is_prime, bubble_sort

section .text

; int arr_sum(const int *a, int n)
arr_sum:
    xor eax, eax
    xor r8d, r8d                 ; i
.next:
    cmp r8d, edx
    jge .done
    add eax, [rcx + r8*4]
    inc r8d
    jmp .next
.done:
    ret

; int arr_min(const int *a, int n)  (n >= 1)
arr_min:
    mov eax, [rcx]
    mov r8d, 1
.next:
    cmp r8d, edx
    jge .done
    mov r9d, [rcx + r8*4]
    cmp r9d, eax
    cmovl eax, r9d
    inc r8d
    jmp .next
.done:
    ret

; int arr_max(const int *a, int n)  (n >= 1)
arr_max:
    mov eax, [rcx]
    mov r8d, 1
.next:
    cmp r8d, edx
    jge .done
    mov r9d, [rcx + r8*4]
    cmp r9d, eax
    cmovg eax, r9d
    inc r8d
    jmp .next
.done:
    ret

; int is_prime(int n) -> 1 / 0 : جرّب القواسم d من 2 ما دام d*d <= n
is_prime:
    xor eax, eax
    cmp ecx, 2
    jl .done                     ; الأعداد الأصغر من 2 ليست أولية
    mov r8d, ecx                 ; n
    mov r9d, 2                   ; d
.try:
    mov eax, r9d
    imul eax, r9d
    cmp eax, r8d
    jg .prime                    ; d*d > n: لا قاسم
    mov eax, r8d
    xor edx, edx
    div r9d
    test edx, edx
    jz .composite                ; d يقسم n
    inc r9d
    jmp .try
.prime:
    mov eax, 1
    ret
.composite:
    xor eax, eax
.done:
    ret

; void bubble_sort(int *a, int n) - ترتيب تصاعدي في المكان
bubble_sort:
    mov r8d, edx
    dec r8d                      ; عدد المرات = n - 1
.outer:
    cmp r8d, 0
    jle .done
    xor r9d, r9d                 ; j
.inner:
    cmp r9d, r8d
    jge .next_pass
    mov eax, [rcx + r9*4]
    mov r10d, [rcx + r9*4 + 4]
    cmp eax, r10d
    jle .no_swap
    mov [rcx + r9*4], r10d       ; بدّل الجارين
    mov [rcx + r9*4 + 4], eax
.no_swap:
    inc r9d
    jmp .inner
.next_pass:
    dec r8d
    jmp .outer
.done:
    ret
