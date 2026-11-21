"""Screenshots of a ROM taken by Mesen 2 itself, from a script (no desktop capture, no window).

Mesen 2 has a headless test runner: ``Mesen.exe --testRunner script.lua rom`` runs the emulation without a window
and ends when the script calls ``emu.stop(exitCode)``. ``emu.takeScreenshot()`` returns the current frame as PNG
bytes. Mesen's Lua sandbox has no ``io`` / ``os`` library unless the user turns on "Allow access to I/O and OS
functions" in the script window settings, so RAD IDE does not touch that setting: the script prints the PNG as
hex on stdout (``RADSHOT <frame> <hex>``) and this module writes the files.

    shots = mesen_screenshots("game.nes", [60, 240], "shots/", inputs=[(120, 130, {"start": True})])

*inputs*: ``(first frame, last frame, buttons)`` - buttons are Mesen's input names (a, b, select, start, up,
down, left, right), held on controller port 0 during those frames.

The runs use a private runner copy of Mesen (hard links of Mesen.exe and its DLLs in
%LOCALAPPDATA%/RADIDE/retro/mesen-runner, Mesen's portable mode = its own settings.json): the user's Mesen
settings are never changed, and a Mesen the user has open at the same time is not disturbed. The runner's
settings put a standard controller in port 1 (a portable Mesen started from an empty settings.json has "None"
there, and ``emu.setInput`` would do nothing).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import manager

LUA = r"""-- written by RAD IDE (radide/retro/emu/mesenshot.py)
local shots = {%(frames)s}
local last = %(last)d
local inputs = {%(inputs)s}
local frame = 0
local function hex(s)
  return (s:gsub(".", function(c) return string.format("%%02X", string.byte(c)) end))
end
emu.addEventCallback(function()
  for _, i in ipairs(inputs) do
    if frame >= i[1] and frame <= i[2] then emu.setInput(i[3], 0) end
  end
end, emu.eventType.inputPolled)
emu.addEventCallback(function()
  frame = frame + 1
  if shots[frame] then
    print("RADSHOT " .. frame .. " " .. hex(emu.takeScreenshot()))
  end
  if frame >= last then
    print("RADDONE " .. frame)
    emu.stop(0)
  end
end, emu.eventType.endFrame)
"""


class ShotError(RuntimeError):
    pass


def _lua_table(buttons: dict) -> str:
    return "{" + ", ".join(f"{k}={'true' if v else 'false'}" for k, v in buttons.items()) + "}"


def script(frames, inputs=None) -> str:
    frames = sorted({int(f) for f in frames if int(f) > 0})
    if not frames:
        raise ValueError("no frame numbers")
    ins = ", ".join(f"{{{int(a)}, {int(b)}, {_lua_table(btn)}}}" for a, b, btn in (inputs or []))
    return LUA % {"frames": ", ".join(f"[{f}]=true" for f in frames), "last": frames[-1], "inputs": ins}


RUNNER_FILES = ("Mesen.exe", "MesenCore.dll", "libHarfBuzzSharp.dll", "libSkiaSharp.dll", "MesenNesDB.txt")
CONTROLLERS = (("Nes", "NesController"), ("Snes", "SnesController"), ("PcEngine", "PceController"),
               ("Sms", "SmsController"))


def runner(exe: str) -> str:
    """The private runner copy of *exe* (created / refreshed when the installed Mesen changes)."""
    src = Path(exe).parent
    dst = manager.config_dir("mesen-runner")
    for name in RUNNER_FILES:
        f, t = src / name, dst / name
        if not f.is_file():
            continue
        if t.is_file() and t.stat().st_size == f.stat().st_size and t.stat().st_mtime >= f.stat().st_mtime:
            continue
        if t.exists():
            t.unlink()
        try:
            os.link(f, t)                     # same volume: no extra disk space
        except OSError:
            shutil.copy2(f, t)
    sp = dst / "settings.json"
    try:
        d = json.loads(sp.read_text(encoding="utf-8-sig")) if sp.is_file() else {}
    except (OSError, ValueError):
        d = {}
    if not d:
        user = src / "settings.json"
        try:
            d = json.loads(user.read_text(encoding="utf-8-sig")) if user.is_file() else {}
        except (OSError, ValueError):
            d = {}
    changed = not sp.is_file()
    for console, ctl in CONTROLLERS:
        sect = d.get(console)
        if isinstance(sect, dict):
            port = sect.setdefault("Port1", {})
            if isinstance(port, dict) and port.get("Type") in (None, "None"):
                port["Type"] = ctl
                changed = True
        elif d:
            d[console] = {"Port1": {"Type": ctl}}
            changed = True
    if changed:
        sp.write_text(json.dumps(d, indent=2), encoding="utf-8")
    return str(dst / "Mesen.exe")


def mesen_screenshots(rom, frames, outdir, inputs=None, timeout: float = 90.0, exe: str | None = None,
                      prefix: str = "") -> list[Path]:
    """Run *rom* headless in Mesen 2 and save a PNG at every frame number in *frames* -> the files written."""
    exe = exe or manager.find("mesen")
    if not exe:
        raise ShotError(manager.missing_hint("mesen"))
    rom = Path(rom).resolve()
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="radide-mesen-") as tmp:
        lua = Path(tmp) / "shots.lua"
        lua.write_text(script(frames, inputs), encoding="utf-8")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        run_exe = runner(exe)
        p = subprocess.Popen([run_exe, "--testRunner", "--doNotSaveSettings", str(lua), str(rom)], cwd=tmp,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=flags)
        try:
            out, _ = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()                                  # only the process started here
            out, _ = p.communicate()
            raise ShotError(f"Mesen did not finish within {timeout:.0f} s")
    written = []
    text = out.decode("latin-1", "replace")
    for line in text.splitlines():
        if not line.startswith("RADSHOT "):
            continue
        _tag, frame, hx = line.split(" ", 2)
        try:
            png = bytes.fromhex(hx.strip())
        except ValueError:
            continue
        f = outdir / f"{prefix or rom.stem}_f{int(frame):05d}.png"
        f.write_bytes(png)
        written.append(f)
    if not written:
        tail = "\n".join(text.splitlines()[-8:])
        raise ShotError(f"Mesen returned {p.returncode} without screenshots:\n{tail}")
    return written


__all__ = ["ShotError", "mesen_screenshots", "runner", "script"]
