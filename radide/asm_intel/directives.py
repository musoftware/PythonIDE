"""Assembler directives, pseudo-instructions and macro keywords per dialect (NASM, MASM, FASM, GAS).

Descriptions are original short summaries; the hovers link to each assembler's official manual (DOC_URLS).
Format: ``name | description`` per line; names are matched without case (GAS directives too).
"""
from __future__ import annotations

DOC_URLS = {
    "nasm": "https://www.nasm.us/docs.php",
    "masm": "https://learn.microsoft.com/en-us/cpp/assembler/masm/microsoft-macro-assembler-reference",
    "fasm": "https://flatassembler.net/docs.php",
    "gas": "https://sourceware.org/binutils/docs/as/",
}
DIALECT_NAMES = {"nasm": "NASM", "masm": "MASM", "fasm": "FASM", "gas": "GNU as (GAS)"}

_DATA_COMMON = """
db|Define bytes: numbers, characters or strings ("Hello", 13, 10, 0).
dw|Define 16-bit words.
dd|Define 32-bit dwords (also single-precision floats: dd 1.5).
dq|Define 64-bit qwords (also double-precision floats).
dt|Define 80-bit values (x87 extended floats / packed BCD).
equ|Give a name to a constant value: NAME equ 10.
"""

NASM = _DATA_COMMON + """
do|Define 128-bit octowords.
dy|Define 256-bit values.
dz|Define 512-bit values.
resb|Reserve uninitialised bytes (in section .bss): buffer resb 256.
resw|Reserve uninitialised words.
resd|Reserve uninitialised dwords.
resq|Reserve uninitialised qwords.
rest|Reserve uninitialised 80-bit values.
reso|Reserve uninitialised 128-bit values.
resy|Reserve uninitialised 256-bit values.
resz|Reserve uninitialised 512-bit values.
times|Repeat an instruction or data N times: times 64 db 0.
incbin|Include a binary file verbatim.
section|Switch to a section: .text (code), .data (initialised data), .bss (reserved space), .rdata (read-only).
segment|Same as SECTION.
bits|Select 16, 32 or 64-bit code generation: bits 64.
use16|Same as BITS 16.
use32|Same as BITS 32.
use64|Same as BITS 64.
default|default rel makes [label] RIP-relative in 64-bit code (recommended for Win64 / PIE).
global|Export a symbol to the linker (global main / global _start).
extern|Import a symbol defined elsewhere (a DLL function or C runtime function): extern MessageBoxA.
common|Declare a common (shared, uninitialised) variable.
static|Make a symbol local to the object file (debug info).
align|Pad with NOPs (code) until the address is a multiple of N.
alignb|Pad with reserved space (bss) until aligned.
org|Origin address for flat binary output (org 100h for DOS .COM files).
absolute|Start an absolute (unallocated) section for defining offsets.
struc|Begin a structure definition (field offsets): struc POINT / .x resd 1 / .y resd 1 / endstruc.
endstruc|End a STRUC definition (defines NAME_size).
istruc|Begin an initialised instance of a structure.
at|Set a field inside ISTRUC: at POINT.x, dd 5.
iend|End an ISTRUC instance.
cpu|Restrict the instruction set: cpu 686, cpu x64.
float|Control floating-point constant behaviour (daz, nodaz, near, up, down, zero).
rel|RIP-relative address: [rel msg].
abs|Absolute address (opposite of REL).
wrt|With respect to: a segment or a relocation type (wrt ..plt, wrt ..got).
strict|Force the operand size the source says (no optimisation).
seg|The segment base of a symbol (16-bit code).
byte|8-bit operand size: mov byte [rdi], 0.
word|16-bit operand size.
dword|32-bit operand size.
qword|64-bit operand size.
tword|80-bit operand size.
oword|128-bit operand size.
yword|256-bit operand size.
zword|512-bit operand size.
%define|Single-line macro: %define BUFSIZE 256 (case-sensitive; %idefine ignores case).
%idefine|Case-insensitive single-line macro.
%xdefine|Single-line macro expanded at definition time.
%undef|Remove a single-line macro.
%assign|Numeric single-line macro that can be redefined: %assign i i+1.
%strlen|Length of a string into a macro.
%substr|Part of a string into a macro.
%macro|Begin a multi-line macro: %macro name nparams ... %endmacro; parameters are %1, %2 ...
%imacro|Case-insensitive multi-line macro.
%endmacro|End a %macro definition.
%rotate|Rotate the macro parameters (loops over variable arguments).
%rep|Repeat a block: %rep 8 ... %endrep.
%endrep|End a %rep block.
%exitrep|Leave a %rep block early.
%if|Conditional assembly on an expression.
%ifdef|Assemble if a macro is defined.
%ifndef|Assemble if a macro is not defined.
%ifidn|Assemble if two texts are identical.
%ifidni|Assemble if two texts are identical (ignoring case).
%ifnum|Assemble if the text is a number.
%ifstr|Assemble if the text is a string.
%ifmacro|Assemble if a multi-line macro exists.
%elif|Else-if branch of %if.
%else|Else branch of %if.
%endif|End a %if block.
%include|Include another source file: %include "macros.inc".
%use|Include a standard macro package (%use altreg, %use smartalign).
%error|Stop assembly with an error message.
%warning|Print a warning.
%fatal|Stop immediately with an error.
%local|Declare local stack variables (with %stacksize).
%stacksize|Set the stack model for %arg / %local (flat, flat64, large, small).
%arg|Declare stack arguments of a procedure.
%push|Push a context on the preprocessor context stack (block macros).
%pop|Pop the preprocessor context.
%repl|Rename the current context.
%line|Set the source line number for error messages.
%pragma|Pass an option to the assembler or output format.
__?FILE?__|Name of the current source file.
__?LINE?__|Current line number.
__?BITS?__|Current BITS mode.
"""

