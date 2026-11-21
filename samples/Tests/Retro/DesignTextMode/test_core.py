"""Text-Mode Designer core: model, renderer, ANSI / BIN / TXT round trips, code generation (regions), and the
asm target running in RAD IDE's 8086 emulator compared with the run-time simulator. No Qt, no toolchain.

    python samples/Tests/Retro/DesignTextMode/test_core.py
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from radide.retro.design.textmode import ansi, cp437                          # noqa: E402
from radide.retro.design.textmode.buffer import CellBuffer                    # noqa: E402
from radide.retro.design.textmode.codegen import asm, basic, c, pascal        # noqa: E402
from radide.retro.design.textmode.codegen.common import build_app, read_regions  # noqa: E402
from radide.retro.design.textmode.model import TScreen, hot_split, new_screen  # noqa: E402
from radide.retro.design.textmode.render import render, render_static          # noqa: E402
from radide.retro.design.textmode.sim import Sim, alt, key_bios                # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)


def demo_screen() -> TScreen:
    s = new_screen("Main")
    bar = s.controls[0]
    bar.props["menus"] = [{"text": "&File", "items": [{"text": "&New", "name": "mnuNew", "shortcut": "F2"},
                                                      {"text": "-"}, {"text": "E&xit", "name": "mnuExit"}]},
                          {"text": "&Help", "items": [{"text": "&About...", "name": "mnuAbout"}]}]
    s.add("TextBox", 30, 10, 8, events=["Change"])
    s.add("CheckBox", 30, 11, 16)
    s.add("ListBox", 2, 3, 16, 5, items=["One", "Two", "Three", "Four", "Five", "Six"], events=["Change", "Click"])
    s.add("Option", 30, 12, 14, text="Opt &A", value=True)
    s.add("Option", 30, 13, 14, text="Opt &B")
    s.add("ProgressBar", 2, 12, 20, value=30)
    s.add("Label", 2, 14, 20, text="right", align="right")
    s.add("Button", 2, 16, 10, text="&Go", events=["Click"], enabled=False)
    s.add("Separator", s.controls[2].x, s.controls[2].y + 6, s.controls[2].w)
    return s


def test_model():
    t, m, k = hot_split("&Save && Exit")
    check("hot_split & marks hotkey", (t, m, k) == ("Save & Exit", "10000000000", ord("S")), (t, m, k))
    t, m, _ = hot_split(" ~F1~ Help", "~")
    check("hot_split ~ spans", t == " F1 Help" and m == "01100000", (t, m))
    s = demo_screen()
    check("unique names", len({c.name for c in s.controls}) == len(s.controls))
    check("no problems in the demo", not s.problems(), s.problems())
    s2 = TScreen.from_dict(__import__("json").loads(s.to_json()))
    check("json round trip", s2.to_json() == s.to_json())
    win = s.controls[2]
    inside = s.contained(win)
    check("window contains its label and buttons", {c.type for c in inside} >= {"Label", "Button"}, inside)
    bad = new_screen("Bad", sample=False)
    bad.add("Label", 0, 0, name="my_label")
    bad.add("Label", 0, 1, name="Print")
    check("validation: underscore and reserved words", len(bad.problems()) == 2, bad.problems())
    c1 = bad.add("Button", 75, 24, 20)
    bad.clamp(c1)
    check("clamp keeps controls on the screen", c1.x + c1.w <= 80 and c1.y < 25, c1.rect())


def test_render():
    s = demo_screen()
    b = render_static(s)
    win = s.controls[2]
    check("double border corner", b.get(win.x, win.y)[0] == 0xC9)
    check("title on the border", cp437.encode(" Main ")[1] in b.chars[win.y * 80: win.y * 80 + 80])
    check("shadow attribute 08h", b.get(win.x + win.w, win.y + 1)[1] == 0x08)
    sep = s.controls[-1]
    check("separator joined to the double border", b.get(sep.x, sep.y)[0] == 0xC7 and
          b.get(sep.x + sep.w - 1, sep.y)[0] == 0xB6, (hex(b.get(sep.x, sep.y)[0]),))
    full = render(s)
    ok_btn = next(c for c in s.controls if c.type == "Button")
    check("first control in tab order has the focus colours", full.get(ok_btn.x + 1, ok_btn.y)[1] == 0x2F,
          hex(full.get(ok_btn.x + 1, ok_btn.y)[1]))
    runs = b.rle()
    check("RLE runs never cross a line", all(n <= 80 for n, _c, _a in runs) and sum(n for n, _c, _a in runs) == 2000)


def test_ansi(tmp: Path):
    s = demo_screen()
    b = render(s)
    data = ansi.to_ansi(b)
    back = ansi.parse_ansi(data)
    # characters ANSI cannot carry (ESC, CR, LF ...) become spaces
    want = b.copy()
    for i, ch in enumerate(want.chars):
        if ch in (0x1B, 0x1A, 0x0D, 0x0A, 0x09, 0x00, 0x08):
            want.chars[i] = 0x20
    check("ANSI round trip", back == want, back.diff(want)[:5])
    p = tmp / "art.ans"
    ansi.save_art(b, p, ansi.Sauce(title="Demo", author="RAD", group="IDE"))
    sc = ansi.art_sauce(p)
    check("SAUCE record written and read", sc is not None and (sc.title, sc.author, sc.group, sc.width) ==
          ("Demo", "RAD", "IDE", 80), sc)
    check("ANSI file loads back", ansi.load_art(p) == want)
    pb = tmp / "art.bin"
    ansi.save_art(b, pb)
    check("BIN round trip (lossless)", ansi.load_art(pb) == b)
    raw = tmp / "dump.bin"
    raw.write_bytes(b.to_bin())
    check("raw B800 dump loads", ansi.load_art(raw) == b)
    pt = tmp / "art.txt"
    ansi.save_art(b, pt)
    check("TXT keeps the characters", ansi.load_art(pt).plain_text() == b.plain_text())
    # foreign ANSI: cursor movement, bold, reset, deferred wrap
    foreign = b"\x1b[2J\x1b[1;33;44mHi\x1b[0m\x1b[3;5Hx" + b"A" * 80 + b"\r\nB"
    fb = ansi.parse_ansi(foreign)
    check("ANSI colours and cursor position", fb.get(0, 0) == (ord("H"), 0x1E) and fb.get(4, 2)[0] == ord("x"),
          (fb.get(0, 0), fb.get(4, 2)))
    check("ANSI deferred wrap", fb.get(0, 4)[0] == ord("B"), fb.plain_text()[:300])


def test_regions():
    s = demo_screen()
    for name, mod, kw, marker, code in (
            ("basic", basic, {"dialect": "freebasic"}, "' >>> USER CODE Button3_Click", "  BEEP"),
            ("pascal", pascal, {}, "{ >>> USER CODE Button3_Click", "begin\n  Write(#7);\nend;"),
            ("c", c, {}, "/* >>> USER CODE Button3_Click", "    putchar(7);"),
            ("asm", asm, {}, "; >>> USER CODE Button3_Click", "    mov ah, 2")):
        text, _w = mod.generate([s], **kw)
        lines = text.split("\n")
        i = next(k for k, ln in enumerate(lines) if ln.startswith(marker))
        j = next(k for k in range(i + 1, len(lines)) if "<<< END USER CODE" in lines[k])
        lines[i + 1:j] = code.split("\n")
        edited = "\n".join(lines)
        again, _w = mod.generate([s], edited, **kw)
        check(f"{name}: user code kept when regenerated", read_regions(again).get("Button3_Click") == code,
              read_regions(again).get("Button3_Click"))
        s2 = s.clone()
        s2.find("Button3").props["events"] = []
        orphan, _w = mod.generate([s2], edited, **kw)
        body = read_regions(orphan).get("orphaned", "")
        check(f"{name}: removed handler's code kept commented out", "Button3_Click" in body and
              code.split("\n")[0].strip() in body, body[:200])


def test_emulator():
    from radide.emu8086.assembler import assemble
    from radide.emu8086.machine import Machine
    s = demo_screen()
    src, _w = asm.generate([s])
    prog = assemble(src, "main.asm")
    check("asm target assembles with RAD IDE's 8086 assembler", prog.ok, [str(e) for e in prog.errors[:5]])
    if not prog.ok:
        return
    seqs = {"start": [], "tab": [9], "type": [9, 9] + [ord(ch) for ch in "helloworld"] + [8],
            "check": [9, 9, 9, 32], "list": [9, 9, 9, 9] + [256 + 80] * 6 + [256 + 72],
            "menu": [256 + 68], "menu-move": [256 + 68, 256 + 80, 256 + 77], "alt-f": [alt("f")],
            "alt-b option": [alt("b")], "shift+tab": [256 + 15, 256 + 15], "menu-esc": [256 + 68, 27],
            "esc cancels": [27], "menu-hotkey": [alt("h"), ord("a")]}
    for name, keys in seqs.items():
        m = Machine()
        m.load(prog)
        m.record_history = False
        for k in keys:
            m.push_key(*key_bios(k))
        m.run(6_000_000)
        got = CellBuffer.from_bin(bytes(m.mem[0xB8000:0xB8000 + 4000]), 80)
        sim = Sim([s]).start()
        for k in keys:
            sim.handle_key(k)
        d = sim.buf.diff(got)
        check(f"emulator = simulator after keys: {name}", not d, d[:4])
    check("simulator: initial screen = render()", Sim([s]).start().buf == render(s))


def test_app_tables():
    s = demo_screen()
    app = build_app([s])
    names = [h.key for h in app.handlers]
    check("handlers: controls, menu items", {"Text1_Change", "List1_Change", "List1_Click", "Button3_Click",
                                             "mnuNew_Click", "mnuExit_Click", "mnuAbout_Click"} <= set(names), names)
    check("menus and items", len(app.menus) == 2 and len(app.items) == 4)
    cancel = next(c for c in app.ctls if c.name == "Button2")
    check("Esc = Cancel button", app.screens[0].cancel == cancel.index)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="tui-core-"))
    for fn in (test_model, test_render, lambda: test_ansi(tmp), test_regions, test_app_tables, test_emulator):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            check(f"{getattr(fn, '__name__', 'test')} crashed", False, e)
    ok = sum(1 for _n, c in RESULTS if c)
    print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}", flush=True)
    os._exit(0 if ok == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
