; (c) 2026 Musoftware - https://musoftwares.com - MIT License
;
; MasmTextTools - an x64 console program written with MASM (ml64 from Visual Studio).
; Part 1 (strings): reads one line and prints its length, the text reversed, in upper case, the number of
;   vowels and the number of words - every routine is a hand-written byte loop (MOVZX / CMP / Jcc / STOSB).
; Part 2 (arrays): sums a table of 64-bit numbers, finds the smallest / largest, the average, and sorts a copy
;   with insertion sort, then prints the sorted table.
;
; ml64 has no INVOKE: functions are called the C way - arguments in RCX, RDX, R8, R9, 32 bytes of shadow space,
; RSP 16-byte aligned at every CALL; RBX, RSI, RDI, R12-R15 must be kept by a procedure that changes them.
; Ctrl+F5 runs it (type the line in the Program Input bar).

extern printf : proc
extern scanf : proc
extern fflush : proc

.data
title_s     db "MASM text tools - type a line of text:", 10, 0
fmt_line    db "%255[^", 10, "]", 0                 ; read up to 255 characters until the end of the line
fmt_len     db "Length    : %d", 10, 0
fmt_rev     db "Reversed  : %s", 10, 0
fmt_up      db "Uppercase : %s", 10, 0
fmt_vow     db "Vowels    : %d", 10, 0
fmt_words   db "Words     : %d", 10, 0
arr_title   db 10, "Array tools on: ", 0
fmt_num     db "%lld ", 0
newline     db 10, 0
fmt_sum     db "Sum       : %lld", 10, 0
fmt_minmax  db "Min / Max : %lld / %lld", 10, 0
fmt_avg     db "Average   : %lld", 10, 0
sorted_s    db "Sorted    : ", 0
vowels      db "aeiouAEIOU", 0

numbers     dq 42, -7, 15, 99, 0, 23, -18, 64, 8, 31
COUNT       equ 10

line        db 256 dup (0)
work        db 256 dup (0)
sorted      dq COUNT dup (0)

.code

; ------------------------------------------------------------------ string routines (no calls inside)
; strlen_ : RCX = text -> RAX = length
strlen_ proc
    xor eax, eax
next_ch:
    cmp byte ptr [rcx + rax], 0
    je done
    inc rax
    jmp next_ch
done:
    ret
strlen_ endp

; reverse_ : RCX = source, RDX = destination (both 256 bytes) -> destination = source reversed
reverse_ proc
    push rsi
    push rdi
    mov rsi, rcx
    mov rdi, rdx
    call strlen_                    ; RAX = length (RCX is still the source)
    mov rcx, rax
rev_loop:
    test rcx, rcx
    jz rev_end
    dec rcx
    mov al, byte ptr [rsi + rcx]
    mov byte ptr [rdi], al
    inc rdi
    jmp rev_loop
rev_end:
    mov byte ptr [rdi], 0
    pop rdi
    pop rsi
    ret
reverse_ endp

; upper_ : RCX = text, changed in place to upper case (a..z only)
upper_ proc
up_loop:
    mov al, byte ptr [rcx]
    test al, al
    jz up_end
    cmp al, 'a'
    jb up_next
    cmp al, 'z'
    ja up_next
    sub al, 32
    mov byte ptr [rcx], al
up_next:
    inc rcx
    jmp up_loop
up_end:
    ret
upper_ endp

; count_vowels : RCX = text -> RAX = number of characters found in 'vowels'
count_vowels proc
    xor eax, eax
cv_loop:
    movzx edx, byte ptr [rcx]
    test edx, edx
    jz cv_end
    lea r8, vowels
cv_scan:
    movzx r9d, byte ptr [r8]
    test r9d, r9d
    jz cv_next
    cmp edx, r9d
    je cv_hit
    inc r8
    jmp cv_scan
cv_hit:
    inc rax
cv_next:
    inc rcx
    jmp cv_loop
cv_end:
    ret
count_vowels endp

; count_words : RCX = text -> RAX = number of words (runs of characters other than space / tab)
count_words proc
    xor eax, eax
    xor edx, edx                    ; EDX = 1 while inside a word
cw_loop:
    mov r8b, byte ptr [rcx]
    test r8b, r8b
    jz cw_end
    cmp r8b, ' '
    je cw_space
    cmp r8b, 9
    je cw_space
    test edx, edx
    jnz cw_next
    inc rax                         ; the first character of a new word
    mov edx, 1
    jmp cw_next
cw_space:
    xor edx, edx
cw_next:
    inc rcx
    jmp cw_loop
