"""x86 / x86-64 instruction and register tables for the assembly IntelliSense (no Qt here).

Every description below is original text written for RAD IDE (short summaries, not copied from any
manual). The authoritative reference is the Intel 64 and IA-32 Architectures Software Developer's
Manual (SDM_URL); hovers link to it.

Table format (one instruction per line):  ``mnemonic | category | flags | operand forms | description``

* flags: ``w:`` written (set from the result), ``r:`` read (tested), ``u:`` left undefined, ``0:`` cleared,
  ``1:`` set; ``-`` = no flags change.  Example: ``r:CF w:OF SF ZF AF PF CF``
* operand forms: alternatives separated by ``;`` (``r/m`` = register or memory, ``imm`` = immediate,
  ``xmm/m128`` = XMM register or 128-bit memory, ``rel`` = code label)
"""
from __future__ import annotations

from dataclasses import dataclass, field

SDM_URL = "https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html"
AMD_URL = "https://www.amd.com/en/search/documentation/hub.html"


@dataclass
class Instr:
    name: str
    category: str
    flags: str
    forms: list[str]
    doc: str
    alias_of: str = ""
    bits: str = ""                      # "16/32" = not encodable in 64-bit mode


@dataclass
class Register:
    name: str
    size: int                            # bits
    doc: str
    family: str = ""                     # rax for eax/ax/al/ah ...
    parts: list[str] = field(default_factory=list)


CATEGORY_TITLES = {
    "data": "Data transfer", "arith": "Integer arithmetic", "logic": "Logic", "shift": "Shift / rotate",
    "bit": "Bit manipulation", "control": "Control transfer", "cond": "Conditional", "string": "String",
    "flags": "Flag control", "stack": "Stack", "system": "System", "io": "Port I/O", "conv": "Conversion",
    "misc": "Miscellaneous", "prefix": "Prefix", "bcd": "BCD arithmetic (16/32-bit only)", "x87": "x87 FPU",
    "mmx": "MMX", "sse": "SSE", "sse2": "SSE2", "sse3": "SSE3", "ssse3": "SSSE3", "sse41": "SSE4.1",
    "sse42": "SSE4.2", "aes": "AES-NI / CLMUL", "avx": "AVX", "avx2": "AVX2", "fma": "FMA3", "bmi": "BMI1 / BMI2",
    "sync": "Memory ordering / cache",
}

