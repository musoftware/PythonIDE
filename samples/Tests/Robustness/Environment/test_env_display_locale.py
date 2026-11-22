"""Environment robustness - display scaling, monitors, themes, Arabic / Turkish locales, console code pages.

    .venv\\Scripts\\python samples\\Tests\\Robustness\\Environment\\test_env_display_locale.py

1. High DPI: the designer runs under QT_SCALE_FACTOR 1 / 1.25 / 1.5 / 2 (QT_ENABLE_HIGHDPI_SCALING=1, offscreen):
   a mouse drag, a resize by the bottom-right handle, a snapline and a drag at 150 % zoom give exactly the same
   Left / Top / Width / Height (form units) as at 100 %; the overlay keeps the form's logical size.
2. Monitors: dialogs and the main window whose saved geometry is on a monitor that is gone (right, left/top) or
   larger than the screen come back on the screen (radide/screenfit.py).
3. Themes Light / Blue / Dark / High Contrast: theme colour pairs (text on window, menus, tabs, status, tooltips,
   selection ...) reach WCAG AA 4.5:1; rendered dialog text / buttons and the designer's controls are readable.
4. Locale: numbers typed the Arabic / European way ("0,5", "٠٫٥", "١٢٠") are read by the Properties window
   (components.proptypes.number_text); with Python's locale set to Arabic and Turkish, forms save / load the same
   and generated code has no locale digits; Turkish dotted / dotless i in VB6 identifiers translate and build.
5. Console code pages: output of child processes in cp1252 / cp720 / cp1256 / UTF-8 / invalid bytes never
   crashes build.run, the GUI Bridge build step (radide.runtimes.bridge - it used to raise UnicodeDecodeError) or
   the run session decoder; Arabic text comes out right on an Arabic Windows (code pages simulated).
Exit code = number of failures."""
from __future__ import annotations

import json
import locale
import os  # noqa: F401
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _envlib as E  # noqa: E402
from _envlib import ok  # noqa: E402

ROOT = E.scratch("display_locale")
CHILD = str(HERE / "_display_child.py")


def child(mode: str, **env) -> dict:
    for attempt in (1, 2):              # one retry: an offscreen Qt child can die at start on a loaded machine
        rep, text = E.run_report([E.PY, CHILD, mode], E.child_env(**env), 900)
        if rep:
            return rep
        print(f"(attempt {attempt}: no report)\n" + text[-3000:])
    return rep


# =================================================================== 1. DPI
print("== 1. High DPI", flush=True)
base = None
for f in ("1", "1.25", "1.5", "2"):
    rep = child("dpi", QT_SCALE_FACTOR=f, QT_ENABLE_HIGHDPI_SCALING="1")
    ok(f"scale {f}: designer runs (devicePixelRatio {rep.get('dpr')})", rep.get("dpr") == float(f), rep.get("dpr"))
    if f == "1":
        base = rep
        ok("100 %: drag moves by grid steps", rep.get("drag", [0])[:2] == [56, 40], rep.get("drag"))
        ok("100 %: snapline makes the left edges equal", rep.get("snap_left", [0, 1])[0] == rep.get("snap_left",
                                                                                                    [0, 1])[1])
        continue
    for k in ("drag", "resize", "snap_left", "zoom_drag", "overlay_size", "grab_logical", "form_size", "saved_props"):
        ok(f"scale {f}: {k} identical to 100 % (form units, no off-by-scale)", rep.get(k) == base.get(k),
           f"{rep.get(k)} != {base.get(k)}")

# =================================================================== 2. monitors
print("== 2. Monitors", flush=True)
rep = child("screens")
for label, w in (rep.get("windows") or {}).items():
    ok(f"window restore: {label} -> on the screen", w["visible"], w)
    if label != "main window, monitor gone":
        ok(f"window restore: {label} -> completely inside the available area", w["inside"], (w, rep.get("screen")))
ok("screen restore report complete", len(rep.get("windows") or {}) == 4, rep)

