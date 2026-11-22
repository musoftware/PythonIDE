; (c) 2026 Musoftware - https://musoftwares.com - MIT License
;
; FasmTemperature - Form1 event handlers (FASM, x64 Windows, GUI Bridge).
; Converts whole degrees between Celsius and Fahrenheit with integer arithmetic (IMUL / IDIV with rounding),
; describes the temperature (a chain of CMP / Jcc), and moves a ProgressBar (rad_set_int ... 'Value').
; The result text is formatted with the C runtime's sprintf (the object is linked by gcc).
;
; Inside a handler RBX, RSI, RDI and R12 are ours (saved by the handler macro); RSP is aligned with shadow space.
include 'radgui_fasm.inc'       ; first: format MS64 COFF + the macros + section '.text'
include 'Form1.inc'            ; generated: the control names of Form1 (txtValue, lblOut, barHeat ...)

extrn sprintf

; div_round: RAX / RCX rounded to the nearest whole number (halves away from zero) -> RAX
div_round:
    mov r8, rcx
    shr r8, 1                       ; half of the divisor (divisor > 0)
    test rax, rax
    js .negative
    add rax, r8
    cqo
    idiv rcx
    ret
.negative:
    sub rax, r8
    cqo
    idiv rcx
    ret

; describe: RSI = degrees Celsius -> label lblFeel + progress bar barHeat (-40 C .. 120 C = 0 .. 100 %)
; (FASM: the rad_* macros define labels, so the jump targets below are global names)
describe:
    sub rsp, 8
    cmp rsi, 0
    jl describe_freezing
    cmp rsi, 15
    jl describe_cold
    cmp rsi, 25
    jl describe_mild
    cmp rsi, 35
    jl describe_warm
    rad_set lblFeel, 'Text', 'Hot - drink some water!'
    jmp describe_bar
describe_freezing:
    rad_set lblFeel, 'Text', 'Freezing - water turns to ice.'
    jmp describe_bar
describe_cold:
    rad_set lblFeel, 'Text', 'Cold - take a jacket.'
    jmp describe_bar
describe_mild:
    rad_set lblFeel, 'Text', 'Mild - a pleasant day.'
    jmp describe_bar
describe_warm:
    rad_set lblFeel, 'Text', 'Warm.'
describe_bar:
    mov rax, rsi                    ; percent = (C + 40) * 100 / 160, clamped to 0 .. 100
    add rax, 40
    imul rax, 100
    mov rcx, 160
    cqo
    idiv rcx
    cmp rax, 0
    jge describe_not_low
    xor eax, eax
describe_not_low:
    cmp rax, 100
    jle describe_not_high
    mov eax, 100
describe_not_high:
    mov rbx, rax
    rad_set_int barHeat, 'Value', rbx
    add rsp, 8
    ret

handler Form1_Load
    rad_set lblOut, 'Text', 'Type a temperature and choose a direction.'
    rad_set_int barHeat, 'Value', 0
endhandler

handler btnToF_Click
    rad_get_int txtValue, 'Text'    ; RAX = degrees Celsius
    mov rsi, rax
    imul rax, 9                     ; F = C * 9 / 5 + 32
    mov rcx, 5
    call div_round
    add rax, 32
    mov rdi, rax
    lea rcx, [buf]
    lea rdx, [fmt_c2f]
    mov r8, rsi
    mov r9, rdi
    call sprintf
    rad_set lblOut, 'Text', buf
    call describe                   ; RSI = Celsius
endhandler

handler btnToC_Click
    rad_get_int txtValue, 'Text'    ; RAX = degrees Fahrenheit
    mov rdi, rax
    sub rax, 32                     ; C = (F - 32) * 5 / 9
    imul rax, 5
    mov rcx, 9
    call div_round
    mov rsi, rax
    lea rcx, [buf]
    lea rdx, [fmt_f2c]
    mov r8, rdi
    mov r9, rsi
    call sprintf
    rad_set lblOut, 'Text', buf
    call describe
endhandler

section '.data' data readable writeable
    fmt_c2f     db '%lld C = %lld F', 0
    fmt_f2c     db '%lld F = %lld C', 0
    buf         rb 96