_ARITH = "w:OF SF ZF AF PF CF"
_LOGIC = "0:OF CF w:SF ZF PF u:AF"
_TABLE = r"""
mov|data|-|r/m, r; r, r/m; r/m, imm; r64, imm64; sreg, r/m16|Copy the source operand into the destination. Memory-to-memory moves are not allowed.
movzx|data|-|r16/32/64, r/m8; r32/64, r/m16|Copy a smaller value into a bigger register and fill the upper bits with zeros (unsigned widening).
movsx|data|-|r16/32/64, r/m8; r32/64, r/m16|Copy a smaller value into a bigger register, repeating its sign bit (signed widening).
movsxd|data|-|r64, r/m32|Sign-extend a 32-bit value into a 64-bit register (64-bit mode).
lea|data|-|r, m|Load the computed address of the memory operand (not its contents). Often used for fast arithmetic: lea eax, [ebx+ebx*4].
xchg|data|-|r/m, r; r, r/m|Swap the two operands. With a memory operand the CPU locks the bus automatically (atomic).
cmpxchg|sync|w:OF SF ZF AF PF CF|r/m, r|Compare AL/AX/EAX/RAX with the destination; if equal store the source there (ZF=1), else load the destination into the accumulator (ZF=0). Use with LOCK for atomic compare-and-swap.
cmpxchg8b|sync|w:ZF|m64|Compare EDX:EAX with the 8-byte memory operand; if equal store ECX:EBX there, else load it into EDX:EAX.
cmpxchg16b|sync|w:ZF|m128|Compare RDX:RAX with the 16-byte (16-aligned) memory operand; if equal store RCX:RBX there, else load it into RDX:RAX.
xadd|sync|w:OF SF ZF AF PF CF|r/m, r|Exchange the operands, then store their sum in the destination. With LOCK: atomic fetch-and-add.
push|stack|-|r/m16/32/64; imm; sreg|Decrement the stack pointer by the operand size and store the operand at [esp]/[rsp]. In 64-bit mode pushes are 8 bytes.
pop|stack|-|r/m16/32/64; sreg|Load the value at the top of the stack into the operand, then increase the stack pointer.
pusha|stack|-|(none)|Push all 16-bit general registers (AX CX DX BX SP BP SI DI).|bits=16/32
pushad|stack|-|(none)|Push all 32-bit general registers (EAX ECX EDX EBX ESP EBP ESI EDI). Not available in 64-bit mode.|bits=16/32
popa|stack|-|(none)|Pop the 16-bit general registers pushed by PUSHA (SP is skipped).|bits=16/32
popad|stack|-|(none)|Pop the 32-bit general registers pushed by PUSHAD (ESP is skipped). Not available in 64-bit mode.|bits=16/32
pushf|stack|-|(none)|Push the 16-bit FLAGS register.
pushfd|stack|-|(none)|Push the 32-bit EFLAGS register.|bits=16/32
pushfq|stack|-|(none)|Push RFLAGS (64-bit mode).
popf|stack|w:all|(none)|Pop the 16-bit FLAGS register.
popfd|stack|w:all|(none)|Pop EFLAGS.|bits=16/32
popfq|stack|w:all|(none)|Pop RFLAGS (64-bit mode).
bswap|data|-|r32; r64|Reverse the byte order of the register (little-endian <-> big-endian).
movbe|data|-|r, m; m, r|Load or store with the bytes swapped (big-endian move).
cbw|conv|-|(none)|Sign-extend AL into AX.
cwde|conv|-|(none)|Sign-extend AX into EAX.
cdqe|conv|-|(none)|Sign-extend EAX into RAX.
cwd|conv|-|(none)|Sign-extend AX into DX:AX (before a 16-bit IDIV).
cdq|conv|-|(none)|Sign-extend EAX into EDX:EAX (prepare a 32-bit IDIV).
cqo|conv|-|(none)|Sign-extend RAX into RDX:RAX (prepare a 64-bit IDIV).
add|arith|w:OF SF ZF AF PF CF|r/m, r; r, r/m; r/m, imm|Add the source to the destination.
adc|arith|r:CF w:OF SF ZF AF PF CF|r/m, r; r, r/m; r/m, imm|Add the source plus the carry flag to the destination (multi-word addition).
sub|arith|w:OF SF ZF AF PF CF|r/m, r; r, r/m; r/m, imm|Subtract the source from the destination.
sbb|arith|r:CF w:OF SF ZF AF PF CF|r/m, r; r, r/m; r/m, imm|Subtract the source plus the carry flag (multi-word subtraction).
imul|arith|w:OF CF u:SF ZF AF PF|r/m; r, r/m; r, r/m, imm|Signed multiply. One operand: AL/AX/EAX/RAX times it into AX / DX:AX / EDX:EAX / RDX:RAX. Two or three operands: truncated product in the register.
mul|arith|w:OF CF u:SF ZF AF PF|r/m|Unsigned multiply AL/AX/EAX/RAX by the operand; the double-size result goes to AX / DX:AX / EDX:EAX / RDX:RAX.
idiv|arith|u:OF SF ZF AF PF CF|r/m|Signed divide AX / DX:AX / EDX:EAX / RDX:RAX by the operand: quotient in AL/AX/EAX/RAX, remainder in AH/DX/EDX/RDX. Sign-extend first (CBW/CWD/CDQ/CQO). Divide by zero raises #DE.
div|arith|u:OF SF ZF AF PF CF|r/m|Unsigned divide AX / DX:AX / EDX:EAX / RDX:RAX by the operand: quotient in the accumulator, remainder in AH/DX/EDX/RDX. Clear the high half first (xor edx, edx).
inc|arith|w:OF SF ZF AF PF|r/m|Add 1 to the operand. CF is not changed.
dec|arith|w:OF SF ZF AF PF|r/m|Subtract 1 from the operand. CF is not changed.
neg|arith|w:OF SF ZF AF PF CF|r/m|Two's complement negation (0 - operand). CF=0 only when the operand was 0.
cmp|arith|w:OF SF ZF AF PF CF|r/m, r; r, r/m; r/m, imm|Compare: subtract the source from the destination, set the flags and throw the result away. Follow with Jcc / SETcc / CMOVcc.
and|logic|0:OF CF w:SF ZF PF u:AF|r/m, r; r, r/m; r/m, imm|Bitwise AND.
or|logic|0:OF CF w:SF ZF PF u:AF|r/m, r; r, r/m; r/m, imm|Bitwise inclusive OR.
xor|logic|0:OF CF w:SF ZF PF u:AF|r/m, r; r, r/m; r/m, imm|Bitwise exclusive OR. xor eax, eax is the usual way to zero a register.
not|logic|-|r/m|Bitwise NOT (one's complement). No flags change.
test|logic|0:OF CF w:SF ZF PF u:AF|r/m, r; r/m, imm|Bitwise AND that only sets the flags. test eax, eax checks for zero / sign.
shl|shift|w:CF OF SF ZF PF u:AF|r/m, 1; r/m, cl; r/m, imm8|Shift left, filling with zeros (multiply by 2^n). The last bit shifted out goes to CF.
sal|shift|w:CF OF SF ZF PF u:AF|r/m, 1; r/m, cl; r/m, imm8|Arithmetic shift left (same instruction as SHL).
shr|shift|w:CF OF SF ZF PF u:AF|r/m, 1; r/m, cl; r/m, imm8|Logical shift right, filling with zeros (unsigned divide by 2^n).
sar|shift|w:CF OF SF ZF PF u:AF|r/m, 1; r/m, cl; r/m, imm8|Arithmetic shift right, repeating the sign bit (signed divide by 2^n, rounding toward minus infinity).
rol|shift|w:CF OF|r/m, 1; r/m, cl; r/m, imm8|Rotate left; the bit that leaves on the left re-enters on the right and is copied to CF.
ror|shift|w:CF OF|r/m, 1; r/m, cl; r/m, imm8|Rotate right; the bit that leaves on the right re-enters on the left and is copied to CF.
rcl|shift|r:CF w:CF OF|r/m, 1; r/m, cl; r/m, imm8|Rotate left through the carry flag (operand plus CF form one ring).
rcr|shift|r:CF w:CF OF|r/m, 1; r/m, cl; r/m, imm8|Rotate right through the carry flag.
shld|shift|w:CF SF ZF PF u:OF AF|r/m, r, imm8; r/m, r, cl|Double-precision shift left: bits shifted in come from the second operand.
shrd|shift|w:CF SF ZF PF u:OF AF|r/m, r, imm8; r/m, r, cl|Double-precision shift right: bits shifted in come from the second operand.
bt|bit|w:CF u:OF SF AF PF|r/m, r; r/m, imm8|Copy the selected bit into CF.
bts|bit|w:CF u:OF SF AF PF|r/m, r; r/m, imm8|Copy the selected bit into CF, then set it.
btr|bit|w:CF u:OF SF AF PF|r/m, r; r/m, imm8|Copy the selected bit into CF, then clear it.
btc|bit|w:CF u:OF SF AF PF|r/m, r; r/m, imm8|Copy the selected bit into CF, then invert it.
bsf|bit|w:ZF u:OF SF AF PF CF|r, r/m|Index of the lowest set bit; ZF=1 (destination undefined) when the source is 0.
bsr|bit|w:ZF u:OF SF AF PF CF|r, r/m|Index of the highest set bit; ZF=1 (destination undefined) when the source is 0.
lzcnt|bit|w:CF ZF u:OF SF AF PF|r, r/m|Count leading zero bits (operand size when the source is 0, CF=1). Needs ABM/LZCNT support.
tzcnt|bit|w:CF ZF u:OF SF AF PF|r, r/m|Count trailing zero bits (operand size when the source is 0, CF=1). Needs BMI1.
popcnt|bit|0:OF SF AF CF PF w:ZF|r, r/m|Count the set bits of the source.
jmp|control|-|rel; r/m|Jump: continue execution at the target unconditionally.
call|control|-|rel; r/m|Push the return address and jump to the procedure. On Win64 keep RSP 16-byte aligned and reserve 32 bytes of shadow space first.
ret|control|-|(none); imm16|Pop the return address and jump to it. ret n also removes n bytes of arguments (stdcall).
retn|control|-|(none); imm16|Near return (same as RET).
retf|control|-|(none); imm16|Far return: pops the instruction pointer and CS.
loop|control|-|rel8|Decrement ECX/RCX (CX in 16-bit code) and jump if it is not zero. Flags are not changed.
loope|control|r:ZF|rel8|Decrement the counter; jump while it is not zero and ZF=1.
loopz|control|r:ZF|rel8|Same as LOOPE.
loopne|control|r:ZF|rel8|Decrement the counter; jump while it is not zero and ZF=0.
loopnz|control|r:ZF|rel8|Same as LOOPNE.
jcxz|control|-|rel8|Jump if CX is zero.|bits=16/32
jecxz|control|-|rel8|Jump if ECX is zero.
jrcxz|control|-|rel8|Jump if RCX is zero (64-bit mode).
int|system|0:IF TF|imm8|Call software interrupt handler n (int 21h DOS services, int 10h BIOS video, int 80h Linux 32-bit system calls).
int3|system|-|(none)|Breakpoint trap (one-byte 0CCh). Debuggers stop here.
into|system|r:OF|(none)|Interrupt 4 when OF=1.|bits=16/32
iret|system|w:all|(none)|Return from an interrupt handler (pops IP, CS and FLAGS).
iretd|system|w:all|(none)|32-bit return from an interrupt handler.
iretq|system|w:all|(none)|64-bit return from an interrupt handler.
syscall|system|-|(none)|Fast system call (64-bit Linux: number in RAX, arguments in RDI RSI RDX R10 R8 R9; RCX and R11 are destroyed).
sysret|system|w:all|(none)|Return from a SYSCALL handler to user mode.
sysenter|system|-|(none)|Fast system call (32-bit).
sysexit|system|-|(none)|Return from a SYSENTER handler.
enter|stack|-|imm16, imm8|Make a stack frame: push EBP/RBP, copy the stack pointer to it and reserve the given number of bytes.
leave|stack|-|(none)|Destroy the stack frame: mov esp, ebp / mov rsp, rbp then pop the frame pointer.
nop|misc|-|(none); r/m|No operation. The r/m form is a multi-byte NOP used for alignment.
hlt|system|-|(none)|Stop the processor until the next interrupt (privileged).
pause|misc|-|(none)|Spin-wait hint: improves the speed and power use of busy-wait loops.
cpuid|system|-|(none)|Return processor information selected by EAX (and ECX) in EAX, EBX, ECX, EDX.
rdtsc|system|-|(none)|Read the time-stamp counter into EDX:EAX.
rdtscp|system|-|(none)|Read the time-stamp counter into EDX:EAX and the processor id into ECX (waits for earlier instructions).
rdrand|misc|0:OF SF ZF AF PF w:CF|r|Hardware random number; CF=1 when a value was returned.
rdseed|misc|0:OF SF ZF AF PF w:CF|r|Random seed from the hardware entropy source; CF=1 when valid.
ud2|system|-|(none)|Guaranteed invalid instruction (raises #UD) - marks unreachable code.
xlat|data|-|m8|Table look-up: AL = [EBX/RBX + AL].
xlatb|data|-|(none)|Table look-up: AL = [EBX/RBX + AL].
movsb|string|r:DF|(none)|Copy a byte from [ESI/RSI] to [EDI/RDI] and step both pointers (forward when DF=0). With REP: copy ECX/RCX bytes.
movsw|string|r:DF|(none)|Copy a word from [ESI] to [EDI] and step both pointers by 2. With REP: ECX words.
movsd|string|r:DF|(none); xmm, xmm/m64; m64, xmm|String form: copy a dword from [ESI] to [EDI] (REP for blocks). SSE2 form: move a scalar double between XMM registers / memory.
movsq|string|r:DF|(none)|Copy a qword from [RSI] to [RDI] and step both pointers by 8 (64-bit mode).
cmpsb|string|r:DF w:OF SF ZF AF PF CF|(none)|Compare the bytes at [ESI] and [EDI] and step both pointers. REPE/REPNE compare whole blocks.
cmpsw|string|r:DF w:OF SF ZF AF PF CF|(none)|Compare the words at [ESI] and [EDI] and step both pointers.
cmpsd|string|r:DF w:OF SF ZF AF PF CF|(none); xmm, xmm/m64, imm8|String form: compare dwords at [ESI] and [EDI]. SSE2 form: compare scalar doubles with the predicate imm8 (mask result).
cmpsq|string|r:DF w:OF SF ZF AF PF CF|(none)|Compare the qwords at [RSI] and [RDI] and step both pointers.
scasb|string|r:DF w:OF SF ZF AF PF CF|(none)|Compare AL with the byte at [EDI] and step EDI. repne scasb finds a byte (strlen idiom).
scasw|string|r:DF w:OF SF ZF AF PF CF|(none)|Compare AX with the word at [EDI] and step EDI.
scasd|string|r:DF w:OF SF ZF AF PF CF|(none)|Compare EAX with the dword at [EDI] and step EDI.
scasq|string|r:DF w:OF SF ZF AF PF CF|(none)|Compare RAX with the qword at [RDI] and step RDI.
lodsb|string|r:DF|(none)|Load the byte at [ESI] into AL and step ESI.
lodsw|string|r:DF|(none)|Load the word at [ESI] into AX and step ESI.
lodsd|string|r:DF|(none)|Load the dword at [ESI] into EAX and step ESI.
lodsq|string|r:DF|(none)|Load the qword at [RSI] into RAX and step RSI.
stosb|string|r:DF|(none)|Store AL at [EDI] and step EDI. rep stosb fills ECX bytes (memset idiom).
stosw|string|r:DF|(none)|Store AX at [EDI] and step EDI.
stosd|string|r:DF|(none)|Store EAX at [EDI] and step EDI.
stosq|string|r:DF|(none)|Store RAX at [RDI] and step RDI.
insb|io|r:DF|(none)|Read a byte from port DX into [EDI] (privileged on protected OSes).
outsb|io|r:DF|(none)|Write the byte at [ESI] to port DX.
in|io|-|al/ax/eax, imm8; al/ax/eax, dx|Read from an I/O port (DOS / bare metal; privileged under Windows and Linux).
out|io|-|imm8, al/ax/eax; dx, al/ax/eax|Write to an I/O port (DOS / bare metal; privileged under Windows and Linux).
clc|flags|0:CF|(none)|Clear the carry flag.
stc|flags|1:CF|(none)|Set the carry flag.
cmc|flags|w:CF|(none)|Complement (invert) the carry flag.
cld|flags|0:DF|(none)|Clear the direction flag: string instructions go forward (the ABIs expect DF=0 at calls).
std|flags|1:DF|(none)|Set the direction flag: string instructions go backward.
cli|flags|0:IF|(none)|Disable maskable interrupts (privileged).
sti|flags|1:IF|(none)|Enable maskable interrupts (privileged).
lahf|flags|-|(none)|Copy SF ZF AF PF CF into AH.
sahf|flags|w:SF ZF AF PF CF|(none)|Load SF ZF AF PF CF from AH.
lock|prefix|-|instruction|Make the following read-modify-write instruction atomic (add, inc, xchg, cmpxchg, xadd ... with a memory destination).
rep|prefix|-|string instruction|Repeat the string instruction ECX/RCX times (movs, stos, lods, ins, outs).
repe|prefix|r:ZF|string instruction|Repeat while equal (ZF=1) and the counter is not zero (cmps, scas).
repz|prefix|r:ZF|string instruction|Same as REPE.
repne|prefix|r:ZF|string instruction|Repeat while not equal (ZF=0) and the counter is not zero (cmps, scas).
repnz|prefix|r:ZF|string instruction|Same as REPNE.
aaa|bcd|w:AF CF u:OF SF ZF PF|(none)|ASCII adjust AL after an addition of unpacked BCD digits.|bits=16/32
aas|bcd|w:AF CF u:OF SF ZF PF|(none)|ASCII adjust AL after a subtraction of unpacked BCD digits.|bits=16/32
aam|bcd|w:SF ZF PF u:OF AF CF|(none); imm8|ASCII adjust after multiply: AH = AL / 10, AL = AL mod 10.|bits=16/32
aad|bcd|w:SF ZF PF u:OF AF CF|(none); imm8|ASCII adjust before division: AL = AH*10 + AL, AH = 0.|bits=16/32
daa|bcd|w:AF CF SF ZF PF u:OF|(none)|Decimal adjust AL after adding packed BCD values.|bits=16/32
das|bcd|w:AF CF SF ZF PF u:OF|(none)|Decimal adjust AL after subtracting packed BCD values.|bits=16/32
bound|system|-|r, m|Raise #BR when the index register is outside the bounds pair in memory.|bits=16/32
lfence|sync|-|(none)|Load fence: earlier loads complete before later ones start.
sfence|sync|-|(none)|Store fence: earlier stores become visible before later ones.
mfence|sync|-|(none)|Full memory fence for loads and stores.
prefetcht0|sync|-|m8|Hint: bring the cache line into all cache levels.
prefetcht1|sync|-|m8|Hint: bring the cache line into L2 and higher.
prefetcht2|sync|-|m8|Hint: bring the cache line into L3 and higher.
prefetchnta|sync|-|m8|Hint: fetch the cache line with minimal cache pollution (non-temporal).
clflush|sync|-|m8|Write back and invalidate the cache line that holds the address.
wait|x87|-|(none)|Wait until pending unmasked x87 exceptions are handled.
fwait|x87|-|(none)|Same as WAIT.
andn|bmi|w:SF ZF 0:OF CF u:AF PF|r, r, r/m|dest = NOT src1 AND src2 (BMI1).
bextr|bmi|w:ZF 0:OF CF u:AF SF PF|r, r/m, r|Extract a bit field: start and length come from the third operand (BMI1).
blsi|bmi|w:SF ZF CF 0:OF u:AF PF|r, r/m|Isolate the lowest set bit (BMI1).
blsmsk|bmi|w:SF CF 0:ZF OF u:AF PF|r, r/m|Mask up to and including the lowest set bit (BMI1).
blsr|bmi|w:SF ZF CF 0:OF u:AF PF|r, r/m|Clear the lowest set bit (BMI1).
bzhi|bmi|w:SF ZF CF 0:OF u:AF PF|r, r/m, r|Zero the bits at and above the index in the third operand (BMI2).
pdep|bmi|-|r, r, r/m|Parallel bit deposit: scatter the low bits of src1 to the positions set in the mask (BMI2).
pext|bmi|-|r, r, r/m|Parallel bit extract: gather the bits selected by the mask into the low bits (BMI2).
rorx|bmi|-|r, r/m, imm8|Rotate right without touching the flags (BMI2).
sarx|bmi|-|r, r/m, r|Arithmetic shift right by a register count without touching the flags (BMI2).
shlx|bmi|-|r, r/m, r|Shift left by a register count without touching the flags (BMI2).
shrx|bmi|-|r, r/m, r|Logical shift right by a register count without touching the flags (BMI2).
mulx|bmi|-|r, r, r/m|Unsigned multiply EDX/RDX by the source without touching the flags: high half to the first operand, low half to the second (BMI2).
adcx|arith|r:CF w:CF|r, r/m|Add with carry using only CF (ADX) - lets two carry chains run in parallel with ADOX.
adox|arith|r:OF w:OF|r, r/m|Add with carry using OF as the carry (ADX).
crc32|sse42|-|r32, r/m8/16/32; r64, r/m64|Accumulate a CRC-32C (Castagnoli) checksum (SSE4.2).
movnti|sync|-|m32/64, r32/64|Store a register to memory with a non-temporal hint (bypasses the caches).
lgdt|system|-|m|Load the global descriptor table register (privileged).
lidt|system|-|m|Load the interrupt descriptor table register (privileged).
sgdt|system|-|m|Store the global descriptor table register.
sidt|system|-|m|Store the interrupt descriptor table register.
rdmsr|system|-|(none)|Read the model-specific register ECX into EDX:EAX (privileged).
wrmsr|system|-|(none)|Write EDX:EAX into the model-specific register ECX (privileged).
xgetbv|system|-|(none)|Read the extended control register ECX (XCR0 tells which AVX state the OS saves) into EDX:EAX.
invlpg|system|-|m|Invalidate the TLB entry of the page (privileged).
fld|x87|-|m32fp; m64fp; m80fp; st(i)|Push a floating-point value onto the x87 register stack.
fst|x87|-|m32fp; m64fp; st(i)|Store ST(0) without popping.
fstp|x87|-|m32fp; m64fp; m80fp; st(i)|Store ST(0) and pop the register stack.
fild|x87|-|m16int; m32int; m64int|Convert a signed integer from memory and push it.
fist|x87|-|m16int; m32int|Store ST(0) as an integer (current rounding mode).
fistp|x87|-|m16int; m32int; m64int|Store ST(0) as an integer and pop.
fisttp|x87|-|m16int; m32int; m64int|Store ST(0) as a truncated integer and pop (SSE3).
fld1|x87|-|(none)|Push +1.0.
fldz|x87|-|(none)|Push +0.0.
fldpi|x87|-|(none)|Push pi.
fldl2e|x87|-|(none)|Push log2(e).
fldln2|x87|-|(none)|Push ln(2).
fadd|x87|-|m32fp; m64fp; st(0), st(i); st(i), st(0)|Floating-point add.
faddp|x87|-|st(i), st(0); (none)|Add ST(0) to ST(i) and pop.
fiadd|x87|-|m16int; m32int|Add an integer from memory to ST(0).
fsub|x87|-|m32fp; m64fp; st(0), st(i); st(i), st(0)|Floating-point subtract.
fsubp|x87|-|st(i), st(0); (none)|Subtract and pop.
fsubr|x87|-|m32fp; m64fp; st(0), st(i)|Reverse subtract (source minus destination).
fsubrp|x87|-|st(i), st(0); (none)|Reverse subtract and pop.
fmul|x87|-|m32fp; m64fp; st(0), st(i); st(i), st(0)|Floating-point multiply.
fmulp|x87|-|st(i), st(0); (none)|Multiply and pop.
fdiv|x87|-|m32fp; m64fp; st(0), st(i); st(i), st(0)|Floating-point divide.
fdivp|x87|-|st(i), st(0); (none)|Divide and pop.
fdivr|x87|-|m32fp; m64fp; st(0), st(i)|Reverse divide (source divided by destination).
fdivrp|x87|-|st(i), st(0); (none)|Reverse divide and pop.
fchs|x87|-|(none)|Change the sign of ST(0).
fabs|x87|-|(none)|Absolute value of ST(0).
fsqrt|x87|-|(none)|Square root of ST(0).
fsin|x87|-|(none)|Sine of ST(0) (radians).
fcos|x87|-|(none)|Cosine of ST(0) (radians).
fsincos|x87|-|(none)|Replace ST(0) with its sine and push its cosine.
fptan|x87|-|(none)|Partial tangent: replace ST(0) with tan and push 1.0.
fpatan|x87|-|(none)|Arctangent of ST(1)/ST(0), store in ST(1) and pop.
f2xm1|x87|-|(none)|ST(0) = 2^ST(0) - 1 (for -1 <= ST(0) <= 1).
fyl2x|x87|-|(none)|ST(1) = ST(1) * log2(ST(0)), then pop.
fscale|x87|-|(none)|Multiply ST(0) by 2 raised to the integer part of ST(1).
frndint|x87|-|(none)|Round ST(0) to an integer (current rounding mode).
fprem|x87|-|(none)|Partial remainder of ST(0) / ST(1).
fcom|x87|-|m32fp; m64fp; st(i)|Compare ST(0) with the operand (sets the FPU condition codes C0 C2 C3).
fcomp|x87|-|m32fp; m64fp; st(i)|Compare and pop.
fcompp|x87|-|(none)|Compare ST(0) with ST(1) and pop both.
fcomi|x87|w:ZF PF CF|st(0), st(i)|Compare and set EFLAGS directly (use JA/JB/JE afterwards).
fcomip|x87|w:ZF PF CF|st(0), st(i)|Compare, set EFLAGS and pop.
fucomi|x87|w:ZF PF CF|st(0), st(i)|Unordered compare (no exception for QNaN), set EFLAGS.
fucomip|x87|w:ZF PF CF|st(0), st(i)|Unordered compare, set EFLAGS and pop.
ftst|x87|-|(none)|Compare ST(0) with 0.0.
fxch|x87|-|st(i); (none)|Exchange ST(0) and ST(i).
finit|x87|-|(none)|Initialise the FPU (after checking pending exceptions).
fninit|x87|-|(none)|Initialise the FPU without waiting.
fstsw|x87|-|m16; ax|Store the FPU status word (fstsw ax + sahf: old way to branch on a compare).
fnstsw|x87|-|m16; ax|Store the FPU status word without waiting.
fldcw|x87|-|m16|Load the FPU control word (rounding mode, precision, exception masks).
fstcw|x87|-|m16|Store the FPU control word.
fnstcw|x87|-|m16|Store the FPU control word without waiting.
ffree|x87|-|st(i)|Mark ST(i) empty.
fincstp|x87|-|(none)|Increment the FPU stack-top pointer.
fdecstp|x87|-|(none)|Decrement the FPU stack-top pointer.
fxam|x87|-|(none)|Classify ST(0) (zero, normal, infinity, NaN ...) into C0-C3.
fxsave|x87|-|m512byte|Save the x87, MMX and SSE state (512 bytes, 16-aligned).
fxrstor|x87|-|m512byte|Restore the state saved by FXSAVE.
emms|mmx|-|(none)|Empty the MMX state so x87 code can run again.
movd|mmx|-|mm/xmm, r/m32; r/m32, mm/xmm|Move a dword between a general register / memory and an MMX or XMM register (upper bits zeroed).
movq|mmx|-|mm/xmm, r/m64; r/m64, mm/xmm; xmm, xmm/m64|Move a qword between registers / memory (XMM upper half zeroed).
movaps|sse|-|xmm, xmm/m128; m128, xmm|Move 4 packed singles; memory must be 16-byte aligned.
movups|sse|-|xmm, xmm/m128; m128, xmm|Move 4 packed singles; no alignment needed.
movss|sse|-|xmm, xmm/m32; m32, xmm|Move a scalar single (from memory: upper elements zeroed).
movlps|sse|-|xmm, m64; m64, xmm|Move the two low singles to or from memory.
movhps|sse|-|xmm, m64; m64, xmm|Move the two high singles to or from memory.
movhlps|sse|-|xmm, xmm|Copy the high two singles of the source into the low half of the destination.
movlhps|sse|-|xmm, xmm|Copy the low two singles of the source into the high half of the destination.
movmskps|sse|-|r32, xmm|Collect the sign bits of the 4 singles into a 4-bit mask.
addps|sse|-|xmm, xmm/m128|Add packed singles.
addss|sse|-|xmm, xmm/m32|Add the low singles.
subps|sse|-|xmm, xmm/m128|Subtract packed singles.
subss|sse|-|xmm, xmm/m32|Subtract the low singles.
mulps|sse|-|xmm, xmm/m128|Multiply packed singles.
mulss|sse|-|xmm, xmm/m32|Multiply the low singles.
divps|sse|-|xmm, xmm/m128|Divide packed singles.
divss|sse|-|xmm, xmm/m32|Divide the low singles.
sqrtps|sse|-|xmm, xmm/m128|Square roots of packed singles.
sqrtss|sse|-|xmm, xmm/m32|Square root of the low single.
rsqrtps|sse|-|xmm, xmm/m128|Fast approximate 1/sqrt(x) of packed singles (about 12 bits).
rcpps|sse|-|xmm, xmm/m128|Fast approximate reciprocals of packed singles.
maxps|sse|-|xmm, xmm/m128|Per-element maximum of packed singles.
maxss|sse|-|xmm, xmm/m32|Maximum of the low singles.
minps|sse|-|xmm, xmm/m128|Per-element minimum of packed singles.
minss|sse|-|xmm, xmm/m32|Minimum of the low singles.
andps|sse|-|xmm, xmm/m128|Bitwise AND of packed singles (absolute value with a mask).
andnps|sse|-|xmm, xmm/m128|Bitwise (NOT destination) AND source.
orps|sse|-|xmm, xmm/m128|Bitwise OR.
xorps|sse|-|xmm, xmm/m128|Bitwise XOR; xorps xmm0, xmm0 zeroes the register.
cmpps|sse|-|xmm, xmm/m128, imm8|Compare packed singles with predicate imm8 (0 eq, 1 lt, 2 le, 3 unord, 4 neq, 5 nlt, 6 nle, 7 ord): all-ones masks where true.
cmpss|sse|-|xmm, xmm/m32, imm8|Compare the low singles with predicate imm8 (mask result).
comiss|sse|w:ZF PF CF 0:OF SF AF|xmm, xmm/m32|Compare the low singles and set EFLAGS (use JA/JB/JE ...).
ucomiss|sse|w:ZF PF CF 0:OF SF AF|xmm, xmm/m32|Unordered compare of the low singles into EFLAGS (no exception on QNaN).
shufps|sse|-|xmm, xmm/m128, imm8|Shuffle: two singles from the destination and two from the source picked by imm8.
unpcklps|sse|-|xmm, xmm/m128|Interleave the low singles of both operands.
unpckhps|sse|-|xmm, xmm/m128|Interleave the high singles of both operands.
cvtsi2ss|sse|-|xmm, r/m32; xmm, r/m64|Convert a signed integer to a scalar single.
cvtss2si|sse|-|r32/64, xmm/m32|Convert the low single to an integer (current rounding).
cvttss2si|sse|-|r32/64, xmm/m32|Convert the low single to an integer, truncating.
ldmxcsr|sse|-|m32|Load the MXCSR control / status register.
stmxcsr|sse|-|m32|Store the MXCSR register.
movntps|sse|-|m128, xmm|Non-temporal store of packed singles.
movapd|sse2|-|xmm, xmm/m128; m128, xmm|Move 2 packed doubles (16-byte aligned memory).
movupd|sse2|-|xmm, xmm/m128; m128, xmm|Move 2 packed doubles (no alignment needed).
movdqa|sse2|-|xmm, xmm/m128; m128, xmm|Move 128 bits of integers (16-byte aligned memory).
movdqu|sse2|-|xmm, xmm/m128; m128, xmm|Move 128 bits of integers (unaligned).
movntdq|sse2|-|m128, xmm|Non-temporal store of 128 bits.
addpd|sse2|-|xmm, xmm/m128|Add packed doubles.
addsd|sse2|-|xmm, xmm/m64|Add the low doubles.
subpd|sse2|-|xmm, xmm/m128|Subtract packed doubles.
subsd|sse2|-|xmm, xmm/m64|Subtract the low doubles.
mulpd|sse2|-|xmm, xmm/m128|Multiply packed doubles.
mulsd|sse2|-|xmm, xmm/m64|Multiply the low doubles.
divpd|sse2|-|xmm, xmm/m128|Divide packed doubles.
divsd|sse2|-|xmm, xmm/m64|Divide the low doubles.
sqrtpd|sse2|-|xmm, xmm/m128|Square roots of packed doubles.
sqrtsd|sse2|-|xmm, xmm/m64|Square root of the low double.
maxpd|sse2|-|xmm, xmm/m128|Per-element maximum of packed doubles.
maxsd|sse2|-|xmm, xmm/m64|Maximum of the low doubles.
minpd|sse2|-|xmm, xmm/m128|Per-element minimum of packed doubles.
minsd|sse2|-|xmm, xmm/m64|Minimum of the low doubles.
andpd|sse2|-|xmm, xmm/m128|Bitwise AND of packed doubles.
andnpd|sse2|-|xmm, xmm/m128|Bitwise (NOT destination) AND source.
orpd|sse2|-|xmm, xmm/m128|Bitwise OR.
xorpd|sse2|-|xmm, xmm/m128|Bitwise XOR.
cmppd|sse2|-|xmm, xmm/m128, imm8|Compare packed doubles with predicate imm8 (mask result).
comisd|sse2|w:ZF PF CF 0:OF SF AF|xmm, xmm/m64|Compare the low doubles and set EFLAGS.
ucomisd|sse2|w:ZF PF CF 0:OF SF AF|xmm, xmm/m64|Unordered compare of the low doubles into EFLAGS.
shufpd|sse2|-|xmm, xmm/m128, imm8|Shuffle doubles picked by imm8.
unpcklpd|sse2|-|xmm, xmm/m128|Combine the low doubles of both operands.
unpckhpd|sse2|-|xmm, xmm/m128|Combine the high doubles of both operands.
cvtsi2sd|sse2|-|xmm, r/m32; xmm, r/m64|Convert a signed integer to a scalar double.
cvtsd2si|sse2|-|r32/64, xmm/m64|Convert the low double to an integer (current rounding).
cvttsd2si|sse2|-|r32/64, xmm/m64|Convert the low double to an integer, truncating (C cast).
cvtss2sd|sse2|-|xmm, xmm/m32|Convert the low single to a double.
cvtsd2ss|sse2|-|xmm, xmm/m64|Convert the low double to a single.
cvtdq2ps|sse2|-|xmm, xmm/m128|Convert 4 signed dwords to singles.
cvtps2dq|sse2|-|xmm, xmm/m128|Convert 4 singles to dwords (current rounding).
cvttps2dq|sse2|-|xmm, xmm/m128|Convert 4 singles to dwords, truncating.
cvtdq2pd|sse2|-|xmm, xmm/m64|Convert 2 signed dwords to doubles.
cvtpd2dq|sse2|-|xmm, xmm/m128|Convert 2 doubles to dwords.
cvtpd2ps|sse2|-|xmm, xmm/m128|Convert 2 doubles to singles.
cvtps2pd|sse2|-|xmm, xmm/m64|Convert 2 singles to doubles.
movmskpd|sse2|-|r32, xmm|Collect the sign bits of the 2 doubles.
paddb|sse2|-|xmm, xmm/m128|Add packed bytes (wrap-around).
paddw|sse2|-|xmm, xmm/m128|Add packed words (wrap-around).
paddd|sse2|-|xmm, xmm/m128|Add packed dwords.
paddq|sse2|-|xmm, xmm/m128|Add packed qwords.
paddsb|sse2|-|xmm, xmm/m128|Add packed signed bytes with saturation.
paddsw|sse2|-|xmm, xmm/m128|Add packed signed words with saturation.
paddusb|sse2|-|xmm, xmm/m128|Add packed unsigned bytes with saturation.
paddusw|sse2|-|xmm, xmm/m128|Add packed unsigned words with saturation.
psubb|sse2|-|xmm, xmm/m128|Subtract packed bytes.
psubw|sse2|-|xmm, xmm/m128|Subtract packed words.
psubd|sse2|-|xmm, xmm/m128|Subtract packed dwords.
psubq|sse2|-|xmm, xmm/m128|Subtract packed qwords.
psubsb|sse2|-|xmm, xmm/m128|Subtract packed signed bytes with saturation.
psubsw|sse2|-|xmm, xmm/m128|Subtract packed signed words with saturation.
psubusb|sse2|-|xmm, xmm/m128|Subtract packed unsigned bytes with saturation.
psubusw|sse2|-|xmm, xmm/m128|Subtract packed unsigned words with saturation.
pmullw|sse2|-|xmm, xmm/m128|Multiply packed words, keep the low 16 bits.
pmulhw|sse2|-|xmm, xmm/m128|Multiply packed signed words, keep the high 16 bits.
pmulhuw|sse2|-|xmm, xmm/m128|Multiply packed unsigned words, keep the high 16 bits.
pmuludq|sse2|-|xmm, xmm/m128|Multiply the even unsigned dwords into 64-bit products.
pmaddwd|sse2|-|xmm, xmm/m128|Multiply words and add adjacent pairs into dwords.
pavgb|sse2|-|xmm, xmm/m128|Rounded average of unsigned bytes.
pavgw|sse2|-|xmm, xmm/m128|Rounded average of unsigned words.
pmaxsw|sse2|-|xmm, xmm/m128|Maximum of signed words.
pmaxub|sse2|-|xmm, xmm/m128|Maximum of unsigned bytes.
pminsw|sse2|-|xmm, xmm/m128|Minimum of signed words.
pminub|sse2|-|xmm, xmm/m128|Minimum of unsigned bytes.
psadbw|sse2|-|xmm, xmm/m128|Sum of absolute byte differences per 8-byte half.
pand|sse2|-|xmm, xmm/m128|Bitwise AND (128 bits).
pandn|sse2|-|xmm, xmm/m128|Bitwise (NOT destination) AND source.
por|sse2|-|xmm, xmm/m128|Bitwise OR.
pxor|sse2|-|xmm, xmm/m128|Bitwise XOR; pxor xmm0, xmm0 zeroes it.
pcmpeqb|sse2|-|xmm, xmm/m128|Compare bytes for equality (0FFh where equal).
pcmpeqw|sse2|-|xmm, xmm/m128|Compare words for equality.
pcmpeqd|sse2|-|xmm, xmm/m128|Compare dwords for equality.
pcmpgtb|sse2|-|xmm, xmm/m128|Signed greater-than compare of bytes.
pcmpgtw|sse2|-|xmm, xmm/m128|Signed greater-than compare of words.
pcmpgtd|sse2|-|xmm, xmm/m128|Signed greater-than compare of dwords.
psllw|sse2|-|xmm, xmm/m128; xmm, imm8|Shift words left.
pslld|sse2|-|xmm, xmm/m128; xmm, imm8|Shift dwords left.
psllq|sse2|-|xmm, xmm/m128; xmm, imm8|Shift qwords left.
psrlw|sse2|-|xmm, xmm/m128; xmm, imm8|Shift words right (logical).
psrld|sse2|-|xmm, xmm/m128; xmm, imm8|Shift dwords right (logical).
psrlq|sse2|-|xmm, xmm/m128; xmm, imm8|Shift qwords right (logical).
psraw|sse2|-|xmm, xmm/m128; xmm, imm8|Shift words right (arithmetic).
psrad|sse2|-|xmm, xmm/m128; xmm, imm8|Shift dwords right (arithmetic).
pslldq|sse2|-|xmm, imm8|Shift the whole register left by imm8 bytes.
psrldq|sse2|-|xmm, imm8|Shift the whole register right by imm8 bytes.
pshufd|sse2|-|xmm, xmm/m128, imm8|Shuffle dwords chosen by imm8 (2 bits per element).
pshufhw|sse2|-|xmm, xmm/m128, imm8|Shuffle the high four words.
pshuflw|sse2|-|xmm, xmm/m128, imm8|Shuffle the low four words.
punpcklbw|sse2|-|xmm, xmm/m128|Interleave low bytes (zero-extend with a zero register).
punpcklwd|sse2|-|xmm, xmm/m128|Interleave low words.
punpckldq|sse2|-|xmm, xmm/m128|Interleave low dwords.
punpcklqdq|sse2|-|xmm, xmm/m128|Interleave low qwords.
punpckhbw|sse2|-|xmm, xmm/m128|Interleave high bytes.
punpckhwd|sse2|-|xmm, xmm/m128|Interleave high words.
punpckhdq|sse2|-|xmm, xmm/m128|Interleave high dwords.
punpckhqdq|sse2|-|xmm, xmm/m128|Interleave high qwords.
packsswb|sse2|-|xmm, xmm/m128|Pack signed words to signed bytes with saturation.
packssdw|sse2|-|xmm, xmm/m128|Pack signed dwords to signed words with saturation.
packuswb|sse2|-|xmm, xmm/m128|Pack signed words to unsigned bytes with saturation.
pmovmskb|sse2|-|r32, xmm|Collect the top bit of each byte into a 16-bit mask (fast string scanning).
pextrw|sse2|-|r32, xmm, imm8|Extract the word selected by imm8.
pinsrw|sse2|-|xmm, r32/m16, imm8|Insert a word at the position selected by imm8.
maskmovdqu|sse2|-|xmm, xmm|Store the selected bytes to [EDI/RDI] (non-temporal).
addsubps|sse3|-|xmm, xmm/m128|Alternately subtract and add packed singles.
addsubpd|sse3|-|xmm, xmm/m128|Subtract the low doubles, add the high ones.
haddps|sse3|-|xmm, xmm/m128|Horizontal add of adjacent singles.
haddpd|sse3|-|xmm, xmm/m128|Horizontal add of adjacent doubles.
hsubps|sse3|-|xmm, xmm/m128|Horizontal subtract of adjacent singles.
hsubpd|sse3|-|xmm, xmm/m128|Horizontal subtract of adjacent doubles.
movddup|sse3|-|xmm, xmm/m64|Duplicate the low double into both halves.
movshdup|sse3|-|xmm, xmm/m128|Duplicate the odd singles.
movsldup|sse3|-|xmm, xmm/m128|Duplicate the even singles.
lddqu|sse3|-|xmm, m128|Unaligned 128-bit load that is fast across cache lines.
pshufb|ssse3|-|xmm, xmm/m128|Shuffle bytes with a control vector (table look-up of 16 bytes).
phaddw|ssse3|-|xmm, xmm/m128|Horizontal add of adjacent words.
phaddd|ssse3|-|xmm, xmm/m128|Horizontal add of adjacent dwords.
phsubw|ssse3|-|xmm, xmm/m128|Horizontal subtract of adjacent words.
phsubd|ssse3|-|xmm, xmm/m128|Horizontal subtract of adjacent dwords.
pabsb|ssse3|-|xmm, xmm/m128|Absolute values of signed bytes.
pabsw|ssse3|-|xmm, xmm/m128|Absolute values of signed words.
pabsd|ssse3|-|xmm, xmm/m128|Absolute values of signed dwords.
palignr|ssse3|-|xmm, xmm/m128, imm8|Concatenate both operands and extract 16 bytes starting at byte imm8.
pmulhrsw|ssse3|-|xmm, xmm/m128|Multiply signed words with rounding and scaling (fixed-point Q15).
pmaddubsw|ssse3|-|xmm, xmm/m128|Multiply unsigned by signed bytes and add pairs with saturation.
psignb|ssse3|-|xmm, xmm/m128|Negate, keep or zero bytes according to the sign of the source.
psignw|ssse3|-|xmm, xmm/m128|Negate, keep or zero words according to the sign of the source.
psignd|ssse3|-|xmm, xmm/m128|Negate, keep or zero dwords according to the sign of the source.
blendps|sse41|-|xmm, xmm/m128, imm8|Pick each single from the source or the destination by the bits of imm8.
blendpd|sse41|-|xmm, xmm/m128, imm8|Pick each double from the source or the destination by imm8.
blendvps|sse41|-|xmm, xmm/m128, <xmm0>|Pick singles by the sign bits of XMM0.
blendvpd|sse41|-|xmm, xmm/m128, <xmm0>|Pick doubles by the sign bits of XMM0.
pblendw|sse41|-|xmm, xmm/m128, imm8|Pick words by the bits of imm8.
pblendvb|sse41|-|xmm, xmm/m128, <xmm0>|Pick bytes by the sign bits of XMM0.
dpps|sse41|-|xmm, xmm/m128, imm8|Dot product of singles (imm8 selects inputs and outputs).
dppd|sse41|-|xmm, xmm/m128, imm8|Dot product of doubles.
insertps|sse41|-|xmm, xmm/m32, imm8|Insert a single and optionally zero elements.
extractps|sse41|-|r/m32, xmm, imm8|Extract the single selected by imm8.
pinsrb|sse41|-|xmm, r32/m8, imm8|Insert a byte.
pinsrd|sse41|-|xmm, r/m32, imm8|Insert a dword.
pinsrq|sse41|-|xmm, r/m64, imm8|Insert a qword.
pextrb|sse41|-|r/m8, xmm, imm8|Extract a byte.
pextrd|sse41|-|r/m32, xmm, imm8|Extract a dword.
pextrq|sse41|-|r/m64, xmm, imm8|Extract a qword.
pmovzxbw|sse41|-|xmm, xmm/m64|Zero-extend 8 bytes to words.
pmovzxbd|sse41|-|xmm, xmm/m32|Zero-extend 4 bytes to dwords.
pmovzxwd|sse41|-|xmm, xmm/m64|Zero-extend 4 words to dwords.
pmovzxdq|sse41|-|xmm, xmm/m64|Zero-extend 2 dwords to qwords.
pmovsxbw|sse41|-|xmm, xmm/m64|Sign-extend 8 bytes to words.
pmovsxbd|sse41|-|xmm, xmm/m32|Sign-extend 4 bytes to dwords.
pmovsxwd|sse41|-|xmm, xmm/m64|Sign-extend 4 words to dwords.
pmovsxdq|sse41|-|xmm, xmm/m64|Sign-extend 2 dwords to qwords.
pmulld|sse41|-|xmm, xmm/m128|Multiply dwords, keep the low 32 bits.
pmuldq|sse41|-|xmm, xmm/m128|Multiply the even signed dwords into 64-bit products.
pminsb|sse41|-|xmm, xmm/m128|Minimum of signed bytes.
pminsd|sse41|-|xmm, xmm/m128|Minimum of signed dwords.
pminuw|sse41|-|xmm, xmm/m128|Minimum of unsigned words.
pminud|sse41|-|xmm, xmm/m128|Minimum of unsigned dwords.
pmaxsb|sse41|-|xmm, xmm/m128|Maximum of signed bytes.
pmaxsd|sse41|-|xmm, xmm/m128|Maximum of signed dwords.
pmaxuw|sse41|-|xmm, xmm/m128|Maximum of unsigned words.
pmaxud|sse41|-|xmm, xmm/m128|Maximum of unsigned dwords.
roundps|sse41|-|xmm, xmm/m128, imm8|Round packed singles (imm8: 0 nearest, 1 down, 2 up, 3 truncate).
roundpd|sse41|-|xmm, xmm/m128, imm8|Round packed doubles.
roundss|sse41|-|xmm, xmm/m32, imm8|Round the low single.
roundsd|sse41|-|xmm, xmm/m64, imm8|Round the low double.
ptest|sse41|w:ZF CF 0:OF SF AF PF|xmm, xmm/m128|ZF = (a AND b) is zero, CF = (NOT a AND b) is zero.
pcmpeqq|sse41|-|xmm, xmm/m128|Compare qwords for equality.
packusdw|sse41|-|xmm, xmm/m128|Pack signed dwords to unsigned words with saturation.
movntdqa|sse41|-|xmm, m128|Non-temporal aligned load (write-combining memory).
phminposuw|sse41|-|xmm, xmm/m128|Find the minimum unsigned word and its index.
mpsadbw|sse41|-|xmm, xmm/m128, imm8|Multiple sums of absolute byte differences (block matching).
pcmpgtq|sse42|-|xmm, xmm/m128|Signed greater-than compare of qwords.
pcmpestri|sse42|w:CF ZF SF OF 0:AF PF|xmm, xmm/m128, imm8|Compare strings with explicit lengths (EAX, EDX); index result in ECX.
pcmpestrm|sse42|w:CF ZF SF OF 0:AF PF|xmm, xmm/m128, imm8|Compare strings with explicit lengths; mask result in XMM0.
pcmpistri|sse42|w:CF ZF SF OF 0:AF PF|xmm, xmm/m128, imm8|Compare zero-terminated strings; index result in ECX.
pcmpistrm|sse42|w:CF ZF SF OF 0:AF PF|xmm, xmm/m128, imm8|Compare zero-terminated strings; mask result in XMM0.
aesenc|aes|-|xmm, xmm/m128|One AES encryption round.
aesenclast|aes|-|xmm, xmm/m128|Last AES encryption round.
aesdec|aes|-|xmm, xmm/m128|One AES decryption round.
aesdeclast|aes|-|xmm, xmm/m128|Last AES decryption round.
aeskeygenassist|aes|-|xmm, xmm/m128, imm8|Help expand the AES key.
aesimc|aes|-|xmm, xmm/m128|Inverse mix columns (prepare decryption keys).
pclmulqdq|aes|-|xmm, xmm/m128, imm8|Carry-less multiply of two qwords (CRC, GCM).
vbroadcastss|avx|-|xmm/ymm, m32; xmm/ymm, xmm|Copy one single into every element.
vbroadcastsd|avx|-|ymm, m64; ymm, xmm|Copy one double into every element.
vbroadcastf128|avx|-|ymm, m128|Copy 128 bits into both halves.
vinsertf128|avx|-|ymm, ymm, xmm/m128, imm8|Insert 128 bits into the half chosen by imm8.
vextractf128|avx|-|xmm/m128, ymm, imm8|Extract the 128-bit half chosen by imm8.
vperm2f128|avx|-|ymm, ymm, ymm/m256, imm8|Choose each 128-bit half from either source (or zero).
vpermilps|avx|-|xmm/ymm, xmm/ymm, xmm/ymm/m; xmm/ymm, xmm/ymm/m, imm8|Permute singles inside each 128-bit lane.
vpermilpd|avx|-|xmm/ymm, xmm/ymm, xmm/ymm/m; xmm/ymm, xmm/ymm/m, imm8|Permute doubles inside each 128-bit lane.
vmaskmovps|avx|-|xmm/ymm, xmm/ymm, m; m, xmm/ymm, xmm/ymm|Masked load / store of singles (no fault on masked elements).
vmaskmovpd|avx|-|xmm/ymm, xmm/ymm, m; m, xmm/ymm, xmm/ymm|Masked load / store of doubles.
vzeroupper|avx|-|(none)|Zero the upper halves of all YMM registers - do this before calling non-AVX code to avoid slow transitions.
vzeroall|avx|-|(none)|Zero all YMM registers.
vtestps|avx|w:ZF CF 0:OF SF AF PF|xmm/ymm, xmm/ymm/m|Test the sign bits of singles (like PTEST).
vtestpd|avx|w:ZF CF 0:OF SF AF PF|xmm/ymm, xmm/ymm/m|Test the sign bits of doubles.
vpbroadcastb|avx2|-|xmm/ymm, xmm/m8|Copy one byte into every element.
vpbroadcastw|avx2|-|xmm/ymm, xmm/m16|Copy one word into every element.
vpbroadcastd|avx2|-|xmm/ymm, xmm/m32|Copy one dword into every element.
vpbroadcastq|avx2|-|xmm/ymm, xmm/m64|Copy one qword into every element.
vinserti128|avx2|-|ymm, ymm, xmm/m128, imm8|Insert 128 integer bits into a half.
vextracti128|avx2|-|xmm/m128, ymm, imm8|Extract a 128-bit integer half.
vperm2i128|avx2|-|ymm, ymm, ymm/m256, imm8|Choose each integer half from either source.
vpermd|avx2|-|ymm, ymm, ymm/m256|Permute dwords across the full register.
vpermq|avx2|-|ymm, ymm/m256, imm8|Permute qwords across the full register.
vpermps|avx2|-|ymm, ymm, ymm/m256|Permute singles across the full register.
vpermpd|avx2|-|ymm, ymm/m256, imm8|Permute doubles across the full register.
vpsllvd|avx2|-|xmm/ymm, xmm/ymm, xmm/ymm/m|Shift each dword left by its own count.
vpsllvq|avx2|-|xmm/ymm, xmm/ymm, xmm/ymm/m|Shift each qword left by its own count.
vpsrlvd|avx2|-|xmm/ymm, xmm/ymm, xmm/ymm/m|Shift each dword right (logical) by its own count.
vpsrlvq|avx2|-|xmm/ymm, xmm/ymm, xmm/ymm/m|Shift each qword right (logical) by its own count.
vpsravd|avx2|-|xmm/ymm, xmm/ymm, xmm/ymm/m|Shift each dword right (arithmetic) by its own count.
vpgatherdd|avx2|-|xmm/ymm, vm32, xmm/ymm|Gather dwords from memory with dword indexes (mask register is cleared).
vgatherdps|avx2|-|xmm/ymm, vm32, xmm/ymm|Gather singles with dword indexes.
vgatherdpd|avx2|-|xmm/ymm, vm32, xmm/ymm|Gather doubles with dword indexes.
vpmaskmovd|avx2|-|xmm/ymm, xmm/ymm, m; m, xmm/ymm, xmm/ymm|Masked load / store of dwords.
vpblendd|avx2|-|xmm/ymm, xmm/ymm, xmm/ymm/m, imm8|Pick dwords by the bits of imm8.
"""

