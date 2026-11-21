"""PeDocument: one Windows program (.exe / .dll) opened for editing in the PE / MFC workbench.

    doc = PeDocument.open("app.exe")
    doc.resources                                  # [ResEntry] (edited in memory)
    doc.set_resource(type, name, lang, data)       # add / replace (undoable)
    doc.patch_instructions(va, "mov eax, 1", count=1)   # in place, same size or smaller (NOP padded)
    doc.mfc_retarget(entry, new_pfn)               # point a message-map entry at another existing function
    doc.mfc_remove_entry(map, index) / doc.mfc_add_entry(map, ...)   # add only where space was freed
    doc.undo() / doc.redo()
    path, notes = doc.save()                        # new file "<name>_edited.exe" (+ .bak of what it replaces)

Patching is deliberately limited: no new code is added to the program (no code caves); instructions are
replaced in place by instructions of the same size or smaller.
"""
from __future__ import annotations

import copy
import shutil
import struct
from dataclasses import dataclass
from pathlib import Path

from . import mfc as M
from . import resources as R
from .image import (DIR_RESOURCE, DLLCHAR_DYNAMIC_BASE, PEError, PEImage, REL_DIR64, REL_HIGHLOW,
                    SCN_CNT_INITIALIZED_DATA, SCN_MEM_READ, align)

MAX_UNDO = 60


class EditError(ValueError):
    pass


@dataclass
class PatchRecord:
    desc: str
    va: int
    old: bytes
    new: bytes


