%include "radgui.inc"
%include "Form1.inc"

section .text

handler btnAdd_Click
    rad_get_int txtA, "Text"     ; rax = A
    mov rbx, rax                 ; rbx يبقى بعد الماكرو التالي
    rad_get_int txtB, "Text"     ; rax = B
    add rbx, rax
    rad_set_int lblResult, "Text", rbx
endhandler

handler btnMul_Click
    rad_get_int txtA, "Text"
    mov rbx, rax
    rad_get_int txtB, "Text"
    imul rbx, rax
    rad_set_int lblResult, "Text", rbx
endhandler
