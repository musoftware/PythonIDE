# =============================================================================================
# RAD IDE GUI Bridge - GNU as (x64 Windows, AT&T syntax) include. Copied into the project by RAD IDE.
#
# The IDE draws the forms; the form's file is assembled with  as --64  and linked by gcc with the C client of
# the GUI Bridge (radgui.c + radasm.c). GNU as removes the quotes of macro arguments, so the macros look at
# the ROLE of each argument:
#   * object / property / text arguments: a register (%rbx: a char* you prepared) or anything else, which is
#     taken as TEXT:  rad_set lblOut, Text, "Hello world"  (quote text with spaces or commas);
#     a label of your own string must be loaded into a register first (leaq msg(%rip), %rbx);
#   * integer arguments (rad_set_int, rad_str_int, rad_arg): a register (%rbx), a number ($42) or memory
#     (clicks(%rip)).
# Every macro keeps the stack 16-byte aligned for the call, puts the result in %rax and may change %rax,
# %rcx, %rdx, %r8 - %r11 (the Win64 volatile registers). Arguments are loaded in the order %rcx, %rdx, %r8:
# do not pass %rcx / %rdx as a later argument.
#
#   handler Command1_Click          # an event handler: <Control>_<Event> (prologue + .globl)
#       rad_set Label1, Text, "Hello from assembly!"
#       rad_get_int Text1, Text     # %rax = the number typed in Text1
#       incq    %rax
#       rad_set_int Label1, Text, %rax
#   endhandler                      # epilogue + ret
#
#   rad_set obj, prop, text        rad_get obj, prop          -> %rax = char*
#   rad_set_int obj, prop, n       rad_get_int obj, prop      -> %rax = 64-bit integer
#   rad_call obj, method, args     rad_msgbox text            rad_input prompt -> %rax = char*
#   rad_show form   rad_hide form  rad_end  rad_print text    rad_arg n -> %rax = char*
#   radcall "Module.func", "[2, 3]" -> %rax = JSON text   rad_str_int n   rad_int_str text
# =============================================================================================

# RAD_INVOKE function : aligned call with 32 bytes of shadow space (%rbp is saved and restored)
.macro RAD_INVOKE fn
        pushq   %rbp
        movq    %rsp, %rbp
        andq    $-16, %rsp
        subq    $32, %rsp
        call    \fn
        movq    %rbp, %rsp
        popq    %rbp
.endm

# ---------------------------------------------------------------------------- event handlers
.macro handler name
        .text
        .globl  \name
\name:
        pushq   %rbp
        movq    %rsp, %rbp
        pushq   %rbx
        pushq   %rsi
        pushq   %rdi
        pushq   %r12
        andq    $-16, %rsp
        subq    $32, %rsp
.endm

.macro endhandler
        leaq    -32(%rbp), %rsp
        popq    %r12
        popq    %rdi
        popq    %rsi
        popq    %rbx
        popq    %rbp
        ret
.endm

# ---------------------------------------------------------------------------- GUI Bridge calls
.macro rad_set obj, prop, value
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\obj","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \obj, %rcx
  .else
        jmp     .Lrad_eobj\@
.Lrad_sobj\@: .asciz "\obj"
.Lrad_eobj\@:
        leaq    .Lrad_sobj\@(%rip), %rcx
  .endif
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\prop","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \prop, %rdx
  .else
        jmp     .Lrad_eprop\@
.Lrad_sprop\@: .asciz "\prop"
.Lrad_eprop\@:
        leaq    .Lrad_sprop\@(%rip), %rdx
  .endif
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\value","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \value, %r8
  .else
        jmp     .Lrad_evalue\@
.Lrad_svalue\@: .asciz "\value"
.Lrad_evalue\@:
        leaq    .Lrad_svalue\@(%rip), %r8
  .endif
        RAD_INVOKE rad_set
.endm

.macro rad_get obj, prop
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\obj","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \obj, %rcx
  .else
        jmp     .Lrad_eobj\@
.Lrad_sobj\@: .asciz "\obj"
.Lrad_eobj\@:
        leaq    .Lrad_sobj\@(%rip), %rcx
  .endif
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\prop","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \prop, %rdx
  .else
        jmp     .Lrad_eprop\@
.Lrad_sprop\@: .asciz "\prop"
.Lrad_eprop\@:
        leaq    .Lrad_sprop\@(%rip), %rdx
  .endif
        RAD_INVOKE rad_get
.endm

.macro rad_set_int obj, prop, value:vararg
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\obj","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \obj, %rcx
  .else
        jmp     .Lrad_eobj\@
.Lrad_sobj\@: .asciz "\obj"
.Lrad_eobj\@:
        leaq    .Lrad_sobj\@(%rip), %rcx
  .endif
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\prop","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \prop, %rdx
  .else
        jmp     .Lrad_eprop\@
