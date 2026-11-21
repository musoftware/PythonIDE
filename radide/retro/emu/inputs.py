"""Default controller input for the portable Mesen 2 configuration RAD IDE creates (no Qt in here).

A portable Mesen 2 (``settings.json`` next to ``Mesen.exe``) that starts from an empty settings file skips
Mesen's first-run wizard, so NES, SNES and Game Boy controller port 1 stay "None" with no keys: the game runs
but cannot be played. When RAD IDE creates that settings file it now writes port 1 = the standard controller
of each console with a keyboard layout (Mesen 2.1 settings schema, key codes = Avalonia ``Key`` values):

    arrows  = D-pad          X = A      Z = B      S = X (SNES) / turbo A      A = Y (SNES) / turbo B
    Enter   = Start          Right Shift / Backspace / Left Shift = Select     Q / W = L / R (SNES)

plus Mesen's own Xbox gamepad layout in the second mapping. Everything else is left to Mesen's defaults (the
file is partial; Mesen fills in the rest and writes the full file when it closes).

A settings file the user already has is never rewritten on its own: :func:`needs_mesen_defaults` tells
whether a RAD IDE created config still has no controller (port 1 "None" and no key in any mapping), and
:func:`apply_mesen_defaults` sets only those ports when the user accepts the offer in the IDE.
"""
from __future__ import annotations

import json
from pathlib import Path

# Avalonia.Input.Key values (what Mesen 2 stores for keyboard keys)
K_BACK, K_ENTER, K_LEFT, K_UP, K_RIGHT, K_DOWN = 2, 6, 23, 24, 25, 26
K_A, K_Q, K_S, K_W, K_X, K_Z = 44, 60, 62, 66, 67, 69
K_LSHIFT, K_RSHIFT = 116, 117

_ARROWS = {"Up": K_UP, "Down": K_DOWN, "Left": K_LEFT, "Right": K_RIGHT}
# Mesen's own "Xbox" preset (first XInput pad)
_PAD = {"A": 4110, "B": 4109, "X": 4112, "Y": 4111, "L": 4105, "R": 4106, "Up": 4097, "Down": 4098,
        "Left": 4099, "Right": 4100, "Start": 4101, "Select": 4102}


def _maps(main: dict, pad_keys) -> dict:
    return {"Mapping1": dict(_ARROWS, Start=K_ENTER, Select=K_RSHIFT, **main),
            "Mapping2": {k: _PAD[k] for k in pad_keys},
            "Mapping3": {"Select": K_BACK},
            "Mapping4": {"Select": K_LSHIFT}}


# console section -> (port key, controller type, key mappings)
MESEN_PORTS = {
    "Nes": ("Port1", "NesController",
            _maps({"A": K_X, "B": K_Z, "TurboA": K_S, "TurboB": K_A},
                  ("A", "B", "Up", "Down", "Left", "Right", "Start", "Select"))),
    "Snes": ("Port1", "SnesController",
             _maps({"A": K_X, "B": K_Z, "X": K_S, "Y": K_A, "L": K_Q, "R": K_W}, tuple(_PAD))),
    "Gameboy": ("Controller", "GameboyController",
                _maps({"A": K_X, "B": K_Z}, ("A", "B", "Up", "Down", "Left", "Right", "Start", "Select"))),
}


def mesen_defaults() -> dict:
    """The partial settings.json RAD IDE writes for a new portable Mesen 2."""
    d: dict = {console: {port: dict(maps, Type=ctl)} for console, (port, ctl, maps) in MESEN_PORTS.items()}
    # one Mesen window per Run: with "single instance" a second Run only hands the ROM to the open window and
    # exits at once, so RAD IDE could neither track nor stop the emulator it started
    d["Preferences"] = {"SingleInstance": False}
    return d


def write_new_mesen_settings(path) -> bool:
    """Create *path* with :func:`mesen_defaults` - only when it does not exist yet (never overwrites)."""
    p = Path(path)
    if p.exists():
        return False
    p.write_text(json.dumps(mesen_defaults(), indent=2), encoding="utf-8")
    return True


def _load(path) -> dict:
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _port_unset(port) -> bool:
    if not isinstance(port, dict):
        return True
    if port.get("Type") not in (None, "None"):
        return False
    for k, m in port.items():
        if k.startswith("Mapping") and isinstance(m, dict):
            if any(isinstance(v, int) and v for v in m.values()) or any(isinstance(v, list) and any(v)
                                                                       for v in m.values()):
                return False
    return True


def needs_mesen_defaults(path) -> list[str]:
    """Consoles (Nes / Snes / Gameboy) whose port 1 is "None" without any key in *path* (the settings.json)."""
    p = Path(path)
    if not p.is_file():
        return []
    d = _load(p)
    out = []
    for console, (port, _ctl, _maps) in MESEN_PORTS.items():
        sect = d.get(console)
        if sect is None or (isinstance(sect, dict) and _port_unset(sect.get(port))):
            out.append(console)
    return out


def apply_mesen_defaults(path) -> list[str]:
    """Give the unset port 1 of each console in *path* the default controller and keys -> consoles changed.
    Ports the user configured (a type or any key) are left alone; nothing else in the file changes."""
    p = Path(path)
    todo = needs_mesen_defaults(p)
    if not todo:
        return []
    d = _load(p)
    for console in todo:
        port, ctl, maps = MESEN_PORTS[console]
        sect = d.setdefault(console, {})
        cur = sect.get(port) if isinstance(sect.get(port), dict) else {}
        new = dict(cur)
        new["Type"] = ctl
        for mk, keys in maps.items():
            m = dict(cur.get(mk) or {}) if isinstance(cur.get(mk), dict) else {}
            m.update(keys)
            new[mk] = m
        sect[port] = new
    p.write_text(json.dumps(d, indent=2), encoding="utf-8")
    return todo


__all__ = ["MESEN_PORTS", "apply_mesen_defaults", "mesen_defaults", "needs_mesen_defaults",
           "write_new_mesen_settings"]
