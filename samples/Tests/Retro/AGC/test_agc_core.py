"""Apollo AGC support - headless checks (no IDE window).

    python samples/Tests/Retro/AGC/test_agc_core.py [--apollo DIR] [--download]

1. built-in assembler + emulator: HelloDSKY shows V16 N36 and counts seconds, V35E lamp test, V21E -> OPR ERR,
   RSET clears it, V16N36E back to the clock; no hardware alarm restarts; the empty template too
2. DSKY relay-word decoding, the yaAGC socket packets, yaYUL error parsing
3. editor support: F12 across files, hover, outline, references
4. Virtual AGC (skipped when not installed): yaYUL assembles HelloDSKY with 0 errors and its rope is
   word-for-word the built-in assembler's; the built-in emulator runs the yaYUL rope; yaAGC runs it and the
   DSKY (socket protocol) shows V16 N36, the lamp test and the clock
5. Comanche055 (only with --apollo DIR holding a downloaded Comanche055 folder, or --download): yaYUL 0 errors,
   yaAGC + DSKY lamp test
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from radide.agc import assembler, intel, toolchain  # noqa: E402
from radide.agc.dsky_model import DskyModel, relay_word  # noqa: E402
from radide.agc.machine import AgcMachine  # noqa: E402
from radide.agc.yaagc import form_packet, key_packets, parse_packets, parse_registers, parse_stop  # noqa: E402

HERE = Path(__file__).resolve().parent
SAMPLE = HERE / "HelloDSKY"
RESULTS: list[tuple[str, bool]] = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)


def skip(name, why):
    print(f"SKIP {name} ({why})", flush=True)


# ------------------------------------------------------------------ 1. built-in toolchain
prog = assembler.assemble_file(SAMPLE / "MAIN.agc")
check("HelloDSKY assembles with the built-in assembler", prog.ok and prog.words() > 400,
      [d.text() for d in prog.errors[:5]])
m = AgcMachine(prog)
m.run_seconds(2.3)
check("starts with VERB 16 NOUN 36", m.dsky.verb == "16" and m.dsky.noun == "36", m.dsky.summary())
check("R3 counts seconds (N36: seconds x 100)", m.dsky.r3 == "+00200", m.dsky.summary())
m.keys("V35E")
check("V35E lamp test: 88 everywhere", m.dsky.verb == "88" and m.dsky.r1 == "+88888" and
      m.dsky.lamps["OPR ERR"] and m.dsky.lamps["PROG"], m.dsky.summary())
m.keys("V16N36E")
m.run_seconds(61)
check("V16N36E: back to the clock, one minute later R2 = +00001", m.dsky.verb == "16" and m.dsky.r2 == "+00001"
      and m.dsky.prog == "  " and not m.dsky.lamps["OPR ERR"], m.dsky.summary())
m.keys("V21E")
check("V21E -> OPR ERR", m.dsky.lamps["OPR ERR"], m.dsky.summary())
m.keys("R")
check("RSET clears OPR ERR", not m.dsky.lamps["OPR ERR"], m.dsky.summary())
check("no hardware-alarm restarts", m.cpu.restarts == 0, m.cpu.alarm_log[:3])
secs = m.symbol_value("SECS")
check("erasable variable SECS readable", secs is not None and secs[0].kind == "E", secs)
lt = m.program.addr_of_line.get(("main.agc", next(i for i, l in enumerate(
    (SAMPLE / "MAIN.agc").read_text().splitlines(), 1) if l.startswith("TICK "))))
check("source line -> address map (TICK)", lt is not None and lt.kind == "F", lt)

# breakpoint on TICK: stops within ~1 s
m2 = AgcMachine(prog)
tick_line = next(i for i, l in enumerate((SAMPLE / "MAIN.agc").read_text().splitlines(), 1) if l.startswith("TICK "))
m2.set_breakpoint_lines([("MAIN.agc", tick_line)])
r = m2.run_seconds(1.5, stop=m2.at_breakpoint)
check("breakpoint on TICK hit", r == "stop" and m2.current_line()[1] == tick_line, (r, m2.current_line()))

# alarms: a program that never touches NEWJOB / has no interrupts restarts
bad = assembler.assemble_text("""A EQUALS 0
                SETLOC  4000
                INHINT
                TCF     LOOP
LOOP            CA      A
                TCF     LOOP
