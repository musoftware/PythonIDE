# =============================================================================================
# RAD IDE GUI Bridge - GNU as (x64 Windows, Intel syntax: .intel_syntax noprefix) include. Copied into the
# project by RAD IDE.
#
# The IDE draws the forms; the form's file is assembled with  as --64  and linked by gcc with the C client of
# the GUI Bridge (radgui.c + radasm.c). GNU as removes the quotes of macro arguments, so the macros look at
# the ROLE of each argument:
#   * object / property / text arguments: a register (rbx: a char* you prepared) or anything else, which is
#     taken as TEXT:  rad_set lblOut, Text, "Hello world"  (quote text with spaces or commas);
#     a label of your own string must be loaded into a register first (lea rbx, [rip + msg]);
#   * integer arguments (rad_set_int, rad_str_int, rad_arg): a register (rbx), a number (42) or memory
#     (QWORD PTR [rip + clicks]).
# Every macro keeps the stack 16-byte aligned for the call, puts the result in RAX and may change RAX, RCX,
# RDX, R8 - R11 (the Win64 volatile registers). Arguments are loaded in the order RCX, RDX, R8: do not pass
# RCX / RDX as a later argument.
#
#   handler Command1_Click          # an event handler: <Control>_<Event> (prologue + .globl)
#       rad_set Label1, Text, "Hello from assembly!"
#       rad_get_int Text1, Text     # RAX = the number typed in Text1
#       inc     rax
#       rad_set_int Label1, Text, rax
#   endhandler                      # epilogue + ret
#
#   rad_set obj, prop, text        rad_get obj, prop          -> RAX = char*
#   rad_set_int obj, prop, n       rad_get_int obj, prop      -> RAX = 64-bit integer
#   rad_call obj, method, args     rad_msgbox text            rad_input prompt -> RAX = char*
#   rad_show form   rad_hide form  rad_end  rad_print text    rad_arg n -> RAX = char*
#   radcall "Module.func", "[2, 3]" -> RAX = JSON text   rad_str_int n   rad_int_str text
# =============================================================================================
        .intel_syntax noprefix

# RAD_INVOKE function : aligned call with 32 bytes of shadow space (RBP is saved and restored)
.macro RAD_INVOKE fn
        push    rbp
        mov     rbp, rsp
        and     rsp, -16
        sub     rsp, 32
        call    \fn
        mov     rsp, rbp
        pop     rbp
.endm

# ---------------------------------------------------------------------------- event handlers
.macro handler name
        .text
        .globl  \name
\name:
        push    rbp
        mov     rbp, rsp
        push    rbx
        push    rsi
        push    rdi
        push    r12
        and     rsp, -16
        sub     rsp, 32
.endm

.macro endhandler
        lea     rsp, [rbp - 32]
        pop     r12
        pop     rdi
        pop     rsi
        pop     rbx
        pop     rbp
        ret
.endm

# ---------------------------------------------------------------------------- GUI Bridge calls
.macro rad_set obj, prop, value
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\obj","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rcx, \obj
  .else
        jmp     .Lrad_eobj\@
.Lrad_sobj\@: .asciz "\obj"
.Lrad_eobj\@:
        lea     rcx, [rip + .Lrad_sobj\@]
  .endif
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\prop","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rdx, \prop
  .else
        jmp     .Lrad_eprop\@
.Lrad_sprop\@: .asciz "\prop"
.Lrad_eprop\@:
        lea     rdx, [rip + .Lrad_sprop\@]
  .endif
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\value","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     r8, \value
  .else
        jmp     .Lrad_evalue\@
.Lrad_svalue\@: .asciz "\value"
.Lrad_evalue\@:
        lea     r8, [rip + .Lrad_svalue\@]
  .endif
        RAD_INVOKE rad_set
.endm

.macro rad_get obj, prop
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\obj","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rcx, \obj
  .else
        jmp     .Lrad_eobj\@
.Lrad_sobj\@: .asciz "\obj"
.Lrad_eobj\@:
        lea     rcx, [rip + .Lrad_sobj\@]
  .endif
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\prop","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rdx, \prop
  .else
        jmp     .Lrad_eprop\@
.Lrad_sprop\@: .asciz "\prop"
.Lrad_eprop\@:
        lea     rdx, [rip + .Lrad_sprop\@]
  .endif
        RAD_INVOKE rad_get
.endm

.macro rad_set_int obj, prop, value:vararg
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\obj","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rcx, \obj
  .else
        jmp     .Lrad_eobj\@
.Lrad_sobj\@: .asciz "\obj"
.Lrad_eobj\@:
        lea     rcx, [rip + .Lrad_sobj\@]
  .endif
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\prop","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rdx, \prop
  .else
        jmp     .Lrad_eprop\@
