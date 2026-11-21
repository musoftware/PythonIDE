"""Strong name key files (.snk) - what ``sn -k`` and Visual Studio's Signing page "Create strong
name key" produce: an RSA key pair in the CryptoAPI PRIVATEKEYBLOB layout.

Layout (little-endian): BLOBHEADER {bType=0x07 PRIVATEKEYBLOB, bVersion=0x02, reserved=0,
aiKeyAlg=0x00002400 CALG_RSA_SIGN}, RSAPUBKEY {magic "RSA2", bitlen, pubexp}, then modulus (bitlen/8),
prime1, prime2, exponent1, exponent2, coefficient (bitlen/16 each) and privateExponent (bitlen/8).
Key generation uses Python's ``secrets`` module and Miller-Rabin primality tests (no dependency).
"""
from __future__ import annotations

import secrets
import struct
from pathlib import Path

_SMALL_PRIMES = [p for p in range(3, 2000, 2) if all(p % d for d in range(3, int(p ** 0.5) + 1, 2))]


def _is_probable_prime(n: int, rounds: int = 40) -> bool:
    if n < 2:
        return False
    for p in _SMALL_PRIMES:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for _ in range(rounds):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _r in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _prime(bits: int, e: int) -> int:
    while True:
        c = secrets.randbits(bits) | (1 << (bits - 1)) | (1 << (bits - 2)) | 1
        if (c - 1) % e and _is_probable_prime(c):
            return c


def generate_key(bits: int = 1024, e: int = 65537) -> dict:
    while True:
        p, q = _prime(bits // 2, e), _prime(bits // 2, e)
        if p == q:
            continue
        n = p * q
        if n.bit_length() != bits:
            continue
        phi = (p - 1) * (q - 1)
        d = pow(e, -1, phi)
        if p < q:
            p, q = q, p
        return {"n": n, "e": e, "d": d, "p": p, "q": q, "dp": d % (p - 1), "dq": d % (q - 1),
                "qinv": pow(q, -1, p), "bits": bits}


def _le(x: int, size: int) -> bytes:
    return x.to_bytes(size, "little")


def snk_bytes(key: dict) -> bytes:
    bits = key["bits"]
    full, half = bits // 8, bits // 16
    head = struct.pack("<BBHI", 0x07, 0x02, 0, 0x00002400) + b"RSA2" + struct.pack("<II", bits, key["e"])
    return head + b"".join([_le(key["n"], full), _le(key["p"], half), _le(key["q"], half), _le(key["dp"], half),
                            _le(key["dq"], half), _le(key["qinv"], half), _le(key["d"], full)])


def parse_snk(data: bytes) -> dict:
    """Read a PRIVATEKEYBLOB back (validation and tests)."""
    btype, ver, _r, alg = struct.unpack_from("<BBHI", data, 0)
    magic = data[8:12]
    bits, e = struct.unpack_from("<II", data, 12)
    if btype != 0x07 or magic != b"RSA2":
        raise ValueError("not a strong name key pair (PRIVATEKEYBLOB / RSA2)")
    full, half = bits // 8, bits // 16
    pos = 20
    out = {"bits": bits, "e": e, "alg": alg, "version": ver}
    for name, size in (("n", full), ("p", half), ("q", half), ("dp", half), ("dq", half), ("qinv", half),
                       ("d", full)):
        out[name] = int.from_bytes(data[pos:pos + size], "little")
        pos += size
    return out


def create_snk(path, bits: int = 1024) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(snk_bytes(generate_key(bits)))
    return path
