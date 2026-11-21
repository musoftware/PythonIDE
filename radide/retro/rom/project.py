"""ROM Hacking project (rom.json beside project.radproj). Pure Python - the IDE plugin
(radide/languages/retro_romhack.py) and ``python -m radide.retro.rom build <folder>`` use it.

    rom.json
    {
      "rom": "rom/clean.nes",            # the clean ROM: relative = copied into the project, absolute = referenced
      "rom_crc32": "1A2B3C4D",           # CRC32 of the clean ROM when it was chosen (Build warns when it changes)
      "system": "nes",
      "output": "build/MyHack.nes",      # Build writes the patched ROM here
      "patches": [{"file": "patches/001_title.ips", "enabled": true, "note": "..."}],
      "tables": ["tables/game.tbl"],
      "fix_checksum": true,              # repair the header checksum after patching (GB / SNES / Genesis ...)
      "work": "work/MyHack.nes"          # optional working copy edited in the hex editor
    }

The original ROM file is never written: Build always starts from a fresh copy in memory.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .detect import detect, fix_checksum
from .patches import PatchError, apply_patch, create_patch, crc32

FILE = "rom.json"
PATCH_EXTS = (".ips", ".bps", ".ups")


@dataclass
class PatchEntry:
    file: str
    enabled: bool = True
    note: str = ""


@dataclass
class RomProject:
    folder: Path
    rom: str = ""
    rom_crc32: str = ""
    system: str = ""
    output: str = ""
    patches: list[PatchEntry] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    fix_checksum: bool = True
    work: str = ""
    extra: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ io
    @classmethod
    def load(cls, folder) -> "RomProject":
        folder = Path(folder)
        p = folder / FILE
        d = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
        known = ("rom", "rom_crc32", "system", "output", "patches", "tables", "fix_checksum", "work")
        patches = []
        for e in d.get("patches") or []:
            if isinstance(e, str):
                patches.append(PatchEntry(e))
            elif isinstance(e, dict) and e.get("file"):
                patches.append(PatchEntry(str(e["file"]), bool(e.get("enabled", True)), str(e.get("note", ""))))
        return cls(folder, str(d.get("rom") or ""), str(d.get("rom_crc32") or ""), str(d.get("system") or ""),
                   str(d.get("output") or ""), patches, [str(t) for t in d.get("tables") or []],
                   bool(d.get("fix_checksum", True)), str(d.get("work") or ""),
                   {k: v for k, v in d.items() if k not in known})

    def save(self) -> Path:
        d = {"rom": self.rom, "rom_crc32": self.rom_crc32, "system": self.system, "output": self.output,
             "patches": [{"file": p.file, "enabled": p.enabled, **({"note": p.note} if p.note else {})}
                         for p in self.patches],
             "tables": self.tables, "fix_checksum": self.fix_checksum}
        if self.work:
            d["work"] = self.work
        d.update(self.extra)
        p = self.folder / FILE
        p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return p

    # ------------------------------------------------------------------ paths
    def path(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else self.folder / p

    def rel(self, path) -> str:
        p = Path(path).resolve()
        try:
            return p.relative_to(self.folder.resolve()).as_posix()
        except ValueError:
            return str(p)

    @property
    def rom_path(self) -> Path | None:
        return self.path(self.rom) if self.rom else None

    @property
    def output_path(self) -> Path:
        if self.output:
            return self.path(self.output)
        ext = self.rom_path.suffix if self.rom_path else ".bin"
        return self.folder / "build" / f"{self.folder.name}_patched{ext}"

    @property
    def work_path(self) -> Path | None:
        return self.path(self.work) if self.work else None

    # ------------------------------------------------------------------ the ROM
    def set_rom(self, source, copy: bool = True) -> Path:
        """Choose the clean ROM. *copy*: copy it into rom/ (the project stays self-contained); otherwise
        the project references the file where it is. The source file is only read."""
        src = Path(source).resolve()
        data = src.read_bytes()
        if copy:
            dest = self.folder / "rom" / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.resolve() != src:
                shutil.copyfile(src, dest)
            self.rom = self.rel(dest)
        else:
            self.rom = str(src)
        self.rom_crc32 = f"{crc32(data):08X}"
        info = detect(data, src.name)
        self.system = info.system
        # the empty template writes a placeholder build/<name>_patched.bin before a ROM is chosen: give the
        # output the ROM's extension (a .nes must stay .nes for the emulators and the hex editor)
        if not self.output or (self.output.startswith("build/") and self.output.endswith("_patched.bin")
                               and src.suffix.lower() != ".bin"):
            self.output = f"build/{Path(self.output).stem if self.output else self.folder.name + '_patched'}" \
                          f"{src.suffix}"
        return self.rom_path

    def clean_rom(self) -> bytes:
        p = self.rom_path
        if p is None:
            raise PatchError("The project has no source ROM yet (Project > ROM Hacking > Set Source ROM...).")
        if not p.is_file():
            raise PatchError(f"The source ROM was not found: {p}")
        return p.read_bytes()

    # ------------------------------------------------------------------ patches
    def add_patch(self, path, note: str = "") -> PatchEntry:
        p = Path(path)
        dest_dir = self.folder / "patches"
        if p.resolve().parent != dest_dir.resolve():
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / p.name
            i = 2
            while dest.exists():
                dest = dest_dir / f"{p.stem}_{i}{p.suffix}"
                i += 1
            shutil.copyfile(p, dest)
            p = dest
        e = PatchEntry(self.rel(p), True, note)
        self.patches.append(e)
        return e

    def move_patch(self, index: int, delta: int) -> None:
        j = index + delta
        if 0 <= index < len(self.patches) and 0 <= j < len(self.patches):
            self.patches[index], self.patches[j] = self.patches[j], self.patches[index]

    def next_patch_name(self, stem: str, fmt: str) -> Path:
        n = len(self.patches) + 1
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem) or "edits"
        d = self.folder / "patches"
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{n:03d}_{safe}.{fmt}"
        while p.exists():
            n += 1
            p = d / f"{n:03d}_{safe}.{fmt}"
        return p

    # ------------------------------------------------------------------ build
    def apply_all(self, upto: int | None = None, log=None) -> bytes:
        """The clean ROM with the enabled patches applied in order (patches[:upto])."""
        data = self.clean_rom()
        if self.rom_crc32 and f"{crc32(data):08X}" != self.rom_crc32.upper() and log:
            log(f"warning: the source ROM changed since it was chosen (CRC32 {crc32(data):08X}, "
                f"recorded {self.rom_crc32})")
        for e in self.patches[:upto]:
            if not e.enabled:
                continue
            p = self.path(e.file)
            if not p.is_file():
                raise PatchError(f"Patch not found: {e.file}")
            before = len(data)
            try:
                data = apply_patch(data, p.read_bytes())
            except PatchError as err:
                raise PatchError(f"{e.file}: {err}") from err
            if log:
                log(f"applied {e.file} ({before:,} -> {len(data):,} bytes)")
        return data

    def build(self, log=print) -> Path:
        data = self.apply_all(log=log)
        name = self.rom_path.name if self.rom_path else "rom.bin"
        if self.fix_checksum:
            try:
                fixed, msg = fix_checksum(data, name)
                if fixed != data:
                    log(f"fixed the header checksum: {msg}")
                data = fixed
            except ValueError:
                pass
        out = self.output_path
        out.parent.mkdir(parents=True, exist_ok=True)
        src = self.rom_path.resolve() if self.rom_path else None
        if src is not None and out.resolve() == src:
            raise PatchError("The output file is the source ROM - choose another output name.")
        out.write_bytes(data)
        log(f"Build: {self.rel(out)} ({len(data):,} bytes, CRC32 {crc32(data):08X})")
        return out

    def make_work_copy(self) -> Path:
        """work/<name>: the current build result to edit in the hex editor (Capture Edits turns the edits into a
        patch)."""
        data = self.apply_all()
        name = self.rom_path.name if self.rom_path else "rom.bin"
        p = self.folder / "work" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        self.work = self.rel(p)
        return p

    def capture_edits(self, fmt: str = "ips", stem: str = "edits", note: str = "") -> PatchEntry | None:
        """Diff the working copy against clean ROM + all patches and add the difference as a new patch.
        None when the working copy has no changes."""
        wp = self.work_path
        if wp is None or not wp.is_file():
            raise PatchError("There is no working copy (Project > ROM Hacking > Edit Working Copy).")
        base = self.apply_all()
        work = wp.read_bytes()
        if work == base:
            return None
        if fmt == "ips" and len(work) > (1 << 24):
            fmt = "bps"
        patch = create_patch(base, work, fmt, metadata=note)
        p = self.next_patch_name(stem, fmt)
        p.write_bytes(patch)
        e = PatchEntry(self.rel(p), True, note)
        self.patches.append(e)
        return e


def new_project(folder, name: str = "", rom=None, copy: bool = True) -> RomProject:
    folder = Path(folder)
    for sub in ("patches", "tables", "build"):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    rp = RomProject(folder)
    if rom is not None:
        rp.set_rom(rom, copy)
    rp.save()
    return rp


__all__ = ["FILE", "PATCH_EXTS", "PatchEntry", "RomProject", "new_project"]
