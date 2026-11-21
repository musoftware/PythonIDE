; =============================================================================================
; RAD IDE GUI Bridge - FASM (x64 Windows) include. Copied into the project by RAD IDE when it runs.
;
; Include it FIRST in a form's file: it starts the object (format MS64 COFF) and its code section. The form's
; file is assembled into an object and linked by gcc with the C client of the GUI Bridge (radgui.c + radasm.c).
; Every macro below:
;   * accepts a string literal ('Label1' or "Label1"), a control name of Form1.inc, a label (its address),
;     a register, a number or a memory operand ([clicks]),
;   * keeps the stack 16-byte aligned for the call (it can be used anywhere, even outside a handler),
;   * puts the result in RAX (text pointer / integer),
;   * may change RAX, RCX, RDX, R8 - R11 (the Win64 volatile registers).
; Arguments are loaded in the order RCX, RDX, R8: do not pass RCX / RDX as a later argument.
;
;   handler Command1_Click          ; an event handler: <Control>_<Event> (prologue + public)
;       rad_set 'Label1', 'Text', 'Hello from assembly!'
;       rad_get_int 'Text1', 'Text' ; RAX = the number typed in Text1
;       inc rax
;       rad_set_int 'Label1', 'Text', rax
;   endhandler                      ; epilogue + ret
;
;   rad_set obj, prop, text        rad_get obj, prop          -> RAX = char*
;   rad_set_int obj, prop, n       rad_get_int obj, prop      -> RAX = 64-bit integer
;   rad_call obj, method, args     -> RAX = char*
;   rad_msgbox text                rad_input prompt           -> RAX = char*
;   rad_show form   rad_hide form  rad_end  rad_print text    rad_arg n -> RAX = char*
;   radcall 'Module.func', '[2, 3]'  -> RAX = JSON text of the result (RAD Hub, other languages)
;   rad_str_int n -> RAX = char*     rad_int_str text -> RAX = integer
; =============================================================================================
format MS64 COFF

extrn rad_set
extrn rad_get
extrn rad_call
extrn rad_msgbox
extrn rad_input
extrn rad_show
extrn rad_hide
extrn rad_end
extrn rad_print
extrn rad_arg
extrn radcall
extrn rad_set_int
extrn rad_get_int
extrn rad_str_int
extrn rad_int_str

; RADARG reg, value : string -> address of a copy kept in the code; register / number / memory -> mov;
; any other name (a label) -> its address
macro RADARG reg, arg
{
  local text, skip
  if arg eqtype ''
    lea reg, [text]
    jmp skip
    text db arg, 0
    skip:
  else if arg in <rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15>
    mov reg, arg
  else if arg eqtype 0
    mov reg, arg
  else if arg eqtype [0]
    mov reg, arg
  else
    lea reg, [arg]
  end if
}

; RADCALL function : aligned call with 32 bytes of shadow space (RBP is saved and restored)
macro RADCALL fn
{
    push rbp
    mov rbp, rsp
    and rsp, -16
    sub rsp, 32
    call fn
    mov rsp, rbp
    pop rbp
}

; ---------------------------------------------------------------------------- event handlers
macro handler name
{
  public name
  name:
    push rbp
    mov rbp, rsp
    push rbx
    push rsi
    push rdi
    push r12
    and rsp, -16
    sub rsp, 32
}

macro endhandler
{
    lea rsp, [rbp - 32]
    pop r12
    pop rdi
    pop rsi
    pop rbx
    pop rbp
    ret
}

; ---------------------------------------------------------------------------- GUI Bridge calls
macro rad_set obj, prop, value
{
    RADARG rcx, obj
    RADARG rdx, prop
    RADARG r8, value
    RADCALL rad_set
}

macro rad_get obj, prop
{
    RADARG rcx, obj
    RADARG rdx, prop
    RADCALL rad_get
}

macro rad_set_int obj, prop, value
{
    RADARG rcx, obj
    RADARG rdx, prop
    RADARG r8, value
    RADCALL rad_set_int
}

macro rad_get_int obj, prop
{
    RADARG rcx, obj
    RADARG rdx, prop
    RADCALL rad_get_int
}

macro rad_call obj, method, args
{
    RADARG rcx, obj
    RADARG rdx, method
    RADARG r8, args
    RADCALL rad_call
}

macro rad_msgbox text
{
    RADARG rcx, text
    RADCALL rad_msgbox
}

macro rad_input prompt
{
    RADARG rcx, prompt
    RADCALL rad_input
}

macro rad_show form
{
    RADARG rcx, form
    RADCALL rad_show
}

macro rad_hide form
{
    RADARG rcx, form
    RADCALL rad_hide
}

macro rad_print text
{
    RADARG rcx, text
    RADCALL rad_print
}

macro rad_end
{
    RADCALL rad_end
}

macro rad_arg n
{
    RADARG rcx, n
    RADCALL rad_arg
}

macro rad_str_int n
{
    RADARG rcx, n
    RADCALL rad_str_int
}

macro rad_int_str text
{
    RADARG rcx, text
    RADCALL rad_int_str
}

macro radcall name, args
{
    RADARG rcx, name
    RADARG rdx, args
    RADCALL radcall
}

section '.text' code readable executable
