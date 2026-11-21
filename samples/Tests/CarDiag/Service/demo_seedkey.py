"""Seed/key plug-in for RAD IDE's Demo car simulator ONLY (security level 1 of the simulated engine unit).

It shows the plug-in interface (radide/cardiag/service/security.py): RAD IDE contains no seed/key algorithms;
for a real vehicle you select the plug-in / DLL you are licensed to use. This rule opens nothing but the
simulator."""
NAME = "Demo car seed/key (simulator only)"
LICENSE = "Sample for RAD IDE's Demo car simulator - does not work with any real control unit."


def compute_key(seed: bytes, level: int, ecu: dict) -> bytes:
    if level != 1:
        raise ValueError("the Demo car only has security level 1")
    return bytes(b ^ 0x5A for b in reversed(seed))
