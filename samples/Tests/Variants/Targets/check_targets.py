"""Layout sizes (variants) and TwoPane on the non-Python targets (plan MOTION_VARIANTS_FOLDABLES slice D).

    python samples/Tests/Variants/Targets/check_targets.py

1. Pure: the generated code of every target uses variants.plan() (Ring rows, Flutter rv.pick / RadTwoPane,
   Kivy root.radsizes / RadTwoPane, React Native placeV / useSizes / TwoPane); forms without sizes are
   unchanged.
2. make_targets.py rebuilds Variants_Ring / Variants_Flutter / Variants_Kivy / Variants_Expo.
3. Ring: the window is resized across the breakpoint (button moved + renamed, label hidden, title).  SKIP w/o Ring
4. Flutter: flutter analyze + flutter test (phone / tablet / half-open display feature).            SKIP w/o Flutter
5. Kivy: phone and tablet window sizes; RADIDE_HINGE splits the TwoPane.                            SKIP w/o Kivy
6. React Native: the screen renders in Node at phone and tablet widths.                             SKIP w/o node
7. WinForms C# / VB.NET: a "Small" size moves / renames a button when the window is narrowed.        SKIP w/o dotnet
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1] / "Motion" / "Targets"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(HERE))
from target_tools import (ROOT, check, flutter_check, kivy_run, ring_run, rn_run, skip, summary,  # noqa: E402
                          winforms_case)

sys.path.insert(0, str(ROOT))
from radide import fxtargets as FX  # noqa: E402
from radide.variants import model as vm  # noqa: E402


def pure():
    import make_targets
    make_targets.build()
    check("samples rebuilt", (HERE / "Variants_Flutter" / "lib" / "radlayout.dart").is_file()
          and (HERE / "Variants_Kivy" / "radkivyfx.py").is_file() and (HERE / "Variants_Expo" / "radfx.js").is_file()
          and (HERE / "Variants_Ring" / "_radfx.ring").is_file())
    from radide.model import Form
    f = Form.load(HERE / "Variants_Flutter" / "Form1.form")
    plan = FX.variant_plan(f)
    check("variant_plan: 3 sizes", plan and [s["id"] for s in plan["sizes"]] == ["phone", "tablet", "tabletop"])
    check("managed controls: btnGo", "btnGo" in FX.managed_controls(plan))
    check("when_tuple: posture spelled half-opened", FX.when_tuple({"posture": "HalfOpened"})[5] == "half-opened")
    tp = FX.two_panes(f)
    check("two_panes: TwoPane1 with colList / colDetail", tp and tp[0]["panes"] == ["colList", "colDetail"]
          and tp[0]["ratio"] == 0.4)
    ring = (HERE / "Variants_Ring" / "Form1_designer.ring").read_text(encoding="utf-8")
    check("Ring: size rows + resize filter", "Form1_VSizes" in ring and "Form1_ApplySizes()" in ring
          and "RadFx_Pass(" in ring)
    check("Ring: a moved control leaves the Anchor rows", "[btnGo," not in ring.split("Form1_Lay1 =")[-1].split("\n")[0])
    dart = (HERE / "Variants_Flutter" / "lib" / "form1_designer.dart").read_text(encoding="utf-8")
    check("Flutter: RadVariant + rv.pick + RadTwoPane", "RadVariant.of(context, _radSizes)" in dart
          and "rv.pick<double>(" in dart and "RadTwoPane(" in dart)
    kv = (HERE / "Variants_Kivy" / "Form1_designer.py").read_text(encoding="utf-8")
    check("Kivy: KV positions follow root.radsizes + RadTwoPane", "in root.radsizes" in kv and "RadTwoPane:" in kv)
    jsx = (HERE / "Variants_Expo" / "Form1_designer.jsx").read_text(encoding="utf-8")
    check("Expo: placeV / useSizes / TwoPane", "placeV(this, rv" in jsx and "useSizes(this, rv" in jsx
          and "<TwoPane " in jsx)
    # no sizes -> nothing generated
    plain = Form()
    plain.add("Button", 0, 0)
    check("no sizes -> variant_plan None", FX.variant_plan(plain) is None)
    # matching like CSS: later sizes win
    g = Form()
    g.props.update(Width=800, Height=600)
    vm.add_size(g, {"id": "a", "when": {"minWidth": 600}})
    vm.add_size(g, {"id": "b", "when": {"orientation": "landscape"}})
    check("cascade order kept", vm.matching(vm.sizes(g), 800, 600, None, None, None) == ["a", "b"])


RING_TEST = r'''load "Form1.ring"
oApp = NULL
nStep = 0
func main
    oApp = new qApp
    Form1_Show()
    oT = new qTimer(Form1)
    oT.setInterval(300)
    oT.setTimeoutEvent("Check()")
    oT.start()
    oApp.exec()
func Report cTag
    a = Form1_CurrentSizes()
    cs = ""
    for x in a cs += x + "," next
    see "R " + cTag + " " + QWidget_x(btnGo.pObject) + " " + QWidget_y(btnGo.pObject) + " " + QWidget_width(btnGo.pObject) + " " + substr(btnGo.text(), " ", "_") + " " + lblSide.isVisible() + " " + substr(Form1.windowTitle(), " ", "_") + " " + cs + " " + QWidget_width(pnlMain.pObject) + nl
func Check
    nStep += 1
    if nStep = 1 Report("base") Form1.resize(420, 400) return ok
    if nStep = 2 Report("small") Form1.resize(900, 400) return ok
    Report("wide")
    oApp.quit()
'''


def ring():
    out = ring_run(HERE / "Variants_Ring", RING_TEST)
    if out is None:
        skip("Ring run", "ring.exe not found")
        return
    r = {}
    for line in out.splitlines():
        p = line.split(" ")
        if len(p) >= 9 and p[0] == "R":
            r[p[1]] = p[2:]
    check("Ring: designed layout at 640 wide", r.get("base", [])[:4] == ["400", "20", "200", "Go"], out[-600:])
    check("Ring: Small size moves / renames the button, hides the label, retitles",
          r.get("small", [])[:6] == ["20", "340", "380", "Go_(small)", "0", "Sizes_(Ring)_-_small"], r.get("small"))
    check("Ring: anchored panel still stretches", r.get("small", ["0"] * 8)[7] == "380", r.get("small"))
    check("Ring: back to the designed look when wide (anchored right)",
          r.get("wide", [])[:6] == ["660", "20", "200", "Go", "1", "Sizes_(Ring)"], r.get("wide"))


KIVY_EXEC = """
import json
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
R = {}
def st(tag):
    R[tag] = {'sizes': list(scr.radsizes), 'btn_x': round((scr.btnGo.x - scr.ids['w__body'].x) / dp(1)),
              'text': scr.btnGo.text, 'side': scr.lblSide.visible, 'detail_op': scr.colDetail.opacity,
              'list_w': round(scr.colList.width / dp(1))}
