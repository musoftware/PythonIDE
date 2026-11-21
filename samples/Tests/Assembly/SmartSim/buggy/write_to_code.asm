; Bug: 'counter' is defined in the code section, which is read-only.
default rel
global main

section .text
counter dd 0
main:
    sub rsp, 40
    inc dword [counter]         ; EXPECT: sim.write_readonly
    add rsp, 40
    ret
