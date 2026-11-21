"""Seed/key plug-ins for SecurityAccess (0x27).

RAD IDE contains **no** security-access algorithms and never guesses or brute-forces keys. A function that needs
security access works only with a plug-in the user selects and is licensed to use (for example the seed/key
library a manufacturer's service portal or a tool vendor gives to a workshop):

* a Python module (``.py``) defining ``compute_key(seed: bytes, level: int, ecu: dict) -> bytes``
  (optional ``NAME`` and ``LICENSE`` strings are shown to the user);
* a Windows DLL with the widely used ``GenerateKeyEx`` export:
  ``int GenerateKeyEx(const unsigned char *seed, unsigned int seedLen, unsigned int level, const char *variant,
  unsigned char *key, unsigned int maxKeyLen, unsigned int *keyLen)`` (0 = success). The DLL must match the
  bitness of the IDE's Python (64-bit); a 32-bit DLL cannot be loaded and the user is told so.

Immobiliser / key / PIN functions are not offered by the service framework whatever the plug-in can do
(definitions.py rejects such definitions).
"""
from __future__ import annotations

import ctypes
import importlib.util
import os
import struct
from pathlib import Path

from .text import BiText
from .transport import ServiceError


class SeedKeyPlugin:
    kind = "?"

    def __init__(self, path: str):
        self.path = str(path)
        self.name = Path(path).name
        self.license = ""

    def compute_key(self, seed: bytes, level: int, ecu) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError

    def describe(self) -> str:
        return f"{self.name} ({self.kind})"


def _ecu_info(ecu) -> dict:
    if isinstance(ecu, dict):
        return dict(ecu)
    return {"key": getattr(ecu, "key", ""), "name": getattr(ecu, "name", ""), "tx": getattr(ecu, "tx", 0),
            "rx": getattr(ecu, "rx", 0), "protocol": getattr(ecu, "protocol", "uds"),
            "variant": (getattr(ecu, "extra", None) or {}).get("variant", "")}


class PythonPlugin(SeedKeyPlugin):
    kind = "Python"

    def __init__(self, path: str):
        super().__init__(path)
        spec = importlib.util.spec_from_file_location(f"radide_seedkey_{abs(hash(path))}", path)
        if spec is None or spec.loader is None:
            raise ServiceError(BiText(f"Cannot load the plug-in {path}", f"تعذّر تحميل الإضافة {path}"),
                               code="security")
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:  # noqa: BLE001 - a broken plug-in gets a readable message
            raise ServiceError(BiText(f"The plug-in failed to load: {e}", f"فشل تحميل الإضافة: {e}"),
                               code="security") from e
        fn = getattr(mod, "compute_key", None)
        if not callable(fn):
            raise ServiceError(BiText("The plug-in has no compute_key(seed, level, ecu) function.",
                                      "الإضافة لا تحتوي على الدالة compute_key(seed, level, ecu)."), code="security")
        self._fn = fn
        self.name = str(getattr(mod, "NAME", "") or self.name)
        self.license = str(getattr(mod, "LICENSE", "") or "")

    def compute_key(self, seed: bytes, level: int, ecu) -> bytes:
        try:
            key = self._fn(bytes(seed), int(level), _ecu_info(ecu))
        except Exception as e:  # noqa: BLE001
            raise ServiceError(BiText(f"The seed/key plug-in failed: {e}", f"فشلت إضافة seed/key: {e}"),
                               code="security") from e
        if isinstance(key, int):
            key = key.to_bytes(max(1, len(seed)), "big")
        return bytes(key)


class DllPlugin(SeedKeyPlugin):
    kind = "DLL"

    def __init__(self, path: str):
        super().__init__(path)
        bits = struct.calcsize("P") * 8
        try:
            lib = ctypes.WinDLL(path) if os.name == "nt" else ctypes.CDLL(path)
        except OSError as e:
            raise ServiceError(BiText(
                f"Cannot load the DLL ({e}). It must be a {bits}-bit DLL to match RAD IDE's Python.",
                f"تعذّر تحميل ملف DLL ({e}). يجب أن يكون {bits}-بت ليطابق بايثون RAD IDE."), code="security") from e
        fn = getattr(lib, "GenerateKeyEx", None)
        if fn is None:
            raise ServiceError(BiText("The DLL has no GenerateKeyEx export.", "ملف DLL لا يصدّر الدالة GenerateKeyEx."),
                               code="security")
        fn.restype = ctypes.c_int
        fn.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_uint, ctypes.c_uint, ctypes.c_char_p,
                       ctypes.POINTER(ctypes.c_ubyte), ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)]
        self._fn = fn

    def compute_key(self, seed: bytes, level: int, ecu) -> bytes:
        seed_buf = (ctypes.c_ubyte * max(1, len(seed)))(*seed)
        key_buf = (ctypes.c_ubyte * 64)()
        out_len = ctypes.c_uint(0)
        variant = str(_ecu_info(ecu).get("variant") or "").encode("ascii", "replace")
        rc = self._fn(seed_buf, len(seed), int(level), variant, key_buf, 64, ctypes.byref(out_len))
        if rc != 0:
            raise ServiceError(BiText(f"GenerateKeyEx returned error {rc}.", f"أعادت GenerateKeyEx الخطأ {rc}."),
                               code="security")
        return bytes(key_buf[:out_len.value])


def load_plugin(path: str) -> SeedKeyPlugin:
    p = Path(path)
    if not p.is_file():
        raise ServiceError(BiText(f"Plug-in not found: {path}", f"الإضافة غير موجودة: {path}"), code="security")
    if p.suffix.lower() == ".py":
        return PythonPlugin(str(p))
    if p.suffix.lower() in (".dll", ".so", ".dylib"):
        return DllPlugin(str(p))
    raise ServiceError(BiText("A seed/key plug-in is a .py module or a .dll.",
                              "إضافة seed/key هي وحدة .py أو ملف .dll."), code="security")
