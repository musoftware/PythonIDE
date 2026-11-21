"""An Intel 8086 CPU (with the 80186 extras courses meet: push imm, pusha/popa, shifts by an immediate,
imul imm, enter/leave, ins/outs) written from the published instruction semantics.

    cpu = CPU(memory)                  # memory: bytearray of 1 MB (+ 64 KB guard)
    cpu.step()                         # one instruction (a REP string instruction runs all its iterations)

Interrupt services implemented in Python use the reserved opcode ``F1 nn``: the IVT points each vector to a
tiny ROM stub ``F1 nn CF`` (hook, IRET), so programs can still hook vectors themselves. ``cpu.hook(n)``
handles the service; it may set ``cpu.retry`` to run the hook again later (an input service waiting for a key).
Every memory write goes through ``wb`` so the debugger can keep an undo log (``cpu.undo``) for reverse steps.
"""
from __future__ import annotations

CF, PF, AF, ZF, SF, TF, IF, DF, OF = 0x1, 0x4, 0x10, 0x40, 0x80, 0x100, 0x200, 0x400, 0x800
FLAG_NAMES = (("OF", OF), ("DF", DF), ("IF", IF), ("TF", TF), ("SF", SF), ("ZF", ZF), ("AF", AF), ("PF", PF),
              ("CF", CF))
PARITY = bytes(1 if bin(i).count("1") % 2 == 0 else 0 for i in range(256))
REG16_NAMES = ("AX", "CX", "DX", "BX", "SP", "BP", "SI", "DI")
REG8_NAMES = ("AL", "CL", "DL", "BL", "AH", "CH", "DH", "BH")
SREG_NAMES = ("ES", "CS", "SS", "DS")
AX, CX, DX, BX, SP, BP, SI, DI = range(8)
ES, CS, SS, DS = range(4)
MEM_SIZE = 0x100000


class CPUError(Exception):
    def __init__(self, code: str, **args):
        super().__init__(code)
        self.code = code
        self.args_ = args


def _s8(v: int) -> int:
    return v - 0x100 if v & 0x80 else v


def _s16(v: int) -> int:
    return v - 0x10000 if v & 0x8000 else v