.Lrad_sprop\@: .asciz "\prop"
.Lrad_eprop\@:
        leaq    .Lrad_sprop\@(%rip), %rdx
  .endif
        movq    \value, %r8
        RAD_INVOKE rad_set_int
.endm

.macro rad_get_int obj, prop
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\obj","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \obj, %rcx
  .else
        jmp     .Lrad_eobj\@
.Lrad_sobj\@: .asciz "\obj"
.Lrad_eobj\@:
        leaq    .Lrad_sobj\@(%rip), %rcx
  .endif
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\prop","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \prop, %rdx
  .else
        jmp     .Lrad_eprop\@
.Lrad_sprop\@: .asciz "\prop"
.Lrad_eprop\@:
        leaq    .Lrad_sprop\@(%rip), %rdx
  .endif
        RAD_INVOKE rad_get_int
.endm

.macro rad_call obj, method, args
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\obj","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \obj, %rcx
  .else
        jmp     .Lrad_eobj\@
.Lrad_sobj\@: .asciz "\obj"
.Lrad_eobj\@:
        leaq    .Lrad_sobj\@(%rip), %rcx
  .endif
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\method","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \method, %rdx
  .else
        jmp     .Lrad_emethod\@
.Lrad_smethod\@: .asciz "\method"
.Lrad_emethod\@:
        leaq    .Lrad_smethod\@(%rip), %rdx
  .endif
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\args","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \args, %r8
  .else
        jmp     .Lrad_eargs\@
.Lrad_sargs\@: .asciz "\args"
.Lrad_eargs\@:
        leaq    .Lrad_sargs\@(%rip), %r8
  .endif
        RAD_INVOKE rad_call
.endm

.macro rad_msgbox text
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\text","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \text, %rcx
  .else
        jmp     .Lrad_etext\@
.Lrad_stext\@: .asciz "\text"
.Lrad_etext\@:
        leaq    .Lrad_stext\@(%rip), %rcx
  .endif
        RAD_INVOKE rad_msgbox
.endm

.macro rad_input prompt
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\prompt","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \prompt, %rcx
  .else
        jmp     .Lrad_eprompt\@
.Lrad_sprompt\@: .asciz "\prompt"
.Lrad_eprompt\@:
        leaq    .Lrad_sprompt\@(%rip), %rcx
  .endif
        RAD_INVOKE rad_input
.endm

.macro rad_show form
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\form","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \form, %rcx
  .else
        jmp     .Lrad_eform\@
.Lrad_sform\@: .asciz "\form"
.Lrad_eform\@:
        leaq    .Lrad_sform\@(%rip), %rcx
  .endif
        RAD_INVOKE rad_show
.endm

.macro rad_hide form
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\form","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \form, %rcx
  .else
        jmp     .Lrad_eform\@
.Lrad_sform\@: .asciz "\form"
.Lrad_eform\@:
        leaq    .Lrad_sform\@(%rip), %rcx
  .endif
        RAD_INVOKE rad_hide
.endm

.macro rad_print text
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\text","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \text, %rcx
  .else
        jmp     .Lrad_etext\@
.Lrad_stext\@: .asciz "\text"
.Lrad_etext\@:
        leaq    .Lrad_stext\@(%rip), %rcx
  .endif
        RAD_INVOKE rad_print
.endm

.macro rad_end
        RAD_INVOKE rad_end
.endm

.macro rad_arg n:vararg
        movq    \n, %rcx
        RAD_INVOKE rad_arg
.endm

.macro rad_str_int n:vararg
        movq    \n, %rcx
        RAD_INVOKE rad_str_int
.endm

.macro rad_int_str text
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\text","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \text, %rcx
  .else
        jmp     .Lrad_etext\@
.Lrad_stext\@: .asciz "\text"
.Lrad_etext\@:
        leaq    .Lrad_stext\@(%rip), %rcx
  .endif
        RAD_INVOKE rad_int_str
.endm

.macro radcall name, args
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\name","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \name, %rcx
  .else
        jmp     .Lrad_ename\@
.Lrad_sname\@: .asciz "\name"
.Lrad_ename\@:
        leaq    .Lrad_sname\@(%rip), %rcx
  .endif
  .set .Lrad_isreg, 0
  .irp rr, %rax,%rbx,%rcx,%rdx,%rsi,%rdi,%rbp,%r8,%r9,%r10,%r11,%r12,%r13,%r14,%r15
    .ifc "\args","\rr"
      .set .Lrad_isreg, 1
    .endif
  .endr
  .if .Lrad_isreg
        movq    \args, %rdx
  .else
        jmp     .Lrad_eargs\@
.Lrad_sargs\@: .asciz "\args"
.Lrad_eargs\@:
        leaq    .Lrad_sargs\@(%rip), %rdx
  .endif
        RAD_INVOKE radcall
.endm
