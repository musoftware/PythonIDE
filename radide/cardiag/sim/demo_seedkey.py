"""Seed/key plug-in for the RAD IDE **Demo car only** (an example of the plug-in format of
radide/cardiag/service/security.py). It unlocks nothing in a real vehicle: real control units use their
manufacturer's algorithms, which RAD IDE does not contain - use the plug-in your tool vendor or the
manufacturer's service portal licenses to you."""

NAME = "RAD IDE Demo car"
LICENSE = "Demo car simulator only"


def compute_key(seed: bytes, level: int, ecu: dict) -> bytes:
    return bytes(((b ^ 0x5A) + level + i * 7) & 0xFF for i, b in enumerate(seed))
