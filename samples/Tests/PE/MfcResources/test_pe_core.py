"""PE / MFC workbench library tests (radide/pe): parse, edit, save, re-parse, run the edited program.

    .venv\\Scripts\\python samples\\Tests\\PE\\MfcResources\\test_pe_core.py

Uses prebuilt/MiniMfc32.pe and MiniMfc64.pe (rebuild with build.py when MSVC is installed). The edited
programs are started for a moment through winrun.py (only processes started here are closed).
Prints PASS/FAIL per check and a total.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from radide.pe import mfc as M  # noqa: E402
from radide.pe import rc  # noqa: E402
from radide.pe import resources as R  # noqa: E402
from radide.pe.document import EditError, PeDocument  # noqa: E402
from radide.pe.image import PEImage  # noqa: E402

RESULTS: list[tuple[bool, str]] = []
IDC_BUTTON1, IDC_BUTTON2, IDC_STATUS, IDC_EDIT1 = 1001, 1002, 1004, 1003
ID_FILE_HELLO, IDS_HELLO, IDS_BYE = 40001, 2001, 2002
RUN = sys.platform == "win32"


def check(ok, name: str, detail: str = "") -> None:
    RESULTS.append((bool(ok), name))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail and not ok else ""))


def handler_of(doc: PeDocument, cls: str, ctrl_id: int):
    m = next(m for m in doc.message_maps() if m.class_name == cls)
    return m, next(e for e in m.entries if e.msg == M.WM_COMMAND and e.id == ctrl_id and e.code == 0)


def suite(bits: str, work: Path) -> None:
    src = HERE / "prebuilt" / f"MiniMfc{bits}.pe"
    exe = work / f"MiniMfc{bits}.exe"
    shutil.copy2(src, exe)
    original = exe.read_bytes()
    doc = PeDocument.open(exe)
    tag = f"[{bits}] "
    check(doc.img.is64 == (bits == "64"), tag + "PE header: machine / PE32+")
    # ---------- resources: parse
    types = {e.type for e in doc.resources}
    check({R.RT_DIALOG, R.RT_MENU, R.RT_STRING, R.RT_ACCELERATOR, R.RT_VERSION, R.RT_GROUP_ICON, R.RT_BITMAP,
           R.RT_MANIFEST, R.RT_TOOLBAR, R.RT_DLGINIT, R.RT_RCDATA} <= types, tag + "all resource types listed")
    exact = all(R.build_dialog(R.parse_dialog(e.data)) == e.data for e in doc.find(R.RT_DIALOG)) and \
        all(R.build_menu(R.parse_menu(e.data)) == e.data for e in doc.find(R.RT_MENU)) and \
        all(R.build_version(R.parse_version(e.data)) == e.data for e in doc.find(R.RT_VERSION))
    check(exact, tag + "dialog / menu / version codecs are byte-exact")
    d = doc.dialog(101, 0x409)
    check(d.title == "MiniMfc Test Dialog" and len(d.controls) == 15, tag + "main dialog parsed")
    tb = R.parse_toolbar(doc.get(R.RT_TOOLBAR, 128).data)
    check(tb.ids == [40001, 0, 40004, 40003] and (tb.width, tb.height) == (16, 15), tag + "MFC toolbar parsed")
    check([i.text for i in R.parse_dlginit(doc.get(R.RT_DLGINIT, 101).data)] == ["Red", "Green", "Blue"],
          tag + "MFC DLGINIT parsed")
    # ---------- MFC message maps
    maps = doc.message_maps()
    names = {m.class_name for m in maps}
    check({"CMainDlg", "CAboutDlg", "CDialog"} <= names, tag + "message maps + RTTI class names", str(names))
    main = next(m for m in maps if m.class_name == "CMainDlg")
    check(len(main.entries) == 12, tag + "CMainDlg has 12 entries", str(len(main.entries)))
    owner = M.guess_dialog_owner(maps, {c.id for c in d.controls})
    check(owner is not None and owner.class_name == "CMainDlg", tag + "dialog 101 linked to CMainDlg")
    hs = M.handlers_for_control(maps, IDC_BUTTON1, owner)
    check(len(hs) == 1 and hs[0][1].code == 0, tag + "IDC_BUTTON1 -> one BN_CLICKED handler")
    check(any(e.matches_control(1011) and e.id != e.last_id for e in main.entries), tag + "ON_CONTROL_RANGE found")
    an = doc.analysis()
    _m, e1 = handler_of(doc, "CMainDlg", IDC_BUTTON1)
    lst = an.listing_text(e1.pfn)
    callees = [ln.target for ln in an.listing(e1.pfn) if ln.mnemonic in ("call", "jmp") and ln.target]
    text = lst + "".join(an.listing_text(t) for t in callees[:3])
    check("CMainDlg::" in an.name_of(e1.pfn) and "LoadStringW" in text, tag + "handler disassembly named and readable",
          an.name_of(e1.pfn))
    # ---------- edits
    d.title = "Edited by RAD IDE"
    b1 = next(c for c in d.controls if c.id == IDC_BUTTON1)
    b1.text = "Hello &World"
    b1.x += 3
    d.controls.append(R.DlgControl(0x82, "Added label", 1500, 0x50020000, 0, 10, 160, 80, 8))
    d.cy += 10
    doc.set_dialog(101, 0x409, d)
    doc.set_string(IDS_BYE, "Changed string from RAD IDE", 0x409)
    menu = doc.menu(102, 0x409)
    menu.items[0].children[0].text = "&Hi there\tCtrl+H"
    menu.items[0].children.insert(1, R.MenuItem("&New item", 40010))
    doc.set_menu(102, 0x409, menu)
    ver_e, ver = doc.version()
    ver.strings["040904b0"]["CompanyName"] = "Edited Company"
    ver.file_version = (2, 0, 0, 7)
    doc.set_resource(R.RT_VERSION, ver_e.name, ver_e.lang, R.build_version(ver))
    acc = R.parse_accel(doc.get(R.RT_ACCELERATOR, 103).data)
    acc.append(R.Accel(R.FVIRTKEY | R.FCONTROL, ord("N"), 40010))
    doc.set_resource(R.RT_ACCELERATOR, 103, 0x409, R.build_accel(acc))
    # big resource: forces .rsrc to grow past its section
    doc.set_resource(R.RT_RCDATA, "BIGDATA", 0x409, bytes(range(256)) * 400)
    # MFC: Button1 -> Button2's handler
    _m, e2 = handler_of(doc, "CMainDlg", IDC_BUTTON2)
    doc.mfc_retarget(e1, e2.pfn)
    _m, e1b = handler_of(doc, "CMainDlg", IDC_BUTTON1)
    check(e1b.pfn == e2.pfn, tag + "retarget written")
    try:
        doc.mfc_retarget(e1b, e2.pfn + 1)
        check(False, tag + "retarget to a non-function refused")
    except EditError:
        check(True, tag + "retarget to a non-function refused")
    # remove ON_UPDATE_COMMAND_UI, then an add fits in the freed slot
    main = next(m for m in doc.message_maps() if m.class_name == "CMainDlg")
    try:
        doc.mfc_add_entry(main, M.WM_COMMAND, 0, 1500, None, M.command_signature(doc.message_maps()), e2.pfn)
        check(False, tag + "add without free slot refused")
    except EditError:
        check(True, tag + "add without free slot refused")
    idx = next(e.index for e in main.entries if e.code == M.CN_UPDATE_COMMAND_UI)
    doc.mfc_remove_entry(main, idx)
    main = next(m for m in doc.message_maps() if m.class_name == "CMainDlg")
    check(len(main.entries) == 11 and doc.free_slots(main) == 1, tag + "entry removed, one slot free")
    # menu item 40010 -> the "Menu Hello" handler (handled through the freed slot)
    _m, hello = handler_of(doc, "CMainDlg", ID_FILE_HELLO)
    doc.mfc_add_entry(main, M.WM_COMMAND, 0, 40010, None, M.command_signature(doc.message_maps()), hello.pfn)
    main = next(m for m in doc.message_maps() if m.class_name == "CMainDlg")
    check(len(main.entries) == 12 and any(e.id == 40010 for e in main.entries), tag + "entry added in freed slot")
    # instruction patch: same size OK, bigger refused
    an = doc.analysis()
    lines = an.listing(e2.pfn)
    try:
        doc.plan_instruction_patch(lines[0].va, "\n".join(["nop"] * (lines[0].size + 1)), 1)
        check(False, tag + "larger instruction patch refused")
    except EditError:
        check(True, tag + "larger instruction patch refused")
    cur = lines[0].mnemonic + " " + lines[0].op_str
    rec = doc.patch_instructions(lines[0].va, cur, 1)
    check(rec.new == rec.old, tag + "same instruction re-assembled to the same bytes", f"{rec.old.hex()} {rec.new.hex()}")
    # undo / redo
    before = doc.dialog(101, 0x409).title
    doc.set_string(IDS_HELLO, "temporary", 0x409)
    doc.undo()
    check(doc.string(IDS_HELLO, 0x409) == "Hello from button 1" and before == "Edited by RAD IDE", tag + "undo")
    doc.redo()
    check(doc.string(IDS_HELLO, 0x409) == "temporary", tag + "redo")
    doc.undo()
    # ---------- save + re-parse
    out_path, notes = doc.save()
    check(out_path.name == f"MiniMfc{bits}_edited.exe" and exe.read_bytes() == original,
          tag + "saved as new file, original untouched")
    doc.save(out_path)
    check(out_path.with_name(out_path.name + ".bak").is_file(), tag + "overwriting makes a .bak")
    img = PEImage(out_path.read_bytes())
    check(img.compute_checksum() == img.checksum, tag + "PE checksum updated")
    doc2 = PeDocument.open(out_path)
    d2 = doc2.dialog(101, 0x409)
    check(d2.title == "Edited by RAD IDE" and any(c.text == "Hello &World" for c in d2.controls) and
          any(c.id == 1500 for c in d2.controls), tag + "re-parsed dialog edits")
    check(doc2.string(IDS_BYE, 0x409) == "Changed string from RAD IDE", tag + "re-parsed string")
    m2 = doc2.menu(102, 0x409)
    check(m2.items[0].children[0].text.startswith("&Hi there") and m2.items[0].children[1].id == 40010,
          tag + "re-parsed menu")
    check(doc2.version()[1].strings["040904b0"]["CompanyName"] == "Edited Company" and
          doc2.version()[1].file_version == (2, 0, 0, 7), tag + "re-parsed version info")
    check(len(doc2.get(R.RT_RCDATA, "BIGDATA").data) == 102400, tag + "big resource (new .rsrc section)")
    mm = next(m for m in doc2.message_maps() if m.class_name == "CMainDlg")
    check(next(e for e in mm.entries if e.id == IDC_BUTTON1).pfn == e2.pfn, tag + "re-parsed retarget")
    relocs = img.reloc_set()
    ent = next(e for e in mm.entries if e.id == 40010)
    check((ent.va + 16 + img.ptr_size - img.image_base) in relocs, tag + "relocation for added entry")
    # ---------- .rc export / import
    rcp = rc.export_rc(doc2.resources, work / f"rc{bits}", "mini")
    back = {e.key: e.data for e in rc.import_rc(rcp)}
    cur = {e.key: e.data for e in doc2.resources}
    check(back == cur, tag + ".rc export -> import gives the same resources")
    # ---------- run the edited program
    if RUN:
        from winrun import App
        app = App(out_path)
        try:
            check(app.ok and app.title() == "Edited by RAD IDE", tag + "edited exe starts, new caption",
                  app.title() if app.ok else "no window")
            if app.ok:
                check(app.item_text(IDC_BUTTON1) == "Hello &World".replace("&", "") or
                      app.item_text(IDC_BUTTON1) == "Hello &World", tag + "new button caption")
                app.click(IDC_BUTTON1)
                check(app.item_text(IDC_STATUS) == "Changed string from RAD IDE",
                      tag + "Button1 now runs Button2's handler (+ edited string)", app.item_text(IDC_STATUS))
                app.command(40010)
                check(app.item_text(IDC_STATUS) == "Menu Hello", tag + "added entry handles the new menu id",
                      app.item_text(IDC_STATUS))
                app.click(IDC_BUTTON2)
                check(app.item_text(IDC_STATUS) == "Changed string from RAD IDE", tag + "Button2 unchanged")
        finally:
            app.close()
        app = App(exe)
        try:
            app.click(IDC_BUTTON1)
            check(app.ok and app.item_text(IDC_STATUS) == "Hello from button 1", tag + "original exe unchanged")
        finally:
            app.close()


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="pe_mfc_test_"))
    try:
        for bits in ("32", "64"):
            suite(bits, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    ok = sum(1 for r in RESULTS if r[0])
    print(f"\n{ok}/{len(RESULTS)} passed")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
