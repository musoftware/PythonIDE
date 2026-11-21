"""Car Fault Guide (Tools > Car Fault Guide...): the fault knowledge base inside the IDE (docs/CARDIAG.md).

Tabs: Fault Codes (lookup and search in English / Arabic, manufacturer packs), Warning Lights ("What light is on?"
picker with RAD IDE's own icons), Symptoms (question wizard -> likely causes -> the live data to watch) and Explain
with AI (DTCs + freeze frame + live data to the IDE's AI provider; the knowledge-base explanation works offline).

The Car Diagnostics workbench (features/cardiag_scan.py) gets the same guide as its "Guide" tab through
``cardiag_scan.TAB_HOOKS``; "Scan the car" and "Watch in Live Data" go to that workbench, and "Use the car's data"
takes its fault codes, freeze frame and live values. Other slices call ``win.cardiag_guide.show_code(code)``.
"""
from __future__ import annotations

import html as _html

from PyQt6.QtCore import QByteArray, QEvent, QRectF, QSize, Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QIcon, QImage, QPainter, QPixmap, QTextDocument
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QRadioButton,
                             QScrollArea, QSplitter, QTabWidget, QTextBrowser, QToolButton, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

ROLE = Qt.ItemDataRole.UserRole
SEV_RANK = {"red": 0, "amber": 1, "green": 2}


def _lang() -> str:
    try:
        from ..i18n import language
        return language() or "en"
    except Exception:  # noqa: BLE001
        return "en"


def tr(text: str) -> str:
    try:
        from ..i18n import tr as _t
        return _t(text)
    except Exception:  # noqa: BLE001
        return text


def _esc(s) -> str:
    return _html.escape(str(s), quote=False)


def light_image(light_id: str, colour: str = "", size: int = 48) -> QImage:
    """The warning light's SVG icon rendered to an image."""
    from ..cardiag.kb import lights as L
    from PyQt6.QtSvg import QSvgRenderer
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    r = QSvgRenderer(QByteArray(L.svg(light_id, colour, size).encode("utf-8")))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r.render(p, QRectF(0, 0, size, size))
    p.end()
    return img


def light_icon(light_id: str, colour: str = "", size: int = 48) -> QIcon:
    return QIcon(QPixmap.fromImage(light_image(light_id, colour, size)))


def _html_page(body: str) -> str:
    rtl = _lang() == "ar"
    return (f"<div dir='{'rtl' if rtl else 'ltr'}' style='font-size:10.5pt'>{body}</div>")


def code_html(info: dict, lang: str) -> str:
    """The detail page of one fault code (knowledge-base entry)."""
    from ..cardiag import kb
    from ..cardiag.kb.vocab import SEVERITY_COLOR
    t = (lambda f: kb.text(info, f, lang))
    h = [f"<h2 style='margin-bottom:0'>{_esc(info['code'])}</h2>",
         f"<h3 style='margin-top:2px'>{_esc(t('title'))}</h3>"]
    if lang == "ar" and info.get("title") and info.get("title") != info.get("title_ar"):
        h.append(f"<p style='color:gray;margin-top:0' dir='ltr'>{_esc(info['title'])}</p>")
    if info.get("ftb") is not None:
        h.append(f"<p><b>{_esc(tr('Failure type:'))}</b> {_esc(info['ftb_text'][1 if lang == 'ar' else 0])}</p>")
    meta = []
    if info.get("severity"):
        col = SEVERITY_COLOR.get(info["severity"], "#888")
        meta.append(f"<b>{_esc(tr('Severity:'))}</b> <span style='color:{col}'>&#9679; "
                    f"{_esc(t('severity_text'))}</span>")
    if info.get("system_name"):
        meta.append(f"<b>{_esc(tr('System:'))}</b> {_esc(t('system_name'))}")
    if info.get("monitor_name"):
        meta.append(f"<b>{_esc(tr('Readiness monitor:'))}</b> {_esc(t('monitor_name'))}")
    if info.get("specific"):
        src = info.get("source", "")
        meta.append(f"<b>{_esc(tr('Source:'))}</b> " + (_esc(tr("manufacturer pack")) + f" {_esc(src[5:])}"
                                                        if src.startswith("pack:") else
                                                        _esc(tr("manufacturer-specific - meaning varies"))))
    if meta:
        h.append("<p>" + "<br>".join(meta) + "</p>")
    if info.get("safety"):
        h.append(f"<p style='color:#d33a2c'><b>{_esc(tr('Safety-relevant:'))}</b> "
                 f"{_esc(tr('Have it checked before driving on; do not clear it just to turn the lamp off.'))}</p>")
    if info.get("drive_text"):
        h.append(f"<p><b>{_esc(tr('Safe to drive?'))}</b> {_esc(t('drive_text'))}</p>")
    if info.get("explain"):
        h.append(f"<p>{_esc(t('explain'))}</p>")
    cs = t("causes")
    if cs:
        h.append(f"<h4>{_esc(tr('Common causes (most likely first)'))}</h4><ol>"
                 + "".join(f"<li>{_esc(c)}</li>" for c in cs) + "</ol>")
    ch = t("checks")
    if ch:
        h.append(f"<h4>{_esc(tr('What to check first'))}</h4><ol>"
                 + "".join(f"<li>{_esc(c)}</li>" for c in ch) + "</ol>")
    links = []
    if info.get("pids"):
        links.append(f"<a href='watch:{','.join(str(p) for p in info['pids'])}'>{_esc(tr('Watch in Live Data'))}</a>")
    links.append(f"<a href='scan:'>{_esc(tr('Scan the car'))}</a>")
    links.append(f"<a href='ai:{_esc(info['code'])}'>{_esc(tr('Explain with AI'))}</a>")
    h.append("<p>" + " &nbsp;|&nbsp; ".join(links) + "</p>")
    if info.get("related"):
        h.append(f"<p><b>{_esc(tr('Related codes:'))}</b> "
                 + ", ".join(f"<a href='code:{_esc(r)}'>{_esc(r)}</a>" for r in info["related"]) + "</p>")
    if info.get("obd_emissions") and not info.get("specific"):
        h.append(f"<p style='color:gray'>{_esc(tr('Emissions-related code: after the repair it is cleared normally; the readiness monitors then need a drive cycle to complete again.'))}</p>")
    return _html_page("".join(h))