st('phone')
Window.size = (dp(900), dp(700))
def b(dt):
    st('tablet')
    open(r'$OUT', 'w').write(json.dumps(R))
Clock.schedule_once(b, 1.0)
"""


def kivy():
    r = kivy_run(HERE / "Variants_Kivy", KIVY_EXEC, secs=6)
    if r is None:
        skip("Kivy run", "kivy is not installed")
        return
    ph, tb = r.get("phone", {}), r.get("tablet", {})
    check("Kivy: phone size, one pane", ph.get("sizes") == ["phone"] and ph.get("btn_x") == 16
          and ph.get("text") == "Go" and ph.get("side") is True and ph.get("detail_op") == 0, r)
    check("Kivy: tablet size moves / renames the button and hides the label", tb.get("sizes") == ["tablet"]
          and tb.get("btn_x") == 500 and tb.get("text") == "Go (tablet)" and tb.get("side") is False, r)
    # a vertical hinge band across the TwoPane (window coords, dp): both panes, split at the band
    r2 = kivy_run(HERE / "Variants_Kivy", KIVY_EXEC.replace("Window.size = (dp(900), dp(700))", "pass"),
                  env={"RADIDE_HINGE": "200,0,10,900"}, secs=6)
    ph2 = (r2 or {}).get("phone", {})
    check("Kivy: RADIDE_HINGE splits the TwoPane at the hinge", ph2.get("detail_op") == 1
          and ph2.get("list_w") == 200 - 16, r2)


def rn():
    r = rn_run(TOOLS / "rn_harness" / "variants_entry.js")
    if r is None:
        skip("React Native run", "node / esbuild not available")
        return
    ph, tb = r.get("phone", {}), r.get("tablet", {})
    check("RN: phone size = the designed layout", ph.get("sizes") == ["phone"] and ph.get("btnLeft") == 16
          and ph.get("text") == "Go" and ph.get("side") is True and ph.get("pane") is True, r)
    check("RN: tablet size moves / renames / hides", tb.get("sizes") == ["tablet"] and tb.get("btnLeft") == 500
          and tb.get("text") == "Go (tablet)" and tb.get("side") is False, r)


def wf_form(f):
    c = f.add("Button", 600, 20)
    c.props.update(Name="btnGo", Left=600, Top=20, Width=160, Height=30, Text="Go", Anchor="Top, Right")
    lbl = f.add("Label", 20, 20)
    lbl.props.update(Name="lblHint", Left=20, Top=20, Width=200, Height=24, Text="Only wide")
    vm.add_size(f, {"id": "small", "label": "Small", "when": {"maxWidth": 599}, "preview": {"width": 500, "height": 450}})
    for k, v in (("Left", 20), ("Top", 400), ("Width", 460)):
        vm.set_override(f, c, "small", k, v)
    vm.set_override(f, c, "small", "Text", "Go (small)")
    vm.set_override(f, lbl, "small", "Visible", False)


def winforms():
    for lang in ("cs", "vb"):
        res = winforms_case(lang, wf_form, resize="500,450", tag="_var")
        if res is None:
            skip("WinForms", "dotnet not found")
            return
        ok, log, st, _report, _dst = res
        check(f"WinForms {lang}: dotnet build", ok, log)
        if not ok:
            continue
        t1, t4 = st.get("t1", {}), st.get("t4", {})
        check(f"WinForms {lang}: designed layout at 800 wide", t1.get("btnGo", {}).get("x") == 600
              and t1.get("@sizes") == "", t1)
        check(f"WinForms {lang}: Small size at 500 wide", t4.get("@sizes") == "small" and t4.get("btnGo", {}).get("x") == 20
              and t4.get("btnGo", {}).get("y") == 400 and t4.get("btnGo", {}).get("w") == 460
              and t4.get("btnGo", {}).get("text") == "Go (small)" and t4.get("lblHint", {}).get("visible") is False, t4)


def qt_views():
    """SuperPreview hinge of the foldable presets and the Design View device combo (orange frame + hinge)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PyQt6.QtCore import QCoreApplication, QEventLoop, QSettings, QTimer
        from PyQt6.QtWidgets import QApplication
        from radide.web_site import design, superpreview as sp
    except Exception as e:  # noqa: BLE001
        skip("SuperPreview / Design View", e)
        return
    QCoreApplication.setOrganizationName("RADIDE-TEST")
    QCoreApplication.setApplicationName("RADIDE-TEST-slice-d-variants")
    app = QApplication.instance() or QApplication(sys.argv[:1])
    QSettings().clear()
    duo = next(i for i, p in enumerate(sp.PRESETS) if p.device == "surface_duo2")
    pane = sp.PreviewPane("A", duo, browsers={})
    pane.resize(900, 700)
    pane.show()
    for _ in range(5):
        app.processEvents()
    pane.layout_view()
    check("SuperPreview: Surface Duo spanned draws the hinge band", pane.hinge.isVisible()
          and pane.hinge.bands == [(540, 0, 26, 720, "band")], pane.hinge.bands)
    img = pane.hinge.grab().toImage()
    s = pane.hinge.scale
    c = img.pixelColor(int((540 + 13) * s), img.height() // 2)
    check("SuperPreview: the band is painted dark (widget.grab)", c.alpha() > 100 and c.red() < 80, c.name())
    pane.preset.setCurrentIndex(0)
    app.processEvents()
    check("SuperPreview: phones have no hinge", not pane.hinge.isVisible())
    pane.close()
    if not hasattr(design, "DesignView"):
        skip("Design View", "QtWebEngine missing")
        return
    from types import SimpleNamespace
    from target_tools import SCRATCH
    SCRATCH.mkdir(parents=True, exist_ok=True)
    page = SCRATCH / "dv_page.html"
    page.write_text("<!DOCTYPE html><html><head><title>t</title></head><body><h1>Hi</h1></body></html>",
                    encoding="utf-8")
    dv = design.DesignView(SimpleNamespace(project=None, log=print), page)
    dv.resize(1200, 800)
    dv.show()
    loop = QEventLoop()
    dv.ready.connect(loop.quit)
    QTimer.singleShot(25000, loop.quit)
    loop.exec()
    check("Design View ready", dv.is_ready())

    def js(code, ms=400):
        lp = QEventLoop()
        res = {}
        QTimer.singleShot(ms, lambda: dv.web.page().runJavaScript(code, lambda v: (res.setdefault("v", v), lp.quit())))
        QTimer.singleShot(ms + 8000, lp.quit)
        lp.exec()
        return res.get("v")
    dv.set_device("duoSpanned")
    r = js("JSON.stringify([radEditor.getDevice(), document.body.classList.contains('rad-size-only'), "
           "document.getElementById('rad-size-label').textContent, !!document.querySelector('.rad-hinge')])")
    check("Design View: Surface Duo device -> orange frame, This size only label, hinge band",
          r and '"duoSpanned",true,"This size only: Surface Duo 2 spanned (1106)",true' in r, r)
    img = dv.grab().toImage()
    check("Design View grab", not img.isNull())
    dv.set_device("desktop")
    r = js("document.body.classList.contains('rad-size-only')")
    check("Design View: Desktop -> no frame", r is False, r)
    dv.close()
    QSettings().clear()


def main() -> int:
    pure()
    ring()
    res = flutter_check(HERE / "Variants_Flutter")
    if not res:
        skip("Flutter", "flutter not found")
    for name, ok, detail in res:
        check(f"Flutter (Variants_Flutter): {name}", ok, detail)
    kivy()
    rn()
    winforms()
    qt_views()
    return summary()


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
