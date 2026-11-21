; =============================================================================================
; RAD IDE GUI Bridge - NASM (x64 Windows) include. Copied into the project by RAD IDE when it runs.
;
; The IDE draws the forms. Your assembly code handles the events and talks to the controls through the
; C client (radgui.c + radasm.c, linked with gcc). Every macro below:
;   * accepts a string literal ("Label1"), a label of a zero-terminated string, a register or a number,
;   * keeps the stack 16-byte aligned for the call (it can be used anywhere, even outside a handler),
;   * puts the result in RAX (text pointer / integer) or XMM0 (double),
;   * may change RAX, RCX, RDX, R8 - R11 and XMM0 - XMM5 (the Win64 volatile registers).
; Arguments are loaded in the order RCX, RDX, R8, R9: do not pass RCX / RDX / R8 as a later argument.
;
;   handler Command1_Click          ; an event handler: <Control>_<Event> (prologue + global)
;       rad_set "Label1", "Text", "Hello from assembly!"
;       rad_get_int "Text1", "Text" ; RAX = the number typed in Text1
;       inc rax
;       rad_set_int "Label1", "Text", rax
;   endhandler                      ; epilogue + ret
;
;   rad_set obj, prop, text        rad_get obj, prop          -> RAX = char*
;   rad_set_int obj, prop, n       rad_get_int obj, prop      -> RAX = 64-bit integer
;   rad_call obj, method, args     -> RAX = char* (method arguments separated by TAB)
;   rad_msgbox text                rad_input prompt           -> RAX = char*
;   rad_show form   rad_hide form  rad_end  rad_print text    rad_arg n -> RAX = char* (X Y Button KeyCode KeyChar)
;   radcall "Module.func", "[2, 3]"  -> RAX = JSON text of the result (RAD Hub, other languages)
;   rad_str_int n -> RAX = char* (integer to text)   rad_int_str text -> RAX = integer (text to integer)
; =============================================================================================
%ifndef RADGUI_INC
%define RADGUI_INC

default rel

extern rad_set, rad_get, rad_call, rad_msgbox, rad_input, rad_show, rad_hide, rad_end, rad_print
extern rad_num, rad_str, rad_arg, radcall, rad_error, rad_init, rad_next_event, rad_done
extern rad_obj, rad_ev, rad_args
extern rad_set_int, rad_get_int, rad_str_int, rad_int_str

; RADARG reg, value : string literal -> address of a hidden copy in .rdata; register / number / memory
; operand ([x], qword [rbx+8]) -> mov; any other name (a label) -> its address (lea).
%macro RADARG 2
  %ifstr %2
    [section .rdata]
    %%text: db %2, 0
    __?SECT?__
    lea %1, [rel %%text]
  %elifnum %2
    mov %1, %2
  %elifnid %2
    mov %1, %2
  %else
    %assign %%reg 0
    %ifidni %2, rax
      %assign %%reg 1
    %elifidni %2, rbx
      %assign %%reg 1
    %elifidni %2, rcx
      %assign %%reg 1
    %elifidni %2, rdx
      %assign %%reg 1
    %elifidni %2, rsi
      %assign %%reg 1
    %elifidni %2, rdi
      %assign %%reg 1
    %elifidni %2, rbp
      %assign %%reg 1
    %elifidni %2, r8
      %assign %%reg 1
    %elifidni %2, r9
      %assign %%reg 1
    %elifidni %2, r10
      %assign %%reg 1
    %elifidni %2, r11
      %assign %%reg 1
    %elifidni %2, r12
      %assign %%reg 1
    %elifidni %2, r13
      %assign %%reg 1
    %elifidni %2, r14
      %assign %%reg 1
    %elifidni %2, r15
      %assign %%reg 1
    %endif
    %if %%reg
      mov %1, %2
    %else
      lea %1, [rel %2]
    %endif
  %endif
%endmacro

; RADCALL function : aligned call with 32 bytes of shadow space (RBP is saved and restored)
%macro RADCALL 1
    push rbp
    mov rbp, rsp
    and rsp, -16
    sub rsp, 32
    call %1
    mov rsp, rbp
    pop rbp
%endmacro

; ---------------------------------------------------------------------------- event handlers
; handler Name : global label + frame (RBP) with the stack aligned; locals: sub rsp, N (N multiple of 16)
%macro handler 1
  global %1
  %1:
    push rbp
    mov rbp, rsp
    push rbx
    push rsi
    push rdi
    push r12
    and rsp, -16
    sub rsp, 32
%endmacro

%macro endhandler 0
    lea rsp, [rbp - 32]
    pop r12
    pop rdi
    pop rsi
    pop rbx
    pop rbp
    ret
%endmacro

; ---------------------------------------------------------------------------- GUI Bridge calls
%macro rad_set 3
    RADARG rcx, %1
    RADARG rdx, %2
    RADARG r8, %3
    RADCALL rad_set
%endmacro

%macro rad_get 2
    RADARG rcx, %1
    RADARG rdx, %2
    RADCALL rad_get
%endmacro

%macro rad_set_int 3
    RADARG rcx, %1
    RADARG rdx, %2
    RADARG r8, %3
    RADCALL rad_set_int
%endmacro

%macro rad_get_int 2
    RADARG rcx, %1
    RADARG rdx, %2
    RADCALL rad_get_int
%endmacro

%macro rad_call 3
    RADARG rcx, %1
    RADARG rdx, %2
    RADARG r8, %3
    RADCALL rad_call
%endmacro

%macro rad_msgbox 1
    RADARG rcx, %1
    RADCALL rad_msgbox
%endmacro

%macro rad_input 1
    RADARG rcx, %1
    RADCALL rad_input
%endmacro

%macro rad_show 1
    RADARG rcx, %1
    RADCALL rad_show
%endmacro

%macro rad_hide 1
    RADARG rcx, %1
    RADCALL rad_hide
%endmacro

%macro rad_print 1
    RADARG rcx, %1
    RADCALL rad_print
%endmacro

%macro rad_end 0
    RADCALL rad_end
%endmacro

%macro rad_arg 1
    RADARG rcx, %1
    RADCALL rad_arg
%endmacro

%macro rad_str_int 1
    RADARG rcx, %1
    RADCALL rad_str_int
%endmacro

%macro rad_int_str 1
    RADARG rcx, %1
    RADCALL rad_int_str
%endmacro

%macro radcall 2
    RADARG rcx, %1
    RADARG rdx, %2
    RADCALL radcall
%endmacro

%endif