# ============================================================================================ the guide widget
class CarFaultGuide(QWidget):
    def __init__(self, win=None, workbench=None, parent=None):
        super().__init__(parent)
        self.win = win
        self.wb = workbench                    # the Car Diagnostics workbench this guide belongs to (or None)
        self.setObjectName("CarFaultGuide")
        self._light_buttons: dict[str, QToolButton] = {}
        self._answers: dict[str, str] = {}
        self._job = None
        self._ai_text = ""
        self._pending_pids: list[int] = []
        self._build()
        self.search("")

    # ------------------------------------------------------------------ layout
    def _build(self) -> None:
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 4, 4, 4)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("CarGuideTabs")
        self.tabs.addTab(self._build_codes(), tr("Fault Codes"))
        self.tabs.addTab(self._build_lights(), tr("Warning Lights"))
        self.tabs.addTab(self._build_symptoms(), tr("Symptoms"))
        self.tabs.addTab(self._build_ai(), tr("Explain with AI"))
        v.addWidget(self.tabs)

    def _browser(self, name: str) -> QTextBrowser:
        b = QTextBrowser()
        b.setObjectName(name)
        b.setOpenLinks(False)
        b.anchorClicked.connect(self._link)
        b.setProperty("i18n_skip", True)
        return b

    # ---- Fault codes
    def _build_codes(self) -> QWidget:
        from ..cardiag.kb import vocab
        w = QWidget()
        w.setObjectName("CarGuideTab_Codes")
        v = QVBoxLayout(w)
        top = QHBoxLayout()
        self.q = QLineEdit()
        self.q.setObjectName("CarGuideSearch")
        self.q.setPlaceholderText(tr("Code, words or symptom (e.g. P0217, overheating, won't start)"))
        self.q.setClearButtonEnabled(True)
        self._qtimer = QTimer(self)
        self._qtimer.setSingleShot(True)
        self._qtimer.setInterval(200)
        self._qtimer.timeout.connect(lambda: self.search(self.q.text()))
        self.q.textChanged.connect(lambda *_: self._qtimer.start())
        self.q.returnPressed.connect(lambda: self.search(self.q.text()))
        top.addWidget(self.q, 1)
        self.f_sys = QComboBox()
        self.f_sys.setObjectName("CarGuideSystem")
        self.f_sys.addItem(tr("All systems"), "")
        for k in vocab.SYSTEMS:
            self.f_sys.addItem(vocab.name(vocab.SYSTEMS, k, _lang()), k)
        self.f_sys.setProperty("i18n_skip_items", True)
        self.f_sys.currentIndexChanged.connect(lambda *_: self.search(self.q.text()))
        top.addWidget(self.f_sys)
        self.f_sev = QComboBox()
        self.f_sev.setObjectName("CarGuideSeverity")
        self.f_sev.addItem(tr("Any severity"), "")
        for k in ("red", "amber", "green"):
            self.f_sev.addItem(vocab.name(vocab.SEVERITY, k, _lang()), k)
        self.f_sev.setProperty("i18n_skip_items", True)
        self.f_sev.currentIndexChanged.connect(lambda *_: self.search(self.q.text()))
        top.addWidget(self.f_sev)
        v.addLayout(top)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.results = QTreeWidget()
        self.results.setObjectName("CarGuideResults")
        self.results.setHeaderLabels([tr("Code"), tr("Title"), tr("Severity")])
        self.results.setRootIsDecorated(False)
        self.results.setProperty("i18n_skip_items", True)
        self.results.currentItemChanged.connect(lambda cur, _p: self._show_result(cur))
        split.addWidget(self.results)
        self.detail = self._browser("CarGuideDetail")
        split.addWidget(self.detail)
        split.setSizes([420, 620])
        v.addWidget(split, 1)
        bottom = QHBoxLayout()
        self.cov = QLabel()
        self.cov.setObjectName("CarGuideCoverage")
        self.cov.setProperty("i18n_skip", True)
        bottom.addWidget(self.cov, 1)
        b = QPushButton(tr("Import Manufacturer Codes..."))
        b.setObjectName("CarGuideImport")
        b.setToolTip(tr("CSV or JSON definitions of manufacturer-specific codes that you are allowed to use"))
        b.clicked.connect(lambda: self.import_pack())
        bottom.addWidget(b)
        b = QPushButton(tr("Save Template..."))
        b.clicked.connect(self._save_template)
        bottom.addWidget(b)
        self.b_packs = QPushButton(tr("Remove Pack..."))
        self.b_packs.clicked.connect(self._remove_pack)
        bottom.addWidget(self.b_packs)
        v.addLayout(bottom)
        self._coverage()
        return w

    def _coverage(self) -> None:
        from ..cardiag import kb
        s = kb.stats()
        bp = s["by_prefix"]
        txt = tr("Knowledge base: {} codes").replace("{}", str(s["total"])) + "  (" + ", ".join(
            f"{k}xxx {n}" for k, n in sorted(bp.items())) + ")"
        if s["packs"]:
            txt += "  " + tr("Packs:") + " " + ", ".join(f"{n} ({c})" for n, _m, c in s["packs"])
        self.cov.setText(txt)

    def search(self, query: str) -> list:
        from ..cardiag import kb
        lang = _lang()
        res = kb.search(query, limit=300, system=self.f_sys.currentData() or "",
                        severity=self.f_sev.currentData() or "")
        if not query.strip() and not res:
            res = [(c, 0.0) for c in ("P0217", "P0300", "P0171", "P0420", "P0562", "P0128", "P0455", "U0100",
                                      "C0035", "B0001")]
        n = kb.normalize_code(query)
        if n is not None and n[1] is not None:            # "C0035-1F": show the failure type too
            res = [(query.strip().upper(), 1001.0)] + res
        self.results.clear()
        from ..cardiag.kb.vocab import SEVERITY_COLOR
        from PyQt6.QtGui import QColor
        for code, _score in res:
            info = kb.lookup(code)
            if info is None:
                continue
            it = QTreeWidgetItem([info["code"], kb.text(info, "title", lang),
                                  kb.text(info, "severity_text", lang).split(" - ")[0]])
            it.setData(0, ROLE, info["code"])
            if info.get("severity"):
                it.setForeground(2, QColor(SEVERITY_COLOR[info["severity"]]))
            if info.get("safety"):
                it.setForeground(0, QColor("#d33a2c"))
            self.results.addTopLevelItem(it)
        self.results.resizeColumnToContents(0)
        if self.results.topLevelItemCount():
            self.results.setCurrentItem(self.results.topLevelItem(0))
        elif query.strip():
            self.detail.setHtml(_html_page(f"<p>{_esc(tr('Nothing found. Try other words, a code (P0217) or a symptom.'))}</p>"))
        return res

    def _show_result(self, it) -> None:
        if it is None:
            return
        self._show_code_page(it.data(0, ROLE))

    def _show_code_page(self, code: str) -> None:
        from ..cardiag import kb
        make = ""
        info = kb.lookup(code, make)
        if info is None:
            return
        self._current_code = info["code"]
        self.detail.setHtml(code_html(info, _lang()))

    def show_code(self, code: str = "") -> None:
        """Open the Fault Codes tab on *code* (used by the service and scan slices)."""
        self.tabs.setCurrentIndex(0)
        if code:
            self.q.setText(code)
            self._qtimer.stop()
            self.search(code)

    # ---- packs
    def import_pack(self, path: str | None = None, make: str = ""):
        from ..cardiag import kb
        if not path:
            path, _f = QFileDialog.getOpenFileName(self, tr("Import Manufacturer Codes"), "",
                                                   tr("Code definitions (*.csv *.json)"))
            if not path:
                return None
        try:
            pack = kb.import_pack(path, make=make)
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, tr("Import Manufacturer Codes"), tr("The pack was not imported:") + f"\n{e}")
            return None
        self._coverage()
        self.search(self.q.text())
        QMessageBox.information(self, tr("Import Manufacturer Codes"),
                                tr("{} code definitions imported.").replace("{}", str(len(pack["codes"]))))
        return pack

    def _save_template(self) -> None:
        from ..cardiag import kb
        path, _f = QFileDialog.getSaveFileName(self, tr("Save Template"), "dtc-pack-template.csv", "CSV (*.csv)")
        if path:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                f.write(kb.TEMPLATE_CSV)

    def _remove_pack(self) -> None:
        from ..cardiag import kb
        from PyQt6.QtWidgets import QInputDialog
        names = [p["name"] for p in kb.packs()]
        if not names:
            QMessageBox.information(self, tr("Remove Pack"), tr("No manufacturer packs are installed."))
            return
        name, ok = QInputDialog.getItem(self, tr("Remove Pack"), tr("Pack:"), names, 0, False)
        if ok and name:
            kb.remove_pack(name)
            self._coverage()
            self.search(self.q.text())

    # ---- Warning lights
    def _build_lights(self) -> QWidget:
        from ..cardiag.kb import lights as L
        w = QWidget()
        w.setObjectName("CarGuideTab_Lights")
        v = QVBoxLayout(w)
        self.l_head = QLabel(tr("Which warning lights are on? Click every light you see on the dashboard."))
        self.l_head.setWordWrap(True)
        v.addWidget(self.l_head)
        split = QSplitter(Qt.Orientation.Horizontal)
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(4)
        for i, lid in enumerate(L.ids()):
            light = L.LIGHTS[lid]
            b = QToolButton()
            b.setObjectName(f"CarGuideLight_{lid}")
            b.setCheckable(True)
            b.setIcon(light_icon(lid, "", 48))
            b.setIconSize(QSize(40, 40))
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.setText(L.text(light.name, _lang()))
            b.setProperty("i18n_skip", True)
            b.setMinimumSize(118, 82)
            b.setAutoRaise(True)
            b.toggled.connect(lambda _on: self.update_lights())
            grid.addWidget(b, i // 4, i % 4)
            self._light_buttons[lid] = b
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(grid_w)
        split.addWidget(sc)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.l_flash = QCheckBox(tr("The light is flashing / red"))
        self.l_flash.setObjectName("CarGuideFlashing")
        self.l_flash.toggled.connect(lambda _on: self.update_lights())
        rv.addWidget(self.l_flash)
        self.l_view = self._browser("CarGuideLightView")
        rv.addWidget(self.l_view, 1)
        row = QHBoxLayout()
        self.l_read = QPushButton(tr("Read the Car's Lights"))
        self.l_read.setObjectName("CarGuideLightRead")
        self.l_read.setToolTip(tr("Ask the connected car which warning lights are on (check-engine lamp from OBD-II; "
                                  "the others from the instrument cluster when it is known, or from the faults of "
                                  "the ABS / airbag units)"))
        self.l_read.clicked.connect(lambda: self.read_car_lights())
        row.addWidget(self.l_read)
        self.l_scan = QPushButton(tr("Scan the Car"))
        self.l_scan.setObjectName("CarGuideLightScan")
        self.l_scan.clicked.connect(lambda: self.scan())
        row.addWidget(self.l_scan)
        self.l_watch = QPushButton(tr("Watch in Live Data"))
        self.l_watch.setObjectName("CarGuideLightWatch")
        self.l_watch.clicked.connect(lambda: self.watch(self._light_result.get("pids", [])))
        row.addWidget(self.l_watch)
        b = QPushButton(tr("Clear Selection"))
        b.clicked.connect(self.clear_lights)
        row.addWidget(b)
        row.addStretch(1)
        rv.addLayout(row)
        split.addWidget(right)
        split.setSizes([520, 520])
        v.addWidget(split, 1)
        self._light_result: dict = {}
        self.update_lights()
        return w

    def selected_lights(self) -> list[str]:
        return [lid for lid, b in self._light_buttons.items() if b.isChecked()]

    def select_lights(self, ids, flashing: bool = False) -> dict:
        for lid, b in self._light_buttons.items():
            b.blockSignals(True)
            b.setChecked(lid in ids)
            b.blockSignals(False)
        self.l_flash.blockSignals(True)
        self.l_flash.setChecked(flashing)
        self.l_flash.blockSignals(False)
        self.tabs.setCurrentIndex(1)
        return self.update_lights()

    def clear_lights(self) -> None:
        self._light_source = ""
        self.select_lights([])

    def read_car_lights(self):
        """Which lights are on in the connected car: the check-engine lamp (MIL) from OBD-II 01 01 on every car;
        the instrument cluster's lamp word on the Demo car simulator (on real cars that identifier is
        manufacturer-specific); ABS / airbag lights inferred from confirmed faults of those units after Scan All
        Control Units. The result is selected in the picker with its explanation. Runs in the background."""
        wb = self._workbench(create=False)
        if wb is None or wb.client is None:
            QMessageBox.information(self, tr("Car Fault Guide"),
                                    tr("Connect to the car (or the Demo car) in the Car Diagnostics workbench first."))
            return None
        client, link = wb.client, wb.link
        entries = list(getattr(wb, "entries", []) or [])

        def work():
            lit, src = set(), ["obd"]
            if any(st.mil for st in client.readiness().values()):
                lit.add("mil")
            try:
                from ..cardiag.service.definitions import is_virtual_car_link
                if is_virtual_car_link(link):
                    from ..cardiag.link.uds import UdsClient
                    from ..cardiag.sim.car import LAMPS
                    bits = int.from_bytes(UdsClient(link, 0x720, 0x728).read_did(0x2220)[:2], "big")
                    lit |= {key for bit, key, _en, _ar in LAMPS if bits >> bit & 1}
                    src.append("cluster")
            except Exception:  # noqa: BLE001 - the lamp word is optional
                pass
            for e in entries:
                if "uds" in e.kinds and "stored" in e.kinds:
                    if e.code.startswith("C0"):
                        lit.add("abs")
                        src.append("faults")
                    elif e.code.startswith("B00"):
                        lit.add("airbag")
                        src.append("faults")
            return lit, src

        def done(r, e):
            if e is not None or not r:
                return
            lit, src = r
            parts = [tr("check-engine lamp from OBD-II")]
            if "cluster" in src:
                parts.append(tr("the other lamps from the instrument cluster"))
            if "faults" in src:
                parts.append(tr("ABS / airbag lamps inferred from the faults of those units"))
            self._light_source = tr("Read from the car:") + " " + ", ".join(parts) + "."
            self.select_lights(sorted(x for x in lit if x in self._light_buttons))
            self.car_lights = sorted(lit)
        self.car_lights = None
        wb.run(work, done, "Reading the warning lights...")
        return True

    def _car_codes(self) -> list[str]:
        wb = self._workbench(create=False)
        return [e.code for e in getattr(wb, "entries", []) or []] if wb is not None else []

    def update_lights(self) -> dict:
        from ..cardiag import kb
        from ..cardiag.kb import lights as L
        lang = _lang()
        ids = self.selected_lights()
        doc = self.l_view.document()
        if not ids:
            self._light_result = {}
            self.l_view.setHtml(_html_page(f"<p>{_esc(tr('Select the lights that are on.'))}</p>"
                                           "<p>" + _esc(tr("Red = stop safely and check before driving on. "
                                                           "Amber = have it checked soon. Green / blue = information."))
                                           + "</p>"))
            self.l_watch.setEnabled(False)
            return {}
        colours = {}
        for lid in ids:
            light = L.LIGHTS[lid]
            if self.l_flash.isChecked():
                colours[lid] = "flashing" if "flashing" in light.colours else ("red" if "red" in light.colours
                                                                               else light.colours[0])
        r = L.pick(ids, colours, present=self._car_codes(), lang=lang)
        self._light_result = r
        h = []
        if getattr(self, "_light_source", ""):
            h.append(f"<p style='color:gray'>{_esc(self._light_source)}</p>")
        if r["stop"]:
            h.append(f"<p style='color:#d33a2c;font-weight:bold'>{_esc(tr('A red or flashing light: stop safely or reduce load now, then read the advice below.'))}</p>")
        for lid in ids:
            light = L.LIGHTS[lid]
            col = colours.get(lid) or light.colours[0]
            if col not in light.do_now:
                col = light.colours[0]
            doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(f"light:{lid}"),
                            light_image(lid, col, 40))
            h.append(f"<table><tr><td><img src='light:{lid}' width='40' height='40'></td><td>&nbsp;</td><td>"
                     f"<b>{_esc(L.text(light.name, lang))}</b><br><span style='color:gray'>"
                     f"{_esc(L.COLOURS[col][2 if lang == 'ar' else 1])}</span></td></tr></table>")
            h.append(f"<p>{_esc(L.text(light.meaning, lang))}</p>")
            h.append(f"<p><b>{_esc(tr('What to do now:'))}</b> {_esc(L.text(light.do_now[col], lang))}</p>")
            if not light.obd and light.module[0]:
                h.append(f"<p style='color:gray'>{_esc(tr('Its codes are stored in:'))} "
                         f"{_esc(L.text(light.module, lang))} - "
                         f"{_esc(tr('a generic OBD-II engine scan does not show them; use a connection that can read that unit.'))}</p>")
        for c in r["combos"]:
            h.append(f"<p style='background:#fff3cd;color:#5a4500;padding:4px'><b>{_esc(tr('Together:'))}</b> {_esc(c)}</p>")
        if r["codes"]:
            car = set(self._car_codes())
            h.append(f"<h4>{_esc(tr('Likely fault codes'))}</h4><ul>")
            for code, _s in r["codes"][:15]:
                info = kb.lookup(code) or {}
                mark = f" <b>({_esc(tr('reported by the car'))})</b>" if code in car else ""
                h.append(f"<li><a href='code:{code}'>{code}</a> - {_esc(kb.text(info, 'title', lang))}{mark}</li>")
            h.append("</ul>")
        h.append(f"<p><a href='scan:'>{_esc(tr('Scan the car to see which codes are really stored'))}</a></p>")
        self.l_view.setHtml(_html_page("".join(h)))
        self.l_watch.setEnabled(bool(r["pids"]))
        return r

    # ---- Symptoms wizard
    def _build_symptoms(self) -> QWidget:
        from ..cardiag.kb import symptoms as S
        w = QWidget()
        w.setObjectName("CarGuideTab_Symptoms")
        v = QHBoxLayout(w)
        left = QVBoxLayout()
        self.s_find = QLineEdit()
        self.s_find.setObjectName("CarGuideSymptomFind")
        self.s_find.setPlaceholderText(tr("Describe it (e.g. the engine overheats, shakes at idle)"))
        self.s_find.returnPressed.connect(lambda: self.find_symptom(self.s_find.text()))
        left.addWidget(self.s_find)
        self.s_list = QListWidget()
        self.s_list.setObjectName("CarGuideSymptoms")
        self.s_list.setProperty("i18n_skip_items", True)
        for sid in S.ids():
            it = QListWidgetItem(S.text(S.SYMPTOMS[sid]["name"], _lang()))
            it.setData(ROLE, sid)
            self.s_list.addItem(it)
        self.s_list.currentItemChanged.connect(lambda cur, _p: self.start_symptom(cur.data(ROLE)) if cur else None)
        left.addWidget(self.s_list, 1)
        lw = QWidget()
        lw.setLayout(left)
        lw.setMinimumWidth(180)
        mid = QVBoxLayout()
        self.s_intro = QLabel()
        self.s_intro.setWordWrap(True)
        self.s_intro.setProperty("i18n_skip", True)
        mid.addWidget(self.s_intro)
        self.s_qbox = QWidget()
        self.s_qlay = QVBoxLayout(self.s_qbox)
        self.s_qlay.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(self.s_qbox)
        mid.addWidget(sc, 1)
        mw = QWidget()
        mw.setLayout(mid)
        right = QVBoxLayout()
        self.s_view = self._browser("CarGuideSymptomView")
        right.addWidget(self.s_view, 1)
        row = QHBoxLayout()
        self.s_watch = QPushButton(tr("Watch in Live Data"))
        self.s_watch.setObjectName("CarGuideSymptomWatch")
        self.s_watch.clicked.connect(lambda: self.watch(self._sym_result.get("pids", [])))
        row.addWidget(self.s_watch)
        b = QPushButton(tr("Scan the Car"))
        b.clicked.connect(lambda: self.scan())
        row.addWidget(b)
        b = QPushButton(tr("Explain with AI"))
        b.clicked.connect(self._symptom_to_ai)
        row.addWidget(b)
        row.addStretch(1)
        right.addLayout(row)
        rw = QWidget()
        rw.setLayout(right)
        mw.setMinimumWidth(260)
        sp = QSplitter(Qt.Orientation.Horizontal)
        sp.addWidget(lw)
        sp.addWidget(mw)
        sp.addWidget(rw)
        sp.setStretchFactor(0, 2)
        sp.setStretchFactor(1, 3)
        sp.setStretchFactor(2, 4)
        sp.setSizes([220, 340, 440])
        v.addWidget(sp, 1)
        self._symptom = ""
        self._sym_result: dict = {}
        return w

    def find_symptom(self, text: str) -> list[str]:
        from ..cardiag.kb import symptoms as S
        found = S.match(text)
        if found:
            self.select_symptom(found[0])
        else:
            self.s_view.setHtml(_html_page(f"<p>{_esc(tr('No matching symptom - pick one from the list.'))}</p>"))
        return found

    def select_symptom(self, sid: str) -> None:
        self.tabs.setCurrentIndex(2)
        for i in range(self.s_list.count()):
            if self.s_list.item(i).data(ROLE) == sid:
                if self.s_list.currentRow() == i:
                    self.start_symptom(sid)
                else:
                    self.s_list.setCurrentRow(i)
                return

    def start_symptom(self, sid: str) -> None:
        from ..cardiag.kb import symptoms as S
        lang = _lang()
        self._symptom = sid
        self._answers = {}
        d = S.SYMPTOMS[sid]
        self.s_intro.setText(f"<b>{_esc(S.text(d['name'], lang))}</b><br>{_esc(S.text(d.get('intro'), lang))}")
        while self.s_qlay.count():
            it = self.s_qlay.takeAt(0)
            old = it.widget()
            if old is not None:
                old.hide()
                old.deleteLater()
        self._qgroups = {}
        for q in d["questions"]:
            g = QGroupBox(S.text(q["text"], lang))
            g.setObjectName(f"CarGuideQ_{q['id']}")
            g.setProperty("i18n_skip", True)
            gl = QVBoxLayout(g)
            grp = QButtonGroup(g)
            for o in q["options"]:
                rb = QRadioButton(S.text(o["text"], lang))
                rb.setObjectName(f"CarGuideA_{q['id']}_{o['id']}")
                rb.setProperty("i18n_skip", True)
                rb.toggled.connect(lambda on, qid=q["id"], oid=o["id"]: on and self.answer(qid, oid))
                grp.addButton(rb)
                gl.addWidget(rb)
            self.s_qlay.addWidget(g)
            self._qgroups[q["id"]] = grp
        self.s_qlay.addStretch(1)
        self._show_symptom()

    def answer(self, qid: str, oid: str) -> dict:
        self._answers[qid] = oid
        for b in getattr(self, "_qgroups", {}).get(qid, QButtonGroup()).buttons():
            if b.objectName() == f"CarGuideA_{qid}_{oid}" and not b.isChecked():
                b.blockSignals(True)
                b.setChecked(True)
                b.blockSignals(False)
        return self._show_symptom()

    def _show_symptom(self) -> dict:
        from ..cardiag.kb import symptoms as S
        from ..cardiag.obd import pids as P
        if not self._symptom:
            return {}
        lang = _lang()
        r = S.evaluate(self._symptom, self._answers, lang)
        self._sym_result = r
        h = []
        if r["stop"]:
            h.append(f"<p style='color:#d33a2c;font-weight:bold'>{_esc(tr('Safety first - read the notes before driving on.'))}</p>")
        for n in r["notes"]:
            h.append(f"<p style='background:#fff3cd;color:#5a4500;padding:4px'>{_esc(n)}</p>")
        h.append(f"<h3>{_esc(tr('Likely causes'))}</h3>")
        h.append(f"<p style='color:gray'>{_esc(tr('Answered {} of {} questions - more answers give a better ranking.').replace('{}', str(r['answered']), 1).replace('{}', str(r['questions']), 1))}</p><ol>")
        for c in r["causes"]:
            h.append(f"<li><b>{_esc(c['name'])}</b> ({c['percent']} %)<br>{_esc(c['explain'])}<br>"
                     f"<i>{_esc(tr('Check:'))}</i> {_esc(c['check'])}</li>")
        h.append("</ol>")
        if r["watch"]:
            h.append(f"<h4>{_esc(tr('Live data to watch'))}</h4><ul>")
            for pid, hint in r["watch"]:
                try:
                    pname = tr(P.get(pid).name)
                except Exception:  # noqa: BLE001
                    pname = f"PID {pid:02X}"
                h.append(f"<li><b>{_esc(pname)}</b>: {_esc(hint)}</li>")
            h.append(f"</ul><p><a href='watch:{','.join(str(p) for p in r['pids'])}'>{_esc(tr('Watch these in Live Data'))}</a></p>")
        if r["codes"]:
            h.append(f"<h4>{_esc(tr('Fault codes that often come with it'))}</h4><p>"
                     + ", ".join(f"<a href='code:{c}'>{c}</a>" for c, _t in r["codes"][:14]) + "</p>")
        self.s_view.setHtml(_html_page("".join(h)))
        return r

    def _symptom_to_ai(self) -> None:
        if self._symptom:
            self.ai_symptoms = [self._symptom]
        self.tabs.setCurrentIndex(3)
        self._ai_context_label()

    # ---- Explain with AI
    def _build_ai(self) -> QWidget:
        w = QWidget()
        w.setObjectName("CarGuideTab_AI")
        v = QVBoxLayout(w)
        g = QGridLayout()
        g.addWidget(QLabel(tr("Fault codes:")), 0, 0)
        self.ai_codes = QLineEdit()
        self.ai_codes.setObjectName("CarGuideAICodes")
        self.ai_codes.setPlaceholderText("P0217, P0128")
        g.addWidget(self.ai_codes, 0, 1)
        b = QPushButton(tr("Use the Car's Data"))
        b.setObjectName("CarGuideAIUseCar")
        b.setToolTip(tr("Fault codes, freeze frame and live values from the Car Diagnostics workbench"))
        b.clicked.connect(lambda: self.use_car_data())
        g.addWidget(b, 0, 2)
        g.addWidget(QLabel(tr("Your question:")), 1, 0)
        self.ai_q = QLineEdit()
        self.ai_q.setObjectName("CarGuideAIQuestion")
        self.ai_q.setPlaceholderText(tr("Optional - e.g. can I drive to work?"))
        g.addWidget(self.ai_q, 1, 1, 1, 2)
        g.addWidget(QLabel(tr("Answer language:")), 2, 0)
        self.ai_lang = QComboBox()
        self.ai_lang.setObjectName("CarGuideAILang")
        self.ai_lang.addItem("العربية", "ar")
        self.ai_lang.addItem("English", "en")
        self.ai_lang.setProperty("i18n_skip_items", True)
        g.addWidget(self.ai_lang, 2, 1)
        v.addLayout(g)
        self.ai_ctx = QLabel()
        self.ai_ctx.setObjectName("CarGuideAIContext")
        self.ai_ctx.setWordWrap(True)
        self.ai_ctx.setProperty("i18n_skip", True)
        v.addWidget(self.ai_ctx)
        row = QHBoxLayout()
        self.b_offline = QPushButton(tr("Explain (Knowledge Base)"))
        self.b_offline.setObjectName("CarGuideAIOffline")
        self.b_offline.clicked.connect(lambda: self.explain_offline())
        row.addWidget(self.b_offline)
        self.b_ask = QPushButton(tr("Ask AI"))
        self.b_ask.setObjectName("CarGuideAIAsk")
        self.b_ask.clicked.connect(lambda: self.ask_ai())
        row.addWidget(self.b_ask)
        self.b_stop = QPushButton(tr("Stop"))
        self.b_stop.setEnabled(False)
        self.b_stop.clicked.connect(self._stop_ai)
        row.addWidget(self.b_stop)
        b = QPushButton(tr("Show Prompt"))
        b.setObjectName("CarGuideAIPrompt")
        b.clicked.connect(self._show_prompt)
        row.addWidget(b)
        row.addStretch(1)
        self.ai_status = QLabel()
        self.ai_status.setObjectName("CarGuideAIStatus")
        self.ai_status.setProperty("i18n_skip", True)
        row.addWidget(self.ai_status)
        v.addLayout(row)
        self.ai_out = self._browser("CarGuideAIOut")
        v.addWidget(self.ai_out, 1)
        note = QLabel(tr("The AI answer is a suggestion to help you understand the fault - confirm it with a check "
                         "or a measurement before replacing parts."))
        note.setWordWrap(True)
        note.setStyleSheet("color:gray")
        v.addWidget(note)
        self.ai_freeze: list = []
        self.ai_live: list = []
        self.ai_vehicle: dict = {}
        self.ai_readiness: list = []
        self.ai_symptoms: list = []
        self.provider = None                     # tests can set a provider object (radide.ai Provider)
        self._ai_context_label()
        return w

    def _ai_context_label(self) -> None:
        bits = []
        if self.ai_freeze:
            bits.append(tr("freeze frame"))
        if self.ai_live:
            bits.append(tr("{} live values").replace("{}", str(len(self.ai_live))))
        if self.selected_lights():
            bits.append(tr("warning lights"))
        if self.ai_symptoms:
            bits.append(tr("symptom"))
        if self.ai_vehicle.get("vin"):
            bits.append("VIN " + self.ai_vehicle["vin"])
        self.ai_ctx.setText((tr("Also sent:") + " " + ", ".join(bits)) if bits else
                            tr("Tip: \"Use the Car's Data\" adds the freeze frame and live values from the scan tool."))

    def context(self):
        from ..cardiag.kb.ai import Context
        codes = [c.strip() for c in self.ai_codes.text().replace(";", ",").replace(" ", ",").split(",") if c.strip()]
        wb = self._workbench(create=False)
        dtcs = []
        car = {e.code: e for e in getattr(wb, "entries", []) or []} if wb is not None else {}
        for c in codes:
            e = car.get(c.upper())
            dtcs.append({"code": c, "ecu": getattr(e, "ecu", ""), "kinds": sorted(getattr(e, "kinds", []) or [])}
                        if e is not None else c)
        return Context(dtcs=dtcs, freeze=list(self.ai_freeze), live=list(self.ai_live), vehicle=dict(self.ai_vehicle),
                       lights=self.selected_lights(), symptoms=list(self.ai_symptoms), readiness=list(self.ai_readiness),
                       question=self.ai_q.text())

    def use_car_data(self) -> bool:
        """Take fault codes, freeze frames, live values and the VIN from the Car Diagnostics workbench."""
        wb = self._workbench(create=False)
        if wb is None or (getattr(wb, "client", None) is None and not getattr(wb, "entries", None)):
            QMessageBox.information(self, tr("Explain with AI"),
                                    tr("Connect to the car in Tools > Car Diagnostics... and read the fault codes "
                                       "first."))
            return False
        from ..cardiag.obd import pids as P
        codes = []
        for e in wb.entries or []:
            if e.code not in codes:
                codes.append(e.code)
        self.ai_codes.setText(", ".join(codes))
        self.ai_freeze = []
        for _ecu, ff in sorted((getattr(wb, "freeze", {}) or {}).items()):
            vals = []
            try:
                for r in ff.readings():
                    for j, val in enumerate(r.values[:3]):
                        name = P.get(r.pid).name + (f" [{j + 1}]" if j else "")
                        vals.append((name, val.value, val.unit))
            except Exception:  # noqa: BLE001
                pass
            if vals:
                self.ai_freeze.append({"dtc": getattr(ff, "dtc", ""), "values": vals})
        self.ai_live = []
        t = getattr(wb, "live_table", None)
        if t is not None:
            for r in range(t.rowCount()):
                items = [t.item(r, c) for c in range(3)]
                if all(items) and items[1].text() not in ("", "-"):
                    self.ai_live.append((items[0].text(), items[1].text(), items[2].text()))
        vi = getattr(wb, "vinfo", None)
        self.ai_vehicle = {"vin": getattr(vi, "vin", "") or ""} if vi is not None else {}
        self._ai_context_label()
        return True

    def explain_offline(self) -> str:
        from ..cardiag.kb import ai as kbai
        txt = kbai.offline_explanation(self.context(), self.ai_lang.currentData())
        self._set_ai_text(txt, rtl=self.ai_lang.currentData() == "ar")
        self.ai_status.setText(tr("Knowledge base (offline)"))
        return txt

    def _set_ai_text(self, txt: str, rtl: bool) -> None:
        self._ai_text = txt
        body = "<br>".join(_esc(line) for line in txt.splitlines())
        self.ai_out.setHtml(f"<div dir='{'rtl' if rtl else 'ltr'}' style='font-size:10.5pt'>{body}</div>")

    def _show_prompt(self) -> None:
        from ..cardiag.kb import ai as kbai
        system, user = kbai.build_prompt(self.context(), self.ai_lang.currentData())
        self._set_ai_text("[system]\n" + system + "\n\n[user]\n" + user, rtl=False)

    def ask_ai(self):
        from ..cardiag.kb import ai as kbai
        ctx = self.context()
        if not ctx.dtcs and not ctx.lights and not ctx.symptoms and not ctx.question.strip():
            QMessageBox.information(self, tr("Explain with AI"),
                                    tr("Enter fault codes, select warning lights or a symptom, or ask a question."))
            return None
        lang = self.ai_lang.currentData()
        offline = kbai.offline_explanation(ctx, lang)
        try:
            job = kbai.ask(ctx, lang, provider=self.provider)
        except Exception as e:  # noqa: BLE001 - no AI configured: the knowledge base still answers
            self._set_ai_text(tr("AI is not available:") + f" {e}\n\n" + offline, rtl=lang == "ar")
            self.ai_status.setText(tr("Knowledge base (offline)"))
            return None
        self._job = job
        self._ai_text = ""
        self.ai_status.setText(tr("Asking {}...").replace("{}", getattr(job, "provider_id", "") or "AI"))
        self.b_stop.setEnabled(True)
        self.b_ask.setEnabled(False)
        rtl = lang == "ar"

        def delta(s):
            self._ai_text += s
            self._set_ai_text(self._ai_text, rtl)

        def finished(full):
            self._job = None
            self.b_stop.setEnabled(False)
            self.b_ask.setEnabled(True)
            self._set_ai_text((full or self._ai_text).strip(), rtl)
            self.ai_status.setText(tr("AI answer"))

        def failed(msg):
            self._job = None
            self.b_stop.setEnabled(False)
            self.b_ask.setEnabled(True)
            self._set_ai_text(tr("AI is not available:") + f" {msg}\n\n" + offline, rtl)
            self.ai_status.setText(tr("Knowledge base (offline)"))
        job.delta.connect(delta)
        job.finished.connect(finished)
        job.failed.connect(failed)
        return job

    def _stop_ai(self) -> None:
        if self._job is not None:
            self._job.cancel()

    # ------------------------------------------------------------------ links to the scan tool
    def _workbench(self, create: bool = True):
        if self.wb is not None:
            try:
                self.wb.objectName()
                return self.wb
            except RuntimeError:
                self.wb = None
        scan = getattr(self.win, "cardiag_scan", None)
        if scan is None:
            return None
        wb = getattr(scan, "wb", None)
        if wb is not None:
            try:
                wb.objectName()
            except RuntimeError:
                wb = None
        if wb is None and create:
            wb = scan.open()
        return wb

    def _show_workbench(self, wb) -> None:
        scan = getattr(self.win, "cardiag_scan", None)
        if self.wb is None and scan is not None:
            scan.open()

    def scan(self) -> bool:
        """Open the Car Diagnostics workbench and read the codes (when connected)."""
        wb = self._workbench()
        if wb is None:
            QMessageBox.information(self, tr("Car Fault Guide"), tr("The Car Diagnostics scan tool is not available."))
            return False
        self._show_workbench(wb)
        wb.tabs.setCurrentIndex(0)
        if wb.client is None:
            QMessageBox.information(self, tr("Car Fault Guide"),
                                    tr("Connect to the car (or the Demo car) in the Car Diagnostics workbench, then "
                                       "read the fault codes."))
            return False
        wb.read_codes()
        return True

    def watch(self, pids) -> bool:
        """Select these PIDs in the workbench's Live Data (after connecting if needed) and show it."""
        pids = [int(p) for p in pids or []]
        if not pids:
            return False
        wb = self._workbench()
        if wb is None:
            return False
        self._show_workbench(wb)
        if wb.client is None:
            self._pending_pids = pids
            try:
                wb.connected.connect(self._apply_pending, Qt.ConnectionType.UniqueConnection)
            except TypeError:
                pass
            QMessageBox.information(self, tr("Car Fault Guide"),
                                    tr("Connect to the car (or the Demo car): the live data will be selected "
                                       "automatically."))
            return False
        wb.select_pids(pids)
        wb.tabs.setCurrentWidget(wb.tabs.findChild(QWidget, "CarDiagTab_Live") or wb.tabs.widget(1))
        return True

    def _apply_pending(self, on: bool) -> None:
        if on and self._pending_pids:
            pids, self._pending_pids = self._pending_pids, []
            QTimer.singleShot(300, lambda: self.watch(pids))

    def _link(self, url: QUrl) -> None:
        s = url.toString()
        kind, _sep, arg = s.partition(":")
        if kind == "code":
            self.show_code(arg)
        elif kind == "watch":
            self.watch([int(x) for x in arg.split(",") if x.strip().isdigit()])
        elif kind == "scan":
            self.scan()
        elif kind == "ai":
            self.ai_codes.setText(arg)
            self.tabs.setCurrentIndex(3)
            self._ai_context_label()

    # ------------------------------------------------------------------ language
    def changeEvent(self, ev) -> None:
        super().changeEvent(ev)
        if ev.type() == QEvent.Type.LanguageChange:
            QTimer.singleShot(0, self.retranslate)

    def retranslate(self) -> None:
        """Knowledge-base texts follow the UI language."""
        try:
            from ..cardiag.kb import lights as L
            from ..cardiag.kb import symptoms as S
            from ..cardiag.kb import vocab
            lang = _lang()
            self.q.setPlaceholderText(tr("Code, words or symptom (e.g. P0217, overheating, won't start)"))
            self.s_find.setPlaceholderText(tr("Describe it (e.g. the engine overheats, shakes at idle)"))
            self.ai_q.setPlaceholderText(tr("Optional - e.g. can I drive to work?"))
            for lid, b in self._light_buttons.items():
                b.setText(L.text(L.LIGHTS[lid].name, lang))
            for i in range(self.s_list.count()):
                it = self.s_list.item(i)
                it.setText(S.text(S.SYMPTOMS[it.data(ROLE)]["name"], lang))
            self.f_sys.setItemText(0, tr("All systems"))
            self.f_sev.setItemText(0, tr("Any severity"))
            self._coverage()
            self._ai_context_label()
            for combo, table in ((self.f_sys, vocab.SYSTEMS), (self.f_sev, vocab.SEVERITY)):
                for i in range(1, combo.count()):
                    combo.setItemText(i, vocab.name(table, combo.itemData(i), lang))
            cur = self.results.currentItem()
            code = cur.data(0, ROLE) if cur is not None else None
            self.search(self.q.text())
            if code:
                self._show_code_page(code)
            self.update_lights()
            if self._symptom:
                answers = dict(self._answers)
                self.start_symptom(self._symptom)
                for q, o in answers.items():
                    self.answer(q, o)
        except RuntimeError:
            pass