class PeDocument:
    def __init__(self, data: bytes, path: Path | None = None):
        self.path = Path(path) if path else None
        self.original = bytes(data)
        self.img = PEImage(bytearray(data))
        self.resources: list[R.ResEntry] = R.read_tree(self.img)
        self.res_dirty = False
        self.reloc_add: set[int] = set()
        self.reloc_remove: set[int] = set()
        self.patches: list[PatchRecord] = []
        self.spare: dict[int, int] = {}          # entries_va -> slots (incl. terminator) freed by removals
        self._undo: list[tuple] = []
        self._redo: list[tuple] = []
        self.saved_state = self._state()
        self._analysis = None
        self._maps = None
        self.listeners = []

    @classmethod
    def open(cls, path) -> "PeDocument":
        p = Path(path)
        data = p.read_bytes()
        return cls(data, p)

    # ================================================================ state / undo
    def _state(self) -> tuple:
        return (bytes(self.img.data), copy.deepcopy(self.resources), self.res_dirty, set(self.reloc_add),
                set(self.reloc_remove), list(self.patches), dict(self.spare))

    def _restore(self, st: tuple) -> None:
        data, res, dirty, ra, rr, patches, spare = st
        code_changed = bytes(self.img.data) != data
        self.img = PEImage(bytearray(data))
        self.resources = copy.deepcopy(res)
        self.res_dirty, self.reloc_add, self.reloc_remove = dirty, set(ra), set(rr)
        self.patches, self.spare = list(patches), dict(spare)
        if code_changed:
            self._maps = None
            if self._analysis is not None:
                self._analysis.img = self.img
        self._changed()

    def checkpoint(self) -> None:
        """Call before every edit (it is what Undo goes back to)."""
        self._undo.append(self._state())
        if len(self._undo) > MAX_UNDO:
            self._undo.pop(0)
        self._redo.clear()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(self._state())
        self._restore(self._undo.pop())
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(self._state())
        self._restore(self._redo.pop())
        return True

    def is_modified(self) -> bool:
        st = self._state()
        return st[0] != self.saved_state[0] or self.res_dirty != self.saved_state[2] or \
            st[1] != self.saved_state[1] or st[3:5] != self.saved_state[3:5]

    def _changed(self) -> None:
        for cb in list(self.listeners):
            try:
                cb()
            except Exception:  # noqa: BLE001
                pass

    # ================================================================ analysis (cached)
    @property
    def is64(self) -> bool:
        return self.img.is64

    def analysis(self, progress=None):
        if self._analysis is None:
            from .code import CodeAnalysis
            an = CodeAnalysis(self.img)
            an.analyze(progress)
            for m in self.message_maps():
                for e in m.entries:
                    an.add_function(e.pfn, None, "mfc")
            self._name_handlers(an)
            an.reclose()
            self._analysis = an
        return self._analysis

    def _name_handlers(self, an) -> None:
        for m in self.message_maps():
            cls = m.class_name or f"Class{m.va:X}"
            for e in m.entries:
                f = an.functions.get(e.pfn)
                if f is None or not f.name.startswith("sub_"):
                    continue
                if e.msg == M.WM_COMMAND and e.code == M.CN_UPDATE_COMMAND_UI:
                    n = f"OnUpdate{e.id}"
                elif e.msg in (M.WM_COMMAND, M.WM_NOTIFY):
                    n = f"On{e.event_text().split()[0].replace('/', '').replace('WM_NOTIFY', 'Notify')}_{e.id}"
                else:
                    n = "On" + M.message_name(e.msg).replace("WM_", "").replace("+", "_").title().replace("_", "")
                an.rename(e.pfn, f"{cls}::{n}")

    def message_maps(self) -> list[M.MsgMap]:
        if self._maps is None:
            self._maps = M.find_message_maps(self.img)
        return self._maps

    def refresh_maps(self) -> list[M.MsgMap]:
        self._maps = None
        return self.message_maps()

    # ================================================================ resources
    def find(self, rtype, name=None, lang=None) -> list[R.ResEntry]:
        return [e for e in self.resources if e.type == rtype and (name is None or e.name == name)
                and (lang is None or e.lang == lang)]

    def get(self, rtype, name, lang=None) -> R.ResEntry | None:
        r = self.find(rtype, name, lang)
        return r[0] if r else None

    def set_resource(self, rtype, name, lang: int, data: bytes, checkpoint: bool = True) -> None:
        if checkpoint:
            self.checkpoint()
        for e in self.resources:
            if e.key == (rtype, name, lang):
                e.data = bytes(data)
                break
        else:
            self.resources.append(R.ResEntry(rtype, name, lang, bytes(data)))
        self.res_dirty = True
        self._changed()

    def remove_resource(self, rtype, name, lang: int, checkpoint: bool = True) -> None:
        if checkpoint:
            self.checkpoint()
        self.resources = [e for e in self.resources if e.key != (rtype, name, lang)]
        self.res_dirty = True
        self._changed()

    def next_id(self, rtype) -> int:
        ids = [e.name for e in self.resources if e.type == rtype and isinstance(e.name, int)]
        return max(ids, default=0) + 1

    # --- typed helpers
    def dialog(self, name, lang) -> R.Dialog:
        return R.parse_dialog(self.get(R.RT_DIALOG, name, lang).data)

    def set_dialog(self, name, lang, d: R.Dialog) -> None:
        self.set_resource(R.RT_DIALOG, name, lang, R.build_dialog(d))

    def menu(self, name, lang) -> R.Menu:
        return R.parse_menu(self.get(R.RT_MENU, name, lang).data)

    def set_menu(self, name, lang, m: R.Menu) -> None:
        self.set_resource(R.RT_MENU, name, lang, R.build_menu(m))

    def strings(self, lang: int | None = None) -> dict[int, dict[int, str]]:
        """{lang: {string id: text}}"""
        out: dict[int, dict[int, str]] = {}
        for e in self.resources:
            if e.type == R.RT_STRING and isinstance(e.name, int) and (lang is None or e.lang == lang):
                out.setdefault(e.lang, {}).update(R.parse_string_block(e.data, e.name))
        return out

    def set_strings(self, lang: int, strings: dict[int, str]) -> None:
        """Replace every string-table block of *lang* with *strings*."""
        self.checkpoint()
        self.resources = [e for e in self.resources if not (e.type == R.RT_STRING and e.lang == lang)]
        for bid, data in sorted(R.build_string_blocks({k: v for k, v in strings.items() if v != ""}).items()):
            self.resources.append(R.ResEntry(R.RT_STRING, bid, lang, data))
        self.res_dirty = True
        self._changed()

    def set_string(self, sid: int, text: str, lang: int) -> None:
        cur = self.strings(lang).get(lang, {})
        cur[sid] = text
        self.set_strings(lang, cur)

    def string(self, sid: int, lang: int | None = None) -> str | None:
        for lg, items in self.strings(lang).items():
            if sid in items:
                return items[sid]
        return None

    def version(self) -> tuple[R.ResEntry, R.VersionInfo] | None:
        e = next((e for e in self.resources if e.type == R.RT_VERSION), None)
        return (e, R.parse_version(e.data)) if e else None

    def icon_file(self, entry: R.ResEntry) -> bytes:
        cursor = entry.type == R.RT_GROUP_CURSOR
        img_type = R.RT_CURSOR if cursor else R.RT_ICON
        images = {e.name: e.data for e in self.resources if e.type == img_type and isinstance(e.name, int)}
        return R.group_to_file(entry.data, images, cursor)

    def replace_icon_group(self, entry: R.ResEntry, file_data: bytes) -> None:
        """Replace an icon / cursor group with the images of an .ico / .cur file."""
        cursor = entry.type == R.RT_GROUP_CURSOR
        img_type = R.RT_CURSOR if cursor else R.RT_ICON
        old_ids = {g["id"] for g in R.group_entries(entry.data)}
        used_elsewhere = set()
        for e in self.resources:
            if e.type == entry.type and e.key != entry.key:
                used_elsewhere |= {g["id"] for g in R.group_entries(e.data)}
        self.checkpoint()
        self.resources = [e for e in self.resources
                          if not (e.type == img_type and e.name in old_ids and e.name not in used_elsewhere)]
        first = self.next_id(img_type)
        group, images = R.file_to_group(file_data, first, cursor)
        for rid, data in images.items():
            self.resources.append(R.ResEntry(img_type, rid, entry.lang, data))
        self.set_resource(entry.type, entry.name, entry.lang, group, checkpoint=False)

    def add_icon_group(self, name, lang: int, file_data: bytes, cursor: bool = False) -> None:
        img_type = R.RT_CURSOR if cursor else R.RT_ICON
        self.checkpoint()
        group, images = R.file_to_group(file_data, self.next_id(img_type), cursor)
        for rid, data in images.items():
            self.resources.append(R.ResEntry(img_type, rid, lang, data))
        self.set_resource(R.RT_GROUP_CURSOR if cursor else R.RT_GROUP_ICON, name, lang, group, checkpoint=False)

    def replace_all_resources(self, entries: list[R.ResEntry]) -> None:
        self.checkpoint()
        self.resources = [copy.copy(e) for e in entries]
        self.res_dirty = True
        self._changed()

    def languages(self) -> list[int]:
        return sorted({e.lang for e in self.resources})

    # ================================================================ code patches (in place only)
    def read_va(self, va: int, n: int) -> bytes:
        return self.img.read_va(va, n)

    def _check_code(self, va: int, n: int) -> None:
        if not self.img.is_code_va(va) or not self.img.is_code_va(va + n - 1):
            raise EditError(f"0x{va:X} is not inside a code section.")

    def _neutralize_relocs(self, va: int, n: int) -> list[int]:
        """Relocation entries inside a patched range would change the new bytes at load time: drop them."""
        lo, hi = va - self.img.image_base, va - self.img.image_base + n
        hit = [r for r, t in self.img.relocations() if t != 0 and lo - 7 < r < hi and r not in self.reloc_remove]
        hit = [r for r in hit if r + (8 if t_is64(self) else 4) > lo]
        self.reloc_remove.update(hit)
        self.reloc_add.difference_update(hit)
        return hit

    def plan_instruction_patch(self, va: int, asm_text: str, count: int = 1) -> tuple[bytes, bytes, list]:
        """(new bytes padded with NOPs, original bytes, original lines) or raises EditError."""
        from .asm import AsmError, assemble
        an = self.analysis()
        lines = an.disasm(va, 16 * max(1, count) + 16, max_lines=max(1, count))
        if len(lines) < count or any(ln.mnemonic == "db" for ln in lines):
            raise EditError(f"Cannot decode {count} instruction(s) at 0x{va:X}.")
        span = sum(ln.size for ln in lines)
        self._check_code(va, span)
        try:
            new = assemble(asm_text, va, self.is64)
        except AsmError as e:
            raise EditError(str(e)) from None
        if not new:
            raise EditError("Nothing to assemble.")
        if len(new) > span:
            raise EditError(f"The new code needs {len(new)} bytes but the {count} instruction(s) it replaces "
                            f"have {span}. Only same-size or smaller edits are allowed (no code is added to "
                            "the program). Replace more instructions or write shorter code.")
        old = self.read_va(va, span)
        return new + b"\x90" * (span - len(new)), old, lines

    def patch_instructions(self, va: int, asm_text: str, count: int = 1, desc: str = "") -> PatchRecord:
        new, old, lines = self.plan_instruction_patch(va, asm_text, count)
        return self._patch(va, old, new, desc or f"{'; '.join(ln.mnemonic + ' ' + ln.op_str for ln in lines)}"
                           f"  ->  {asm_text.strip()}")

    def patch_bytes(self, va: int, new: bytes, desc: str = "") -> PatchRecord:
        """Overwrite bytes in place (same length)."""
        old = self.read_va(va, len(new))
        return self._patch(va, old, bytes(new), desc or f"bytes at 0x{va:X}")

    def nop_instructions(self, va: int, count: int = 1) -> PatchRecord:
        lines = self.analysis().disasm(va, 16 * count + 16, max_lines=count)
        span = sum(ln.size for ln in lines)
        self._check_code(va, span)
        return self._patch(va, self.read_va(va, span), b"\x90" * span, f"NOP {count} instruction(s) at 0x{va:X}")

    def _patch(self, va: int, old: bytes, new: bytes, desc: str) -> PatchRecord:
        if len(old) != len(new):
            raise EditError("In-place patches must keep the size.")
        self.checkpoint()
        try:
            self.img.write_va(va, new)
        except PEError as e:
            self._undo.pop()
            raise EditError(str(e)) from None
        dropped = self._neutralize_relocs(va, len(new)) if old != new else []
        rec = PatchRecord(desc + (f"  [{len(dropped)} relocation(s) dropped]" if dropped else ""), va, old, new)
        self.patches.append(rec)
        if self._analysis is not None:
            self._analysis.img = self.img
        self._changed()
        return rec

    def revert_patch(self, rec: PatchRecord) -> None:
        self.checkpoint()
        self.img.write_va(rec.va, rec.old)
        lo = rec.va - self.img.image_base
        orig_relocs = {r for r, t in PEImage(bytearray(self.original)).relocations() if lo - 7 < r < lo + len(rec.old)}
        self.reloc_remove.difference_update(orig_relocs)
        self.patches = [p for p in self.patches if p is not rec]
        self._changed()

    def aslr_enabled(self) -> bool:
        return bool(self.img.dll_characteristics & DLLCHAR_DYNAMIC_BASE)

    # ================================================================ MFC message-map edits
    def _entry_values(self, m: M.MsgMap) -> list[tuple]:
        return [(e.msg, e.code, e.id, e.last_id, e.sig, e.pfn) for e in m.entries]

    def valid_handler_targets(self) -> set[int]:
        """Existing functions a message-map entry may point at (known functions in code sections)."""
        an = self.analysis()
        return {va for va in an.functions if self.img.is_code_va(va)}

    def mfc_retarget(self, entry: M.MsgEntry, new_pfn: int) -> None:
        if new_pfn not in self.valid_handler_targets():
            raise EditError(f"0x{new_pfn:X} is not the start of a known function in this program. Pick an "
                            "existing function (for example another handler).")
        self.checkpoint()
        P = self.img.ptr_size
        self.img.write_va(entry.va + 16 + P, struct.pack("<Q" if P == 8 else "<I", new_pfn))
        self.patches.append(PatchRecord(f"Message map: entry {entry.macro()} -> 0x{new_pfn:X}",
                                        entry.va + 16 + P, struct.pack("<Q" if P == 8 else "<I", entry.pfn),
                                        struct.pack("<Q" if P == 8 else "<I", new_pfn)))
        self.refresh_maps()
        self._changed()

    def _write_table(self, m: M.MsgMap, values: list[tuple], slots: int, desc: str) -> None:
        E = M.entry_size(self.img)
        old_vals = self._entry_values(m)
        blob = b"".join(M.pack_entry(self.img, *v) for v in values)
        blob += b"\0" * (slots * E - len(blob))
        old_blob = self.read_va(m.entries_va, slots * E)
        self.img.write_va(m.entries_va, blob)
        if self.img.relocations():
            before = set(M.pointer_slots(self.img, m.entries_va, old_vals))
            after = set(M.pointer_slots(self.img, m.entries_va, values))
            for r in before - after:
                self.reloc_remove.add(r)
                self.reloc_add.discard(r)
            for r in after - before:
                self.reloc_add.add(r)
                self.reloc_remove.discard(r)
        self.patches.append(PatchRecord(desc, m.entries_va, old_blob, blob))

    def mfc_remove_entry(self, m: M.MsgMap, index: int) -> None:
        if not 0 <= index < len(m.entries):
            raise EditError("No such entry.")
        self.checkpoint()
        vals = self._entry_values(m)
        removed = m.entries[index]
        slots = max(self.spare.get(m.entries_va, 0), len(vals) + 1)
        del vals[index]
        self._write_table(m, vals, slots, f"Message map {m.label}: removed {removed.macro()}")
        self.spare[m.entries_va] = slots
        self.refresh_maps()
        self._changed()

    def free_slots(self, m: M.MsgMap) -> int:
        return max(0, self.spare.get(m.entries_va, 0) - (len(m.entries) + 1))

    def mfc_add_entry(self, m: M.MsgMap, msg: int, code: int, cid: int, last: int | None, sig: int, pfn: int) -> None:
        if self.free_slots(m) < 1:
            raise EditError(f"The message map of {m.label} has no free slot. An entry can only be added where "
                            "one was removed before in this session (the table is not moved or enlarged).")
        if pfn not in self.valid_handler_targets():
            raise EditError(f"0x{pfn:X} is not the start of a known function in this program.")
        self.checkpoint()
        vals = self._entry_values(m) + [(msg, code, cid, cid if last is None else last, sig, pfn)]
        self._write_table(m, vals, self.spare[m.entries_va], f"Message map {m.label}: added entry "
                          f"{M.MsgEntry(0, 0, msg, code, cid, cid if last is None else last, sig, pfn).macro()}")
        self.refresh_maps()
        self._changed()

    # ================================================================ save
    def default_save_path(self) -> Path:
        p = self.path or Path("program.exe")
        return p.with_name(f"{p.stem}_edited{p.suffix}")

    def build(self) -> tuple[bytes, list[str]]:
        """The edited file's bytes and notes for the user."""
        notes: list[str] = []
        out = PEImage(bytearray(self.img.data))
        if out.strip_certificate():
            notes.append("The digital signature (Authenticode) was removed: it is no longer valid after an edit.")
        if self.res_dirty:
            self._write_resources(out, notes)
        if self.reloc_add or self.reloc_remove:
            typ = REL_DIR64 if out.is64 else REL_HIGHLOW
            cur = {r: t for r, t in out.relocations()}
            for r in self.reloc_remove:
                cur.pop(r, None)
            for r in self.reloc_add:
                cur[r] = typ
            out.set_relocations(sorted(cur.items()))
            notes.append(f"Relocation table rebuilt ({len(self.reloc_add)} added, {len(self.reloc_remove)} removed).")
        out.update_checksum()
        return bytes(out.data), notes

    def _write_resources(self, out: PEImage, notes: list[str]) -> None:
        rva, _size = out.directory(DIR_RESOURCE)
        sec = out.section_of(rva) if rva else None
        if sec is not None and sec.vaddr == rva:
            blob = R.build_tree(self.resources, sec.vaddr)
            if len(blob) <= out._virtual_room(sec):
                out.set_section_data(sec.index, blob)
                out.set_directory(DIR_RESOURCE, sec.vaddr, len(blob))
                return
        last = max(out.sections, key=lambda s: s.vaddr)
        new_va = align(last.vaddr + max(last.vsize, last.raw_size), out.section_alignment)
        blob = R.build_tree(self.resources, new_va)
        s = out.add_section(".rsrc", blob, len(blob), SCN_CNT_INITIALIZED_DATA | SCN_MEM_READ)
        if s.vaddr != new_va:
            blob = R.build_tree(self.resources, s.vaddr)
            out.set_section_data(s.index, blob)
        out.set_directory(DIR_RESOURCE, s.vaddr, len(blob))
        notes.append("The resources no longer fit in place and were written to a new last section.")

    def save(self, path=None) -> tuple[Path, list[str]]:
        """Write the edited program to *path* (default <name>_edited.exe). The opened original is never
        changed silently: a file that is replaced is copied to <file>.bak first."""
        target = Path(path) if path else self.default_save_path()
        data, notes = self.build()
        PEImage(bytearray(data))                        # sanity: the result parses
        if target.exists():
            bak = target.with_name(target.name + ".bak")
            if not bak.exists() or (self.path is not None and target.resolve() == self.path.resolve()):
                if not bak.exists():
                    shutil.copy2(target, bak)
                    notes.append(f"Backup: {bak.name}")
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(target)
        self.saved_state = self._state()
        self.saved_path = target
        self._changed()
        return target, notes


def t_is64(doc: PeDocument) -> bool:
    return doc.img.is64
