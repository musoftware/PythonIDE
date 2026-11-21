; محلّل الأعداد - البرنامج الرئيسي
default rel
global main
extern printf, scanf, putchar
extern arr_sum, arr_min, arr_max, is_prime, bubble_sort   ; من stats.asm

MAXN equ 20

section .data
    fmt_int    db "%d", 0
    msg_count  db "How many numbers (1-20)?", 10, 0
    msg_bad    db "Please enter 1 to 20 numbers.", 10, 0
    fmt_num    db "%d ", 0
    hdr_sorted db "Sorted: ", 0
    fmt_sum    db "Sum: %d", 10, 0
    fmt_minmax db "Min: %d  Max: %d", 10, 0
    fmt_avg    db "Average: %d (remainder %d)", 10, 0
    hdr_primes db "Primes: ", 0
    hdr_chart  db "Chart (* = 3):", 10, 0
    fmt_bar    db "%3d | ", 0

section .bss
    n    resd 1
    nums resd MAXN

section .text
main:
    push rbx
    push rsi
    push rdi
    push r12
    sub rsp, 40

    ; ---- كم عددًا؟
    lea rcx, [msg_count]
    call printf
    lea rcx, [fmt_int]
    lea rdx, [n]
    call scanf
    mov r12d, [n]
    cmp r12d, 1
    jl .bad
    cmp r12d, MAXN
    jg .bad

    ; ---- اقرأ الأعداد في nums
    lea rsi, [nums]
    xor ebx, ebx
.read:
    lea rcx, [fmt_int]
    lea rdx, [rsi + rbx*4]       ; عنوان nums[i]
    call scanf
    inc ebx
    cmp ebx, r12d
    jl .read

    ; ---- رتّب واطبع
    mov rcx, rsi
    mov edx, r12d
    call bubble_sort
    lea rcx, [hdr_sorted]
    call printf
    xor ebx, ebx
.print_sorted:
    lea rcx, [fmt_num]
    mov edx, [rsi + rbx*4]
    call printf
    inc ebx
    cmp ebx, r12d
    jl .print_sorted
    mov ecx, 10
    call putchar

    ; ---- المجموع
    mov rcx, rsi
    mov edx, r12d
    call arr_sum
    mov edi, eax                 ; نحتاجه للمتوسط
    lea rcx, [fmt_sum]
    mov edx, eax
    call printf

    ; ---- الأصغر والأكبر
    mov rcx, rsi
    mov edx, r12d
    call arr_min
    mov ebx, eax
    mov rcx, rsi
    mov edx, r12d
    call arr_max
    lea rcx, [fmt_minmax]
    mov edx, ebx
    mov r8d, eax
    call printf

    ; ---- المتوسط (قسمة بإشارة)
    mov eax, edi
    cdq
    idiv r12d
    lea rcx, [fmt_avg]
    mov r8d, edx                 ; الباقي
    mov edx, eax                 ; الخارج
    call printf

    ; ---- الأعداد الأولية
    lea rcx, [hdr_primes]
    call printf
    xor ebx, ebx
.primes:
    mov ecx, [rsi + rbx*4]
    call is_prime
    test eax, eax
    jz .not_prime
    lea rcx, [fmt_num]
    mov edx, [rsi + rbx*4]
    call printf
.not_prime:
    inc ebx
    cmp ebx, r12d
    jl .primes
    mov ecx, 10
    call putchar

    ; ---- الرسم البياني: نجمة لكل 3
    lea rcx, [hdr_chart]
    call printf
    xor ebx, ebx
.bar:
    lea rcx, [fmt_bar]
    mov edx, [rsi + rbx*4]
    call printf
    mov eax, [rsi + rbx*4]
    cdq
    mov ecx, 3
    idiv ecx
    mov edi, eax                 ; عدد النجوم
.star:
    test edi, edi
    jle .bar_end
    mov ecx, '*'
    call putchar
    dec edi
    jmp .star
.bar_end:
    mov ecx, 10
    call putchar
    inc ebx
    cmp ebx, r12d
    jl .bar
    jmp .done

.bad:
    lea rcx, [msg_bad]
    call printf
.done:
    xor eax, eax
    add rsp, 40
    pop r12
    pop rdi
    pop rsi
    pop rbx
    ret