# condition codes: suffix -> (meaning, flags read, synonyms)
CONDITIONS = [
    ("o", "overflow (OF=1)", "OF", []),
    ("no", "no overflow (OF=0)", "OF", []),
    ("b", "below - unsigned less (CF=1)", "CF", ["c", "nae"]),
    ("ae", "above or equal - unsigned (CF=0)", "CF", ["nb", "nc"]),
    ("e", "equal / zero (ZF=1)", "ZF", ["z"]),
    ("ne", "not equal / not zero (ZF=0)", "ZF", ["nz"]),
    ("be", "below or equal - unsigned (CF=1 or ZF=1)", "CF ZF", ["na"]),
    ("a", "above - unsigned greater (CF=0 and ZF=0)", "CF ZF", ["nbe"]),
    ("s", "sign - negative (SF=1)", "SF", []),
    ("ns", "not sign - zero or positive (SF=0)", "SF", []),
    ("p", "parity even (PF=1)", "PF", ["pe"]),
    ("np", "parity odd (PF=0)", "PF", ["po"]),
    ("l", "less - signed (SF<>OF)", "SF OF", ["nge"]),
    ("ge", "greater or equal - signed (SF=OF)", "SF OF", ["nl"]),
    ("le", "less or equal - signed (ZF=1 or SF<>OF)", "ZF SF OF", ["ng"]),
    ("g", "greater - signed (ZF=0 and SF=OF)", "ZF SF OF", ["nle"]),
]