class CPU:
    def __init__(self, mem: bytearray | None = None):
        self.mem = mem if mem is not None else bytearray(MEM_SIZE + 0x10000)
        self.r = [0] * 8
        self.s = [0] * 4
        self.ip = 0
        self.flags = 0xF002
        self.hook = None             # callable(n): Python interrupt service for "F1 n"
        self.port_in = None          # callable(port, w) -> value
        self.port_out = None         # callable(port, value, w)
        self.undo: list | None = None
        self.retry = False
        self.halted = False
        self.video_dirty = True
        self.seg_ovr = -1
        self.rep = 0
        self.cycles = 0              # instructions executed
        self.op_ip = 0               # IP of the instruction being executed
        self.op_cs = 0
        # decoded ModRM
        self.ea_reg = False
        self.ea_rm = 0
        self.ea_seg = 0
        self.ea_off = 0
        self._table = [self._bad] * 256
        self._build()

    # ================================================================== registers
    def get8(self, r: int) -> int:
        return self.r[r] & 0xFF if r < 4 else self.r[r - 4] >> 8

    def set8(self, r: int, v: int) -> None:
        if r < 4:
            self.r[r] = (self.r[r] & 0xFF00) | (v & 0xFF)
        else:
            self.r[r - 4] = (self.r[r - 4] & 0x00FF) | ((v & 0xFF) << 8)

    def flag(self, f: int) -> bool:
        return bool(self.flags & f)

    def set_flag(self, f: int, on) -> None:
        if on:
            self.flags |= f
        else:
            self.flags &= ~f

    # ================================================================== memory
    def rb(self, seg: int, off: int) -> int:
        return self.mem[((seg << 4) + (off & 0xFFFF)) & 0xFFFFF]

    def rw(self, seg: int, off: int) -> int:
        base = seg << 4
        m = self.mem
        return m[(base + (off & 0xFFFF)) & 0xFFFFF] | (m[(base + ((off + 1) & 0xFFFF)) & 0xFFFFF] << 8)

    def wb(self, seg: int, off: int, v: int) -> None:
        a = ((seg << 4) + (off & 0xFFFF)) & 0xFFFFF
        if self.undo is not None:
            self.undo.append((a, self.mem[a]))
        self.mem[a] = v & 0xFF
        if 0xA0000 <= a < 0xC0000:
            self.video_dirty = True

    def ww(self, seg: int, off: int, v: int) -> None:
        self.wb(seg, off, v)
        self.wb(seg, off + 1, v >> 8)

    def write_linear(self, a: int, v: int) -> None:
        a &= 0xFFFFF
        if self.undo is not None:
            self.undo.append((a, self.mem[a]))
        self.mem[a] = v & 0xFF
        if 0xA0000 <= a < 0xC0000:
            self.video_dirty = True

    def fetch8(self) -> int:
        v = self.mem[((self.s[CS] << 4) + self.ip) & 0xFFFFF]
        self.ip = (self.ip + 1) & 0xFFFF
        return v

    def fetch16(self) -> int:
        lo = self.fetch8()
        return lo | (self.fetch8() << 8)

    def push(self, v: int) -> None:
        sp = (self.r[SP] - 2) & 0xFFFF
        self.r[SP] = sp
        self.ww(self.s[SS], sp, v)

    def pop(self) -> int:
        sp = self.r[SP]
        v = self.rw(self.s[SS], sp)
        self.r[SP] = (sp + 2) & 0xFFFF
        return v

    # ================================================================== ModRM
    def modrm(self) -> int:
        """Decode a ModRM byte (and displacement); return the reg field."""
        b = self.fetch8()
        mod, reg, rm = b >> 6, (b >> 3) & 7, b & 7
        if mod == 3:
            self.ea_reg = True
            self.ea_rm = rm
            return reg
        self.ea_reg = False
        r = self.r
        seg = DS
        if rm == 0:
            off = r[BX] + r[SI]
        elif rm == 1:
            off = r[BX] + r[DI]
        elif rm == 2:
            off = r[BP] + r[SI]
            seg = SS
        elif rm == 3:
            off = r[BP] + r[DI]
            seg = SS
        elif rm == 4:
            off = r[SI]
        elif rm == 5:
            off = r[DI]
        elif rm == 6:
            if mod == 0:
                off = self.fetch16()
            else:
                off = r[BP]
                seg = SS
        else:
            off = r[BX]
        if mod == 1:
            off += _s8(self.fetch8())
        elif mod == 2:
            off += self.fetch16()
        self.ea_off = off & 0xFFFF
        self.ea_seg = self.s[self.seg_ovr if self.seg_ovr >= 0 else seg]
        return reg

    def rm_read(self, w: int) -> int:
        if self.ea_reg:
            return self.r[self.ea_rm] if w else self.get8(self.ea_rm)
        return self.rw(self.ea_seg, self.ea_off) if w else self.rb(self.ea_seg, self.ea_off)

    def rm_write(self, w: int, v: int) -> None:
        if self.ea_reg:
            if w:
                self.r[self.ea_rm] = v & 0xFFFF
            else:
                self.set8(self.ea_rm, v)
        elif w:
            self.ww(self.ea_seg, self.ea_off, v)
        else:
            self.wb(self.ea_seg, self.ea_off, v)

    def reg_read(self, reg: int, w: int) -> int:
        return self.r[reg] if w else self.get8(reg)

    def reg_write(self, reg: int, w: int, v: int) -> None:
        if w:
            self.r[reg] = v & 0xFFFF
        else:
            self.set8(reg, v)

    def data_seg(self) -> int:
        return self.s[self.seg_ovr if self.seg_ovr >= 0 else DS]

    # ================================================================== flags / ALU
    def szp(self, r: int, w: int) -> None:
        f = self.flags & ~(ZF | SF | PF)
        if r == 0:
            f |= ZF
        if r & (0x8000 if w else 0x80):
            f |= SF
        if PARITY[r & 0xFF]:
            f |= PF
        self.flags = f

    def alu(self, n: int, a: int, b: int, w: int) -> int:
        mask = 0xFFFF if w else 0xFF
        sign = 0x8000 if w else 0x80
        f = self.flags & ~(CF | PF | AF | ZF | SF | OF)
        if n == 0 or n == 2:                     # add / adc
            r = a + b + (self.flags & CF if n == 2 else 0)
            if r > mask:
                f |= CF
            r &= mask
            if (a ^ r) & (b ^ r) & sign:
                f |= OF
            if (a ^ b ^ r) & 0x10:
                f |= AF
        elif n == 5 or n == 7 or n == 3:         # sub / cmp / sbb
            r = a - b - (self.flags & CF if n == 3 else 0)
            if r < 0:
                f |= CF
            r &= mask
            if (a ^ b) & (a ^ r) & sign:
                f |= OF
            if (a ^ b ^ r) & 0x10:
                f |= AF
        elif n == 1:
            r = a | b
        elif n == 4:
            r = a & b
        else:
            r = a ^ b
        if r == 0:
            f |= ZF
        if r & sign:
            f |= SF
        if PARITY[r & 0xFF]:
            f |= PF
        self.flags = f
        return r

    def inc_dec(self, v: int, w: int, dec: bool) -> int:
        cf = self.flags & CF
        r = self.alu(5 if dec else 0, v, 1, w)
        self.flags = (self.flags & ~CF) | cf
        return r

    def shift(self, n: int, v: int, count: int, w: int) -> int:
        bits = 16 if w else 8
        mask = 0xFFFF if w else 0xFF
        sign = 0x8000 if w else 0x80
        count &= 0x1F
        if count == 0:
            return v
        f = self.flags
        cf = f & CF
        if n == 0:                                  # ROL
            for _ in range(count):
                cf = 1 if v & sign else 0
                v = ((v << 1) | cf) & mask
            f = (f & ~(CF | OF)) | cf | (OF if (bool(v & sign) ^ bool(cf)) else 0)
        elif n == 1:                                # ROR
            for _ in range(count):
                cf = v & 1
                v = (v >> 1) | (cf << (bits - 1))
            f = (f & ~(CF | OF)) | cf | (OF if (bool(v & sign) ^ bool(v & (sign >> 1))) else 0)
        elif n == 2:                                # RCL
            for _ in range(count):
                out = 1 if v & sign else 0
                v = ((v << 1) | cf) & mask
                cf = out
            f = (f & ~(CF | OF)) | cf | (OF if (bool(v & sign) ^ bool(cf)) else 0)
        elif n == 3:                                # RCR
            for _ in range(count):
                out = v & 1
                v = (v >> 1) | (cf << (bits - 1))
                cf = out
            f = (f & ~(CF | OF)) | cf | (OF if (bool(v & sign) ^ bool(v & (sign >> 1))) else 0)
        else:
            orig = v
            if n in (4, 6):                         # SHL / SAL
                cf = (v >> (bits - count)) & 1 if count <= bits else 0
                v = (v << count) & mask
                of = bool(v & sign) ^ bool(cf)
            elif n == 5:                            # SHR
                cf = (v >> (count - 1)) & 1 if count <= bits else 0
                v = v >> count if count < bits else 0
                of = bool(orig & sign)
            else:                                   # SAR
                sv = _s16(v) if w else _s8(v)
                cf = (sv >> min(count - 1, bits)) & 1
                v = (sv >> min(count, bits)) & mask
                of = False
            f = (f & ~(CF | OF | AF)) | cf | (OF if of else 0)
            self.flags = f
            self.szp(v, w)
            return v
        self.flags = f
        return v

    # ================================================================== interrupts
    def interrupt(self, n: int) -> None:
        self.push(self.flags | 0xF002)
        self.flags &= ~(IF | TF)
        self.push(self.s[CS])
        self.push(self.ip)
        self.ip = self.rw(0, n * 4)
        self.s[CS] = self.rw(0, n * 4 + 2)

    # ================================================================== execution
    def step(self) -> None:
        self.seg_ovr = -1
        self.rep = 0
        self.op_cs = self.s[CS]
        self.op_ip = self.ip
        table = self._table
        while True:
            op = self.fetch8()
            if op == 0x26:
                self.seg_ovr = ES
            elif op == 0x2E:
                self.seg_ovr = CS
            elif op == 0x36:
                self.seg_ovr = SS
            elif op == 0x3E:
                self.seg_ovr = DS
            elif op == 0xF3 or op == 0xF2:
                self.rep = op
            elif op == 0xF0:
                pass
            else:
                break
        self.cycles += 1
        table[op](op)

    def _bad(self, op: int) -> None:
        self.ip = self.op_ip
        raise CPUError("R-BAD-OPCODE", op=f"{op:02X}h", addr=f"{self.op_cs:04X}:{self.op_ip:04X}")

    def _build(self) -> None:
        t = self._table
        for n in range(8):
            for k in range(6):
                t[n * 8 + k] = self._op_alu
        for op, fn in ((0x06, self._push_sreg), (0x0E, self._push_sreg), (0x16, self._push_sreg),
                       (0x1E, self._push_sreg), (0x07, self._pop_sreg), (0x17, self._pop_sreg),
                       (0x1F, self._pop_sreg), (0x27, self._daa), (0x2F, self._das), (0x37, self._aaa),
                       (0x3F, self._aas)):
            t[op] = fn
        for k in range(8):
            t[0x40 + k] = self._inc_r16
            t[0x48 + k] = self._dec_r16
            t[0x50 + k] = self._push_r16
            t[0x58 + k] = self._pop_r16
            t[0x90 + k] = self._xchg_ax
            t[0xB0 + k] = self._mov_r8_imm
            t[0xB8 + k] = self._mov_r16_imm
        t[0x60] = self._pusha
        t[0x61] = self._popa
        t[0x68] = self._push_imm16
        t[0x69] = self._imul_imm
        t[0x6A] = self._push_imm8
        t[0x6B] = self._imul_imm
        for k in range(0x6C, 0x70):
            t[k] = self._insouts
        for k in range(0x70, 0x80):
            t[k] = self._jcc
        for k in range(0x80, 0x84):
            t[k] = self._grp1
        t[0x84] = t[0x85] = self._test_rm_r
        t[0x86] = t[0x87] = self._xchg_rm
        for k in range(0x88, 0x8C):
            t[k] = self._mov_rm
        t[0x8C] = self._mov_rm_sreg
        t[0x8D] = self._lea
        t[0x8E] = self._mov_sreg_rm
        t[0x8F] = self._pop_rm
        t[0x98] = self._cbw
        t[0x99] = self._cwd
        t[0x9A] = self._call_far
        t[0x9B] = self._nop
        t[0x9C] = self._pushf
        t[0x9D] = self._popf
        t[0x9E] = self._sahf
        t[0x9F] = self._lahf
        for k in range(0xA0, 0xA4):
            t[k] = self._mov_moffs
        for k in (0xA4, 0xA5, 0xA6, 0xA7, 0xAA, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF):
            t[k] = self._string
        t[0xA8] = t[0xA9] = self._test_acc
        t[0xC0] = t[0xC1] = self._shift_imm
        t[0xC2] = self._ret_imm
        t[0xC3] = self._ret
        t[0xC4] = t[0xC5] = self._lxs
        t[0xC6] = t[0xC7] = self._mov_rm_imm
        t[0xC8] = self._enter
        t[0xC9] = self._leave
        t[0xCA] = self._retf_imm
        t[0xCB] = self._retf
        t[0xCC] = self._int3
        t[0xCD] = self._int
        t[0xCE] = self._into
        t[0xCF] = self._iret
        for k in range(0xD0, 0xD4):
            t[k] = self._shift
        t[0xD4] = self._aam
        t[0xD5] = self._aad
        t[0xD6] = self._salc
        t[0xD7] = self._xlat
        for k in range(0xD8, 0xE0):
            t[k] = self._esc
        for k in range(0xE0, 0xE4):
            t[k] = self._loop
        for k in (0xE4, 0xE5, 0xEC, 0xED):
            t[k] = self._in
        for k in (0xE6, 0xE7, 0xEE, 0xEF):
            t[k] = self._out
        t[0xE8] = self._call_near
        t[0xE9] = self._jmp_near
        t[0xEA] = self._jmp_far
        t[0xEB] = self._jmp_short
        t[0xF1] = self._hook
        t[0xF4] = self._hlt
        t[0xF5] = self._cmc
        t[0xF6] = t[0xF7] = self._grp3
        for k in range(0xF8, 0xFE):
            t[k] = self._flagop
        t[0xFE] = self._grp4
        t[0xFF] = self._grp5

    # ------------------------------------------------------------------ handlers
    def _op_alu(self, op: int) -> None:
        n = (op >> 3) & 7
        k = op & 7
        w = op & 1
        if k < 4:
            reg = self.modrm()
            if k < 2:            # rm, reg
                a = self.rm_read(w)
                r = self.alu(n, a, self.reg_read(reg, w), w)
                if n != 7:
                    self.rm_write(w, r)
            else:                # reg, rm
                a = self.reg_read(reg, w)
                r = self.alu(n, a, self.rm_read(w), w)
                if n != 7:
                    self.reg_write(reg, w, r)
        else:
            if w:
                r = self.alu(n, self.r[AX], self.fetch16(), 1)
                if n != 7:
                    self.r[AX] = r
            else:
                r = self.alu(n, self.r[AX] & 0xFF, self.fetch8(), 0)
                if n != 7:
                    self.set8(0, r)

    def _push_sreg(self, op: int) -> None:
        self.push(self.s[(op >> 3) & 3])

    def _pop_sreg(self, op: int) -> None:
        self.s[(op >> 3) & 3] = self.pop()

    def _daa(self, op: int) -> None:
        al = self.r[AX] & 0xFF
        old_al, old_cf = al, self.flags & CF
        f = self.flags & ~CF
        if (al & 0x0F) > 9 or self.flags & AF:
            al += 6
            f |= AF
        else:
            f &= ~AF
        if old_al > 0x99 or old_cf:
            al += 0x60
            f |= CF
        self.flags = f
        self.set8(0, al)
        self.szp(al & 0xFF, 0)

    def _das(self, op: int) -> None:
        al = self.r[AX] & 0xFF
        old_al, old_cf = al, self.flags & CF
        f = self.flags & ~CF
        if (al & 0x0F) > 9 or self.flags & AF:
            al -= 6
            f |= AF
        else:
            f &= ~AF
        if old_al > 0x99 or old_cf:
            al -= 0x60
            f |= CF
        self.flags = f
        self.set8(0, al & 0xFF)
        self.szp(al & 0xFF, 0)

    def _aaa(self, op: int) -> None:
        ax = self.r[AX]
        if (ax & 0x0F) > 9 or self.flags & AF:
            ax = (ax + 0x106) & 0xFFFF
            self.flags |= AF | CF
        else:
            self.flags &= ~(AF | CF)
        self.r[AX] = ax & 0xFF0F

    def _aas(self, op: int) -> None:
        ax = self.r[AX]
        if (ax & 0x0F) > 9 or self.flags & AF:
            al = ((ax & 0xFF) - 6) & 0xFF
            ah = ((ax >> 8) - 1) & 0xFF
            ax = (ah << 8) | al
            self.flags |= AF | CF
        else:
            self.flags &= ~(AF | CF)
        self.r[AX] = ax & 0xFF0F

    def _inc_r16(self, op: int) -> None:
        k = op & 7
        self.r[k] = self.inc_dec(self.r[k], 1, False)

    def _dec_r16(self, op: int) -> None:
        k = op & 7
        self.r[k] = self.inc_dec(self.r[k], 1, True)

    def _push_r16(self, op: int) -> None:
        k = op & 7
        if k == SP:                       # 8086: pushes the decremented SP
            sp = (self.r[SP] - 2) & 0xFFFF
            self.r[SP] = sp
            self.ww(self.s[SS], sp, sp)
        else:
            self.push(self.r[k])

    def _pop_r16(self, op: int) -> None:
        v = self.pop()
        self.r[op & 7] = v

    def _xchg_ax(self, op: int) -> None:
        k = op & 7
        if k:
            self.r[AX], self.r[k] = self.r[k], self.r[AX]

    def _mov_r8_imm(self, op: int) -> None:
        self.set8(op & 7, self.fetch8())

    def _mov_r16_imm(self, op: int) -> None:
        self.r[op & 7] = self.fetch16()

    def _pusha(self, op: int) -> None:
        sp = self.r[SP]
        for k in (AX, CX, DX, BX):
            self.push(self.r[k])
        self.push(sp)
        for k in (BP, SI, DI):
            self.push(self.r[k])

    def _popa(self, op: int) -> None:
        for k in (DI, SI, BP):
            self.r[k] = self.pop()
        self.pop()
        for k in (BX, DX, CX, AX):
            self.r[k] = self.pop()

    def _push_imm16(self, op: int) -> None:
        self.push(self.fetch16())

    def _push_imm8(self, op: int) -> None:
        self.push(_s8(self.fetch8()) & 0xFFFF)

    def _imul_imm(self, op: int) -> None:
        reg = self.modrm()
        a = _s16(self.rm_read(1))
        b = _s16(self.fetch16()) if op == 0x69 else _s8(self.fetch8())
        r = a * b
        self.r[reg] = r & 0xFFFF
        over = not -0x8000 <= r <= 0x7FFF
        self.set_flag(CF, over)
        self.set_flag(OF, over)

    def _insouts(self, op: int) -> None:
        w = op & 1
        step = (2 if w else 1) * (-1 if self.flags & DF else 1)
        while True:
            if self.rep and self.r[CX] == 0:
                return
            if op < 0x6E:
                v = self.port_in(self.r[DX], w) if self.port_in else 0xFFFF
                (self.ww if w else self.wb)(self.s[ES], self.r[DI], v)
                self.r[DI] = (self.r[DI] + step) & 0xFFFF
            else:
                seg = self.data_seg()
                v = self.rw(seg, self.r[SI]) if w else self.rb(seg, self.r[SI])
                if self.port_out:
                    self.port_out(self.r[DX], v, w)
                self.r[SI] = (self.r[SI] + step) & 0xFFFF
            if not self.rep:
                return
            self.r[CX] = (self.r[CX] - 1) & 0xFFFF

    def cond(self, c: int) -> bool:
        f = self.flags
        if c == 0:
            return bool(f & OF)
        if c == 1:
            return not f & OF
        if c == 2:
            return bool(f & CF)
        if c == 3:
            return not f & CF
        if c == 4:
            return bool(f & ZF)
        if c == 5:
            return not f & ZF
        if c == 6:
            return bool(f & (CF | ZF))
        if c == 7:
            return not f & (CF | ZF)
        if c == 8:
            return bool(f & SF)
        if c == 9:
            return not f & SF
        if c == 10:
            return bool(f & PF)
        if c == 11:
            return not f & PF
        lt = bool(f & SF) != bool(f & OF)
        if c == 12:
            return lt
        if c == 13:
            return not lt
        if c == 14:
            return lt or bool(f & ZF)
        return not lt and not f & ZF

    def _jcc(self, op: int) -> None:
        d = _s8(self.fetch8())
        if self.cond(op & 0x0F):
            self.ip = (self.ip + d) & 0xFFFF

    def _grp1(self, op: int) -> None:
        w = op & 1
        n = self.modrm()
        a = self.rm_read(w)
        if op == 0x81:
            b = self.fetch16()
        elif op == 0x83:
            b = _s8(self.fetch8()) & 0xFFFF
        else:
            b = self.fetch8()
        r = self.alu(n, a, b, w)
        if n != 7:
            self.rm_write(w, r)

    def _test_rm_r(self, op: int) -> None:
        w = op & 1
        reg = self.modrm()
        self.alu(4, self.rm_read(w), self.reg_read(reg, w), w)

    def _xchg_rm(self, op: int) -> None:
        w = op & 1
        reg = self.modrm()
        a = self.rm_read(w)
        self.rm_write(w, self.reg_read(reg, w))
        self.reg_write(reg, w, a)

    def _mov_rm(self, op: int) -> None:
        w = op & 1
        reg = self.modrm()
        if op & 2:
            self.reg_write(reg, w, self.rm_read(w))
        else:
            self.rm_write(w, self.reg_read(reg, w))

    def _mov_rm_sreg(self, op: int) -> None:
        reg = self.modrm()
        self.rm_write(1, self.s[reg & 3])

    def _lea(self, op: int) -> None:
        reg = self.modrm()
        if self.ea_reg:
            raise CPUError("R-BAD-OPCODE", op="8Dh (lea reg)", addr=f"{self.op_cs:04X}:{self.op_ip:04X}")
        self.r[reg] = self.ea_off

    def _mov_sreg_rm(self, op: int) -> None:
        reg = self.modrm() & 3
        self.s[reg] = self.rm_read(1)

    def _pop_rm(self, op: int) -> None:
        self.modrm()
        v = self.pop()
        self.rm_write(1, v)

    def _cbw(self, op: int) -> None:
        al = self.r[AX] & 0xFF
        self.r[AX] = al | (0xFF00 if al & 0x80 else 0)

    def _cwd(self, op: int) -> None:
        self.r[DX] = 0xFFFF if self.r[AX] & 0x8000 else 0

    def _call_far(self, op: int) -> None:
        off = self.fetch16()
        seg = self.fetch16()
        self.push(self.s[CS])
        self.push(self.ip)
        self.s[CS], self.ip = seg, off

    def _nop(self, op: int) -> None:
        pass

    def _pushf(self, op: int) -> None:
        self.push((self.flags & 0x0FD5) | 0xF002)

    def _popf(self, op: int) -> None:
        self.flags = (self.pop() & 0x0FD5) | 0xF002

    def _sahf(self, op: int) -> None:
        self.flags = (self.flags & 0xFF00) | ((self.r[AX] >> 8) & 0xD5) | 0x02

    def _lahf(self, op: int) -> None:
        self.set8(4, (self.flags & 0xD5) | 0x02)

    def _mov_moffs(self, op: int) -> None:
        w = op & 1
        off = self.fetch16()
        seg = self.data_seg()
        if op < 0xA2:
            if w:
                self.r[AX] = self.rw(seg, off)
            else:
                self.set8(0, self.rb(seg, off))
        elif w:
            self.ww(seg, off, self.r[AX])
        else:
            self.wb(seg, off, self.r[AX])

    def _string(self, op: int) -> None:
        w = op & 1
        size = 2 if w else 1
        step = -size if self.flags & DF else size
        kind = op & 0xFE
        r = self.r
        src = self.data_seg()
        es = self.s[ES]
        rep = self.rep
        rd = self.rw if w else self.rb
        wr = self.ww if w else self.wb
        while True:
            if rep and r[CX] == 0:
                return
            if kind == 0xA4:                     # MOVS
                wr(es, r[DI], rd(src, r[SI]))
                r[SI] = (r[SI] + step) & 0xFFFF
                r[DI] = (r[DI] + step) & 0xFFFF
            elif kind == 0xA6:                   # CMPS
                self.alu(7, rd(src, r[SI]), rd(es, r[DI]), w)
                r[SI] = (r[SI] + step) & 0xFFFF
                r[DI] = (r[DI] + step) & 0xFFFF
            elif kind == 0xAA:                   # STOS
                wr(es, r[DI], r[AX] if w else r[AX] & 0xFF)
                r[DI] = (r[DI] + step) & 0xFFFF
            elif kind == 0xAC:                   # LODS
                if w:
                    r[AX] = rd(src, r[SI])
                else:
                    self.set8(0, rd(src, r[SI]))
                r[SI] = (r[SI] + step) & 0xFFFF
            else:                                # SCAS
                self.alu(7, r[AX] if w else r[AX] & 0xFF, rd(es, r[DI]), w)
                r[DI] = (r[DI] + step) & 0xFFFF
            if not rep:
                return
            r[CX] = (r[CX] - 1) & 0xFFFF
            if kind in (0xA6, 0xAE):
                zf = bool(self.flags & ZF)
                if (rep == 0xF3 and not zf) or (rep == 0xF2 and zf):
                    return

    def _test_acc(self, op: int) -> None:
        if op & 1:
            self.alu(4, self.r[AX], self.fetch16(), 1)
        else:
            self.alu(4, self.r[AX] & 0xFF, self.fetch8(), 0)

    def _shift_imm(self, op: int) -> None:
        w = op & 1
        n = self.modrm()
        v = self.rm_read(w)
        c = self.fetch8()
        self.rm_write(w, self.shift(n, v, c, w))

    def _shift(self, op: int) -> None:
        w = op & 1
        n = self.modrm()
        v = self.rm_read(w)
        c = (self.r[CX] & 0xFF) if op & 2 else 1
        self.rm_write(w, self.shift(n, v, c, w))

    def _ret_imm(self, op: int) -> None:
        n = self.fetch16()
        self.ip = self.pop()
        self.r[SP] = (self.r[SP] + n) & 0xFFFF

    def _ret(self, op: int) -> None:
        self.ip = self.pop()

    def _lxs(self, op: int) -> None:
        reg = self.modrm()
        if self.ea_reg:
            raise CPUError("R-BAD-OPCODE", op=f"{op:02X}h", addr=f"{self.op_cs:04X}:{self.op_ip:04X}")
        self.r[reg] = self.rw(self.ea_seg, self.ea_off)
        self.s[ES if op == 0xC4 else DS] = self.rw(self.ea_seg, self.ea_off + 2)

    def _mov_rm_imm(self, op: int) -> None:
        w = op & 1
        self.modrm()
        self.rm_write(w, self.fetch16() if w else self.fetch8())

    def _enter(self, op: int) -> None:
        size = self.fetch16()
        level = self.fetch8() & 0x1F
        self.push(self.r[BP])
        frame = self.r[SP]
        for _ in range(1, level):
            self.r[BP] = (self.r[BP] - 2) & 0xFFFF
            self.push(self.rw(self.s[SS], self.r[BP]))
        if level:
            self.push(frame)
        self.r[BP] = frame
        self.r[SP] = (self.r[SP] - size) & 0xFFFF

    def _leave(self, op: int) -> None:
        self.r[SP] = self.r[BP]
        self.r[BP] = self.pop()

    def _retf_imm(self, op: int) -> None:
        n = self.fetch16()
        self.ip = self.pop()
        self.s[CS] = self.pop()
        self.r[SP] = (self.r[SP] + n) & 0xFFFF

    def _retf(self, op: int) -> None:
        self.ip = self.pop()
        self.s[CS] = self.pop()

    def _int3(self, op: int) -> None:
        self.interrupt(3)

    def _int(self, op: int) -> None:
        self.interrupt(self.fetch8())

    def _into(self, op: int) -> None:
        if self.flags & OF:
            self.interrupt(4)

    def _iret(self, op: int) -> None:
        self.ip = self.pop()
        self.s[CS] = self.pop()
        self.flags = (self.pop() & 0x0FD5) | 0xF002

    def _aam(self, op: int) -> None:
        base = self.fetch8()
        if base == 0:
            self.ip = self.op_ip
            self.interrupt(0)
            return
        al = self.r[AX] & 0xFF
        self.r[AX] = ((al // base) << 8) | (al % base)
        self.szp(al % base, 0)

    def _aad(self, op: int) -> None:
        base = self.fetch8()
        ax = self.r[AX]
        al = ((ax >> 8) * base + (ax & 0xFF)) & 0xFF
        self.r[AX] = al
        self.szp(al, 0)

    def _salc(self, op: int) -> None:
        self.set8(0, 0xFF if self.flags & CF else 0)

    def _xlat(self, op: int) -> None:
        self.set8(0, self.rb(self.data_seg(), self.r[BX] + (self.r[AX] & 0xFF)))

    def _esc(self, op: int) -> None:
        self.modrm()                  # no FPU: the instruction is decoded and ignored

    def _loop(self, op: int) -> None:
        d = _s8(self.fetch8())
        if op == 0xE3:
            if self.r[CX] == 0:
                self.ip = (self.ip + d) & 0xFFFF
            return
        cx = (self.r[CX] - 1) & 0xFFFF
        self.r[CX] = cx
        if cx == 0:
            return
        zf = bool(self.flags & ZF)
        if op == 0xE2 or (op == 0xE1 and zf) or (op == 0xE0 and not zf):
            self.ip = (self.ip + d) & 0xFFFF

    def _in(self, op: int) -> None:
        w = op & 1
        port = self.fetch8() if op < 0xEC else self.r[DX]
        v = self.port_in(port, w) if self.port_in else 0xFFFF
        if w:
            self.r[AX] = v & 0xFFFF
        else:
            self.set8(0, v)

    def _out(self, op: int) -> None:
        w = op & 1
        port = self.fetch8() if op < 0xEC else self.r[DX]
        if self.port_out:
            self.port_out(port, self.r[AX] if w else self.r[AX] & 0xFF, w)

    def _call_near(self, op: int) -> None:
        d = self.fetch16()
        self.push(self.ip)
        self.ip = (self.ip + d) & 0xFFFF

    def _jmp_near(self, op: int) -> None:
        d = self.fetch16()
        self.ip = (self.ip + d) & 0xFFFF

    def _jmp_far(self, op: int) -> None:
        off = self.fetch16()
        seg = self.fetch16()
        self.s[CS], self.ip = seg, off

    def _jmp_short(self, op: int) -> None:
        d = _s8(self.fetch8())
        self.ip = (self.ip + d) & 0xFFFF

    def _hook(self, op: int) -> None:
        n = self.fetch8()
        self.retry = False
        if self.hook is not None:
            self.hook(n)
        if self.retry:
            self.ip = self.op_ip

    def _hlt(self, op: int) -> None:
        self.halted = True

    def _cmc(self, op: int) -> None:
        self.flags ^= CF

    def _flagop(self, op: int) -> None:
        f = {0xF8: (CF, 0), 0xF9: (CF, 1), 0xFA: (IF, 0), 0xFB: (IF, 1), 0xFC: (DF, 0), 0xFD: (DF, 1)}[op]
        self.set_flag(f[0], f[1])

    def _grp3(self, op: int) -> None:
        w = op & 1
        n = self.modrm()
        v = self.rm_read(w)
        if n in (0, 1):                                   # TEST rm, imm
            self.alu(4, v, self.fetch16() if w else self.fetch8(), w)
        elif n == 2:                                      # NOT
            self.rm_write(w, ~v)
        elif n == 3:                                      # NEG
            r = self.alu(5, 0, v, w)
            self.set_flag(CF, v != 0)
            self.rm_write(w, r)
        elif n == 4:                                      # MUL
            if w:
                r = self.r[AX] * v
                self.r[AX] = r & 0xFFFF
                self.r[DX] = r >> 16
                over = self.r[DX] != 0
            else:
                r = (self.r[AX] & 0xFF) * v
                self.r[AX] = r & 0xFFFF
                over = (r >> 8) != 0
            self.set_flag(CF, over)
            self.set_flag(OF, over)
            self.szp(r & (0xFFFF if w else 0xFF), w)
        elif n == 5:                                      # IMUL
            if w:
                r = _s16(self.r[AX]) * _s16(v)
                self.r[AX] = r & 0xFFFF
                self.r[DX] = (r >> 16) & 0xFFFF
                over = not -0x8000 <= r <= 0x7FFF
            else:
                r = _s8(self.r[AX] & 0xFF) * _s8(v)
                self.r[AX] = r & 0xFFFF
                over = not -0x80 <= r <= 0x7F
            self.set_flag(CF, over)
            self.set_flag(OF, over)
        elif n == 6:                                      # DIV
            if v == 0:
                return self._div_error()
            if w:
                num = (self.r[DX] << 16) | self.r[AX]
                q, rem = divmod(num, v)
                if q > 0xFFFF:
                    return self._div_error()
                self.r[AX], self.r[DX] = q, rem
            else:
                num = self.r[AX]
                q, rem = divmod(num, v)
                if q > 0xFF:
                    return self._div_error()
                self.r[AX] = (rem << 8) | q
        else:                                             # IDIV
            if v == 0:
                return self._div_error()
            if w:
                num = (self.r[DX] << 16) | self.r[AX]
                if num & 0x80000000:
                    num -= 1 << 32
                d = _s16(v)
                q = abs(num) // abs(d) * (1 if (num < 0) == (d < 0) else -1)
                rem = num - q * d
                if not -0x8000 <= q <= 0x7FFF:
                    return self._div_error()
                self.r[AX], self.r[DX] = q & 0xFFFF, rem & 0xFFFF
            else:
                num = _s16(self.r[AX])
                d = _s8(v)
                q = abs(num) // abs(d) * (1 if (num < 0) == (d < 0) else -1)
                rem = num - q * d
                if not -0x80 <= q <= 0x7F:
                    return self._div_error()
                self.r[AX] = ((rem & 0xFF) << 8) | (q & 0xFF)

    def _div_error(self) -> None:
        # 8086: the saved IP is the one after the instruction; we keep the start (easier to show the line)
        self.ip = self.op_ip
        self.interrupt(0)

    def _grp4(self, op: int) -> None:
        n = self.modrm()
        v = self.rm_read(0)
        if n == 0:
            self.rm_write(0, self.inc_dec(v, 0, False))
        elif n == 1:
            self.rm_write(0, self.inc_dec(v, 0, True))
        else:
            self._bad(op)

    def _grp5(self, op: int) -> None:
        n = self.modrm()
        if n == 0:
            self.rm_write(1, self.inc_dec(self.rm_read(1), 1, False))
        elif n == 1:
            self.rm_write(1, self.inc_dec(self.rm_read(1), 1, True))
        elif n == 2:                       # CALL near indirect
            target = self.rm_read(1)
            self.push(self.ip)
            self.ip = target
        elif n == 3:                       # CALL far indirect
            off = self.rw(self.ea_seg, self.ea_off)
            seg = self.rw(self.ea_seg, self.ea_off + 2)
            self.push(self.s[CS])
            self.push(self.ip)
            self.s[CS], self.ip = seg, off
        elif n == 4:
            self.ip = self.rm_read(1)
        elif n == 5:
            off = self.rw(self.ea_seg, self.ea_off)
            seg = self.rw(self.ea_seg, self.ea_off + 2)
            self.s[CS], self.ip = seg, off
        elif n == 6:
            self.push(self.rm_read(1))
        else:
            self._bad(op)
