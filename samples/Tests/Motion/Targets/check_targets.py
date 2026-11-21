"""Animation presets on the non-Python targets (plan MOTION_VARIANTS_FOLDABLES slice D).

    python samples/Tests/Motion/Targets/check_targets.py

1. Pure: expand() of all 15 presets for ring / dart / kivy / rn / winforms / css, the fallbacks each target
   reports (no transforms on Ring / WinForms; no child transparency on WinForms), fxtargets.channels(),
   Error List lines, forms without animations generate no runtime code.
2. make_targets.py rebuilds Motion_Ring / Motion_Flutter / Motion_Kivy / Motion_Expo.
3. Ring (ring.exe, RingQt offscreen): load animations, click-type triggers, chains, On hide, timer colour,
   reduced motion.                                                       SKIP without Ring
4. Flutter: flutter analyze + flutter test (test/motion_test.dart).       SKIP without Flutter
5. Kivy: the app runs; slide / typewriter / shake / On hide.             SKIP without Kivy
6. React Native: the generated screen + radfx.js run in Node (esbuild bundle with stubs).  SKIP without node
7. WinForms C# and VB.NET: temp copies of samples/Tests/ForeignProjects/WinFormsCS|VB get controls +
   animations, Save writes Form1.radide.json + Form1.RadFx.cs|vb (Designer untouched for them), dotnet build,
   the program runs with RADIDE_FX_SELFTEST.                              SKIP without dotnet
8. Web page: radfx.css / radfx.js in QtWebEngine (offscreen): computed animation names per trigger;
   design.add_radfx() links them; the GrapesJS Design View has the foldable devices, radSizeFrame and the
   Animate trait type.                                                    SKIP without QtWebEngine
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from target_tools import (ROOT, check, flutter_check, kivy_run, ring_run, rn_run, skip, summary,  # noqa: E402
                          winforms_case)

sys.path.insert(0, str(ROOT))
from radide import fxtargets as FX  # noqa: E402
from radide import motion  # noqa: E402
from radide.languages import get_plugin  # noqa: E402
from radide.model import Form  # noqa: E402
from radide.motion import presets as P  # noqa: E402


# =============================================================================== 1. pure
def pure():
    f = Form()
    b = f.add("Button", 10, 10)
    f.add("Label", 10, 60)
    for pid in P.CATALOG:
        motion.add(f, b.name, pid)
    expect_fb = {"ring": {"rotate", "flip", "pulse", "scaleIn", "scaleOut", "zoom"},
                 "winforms": {"rotate", "flip", "pulse", "scaleIn", "scaleOut", "zoom", "fadeIn", "fadeOut"},
                 "dart": set(), "kivy": set(), "rn": set(), "css": set()}
    by_fx = {a["id"]: a["preset"] for a in f.extra["animations"]}
    for target, want in expect_fb.items():
        plan = FX.fx_plan(f, target)
        got = {by_fx[fx] for fx, _c, _m in plan["fallbacks"]}
        check(f"{target}: 15 presets expanded", len(plan["storyboards"]) == 15, len(plan["storyboards"]))
        check(f"{target}: fallbacks reported = {sorted(want)}", got == want, sorted(got))
    plan = FX.fx_plan(f, "dart")
    ch = {sb["preset"]: FX.channels(sb, b.props) for sb in plan["storyboards"]}
    check("channels: slideIn = tx -80 -> 0 + opacity", ch["slideIn"]["tx"][0][1] == -80 and "opacity" in ch["slideIn"])
    check("channels: rotate = 360 degrees", ch["rotate"]["rot"][-1][1] == 360)
    check("channels: flip = scaleX -1 -> 1", ch["flip"]["sx"][0][1] == -1 and ch["flip"]["sx"][-1][1] == 1)
    check("channels: colorTo keeps the start colour", ch["colorTo"]["bg"][0][1] == "start")
    check("channels: typewriter reveal 0 -> 1", ch["typewriter"]["reveal"][0][1] == 0)
    check("channels: fadeOut hides at the end", ch["fadeOut"]["visible"][-1][1] is False)
    issues = FX.issues(f, "ring")
    check("Error List: Ring fallbacks + fade note", any("wobble" in m for _s, m in issues)
          and any("opacity effect" in m for _s, m in issues), issues[:3])
    check("Error List: Flutter has no fallback lines", not [m for s, m in FX.issues(f, "dart") if s == "Warning"])
    # chain bookkeeping
    g = Form()
    c = g.add("Button", 0, 0)
    motion.add(g, c.name, "move", id="fx1", trigger={"on": "click"})
    motion.add(g, c.name, "bounce", id="fx2", trigger={"on": "after", "after": "fx1"})
    gp = FX.fx_plan(g, "kivy")
    check("after-chains: fx1 starts fx2", gp["storyboards"][0]["chain"] == ["fx2"])
    # forms without animations: nothing new in the generated code
    plain = Form()
    plain.add("Button", 10, 10)
    for pid, marks in (("ring-qt", ("radfx", "RadFx")), ):
        txt = get_plugin(pid).generate_designer(plain, "")
        check(f"{pid}: no runtime for a form without animations", not any(m in txt for m in marks))
    from radide.mobile.codegen_common import ensure_types
    ensure_types()
    sys.path.insert(0, str(HERE))
    from proj import mobile_form
    mf = mobile_form("Plain")
    mf.add("Button", 10, 10)
    for pid, marks in (("flutter", ("radMotion", "RadVariant")), ("kivy", ("radkivyfx", "RadFx")),
                       ("expo", ("./radfx", "FxBox"))):
        txt = get_plugin(pid).generate_designer(mf, "")
        check(f"{pid}: no runtime for a form without animations", not any(m in txt for m in marks))


# =============================================================================== 3. Ring
RING_TEST = r'''load "Form1.ring"
oApp = NULL
nStep = 0
func main
    oApp = new qApp
    Form1_Show()
    see "R t0 titlex " + QWidget_x(lblTitle.pObject) + nl
    oT = new qTimer(Form1)
    oT.setInterval(1500)
    oT.setTimeoutEvent("Check()")
    oT.start()
    oApp.exec()

func Check
    nStep += 1
    if nStep = 1
        see "R t1 titlex " + QWidget_x(lblTitle.pObject) + nl
        see "R t1 titletext " + substr(lblTitle.text(), " ", "_") + nl
        Form1_BeginAnimation("fx3")
        Form1_BeginAnimation("fx5")
        Form1_BeginAnimation("fx11")
        btnHide_Click()
        return
    ok
    see "R t2 shakex " + QWidget_x(btnShake.pObject) + nl
    see "R t2 movex " + QWidget_x(btnMove.pObject) + nl
    see "R t2 movey " + QWidget_y(btnMove.pObject) + nl
    see "R t2 flipw " + QWidget_width(btnFlip.pObject) + nl
    see "R t2 infovisible " + lblInfo.isVisible() + nl
    see "R t2 boxstyle " + substr(pnlBox.styleSheet(), " ", "_") + nl
    oApp.quit()
'''


def ring_results(text: str) -> dict:
    out = {}
    for line in (text or "").splitlines():
        p = line.split(" ")
        if len(p) >= 4 and p[0] == "R":
            out[f"{p[1]}.{p[2]}"] = " ".join(p[3:])
    return out


def ring():
    folder = HERE / "Motion_Ring"
    txt = (folder / "Form1_designer.ring").read_text(encoding="utf-8")
    check("Ring designer loads _radfx.ring + RadFx_Add for 16 animations", 'load "_radfx.ring"' in txt
          and txt.count("RadFx_Add(") == 16)
    check("Ring: click trigger passes the event on (RadFx_Pass)", "RadFx_Pass(" in txt)
    out = ring_run(folder, RING_TEST)
    if out is None:
        skip("Ring run", "ring.exe not found")
        return
    r = ring_results(out)
    check("Ring: slide in starts left of the design position", int(float(r.get("t0.titlex", "999"))) < 20, out[-800:])
    check("Ring: slide in ends at the design position", r.get("t1.titlex") == "20", r)
    check("Ring: typewriter ends with the whole text", r.get("t1.titletext") == "Hello,_motion!", r)
    check("Ring: shake / move chain / flip ran", r.get("t2.shakex") == "20" and r.get("t2.movex") == "80"
          and r.get("t2.movey") == "110" and r.get("t2.flipw") == "120", r)
    check("Ring: On hide (fade out) hides the label", r.get("t2.infovisible") == "0", r)
    out2 = ring_run(folder, RING_TEST.replace('see "R t0 titlex "', 'see "R t0 titlex "'),
                    env={"RADIDE_REDUCED_MOTION": "1"})
    r2 = ring_results(out2)
    check("Ring: reduced motion shows the end at once", r2.get("t0.titlex") == "20", r2)


# =============================================================================== 5. Kivy
KIVY_EXEC = """
import json
from kivy.clock import Clock
R = {}
def a(dt):
    R['title_text'] = scr.lblTitle.text
    R['title_tx'] = scr.lblTitle._rad_look.tx
    scr.BeginAnimation('fx3')
    scr.BeginAnimation('fx7')
    scr.btnHide_Click()
    Clock.schedule_once(b, 0.2)
