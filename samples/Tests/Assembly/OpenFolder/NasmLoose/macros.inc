; macros.inc - included by hello.asm (an include file is not a program: no run target)
%macro TIMES7 1
    imul %1, %1, 7
%endmacro