MASM = _DATA_COMMON + """
byte|8-bit unsigned data / size: msg BYTE "Hi", 0 / byte ptr [rsi].
sbyte|8-bit signed data.
word|16-bit unsigned data / size.
sword|16-bit signed data.
dword|32-bit unsigned data / size.
sdword|32-bit signed data.
fword|48-bit data (far pointer).
qword|64-bit data / size.
sqword|64-bit signed data.
tbyte|80-bit data.
oword|128-bit data.
real4|Single-precision float data.
real8|Double-precision float data.
real10|80-bit extended float data.
xmmword|128-bit operand size.
ymmword|256-bit operand size.
ptr|Operand size override: dword ptr [ebx].
offset|Address of a label (32-bit: mov esi, offset msg).
addr|Address of a variable as an INVOKE argument (works for locals too).
sizeof|Size in bytes of a variable or type.
lengthof|Number of elements of an array variable.
type|Size of one element / of a type.
dup|Repeat initialisers: buffer BYTE 256 DUP(0) / DUP(?).
.model|Memory model and default calling convention (32-bit): .model flat, stdcall.
.code|Begin the code segment.
.data|Begin the initialised data segment.
.data?|Begin the uninitialised data segment.
.const|Begin the read-only data segment.
.stack|Set the stack size (16 / 32-bit).
.386|Enable 80386 instructions.
.486|Enable 80486 instructions.
.586|Enable Pentium instructions.
.686|Enable Pentium Pro instructions.
.686p|Enable Pentium Pro instructions including privileged ones.
.mmx|Enable MMX instructions.
.xmm|Enable SSE instructions.
proc|Begin a procedure: name PROC [USES regs] [args]; ends with name ENDP.
endp|End a procedure: name ENDP.
proto|Declare a procedure prototype so INVOKE can check arguments: MessageBoxA PROTO :DWORD, :DWORD, :DWORD, :DWORD.
invoke|Call a procedure with arguments pushed for its calling convention (32-bit MASM; not in ml64).
uses|Registers a PROC saves and restores automatically.
local|Declare local variables in a PROC (or local labels in a MACRO).
frame|Mark a PROC as having unwind data (ml64): name PROC FRAME.
.pushreg|Unwind info: a register was pushed (ml64 prologue).
.allocstack|Unwind info: stack space was allocated (ml64 prologue).
.setframe|Unwind info: a frame pointer was set.
.savereg|Unwind info: a register was saved to the stack.
.endprolog|End of the prologue (ml64 unwind info).
macro|Begin a macro: name MACRO params ... ENDM.
endm|End a MACRO, REPT, IRP or WHILE block.
exitm|Leave a macro early (optionally returning a value).
textequ|Text macro: name TEXTEQU <text>.
struct|Begin a structure: name STRUCT ... name ENDS.
struc|Same as STRUCT.
union|Begin a union.
ends|End a STRUCT, UNION or SEGMENT.
record|Bit-field record type.
typedef|Define a type alias: PCHAR TYPEDEF PTR BYTE.
include|Include a source file: include windows.inc.
includelib|Ask the linker to use a library: includelib kernel32.lib.
extern|Declare an external symbol: EXTERN ExitProcess:PROC.
extrn|Same as EXTERN.
externdef|Declare a symbol external or public as needed.
public|Export a symbol to the linker.
option|Set assembler options: option casemap:none.
end|End of the source file (32-bit: END start names the entry point).
assume|Tell the assembler what a segment register or register points to.
segment|Begin a named segment (16-bit / advanced code).
align|Align the next data or code.
even|Align to an even address.
org|Set the location counter.
.if|High-level IF (compiled to CMP + Jcc).
.elseif|High-level ELSEIF.
.else|High-level ELSE.
.endif|End of .IF.
.while|High-level WHILE loop.
.endw|End of .WHILE.
.repeat|High-level REPEAT loop.
.until|End of .REPEAT with its condition.
.break|Leave the current .WHILE / .REPEAT loop.
.continue|Jump to the loop condition.
rept|Repeat a block N times.
irp|Repeat a block for each item of a list.
irpc|Repeat a block for each character.
if|Conditional assembly.
ifdef|Assemble if a symbol is defined.
ifndef|Assemble if a symbol is not defined.
elseif|Else-if branch of conditional assembly.
else|Else branch of conditional assembly.
endif|End of conditional assembly.
echo|Print a message while assembling.
comment|Block comment: COMMENT ! ... !
high|High byte of an expression.
low|Low byte of an expression.
"""

