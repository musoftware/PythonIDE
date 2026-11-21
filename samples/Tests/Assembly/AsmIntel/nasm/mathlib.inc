; mathlib.inc - small NASM macro library used by main.asm (RAD IDE IntelliSense test).

%ifndef MATHLIB_INC
%define MATHLIB_INC

%define MAX_COUNT 100

; SQUARE dest, src : dest = src * src
%macro SQUARE 2
    mov     %1, %2
    imul    %1, %2
%endmacro

; CLAMP reg, low, high : keeps reg inside [low, high]
%macro CLAMP 3
    cmp     %1, %2
    jge     %%above
    mov     %1, %2
%%above:
    cmp     %1, %3
    jle     %%done
    mov     %1, %3
%%done:
%endmacro

%endif
