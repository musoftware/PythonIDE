"""Imitations of common C runtime / Win32 functions and Linux system calls for the runtime checks.

The emulated program calls them through stub slots (radide/asm_sim/objload.py): the slot holds ``ret`` (or
``ret n`` for 32-bit stdcall), and the runner calls ``Stubs.call(name)`` just before that ``ret`` runs. A stub
reads its arguments with the program's calling convention, does its work on the emulated memory (output goes
to ``runner.output``, input comes from the check's stdin text), checks pointer arguments (an invalid pointer
becomes a ``sim.bad_pointer_arg`` finding and stops the run - a real program would crash inside the library)
and puts the result in RAX / EAX. Every call is logged (``runner.calls``).
"""
from __future__ import annotations

import re
import struct

from ..asm_intel import apis

STDCALL_RX = re.compile(r"@(\d+)$")


def plain(name: str) -> str:
    n = re.sub(r"^(?:__imp_|_imp__)", "", name)
    n = STDCALL_RX.sub("", n)
    if n.startswith("_") and not n.startswith("__"):
        n = n[1:]
    return n


def ret_bytes(name: str, bits: int) -> bytes:
    """The bytes of a stub slot: ``ret`` or ``ret n`` (32-bit stdcall)."""
    if bits == 32:
        m = STDCALL_RX.search(name)
        n = int(m.group(1)) if m else 0
        if not m:
            api = apis.lookup(name)
            if api is not None and not api.is_crt and not api.variadic and plain(name).lower() != "wsprintfa":
                n = 4 * len(api.params)
        if n:
            return bytes([0xC2, n & 0xFF, n >> 8])
    return b"\xC3"


class StopRun(Exception):
    """Raised by a stub to end the run (exit / invalid pointer)."""


