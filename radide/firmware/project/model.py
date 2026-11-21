"""ECU / firmware project (ecu.json beside project.radproj).  Pure Python: the IDE feature
(radide/features/firmware_project.py), ``python -m radide.firmware.project`` and the tests use it.

    ecu.json
    {
      "original": "original/stock.bin",         # kept read-only; never written by RAD IDE
      "original_sha256": "...", "original_size": 65536,
      "original_format": "raw",                 # raw / ihex / srec / elf (via radide.firmware.formats)
      "image_base": "0x0",                      # address of offset 0 of the flat image (HEX / S19 output)
      "work": "work/stock.bin",                 # the working copy (flat binary) edited in the hex / map editors
      "container": "bin",                       # Build output: bin / hex / s19 / same (= like the original)
      "output": "build/stock_mod.bin",
      "checksums": [ ...blocks, radide/firmware/checksum/blocks.py... ],
      "correct_on_save": true, "correct_on_build": true,
      "maps": "maps/stock.maps.json",           # optional map pack (radide/firmware/maps) for map-level diffs
      "versions": [{"id": "v001", "name": "...", "note": "...", "created": "...", "file": "versions/v001.bin",
                    "sha256": "..."}]
    }

Build = the working copy + corrected checksums -> output in the chosen container + a modification report.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import shutil
import stat
from dataclasses import dataclass, field
from pathlib import Path

from ..checksum.blocks import ChecksumBlock, blocks_from_json, blocks_to_json, correct, hx, report, to_int, verify

FILE = "ecu.json"
CONTAINERS = {"bin": ".bin", "hex": ".hex", "s19": ".s19", "same": ""}
CONTAINER_FMT = {"bin": "raw", "hex": "ihex", "s19": "srec"}


class EcuProjectError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat(sep=" ")


def diff_ranges(a: bytes, b: bytes, limit: int = 100_000) -> list[tuple[int, int]]:
    """[start, end) runs where *a* and *b* differ (a size change is one run at the end)."""
    n = min(len(a), len(b))
    out: list[tuple[int, int]] = []
    if n:
        try:
            import numpy as np
            x = np.frombuffer(a, dtype=np.uint8, count=n) != np.frombuffer(b, dtype=np.uint8, count=n)
            if x.any():
                d = np.diff(np.concatenate([[0], x.astype(np.int8), [0]]))
                starts, ends = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
                out = list(zip(starts.tolist(), ends.tolist()))[:limit]
        except ImportError:
            i = 0
            while i < n and len(out) < limit:
                if a[i] != b[i]:
                    j = i
                    while j < n and a[j] != b[j]:
                        j += 1
                    out.append((i, j))
                    i = j
                else:
                    i += 1
    if len(a) != len(b):
        out.append((n, max(len(a), len(b))))
    return out


def load_image(path, base: int = 0) -> tuple[bytes, str, int]:
    """(flat bytes, format, image base) of a firmware file: raw binaries as they are, Intel HEX / S-record /
    ELF through radide.firmware.formats (gaps filled with 0xFF)."""
    p = Path(path)
    raw = p.read_bytes()
    try:
        from ..formats import detect_format, load_bytes
    except ImportError:                       # the formats package is optional: raw only
        return raw, "raw", base
    fmt = detect_format(raw[:4096], p.name)
    if fmt == "raw":
        return raw, "raw", base
    m = load_bytes(raw, p.name, base, fmt)
    return m.to_flat(0xFF), fmt, m.min_address


def dump_image(data: bytes, fmt: str, base: int = 0) -> bytes:
    if fmt == "raw":
        return bytes(data)
    try:
        from ..formats import MemoryMap, dumps
    except ImportError as e:
        raise EcuProjectError(f"Writing {fmt} needs radide.firmware.formats: {e}") from e
    return dumps(MemoryMap.from_bytes(bytes(data), base), fmt)


@dataclass
class Version:
    id: str
    name: str
    note: str = ""
    created: str = ""
    file: str = ""
    sha256: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "note": self.note, "created": self.created, "file": self.file,
                "sha256": self.sha256}


@dataclass
class MapChange:
    name: str
    kind: str
    cells_changed: int
    cells: int
    max_delta: float
    unit: str = ""
    address: int = 0

    def line(self) -> str:
        u = f" {self.unit}" if self.unit else ""
        return (f"{self.name} ({self.kind} @ {hx(self.address)}): {self.cells_changed}/{self.cells} cells changed, "
                f"largest change {self.max_delta:+g}{u}")


@dataclass
class DiffResult:
    a: str
    b: str
    ranges: list = field(default_factory=list)
    bytes_changed: int = 0
    maps: list = field(default_factory=list)          # MapChange
    unmapped: list = field(default_factory=list)      # byte ranges outside every known map
    checksum_spans: list = field(default_factory=list)

    def summary(self) -> str:
        s = f"{self.bytes_changed:,} byte(s) changed in {len(self.ranges)} range(s)"
        if self.maps:
            s += f", {len(self.maps)} map(s)"
        return s


@dataclass
class BuildResult:
    output: Path
    sha256: str
    checksums: list
    report_path: Path | None = None
    log: list = field(default_factory=list)

    def __fspath__(self) -> str:           # Path(build_result) = the output file
        return str(self.output)

    @property
    def recalculated(self) -> list:
        return [r for r in self.checksums if r.corrected]

    @property
    def problems(self) -> list:
        return [r for r in self.checksums if not r.ok]


@dataclass
class EcuProject:
    folder: Path
    name: str = ""
    original: str = ""
    original_sha256: str = ""
    original_size: int = 0
    original_format: str = "raw"
    image_base: int = 0
    work: str = ""
    container: str = "bin"
    output: str = ""
    checksums: list = field(default_factory=list)
    correct_on_save: bool = True
    correct_on_build: bool = True
    maps: object = ""                 # map pack path, or a list of inline map definitions
    versions: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    KNOWN = ("name", "original", "original_sha256", "original_size", "original_format", "image_base", "work",
             "container", "output", "checksums", "correct_on_save", "correct_on_build", "maps", "versions")

    # ------------------------------------------------------------------ io
    @classmethod
    def load(cls, folder) -> "EcuProject":
        folder = Path(folder)
        p = folder / FILE
        d = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
        vers = []
        for i, v in enumerate(d.get("versions") or []):
            if isinstance(v, dict) and (v.get("id") or v.get("file")):
                vers.append(Version(str(v.get("id") or f"v{i + 1:03d}"), str(v.get("name") or v.get("note") or ""),
                                    str(v.get("note", "")), str(v.get("created") or v.get("time") or ""),
                                    str(v.get("file", "")), str(v.get("sha256", ""))))
        cont = str(d.get("container") or "bin").lower()
        maps = d.get("maps") or ""
        return cls(folder, str(d.get("name") or folder.name), str(d.get("original") or ""),
                   str(d.get("original_sha256") or ""), int(d.get("original_size") or 0),
                   str(d.get("original_format") or "raw"), to_int(d.get("image_base", d.get("base"))),
                   str(d.get("work") or d.get("working") or ""),
                   cont if cont in CONTAINERS else "bin", str(d.get("output") or ""),
                   blocks_from_json(d.get("checksums")), bool(d.get("correct_on_save", True)),
                   bool(d.get("correct_on_build", True)), maps if isinstance(maps, list) else str(maps), vers,
                   {k: v for k, v in d.items() if k not in cls.KNOWN + ("working", "base")})

    def save(self) -> Path:
        blocks = [b if isinstance(b, ChecksumBlock) else ChecksumBlock.from_dict(b) for b in self.checksums]
        self.checksums = blocks
        maps = self.maps
        if isinstance(maps, list):            # inline map definitions (dicts / MapDef objects)
            maps = [m.to_dict() if hasattr(m, "to_dict") else m for m in maps]
        d = {"name": self.name, "original": self.original, "original_sha256": self.original_sha256,
             "original_size": self.original_size, "original_format": self.original_format,
             "image_base": hx(self.image_base), "work": self.work, "container": self.container,
             "output": self.output, "checksums": blocks_to_json(blocks),
             "correct_on_save": self.correct_on_save, "correct_on_build": self.correct_on_build,
             "maps": maps or "", "versions": [v.to_dict() if isinstance(v, Version) else v for v in self.versions]}
        d.update(self.extra)
        p = self.folder / FILE
        p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return p

    # names other firmware tools use for the same things (radide/firmware/ui/adapters.py)
    @property
    def working(self) -> str:
        return self.work

    @property
    def base(self) -> int:
        return self.image_base

    def path(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else self.folder / p

    def rel(self, path) -> str:
        p = Path(path)
        try:
            return p.resolve().relative_to(self.folder.resolve()).as_posix()
        except ValueError:
            return str(p)

    @property
    def original_path(self) -> Path | None:
        return self.path(self.original) if self.original else None

    @property
    def work_path(self) -> Path | None:
        return self.path(self.work) if self.work else None

    @property
    def output_path(self) -> Path:
        if self.output:
            return self.path(self.output)
        return self.folder / "build" / f"{self.name or 'firmware'}_mod{self.output_ext()}"

    @property
    def maps_path(self) -> Path | None:
        return self.path(self.maps) if isinstance(self.maps, str) and self.maps else None

    def output_ext(self) -> str:
        if self.container == "same":
            return {"ihex": ".hex", "srec": ".s19"}.get(self.original_format, ".bin")
        return CONTAINERS.get(self.container, ".bin")

    def output_format(self) -> str:
        if self.container == "same":
            return self.original_format if self.original_format in ("ihex", "srec") else "raw"
        return CONTAINER_FMT.get(self.container, "raw")

    def set_container(self, container: str) -> None:
        if container not in CONTAINERS:
            raise EcuProjectError(f"unknown container '{container}' (bin, hex, s19, same)")
        self.container = container
        out = self.output_path
        self.output = self.rel(out.with_suffix(self.output_ext()))

    # ------------------------------------------------------------------ original + working copy
    def set_original(self, source, copy: bool = True, base: int = 0) -> Path:
        """Choose the original file: copied into original/ (read-only) and a fresh working copy made."""
        src = Path(source)
        if not src.is_file():
            raise EcuProjectError(f"File not found: {src}")
        if copy:
            dest = self.folder / "original" / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                make_writable(dest)
            if src.resolve() != dest.resolve():
                shutil.copyfile(src, dest)
            src = dest
        make_read_only(src)
        flat, fmt, img_base = load_image(src, base)
        self.original = self.rel(src)
        self.original_sha256 = sha256(src.read_bytes())
        self.original_size = len(flat)
        self.original_format = fmt
        self.image_base = img_base if fmt != "raw" else base
        if fmt in ("ihex", "srec") and self.container == "bin":
            # a HEX / S-record original builds back to the same container at its addresses by default
            self.container = "same"
            if self.output:
                self.output = self.rel(self.path(self.output).with_suffix(self.output_ext()))
        work = self.folder / "work" / (src.stem + ".bin")
        work.parent.mkdir(parents=True, exist_ok=True)
        if work.exists():
            make_writable(work)
        work.write_bytes(flat)
        self.work = self.rel(work)
        if not self.output:
            self.output = self.rel(self.folder / "build" / f"{src.stem}_mod{self.output_ext()}")
        return src

    def original_bytes(self) -> bytes:
        p = self.original_path
        if p is None or not p.is_file():
            raise EcuProjectError("The project has no original file (Project > ECU Project > Set Original...)")
        return load_image(p, self.image_base)[0]

    def check_original(self) -> tuple[bool, str]:
        p = self.original_path
        if p is None or not p.is_file():
            return False, "original file missing"
        h = sha256(p.read_bytes())
        if self.original_sha256 and h != self.original_sha256:
            return False, (f"the original file changed on disk (SHA-256 {h[:16]}... expected "
                           f"{self.original_sha256[:16]}...)")
        return True, f"original OK (SHA-256 {h[:16]}...)"

    def work_bytes(self) -> bytes:
        p = self.work_path
        if p is None or not p.is_file():
            data = self.original_bytes()
            self.write_work(data)
            return data
        return p.read_bytes()

    def write_work(self, data: bytes) -> Path:
        p = self.work_path
        if p is None:
            p = self.folder / "work" / f"{self.name or 'firmware'}.bin"
            self.work = self.rel(p)
        self._guard(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(bytes(data))
        return p

    def _guard(self, target: Path) -> None:
        o = self.original_path
        if o is not None and o.exists() and Path(target).resolve() == o.resolve():
            raise EcuProjectError("Refusing to write the original file - it is kept read-only")

    # ------------------------------------------------------------------ checksums
    def verify_checksums(self, data: bytes | None = None) -> list:
        return verify(self.work_bytes() if data is None else data, self.checksums)

    def correct_work(self) -> list:
        """Recalculate the checksum blocks inside the working copy (writes it only when a value changed)."""
        data = bytearray(self.work_bytes())
        res = correct(data, self.checksums)
        if any(r.corrected for r in res):
            self.write_work(bytes(data))
        return res

    def add_block(self, block: ChecksumBlock) -> None:
        self.checksums.append(block)

    # ------------------------------------------------------------------ versions
    def _next_id(self) -> str:
        n = 0
        for v in self.versions:
            try:
                n = max(n, int(v.id.lstrip("v")))
            except ValueError:
                pass
        return f"v{n + 1:03d}"

    def snapshot(self, name: str, note: str = "", data: bytes | None = None) -> Version:
        data = self.work_bytes() if data is None else bytes(data)
        vid = self._next_id()
        f = self.folder / "versions" / f"{vid}.bin"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        v = Version(vid, name or vid, note, now(), self.rel(f), sha256(data))
        self.versions.append(v)
        return v

    def add_version(self, data: bytes, note: str = "") -> Path:
        """Snapshot *data* as a new version (name = the note); returns the version file. Saves ecu.json."""
        v = self.snapshot(note or "", note, data)
        self.save()
        return self.path(v.file)

    def version(self, vid: str) -> Version | None:
        return next((v for v in self.versions if v.id == vid or v.name == vid), None)

    def version_bytes(self, vid: str) -> bytes:
        """'original', 'work', 'build' or a version id / name."""
        if vid == "original":
            return self.original_bytes()
        if vid == "work":
            return self.work_bytes()
        if vid == "build":
            p = self.output_path
            if not p.is_file():
                raise EcuProjectError("Not built yet")
            return load_image(p, self.image_base)[0]
        v = self.version(vid)
        if v is None:
            raise EcuProjectError(f"No version '{vid}'")
        return self.path(v.file).read_bytes()

    def restore(self, vid: str, keep_current: bool = True) -> Version | None:
        """Make version *vid* (or 'original') the working copy; the current working copy is saved first
        as an automatic version when it differs from every saved one."""
        data = self.version_bytes(vid)
        saved = None
        if keep_current and self.work_path is not None and self.work_path.is_file():
            cur = self.work_bytes()
            h = sha256(cur)
            if cur != data and all(v.sha256 != h for v in self.versions):
                saved = self.snapshot(f"Before restoring {vid}", "saved automatically")
        self.write_work(data)
        return saved

    def delete_version(self, vid: str) -> bool:
        v = self.version(vid)
        if v is None:
            return False
        try:
            self.path(v.file).unlink()
        except OSError:
            pass
        self.versions.remove(v)
        return True

    def label(self, vid: str) -> str:
        if vid in ("original", "work", "build"):
            return {"original": "Original", "work": "Working copy", "build": "Build output"}[vid]
        v = self.version(vid)
        return f"{v.id} {v.name}" if v else vid

    # ------------------------------------------------------------------ diff
    def map_pack(self):
        if isinstance(self.maps, list) and self.maps:
            try:
                from ..maps.model import MapPack
                return MapPack.from_dict({"maps": [m.to_dict() if hasattr(m, "to_dict") else m for m in self.maps]})
            except Exception:  # noqa: BLE001
                return None
        p = self.maps_path
        if p is None or not p.is_file():
            w = self.work_path
            if w is None:
                return None
            try:
                from ..maps.model import pack_path_for
                p = pack_path_for(w)
            except ImportError:
                return None
            if not p.is_file():
                return None
        try:
            from ..maps.model import MapPack
            return MapPack.load(p)
        except Exception:  # noqa: BLE001 - maps are optional; a bad pack only loses the map-level diff
            return None

    def diff(self, a: str = "original", b: str = "work", da: bytes | None = None,
             db: bytes | None = None) -> DiffResult:
        da = self.version_bytes(a) if da is None else da
        db = self.version_bytes(b) if db is None else db
        res = DiffResult(self.label(a), self.label(b), diff_ranges(da, db))
        res.bytes_changed = sum(e - s for s, e in res.ranges)
        spans = [sp for blk in self.checksums for x in blk.expand() for sp in x.stored_spans()]
        res.checksum_spans = [(s, e) for s, e in res.ranges if any(ss < e and se > s for ss, se in spans)]
        pack = self.map_pack()
        covered = []
        if pack is not None:
            import numpy as np
            for m in pack:
                rs = m.ranges()
                covered += rs
                if not any(s < e2 and e > s2 for s, e in res.ranges for s2, e2 in rs):
                    continue
                try:
                    va, vb = m.phys(da), m.phys(db)
                    ch = va != vb
                    delta = (vb - va)[ch]
                    mx = float(delta[np.argmax(np.abs(delta))]) if delta.size else 0.0
                    res.maps.append(MapChange(m.name, m.kind, int(ch.sum()), m.cells, round(mx, 6), m.unit,
                                              m.address))
                except Exception:  # noqa: BLE001 - a map past the end of the file etc.
                    continue
        res.unmapped = [(s, e) for s, e in res.ranges
                        if not any(s < ce and e > cs for cs, ce in covered + spans)]
        return res

    # ------------------------------------------------------------------ build / report / patches
    def build(self, log=print, write_report: bool = True) -> BuildResult:
        ok, msg = self.check_original()
        if not ok:
            raise EcuProjectError(f"Build stopped: {msg}")
        lines = [f"Build {self.name}: {msg}"]
        data = bytearray(self.work_bytes())
        if self.correct_on_build and self.checksums:
            results = correct(data, self.checksums)
        else:
            results = verify(bytes(data), self.checksums)
        lines += report(results, "Checksums").splitlines()
        out = self.output_path
        out = out.with_suffix(self.output_ext()) if out.suffix.lower() != self.output_ext() else out
        self._guard(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        blob = dump_image(bytes(data), self.output_format(), self.image_base)
        out.write_bytes(blob)
        lines.append(f"Output: {out} ({self.output_format()}, {len(blob):,} bytes, SHA-256 {sha256(blob)[:16]}...)")
        res = BuildResult(out, sha256(blob), results, log=lines)
        if write_report:
            from .report import modification_report
            rp = out.with_name(out.stem + ".report.txt")
            rp.write_text(modification_report(self, bytes(data), results), encoding="utf-8")
            res.report_path = rp
            lines.append(f"Report: {rp}")
        for ln in lines:
            log(ln)
        return res

    def export_patch(self, path, fmt: str = "", target: str = "build") -> Path:
        """An IPS / BPS / UPS of the modification against the original (``target``: 'build' = the working copy
        with corrected checksums, 'work' = the working copy as it is, or a version id)."""
        from ...retro.rom.patches import create_patch
        p = Path(path)
        fmt = (fmt or p.suffix.lstrip(".") or "bps").lower()
        src = self.original_bytes()
        if target == "build":
            data = bytearray(self.work_bytes())
            if self.checksums:
                correct(data, self.checksums)
            tgt = bytes(data)
        else:
            tgt = self.version_bytes(target)
        blob = create_patch(src, tgt, fmt, metadata=f"RAD IDE ECU project {self.name}")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(blob)
        return p

    def import_patch(self, path, base: str = "original", note: str = "") -> Version | None:
        """Apply an IPS / BPS / UPS to the original (or the working copy) and make it the working copy.
        The current working copy is saved as a version first when it has unsaved changes."""
        from ...retro.rom.patches import apply_patch
        p = Path(path)
        src = self.original_bytes() if base == "original" else self.work_bytes()
        new = apply_patch(src, p.read_bytes())
        saved = None
        if self.work_path is not None and self.work_path.is_file():
            cur = self.work_bytes()
            if cur != new and all(v.sha256 != sha256(cur) for v in self.versions):
                saved = self.snapshot(f"Before importing {p.name}", "saved automatically")
        self.write_work(new)
        self.snapshot(f"Imported {p.name}", note or f"patch applied to the {base}")
        return saved


def make_read_only(p: Path) -> None:
    try:
        os.chmod(p, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    except OSError:
        pass


def make_writable(p: Path) -> None:
    try:
        os.chmod(p, stat.S_IREAD | stat.S_IWRITE)
    except OSError:
        pass


def new_project(folder, name: str = "", original=None, copy: bool = True, base: int = 0) -> EcuProject:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    ep = EcuProject(folder, name or folder.name)
    for sub in ("original", "work", "versions", "build", "profiles", "maps"):
        (folder / sub).mkdir(exist_ok=True)
    if original is not None:
        ep.set_original(original, copy, base)
    ep.save()
    return ep


def is_ecu_project(folder) -> bool:
    return (Path(folder) / FILE).is_file()


__all__ = ["EcuProject", "EcuProjectError", "Version", "DiffResult", "MapChange", "BuildResult", "new_project",
           "is_ecu_project", "diff_ranges", "load_image", "dump_image", "sha256", "FILE", "CONTAINERS"]
