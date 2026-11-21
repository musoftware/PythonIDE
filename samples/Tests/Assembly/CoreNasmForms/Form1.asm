; Event handlers of Form1 (NASM, x64). The IDE draws the form (GUI Bridge); this code reacts to its
; events and changes the controls with the macros of radgui.inc: rad_set, rad_get, rad_get_int, rad_set_int,
; rad_msgbox, rad_input, rad_call ... (see the top of radgui.inc).
;
; A handler is a block   handler <Control>_<Event> ... endhandler   - double-click a control in the designer
; to add one. Inside a handler RBX, RSI, RDI and R12 are yours (they are saved); do not change RBP or RSP.
%include "radgui.inc"
%include "Form1.inc"           ; generated: the names of the controls of Form1 (lblMessage, btnAdd ...)

section .data
    clicks      dq 0

section .text

handler Form1_Load
    rad_set lblMessage, "Text", "Hello from assembly! Type a number and press Add 1."
endhandler

handler btnAdd_Click
    rad_get_int txtNumber, "Text"   ; RAX = the number in the text box
    inc rax
    mov rbx, rax                    ; RBX survives the next macro calls
    rad_set_int txtNumber, "Text", rbx
    inc qword [clicks]
    rad_set_int lblClicks, "Text", [clicks]
    rad_set lblMessage, "Text", "The assembly handler added 1."
endhandler

handler btnHello_Click
    rad_input "What is your name?"  ; RAX = the text typed (a C string)
    mov rbx, rax
    rad_set lblMessage, "Text", rbx
    rad_msgbox "Hello from x64 assembly!"
endhandler
