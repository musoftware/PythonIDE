; (c) 2026 Musoftware - https://musoftwares.com - MIT License
;
; NasmCalculator - Form1 event handlers (NASM, x64 Windows, GUI Bridge).
; The IDE draws the form; every handler below reads the two text boxes with rad_get_int, does 64-bit integer
; arithmetic in registers, formats the result with the C runtime's sprintf and writes it back with rad_set /
; rad_call (ListBox.AddItem). Shows: menus (File > Clear history / Exit, Help > About), MsgBox, a ListBox used
; as a history, guarding against division by zero, a loop (Power) and overflow detection (JO).
;
; Register rules inside a handler (see radgui.inc): RBX, RSI, RDI and R12 are ours and survive the rad_* macros;
; RSP is 16-byte aligned with 32 bytes of shadow space, so plain "call sprintf" is allowed too.
%include "radgui.inc"
%include "Form1.inc"           ; generated from Form1.form: the control names (txtA, lblResult, lstHistory ...)

extern sprintf

section .data
    count       dq 0                            ; number of calculations done
    fmt_line    db "%lld %s %lld = %lld", 0     ; history line
    fmt_result  db "Result: %lld", 0
    fmt_count   db "%lld calculation(s)", 0
    op_add      db "+", 0
    op_sub      db "-", 0
    op_mul      db "x", 0
    op_div      db "/", 0
    op_mod      db "mod", 0
    op_pow      db "^", 0

section .bss
    buf         resb 160                        ; sprintf output

section .text

; ------------------------------------------------------------------ helpers
; read_operands: RSI = first number, RDI = second number (both text boxes, read as 64-bit integers)
read_operands:
    sub rsp, 8                                  ; keep RSP 16-byte aligned for the macro calls
    rad_get_int txtA, "Text"
    mov rsi, rax
    rad_get_int txtB, "Text"
    mov rdi, rax
    add rsp, 8
    ret

; show_result: RSI op RDI = RBX, R12 = the operator text. Writes the result label, adds a history line and
; updates the counter label.
show_result:
    sub rsp, 40                                 ; 32 bytes shadow space + 8 = aligned
    lea rcx, [buf]                              ; sprintf(buf, "Result: %lld", rbx)
    lea rdx, [fmt_result]
    mov r8, rbx
    call sprintf
    rad_set lblResult, "Text", buf
    lea rcx, [buf]                              ; sprintf(buf, "%lld %s %lld = %lld", rsi, r12, rdi, rbx)
    lea rdx, [fmt_line]
    mov r8, rsi
    mov r9, r12
    sub rsp, 16                                 ; two more argument slots (keeps the alignment):
                                                ; the 5th and 6th arguments go after the shadow space
    mov [rsp + 32], rdi
    mov [rsp + 40], rbx
    call sprintf
    add rsp, 16
    rad_call lstHistory, "AddItem", buf
    inc qword [count]
    lea rcx, [buf]
    lea rdx, [fmt_count]
    mov r8, [count]
    call sprintf
    rad_set lblCount, "Text", buf
    add rsp, 40
    ret

; ------------------------------------------------------------------ events
handler Form1_Load
    rad_set lblResult, "Text", "Type two whole numbers and press an operator."
endhandler

handler btnAdd_Click
    call read_operands
    mov rbx, rsi
    add rbx, rdi
    jo .overflow
    lea r12, [op_add]
    call show_result
    jmp .done
.overflow:
    rad_msgbox "The result does not fit in 64 bits."
.done:
endhandler

handler btnSub_Click
    call read_operands
    mov rbx, rsi
    sub rbx, rdi
    jo .overflow
    lea r12, [op_sub]
    call show_result
    jmp .done
.overflow:
    rad_msgbox "The result does not fit in 64 bits."
.done:
endhandler

handler btnMul_Click
    call read_operands
    mov rbx, rsi
    imul rbx, rdi                               ; signed 64 x 64 -> 64, OF set when it does not fit
    jo .overflow
    lea r12, [op_mul]
    call show_result
    jmp .done
.overflow:
    rad_msgbox "The result does not fit in 64 bits."
.done:
endhandler

handler btnDiv_Click
    call read_operands
    test rdi, rdi
    jz .by_zero
    mov rax, rsi
    cqo                                         ; RDX:RAX = sign-extended dividend
    idiv rdi                                    ; RAX = quotient, RDX = remainder
    mov rbx, rax
    lea r12, [op_div]
    call show_result
    jmp .done
.by_zero:
    rad_set lblResult, "Text", "Result: cannot divide by zero"
    rad_msgbox "Division by zero is not allowed."
.done:
endhandler

handler btnMod_Click
    call read_operands
    test rdi, rdi
    jz .by_zero
    mov rax, rsi
    cqo
    idiv rdi
    mov rbx, rdx                                ; the remainder
    lea r12, [op_mod]
    call show_result
    jmp .done
.by_zero:
    rad_msgbox "Division by zero is not allowed."
.done:
endhandler

handler btnPow_Click
    call read_operands
    test rdi, rdi
    js .negative
    mov rbx, 1                                  ; result = 1
    mov rcx, rdi                                ; counter = exponent
.next:
    test rcx, rcx
    jz .finished
    imul rbx, rsi
    jo .overflow
    dec rcx
    jmp .next
.finished:
    lea r12, [op_pow]
    call show_result
    jmp .done
.negative:
    rad_msgbox "Use an exponent of 0 or more."
    jmp .done
.overflow:
    rad_msgbox "The result does not fit in 64 bits."
.done:
endhandler

handler mnuFileClear_Click
    rad_call lstHistory, "Clear", ""
    mov qword [count], 0
    rad_set lblCount, "Text", "0 calculations"
    rad_set lblResult, "Text", "Result: -"
endhandler

handler mnuFileExit_Click
    rad_end
endhandler

handler mnuHelpAbout_Click
    rad_msgbox "NasmCalculator - integer calculator written in x64 NASM assembly with a RAD IDE form."
endhandler
