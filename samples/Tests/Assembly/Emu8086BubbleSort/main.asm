; BubbleSort - sort a byte array in place and print it before and after.
; Open the Variables view of the emulator and watch "list" change while you step.
.model small
.stack 100h

.data
list    db 64, 25, 12, 22, 11, 90, 3, 47
len     equ $ - list
before  db 'Before: $'
after   db 13, 10, 'After:  $'

.code
start:
    mov ax, @data
    mov ds, ax

    mov dx, offset before
    call print_msg
    call print_list

    mov cx, len - 1             ; outer loop: len-1 passes
outer:
    push cx
    mov si, 0
inner:
    mov al, list[si]
    cmp al, list[si+1]
    jbe no_swap
    xchg al, list[si+1]         ; swap the two neighbours
    mov list[si], al
no_swap:
    inc si
    loop inner
    pop cx
    loop outer

    mov dx, offset after
    call print_msg
    call print_list
    mov ax, 4C00h
    int 21h

print_msg:
    mov ah, 09h
    int 21h
    ret

; print every element as a number followed by a space
print_list:
    mov si, 0
pl_next:
    mov al, list[si]
    mov ah, 0
    mov bl, 10
    div bl                      ; AL = tens, AH = units (all values < 100)
    mov bh, ah
    mov dl, al
    add dl, '0'
    mov ah, 02h
    int 21h
    mov dl, bh
    add dl, '0'
    int 21h
    mov dl, ' '
    int 21h
    inc si
    cmp si, len
    jb pl_next
    ret

end start
