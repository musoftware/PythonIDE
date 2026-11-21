"""Firmware / ECU Analysis project (firmware.json beside project.radproj).

    original/<file>     the file you analyse - copied once, set read-only, SHA-256 recorded, never written again
    work/<name>.bin     working copy (flat image at the base address) for your own experiments
    notes.md            your notes
    labels.json         [{address, name, comment, kind}] - names for functions / tables / strings
    firmware.json       format, CPU, base address, memory map, SHA-256, size

The original is verified (SHA-256) every time the project is analysed or built. Pure Python.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from dataclasses import asdict, dataclass, field
from pathlib import Path

FILE = "firmware.json"


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_read_only(path) -> None:
    try:
        os.chmod(path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    except OSError:
        pass


@dataclass
class Label:
    address: int
    name: str
    comment: str = ""
    kind: str = ""              # "func" | "table" | "string" | "data" | ""


@dataclass
class FirmwareProject:
    folder: Path
    name: str = ""
    original: str = ""          # relative path (original/...)
    sha256: str = ""
    size: int = 0
    format: str = ""
    arch: str = ""
    base: int = 0
    working: str = ""
    segments: list[dict] = field(default_factory=list)      # [{address, size, name}]
    extra: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ files
    @property
    def path_json(self) -> Path:
        return Path(self.folder) / FILE

    def path(self, rel: str) -> Path:
        return Path(self.folder) / rel

    @property
    def original_path(self) -> Path | None:
        return self.path(self.original) if self.original else None

    @property
    def working_path(self) -> Path | None:
        return self.path(self.working) if self.working else None

    @property
    def labels_path(self) -> Path:
        return self.path("labels.json")

    @classmethod
    def load(cls, folder) -> "FirmwareProject":
        folder = Path(folder)
        d = json.loads((folder / FILE).read_text(encoding="utf-8"))
        fp = cls(folder)
        for k, v in d.items():
            if k == "base" and isinstance(v, str):
                v = int(v, 0)
            if hasattr(fp, k) and k != "folder":
                setattr(fp, k, v)
        return fp

    def save(self) -> None:
        d = asdict(self)
        d.pop("folder")
        d["base"] = f"0x{self.base:X}"
        self.path_json.write_text(json.dumps(d, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ original
    def set_original(self, src, analyse: bool = True) -> Path:
        """Copy *src* into original/ (read-only) and record its SHA-256. An existing original is never replaced
        silently: a different file goes next to it with a numbered name."""
        src = Path(src)
        dst_dir = self.path("original")
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / src.name
        n = 1
        while dst.exists() and sha256_file(dst) != sha256_file(src):
            dst = dst_dir / f"{src.stem}_{n}{src.suffix}"
            n += 1
        if not dst.exists():
            shutil.copy2(src, dst)
        make_read_only(dst)
        self.original = dst.relative_to(self.folder).as_posix()
        self.sha256 = sha256_file(dst)
        self.size = dst.stat().st_size
        if analyse:
            self.refresh()
        self.save()
        return dst

    def verify(self) -> tuple[bool, str]:
        p = self.original_path
        if p is None:
            return False, "The project has no original file yet."
        if not p.is_file():
            return False, f"The original file is missing: {p}"
        h = sha256_file(p)
        if self.sha256 and h != self.sha256:
            return False, f"The original file was changed (SHA-256 {h[:16]}... expected {self.sha256[:16]}...)."
        return True, "Original intact (SHA-256 matches)."

    def load_original(self):
        from ..formats import load
        p = self.original_path
        if p is None:
            raise FileNotFoundError("no original")
        return load(p, base=self.base if self.format in ("", "raw") else 0)

    def refresh(self, arch: str = "") -> object:
        """Analyse the original and store format, CPU guess, base guess and the memory map."""
        from ..formats import load
        from .report import analyze
        p = self.original_path
        mm = load(p)
        self.format = mm.meta.get("format", "raw")
        res = analyze(mm, arch=arch or self.extra.get("arch_fixed", ""))
        self.arch = res.arch
        if self.format == "raw":
            self.base = res.base
        else:
            self.base = mm.min_address
        self.segments = [{"address": f"0x{s.address + (self.base if self.format == 'raw' else 0):X}",
                          "size": len(s), "name": s.name} for s in mm.segments]
        return res

    def make_working_copy(self) -> Path:
        """work/<name>.bin = the flat image (gaps 0xFF) - never the original file itself."""
        mm = self.load_original()
        dst = self.path("work") / f"{Path(self.original).stem}.bin"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(mm.to_flat(0xFF))
        self.working = dst.relative_to(self.folder).as_posix()
        self.save()
        return dst

    # ------------------------------------------------------------------ labels
    def labels(self) -> list[Label]:
        try:
            d = json.loads(self.labels_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        out = []
        for x in d:
            try:
                a = x["address"]
                out.append(Label(int(a, 0) if isinstance(a, str) else int(a), x.get("name", ""),
                                 x.get("comment", ""), x.get("kind", "")))
            except (KeyError, ValueError, TypeError):
                pass
        return out

    def save_labels(self, labels: list[Label]) -> None:
        d = [{"address": f"0x{x.address:X}", "name": x.name, "comment": x.comment, "kind": x.kind}
             for x in sorted(labels, key=lambda x: x.address)]
        self.labels_path.write_text(json.dumps(d, indent=2), encoding="utf-8")

    def set_label(self, address: int, name: str, comment: str = "", kind: str = "") -> None:
        labs = [x for x in self.labels() if x.address != address]
        if name:
            labs.append(Label(address, name, comment, kind))
        self.save_labels(labs)


NOTES = """# {name} - firmware analysis notes

* Original: original/ (read-only, SHA-256 in firmware.json). It is never modified.
* Working copy: work/ (Project > Firmware Analysis > Make Working Copy) for your own experiments.
* Analysis: Project > Firmware Analysis > Analyze (entropy, strings, CPU, base address, disassembly, Ghidra).
* Labels: labels.json (address, name, comment).

Edits to vehicle software can affect safety, warranty and emissions legality. Keep the original and follow
your local laws.

## Findings

| Address | What |
|---------|------|
|         |      |
"""


def new_project(folder, name: str) -> FirmwareProject:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    fp = FirmwareProject(folder, name)
    if (folder / FILE).exists():
        fp = FirmwareProject.load(folder)
    (folder / "original").mkdir(exist_ok=True)
    notes = folder / "notes.md"
    if not notes.exists():
        notes.write_text(NOTES.format(name=name), encoding="utf-8")
    if not fp.labels_path.exists():
        fp.save_labels([])
    fp.save()
    return fp