def _parse() -> dict[str, Instr]:
    out: dict[str, Instr] = {}
    for raw in _TABLE.strip().splitlines():
        parts = raw.split("|")
        if len(parts) < 5:
            continue
        name, cat, flags, forms, doc = (p.strip() for p in parts[:5])
        bits = ""
        for extra in parts[5:]:
            if extra.startswith("bits="):
                bits = extra[5:]
        out[name] = Instr(name, cat, flags, [f.strip() for f in forms.split(";") if f.strip()], doc, bits=bits)
    for suf, meaning, flags, syn in CONDITIONS:
        for s in [suf, *syn]:
            alias = "" if s == suf else "j" + suf
            out["j" + s] = Instr("j" + s, "cond", "r:" + flags, ["rel8", "rel32"],
                                 f"Jump if {meaning}. Usually follows CMP or TEST.", alias)
            out["set" + s] = Instr("set" + s, "cond", "r:" + flags, ["r/m8"],
                                   f"Set the byte operand to 1 if {meaning}, else to 0.",
                                   "" if s == suf else "set" + suf)
            out["cmov" + s] = Instr("cmov" + s, "cond", "r:" + flags, ["r16/32/64, r/m16/32/64"],
                                    f"Move the source into the destination only if {meaning} (branch-free select).",
                                    "" if s == suf else "cmov" + suf)
    # AVX (VEX) forms of the SSE..SSE4.2 / AES instructions: v + name, non-destructive 3-operand syntax
    vex_skip = {"crc32", "ldmxcsr", "stmxcsr", "movntps", "maskmovdqu"}
    for name, ins in list(out.items()):
        if ins.category in ("sse", "sse2", "sse3", "ssse3", "sse41", "sse42", "aes") and name not in vex_skip:
            v = "v" + name
            if v in out:
                continue
            forms = []
            for f in ins.forms:
                ops = [o.strip() for o in f.split(",")]
                if len(ops) >= 2 and ops[0].startswith("xmm") and not name.startswith(("mov", "cvt", "comi", "ucomi",
                                                                                         "ptest", "pmov", "pextr",
                                                                                         "lddqu", "sqrt", "rcp", "rsqrt",
                                                                                         "pshuf", "pabs", "extract",
                                                                                         "phmin", "aesimc", "aeskey")):
                    ops = [ops[0], ops[0].replace("xmm", "xmm2")] + ops[1:]
                forms.append(", ".join(ops).replace("xmm", "xmm/ymm") if name.endswith(("ps", "pd")) or
                             name.startswith("p") else ", ".join(ops))
            out[v] = Instr(v, "avx", ins.flags, forms,
                           f"AVX (VEX-encoded) form of {name.upper()}: {ins.doc} The VEX form takes a separate "
                           "destination and zeroes the bits above the result; packed forms also work on 256-bit YMM "
                           "registers (AVX / AVX2).", name)
    vex_skip.discard("ldmxcsr")
    out["vldmxcsr"] = Instr("vldmxcsr", "avx", "-", ["m32"], "AVX form of LDMXCSR: load the MXCSR register.", "ldmxcsr")
    out["vstmxcsr"] = Instr("vstmxcsr", "avx", "-", ["m32"], "AVX form of STMXCSR: store the MXCSR register.", "stmxcsr")
    # FMA3: vf[n]madd/msub 132/213/231 ps/pd/ss/sd
    orders = {"132": "a = a*c + b", "213": "a = b*a + c", "231": "a = b*c + a"}
    for op, sign in (("fmadd", "+"), ("fmsub", "-"), ("fnmadd", "-(..)+"), ("fnmsub", "-(..)-")):
        for order, formula in orders.items():
            for t, what in (("ps", "packed singles"), ("pd", "packed doubles"), ("ss", "the low single"),
                            ("sd", "the low double")):
                n = f"v{op}{order}{t}"
                f2 = formula.replace("+", "-") if op == "fmsub" else formula
                if op.startswith("fn"):
                    f2 = formula.replace("= ", "= -(").replace(" + ", ") + " if op == "fnmadd" else ") - ")
                out[n] = Instr(n, "fma", "-", ["xmm/ymm, xmm/ymm, xmm/ymm/m"],
                               f"Fused multiply-{'add' if 'add' in op else 'subtract'}{' negated' if op.startswith('fn') else ''}"
                               f" of {what} with one rounding ({order} operand order: {f2}).", "")
    return out