def b(dt):
    R['shake_mid'] = scr.btnShake._rad_look.tx
    R['rot_mid'] = scr.btnSpin._rad_look.rot
    R['info_op_mid'] = scr.lblInfo.opacity
    Clock.schedule_once(c, 1.2)
def c(dt):
    R['shake_end'] = scr.btnShake._rad_look.tx
    R['info_visible'] = scr.lblInfo.visible
    open(r'$OUT', 'w').write(json.dumps(R))
Clock.schedule_once(a, 2.0)
"""


def kivy():
    r = kivy_run(HERE / "Motion_Kivy", KIVY_EXEC, secs=7)
    if r is None:
        skip("Kivy run", "kivy is not installed")
        return
    check("Kivy: load animations ended (typewriter + slide)", r.get("title_text") == "Hello, motion!"
          and r.get("title_tx") == 0, r)
    check("Kivy: shake / rotate run (canvas Translate / Rotate)", r.get("shake_mid", 0) != 0
          and r.get("rot_mid", 0) > 0, r)
    check("Kivy: On hide fades then hides", 0 < r.get("info_op_mid", 0) < 1 and r.get("info_visible") is False, r)
    check("Kivy: shake ends where it started", r.get("shake_end") == 0, r)


# =============================================================================== 6. React Native
def rn():
    r = rn_run(HERE / "rn_harness" / "motion_entry.js")
    if r is None:
        skip("React Native run", "node / esbuild not available")
        return
    check("RN: load animations (typewriter mid-way, slide)", r.get("titleMid", "x") != "Hello, motion!"
          and r.get("title") == "Hello, motion!" and r.get("titleTx") == 0, r)
    check("RN: click triggers through fireAny / hasHandler", r.get("wantsClick") is True and r.get("shakeMid", 0) != 0
          and r.get("shakeEnd") == 0, r)
    check("RN: after-chain (move then bounce)", r.get("moveTx") == 60 and r.get("moveTyChained", 0) < 0, r)
    check("RN: On hide / On show", r.get("infoVisible") is False and r.get("infoShown") is True, r)
    check("RN: timer colour (JS clock channel)", r.get("boxColorChanged") is True, r)
    check("RN: hover zoom and back on leave", r.get("hoverScale") == 1.15 and r.get("hoverBack") == 1, r)


# =============================================================================== 7. WinForms
def wf_form(f):
    def add(kind, name, x, y, w, h, **p):
        c = f.add(kind, x, y)
        c.props.update(Name=name, Left=x, Top=y, Width=w, Height=h, **p)
        return c
    add("Label", "lblTitle", 20, 14, 300, 28, Text="Hello, motion!")
    add("Button", "btnShake", 20, 60, 110, 30, Text="Shake me")
    add("Button", "btnMove", 20, 110, 110, 30, Text="Move")
    add("Label", "lblInfo", 150, 164, 260, 24, Text="Info", BackColor="#ffe08a")
    add("Panel", "pnlBox", 300, 60, 120, 80, BackColor="#3399ff")
    motion.add(f, "lblTitle", "slideIn", id="fx1", durationMs=600, params={"from": "left", "distance": 120})
    motion.add(f, "lblTitle", "typewriter", id="fx2", durationMs=900)
    motion.add(f, "btnShake", "shake", id="fx3", trigger={"on": "click"})
    motion.add(f, "btnMove", "move", id="fx5", durationMs=400, params={"dx": 60}, trigger={"on": "click"})
    motion.add(f, "btnMove", "bounce", id="fx6", durationMs=500, trigger={"on": "after", "after": "fx5"})
    motion.add(f, "lblInfo", "fadeOut", id="fx8", trigger={"on": "click", "source": "btnShake"})
    motion.add(f, "pnlBox", "colorTo", id="fx10", durationMs=700, params={"color": "#ff7a59"})


def winforms():
    for lang in ("cs", "vb"):
        res = winforms_case(lang, wf_form, clicks="btnShake,btnMove")
        if res is None:
            skip("WinForms", "dotnet not found")
            return
        ok, log, st, report, dst = res
        designer = (dst / f"Form1.Designer.{lang}").read_text(encoding="utf-8-sig")
        check(f"WinForms {lang}: Save wrote the sidecar + partial", any("radide.json" in x for x in report)
              and any(f"RadFx.{lang}" in x for x in report), report)
        check(f"WinForms {lang}: the Designer file has no RAD IDE animation data", "radfx" not in designer.lower()
              and "animations" not in designer)
        check(f"WinForms {lang}: dotnet build", ok, log)
        if not ok:
            continue
        t1, t2, t3 = st.get("t1", {}), st.get("t2", {}), st.get("t3", {})
        check(f"WinForms {lang}: load animations ended", t1.get("lblTitle", {}).get("x") == 20
              and t1.get("lblTitle", {}).get("text") == "Hello, motion!", t1)
        check(f"WinForms {lang}: click -> shake mid-way, move", t2.get("btnShake", {}).get("x", 20) != 20
              and t2.get("btnMove", {}).get("x", 20) > 20, t2)
        check(f"WinForms {lang}: shake back, move + bounce chain ended", t3.get("btnShake", {}).get("x") == 20
              and t3.get("btnMove", {}).get("x") == 80 and t3.get("btnMove", {}).get("y") == 110, t3)
        check(f"WinForms {lang}: fade fallback hid the label (colour restored)", t3.get("lblInfo", {}).get("visible")
              is False and t3.get("lblInfo", {}).get("back") == "#ffe08a", t3)
        check(f"WinForms {lang}: colorTo on load", t1.get("pnlBox", {}).get("back") == "#ff7a59", t1)
        # reload: the sidecar brings the animations back
        from radide.foreign import winforms_cs as W
        f2 = W.load_form(dst / f"Form1.Designer.{lang}")
        check(f"WinForms {lang}: reopened form has its animations (sidecar)", len(f2.extra.get("animations") or []) == 7)
    # a user OnLoad override is respected
    from radide.foreign import winforms_fx
    src, notes = winforms_fx.generate(_tiny(), "namespace X;\npartial class Form1 {}",
                                      "protected override void OnLoad(EventArgs e) { base.OnLoad(e); }", "cs")
    check("WinForms: user OnLoad override -> no generated OnLoad + note", "override void OnLoad" not in src
          and notes and "RadFxAttach" in notes[0])


def _tiny():
    f = Form()
    c = f.add("Button", 0, 0)
    motion.add(f, c.name, "shake")
    return f


# =============================================================================== 8. Web
PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>radfx</title></head><body>
<h1 id="t" class="radfx radfx-bounce">Bounce on load</h1>
<p id="c" class="radfx radfx-shake" data-radfx-trigger="click">Shake on click</p>
<p id="s" class="radfx radfx-fadeIn" data-radfx-trigger="click" data-radfx-source="c">Fade in after click of c</p>
<p id="v" class="radfx radfx-zoom" data-radfx-trigger="visible" style="margin-top:3000px">Zoom when visible</p>
<div class="rad-two-pane"><div>A</div><div>B</div></div>
</body></html>"""


