; Hello.asm - main file of the WinAsm Studio project Hello.wap (MASM 32-bit; needs ml.exe from Visual Studio).
.386
.model flat, stdcall
option casemap:none

ExitProcess PROTO :DWORD
MessageBoxA PROTO :DWORD, :DWORD, :DWORD, :DWORD
includelib kernel32.lib
includelib user32.lib

.data
caption db "WinAsm", 0
text    db "WinAsm Studio project opened in place", 0

.code
start:
    invoke MessageBoxA, 0, addr text, addr caption, 0
    invoke ExitProcess, 0
end start
