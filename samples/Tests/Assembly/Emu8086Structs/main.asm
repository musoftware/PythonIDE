; Emu8086Structs - structures (STRUC / ENDS) and conditional assembly (IF / IFDEF / ELSE / ENDIF) on the 8086.
; A small class list: each student is a STRUC with a name, a mark and a grade letter. The program prints the
; list, the average and the best student. Change SHOW_GRADES / LANGUAGE below and run it again.
; Export it as a real DOS program: 8086 Emulator dock > Export... > MZ .EXE, then run STRUCTS.EXE in DOSBox.

.model small
.stack 100h

SHOW_GRADES equ 1           ; 0 = do not print the grade letters
LANGUAGE    = 1             ; 1 = English, 2 = short headers
COUNT       equ 4

student struc
    sname   db 8 dup (' ')          ; 8 letters
    dollar  db '$'                  ; ends the name for INT 21h / AH=9
    mark    dw 0
    grade   db '?'
student ends

.data
class   student <'Ali     ', , 91, 'A'>
        student <'Mona    ', , 78, 'C'>
        student <'Omar    ', , 85, 'B'>
        student <'Sara    ', , 96, 'A'>
IF LANGUAGE EQ 1
title_s db 'Students of the 8086 course', 13, 10, '$'
avg_s   db 'Average mark: $'
best_s  db 'Best student: $'
ELSE
title_s db 'Students', 13, 10, '$'
avg_s   db 'Avg: $'
best_s  db 'Best: $'
ENDIF
newline db 13, 10, '$'
best    dw 0                    ; address of the best student

.code
print   macro text              ; print a '$' string (IFB: an empty call prints a new line)
IFB <text>
        lea dx, newline
ELSE
        lea dx, text
ENDIF
        mov ah, 9
        int 21h
        endm

main proc
        mov ax, @data
        mov ds, ax
        print title_s

        lea si, class           ; SI walks the array: size student bytes per element
        mov cx, COUNT
        xor bx, bx              ; BX = sum of the marks
        mov best, si
one:    lea dx, [si].sname
        mov ah, 9
        int 21h
        mov ax, [si].mark
        add bx, ax
        call print_num
IFDEF SHOW_GRADES
  IF SHOW_GRADES
        mov dl, ' '
        mov ah, 2
        int 21h
        mov dl, (student ptr [si]).grade
        int 21h
  ENDIF
ENDIF
        print
        mov di, best            ; best = SI when its mark is higher
        mov ax, [si].mark
        cmp ax, [di].mark
        jbe next
        mov best, si
next:   add si, size student
        loop one

        print avg_s
        mov ax, bx
        xor dx, dx
        mov cx, COUNT
        div cx
        call print_num
        print
        print best_s
        mov dx, best
        add dx, student.sname   ; offset of the field (0)
        mov ah, 9
        int 21h
        print
        mov ax, 4C00h
        int 21h
main endp

; print_num: AX as a decimal number
print_num proc
        push ax
        push bx
        push cx
        push dx
        mov bx, 10
        xor cx, cx
digit:  xor dx, dx
        div bx
        push dx
        inc cx
        test ax, ax
        jnz digit
out1:   pop dx
        add dl, '0'
        mov ah, 2
        int 21h
        loop out1
        pop dx
        pop cx
        pop bx
        pop ax
        ret
print_num endp
end main
