"""Native program (PE, x86 / x64) -> a NASM-syntax disassembly listing (``<Program>_disasm.asm``).

Used by the native exe importer (native.py adds the listing to ``_original/recovered``) and by
``export_project(exe, dest)``, which writes a folder that File > Open Folder opens as an Assembly project
(radide/foreign/asm_folder.py)::

    python -m radide.importers.exe.asm_listing Program.exe OutFolder

The listing is for STUDY: functions found by the capstone analysis of native.py (entry point, exports, COFF
symbols, calls), local jump targets as ``.L<address>`` labels, calls to imports as ``call [rel MessageBoxA]``
with an ``extern`` list, referenced strings in a ``.data`` section, and the original address of every
instruction as a comment.  Re-assembling it gives a program only for small, simple executables: relocations,
data tables, resources and code the analysis did not reach are not reconstructed.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_SIZE = {"xmmword": "oword", "ymmword": "yword", "zmmword": "zword", "tbyte": "tword", "xword": "tword"}


def _label(name: str) -> str:
    n = re.sub(r"[^\w.?@$]", "_", name or "")
    if not n or n[0].isdigit():
        n = "f_" + n
    return n


def _nasm_operands(op: str, insn_addr: int, size: int, labels: dict, iat: dict, strings: dict, is64: bool,
                   used_imports: set, used_strings: set) -> str:
    """capstone Intel operands -> NASM operands (no 'ptr', rip-relative -> [rel label], targets -> labels)."""
    s = op
    for k, v in _SIZE.items():
        s = re.sub(rf"\b{k}\b", v, s)
    s = re.sub(r"\s+ptr\b", "", s)
    s = re.sub(r"\b([cdefgs]s):\[", r"[\1:", s)          # fs:[x] -> [fs:x]

    def rip(m):
        sign, disp = m.group(1), int(m.group(2), 16)
        target = insn_addr + size + (disp if sign == "+" else -disp)
        return "[rel " + _target_name(target, labels, iat, strings, used_imports, used_strings) + "]"
    s = re.sub(r"\[rip\s*([+-])\s*(0x[0-9a-fA-F]+)\]", rip, s)

    def absolute(m):                                      # [0x402000] (32-bit IAT / data)
        target = int(m.group(1), 16)
        name = _target_name(target, labels, iat, strings, used_imports, used_strings, fallback=False)
        return f"[{name}]" if name else m.group(0)
    s = re.sub(r"\[(0x[0-9a-fA-F]{5,})\]", absolute, s)
    return s


def _target_name(va: int, labels: dict, iat: dict, strings: dict, used_imports: set, used_strings: set,
                 fallback: bool = True) -> str:
    if va in iat:
        used_imports.add(iat[va])
        return _label(iat[va])
    if va in labels:
        return labels[va]
    if va in strings:
        used_strings.add(va)
        return f"str_{va:X}"
    return f"0x{va:X}" if fallback else ""


def nasm_listing(path, an=None, max_funcs: int = 600, max_insns: int = 120_000) -> str:
    """The listing text of *path* (a NativeAnalysis from native.analyse() may be passed in *an*)."""
    import pefile
    from capstone import CS_ARCH_X86, CS_MODE_32, CS_MODE_64, Cs
    from .native import analyse
    path = Path(path)
    if an is None:
        an = analyse(path)
    pe = pefile.PE(str(path))
    try:
        is64 = pe.FILE_HEADER.Machine == 0x8664
        if an.machine not in ("x64", "x86"):
            return f"; {path.name}: disassembly of {an.machine} code is not supported (only x86 / x64)\n"
        md = Cs(CS_ARCH_X86, CS_MODE_64 if is64 else CS_MODE_32)
        funcs = sorted(an.funcs.values(), key=lambda f: f.addr)[:max_funcs]
        labels = {f.addr: _label(f.name) for f in funcs}
        taken = set()
        for va, n in list(labels.items()):                 # unique function labels
            base, i = n, 2
            while n.lower() in taken:
                n = f"{base}_{i}"
                i += 1
            taken.add(n.lower())
            labels[va] = n
        body: list[str] = []
        used_imports: set = set()
        used_strings: set = set()
        total = 0
        for f in funcs:
            raw = b""
            try:
                raw = pe.get_data(f.addr - an.image_base, max(f.size, 1) + 16)
            except Exception:  # noqa: BLE001
                pass
            insns = list(md.disasm(raw, f.addr))
            end = f.addr + max(f.size, 1)
            insns = [i for i in insns if i.address < end] or insns[:1]
            local = {}
            for i in insns:                                  # local branch targets
                if i.mnemonic.startswith("j") or i.mnemonic.startswith("loop"):
                    m = re.fullmatch(r"0x([0-9a-f]+)", i.op_str)
                    if m:
                        t = int(m.group(1), 16)
                        if f.addr < t < end and t not in labels:
                            local[t] = f".L{t:X}"
            body += ["", f"; ---- {f.name}  (0x{f.addr:X}, {f.size} bytes)", f"{labels[f.addr]}:"]
            for i in insns:
                total += 1
                if total > max_insns:
                    body.append("    ; ... listing truncated (instruction limit)")
                    break
                if i.address in local:
                    body.append(f"{local[i.address]}:")
                mn, ops = i.mnemonic, i.op_str
                if mn == "movabs":
                    mn = "mov"
                m = re.fullmatch(r"0x([0-9a-f]+)", ops)
                if m and (mn.startswith("j") or mn in ("call", "loop", "loope", "loopne")):
                    t = int(m.group(1), 16)
                    ops = local.get(t) or labels.get(t) or ops
                else:
                    ops = _nasm_operands(ops, i.address, i.size, labels, an.iat, an.strings, is64, used_imports,
                                         used_strings)
                text = f"    {mn} {ops}".rstrip()
                body.append(f"{text:<48}; {i.address:08X}  {i.bytes.hex(' ')}")
            if total > max_insns:
                break
        head = [f"; {path.name}: NASM-syntax disassembly listing made by RAD IDE (File > Import > Program (.exe))",
                f"; machine {an.machine}, image base 0x{an.image_base:X}, entry point 0x{an.entry:X}, "
                f"{len(funcs)} function(s){' (analysis stopped at its limit)' if an.truncated else ''}",
                "; For study: relocations, data tables and code the analysis did not reach are not reconstructed,",
                "; so re-assembling it works only for small, simple programs.",
                "", "bits 64" if is64 else "bits 32"]
        if is64:
            head.append("default rel")
        head.append("")
        for name in sorted(used_imports, key=str.lower):
            head.append(f"extern {_label(name)}")
        entry = labels.get(an.entry)
        if entry:
            head.append(f"global {entry}")
        head += ["", "section .text"]
        data = ["", "section .data"] if used_strings else []
        for va in sorted(used_strings):
            s = an.strings.get(va, "")
            parts, cur = [], ""
            for ch in s:
                if 32 <= ord(ch) < 127 and ch != '"':
                    cur += ch
                else:
                    if cur:
                        parts.append(f'"{cur}"')
                        cur = ""
                    parts.append(str(ord(ch) & 0xFF if ord(ch) < 256 else ord("?")))
            if cur:
                parts.append(f'"{cur}"')
            data.append(f"str_{va:X}: db {', '.join(parts + ['0'])}")
        return "\n".join(head + body + data) + "\n"
    finally:
        try:
            pe.close()
        except Exception:  # noqa: BLE001
            pass


def export_project(exe, dest, an=None) -> Path:
    """Write ``<dest>/<Program>_disasm.asm`` + README.md; returns the .asm path (open *dest* with Open Folder)."""
    exe, dest = Path(exe), Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^\w.-]+", "_", exe.stem) or "Program"
    out = dest / f"{stem}_disasm.asm"
    out.write_text(nasm_listing(exe, an), encoding="utf-8")
    (dest / "README.md").write_text(
        f"# {exe.name} - disassembly\n\n"
        f"`{out.name}` is a NASM-syntax listing of the machine code of `{exe.name}` made by RAD IDE "
        "(capstone). Every instruction keeps its original address and bytes as a comment.\n\n"
        "Open this folder with **File > Open Folder** to browse it as an Assembly project. It is meant for "
        "study; re-assembling it works only for small, simple programs.\n", encoding="utf-8")
    return out


if __name__ == "__main__":               # python -m radide.importers.exe.asm_listing Program.exe OutFolder
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    print(export_project(sys.argv[1], sys.argv[2]))