INSTRUCTIONS: dict[str, Instr] = _parse()

# AT&T (GAS) size suffixes accepted on most integer instructions
ATT_SUFFIX = {"b": "byte", "w": "word", "l": "dword (long)", "q": "qword"}
ATT_SUFFIXED = ["mov", "add", "sub", "adc", "sbb", "cmp", "and", "or", "xor", "test", "inc", "dec", "neg", "not",
                "push", "pop", "lea", "shl", "shr", "sar", "sal", "rol", "ror", "imul", "mul", "idiv", "div", "xchg",
                "call", "jmp", "ret", "cmpxchg", "xadd", "bt", "bts", "btr", "btc", "bsf", "bsr"]


def att_base(word: str) -> str:
    """'movq' -> 'mov', 'movzbl' -> 'movzx', 'addl' -> 'add' (AT&T mnemonics); '' if unknown."""
    w = word.lower()
    if len(w) > 2 and w[-1] in ATT_SUFFIX and w[:-1] in ATT_SUFFIXED:
        return w[:-1]
    if w in INSTRUCTIONS:
        return w
    if w.startswith(("movzb", "movzw")) and len(w) == 6:
        return "movzx"
    if w.startswith(("movsb", "movsw")) and len(w) == 6:
        return "movsx"
    if w == "movslq":
        return "movsxd"
    if w in ("cltq",):
        return "cdqe"
    if w in ("cqto",):
        return "cqo"
    if w in ("cltd",):
        return "cdq"
    if w in ("cwtl",):
        return "cwde"
    if w[-1:] in ATT_SUFFIX and w[:-1] in INSTRUCTIONS:
        return w[:-1]
    return ""