FASM = """
db|Define bytes / strings.
dw|Define words.
du|Define words from a string (UTF-16 text).
dd|Define dwords (also floats).
dp|Define 48-bit pointers.
df|Define 48-bit pointers (same as DP).
dq|Define qwords.
dt|Define 80-bit values.
rb|Reserve bytes.
rw|Reserve words.
rd|Reserve dwords.
rp|Reserve 48-bit values.
rf|Reserve 48-bit values.
rq|Reserve qwords.
rt|Reserve 80-bit values.
file|Include a binary file verbatim.
equ|Symbolic constant (text replacement): name equ value.
format|Output format: format PE GUI 4.0 / format PE64 console / format ELF64 executable / format MZ.
entry|Entry point of the program: entry start.
section|PE / ELF section: section '.text' code readable executable.
segment|ELF executable segment: segment readable executable.
code|Section flag: contains code.
data|Section flag: contains data (data import / data export / data fixups).
readable|Section flag: readable.
writeable|Section flag: writeable.
executable|Section flag: executable.
import|Import functions of a DLL (with the import macros): import kernel32, ExitProcess, 'ExitProcess'.
library|List the DLLs used by IMPORT: library kernel32, 'KERNEL32.DLL', user32, 'USER32.DLL'.
export|Export functions from a DLL.
include|Include a source file: include 'win32a.inc' (FASM's Windows headers and macros).
use16|Generate 16-bit code.
use32|Generate 32-bit code.
use64|Generate 64-bit code.
org|Set the origin address.
align|Align the current address.
virtual|Assemble into a virtual block (no output) - for computing offsets.
load|Read a value from already assembled code.
store|Overwrite already assembled code.
times|Repeat an instruction: times 16 nop.
repeat|Repeat a block N times (counter %): repeat 4 ... end repeat.
while|Assembly-time loop while a condition is true.
if|Conditional assembly: if defined name ... else ... end if.
else|Else branch of IF.
end|Close a block: end if / end repeat / end while / end virtual.
break|Leave a repeat / while block.
macro|Define a macro: macro name arg1, arg2 { ... }.
struc|Define a structure macro: struc POINT { .x dd ? .y dd ? }.
struct|Structure (macro package): struct POINT ... ends.
ends|End a STRUCT (macro package).
proc|Procedure with arguments (macro package): proc WindowProc hwnd, wmsg, wparam, lparam ... endp.
endp|End of a PROC.
local|Local variables of a PROC or local labels of a macro.
locals|Begin a block of local variables in a PROC.
endl|End a LOCALS block.
invoke|Call an imported function with arguments (stdcall, through the import table): invoke MessageBox, 0, msg, title, MB_OK.
stdcall|Call a procedure with stdcall arguments.
ccall|Call a procedure with cdecl arguments (caller cleans the stack).
cinvoke|Call an imported cdecl function (printf ...).
fastcall|Call with the Microsoft x64 convention (64-bit macro package).
rept|Repeat a block with a counter: rept 4 i { db i }.
irp|Repeat a block for each value: irp reg, eax, ebx { push reg }.
irps|Repeat a block for each symbol.
match|Pattern-match macro arguments.
define|Symbolic constant (like EQU, but always text).
fix|Constant applied before macro processing.
restore|Undefine the last value of a symbolic constant.
purge|Remove the last definition of a macro.
label|Define a label with a size: label buffer byte.
byte|8-bit operand size.
word|16-bit operand size.
dword|32-bit operand size.
fword|48-bit operand size.
pword|48-bit operand size.
qword|64-bit operand size.
tword|80-bit operand size.
dqword|128-bit operand size.
xword|128-bit operand size.
yword|256-bit operand size.
ptr|Optional size keyword for compatibility.
rva|Relative virtual address of a label (PE).
defined|Test whether a symbol is defined (in IF).
used|Test whether a symbol is used (in IF).
"""