class Stubs:
    def __init__(self, runner):
        self.r = runner
        self.rand_state = 1
        self.heap_next = runner.HEAP_BASE + 0x1000
        self.handles = 0x100

    # ------------------------------------------------------------------ arguments
    def arg(self, i: int, as_float: bool = False):
        r = self.r
        abi = r.abi
        if abi == "win64":
            regs = ("rcx", "rdx", "r8", "r9")
            if i < 4:
                if as_float:
                    return r.xmm_double(i)
                return r.reg(regs[i])
            return r.read_int(r.reg("rsp") + 8 + 32 + 8 * (i - 4), 8)
        if abi == "sysv":
            regs = ("rdi", "rsi", "rdx", "rcx", "r8", "r9")
            if i < 6:
                return r.reg(regs[i])
            return r.read_int(r.reg("rsp") + 8 + 8 * (i - 6), 8)
        return r.read_int(r.reg("esp") + 4 + 4 * i, 4)

    def arg_loc(self, i: int) -> str:
        abi = self.r.abi
        if abi == "win64":
            return ("RCX", "RDX", "R8", "R9")[i] if i < 4 else f"[RSP+{32 + 8 * (i - 4)}]"
        if abi == "sysv":
            return ("RDI", "RSI", "RDX", "RCX", "R8", "R9")[i] if i < 6 else f"[RSP+{8 * (i - 6)}]"
        return f"[ESP+{4 * i}]"

    def arg_reg(self, i: int) -> str:
        loc = self.arg_loc(i)
        return loc.lower() if not loc.startswith("[") else "eax"

    def ptr(self, i: int, func: str, param: str, what_en: str = "a string", what_ar: str = "نص", size: int = 1,
            null_ok: bool = False) -> int:
        """Argument *i* as a pointer; an invalid one ends the run with sim.bad_pointer_arg."""
        v = self.arg(i)
        if v == 0 and null_ok:
            return 0
        if not self.r.valid(v, size):
            self.r.bad_pointer(func, param, i, v, what_en, what_ar, self.arg_loc(i), self.arg_reg(i))
            raise StopRun()
        return v

    def ret(self, v: int) -> None:
        self.r.set_ret(v)

    # ------------------------------------------------------------------ memory helpers
    def cstr(self, addr: int, limit: int = 65536, wide: bool = False) -> str:
        out = bytearray()
        step = 2 if wide else 1
        a = addr
        while len(out) < limit:
            if not self.r.valid(a, step):
                break
            b = self.r.read(a, step)
            if b == b"\0" * step:
                break
            out += b
            a += step
        if wide:
            return out.decode("utf-16-le", errors="replace")
        return out.decode("cp1252", errors="replace")

    def write(self, addr: int, data: bytes) -> None:
        self.r.write(addr, data)

    def alloc(self, n: int) -> int:
        n = max(1, int(n))
        a = self.heap_next
        if a + n > self.r.HEAP_BASE + self.r.HEAP_SIZE:
            return 0
        self.heap_next = (a + n + 15) & ~15
        return a

    # ------------------------------------------------------------------ printf family
    def format(self, fmt: str, first_arg: int, func: str) -> str:
        out = []
        i = 0
        k = first_arg
        n = len(fmt)
        while i < n:
            ch = fmt[i]
            if ch != "%":
                out.append(ch)
                i += 1
                continue
            m = re.match(r"%([-+ #0]*)(\*|\d+)?(?:\.(\*|\d+))?(hh|h|ll|l|I64|I32|z|j|t|L|q)?([diouxXcspfFeEgGaAn%])",
                         fmt[i:])
            if not m:
                out.append(ch)
                i += 1
                continue
            flags, width, prec, length, conv = m.groups()
            i += m.end()
            if conv == "%":
                out.append("%")
                continue
            if width == "*":
                width = str(_signed(self.arg(k), 32))
                k += 1
            if prec == "*":
                prec = str(_signed(self.arg(k), 32))
                k += 1
            spec = "%" + (flags or "") + (width or "") + (("." + prec) if prec is not None else "")
            wide64 = self.r.bits == 64 and length in ("ll", "I64", "z", "j", "t", "q") or (
                self.r.abi == "sysv" and length == "l")
            if conv in "di":
                v = self.arg(k)
                k += 1
                if self.r.bits == 32 and length in ("ll", "I64", "q"):
                    v |= self.arg(k) << 32
                    k += 1
                    v = _signed(v, 64)
                else:
                    v = _signed(v, 64 if wide64 else 32)
                    if length == "h":
                        v = _signed(v, 16)
                    elif length == "hh":
                        v = _signed(v, 8)
                out.append((spec + "d") % v)
            elif conv in "ouxX":
                v = self.arg(k)
                k += 1
                if self.r.bits == 32 and length in ("ll", "I64", "q"):
                    v |= self.arg(k) << 32
                    k += 1
                elif not wide64:
                    v &= 0xFFFFFFFF
                if length == "h":
                    v &= 0xFFFF
                elif length == "hh":
                    v &= 0xFF
                out.append((spec + conv) % v)
            elif conv == "c":
                out.append((spec + "s") % chr(self.arg(k) & 0xFF))
                k += 1
            elif conv == "s":
                p = self.arg(k)
                if not self.r.valid(p, 1):
                    self.r.bad_pointer(func, f"%s (argument {k + 1})", k, p, "a string for %s", "نص لـ %s",
                                       self.arg_loc(k), self.arg_reg(k))
                    raise StopRun()
                k += 1
                out.append((spec + "s") % self.cstr(p, wide=length in ("l", "w") and self.r.abi != "sysv"))
            elif conv == "p":
                out.append(f"{self.arg(k):0{16 if self.r.bits == 64 else 8}X}")
                k += 1
            elif conv in "fFeEgGaA":
                if self.r.bits == 32:
                    lo, hi = self.arg(k), self.arg(k + 1)
                    k += 2
                    v = struct.unpack("<d", struct.pack("<II", lo & 0xFFFFFFFF, hi & 0xFFFFFFFF))[0]
                elif self.r.abi == "sysv":
                    v = self.r.xmm_double(self._xmm_next)
                    self._xmm_next += 1
                else:
                    raw = self.arg(k)
                    k += 1
                    v = struct.unpack("<d", struct.pack("<Q", raw & 0xFFFFFFFFFFFFFFFF))[0]
                c = conv if conv not in "aA" else "e"
                out.append((spec + c) % v)
            elif conv == "n":
                k += 1
        return "".join(out)

    def _printf_like(self, name: str, fmt_index: int) -> str:
        self._xmm_next = 0
        p = self.ptr(fmt_index, name, "format")
        return self.format(self.cstr(p), fmt_index + 1, name)

    # ------------------------------------------------------------------ input
    def read_token(self) -> str | None:
        s = self.r.stdin
        i = 0
        while i < len(s) and s[i].isspace():
            i += 1
        if i >= len(s):
            self.r.stdin = ""
            return None
        j = i
        while j < len(s) and not s[j].isspace():
            j += 1
        tok = s[i:j]
        self.r.stdin = s[j:]
        return tok

    def read_line(self, keep_newline: bool = True) -> str | None:
        s = self.r.stdin
        if not s:
            return None
        k = s.find("\n")
        if k < 0:
            line, rest = s, ""
        else:
            line, rest = s[:k + 1], s[k + 1:]
        self.r.stdin = rest
        return line if keep_newline else line.rstrip("\r\n")

    def scanf(self, name: str, fmt_index: int) -> int:
        fmt = self.cstr(self.ptr(fmt_index, name, "format"))
        k = fmt_index + 1
        count = 0
        for m in re.finditer(r"%(\*)?(\d+)?(hh|h|ll|l|I64|L|z|q)?([diouxXcsfeEgG%\[])", fmt):
            skip, width, length, conv = m.groups()
            if conv == "%":
                continue
            if conv == "c":
                if not self.r.stdin:
                    self.r.input_short(name)
                    return count or -1
                ch, self.r.stdin = self.r.stdin[0], self.r.stdin[1:]
                tok = ch
            else:
                tok = self.read_token()
                if tok is None:
                    self.r.input_short(name)
                    return count or -1
            if skip:
                continue
            what = ("a number variable", "متغير رقمي") if conv not in "sc[" else ("a buffer", "مخزن (buffer)")
            size = {"hh": 1, "h": 2, "ll": 8, "I64": 8, "q": 8, "z": self.r.bits // 8, "L": 8}.get(length or "", 4)
            if self.r.abi == "sysv" and length == "l":
                size = 8
            if conv in "feEgG":
                size = 8 if length in ("l", "L") else 4
            p = self.arg(k)
            if not self.r.valid(p, 1):
                self.r.bad_pointer(name, f"%{conv} (argument {k + 1})", k, p, what[0], what[1], self.arg_loc(k),
                                   self.arg_reg(k))
                raise StopRun()
            k += 1
            if conv in "di":
                try:
                    v = int(tok, 0) if conv == "i" else int(re.match(r"[-+]?\d+", tok).group(0))
                except (ValueError, AttributeError):
                    return count
                self.write(p, (v & ((1 << (8 * size)) - 1)).to_bytes(size, "little"))
            elif conv in "uoxX":
                try:
                    v = int(tok, 16 if conv in "xX" else 8 if conv == "o" else 10)
                except ValueError:
                    return count
                self.write(p, (v & ((1 << (8 * size)) - 1)).to_bytes(size, "little"))
            elif conv in "feEgG":
                try:
                    v = float(tok)
                except ValueError:
                    return count
                self.write(p, struct.pack("<d" if size == 8 else "<f", v))
            elif conv == "c":
                self.write(p, tok.encode("cp1252", errors="replace")[:1])
            else:
                if width:
                    tok = tok[:int(width)]
                self.write(p, tok.encode("cp1252", errors="replace") + b"\0")
            count += 1
        return count

    # ------------------------------------------------------------------ dispatch
    def call(self, name: str) -> None:
        n = plain(name)
        key = n.lower()
        fn = getattr(self, "f_" + key, None)
        if fn is None and key.endswith(("a", "w")) and getattr(self, "f_" + key[:-1], None):
            fn = getattr(self, "f_" + key[:-1])
        if fn is None:
            self.r.log_call(n, "", "0 (not simulated)")
            self.r.unknown_extern(n)
            self.ret(0)
            return
        res = fn()
        if res is None:
            res = 0
        self.ret(res)

    # -- console output
    def f_printf(self):
        s = self._printf_like("printf", 0)
        self.r.out(s)
        self.r.log_call("printf", repr(s)[:80], str(len(s)))
        return len(s)

    def f_wprintf(self):
        return self.f_printf()

    def f_puts(self):
        s = self.cstr(self.ptr(0, "puts", "str"))
        self.r.out(s + "\n")
        self.r.log_call("puts", repr(s)[:80], "1")
        return 1

    def f_putchar(self):
        c = self.arg(0) & 0xFF
        self.r.out(chr(c))
        return c

    def f_fputs(self):
        s = self.cstr(self.ptr(0, "fputs", "str"))
        self.r.out(s)
        return 1

    def f_sprintf(self):
        buf = self.ptr(0, "sprintf", "buffer", "a buffer", "مخزن (buffer)")
        s = self._printf_like("sprintf", 1)
        self.write(buf, s.encode("cp1252", errors="replace") + b"\0")
        self.r.log_call("sprintf", repr(s)[:80], str(len(s)))
        return len(s)

    def f_wsprintf(self):
        return self.f_sprintf()

    def f_snprintf(self):
        buf = self.ptr(0, "snprintf", "buffer", "a buffer", "مخزن (buffer)", null_ok=True)
        size = self.arg(1)
        s = self._printf_like("snprintf", 2)
        if buf and size:
            self.write(buf, s.encode("cp1252", errors="replace")[:size - 1] + b"\0")
        return len(s)

    def f__snprintf(self):
        return self.f_snprintf()

    def f_fflush(self):
        return 0

    def f_setvbuf(self):
        return 0

    def f___acrt_iob_func(self):
        return self.r.HEAP_BASE + 0x100 + 0x30 * (self.arg(0) & 3)

    def f_fprintf(self):
        s = self._printf_like("fprintf", 1)
        self.r.out(s)
        return len(s)

    # -- console input
    def f_scanf(self):
        c = self.scanf("scanf", 0)
        self.r.log_call("scanf", "", str(c))
        return c & 0xFFFFFFFF if c < 0 else c

    def f_scanf_s(self):
        return self.f_scanf()

    def f_sscanf(self):
        src = self.cstr(self.ptr(0, "sscanf", "buffer"))
        saved = self.r.stdin
        self.r.stdin = src
        try:
            c = self.scanf("sscanf", 1)
        finally:
            self.r.stdin = saved
        return c & 0xFFFFFFFF if c < 0 else c

    def f_getchar(self):
        if not self.r.stdin:
            self.r.input_short("getchar")
            return 0xFFFFFFFF
        ch, self.r.stdin = self.r.stdin[0], self.r.stdin[1:]
        return ord(ch) & 0xFF

    def f__getch(self):
        return self.f_getchar()

    def f_getch(self):
        return self.f_getchar()

    def f_gets(self):
        buf = self.ptr(0, "gets", "buffer", "a buffer", "مخزن (buffer)")
        line = self.read_line(False)
        if line is None:
            self.r.input_short("gets")
            return 0
        self.write(buf, line.encode("cp1252", errors="replace") + b"\0")
        return buf

    def f_fgets(self):
        buf = self.ptr(0, "fgets", "buffer", "a buffer", "مخزن (buffer)")
        n = self.arg(1) & 0xFFFFFFFF
        line = self.read_line(True)
        if line is None:
            self.r.input_short("fgets")
            return 0
        self.write(buf, line.encode("cp1252", errors="replace")[:max(0, n - 1)] + b"\0")
        return buf

    # -- process
    def f_exit(self):
        self.r.finish("exit", _signed(self.arg(0), 32))
        raise StopRun()

    def f__exit(self):
        return self.f_exit()

    def f_exitprocess(self):
        code = _signed(self.arg(0), 32)
        self.r.log_call("ExitProcess", str(code), "-")
        self.r.finish("exit", code)
        raise StopRun()

    def f_abort(self):
        self.r.finish("exit", 3)
        raise StopRun()

    # -- strings / memory
    def f_strlen(self):
        return len(self.cstr(self.ptr(0, "strlen", "str")).encode("cp1252", errors="replace"))

    def f_lstrlen(self):
        return self.f_strlen()

    def f_strcpy(self):
        d = self.ptr(0, "strcpy", "dest", "a buffer", "مخزن (buffer)")
        s = self.cstr(self.ptr(1, "strcpy", "src"))
        self.write(d, s.encode("cp1252", errors="replace") + b"\0")
        return d

    def f_lstrcpy(self):
        return self.f_strcpy()

    def f_strcat(self):
        d = self.ptr(0, "strcat", "dest", "a buffer", "مخزن (buffer)")
        cur = self.cstr(d).encode("cp1252", errors="replace")
        s = self.cstr(self.ptr(1, "strcat", "src")).encode("cp1252", errors="replace")
        self.write(d + len(cur), s + b"\0")
        return d

    def f_lstrcat(self):
        return self.f_strcat()

    def f_strcmp(self):
        a = self.cstr(self.ptr(0, "strcmp", "s1"))
        b = self.cstr(self.ptr(1, "strcmp", "s2"))
        return 0 if a == b else (1 if a > b else 0xFFFFFFFF)

    def f_lstrcmp(self):
        return self.f_strcmp()

    def f_memset(self):
        n = self.arg(2)
        d = self.ptr(0, "memset", "dest", "a buffer", "مخزن (buffer)", size=max(1, n))
        self.write(d, bytes([self.arg(1) & 0xFF]) * n)
        return d

    def f_memcpy(self):
        n = self.arg(2)
        d = self.ptr(0, "memcpy", "dest", "a buffer", "مخزن (buffer)", size=max(1, n))
        s = self.ptr(1, "memcpy", "src", "a buffer", "مخزن (buffer)", size=max(1, n))
        self.write(d, self.r.read(s, n))
        return d

    def f_memmove(self):
        return self.f_memcpy()

    def f_atoi(self):
        s = self.cstr(self.ptr(0, "atoi", "str")).strip()
        m = re.match(r"[-+]?\d+", s)
        return (int(m.group(0)) if m else 0) & 0xFFFFFFFF

    def f_atol(self):
        return self.f_atoi()

    def f_abs(self):
        return abs(_signed(self.arg(0), 32))

    def f_toupper(self):
        return ord(chr(self.arg(0) & 0xFF).upper()[0]) & 0xFF

    def f_tolower(self):
        return ord(chr(self.arg(0) & 0xFF).lower()[0]) & 0xFF

    # -- heap
    def f_malloc(self):
        return self.alloc(self.arg(0))

    def f_calloc(self):
        n = (self.arg(0) & 0xFFFFFFFF) * (self.arg(1) & 0xFFFFFFFF)
        a = self.alloc(n)
        if a:
            self.write(a, bytes(n))
        return a

    def f_realloc(self):
        old = self.arg(0)
        n = self.arg(1)
        a = self.alloc(n)
        if old and a and self.r.valid(old, 1):
            self.write(a, self.r.read(old, min(n, max(0, self.r.HEAP_BASE + self.r.HEAP_SIZE - old))))
        return a

    def f_free(self):
        return 0

    def f_heapalloc(self):
        n = self.arg(2)
        a = self.alloc(n)
        if a:
            self.write(a, bytes(n))
        return a

    def f_getprocessheap(self):
        return 0x1000

    def f_heapfree(self):
        return 1

    def f_virtualalloc(self):
        return self.alloc(self.arg(1))

    # -- misc CRT
    def f_rand(self):
        self.rand_state = (self.rand_state * 214013 + 2531011) & 0xFFFFFFFF
        return (self.rand_state >> 16) & 0x7FFF

    def f_srand(self):
        self.rand_state = self.arg(0) & 0xFFFFFFFF
        return 0

    def f_time(self):
        t = 1_780_000_000
        p = self.arg(0)
        if p and self.r.valid(p, 8):
            self.write(p, t.to_bytes(8 if self.r.bits == 64 else 4, "little"))
        return t

    def f__time64(self):
        return self.f_time()

    def f_system(self):
        self.r.log_call("system", repr(self.cstr(self.arg(0)))[:60], "0 (not run)")
        return 0

    # -- Win32
    def f_getstdhandle(self):
        n = _signed(self.arg(0), 32)
        return {-10: 0x10, -11: 0x14, -12: 0x18}.get(n, 0xFFFFFFFFFFFFFFFF if self.r.bits == 64 else 0xFFFFFFFF)

    def f_writeconsole(self):
        n = self.arg(2) & 0xFFFFFFFF
        buf = self.ptr(1, "WriteConsoleA", "lpBuffer", size=max(1, n))
        data = self.r.read(buf, n)
        self.r.out(data.decode("cp1252", errors="replace"))
        pw = self.arg(3)
        if pw:
            if not self.r.valid(pw, 4):
                self.r.bad_pointer("WriteConsoleA", "lpNumberOfCharsWritten", 3, pw, "a DWORD variable",
                                   "متغير DWORD", self.arg_loc(3), self.arg_reg(3))
                raise StopRun()
            self.write(pw, n.to_bytes(4, "little"))
        self.r.log_call("WriteConsoleA", repr(data.decode("cp1252", errors="replace"))[:80], "1")
        return 1

    def f_writefile(self):
        return self.f_writeconsole()

    def f_readconsole(self):
        buf = self.ptr(1, "ReadConsoleA", "lpBuffer", "a buffer", "مخزن (buffer)")
        n = self.arg(2) & 0xFFFFFFFF
        line = self.read_line(True)
        if line is None:
            self.r.input_short("ReadConsoleA")
            line = ""
        data = line.replace("\n", "\r\n").encode("cp1252", errors="replace")[:n]
        self.write(buf, data)
        pr = self.arg(3)
        if pr and self.r.valid(pr, 4):
            self.write(pr, len(data).to_bytes(4, "little"))
        return 1

    def f_readfile(self):
        return self.f_readconsole()

    def f_getcomputername(self):
        buf = self.ptr(0, "GetComputerNameA", "lpBuffer", "a buffer", "مخزن (buffer)")
        psize = self.ptr(1, "GetComputerNameA", "nSize", "a DWORD variable", "متغير DWORD", size=4)
        name = b"RADIDE-SIM"
        self.write(buf, name + b"\0")
        self.write(psize, len(name).to_bytes(4, "little"))
        return 1

    def f_messagebox(self):
        text = self.cstr(self.ptr(1, "MessageBoxA", "lpText"))
        cap = self.cstr(self.ptr(2, "MessageBoxA", "lpCaption", null_ok=True)) if self.arg(2) else "Error"
        self.r.out(f"[MessageBox] {cap}: {text}\n")
        self.r.log_call("MessageBoxA", f"{cap!r}, {text!r}"[:80], "1 (IDOK)")
        return 1

    def f_messageboxw(self):
        text = self.cstr(self.ptr(1, "MessageBoxW", "lpText", size=2), wide=True)
        cap = self.cstr(self.arg(2), wide=True) if self.arg(2) else "Error"
        self.r.out(f"[MessageBox] {cap}: {text}\n")
        return 1

    def f_messagebeep(self):
        return 1

    def f_beep(self):
        return 1

    def f_sleep(self):
        return 0

    def f_gettickcount(self):
        return (self.r.steps // 1000) & 0xFFFFFFFF

    def f_gettickcount64(self):
        return self.r.steps // 1000

    def f_getmodulehandle(self):
        return 0x00400000

    def f_getlasterror(self):
        return 0

    def f_setlasterror(self):
        return 0

    def f_closehandle(self):
        return 1

    def f_setconsoletitle(self):
        return 1

    def f_setconsoletextattribute(self):
        return 1

    def f_freeconsole(self):
        return 1

    def f_allocconsole(self):
        return 1

    def f_getcommandline(self):
        a = self.alloc(16)
        self.write(a, b"program.exe\0")
        return a

    # ------------------------------------------------------------------ Linux system calls
    def syscall(self, number: int, a: list[int], x86: bool) -> int | None:
        """Linux system call *number* (x86-64 numbering, or i386 when *x86*). None = unknown."""
        write_n, read_n, exit_ns = (4, 3, (1, 252)) if x86 else (1, 0, (60, 231))
        if number == write_n:
            fd, buf, n = a[0], a[1], a[2] & 0xFFFFFFFF
            if not self.r.valid(buf, max(1, n)):
                self.r.bad_pointer("write", "buf", 1, buf, "a buffer", "مخزن (buffer)",
                                   "ECX" if x86 else "RSI", "ecx" if x86 else "rsi")
                raise StopRun()
            data = self.r.read(buf, n).decode("utf-8", errors="replace")
            if fd in (1, 2):
                self.r.out(data)
            self.r.log_call("sys_write", f"fd={fd}, {data!r}"[:80], str(n))
            return n
        if number == read_n:
            buf, n = a[1], a[2] & 0xFFFFFFFF
            line = self.read_line(True)
            if line is None:
                self.r.input_short("sys_read")
                return 0
            data = line.encode("utf-8")[:n]
            if not self.r.valid(buf, max(1, len(data))):
                self.r.bad_pointer("read", "buf", 1, buf, "a buffer", "مخزن (buffer)",
                                   "ECX" if x86 else "RSI", "ecx" if x86 else "rsi")
                raise StopRun()
            self.write(buf, data)
            return len(data)
        if number in exit_ns:
            self.r.log_call("sys_exit", str(_signed(a[0], 32)), "-")
            self.r.finish("exit", _signed(a[0], 32))
            raise StopRun()
        return None


def _signed(v: int, bits: int) -> int:
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v
