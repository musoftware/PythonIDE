; Bug: 'mov rcx, [msg]' loads the first 8 characters of the string, not its address.
default rel
global main
extern puts

section .data
    msg db "Hello!", 0

section .text
main:
    sub rsp, 40
    mov rcx, [msg]              ; should be: lea rcx, [msg]
    call puts                   ; EXPECT: sim.bad_pointer_arg
    xor eax, eax
    add rsp, 40
    ret