# =================================================================== 3. themes
print("== 3. Themes", flush=True)
rep = child("themes")
for name, t in (rep.get("themes") or {}).items():
    # Blue: "window" is the dark-blue frame (no text on it; its dialogs get a light Window in theme.palette_for)
    low = {k: v for k, v in t["tokens"].items() if v < 4.5 and not (name == "Blue" and k == "window/text")}
    ok(f"theme {name}: every text/background colour pair >= 4.5:1", not low, low)
    for k in ("dialog_label", "dialog_button", "designer_button", "designer_label"):
        ok(f"theme {name}: rendered {k.replace('_', ' ')} readable (contrast {t[k]})", t[k] >= 4.5, t[k])
ok("all four themes rendered", len(rep.get("themes") or {}) == 4, list(rep.get("themes") or {}))

# =================================================================== 4. locale
print("== 4. Locale", flush=True)
from radide.components.proptypes import coerce, number_text  # noqa: E402
for text, want in (("0,5", 0.5), ("٠٫٥", 0.5), ("1.25", 1.25), (" 2,75 ", 2.75), ("−1,5", -1.5)):
    try:
        got = coerce("float", text)
    except ValueError as e:
        got = e
    ok(f"float typed as {text!r} -> {want}", got == want, got)
for text, want in (("١٢٠", 120), ("120 ", 120), ("1٬200", 1200), ("‏٤٥", 45)):
    try:
        got = int(number_text(text))
    except ValueError as e:
        got = e
    ok(f"int typed as {text!r} -> {want}", got == want, got)
try:
    coerce("float", "abc")
    ok("a wrong number gives a ValueError message (not a crash)", False)
except ValueError as e:
    ok("a wrong number gives a ValueError message (not a crash)", "not a number" in str(e))

from radide.languages import get_plugin  # noqa: E402
from radide.model import Form  # noqa: E402
results_by_locale = {}
for loc in ("ar-EG", "tr-TR", "C"):
    try:
        locale.setlocale(locale.LC_ALL, loc)
        active = True
    except locale.Error:
        active = False
    f = Form()
    f.props["Text"] = "نموذج"
    c = f.add("TrackBar", 10, 10)
    c.props["Name"] = "İsimBar"
    c.props["Value"] = 1200
    p = ROOT / f"loc_{loc}.form"
    f.save(p)
    g = Form.load(p)
    code = get_plugin("python-tk").generate_designer(g, "")
    results_by_locale[loc] = (p.read_bytes(), code)
    ok(f"locale {loc}{'' if active else ' (not installed)'}: form round trip and designer code",
       g.find("İsimBar") is not None and "1200" in code and "١" not in code, code[:200])
locale.setlocale(locale.LC_ALL, "C")
ok("Arabic / Turkish / C locale: identical .form bytes and generated code",
   len({v for v in results_by_locale.values()}) == 1)

# Turkish dotted / dotless i in VB6 identifiers -> native exe
tr_dir = ROOT / "TurkishVB"
shutil.copytree(E.REPO / "samples/Tests/Native/VB6/HelloVB", tr_dir)
bas = tr_dir / "Form1.bas"
src = bas.read_text(encoding="utf-8")
src = src.replace("Private mCount As Integer",
                  "Private mCount As Integer\nPrivate Title As String\nPrivate sayı As Integer\nPrivate İl As String")
src = src.replace('    lblResult.Caption = "Type a name and press Greet"',
                  '    TITLE = "İstanbul ılık"\n    SAYI = 3\n    il = "x"\n'
                  '    lblResult.Caption = title & " " & CStr(Sayı) & İL')
bas.write_text(src, encoding="utf-8")
try:
    locale.setlocale(locale.LC_ALL, "tr-TR")
except locale.Error:
    pass
from radide.deploy.native.vb6fb.translate import translate_project  # noqa: E402
try:
    tr = translate_project(tr_dir)
    ok("Turkish locale: VB6 with I/ı/İ identifiers translates", tr.source and not tr.reasons, tr.reasons[:5])