""")
mb = AgcMachine(bad)
mb.run_seconds(1.0)
check("missing interrupts -> NO RUPT alarm restart (like real hardware)", mb.cpu.restarts > 0 and
      "RUPT" in " ".join(mb.cpu.alarm_log), mb.cpu.alarm_log[:2])
mb.cpu.alarms = False
mb.cpu.restarts = 0
mb.run_seconds(1.0)
check("alarms can be switched off", mb.cpu.restarts == 0)

with tempfile.TemporaryDirectory() as tmp:
    from radide.languages import get_plugin
    plug = get_plugin("agc-yul")
    pe = plug.create_new_project(Path(tmp) / "Empty", "Empty", "agc_empty")
    me = AgcMachine.from_file(Path(pe.folder) / "MAIN.agc")
    me.run_seconds(2.0)
    check("empty template assembles and runs without alarms", me.program.ok and me.cpu.restarts == 0 and
          me.symbol_value("TICKS")[1] >= 190, (me.cpu.alarm_log[:2], me.symbol_value("TICKS")))
    ph = plug.create_new_project(Path(tmp) / "Hello", "Hello", "agc_hello")
    check("Hello DSKY template = the sample", (Path(ph.folder) / "KEYBOARD.agc").read_text() ==
          (SAMPLE / "KEYBOARD.agc").read_text() and ph.startup == "MAIN")

errs = assembler.assemble_text("        SETLOC 4000\nX       FOO     1\n        TC      NOWHERE\n        VLOAD   X\n")
codes = {d.code for d in errs.errors}
check("errors: unknown operator, undefined symbol, interpretive", {"unknown_op", "undefined", "interp"} <= codes,
      codes)
check("error text in Arabic", "غير" in errs.errors[0].text("ar"))

# ------------------------------------------------------------------ 2. DSKY / protocol / parsers
d = DskyModel()
d.channel(0o10, relay_word(10, "3", "5"))
d.channel(0o10, relay_word(7, "1", "2", sign=True))
d.channel(0o11, 0o100)
check("relay words decode", d.verb == "35" and d.r1.startswith("+") and d.lamps["OPR ERR"], d.summary())
pk = form_packet(0o10, 0o54321) + form_packet(0o32, 0o20000, mask=True)
got, rest = parse_packets(b"\x99" + pk + b"\x01")
check("socket packets round-trip (+ resync)", got == [(0o10, 0o54321, False), (0o32, 0o20000, True)] and
      rest == b"\x01", (got, rest))
check("key packet = channel 15 code", parse_packets(key_packets("ENTR"))[0] == [(0o15, 0o34, False)])
check("yaYUL error parsing", toolchain.parse_yayul_output("MAIN.agc:12: Fatal Error: Bad thing\nX.agc:3: Warning: hm\n")
      == [("Error", "MAIN.agc", 12, "Bad thing"), ("Warning", "X.agc", 3, "hm")])
check("yaAGC stop annotation with a Windows path", parse_stop("\x1a\x1aC:\\x\\MAIN.agc:135:135:beg:0x097d\n") ==
      ("C:\\x\\MAIN.agc", 135, 0x97D))
check("yaAGC debugger parsing", parse_stop("\x1a\x1aMAIN.agc:42:1:beg:0x0800\n") == ("MAIN.agc", 42, 0x800) and
      parse_registers("A\t\t0x0005\t5\nQ\t\t0x0800\t2048\n") == {"A": 5, "Q": 0x800})

# ------------------------------------------------------------------ 3. editor support
disp = SAMPLE / "DISPLAY.agc"
code = disp.read_text()
lines = code.splitlines()
i = next(k for k, l in enumerate(lines) if "CA      HOURS" in l)
dfn = intel.definition(code, i, lines[i].index("HOURS") + 1, disp)
check("F12 across files (HOURS -> ERASABLE.agc)", dfn and Path(dfn[0]).name == "ERASABLE.agc", dfn)
check("hover on an instruction", "Count, Compare" in intel.hover("                CCS     TMP", 0, 17, disp))
check("hover on V/N in a comment", "Verb 16" in intel.hover("    CA X     # shows V16N36 here", 0, 22, disp))
check("outline by log section", [s["name"] for s in intel.document_symbols((SAMPLE / "MAIN.agc").read_text())][:2]
      == ["ERASABLE", "INTERRUPTS"])
refs = intel.references(code, i, lines[i].index("HOURS") + 1, disp)
check("references in 3 files", len({Path(r[0]).name for r in refs}) == 3, refs)
spec = intel.monaco_language()
check("Monarch grammar", spec["id"] == "rad-agc" and "TC" in spec["monarch"]["opcodes"])

# ------------------------------------------------------------------ 4. Virtual AGC
yayul, yaagc = toolchain.find("yayul"), toolchain.find("yaagc")


def run_yayul(folder: Path):
    r = subprocess.run([yayul, "MAIN.agc"], cwd=folder, capture_output=True, text=True, errors="replace")
    return r, toolchain.parse_yayul_output(r.stderr)


def dsky_session(folder: Path, port: int, keys_list):
    p = subprocess.Popen(toolchain.yaagc_command("MAIN.agc.bin", port, False), cwd=folder,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.PIPE)
    model, s, out = DskyModel(), None, []
    try:
        for _ in range(60):
            try:
                s = socket.create_connection(("127.0.0.1", port), timeout=1)
                break
            except OSError:
                time.sleep(0.2)
        s.settimeout(0.2)
        buf = b""

        def pump(sec):
            nonlocal buf
            end = time.time() + sec
            while time.time() < end:
                try:
                    data = s.recv(4096)
                except socket.timeout:
                    continue
                if not data:
                    break
                buf += data
                pk2, buf = parse_packets(buf)
                for ch, v, u in pk2:
                    if not u:
                        model.channel(ch, v)
        pump(2.5)
        out.append(model.as_dict())
        for seq in keys_list:
            for k in seq:
                s.sendall(key_packets(k))
                pump(0.3)
            pump(1.0)
            out.append(model.as_dict())
    finally:
        if s:
            s.close()
        p.kill()
    return out


if yayul and yaagc:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "HelloDSKY"
        shutil.copytree(SAMPLE, work)
        r, diags = run_yayul(work)
        check("yaYUL assembles HelloDSKY with 0 errors", r.returncode == 0 and not diags and
              "Fatal errors:  0" in r.stdout, (r.returncode, diags))
        ya = assembler.load_bin((work / "MAIN.agc.bin").read_bytes())
        diffs = [(b, o) for (b, o) in prog.used if prog.rope[b][o] != ya[b][o]]
        check("built-in assembler = yaYUL, word for word", not diffs, diffs[:5])
        my = AgcMachine.from_bin((work / "MAIN.agc.bin").read_bytes())
        my.run_seconds(2.3)
        check("built-in emulator runs the yaYUL rope", my.dsky.verb == "16" and my.dsky.r3 == "+00200",
              my.dsky.summary())
        states = dsky_session(work, 19851, [["VERB", "3", "5", "ENTR"], ["VERB", "1", "6", "NOUN", "3", "6",
                                                                          "ENTR"]])
        check("yaAGC + DSKY socket: V16 N36 at start", states[0]["verb"] == "16" and states[0]["noun"] == "36",
              states[0])
        def secs(st):
            try:
                return int(st["r2"]) * 6000 + int(st["r3"])
            except ValueError:
                return -1
        check("yaAGC: the clock runs (no restarts)", secs(states[2]) > secs(states[0]) >= 0 and
              secs(states[2]) >= 300, (states[0], states[2]))
        check("yaAGC: V35E lamp test", states[1]["r1"] == "+88888", states[1])
        check("yaAGC: V16N36E clock back", states[2]["verb"] == "16" and states[2]["r1"] == "+00000", states[2])
else:
    skip("Virtual AGC checks", "yaYUL / yaAGC not installed: python -m radide.agc.toolchain install")

# ------------------------------------------------------------------ 5. Comanche055
apollo = None
if "--apollo" in sys.argv:
    apollo = Path(sys.argv[sys.argv.index("--apollo") + 1]) / "Comanche055"
elif "--download" in sys.argv and not os.environ.get("RADIDE_OFFLINE"):
    from radide.agc.apollo_source import download
    apollo = download("Comanche055", Path(tempfile.mkdtemp()), log=lambda s: None)
if apollo is not None and (apollo / "MAIN.agc").exists() and yayul and yaagc:
    r, diags = run_yayul(apollo)
    check("yaYUL assembles Comanche055 with 0 errors", r.returncode == 0 and
          not [d for d in diags if d[0] == "Error"] and "Fatal errors:  0" in r.stdout, diags[:5])
    states = dsky_session(apollo, 19852, [["VERB", "3", "5", "ENTR"]])
    check("Comanche055 in yaAGC: V35E lamp test on RAD IDE's DSKY protocol", states[1]["verb"] == "88" and
          states[1]["r1"] == "+88888", states[1])
    check("licence note written", (apollo / "README_RADIDE.txt").exists())
else:
    skip("Comanche055", "pass --apollo DIR (with Comanche055/) or --download")

ok = sum(c for _n, c in RESULTS)
print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
sys.exit(0 if ok == len(RESULTS) else 1)