# ============================================================================ registers
def _registers() -> dict[str, Register]:
    regs: dict[str, Register] = {}

    def add(name, size, doc, family="", parts=None):
        regs[name] = Register(name, size, doc, family or name, parts or [])

    gp = [("a", "Accumulator: multiply / divide operand, return value of functions (all common ABIs)."),
          ("b", "Base register; callee-saved (must be preserved by a called function) in every common ABI."),
          ("c", "Counter: LOOP / REP / shift counts (CL). 1st integer argument of the Microsoft x64 ABI (RCX); "
                "4th of System V (RCX)."),
          ("d", "Data: high half of MUL / DIV results, I/O port number. 2nd argument of Microsoft x64 (RDX); "
                "3rd of System V.")]
    for ch, doc in gp:
        add(f"r{ch}x", 64, doc, f"r{ch}x", [f"e{ch}x", f"{ch}x", f"{ch}h", f"{ch}l"])
        add(f"e{ch}x", 32, f"Low 32 bits of R{ch.upper()}X. {doc} Writing it zeroes the upper 32 bits.", f"r{ch}x")
        add(f"{ch}x", 16, f"Low 16 bits of E{ch.upper()}X. {doc}", f"r{ch}x")
        add(f"{ch}l", 8, f"Low byte of {ch.upper()}X.", f"r{ch}x")
        add(f"{ch}h", 8, f"High byte of {ch.upper()}X (bits 8-15; cannot be used with a REX prefix).", f"r{ch}x")
    idx = [("si", "Source index for string instructions. Callee-saved on Win64; 2nd argument of System V (RSI)."),
           ("di", "Destination index for string instructions. Callee-saved on Win64; 1st argument of System V (RDI)."),
           ("bp", "Frame (base) pointer; callee-saved. [rbp+...] addresses arguments, [rbp-...] locals."),
           ("sp", "Stack pointer: top of the stack. Win64 needs it 16-byte aligned at every CALL, plus 32 bytes "
                  "of shadow space above the return address.")]
    for n, doc in idx:
        add(f"r{n}", 64, doc, f"r{n}", [f"e{n}", n, f"{n}l"])
        add(f"e{n}", 32, f"Low 32 bits of R{n.upper()}. {doc}", f"r{n}")
        add(n, 16, f"Low 16 bits of E{n.upper()}. {doc}", f"r{n}")
        add(f"{n}l", 8, f"Low byte of R{n.upper()} (64-bit mode, needs REX).", f"r{n}")
    for i in range(8, 16):
        role = {8: "3rd argument of Microsoft x64, 5th of System V", 9: "4th argument of Microsoft x64, "
                "6th of System V", 10: "volatile (caller-saved); syscall 4th argument on Linux",
                11: "volatile (caller-saved); destroyed by SYSCALL"}.get(i, "callee-saved (preserve it)")
        add(f"r{i}", 64, f"General register R{i} (64-bit mode only): {role}.", f"r{i}",
            [f"r{i}d", f"r{i}w", f"r{i}b"])
        add(f"r{i}d", 32, f"Low 32 bits of R{i}.", f"r{i}")
        add(f"r{i}w", 16, f"Low 16 bits of R{i}.", f"r{i}")
        add(f"r{i}b", 8, f"Low byte of R{i}.", f"r{i}")
        regs[f"r{i}l"] = Register(f"r{i}l", 8, f"Low byte of R{i} (MASM / GAS spelling of R{i}B).", f"r{i}")
    add("rip", 64, "Instruction pointer (64-bit). [rel label] / label(%rip) addresses data relative to it.")
    add("eip", 32, "Instruction pointer (32-bit); not directly writable (use JMP / CALL / RET).", "rip")
    add("ip", 16, "Instruction pointer (16-bit).", "rip")
    for s, doc in (("cs", "Code segment"), ("ds", "Data segment (default for most memory operands)"),
                   ("es", "Extra segment (destination of string instructions)"), ("ss", "Stack segment"),
                   ("fs", "Extra segment: Win32 TEB at fs:[0]; thread-local storage on Linux x86-64"),
                   ("gs", "Extra segment: Win64 TEB at gs:[0]; thread-local storage on Linux x86")):
        add(s, 16, doc + ".")
    add("rflags", 64, "Flags register: CF PF AF ZF SF TF IF DF OF ...")
    add("eflags", 32, "Flags register: CF PF AF ZF SF TF IF DF OF ...", "rflags")
    add("flags", 16, "Flags register (16-bit).", "rflags")
    for i in range(8):
        add(f"st{i}", 80, f"x87 FPU stack register ST({i}) - {'top of the stack' if i == 0 else f'{i} below the top'}.")
        add(f"mm{i}", 64, f"MMX register {i} (aliases the x87 registers; run EMMS before x87 code).")
        add(f"k{i}", 64, f"AVX-512 opmask register {i}.")
    regs["st"] = Register("st", 80, "Top of the x87 register stack (ST(0)).", "st0")
    for i in range(32):
        vol = ("volatile" if i < 6 else "callee-saved on Win64 (XMM6-XMM15)" if i < 16 else "AVX-512 only")
        arg = (f"; {['1st', '2nd', '3rd', '4th'][i]} floating-point argument on Win64" if i < 4 else "")
        arg += "; float / double return value" if i == 0 else ""
        add(f"xmm{i}", 128, f"SSE register {i} (128 bits: 4 singles, 2 doubles or packed integers) - {vol}{arg}.",
            f"zmm{i}")
        add(f"ymm{i}", 256, f"AVX register {i} (256 bits; the low half is XMM{i}).", f"zmm{i}")
        add(f"zmm{i}", 512, f"AVX-512 register {i} (512 bits; the low halves are YMM{i} / XMM{i}).", f"zmm{i}")
    for i in (0, 2, 3, 4, 8):
        add(f"cr{i}", 64, f"Control register CR{i} (privileged).")
    for i in (0, 1, 2, 3, 6, 7):
        add(f"dr{i}", 64, f"Debug register DR{i} (hardware breakpoints; privileged).")
    return regs


