"""x86 / x64 assembler for patches: Keystone when installed (pip install keystone-engine), otherwise a small
built-in subset that covers the usual patch instructions.

    data = assemble("mov eax, 1\\nret", va=0x401000, is64=False)

Built-in subset: nop, ret, ret N, int3, leave, push/pop reg, push imm, call/jmp/jcc <address>,
mov reg32/64, imm, xor reg, reg, db <bytes>. Multiple instructions: one per line or separated by ';'.
"""
from __future__ import annotations

import re
import struct


class AsmError(ValueError):
    pass


def keystone_available() -> bool:
    try:
        import keystone  # noqa: F401
        return True
    except Exception:  # noqa: BLE001 - also a broken DLL
        return False


def _lines(text: str) -> list[str]:
    out = []
    for raw in text.replace(";", "\n").splitlines():
        s = raw.split("//")[0].strip()
        if s:
            out.append(s)
    return out


def assemble(text: str, va: int, is64: bool) -> bytes:
    lines = _lines(text)
    if not lines:
        return b""
    # db lines are handled here for both back ends
    if keystone_available() and not any(ln.lower().startswith("db ") for ln in lines):
        try:
            import keystone
            ks = keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_64 if is64 else keystone.KS_MODE_32)
            enc, _n = ks.asm("\n".join(lines), va)
            if enc is None:
                raise AsmError("Nothing was assembled.")
            return bytes(enc)
        except AsmError:
            raise
        except Exception as e:  # noqa: BLE001 - KsError
            raise AsmError(f"Assembler: {e}") from None
    out = bytearray()
    for ln in lines:
        out += _builtin(ln, va + len(out), is64)
    return bytes(out)


REG32 = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]
REG64 = ["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi"]
JCC = {"jo": 0, "jno": 1, "jb": 2, "jc": 2, "jnae": 2, "jae": 3, "jnb": 3, "jnc": 3, "je": 4, "jz": 4, "jne": 5,
       "jnz": 5, "jbe": 6, "jna": 6, "ja": 7, "jnbe": 7, "js": 8, "jns": 9, "jp": 10, "jpe": 10, "jnp": 11,
       "jpo": 11, "jl": 12, "jnge": 12, "jge": 13, "jnl": 13, "jle": 14, "jng": 14, "jg": 15, "jnle": 15}


def _num(s: str) -> int:
    s = s.strip().lower()
    neg = s.startswith("-")
    s = s.lstrip("-")
    if s.endswith("h") and re.fullmatch(r"[0-9a-f]+h", s):
        v = int(s[:-1], 16)
    else:
        v = int(s, 0)
    return -v if neg else v


def _builtin(ln: str, va: int, is64: bool) -> bytes:
    s = re.sub(r"\s+", " ", ln.strip().lower())
    op, _, rest = s.partition(" ")
    args = [a.strip() for a in rest.split(",")] if rest else []
    try:
        if op == "db":
            vals = re.split(r"[\s,]+", rest.strip())
            return bytes(int(v, 16) if not v.startswith("0x") else int(v, 0) for v in vals if v)
        if op == "nop" and not args:
            return b"\x90"
        if op in ("ret", "retn"):
            return b"\xC3" if not args else b"\xC2" + struct.pack("<H", _num(args[0]))
        if op == "int3":
            return b"\xCC"
        if op == "leave":
            return b"\xC9"
        if op in ("push", "pop") and len(args) == 1:
            regs = REG64 if is64 else REG32
            if args[0] in regs:
                return bytes([(0x50 if op == "push" else 0x58) + regs.index(args[0])])
            if op == "push":
                v = _num(args[0])
                return b"\x6A" + struct.pack("<b", v) if -128 <= v < 128 else b"\x68" + struct.pack("<I", v & 0xFFFFFFFF)
        if op in ("call", "jmp") and len(args) == 1:
            t = _num(args[0])
            if op == "jmp" and -128 <= t - (va + 2) < 128:
                return b"\xEB" + struct.pack("<b", t - (va + 2))
            rel = t - (va + 5)
            if not -2**31 <= rel < 2**31:
                raise AsmError("Target too far for a relative call / jmp.")
            return (b"\xE8" if op == "call" else b"\xE9") + struct.pack("<i", rel)
        if op in JCC and len(args) == 1:
            t = _num(args[0])
            if -128 <= t - (va + 2) < 128:
                return bytes([0x70 + JCC[op]]) + struct.pack("<b", t - (va + 2))
            return bytes([0x0F, 0x80 + JCC[op]]) + struct.pack("<i", t - (va + 6))
        if op == "xor" and len(args) == 2 and args[0] == args[1]:
            if args[0] in REG32:
                i = REG32.index(args[0])
                return bytes([0x31, 0xC0 | (i << 3) | i])
            if is64 and args[0] in REG64:
                i = REG64.index(args[0])
                return bytes([0x48, 0x31, 0xC0 | (i << 3) | i])
        if op == "mov" and len(args) == 2:
            if args[0] in REG32:
                return bytes([0xB8 + REG32.index(args[0])]) + struct.pack("<I", _num(args[1]) & 0xFFFFFFFF)
            if is64 and args[0] in REG64:
                v = _num(args[1])
                if -2**31 <= v < 2**31:
                    return bytes([0x48, 0xC7, 0xC0 + REG64.index(args[0])]) + struct.pack("<i", v)
                return bytes([0x48, 0xB8 + REG64.index(args[0])]) + struct.pack("<Q", v & (2**64 - 1))
    except (ValueError, struct.error) as e:
        raise AsmError(f"{ln}: {e}") from None
    raise AsmError(f"'{ln}' is not in the built-in assembler subset - install keystone-engine "
                   "(pip install keystone-engine) for full x86 / x64 assembly.")


def nops(n: int) -> bytes:
    return b"\x90" * n


def jmp_rel32(src: int, dst: int) -> bytes:
    return b"\xE9" + struct.pack("<i", dst - (src + 5))


def call_rel32(src: int, dst: int) -> bytes:
    return b"\xE8" + struct.pack("<i", dst - (src + 5))