GAS = """
.text|Switch to the code section.
.data|Switch to the initialised data section.
.bss|Switch to the uninitialised data section.
.section|Switch to a named section: .section .rodata / .section .rdata,"dr".
.globl|Export a symbol: .globl main.
.global|Export a symbol (same as .globl).
.extern|Declare an external symbol (GAS treats undefined symbols as external anyway).
.byte|Define bytes.
.short|Define 16-bit values.
.word|Define 16-bit values on x86.
.hword|Define 16-bit values.
.long|Define 32-bit values.
.int|Define 32-bit values.
.quad|Define 64-bit values.
.octa|Define 128-bit values.
.float|Define single-precision floats.
.single|Define single-precision floats.
.double|Define double-precision floats.
.ascii|Define a string without a terminating zero.
.asciz|Define a zero-terminated string.
.string|Define a zero-terminated string.
.space|Reserve (and fill) N bytes.
.skip|Same as .space.
.zero|Reserve N zero bytes.
.fill|Repeat a value: .fill count, size, value.
.align|Align the location counter (meaning depends on the target; prefer .balign / .p2align).
.balign|Align to a multiple of N bytes.
.p2align|Align to a power of two: .p2align 4 = 16 bytes.
.equ|Constant: .equ NAME, value.
.set|Constant that can be redefined: .set NAME, value.
.equiv|Constant; error if already defined.
.macro|Begin a macro: .macro name arg1, arg2 ... .endm (arguments used as \\arg1).
.endm|End a .macro.
.exitm|Leave a macro early.
.rept|Repeat a block N times.
.irp|Repeat a block for each value.
.irpc|Repeat a block for each character.
.endr|End a .rept / .irp block.
.if|Conditional assembly.
.ifdef|Assemble if a symbol is defined.
.ifndef|Assemble if a symbol is not defined.
.else|Else branch.
.elseif|Else-if branch.
.endif|End of conditional assembly.
.include|Include another source file.
.incbin|Include a binary file.
.type|Symbol type for ELF: .type main, @function.
.size|Symbol size for ELF: .size main, .-main.
.file|Source file name (debug info).
.loc|Source line (debug info).
.def|Begin a COFF symbol definition (Windows).
.endef|End a COFF symbol definition.
.scl|COFF storage class.
.ident|Add an identification string.
.comm|Common symbol: .comm name, size.
.lcomm|Local common symbol (reserved in .bss).
.local|Make a symbol local.
.weak|Weak symbol.
.hidden|Hidden visibility (ELF).
.org|Set the location counter.
.end|End of the source file.
.intel_syntax|Switch to Intel operand order (.intel_syntax noprefix: no % on registers).
.att_syntax|Switch back to AT&T syntax (source first, destination last, % registers, $ immediates).
noprefix|With .intel_syntax: registers are written without %.
.code16|Generate 16-bit code.
.code32|Generate 32-bit code.
.code64|Generate 64-bit code.
.arch|Restrict the instruction set.
.cfi_startproc|Begin unwind (call frame) information for a function.
.cfi_endproc|End unwind information.
.cfi_def_cfa_offset|Unwind info: the frame address is now N bytes above the stack pointer.
.cfi_offset|Unwind info: a register was saved at an offset.
.seh_proc|Begin Windows x64 unwind info for a function (MinGW).
.seh_endprologue|End of the prologue (Windows unwind info).
.seh_endproc|End of the function's Windows unwind info.
.seh_pushreg|Windows unwind info: a register was pushed.
.seh_stackalloc|Windows unwind info: stack space was allocated.
"""

PSEUDO_INSTR = {"db", "dw", "dd", "dq", "dt", "do", "dy", "dz", "resb", "resw", "resd", "resq", "rest", "reso",
                "resy", "resz", "rb", "rw", "rd", "rq", "rt", "rp", "rf", "du", "dp", "df", "byte", "sbyte", "word",
                "sword", "dword", "sdword", "qword", "sqword", "fword", "tbyte", "oword", "real4", "real8", "real10"}


def _parse(text: str) -> dict[str, str]:
    out = {}
    for line in text.strip().splitlines():
        if "|" in line:
            k, v = line.split("|", 1)
            out[k.strip().lower()] = v.strip()
    return out


DIRECTIVES: dict[str, dict[str, str]] = {"nasm": _parse(NASM), "masm": _parse(MASM), "fasm": _parse(FASM),
                                         "gas": _parse(GAS)}


def directive(word: str, dialect: str) -> tuple[str, str] | None:
    """(description, dialect) of a directive / keyword; the current dialect first, then the others."""
    w = word.lower()
    d = DIRECTIVES.get(dialect, {})
    if w in d:
        return d[w], dialect
    return None


def directive_names(dialect: str) -> list[str]:
    return list(DIRECTIVES.get(dialect, {}))
