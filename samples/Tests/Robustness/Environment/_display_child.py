"""Child of test_env_display_locale.py: designer geometry under one QT_SCALE_FACTOR, screen restore, themes.

    QT_SCALE_FACTOR=1.5 python _display_child.py dpi|screens|themes
Prints  REPORT {json}."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
mode = sys.argv[1]

import PyQt6.QtWebEngineWidgets  # noqa: E402,F401
from PyQt6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, QRect, QSettings, Qt  # noqa: E402
from PyQt6.QtGui import QColor, QGuiApplication, QMouseEvent  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST-ENV")
QCoreApplication.setApplicationName("RADIDE-TEST-ENV")
app = QApplication(sys.argv[:1])
QSettings().clear()
for _n in ("warning", "critical", "information", "question"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
rep: dict = {"mode": mode, "dpr": None}


def pump(n=4):
    for _ in range(n):
        app.processEvents()


L = Qt.MouseButton.LeftButton


def mouse(w, kind, pos):
    t = {"press": QEvent.Type.MouseButtonPress, "move": QEvent.Type.MouseMove,
         "release": QEvent.Type.MouseButtonRelease}[kind]
    btn = Qt.MouseButton.NoButton if kind == "move" else L
    btns = L if kind in ("press", "move") else Qt.MouseButton.NoButton
    p = QPointF(QPoint(*pos))
    QApplication.sendEvent(w, QMouseEvent(t, p, w.mapToGlobal(p), btn, btns, Qt.KeyboardModifier.NoModifier))
    pump(1)


def drag(w, a, b, steps=5):
    mouse(w, "press", a)
    for i in range(1, steps + 1):
        mouse(w, "move", (a[0] + (b[0] - a[0]) * i // steps, a[1] + (b[1] - a[1]) * i // steps))
    mouse(w, "release", b)


def geo(c):
    return [int(c.props[k]) for k in ("Left", "Top", "Width", "Height")]


if mode == "dpi":
    from radide.designer import DesignerView, handle_rects
    from radide.document import FormDocument
    from radide.model import Form
    f = Form()
    f.props["Width"], f.props["Height"] = 480, 360
    doc = FormDocument(f, Path(tempfile.gettempdir()) / "radide-envdpi.form")
    for name, x, y in (("b1", 16, 16), ("b2", 160, 120)):
        c = f.add("Button", x, y)
        c.props["Name"] = name
    doc._normalize()
    view = DesignerView(doc)
    view.resize(900, 700)
    view.show()
    pump()
    ov = view.overlay
    rep["dpr"] = ov.devicePixelRatioF()
    rep["overlay_size"] = [ov.width(), ov.height()]
    b1, b2 = f.find("b1"), f.find("b2")
    doc.select(b1)
    drag(ov, (30, 25), (70, 49))
    rep["drag"] = geo(b1)
    doc.select(b1)
    pump()
    br = handle_rects(ov.abs_rect(b1))[4].center()
    drag(ov, (br.x(), br.y()), (br.x() + 30, br.y() + 16))
    rep["resize"] = geo(b1)
    # snapline: drag b2 so that its left edge comes 2 px from b1's left edge -> it sticks
    doc.select(b2)
    l1, l2 = int(b1.props["Left"]), int(b2.props["Left"])
    start = (l2 + 10, int(b2.props["Top"]) + 8)
    drag(ov, start, (start[0] - (l2 - l1) + 2, start[1] + 40))
    rep["snap_left"] = [int(b2.props["Left"]), l1]
    view.set_zoom(1.5)
    pump()
    doc.select(b1)
    c = ov.abs_rect(b1).center()
    drag(ov, (c.x(), c.y()), (c.x() + 48, c.y()))
    rep["zoom_drag"] = geo(b1)
    view.set_zoom(1.0)
    img = ov.grab()
    rep["grab_logical"] = [round(img.width() / img.devicePixelRatio()), round(img.height() / img.devicePixelRatio())]
    rep["form_size"] = [int(f.props["Width"]), int(f.props["Height"])]
    rep["saved_props"] = {c.name: geo(c) for c in f.controls}

elif mode == "screens":
    from radide import screenfit
    screenfit.install(app)
    av = QGuiApplication.primaryScreen().availableGeometry()
    rep["screen"] = [av.x(), av.y(), av.width(), av.height()]
    out = {}
    for label, (x, y, w, h) in {"right monitor gone": (av.right() + 1200, 200, 500, 300),
                                "left/top monitor gone": (-2500, -1500, 500, 300),
                                "bigger than the screen": (100, 100, av.width() + 900, av.height() + 700)}.items():
        d = QDialog()
        d.setWindowTitle(label)
        lay = QVBoxLayout(d)
        lay.addWidget(QLabel("Restored dialog"))
        lay.addWidget(QPushButton("OK"))
        d.setGeometry(x, y, w, h)
        d.show()
        pump(8)
        fg = d.frameGeometry()
        out[label] = {"geometry": [fg.x(), fg.y(), fg.width(), fg.height()], "visible": av.intersects(fg),
                      "inside": av.contains(fg)}
        d.close()
    # the main window: geometry saved on a second monitor that is gone at the next start
    from radide.app import MainWindow
    w1 = MainWindow()
    w1.setGeometry(av.right() + 1600, 300, 1000, 700)
    saved = w1.saveGeometry()
    w1.close()
    w2 = MainWindow()
    w2.restoreGeometry(saved)
    w2.show()
    pump(10)
    fg = w2.frameGeometry()
    out["main window, monitor gone"] = {"geometry": [fg.x(), fg.y(), fg.width(), fg.height()],
                                        "visible": av.intersects(fg), "inside": True}
    rep["windows"] = out

elif mode == "themes":
    from radide import theme as T
    from radide.designer import DesignerView
    from radide.document import FormDocument
    from radide.model import Form

    def lum(c: QColor) -> float:
        def ch(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * ch(c.red()) + 0.7152 * ch(c.green()) + 0.0722 * ch(c.blue())

    def ratio(a, b) -> float:
        la, lb = sorted((lum(QColor(a)), lum(QColor(b))), reverse=True)
        return (la + 0.05) / (lb + 0.05)

    def drawn_contrast(widget, rect: QRect) -> float:
        """Contrast between the darkest and the lightest pixel in *rect* of the rendered widget."""
        img = widget.grab(rect).toImage()
        ls = [lum(img.pixelColor(x, y)) for x in range(0, img.width(), 1) for y in range(0, img.height(), 1)]
        return (max(ls) + 0.05) / (min(ls) + 0.05) if ls else 0

    pairs = [("window", "text"), ("base", "text"), ("button", "button_text"), ("highlight", "highlight_text"),
             ("menu", "menu_text"), ("menu_sel", "menu_sel_text"), ("tab_sel", "tab_sel_text"),
             ("status", "status_text"), ("tooltip", "tooltip_text"), ("header", "header_text"),
             ("banner", "banner_text"), ("title1", "title_text")]
    out = {}
    for name in T.THEMES:
        T.apply(name)
        t = T.current()
        pump()
        tokens = {f"{bg}/{fg}": round(ratio(t[bg], t[fg]), 2) for bg, fg in pairs if bg in t and fg in t}
        d = QDialog()
        lay = QVBoxLayout(d)
        lab = QLabel("Readable dialog text  نص عربي")
        lay.addWidget(lab)
        btn = QPushButton("Button")
        lay.addWidget(btn)
        d.resize(320, 120)
        d.show()
        pump()
        dlg = round(drawn_contrast(lab, lab.rect()), 2)
        btn_c = round(drawn_contrast(btn, btn.rect().adjusted(4, 4, -4, -4)), 2)
        d.close()
        f = Form()
        f.props["Width"], f.props["Height"] = 300, 200
        doc = FormDocument(f, Path(tempfile.gettempdir()) / "radide-envtheme.form")
        c = f.add("Button", 20, 20)
        c.props["Name"], c.props["Text"] = "b", "Caption"
        c2 = f.add("Label", 20, 70)
        c2.props["Name"], c2.props["Text"] = "l", "Label text"
        doc._normalize()
        view = DesignerView(doc)
        view.resize(500, 400)
        view.show()
        pump()
        sf = view.surface
        r_btn = QRect(20, 20, int(c.props["Width"]), int(c.props["Height"])).adjusted(3, 3, -3, -3)
        r_lab = QRect(20, 70, int(c2.props["Width"]), int(c2.props["Height"]))
        des_btn = round(drawn_contrast(sf, r_btn), 2)
        des_lab = round(drawn_contrast(sf, r_lab), 2)
        view.close()
        out[name] = {"tokens": tokens, "dialog_label": dlg, "dialog_button": btn_c, "designer_button": des_btn,
                     "designer_label": des_lab}
    rep["themes"] = out
print("REPORT " + json.dumps(rep, ensure_ascii=False), flush=True)
os._exit(0)
