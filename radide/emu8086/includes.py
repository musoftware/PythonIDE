"""Built-in include files of the 8086 emulator.

``include 'emu8086.inc'`` is common in course material. When the file is not in the project folder the
emulator supplies this library, written for RAD IDE, offering the same macro and procedure names courses use:

    PUTC char            print one character            GOTOXY col, row    move the cursor
    PRINT 'text'         print text                     PRINTN 'text'      print text + new line
    CURSOROFF / CURSORON hide / show the cursor

and procedures you add to the program with a DEFINE_ macro (put them after the code, before END):

    DEFINE_PRINT_NUM      CALL PRINT_NUM       print AX as a signed number
    DEFINE_PRINT_NUM_UNS  CALL PRINT_NUM_UNS   print AX as an unsigned number
    DEFINE_SCAN_NUM       CALL SCAN_NUM        read a signed number from the keyboard into CX
    DEFINE_PRINT_STRING   CALL PRINT_STRING    print the 0-terminated string at DS:SI
    DEFINE_GET_STRING     CALL GET_STRING      read a line into DS:DI (DX = buffer size), 0-terminated
    DEFINE_CLEAR_SCREEN   CALL CLEAR_SCREEN    clear the screen, cursor to the top
    DEFINE_PTHIS          CALL PTHIS / db 'text', 0   print the text that follows the CALL
"""
from __future__ import annotations