except Exception as e:  # noqa: BLE001
    ok("Turkish locale: VB6 with I/ı/İ identifiers translates", False, repr(e))
from radide.deploy import build  # noqa: E402
from radide.deploy.config import PublishConfig  # noqa: E402
try:
    log: list[str] = []
    res = build.build(tr_dir, PublishConfig(app_name="TurkishVB", version="1.0.0", publisher="t"), log=log.append)
    ok("Turkish locale: VB6 project with I/ı/İ identifiers builds a native exe",
       res.kind == "native" and (Path(res.dist) / res.exe).is_file(), "\n".join(log[-12:]))
except Exception as e:  # noqa: BLE001
    ok("Turkish locale: VB6 project with I/ı/İ identifiers builds a native exe", False, f"{e}\n" + "\n".join(log[-15:]))
locale.setlocale(locale.LC_ALL, "C")

# =================================================================== 5. console code pages
print("== 5. Console code pages", flush=True)
import radide.console_text as CT  # noqa: E402
ar = "خطأ: المتغير غير معرف"
samples = {"utf-8": ar.encode("utf-8"), "cp1256": ar.encode("cp1256"), "cp720": ar.encode("cp720"),
           "cp1252": "Fehler: Größe ungültig".encode("cp1252"), "invalid": b"\x81\x8d\x8f\x90\x9d \xff\xfe"}
orig = (CT._ansi, CT._oem)
CT._ansi, CT._oem = (lambda: "cp1256"), (lambda: "cp720")          # an Arabic Windows
for name, data in samples.items():
    try:
        out = CT.decode(data)
        err = None
    except Exception as e:  # noqa: BLE001
        out, err = "", e
    ok(f"Arabic Windows: decode {name} output without an error", err is None, repr(err))
    if name in ("utf-8", "cp1256", "cp720"):
        ok(f"Arabic Windows: {name} Arabic compiler message reads correctly", out == ar, out)
CT._ansi, CT._oem = orig
sd = CT.StreamDecoder()
b = "سطر عربي\n".encode("utf-8")
ok("run output split inside a UTF-8 character is joined", sd.feed(b[:3]) + sd.feed(b[3:]) == "سطر عربي\n")

emit = ("import sys; sys.stdout.buffer.write(bytes.fromhex(sys.argv[1])); sys.stdout.flush(); "
        "sys.exit(int(sys.argv[2]))")
from radide.deploy.build import run as build_run  # noqa: E402
for name, data in samples.items():
    lines: list[str] = []
    try:
        code = build_run([E.PY, "-c", emit, (data + b"\n").hex(), "0"], ROOT, lines.append)
        err = None
    except Exception as e:  # noqa: BLE001
        code, err = -1, e
    ok(f"build.run: tool output in {name} does not crash the build log", err is None and code == 0, repr(err))
cproj = ROOT / "ConsoleBridge"
cproj.mkdir(exist_ok=True)
(cproj / "project.radproj").write_text(json.dumps({"name": "ConsoleBridge", "language": "c-bridge", "forms": [],
                                                   "startup": "", "modules": []}), encoding="utf-8")
for name, data in samples.items():
    build_cmd = f'"{E.PY}" -c "{emit}" {(data + b"\n").hex()} 1'
    r = subprocess.run([E.PY, "-m", "radide.runtimes.bridge", str(cproj), "--build", build_cmd, "--", "cmd", "/c",
                        "echo", "never"], capture_output=True, env=E.child_env(PYTHONIOENCODING="utf-8"), timeout=120)
    err = r.stderr.decode("utf-8", "replace")
    ok(f"GUI Bridge build step: compiler output in {name} -> 'Build failed', no UnicodeDecodeError",
       r.returncode == 1 and "UnicodeDecodeError" not in err and "Traceback" not in err and "Build failed" in err,
       f"rc={r.returncode} {err[-500:]}")

sys.exit(E.summary("Environment: display / locale"))
