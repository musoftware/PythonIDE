"""The DSKY (Display and Keyboard) state, decoded from the AGC's output channels - no Qt.

Channel 10 carries "relay words": bits 15-12 select one of 12 relay words, bit 11 is a sign / lamp bit and
bits 10-6 / 5-1 are two 5-bit digit codes. Channel 11 and Virtual AGC's channel 163 drive the lamps.

    m = DskyModel()
    m.channel(0o10, word)        # from the emulator or the yaAGC socket
    m.prog, m.verb, m.noun, m.r1, m.r2, m.r3   ->  "16", "+00012" ...
    m.lamps["OPR ERR"], m.summary()
"""
from __future__ import annotations

from .isa import DIGIT_CODES, DIGIT_OF

LAMPS = ["UPLINK ACTY", "NO ATT", "STBY", "KEY REL", "OPR ERR", "TEMP", "GIMBAL LOCK", "PROG", "RESTART",
         "TRACKER", "ALT", "VEL", "PRIO DISP", "NO DAP", "COMP ACTY", "AGC WARNING", "VN FLASH"]
CH11_LAMPS = {2: "COMP ACTY", 3: "UPLINK ACTY", 4: "TEMP", 5: "KEY REL", 6: "VN FLASH", 7: "OPR ERR"}
CH163_LAMPS = {1: "AGC WARNING", 4: "TEMP", 5: "KEY REL", 6: "VN FLASH", 7: "OPR ERR", 8: "RESTART", 9: "STBY"}
RELAY12_LAMPS = {1: "PRIO DISP", 2: "NO DAP", 3: "VEL", 4: "NO ATT", 5: "ALT", 6: "GIMBAL LOCK", 8: "TRACKER",
                 9: "PROG"}


class DskyModel:
    def __init__(self):
        self.clear()

    def clear(self) -> None:
        # 21 digit positions: prog 2, verb 2, noun 2, r1 5, r2 5, r3 5
        self.digits: dict[str, list[str]] = {"prog": [" "] * 2, "verb": [" "] * 2, "noun": [" "] * 2,
                                             "r1": [" "] * 5, "r2": [" "] * 5, "r3": [" "] * 5}
        self.signs = {"r1": [False, False], "r2": [False, False], "r3": [False, False]}    # [plus, minus]
        self.lamps = {name: False for name in LAMPS}
        self.writes = 0

    # ------------------------------------------------------------------ channels
    def channel(self, ch: int, value: int) -> bool:
        """Apply one output-channel write. True when the display changed."""
        value &= 0o77777
        if ch == 0o10:
            return self._relay(value)
        if ch == 0o11:
            return self._bits(value, CH11_LAMPS)
        if ch == 0o163:
            return self._bits(value, CH163_LAMPS)
        return False

    def _bits(self, value: int, table: dict) -> bool:
        changed = False
        for bit, name in table.items():
            on = bool(value & (1 << (bit - 1)))
            if self.lamps.get(name) != on:
                self.lamps[name] = on
                changed = True
        return changed

    def _relay(self, value: int) -> bool:
        self.writes += 1
        word = (value >> 11) & 0o17
        b = bool(value & 0o2000)
        c = DIGIT_CODES.get((value >> 5) & 0o37, "?") if (value >> 5) & 0o37 else " "
        d = DIGIT_CODES.get(value & 0o37, "?") if value & 0o37 else " "
        before = self.summary()
        dg, sg = self.digits, self.signs
        if word == 11:
            dg["prog"][0], dg["prog"][1] = c, d
        elif word == 10:
            dg["verb"][0], dg["verb"][1] = c, d
        elif word == 9:
            dg["noun"][0], dg["noun"][1] = c, d
        elif word == 8:
            dg["r1"][0] = d
        elif word == 7:
            sg["r1"][0] = b
            dg["r1"][1], dg["r1"][2] = c, d
        elif word == 6:
            sg["r1"][1] = b
            dg["r1"][3], dg["r1"][4] = c, d
        elif word == 5:
            sg["r2"][0] = b
            dg["r2"][0], dg["r2"][1] = c, d
        elif word == 4:
            sg["r2"][1] = b
            dg["r2"][2], dg["r2"][3] = c, d
        elif word == 3:
            dg["r2"][4] = c
            dg["r3"][0] = d
        elif word == 2:
            sg["r3"][0] = b
            dg["r3"][1], dg["r3"][2] = c, d
        elif word == 1:
            sg["r3"][1] = b
            dg["r3"][3], dg["r3"][4] = c, d
        elif word == 12:
            for bit, name in RELAY12_LAMPS.items():
                self.lamps[name] = bool(value & (1 << (bit - 1)))
            return True
        return self.summary() != before

    # ------------------------------------------------------------------ reading
    def _field(self, name: str) -> str:
        return "".join(self.digits[name])

    def sign(self, reg: str) -> str:
        plus, minus = self.signs[reg]
        return "+" if plus and not minus else "-" if minus and not plus else " "

    @property
    def prog(self) -> str:
        return self._field("prog")

    @property
    def verb(self) -> str:
        return self._field("verb")

    @property
    def noun(self) -> str:
        return self._field("noun")

    @property
    def r1(self) -> str:
        return self.sign("r1") + self._field("r1")

    @property
    def r2(self) -> str:
        return self.sign("r2") + self._field("r2")

    @property
    def r3(self) -> str:
        return self.sign("r3") + self._field("r3")

    def summary(self) -> str:
        on = [n for n in LAMPS if self.lamps.get(n)]
        return (f"PROG {self.prog}  VERB {self.verb}  NOUN {self.noun}  R1 {self.r1}  R2 {self.r2}  R3 {self.r3}"
                + (f"  [{', '.join(on)}]" if on else ""))

    def as_dict(self) -> dict:
        return {"prog": self.prog, "verb": self.verb, "noun": self.noun, "r1": self.r1, "r2": self.r2,
                "r3": self.r3, "lamps": [n for n in LAMPS if self.lamps.get(n)]}


def relay_word(word: int, left: str, right: str, sign: bool = False) -> int:
    """Encode one channel-10 relay word (for tests and the DSKY self-test)."""
    return (word << 11) | (0o2000 if sign else 0) | (DIGIT_OF.get(left, 0) << 5) | DIGIT_OF.get(right, 0)


__all__ = ["DskyModel", "LAMPS", "relay_word"]
