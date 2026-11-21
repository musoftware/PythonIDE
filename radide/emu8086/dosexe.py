"""Export an 8086 program as a real DOS file: ``.COM`` or MZ ``.EXE`` (runs in DOSBox / FreeDOS / MS-DOS).

    data = com_image(prog)                         # COM: the bytes from offset 100h of the one segment
    data = mz_image(text, "main.asm")              # EXE: MZ header + relocation table + image
    path = export_file(Path("main.asm"))           # main.com or main.exe next to the source (the program's kind)
    prog = load_dos_file(data, "x.exe")            # back into a Program the emulator can run (tests, File > Open)

The assembler lays a program out for one load segment (radide/emu8086/assembler.py). An EXE needs to know which
words hold a *segment value* (``mov ax, @data``, ``mov ax, seg x``, far pointers ``dd far_label``, far
``call`` / ``jmp``): DOS adds the real load segment to them. Instead of tracking that inside the encoder, the
program is assembled twice at two load segments (0700h and 1700h): the words whose values differ by exactly
1000h are the segment fixups. Their values relative to the image start become the stored words and their
positions become the MZ relocation table.

MZ header (28 bytes + 4 per relocation, rounded up to 16): ``e_cblp`` / ``e_cp`` (file size in 512-byte pages),
``e_crlc`` (relocations), ``e_cparhdr`` (header paragraphs), ``e_minalloc`` (paragraphs the program needs after
the image: ``?`` data at the end, the stack), ``e_maxalloc`` FFFFh, ``e_ss`` / ``e_sp``, ``e_ip`` / ``e_cs``
(relative to the image), ``e_lfarlc`` = 1Ch.
"""
from __future__ import annotations

import struct
from pathlib import Path

from .assembler import Program, assemble

LOAD_A, LOAD_B = 0x0700, 0x1700


class ExportError(Exception):
    pass


def _image(prog: Program, start_linear: int) -> bytearray:
    end = max((lin + len(data) for lin, data in prog.chunks), default=start_linear)
    img = bytearray(max(0, end - start_linear))
    for lin, data in prog.chunks:
        o = lin - start_linear
        if o < 0:
            raise ExportError("program data below its load address")
        img[o:o + len(data)] = data
    return img


def com_image(prog: Program) -> bytes:
    """The bytes of a COM program (loaded at offset 100h of its segment)."""
    if not prog.com:
        raise ExportError("E-EXPORT-COM")
    if prog.errors:
        raise ExportError(str(prog.errors[0]))
    start = (prog.load_seg << 4) + 0x100
    img = _image(prog, start)
    if prog.entry_ip != 0x100:
        raise ExportError("a COM program starts at 100h: put its first instruction right after org 100h")
    if len(img) > 0xFF00:
        raise ExportError("a COM program must be smaller than 64 KB")
    return bytes(img)


