"""Generic serial-EEPROM dump recognition (no Qt).

A dump read from a 24Cxx (I2C), 93Cxx (Microwire) or 95xxx (SPI) EEPROM is just its memory array, so the size is
the only reliable hint. This module names the chip families that have that size and offers the byte-order views
an EEPROM programmer may need (16-bit word swap for 93Cxx chips read in x16 organisation, 32-bit swap).

It is deliberately generic: no field decoding of any kind (no immobilizer, key, PIN or odometer tooling).
"""
from __future__ import annotations

from dataclasses import dataclass, field

KB = 1024

# size in bytes -> chip names with that capacity
_I2C = {128: "24C01", 256: "24C02", 512: "24C04", 1 * KB: "24C08", 2 * KB: "24C16", 4 * KB: "24C32",
        8 * KB: "24C64", 16 * KB: "24C128", 32 * KB: "24C256", 64 * KB: "24C512", 128 * KB: "24C1024 / 24M01",
        256 * KB: "24M02"}
_MICROWIRE = {128: "93C46", 256: "93C56", 512: "93C66", 1 * KB: "93C76", 2 * KB: "93C86"}
_SPI = {128: "95010", 256: "95020", 512: "95040", 1 * KB: "95080", 2 * KB: "95160", 4 * KB: "95320",
        8 * KB: "95640", 16 * KB: "95128", 32 * KB: "95256", 64 * KB: "95512", 128 * KB: "95M01",
        256 * KB: "95M02", 512 * KB: "95M04"}
MIN_SIZE = 128
MAX_SIZE = 512 * KB


@dataclass
class EepromInfo:
    size: int
    chips: list[str] = field(default_factory=list)       # "24C02 (I2C)", "93C56 (Microwire)" ...
    blank: float = 0.0                                    # share of 0xFF / 0x00 bytes
    notes: list[str] = field(default_factory=list)

    @property
    def title(self) -> str:
        return f"EEPROM image ({self.size:,} bytes)"


def is_eeprom_size(size: int) -> bool:
    return MIN_SIZE <= size <= MAX_SIZE and size & (size - 1) == 0


def guess(data: bytes, filename: str = "") -> EepromInfo | None:
    """EepromInfo when *data* has a serial-EEPROM size, else None. A large file only counts as an EEPROM when it
    is small enough for these chip families (<= 512 KB); flash dumps of the same size are listed as both."""
    n = len(data)
    if not is_eeprom_size(n):
        return None
    info = EepromInfo(n)
    for table, bus in ((_I2C, "I2C"), (_MICROWIRE, "Microwire"), (_SPI, "SPI")):
        if n in table:
            info.chips.append(f"{table[n]} ({bus})")
    if n:
        info.blank = sum(1 for b in data if b in (0x00, 0xFF)) / n
    if info.blank > 0.97:
        info.notes.append("Almost empty (0xFF / 0x00): erased chip or failed read.")
    if n >= 64 * KB:
        info.notes.append("This size is also common for small flash chips: the file may be a program memory dump.")
    if filename.lower().endswith((".eep", ".eeprom", ".e2p")):
        info.notes.append("The file extension says EEPROM.")
    return info


def swap16(data: bytes) -> bytes:
    """Swap the two bytes of every 16-bit word (x16 organised 93Cxx reads, big/little-endian tools)."""
    b = bytearray(data)
    n = len(b) & ~1
    b[0:n:2], b[1:n:2] = data[1:n:2], data[0:n:2]
    return bytes(b)


def swap32(data: bytes) -> bytes:
    """Reverse the byte order of every 32-bit word."""
    b = bytearray(data)
    n = len(b) & ~3
    for i in range(4):
        b[i:n:4] = data[3 - i:n:4]
    return bytes(b)


VIEWS = {"normal": ("As read (8-bit)", lambda d: bytes(d)),
         "swap16": ("16-bit word swap", swap16),
         "swap32": ("32-bit word swap", swap32)}


def view(data: bytes, mode: str) -> bytes:
    return VIEWS.get(mode, VIEWS["normal"])[1](data)


__all__ = ["EepromInfo", "is_eeprom_size", "guess", "swap16", "swap32", "VIEWS", "view", "MIN_SIZE", "MAX_SIZE"]
