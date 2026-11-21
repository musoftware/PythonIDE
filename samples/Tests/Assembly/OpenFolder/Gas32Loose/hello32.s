# Gas32Loose - a loose 32-bit GNU as program (AT&T syntax). RAD IDE assembles it with as --32 and links it with
# GNU ld -m i386pe against msvcrt.dll from SysWOW64.
        .code32
        .data
fmt:    .asciz "GNU as 32-bit loose folder: %d\n"
        .text
        .globl _main
_main:
        movl    $2000, %eax
        addl    $26, %eax
        pushl   %eax
        pushl   $fmt
        call    _printf
        addl    $8, %esp
        xorl    %eax, %eax
        ret