# ============================================================================================= IDE glue
class CarDiagGuide:
    def __init__(self, win):
        self.win = win
        self.guide: CarFaultGuide | None = None
        win.cardiag_guide = self
        QTimer.singleShot(0, self._menus)
        try:
            from . import cardiag_scan
            if self._hook not in cardiag_scan.TAB_HOOKS:
                cardiag_scan.TAB_HOOKS.append(self._hook)
        except Exception:  # noqa: BLE001 - the scan tool is optional
            pass

    @staticmethod
    def plain(text: str) -> str:
        return text.replace("&&", "\x00").replace("&", "").replace("\x00", "&")

    def _menus(self) -> None:
        tools = next((a.menu() for a in self.win.menuBar().actions()
                      if a.menu() is not None and self.plain(a.text()) == "Tools"), None)
        if tools is None or any(a.objectName() == "CarFaultGuideAction" for a in tools.actions()):
            return
        a = QAction("Car Fault &Guide...", tools)
        a.setObjectName("CarFaultGuideAction")
        a.setToolTip("Fault codes explained, warning lights, symptoms, explain with AI")
        a.triggered.connect(lambda: self.open())
        tools.addAction(a)
        self.action = a

    def _hook(self, wb) -> None:
        g = CarFaultGuide(self.win, workbench=wb)
        g.setObjectName("CarFaultGuideTab")
        wb.guide = g
        wb.add_tab(g, "Guide")

    def open(self, tab: int | None = None) -> CarFaultGuide:
        alive = False
        if self.guide is not None:
            try:
                alive = self.guide.parent() is not None or self.guide.isVisible()
            except RuntimeError:
                alive = False
        if not alive:
            self.guide = CarFaultGuide(self.win)
        show = getattr(self.win, "_show_tab", None)
        if callable(show):
            show(self.guide, tr("Car Fault Guide"))
        else:
            self.guide.show()
        if tab is not None:
            self.guide.tabs.setCurrentIndex(tab)
        return self.guide

    def show_code(self, code: str = "") -> CarFaultGuide:
        g = self.open()
        g.show_code(code)
        return g

    def show_lights(self, ids=()) -> CarFaultGuide:
        g = self.open(1)
        if ids:
            g.select_lights(list(ids))
        return g

    def show_symptom(self, sid: str = "") -> CarFaultGuide:
        g = self.open(2)
        if sid:
            g.select_symptom(sid)
        return g


def install(win) -> None:
    CarDiagGuide(win)
