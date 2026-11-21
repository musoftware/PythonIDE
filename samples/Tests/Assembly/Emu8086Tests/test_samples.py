"""Runs every samples/Tests/Assembly/Emu8086* program headless in the 8086 emulator and compares the program
output (DOS / BIOS teletype) and the final 80x25 screen with the expected text. KeyGame is played with
arrow keys until the @ catches the star.

Run:  python samples/Tests/Assembly/Emu8086Tests/test_samples.py      (or with pytest)
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

from radide.emu8086.machine import run_source  # noqa: E402

SAMPLES = HERE.parent

EXPECT = {
    # sample: (keys, expected output, lines expected on the screen)
    "Emu8086Hello": ("", "Hello, 8086 world!\r\n***", ["Hello, 8086 world!", "***"]),
    "Emu8086SumArray": ("", "Total = 2000", ["Total = 2000"]),
    "Emu8086StringReverse": ("RAD IDE\r", "Type a word and press Enter: RAD IDE\r\r\nReversed: EDI DAR",
                             ["Type a word and press Enter: RAD IDE", "Reversed: EDI DAR"]),
    "Emu8086InputNumber": ("1x2a34\r", "Enter a number (0-32767): 1x2a34\r\r\nTwice  = 2468\r\n"
                           "Binary = 0000010011010010\r\n", ["Twice  = 2468", "Binary = 0000010011010010"]),
    "Emu8086Factorial": ("", "7! = 5040", ["7! = 5040"]),
    "Emu8086BubbleSort": ("", "Before: 64 25 12 22 11 90 03 47 \r\nAfter:  03 11 12 22 25 47 64 90 ",
                          ["After:  03 11 12 22 25 47 64 90"]),
}


def _source(name: str) -> str:
    return (SAMPLES / name / "main.asm").read_text(encoding="utf-8")


def test_text_samples():
    for name, (keys, out, screen_lines) in EXPECT.items():
        r = run_source(_source(name), keys=keys)
        assert r["reason"] == "exit", (name, r["reason"], r.get("message"), r["errors"])
        assert r["exit_code"] == 0, (name, r["exit_code"])
        assert r["output"] == out, (name, r["output"])
        screen = r["screen"].splitlines()
        for line in screen_lines:
            assert line in screen, (name, line, screen)


def test_project_files():
    import json
    for d in sorted(SAMPLES.glob("Emu8086*")):
        if d.name == "Emu8086Tests":
            continue
        proj = json.loads((d / "project.radproj").read_text(encoding="utf-8"))
        assert proj["language"] == "emu8086" and proj["modules"] == ["main.asm"], d
        assert (d / "README.md").is_file(), d


def test_colors_screen():
    r = run_source(_source("Emu8086Colors"))
    m = r["machine"]
    assert r["reason"] == "exit"
    assert m.cell(3, 16) == (ord("T"), 0x1E)            # INT 10h 13h title: yellow on blue
    assert m.cell(2, 5)[1] == 0x1F and m.cell(10, 64)[1] == 0x1F     # the window
    assert m.cell(11, 5)[1] == 0x07                      # outside of it
    for k in range(16):                                  # A..P in the 16 foreground colours
        assert m.cell(6, 8 + 2 * k) == (ord("A") + k, 0x10 + k)
    assert m.cursor == [12, 0]
    assert "Text mode colours on the 8086" in r["screen"]


def test_key_game():
    from radide.emu8086.assembler import assemble
    from radide.emu8086.machine import Machine
    prog = assemble(_source("Emu8086KeyGame"), "main.asm")
    assert prog.ok, [str(e) for e in prog.errors]
    m = Machine()
    m.record_history = False
    m.load(prog)
    var = {v.name: v for v in prog.variables}

    def value(name):
        return m.read_var(var[name])[0]
    info = m.run(500_000)
    assert info.reason == "input"
    assert "Score: 0" in m.screen_text()
    for target in range(2):                              # catch two stars
        srow, scol = value("srow"), value("scol")
        assert m.cell(srow, scol) == (ord("*"), 0x0E)
        for _ in range(200):
            prow, pcol = value("prow"), value("pcol")
            if (prow, pcol) == (srow, scol):
                break
            key = "down" if prow < srow else "up" if prow > srow else "right" if pcol < scol else "left"
            m.press(key)
            info = m.run(500_000)
            assert info.reason == "input", info
            assert m.cell(value("prow"), value("pcol")) == (ord("@"), 0x0F)
        assert value("score") == target + 1
        assert f"Score: {target + 1}" in m.screen_text()
    m.press("esc")
    info = m.run(500_000)
    assert info.reason == "exit" and "Game over" in m.screen_text()


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    fails = 0
    for fn in (test_project_files, test_text_samples, test_colors_screen, test_key_game):
        try:
            fn()
            print("PASS", fn.__name__)
        except AssertionError as e:
            fails += 1
            print("FAIL", fn.__name__, repr(e)[:600])
    print(f"failures: {fails}")
    sys.exit(1 if fails else 0)