def mz_image(text: str, filename: str = "main.asm", include_dir=None, read_include=None) -> bytes:
    """An MZ .EXE of the program in *text* (assembled twice to find the segment fixups)."""
    a = assemble(text, filename, load_seg=LOAD_A, include_dir=include_dir, read_include=read_include)
    if a.errors:
        raise ExportError(str(a.errors[0]))
    if a.com:
        raise ExportError("this is a COM program (.model tiny / org 100h): export it as .COM")
    b = assemble(text, filename, load_seg=LOAD_B, include_dir=include_dir, read_include=read_include)
    img_a, img_b = _image(a, LOAD_A << 4), _image(b, LOAD_B << 4)
    if len(img_a) != len(img_b):
        raise ExportError("the program's layout depends on its load address")
    delta = LOAD_B - LOAD_A
    relocs: list[int] = []
    img = bytearray(img_a)
    i = 0
    while i < len(img_a):
        if img_a[i] == img_b[i]:
            i += 1
            continue
        # a differing byte = the high byte of a segment word (+1000h leaves the low byte as it is)
        start = max(0, i - 1)
        if start + 2 > len(img_a):
            raise ExportError(f"cannot relocate the byte at {i:04X}h")
        wa = struct.unpack_from("<H", img_a, start)[0]
        wb = struct.unpack_from("<H", img_b, start)[0]
        if (wb - wa) & 0xFFFF != delta:
            raise ExportError(f"cannot relocate the word at {start:04X}h ({wa:04X}h / {wb:04X}h)")
        struct.pack_into("<H", img, start, (wa - LOAD_A) & 0xFFFF)
        relocs.append(start)
        i = start + 2
    nrel = len(relocs)
    header_paras = (0x1C + 4 * nrel + 15) // 16
    header_size = header_paras * 16
    image_paras = (len(img) + 15) // 16
    end_paras = (a.end_linear >> 4) - LOAD_A
    min_alloc = max(0, end_paras - image_paras)
    if a.ss >= LOAD_A:                                # the stack segment must fit in the allocation
        stack_top = (a.ss - LOAD_A) * 16 + (a.sp or 0x10000)
        min_alloc = max(min_alloc, (stack_top + 15) // 16 - image_paras)
    total = header_size + len(img)
    hdr = bytearray(header_size)
    struct.pack_into("<2sHHHHHHHHHHHHH", hdr, 0, b"MZ", total % 512, (total + 511) // 512, nrel, header_paras,
                     min(min_alloc, 0xFFFF), 0xFFFF, (a.ss - LOAD_A) & 0xFFFF, a.sp & 0xFFFF, 0,
                     a.entry_ip & 0xFFFF, (a.entry_cs - LOAD_A) & 0xFFFF, 0x1C, 0)
    for k, off in enumerate(relocs):
        struct.pack_into("<HH", hdr, 0x1C + 4 * k, off & 0x0F, off >> 4)    # offset, segment (normalized)
    return bytes(hdr + img)


def export_file(source: Path, out: Path | None = None, kind: str = "") -> Path:
    """Write the program of *source* as <name>.com (COM programs) or <name>.exe; returns the written path."""
    source = Path(source)
    text = source.read_text(encoding="utf-8", errors="replace")
    prog = assemble(text, str(source))
    if prog.errors:
        raise ExportError(str(prog.errors[0]))
    kind = kind or ("com" if prog.com else "exe")
    data = com_image(prog) if kind == "com" else mz_image(text, str(source))
    out = Path(out) if out else source.with_suffix("." + kind)
    out.write_bytes(data)
    return out


def load_dos_file(data: bytes, name: str = "", load_seg: int = 0x0700) -> Program:
    """A Program the emulator can run from the bytes of a .COM or MZ .EXE file (the way DOS loads it:
    the PSP at *load_seg*, a COM at PSP:0100h, an EXE image right after the PSP with its fixups applied)."""
    if data[:2] in (b"MZ", b"ZM"):
        (_m, cblp, cp, nrel, hparas, minalloc, _maxalloc, ss, sp, _csum, ip, cs, lfarlc,
         _ovno) = struct.unpack_from("<2sHHHHHHHHHHHHH", data, 0)
        size = (cp - 1) * 512 + cblp if cblp else cp * 512
        img = bytearray(data[hparas * 16:size])
        base = load_seg + 0x10                        # the image starts right after the 256-byte PSP
        for k in range(nrel):
            off, seg = struct.unpack_from("<HH", data, lfarlc + 4 * k)
            p = seg * 16 + off
            v = struct.unpack_from("<H", img, p)[0]
            struct.pack_into("<H", img, p, (v + base) & 0xFFFF)
        prog = Program(com=False, load_seg=base)
        prog.chunks = [(base << 4, bytes(img))]
        prog.entry_cs, prog.entry_ip = (base + cs) & 0xFFFF, ip
        prog.ss, prog.sp = (base + ss) & 0xFFFF, sp
        prog.ds = prog.es = load_seg
        prog.end_linear = ((base + (len(img) + 15) // 16 + minalloc) << 4) & 0xFFFFF
    else:
        prog = Program(com=True, load_seg=load_seg)
        prog.chunks = [((load_seg << 4) + 0x100, bytes(data))]
        prog.entry_cs = prog.ds = prog.es = prog.ss = load_seg
        prog.entry_ip, prog.sp = 0x100, 0xFFFE
        prog.end_linear = ((load_seg + 0x1000) << 4) & 0xFFFFF
    prog.files = [name] if name else []
    return prog


__all__ = ["ExportError", "com_image", "export_file", "load_dos_file", "mz_image"]
