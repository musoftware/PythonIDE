"""ROM workbench (slice "rom" of radide/retro, see docs/RETRO.md): hex editor, ROM / disk / tape detection,
checksum repair, IPS / UPS / BPS patches and the ROM Hacking project.

Pure-Python modules (no Qt): buffer, detect, patches, tbl, inspector, project, synth, emulink.
Qt modules: hexview, hexdoc, dialogs, diffview (imported by radide/features/retro_rom.py).
"""
from __future__ import annotations

from .detect import RomInfo, detect, detect_system, fix_checksum
from .patches import PatchError, apply_patch, create_patch

__all__ = ["PatchError", "RomInfo", "apply_patch", "create_patch", "detect", "detect_system", "fix_checksum"]