def web():
    from radide.web_site import design
    html, files = design.add_radfx(PAGE, ROOT / "x" / "index.html")
    check("web: add_radfx links radfx.css + radfx.js", 'href="radfx.css"' in html and 'src="radfx.js"' in html
          and len(files) == 2)
    check("web: add_radfx is idempotent", design.add_radfx(html, ROOT / "x" / "index.html")[0] == html)
    check("web: a page without Animate is unchanged", design.add_radfx("<html><head></head><body><p>x</p></body></html>",
                                                                       ROOT / "x" / "i.html")[0].count("radfx") == 0)
    check("web: foldable devices in the Design View", any(d == "duoSpanned" for _t, d in design.DesignView.DEVICES)
          if hasattr(design, "DesignView") else True)
    check("web: hinge of Surface Duo spanned", design.device_hinge("duoSpanned") == [540, 26])
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer, QUrl
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWidgets import QApplication
    except Exception as e:  # noqa: BLE001
        skip("web page in QtWebEngine", e)
        return
    QCoreApplication.setOrganizationName("RADIDE-TEST")
    QCoreApplication.setApplicationName("RADIDE-TEST-slice-d")
    _KEEP.append(QApplication.instance() or QApplication(sys.argv[:1]))
    tmp = ROOT / "samples" / "Tests" / "Motion" / "Targets" / "Motion_Web"
    tmp.mkdir(exist_ok=True)
    (tmp / "index.html").write_text(html, encoding="utf-8")
    for p, t in files.items():
        (tmp / p.name).write_text(t, encoding="utf-8")

    def js(view, code, ms=0):
        loop = QEventLoop()
        res = {}
        QTimer.singleShot(ms, lambda: view.page().runJavaScript(code, lambda v: (res.setdefault("v", v), loop.quit())))
        QTimer.singleShot(ms + 8000, loop.quit)
        loop.exec()
        return res.get("v")
    v = QWebEngineView()
    v.resize(800, 600)
    v.show()
    loop = QEventLoop()
    v.loadFinished.connect(lambda ok: loop.quit())
    v.load(QUrl.fromLocalFile(str(tmp / "index.html")))
    QTimer.singleShot(15000, loop.quit)
    loop.exec()
    an = "(id) => getComputedStyle(document.getElementById(id)).animationName"
    r1 = js(v, f"JSON.stringify(['t','c','s','v'].map({an}))", 300)
    r2 = js(v, f"document.getElementById('c').click(); JSON.stringify(['c','s'].map({an}))", 50)
    js(v, "document.getElementById('v').scrollIntoView(); 0", 50)
    r3 = js(v, f"JSON.stringify(['v'].map({an}))", 600)
    r4 = js(v, "getComputedStyle(document.querySelector('.rad-two-pane')).gridTemplateColumns.split(' ').length", 0)
    check("web: On load -> radfx-bounce, click / visible wait", r1 == '["radfx-bounce","none","none","none"]', r1)
    check("web: click -> shake on c and fade in of s (source)", r2 == '["radfx-shake","radfx-fadeIn"]', r2)
    check("web: visible -> zoom (IntersectionObserver)", r3 == '["radfx-zoom"]', r3)
    check("web: .rad-two-pane splits a wide window in two", r4 == 2, r4)
    # the GrapesJS Design View page
    v2 = QWebEngineView()
    v2.resize(1100, 700)
    v2.show()
    loop = QEventLoop()
    v2.loadFinished.connect(lambda ok: loop.quit())
    v2.load(QUrl.fromLocalFile(str(design.DESIGNER_HTML)))
    QTimer.singleShot(20000, loop.quit)
    loop.exec()
    devs = js(v2, "JSON.stringify(radEditor.Devices.getAll().map(d => d.id))", 1500)
    check("Design View: GrapesJS devices include the foldables", devs and "duoSpanned" in devs and "foldOpen" in devs, devs)
    fr = js(v2, "radDevice('tablet'); radSizeFrame('This size only: Tablet', null); "
                "document.body.classList.contains('rad-size-only') && "
                "getComputedStyle(document.getElementById('rad-size-label')).display !== 'none'", 300)
    check("Design View: orange 'This size only' frame + label on a non-desktop device", fr is True, fr)
    hg = js(v2, "radDevice('duoSpanned'); radSizeFrame('x', [540, 26]); "
                "!!document.querySelector('.rad-hinge')", 500)
    check("Design View: hinge band of Surface Duo spanned", hg is True, hg)
    tr = js(v2, "!!radEditor.TraitManager.getType('radfx')", 0)
    check("Design View: Animate trait type registered", tr is True, tr)
    _KEEP.extend([v, v2])          # deleted by os._exit at the end (QtWebEngine teardown is fragile)


_KEEP: list = []


def main() -> int:
    pure()
    sys.path.insert(0, str(HERE))
    import make_targets
    make_targets.build()
    check("samples rebuilt", (HERE / "Motion_Ring" / "_radfx.ring").is_file()
          and (HERE / "Motion_Flutter" / "lib" / "radmotion.dart").is_file()
          and (HERE / "Motion_Kivy" / "radkivyfx.py").is_file() and (HERE / "Motion_Expo" / "radfx.js").is_file())
    ring()
    res = flutter_check(HERE / "Motion_Flutter")
    if not res:
        skip("Flutter", "flutter not found")
    for name, ok, detail in res:
        check(f"Flutter (Motion_Flutter): {name}", ok, detail)
    kivy()
    rn()
    winforms()
    web()
    return summary()


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)          # QtWebEngine may crash while tearing down at interpreter exit
