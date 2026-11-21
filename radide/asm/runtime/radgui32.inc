; =============================================================================================
; RAD IDE GUI Bridge - NASM (x86, 32-bit Windows) include. Copied into the project by RAD IDE when it runs.
;
; The IDE draws the forms. Your assembly code handles the events and talks to the controls through the
; C client (radgui.c + radasm.c compiled with gcc -m32, linked with GNU ld against ucrtbase.dll). The macros
; push their arguments (cdecl: right to left) and remove them after the call. Every macro:
;   * accepts a string literal ("Label1"), a %define'd control name, a label (its address), a register,
;     a number or a memory operand ([clicks]),
;   * puts the result in EAX (text pointer / integer),
;   * may change EAX, ECX and EDX (the 32-bit volatile registers); EBX, ESI, EDI are kept.
; rad_set_int loads its value into EAX first: do not pass EAX / EDX as its object or property.
;
;   handler Command1_Click          ; an event handler: <Control>_<Event> (frame + global)
;       rad_set "Label1", "Text", "Hello from assembly!"
;       rad_get_int "Text1", "Text" ; EAX = the number typed in Text1
;       inc eax
;       rad_set_int "Label1", "Text", eax
;   endhandler                      ; epilogue + ret
;
;   rad_set obj, prop, text        rad_get obj, prop          -> EAX = char*
;   rad_set_int obj, prop, n       rad_get_int obj, prop      -> EAX = 32-bit integer
;   rad_call obj, method, args     -> EAX = char* (method arguments separated by TAB)
;   rad_msgbox text                rad_input prompt           -> EAX = char*
;   rad_show form   rad_hide form  rad_end  rad_print text    rad_arg n -> EAX = char* (X Y Button KeyCode KeyChar)
;   radcall "Module.func", "[2, 3]"  -> EAX = JSON text of the result (RAD Hub, other languages)
;   rad_str_int n -> EAX = char* (integer to text)   rad_int_str text -> EAX = integer (text to integer)
; =============================================================================================
%ifndef RADGUI32_INC
%define RADGUI32_INC

extern _rad_set, _rad_get, _rad_call, _rad_msgbox, _rad_input, _rad_show, _rad_hide, _rad_end, _rad_print
extern _rad_arg, _radcall, _rad_error, _rad_init, _rad_next_event, _rad_done
extern _rad_obj, _rad_ev, _rad_args
extern _rad_set_int, _rad_get_int, _rad_str_int, _rad_int_str

; RADISREG name : %%isreg = 1 when the argument is a 32-bit general purpose register
%macro RADISREG 1
  %assign RADREG 0
  %ifidni %1, eax
    %assign RADREG 1
  %elifidni %1, ebx
    %assign RADREG 1
  %elifidni %1, ecx
    %assign RADREG 1
  %elifidni %1, edx
    %assign RADREG 1
  %elifidni %1, esi
    %assign RADREG 1
  %elifidni %1, edi
    %assign RADREG 1
  %elifidni %1, ebp
    %assign RADREG 1
  %endif
%endmacro

; RADPUSH value : string literal -> address of a hidden copy in .rdata; register -> push reg;
; number / memory operand / label -> push dword value (a label pushes its address)
%macro RADPUSH 1
  %ifstr %1
    [section .rdata]
    %%text: db %1, 0
    __?SECT?__
    push dword %%text
  %else
    RADISREG %1
    %if RADREG
      push %1
    %else
      push dword %1
    %endif
  %endif
%endmacro

; RADLOAD value : EAX = value (register, number, memory operand; a label gives its address)
%macro RADLOAD 1
  %ifstr %1
    [section .rdata]
    %%text: db %1, 0
    __?SECT?__
    mov eax, %%text
  %else
    RADISREG %1
    %if RADREG
      %ifnidni %1, eax
        mov eax, %1
      %endif
    %else
      mov eax, %1
    %endif
  %endif
%endmacro

; ---------------------------------------------------------------------------- event handlers
; handler Name : global label + frame (EBP); EBX, ESI, EDI are saved and free to use; locals: sub esp, N
%macro handler 1
  global %1
  %1:
    push ebp
    mov ebp, esp
    push ebx
    push esi
    push edi
%endmacro

%macro endhandler 0
    lea esp, [ebp - 12]
    pop edi
    pop esi
    pop ebx
    pop ebp
    ret
%endmacro

; ---------------------------------------------------------------------------- GUI Bridge calls
%macro rad_set 3
    RADPUSH %3
    RADPUSH %2
    RADPUSH %1
    call _rad_set
    add esp, 12
%endmacro

%macro rad_get 2
    RADPUSH %2
    RADPUSH %1
    call _rad_get
    add esp, 8
%endmacro

%macro rad_set_int 3
    RADLOAD %3
    cdq                             ; long long value = EDX:EAX
    push edx
    push eax
    RADPUSH %2
    RADPUSH %1
    call _rad_set_int
    add esp, 16
%endmacro

%macro rad_get_int 2
    RADPUSH %2
    RADPUSH %1
    call _rad_get_int               ; long long in EDX:EAX - EAX is the 32-bit value
    add esp, 8
%endmacro

%macro rad_call 3
    RADPUSH %3
    RADPUSH %2
    RADPUSH %1
    call _rad_call
    add esp, 12
%endmacro

%macro rad_msgbox 1
    RADPUSH %1
    call _rad_msgbox
    add esp, 4
%endmacro

%macro rad_input 1
    RADPUSH %1
    call _rad_input
    add esp, 4
%endmacro

%macro rad_show 1
    RADPUSH %1
    call _rad_show
    add esp, 4
%endmacro

%macro rad_hide 1
    RADPUSH %1
    call _rad_hide
    add esp, 4
%endmacro

%macro rad_print 1
    RADPUSH %1
    call _rad_print
    add esp, 4
%endmacro

%macro rad_end 0
    call _rad_end
%endmacro

%macro rad_arg 1
    RADPUSH %1
    call _rad_arg
    add esp, 4
%endmacro

%macro rad_str_int 1
    RADLOAD %1
    cdq
    push edx
    push eax
    call _rad_str_int
    add esp, 8
%endmacro

%macro rad_int_str 1
    RADPUSH %1
    call _rad_int_str
    add esp, 4
%endmacro

%macro radcall 2
    RADPUSH %2
    RADPUSH %1
    call _radcall
    add esp, 8
%endmacro

%endif
