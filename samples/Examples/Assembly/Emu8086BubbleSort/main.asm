; (c) 2026 Musoftware - https://musoftwares.com - MIT License
;
; Emu8086BubbleSort - a 16-bit DOS .COM program for RAD IDE's own 8086 emulator (nothing to install).
; It prints a table of signed words, asks for the order (A = ascending, D = descending), sorts the table
; with bubble sort (with the "no swap -> stop early" improvement), prints every pass and the number of swaps.
;
; Things to try in the IDE: F5 opens the 8086 Emulator dock paused at the first instruction - press F10 / F11
; to step, watch AX / BX / CX / SI and the flags, open Memory at DS:numbers and see the words move, use Step
; Back. Ctrl+F5 runs at full speed. INT 21h services used: 01h read a key, 02h print a character,
; 09h print a $-terminated string, 4Ch exit.

org 100h

start:
    mov dx, offset title_s
    call print_str
    call print_table

ask:
    mov dx, offset ask_s
    call print_str
    mov ah, 01h                 ; read a key (echoed) -> AL
    int 21h
    call newline
    or al, 20h                  ; upper -> lower case
    cmp al, 'a'
    je set_order
    cmp al, 'd'
    je set_order
    mov dx, offset bad_s
    call print_str
    jmp ask
set_order:
    mov [order], al

; ---------------------------------------------------------------- bubble sort
    mov cx, COUNT - 1           ; passes still possible
outer:
    xor bx, bx                  ; BX = swaps in this pass
    mov si, offset numbers
    push cx                     ; inner loop: CX comparisons
inner:
    mov ax, [si]
    mov dx, [si + 2]
    cmp byte ptr [order], 'd'
    je descending
    cmp ax, dx                  ; ascending: swap when a[i] > a[i+1] (signed)
    jle no_swap
    jmp do_swap
descending:
    cmp ax, dx                  ; descending: swap when a[i] < a[i+1]
    jge no_swap
do_swap:
    mov [si], dx
    mov [si + 2], ax
    inc bx
    inc word ptr [swaps]
no_swap:
    add si, 2
    loop inner
    pop cx
    inc word ptr [passes]
    mov dx, offset pass_s       ; "Pass n: ..."
    call print_str
    mov ax, [passes]
    call print_num
    mov dl, ':'
    call print_chr
    call print_table
    test bx, bx                 ; no swap in this pass: the table is sorted
    jz sorted
    loop outer

sorted:
    mov dx, offset swaps_s
    call print_str
    mov ax, [swaps]
    call print_num
    call newline
    mov dx, offset done_s
    call print_str
    mov ax, 4C00h               ; exit with code 0
    int 21h

; ---------------------------------------------------------------- routines
; print_table: " n n n ..." + new line
print_table:
    push cx
    push si
    mov si, offset numbers
    mov cx, COUNT
pt_loop:
    mov dl, ' '
    call print_chr
    mov ax, [si]
    call print_num
    add si, 2
    loop pt_loop
    call newline
    pop si
    pop cx
    ret

; print_num: AX = signed word -> decimal digits (with '-' when negative)
print_num:
    push ax
    push bx
    push cx
    push dx
    test ax, ax
    jns pn_positive
    push ax
    mov dl, '-'
    call print_chr
    pop ax
    neg ax
pn_positive:
    xor cx, cx                  ; CX = digits pushed
    mov bx, 10
pn_divide:
    xor dx, dx
    div bx                      ; AX = AX / 10, DX = remainder
    push dx
    inc cx
    test ax, ax
    jnz pn_divide
pn_print:
    pop dx
    add dl, '0'
    call print_chr
    loop pn_print
    pop dx
    pop cx
    pop bx
    pop ax
    ret

; print_chr: DL = character
print_chr:
    push ax
    mov ah, 02h
    int 21h
    pop ax
    ret

; print_str: DS:DX = $-terminated string
print_str:
    push ax
    mov ah, 09h
    int 21h
    pop ax
    ret

newline:
    push dx
    mov dx, offset crlf
    call print_str
    pop dx
    ret

; ---------------------------------------------------------------- data
COUNT   equ 8
numbers dw 34, -5, 120, 7, 0, 89, -42, 15
order   db 'a'
passes  dw 0
swaps   dw 0
title_s db 'Bubble sort on the 8086 (RAD IDE emulator)', 13, 10, 'Table:$'
ask_s   db 'Order? A = ascending, D = descending: $'
bad_s   db 'Please press A or D.', 13, 10, '$'
pass_s  db 'Pass $'
swaps_s db 'Swaps: $'
done_s  db 'Sorted - bye!', 13, 10, '$'
crlf    db 13, 10, '$'