REGISTERS: dict[str, Register] = _registers()
REG16_ONLY = {"ax", "bx", "cx", "dx", "si", "di", "bp", "sp", "al", "ah", "bl", "bh", "cl", "ch", "dl", "dh",
              "cs", "ds", "es", "ss", "ip", "flags"}


def registers_for(bits: int) -> list[str]:
    """Register names that make sense for 16 / 32 / 64-bit code (completions)."""
    out = []
    for name, r in REGISTERS.items():
        if bits == 16 and (r.size > 16 or name not in REG16_ONLY) and not name.startswith(("st", "xmm", "mm")):
            continue
        if bits == 32 and (name.startswith("r") and name not in ("rflags",) or name.startswith(("zmm", "k", "cr", "dr"))
                           or name in ("sil", "dil", "bpl", "spl")):
            continue
        if bits == 64 and name.startswith(("k", "cr", "dr")):
            continue
        out.append(name)
    return out


def flags_text(flags: str) -> str:
    """'r:CF w:OF SF' -> 'reads CF; writes OF SF' (hover)."""
    if not flags or flags == "-":
        return "none"
    names = {"r": "reads", "w": "writes", "u": "undefined", "0": "cleared", "1": "set"}
    out = []
    for part in flags.split():
        if ":" in part:
            kind, f = part.split(":", 1)
            out.append([names.get(kind, kind), f])
        elif out:
            out[-1][1] += " " + part
        else:
            out.append(["writes", part])
    return "; ".join(f"{k} {v}" for k, v in out)


def instruction(word: str, att: bool = False) -> Instr | None:
    w = word.lower()
    if att:
        base = att_base(w)
        if base:
            return INSTRUCTIONS.get(base)
    return INSTRUCTIONS.get(w)


def register(word: str) -> Register | None:
    w = word.lower().lstrip("%")
    if w.startswith("st(") and w.endswith(")"):
        w = "st" + w[3:-1]
    return REGISTERS.get(w)