.Lrad_sprop\@: .asciz "\prop"
.Lrad_eprop\@:
        lea     rdx, [rip + .Lrad_sprop\@]
  .endif
        mov     r8, \value
        RAD_INVOKE rad_set_int
.endm

.macro rad_get_int obj, prop
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\obj","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rcx, \obj
  .else
        jmp     .Lrad_eobj\@
.Lrad_sobj\@: .asciz "\obj"
.Lrad_eobj\@:
        lea     rcx, [rip + .Lrad_sobj\@]
  .endif
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\prop","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rdx, \prop
  .else
        jmp     .Lrad_eprop\@
.Lrad_sprop\@: .asciz "\prop"
.Lrad_eprop\@:
        lea     rdx, [rip + .Lrad_sprop\@]
  .endif
        RAD_INVOKE rad_get_int
.endm

.macro rad_call obj, method, args
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\obj","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rcx, \obj
  .else
        jmp     .Lrad_eobj\@
.Lrad_sobj\@: .asciz "\obj"
.Lrad_eobj\@:
        lea     rcx, [rip + .Lrad_sobj\@]
  .endif
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\method","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rdx, \method
  .else
        jmp     .Lrad_emethod\@
.Lrad_smethod\@: .asciz "\method"
.Lrad_emethod\@:
        lea     rdx, [rip + .Lrad_smethod\@]
  .endif
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\args","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     r8, \args
  .else
        jmp     .Lrad_eargs\@
.Lrad_sargs\@: .asciz "\args"
.Lrad_eargs\@:
        lea     r8, [rip + .Lrad_sargs\@]
  .endif
        RAD_INVOKE rad_call
.endm

.macro rad_msgbox text
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\text","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rcx, \text
  .else
        jmp     .Lrad_etext\@
.Lrad_stext\@: .asciz "\text"
.Lrad_etext\@:
        lea     rcx, [rip + .Lrad_stext\@]
  .endif
        RAD_INVOKE rad_msgbox
.endm

.macro rad_input prompt
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\prompt","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rcx, \prompt
  .else
        jmp     .Lrad_eprompt\@
.Lrad_sprompt\@: .asciz "\prompt"
.Lrad_eprompt\@:
        lea     rcx, [rip + .Lrad_sprompt\@]
  .endif
        RAD_INVOKE rad_input
.endm

.macro rad_show form
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\form","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rcx, \form
  .else
        jmp     .Lrad_eform\@
.Lrad_sform\@: .asciz "\form"
.Lrad_eform\@:
        lea     rcx, [rip + .Lrad_sform\@]
  .endif
        RAD_INVOKE rad_show
.endm

.macro rad_hide form
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\form","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rcx, \form
  .else
        jmp     .Lrad_eform\@
.Lrad_sform\@: .asciz "\form"
.Lrad_eform\@:
        lea     rcx, [rip + .Lrad_sform\@]
  .endif
        RAD_INVOKE rad_hide
.endm

.macro rad_print text
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\text","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rcx, \text
  .else
        jmp     .Lrad_etext\@
.Lrad_stext\@: .asciz "\text"
.Lrad_etext\@:
        lea     rcx, [rip + .Lrad_stext\@]
  .endif
        RAD_INVOKE rad_print
.endm

.macro rad_end
        RAD_INVOKE rad_end
.endm

.macro rad_arg n:vararg
        mov     rcx, \n
        RAD_INVOKE rad_arg
.endm

.macro rad_str_int n:vararg
        mov     rcx, \n
        RAD_INVOKE rad_str_int
.endm

.macro rad_int_str text
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\text","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rcx, \text
  .else
        jmp     .Lrad_etext\@
.Lrad_stext\@: .asciz "\text"
.Lrad_etext\@:
        lea     rcx, [rip + .Lrad_stext\@]
  .endif
        RAD_INVOKE rad_int_str
.endm

.macro radcall name, args
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\name","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rcx, \name
  .else
        jmp     .Lrad_ename\@
.Lrad_sname\@: .asciz "\name"
.Lrad_ename\@:
        lea     rcx, [rip + .Lrad_sname\@]
  .endif
  .set .Lrad_isreg, 0
  .irp rr, rax,rbx,rcx,rdx,rsi,rdi,rbp,r8,r9,r10,r11,r12,r13,r14,r15,RAX,RBX,RCX,RDX,RSI,RDI,RBP,R8,R9,R10,R11,R12,R13,R14,R15
    .ifc "\args","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        mov     rdx, \args
  .else
        jmp     .Lrad_eargs\@
.Lrad_sargs\@: .asciz "\args"
.Lrad_eargs\@:
        lea     rdx, [rip + .Lrad_sargs\@]
  .endif
        RAD_INVOKE radcall
.endm