RAD8086_INC = r"""
; ---- RAD IDE 8086 helper library (compatible names) ----
PUTC    MACRO   char
        PUSH    AX
        MOV     AL, char
        MOV     AH, 0Eh
        INT     10h
        POP     AX
ENDM

GOTOXY  MACRO   col, row
        PUSH    AX
        PUSH    BX
        PUSH    DX
        MOV     AH, 02h
        MOV     DH, row
        MOV     DL, col
        MOV     BH, 0
        INT     10h
        POP     DX
        POP     BX
        POP     AX
ENDM

PRINT   MACRO   sdat
        LOCAL   next_char, s_dcl, printed, skip_dcl
        PUSH    AX
        PUSH    SI
        JMP     skip_dcl
        s_dcl DB sdat, 0
skip_dcl:
        LEA     SI, s_dcl
next_char:
        MOV     AL, CS:[SI]
        CMP     AL, 0
        JZ      printed
        INC     SI
        MOV     AH, 0Eh
        INT     10h
        JMP     next_char
printed:
        POP     SI
        POP     AX
ENDM

PRINTN  MACRO   sdat
        PRINT   sdat
        PUTC    13
        PUTC    10
ENDM

CURSOROFF MACRO
        PUSH    AX
        PUSH    CX
        MOV     AH, 1
        MOV     CH, 28h
        MOV     CL, 09h
        INT     10h
        POP     CX
        POP     AX
ENDM

CURSORON MACRO
        PUSH    AX
        PUSH    CX
        MOV     AH, 1
        MOV     CH, 06h
        MOV     CL, 07h
        INT     10h
        POP     CX
        POP     AX
ENDM

DEFINE_PRINT_NUM_UNS MACRO
        LOCAL   divide, emit, done_uns
PRINT_NUM_UNS PROC NEAR
        PUSH    AX
        PUSH    BX
        PUSH    CX
        PUSH    DX
        MOV     BX, 10
        XOR     CX, CX
divide:
        XOR     DX, DX
        DIV     BX
        PUSH    DX
        INC     CX
        OR      AX, AX
        JNZ     divide
emit:
        POP     AX
        ADD     AL, '0'
        MOV     AH, 0Eh
        INT     10h
        LOOP    emit
done_uns:
        POP     DX
        POP     CX
        POP     BX
        POP     AX
        RET
PRINT_NUM_UNS ENDP
ENDM

DEFINE_PRINT_NUM MACRO
        LOCAL   positive
PRINT_NUM PROC NEAR
        PUSH    AX
        OR      AX, AX
        JNS     positive
        PUSH    AX
        MOV     AL, '-'
        MOV     AH, 0Eh
        INT     10h
        POP     AX
        NEG     AX
positive:
        CALL    PRINT_NUM_UNS
        POP     AX
        RET
PRINT_NUM ENDP
ENDM

DEFINE_SCAN_NUM MACRO
        LOCAL   next_key, not_minus, digit, backspace, finish, sign_ok, neg_flag
SCAN_NUM PROC NEAR
        PUSH    AX
        PUSH    BX
        PUSH    DX
        PUSH    SI
        XOR     CX, CX
        XOR     SI, SI              ; SI = 1 when the number is negative
next_key:
        MOV     AH, 0
        INT     16h
        CMP     AL, 13
        JE      finish
        CMP     AL, 8
        JE      backspace
        CMP     AL, '-'
        JNE     not_minus
        OR      CX, CX
        JNZ     next_key
        CMP     SI, 0
        JNE     next_key
        MOV     SI, 1
        MOV     AH, 0Eh
        INT     10h
        JMP     next_key
not_minus:
        CMP     AL, '0'
        JB      next_key
        CMP     AL, '9'
        JA      next_key
digit:
        MOV     AH, 0Eh
        INT     10h
        SUB     AL, '0'
        MOV     BL, AL
        MOV     BH, 0
        MOV     AX, CX
        MOV     DX, 10
        MUL     DX
        ADD     AX, BX
        MOV     CX, AX
        JMP     next_key
backspace:
        MOV     AX, CX
        XOR     DX, DX
        MOV     BX, 10
        DIV     BX
        MOV     CX, AX
        MOV     AL, 8
        MOV     AH, 0Eh
        INT     10h
        MOV     AL, ' '
        INT     10h
        MOV     AL, 8
        INT     10h
        JMP     next_key
finish:
        CMP     SI, 0
        JE      sign_ok
neg_flag:
        NEG     CX
sign_ok:
        MOV     AL, 13
        MOV     AH, 0Eh
        INT     10h
        MOV     AL, 10
        INT     10h
        POP     SI
        POP     DX
        POP     BX
        POP     AX
        RET
SCAN_NUM ENDP
ENDM

DEFINE_PRINT_STRING MACRO
        LOCAL   next_ch, done_str
PRINT_STRING PROC NEAR
        PUSH    AX
        PUSH    SI
next_ch:
        MOV     AL, [SI]
        CMP     AL, 0
        JZ      done_str
        INC     SI
        MOV     AH, 0Eh
        INT     10h
        JMP     next_ch
done_str:
        POP     SI
        POP     AX
        RET
PRINT_STRING ENDP
ENDM

DEFINE_GET_STRING MACRO
        LOCAL   wait_key, back, stored, done_get
GET_STRING PROC NEAR
        PUSH    AX
        PUSH    CX
        PUSH    DI
        PUSH    DX
        XOR     CX, CX
        CMP     DX, 1
        JBE     done_get
        DEC     DX
wait_key:
        MOV     AH, 0
        INT     16h
        CMP     AL, 13
        JE      done_get
        CMP     AL, 8
        JE      back
        CMP     CX, DX
        JAE     wait_key
        MOV     [DI], AL
        INC     DI
        INC     CX
        MOV     AH, 0Eh
        INT     10h
        JMP     wait_key
back:
        JCXZ    wait_key
        DEC     DI
        DEC     CX
        MOV     AH, 0Eh
        MOV     AL, 8
        INT     10h
        MOV     AL, ' '
        INT     10h
        MOV     AL, 8
        INT     10h
        JMP     wait_key
done_get:
        MOV     BYTE PTR [DI], 0
stored:
        MOV     AH, 0Eh
        MOV     AL, 13
        INT     10h
        MOV     AL, 10
        INT     10h
        POP     DX
        POP     DI
        POP     CX
        POP     AX
        RET
GET_STRING ENDP
ENDM

DEFINE_CLEAR_SCREEN MACRO
CLEAR_SCREEN PROC NEAR
        PUSH    AX
        PUSH    BX
        PUSH    CX
        PUSH    DX
        MOV     AX, 0600h
        MOV     BH, 07h
        MOV     CX, 0
        MOV     DX, 184Fh
        INT     10h
        MOV     AH, 02h
        MOV     BH, 0
        MOV     DX, 0
        INT     10h
        POP     DX
        POP     CX
        POP     BX
        POP     AX
        RET
CLEAR_SCREEN ENDP
ENDM

DEFINE_PTHIS MACRO
        LOCAL   next_p, done_p
PTHIS PROC NEAR
        POP     SI                  ; the text follows the CALL
        PUSH    AX
next_p:
        MOV     AL, CS:[SI]
        INC     SI
        CMP     AL, 0
        JZ      done_p
        MOV     AH, 0Eh
        INT     10h
        JMP     next_p
done_p:
        POP     AX
        PUSH    SI
        RET
PTHIS ENDP
ENDM
"""

BUILTIN = {"emu8086.inc": RAD8086_INC, "rad8086.inc": RAD8086_INC}


def builtin_include(name: str) -> str | None:
    key = name.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return BUILTIN.get(key)