cw_end:
    ret
count_words endp

; ------------------------------------------------------------------ array routines
; insertion_sort : RCX = array of qwords, RDX = count (sorted ascending in place)
insertion_sort proc
    push rbx
    mov r8, 1                       ; i = 1
is_outer:
    cmp r8, rdx
    jge is_end
    mov rax, qword ptr [rcx + r8*8] ; key = a[i]
    mov r9, r8                      ; j = i
is_inner:
    test r9, r9
    jz is_place
    mov rbx, qword ptr [rcx + r9*8 - 8]
    cmp rbx, rax                    ; while a[j-1] > key: a[j] = a[j-1]
    jle is_place
    mov qword ptr [rcx + r9*8], rbx
    dec r9
    jmp is_inner
is_place:
    mov qword ptr [rcx + r9*8], rax
    inc r8
    jmp is_outer
is_end:
    pop rbx
    ret
insertion_sort endp

; print_array : RCX = array, RDX = count (printf "%lld " for each, then a new line)
print_array proc
    push rbx
    push rsi
    push rdi                        ; 3 pushes + return address = 32 bytes: RSP keeps its alignment
    sub rsp, 32
    mov rbx, rcx
    mov rsi, rdx
    xor edi, edi
pa_loop:
    cmp rdi, rsi
    jge pa_end
    lea rcx, fmt_num
    mov rdx, qword ptr [rbx + rdi*8]
    call printf
    inc rdi
    jmp pa_loop
pa_end:
    lea rcx, newline
    call printf
    add rsp, 32
    pop rdi
    pop rsi
    pop rbx
    ret
print_array endp

; ------------------------------------------------------------------ main
main proc
    push rbx
    push rsi
    push rdi
    sub rsp, 32                     ; 3 pushes + return address + 32 = 64: aligned

    lea rcx, title_s
    call printf
    xor ecx, ecx
    call fflush
    lea rcx, fmt_line
    lea rdx, line
    call scanf                      ; an empty line leaves 'line' empty

    lea rcx, line
    call strlen_
    lea rcx, fmt_len
    mov edx, eax
    call printf

    lea rcx, line
    lea rdx, work
    call reverse_
    lea rcx, fmt_rev
    lea rdx, work
    call printf

    lea rcx, line                   ; copy line -> work, then upper-case the copy
    lea rdx, work
copy_loop:
    mov al, byte ptr [rcx]
    mov byte ptr [rdx], al
    inc rcx
    inc rdx
    test al, al
    jnz copy_loop
    lea rcx, work
    call upper_
    lea rcx, fmt_up
    lea rdx, work
    call printf

    lea rcx, line
    call count_vowels
    lea rcx, fmt_vow
    mov edx, eax
    call printf

    lea rcx, line
    call count_words
    lea rcx, fmt_words
    mov edx, eax
    call printf

    ; ---- arrays
    lea rcx, arr_title
    call printf
    lea rcx, numbers
    mov edx, COUNT
    call print_array

    lea rsi, numbers                ; sum, min, max in one pass
    xor ebx, ebx                    ; RBX = sum
    mov r8, qword ptr [rsi]         ; R8 = min
    mov r9, r8                      ; R9 = max
    xor ecx, ecx
sum_loop:
    cmp ecx, COUNT
    jge sum_end
    mov rax, qword ptr [rsi + rcx*8]
    add rbx, rax
    cmp rax, r8
    jge not_min
    mov r8, rax
not_min:
    cmp rax, r9
    jle not_max
    mov r9, rax
not_max:
    inc ecx
    jmp sum_loop
sum_end:
    mov rsi, r8                     ; keep min / max over the printf calls
    mov rdi, r9
    lea rcx, fmt_sum
    mov rdx, rbx
    call printf
    lea rcx, fmt_minmax
    mov rdx, rsi
    mov r8, rdi
    call printf
    mov rax, rbx                    ; average = sum / COUNT (signed)
    cqo
    mov rcx, COUNT
    idiv rcx
    lea rcx, fmt_avg
    mov rdx, rax
    call printf

    lea rsi, numbers                ; sorted = copy of numbers, then insertion sort
    lea rdi, sorted
    mov ecx, COUNT
    rep movsq
    lea rcx, sorted
    mov edx, COUNT
    call insertion_sort
    lea rcx, sorted_s
    call printf
    lea rcx, sorted
    mov edx, COUNT
    call print_array

    xor eax, eax
    add rsp, 32
    pop rdi
    pop rsi
    pop rbx
    ret
main endp

end
