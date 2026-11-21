"""Qt dialogs for the Flutter designer's project resources (docs/FLUTTER_DESIGNER.md section 7.6):

* ``AssetManagerDialog``  - project assets with thumbnails: import images / SVG / Lottie / fonts, remove (refused
  while a screen uses the file), copy the Dart snippet, insert into the current screen.
* ``FontPickerDialog``    - search the Google Fonts library, pick weights, use it from google_fonts (runtime) or
  bundle it into the project (offline, licence copied) - download runs in a worker thread.
* ``ThemeEditorDialog``   - the project theme (screens/app.ftheme.json): seed colour + scheme variant, presets,
  light / dark / system, fonts, buttons, inputs, cards, app bar, with a live mock preview.

The logic lives in assets.py / fonts.py / themes.py; these classes only present it. Entry points:
``open_asset_manager(parent, folder)``, ``pick_font(parent, folder, current)``, ``edit_theme(parent, folder)``.
"""
from __future__ import annotations

import copy
from pathlib import Path

from PyQt6.QtCore import QObject, QRectF, QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
                             QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget)

from . import assets as AS
from . import fonts as FN
from . import themes as TH


# =========================================================================================== assets
class AssetManagerDialog(QDialog):
    """Project assets with thumbnails. ``selected_rel`` holds the chosen asset after 'Insert' (accept)."""

    def __init__(self, parent, project_folder, kind: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Project Assets")
        self.folder = Path(project_folder)
        self.kind = kind
        self.selected_rel: str | None = None
        self.resize(720, 520)
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.filter = QComboBox()
        for label, k in (("All assets", None), ("Images", "image"), ("SVG", "svg"), ("Lottie", "lottie"),
                         ("Fonts", "font"), ("Other", "other")):
            self.filter.addItem(label, k)
        if kind:
            self.filter.setCurrentIndex(max(0, self.filter.findData(kind)))
        self.filter.currentIndexChanged.connect(self.refresh)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter by name")
        self.search.textChanged.connect(self.refresh)
        top.addWidget(self.filter)
        top.addWidget(self.search, 1)
        b_import = QPushButton("Import...")
        b_import.clicked.connect(self.import_files)
        top.addWidget(b_import)
        lay.addLayout(top)
        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setIconSize(QSize(96, 96))
        self.list.setGridSize(QSize(128, 132))
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setWordWrap(True)
        self.list.currentItemChanged.connect(self._show_info)
        self.list.itemDoubleClicked.connect(lambda _i: self._insert())
        lay.addWidget(self.list, 1)
        self.info = QLabel()
        self.info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.info)
        row = QHBoxLayout()
        self.b_copy = QPushButton("Copy Dart")
        self.b_copy.clicked.connect(self._copy)
        self.b_remove = QPushButton("Remove")
        self.b_remove.clicked.connect(self._remove)
        row.addWidget(self.b_copy)
        row.addWidget(self.b_remove)
        row.addStretch(1)
        bb = QDialogButtonBox()
        self.b_insert = bb.addButton("Insert", QDialogButtonBox.ButtonRole.AcceptRole)
        bb.addButton(QDialogButtonBox.StandardButton.Close)
        self.b_insert.clicked.connect(self._insert)
        bb.rejected.connect(self.reject)
        row.addWidget(bb)
        lay.addLayout(row)
        self.refresh()

    def refresh(self):
        self.list.clear()
        k = self.filter.currentData()
        q = self.search.text().strip().lower()
        for a in AS.list_assets(self.folder, k):
            if q and q not in a.rel.lower():
                continue
            it = QListWidgetItem(a.name)
            try:
                it.setIcon(QIcon(QPixmap.fromImage(AS.thumbnail(self.folder / a.rel, 96))))
            except Exception:  # noqa: BLE001 - a broken file still gets listed
                pass
            it.setData(Qt.ItemDataRole.UserRole, a)
            it.setToolTip(a.rel)
            self.list.addItem(it)
        self._show_info(self.list.currentItem())

    def _current(self) -> AS.AssetInfo | None:
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def _show_info(self, *_):
        a = self._current()
        for b in (self.b_copy, self.b_remove, self.b_insert):
            b.setEnabled(a is not None)
        if a is None:
            self.info.setText(f"{self.list.count()} asset(s) in {self.folder.name}/assets")
            return
        used = AS.asset_usages(self.folder, a.rel)
        where = ", ".join(sorted({u[0] for u in used})) or "not used by a screen"
        self.info.setText(f"{a.rel}  -  {a.kind}, {a.size / 1024:.1f} KB  -  {where}")

    def import_files(self):
        files, _f = QFileDialog.getOpenFileNames(self, "Import assets", str(self.folder), AS.ALL_FILTER)
        if not files:
            return
        try:
            out = AS.import_many(self.folder, files)
        except OSError as e:
            QMessageBox.warning(self, "Import assets", str(e))
            return
        self.refresh()
        if out:
            for i in range(self.list.count()):
                if self.list.item(i).data(Qt.ItemDataRole.UserRole).rel == out[-1].rel:
                    self.list.setCurrentRow(i)
                    break

    def _copy(self):
        a = self._current()
        if a:
            QGuiApplication.clipboard().setText(a.dart_snippet())

    def _remove(self):
        a = self._current()
        if not a:
            return
        used = AS.asset_usages(self.folder, a.rel)
        if used:
            if QMessageBox.question(self, "Remove asset",
                                    f"{a.rel} is used by {', '.join(sorted({u[0] for u in used}))}.\n"
                                    "Remove it anyway?") != QMessageBox.StandardButton.Yes:
                return
        elif QMessageBox.question(self, "Remove asset", f"Delete {a.rel}?") != QMessageBox.StandardButton.Yes:
            return
        AS.remove_asset(self.folder, a.rel, force=True)
        self.refresh()

    def _insert(self):
        a = self._current()
        if a:
            self.selected_rel = a.rel
            self.accept()


def open_asset_manager(parent, project_folder, kind: str | None = None) -> str | None:
    """Show the asset manager; returns the asset chosen with Insert (or None)."""
    d = AssetManagerDialog(parent, project_folder, kind)
    return d.selected_rel if d.exec() == QDialog.DialogCode.Accepted else None


# ============================================================================================ fonts
class _Worker(QObject):
    done = pyqtSignal(object)
    failed = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn(self.progress.emit))
        except Exception as e:  # noqa: BLE001 - reported in the dialog
            self.failed.emit(str(e))


def _run_in_thread(owner, fn, on_done, on_fail, on_progress=None):
    th = QThread(owner)
    w = _Worker(fn)
    w.moveToThread(th)
    th.started.connect(w.run)
    w.done.connect(on_done)
    w.failed.connect(on_fail)
    if on_progress:
        w.progress.connect(on_progress)
    for sig in (w.done, w.failed):
        sig.connect(th.quit)
    th.finished.connect(w.deleteLater)
    owner._threads = getattr(owner, "_threads", []) + [(th, w)]
    th.start()
    return th


class FontPickerDialog(QDialog):
    """Pick a Google font. ``entry`` holds the screen fonts entry after accept:
    ``{"family", "source": "google"}`` or the bundled ``{"family", "source": "asset", "files", "license"}``."""

    SAMPLE = "The quick brown fox jumps over the lazy dog  0123456789\nأبجد هوز حطي كلمن"

    def __init__(self, parent, project_folder=None, current: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Google Fonts")
        self.folder = Path(project_folder) if project_folder else None
        self.entry: dict | None = None
        self.resize(760, 520)
        self.fams = FN.catalog(offline=True)
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search fonts")
        self.search.textChanged.connect(self.refresh)
        self.cat = QComboBox()
        self.cat.addItem("All categories", None)
        for c in FN.CATEGORIES:
            self.cat.addItem(c, c)
        self.cat.currentIndexChanged.connect(self.refresh)
        self.arabic = QCheckBox("Arabic support")
        self.arabic.toggled.connect(self.refresh)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._select)
        b_refresh = QPushButton("Update list from Google Fonts")
        b_refresh.clicked.connect(self._update_catalog)
        for w in (self.search, self.cat, self.arabic):
            left.addWidget(w)
        left.addWidget(self.list, 1)
        left.addWidget(b_refresh)
        lay.addLayout(left, 2)
        right = QVBoxLayout()
        self.title = QLabel()
        f = self.title.font()
        f.setPointSize(f.pointSize() + 4)
        f.setBold(True)
        self.title.setFont(f)
        self.preview = QLabel(self.SAMPLE)
        self.preview.setWordWrap(True)
        self.preview.setMinimumHeight(140)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.preview.setStyleSheet("QLabel { background: white; color: #222; padding: 12px; border-radius: 8px; }")
        right.addWidget(self.title)
        right.addWidget(self.preview)
        wbox = QGroupBox("Weights")
        self.wlay = QHBoxLayout(wbox)
        self.weight_checks: dict[int, QCheckBox] = {}
        right.addWidget(wbox)
        self.italic = QCheckBox("Include italics")
        right.addWidget(self.italic)
        self.bundle = QCheckBox("Bundle the font files in the project (works offline)")
        self.bundle.setChecked(True)
        self.bundle.setEnabled(self.folder is not None)
        if self.folder is None:
            self.bundle.setChecked(False)
        right.addWidget(self.bundle)
        lic = QLabel("Google Fonts are open source (mostly SIL Open Font License 1.1); the licence file is "
                     "copied next to bundled fonts.")
        lic.setWordWrap(True)
        lic.setStyleSheet("color: gray;")
        right.addWidget(lic)
        self.status = QLabel()
        right.addWidget(self.status)
        right.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        self.ok = bb.button(QDialogButtonBox.StandardButton.Ok)
        right.addWidget(bb)
        lay.addLayout(right, 3)
        self.refresh()
        if current:
            self.search.setText(current)

    def refresh(self):
        self.list.clear()
        sub = "arabic" if self.arabic.isChecked() else None
        res = FN.search(self.search.text(), self.fams, self.cat.currentData(), sub)
        if sub and not res:      # built-in list has no subsets: fall back to names
            res = [f for f in FN.search(self.search.text(), self.fams, self.cat.currentData())
                   if any(k in f.family for k in ("Arabic", "Cairo", "Tajawal", "Almarai", "Amiri", "Changa",
                                                  "Messiri", "Readex"))]
        cached = set(FN.cached_families())
        for f in res:
            it = QListWidgetItem(f.family + ("  ✓" if f.family in cached else ""))
            it.setData(Qt.ItemDataRole.UserRole, f)
            it.setToolTip(f"{f.category} - {len(f.weights)} weight(s)")
            self.list.addItem(it)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _fam(self) -> FN.FontFamily | None:
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def _select(self, *_):
        f = self._fam()
        self.ok.setEnabled(f is not None)
        while self.wlay.count():
            w = self.wlay.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.weight_checks = {}
        if f is None:
            return
        self.title.setText(f.family)
        for w in f.weights:
            c = QCheckBox(str(w))
            c.setToolTip(FN.WEIGHT_NAMES.get(w, ""))
            c.setChecked(w in (400, 700) or len(f.weights) == 1)
            self.wlay.addWidget(c)
            self.weight_checks[w] = c
        self.italic.setEnabled(f.has_italic)
        self._preview_font(f.family)

    def _preview_font(self, family: str):
        folder = FN.cache_root() / FN.repo_dir(family)
        qf = QFont("Segoe UI", 15)
        for p in sorted(folder.glob("*.ttf")) if folder.is_dir() else []:
            fid = QFontDatabase.addApplicationFont(str(p))
            fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
            if fams:
                qf = QFont(fams[0], 15)
                break
        self.preview.setFont(qf)
        self.status.setText("" if folder.is_dir() else "Preview uses a system font until the font is downloaded.")

    def _update_catalog(self):
        self.status.setText("Downloading the font list...")

        def done(fams):
            self.fams = fams
            self.status.setText(f"{len(fams)} families")
            self.refresh()
        _run_in_thread(self, lambda _p: FN.catalog(refresh=True), done, self.status.setText)

    def _accept(self):
        f = self._fam()
        if f is None:
            return
        weights = [w for w, c in self.weight_checks.items() if c.isChecked()] or [400]
        if not self.bundle.isChecked():
            self.entry = {"family": f.family, "source": "google"}
            self.accept()
            return
        self.ok.setEnabled(False)
        italic = self.italic.isChecked() and self.italic.isEnabled()

        def done(entry):
            self.entry = entry
            self.accept()

        def fail(msg):
            self.ok.setEnabled(True)
            self.status.setText(msg)
        _run_in_thread(self, lambda prog: FN.add_to_project(self.folder, f.family, weights, italic, progress=prog),
                       done, fail, self.status.setText)


def pick_font(parent, project_folder=None, current: str | None = None) -> dict | None:
    d = FontPickerDialog(parent, project_folder, current)
    return d.entry if d.exec() == QDialog.DialogCode.Accepted else None


# ============================================================================================ theme
def _approx_scheme(seed: str, dark: bool) -> dict[str, QColor]:
    """A rough Material-3-like palette from the seed (preview only; Flutter computes the real one)."""
    c = QColor(f"#{seed[3:]}" if seed.startswith("#") and len(seed) == 9 else seed)
    h, s, _l, _a = c.getHslF()
    h = max(h, 0.0)

    def hsl(sat, light):
        return QColor.fromHslF(h, min(1.0, s * sat), light)
    if dark:
        return {"primary": hsl(0.9, 0.78), "onPrimary": hsl(0.9, 0.2), "surface": hsl(0.15, 0.08),
                "onSurface": hsl(0.1, 0.9), "container": hsl(0.25, 0.16), "outline": hsl(0.15, 0.4)}
    return {"primary": hsl(0.9, 0.42), "onPrimary": QColor("white"), "surface": hsl(0.2, 0.985),
            "onSurface": hsl(0.15, 0.12), "container": hsl(0.35, 0.93), "outline": hsl(0.15, 0.72)}


class ThemePreview(QWidget):
    """Paints a phone-sized mock screen (app bar, card, text field, buttons) for a theme spec."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = TH.new_theme()
        self.dark = False
        self.setMinimumSize(250, 440)

    def set_spec(self, spec: dict, dark: bool):
        self.spec, self.dark = spec, dark
        self.update()

    def paintEvent(self, _e):
        t = self.spec
        sc = _approx_scheme(t.get("seedColor", "#FF5B6CF9"), self.dark)
        over = (t.get("colors") or {}).get("dark" if self.dark else "light") or {}
        if over.get("primary"):
            sc["primary"] = QColor("#" + over["primary"][3:])
        bg = (t.get("background") or {}).get("dark" if self.dark else "light")
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = min(self.width() - 10, 240)
        h = min(self.height() - 10, 430)
        x0, y0 = (self.width() - w) / 2, (self.height() - h) / 2
        p.setPen(QColor("#222"))
        p.setBrush(QColor("#" + bg[3:]) if bg else sc["surface"])
        p.drawRoundedRect(QRectF(x0, y0, w, h), 22, 22)
        fam = (t.get("font") or {}).get("family") or "Segoe UI"
        f = QFont(fam, 11)
        f.setBold(True)
        p.setFont(f)
        p.setPen(sc["onSurface"])
        bar = t.get("appBar") or {}
        p.drawText(QRectF(x0, y0 + 14, w, 30),
                   Qt.AlignmentFlag.AlignCenter if bar.get("centerTitle", True) else
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "   Title")
        # card
        cr = float((t.get("cards") or {}).get("radius", 12))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(sc["container"])
        p.drawRoundedRect(QRectF(x0 + 16, y0 + 56, w - 32, 110), cr, cr)
        p.setPen(sc["onSurface"])
        p.setFont(QFont(fam, 13, QFont.Weight.Bold))
        p.drawText(QRectF(x0 + 30, y0 + 70, w - 60, 26), Qt.AlignmentFlag.AlignLeft, "Headline")
        p.setFont(QFont(fam, 9))
        p.drawText(QRectF(x0 + 30, y0 + 100, w - 60, 50), Qt.TextFlag.TextWordWrap,
                   "Body text uses the theme font and colours.")
        # input
        inp = t.get("inputs") or {}
        ir = float(inp.get("radius", 12))
        r = QRectF(x0 + 16, y0 + 186, w - 32, 44)
        if inp.get("style") == "filled":
            p.setPen(Qt.PenStyle.NoPen)
            fc = inp.get("fillColor")
            p.setBrush(QColor("#" + fc[3:]) if fc else sc["container"])
            p.drawRoundedRect(r, ir, ir)
        elif inp.get("style") == "underline":
            p.setPen(sc["outline"])
            p.drawLine(r.bottomLeft(), r.bottomRight())
        else:
            p.setPen(sc["outline"])
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r, ir, ir)
        p.setPen(sc["outline"])
        p.drawText(r.adjusted(14, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, "Email")
        # buttons
        b = t.get("buttons") or {}
        br, bh = float(b.get("radius", 20)), float(b.get("height", 48))
        r = QRectF(x0 + 16, y0 + 250, w - 32, bh)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(sc["primary"])
        p.drawRoundedRect(r, min(br, bh / 2), min(br, bh / 2))
        p.setPen(sc["onPrimary"])
        p.setFont(QFont(fam, 10, QFont.Weight.DemiBold))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, "Continue")
        r = QRectF(x0 + 16, y0 + 262 + bh, w - 32, bh)
        p.setPen(sc["outline"])
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, min(br, bh / 2), min(br, bh / 2))
        p.setPen(sc["primary"])
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, "Cancel")
        p.end()


class ThemeEditorDialog(QDialog):
    """Edits screens/app.ftheme.json; Save writes it and regenerates lib/theme/app_theme.dart."""

    def __init__(self, parent, project_folder):
        super().__init__(parent)
        self.setWindowTitle("App Theme")
        self.folder = Path(project_folder)
        self.spec = TH.load(self.folder) or TH.new_theme()
        self.resize(760, 560)
        lay = QHBoxLayout(self)
        form_w = QWidget()
        form = QFormLayout(form_w)
        self.preset = QComboBox()
        self.preset.addItem("(choose a preset)", None)
        for name in TH.PRESETS:
            self.preset.addItem(name, name)
        self.preset.currentIndexChanged.connect(self._preset)
        form.addRow("Preset", self.preset)
        self.seed = QPushButton()
        self.seed.clicked.connect(self._pick_seed)
        form.addRow("Seed colour", self.seed)
        self.variant = QComboBox()
        self.variant.addItems(TH.VARIANTS)
        form.addRow("Scheme variant", self.variant)
        self.mode = QComboBox()
        self.mode.addItems(["system", "light", "dark"])
        form.addRow("Theme mode", self.mode)
        self.font = QPushButton()
        self.font.clicked.connect(lambda: self._pick_font("family"))
        form.addRow("Text font", self.font)
        self.hfont = QPushButton()
        self.hfont.clicked.connect(lambda: self._pick_font("headings"))
        form.addRow("Headings font", self.hfont)
        self.hweight = QComboBox()
        self.hweight.addItem("(default)", None)
        for w in ("w500", "w600", "w700", "w800", "w900"):
            self.hweight.addItem(w, f"FontWeight.{w}")
        form.addRow("Headings weight", self.hweight)
        self.b_radius = self._spin(0, 40)
        self.b_height = self._spin(32, 72)
        self.b_elev = self._dspin(0, 12)
        form.addRow("Button radius", self.b_radius)
        form.addRow("Button height", self.b_height)
        form.addRow("Button elevation", self.b_elev)
        self.i_style = QComboBox()
        self.i_style.addItems(TH.INPUT_STYLES)
        self.i_radius = self._spin(0, 40)
        form.addRow("Input style", self.i_style)
        form.addRow("Input radius", self.i_radius)
        self.c_radius = self._spin(0, 40)
        self.c_elev = self._dspin(0, 12)
        form.addRow("Card radius", self.c_radius)
        form.addRow("Card elevation", self.c_elev)
        self.center = QCheckBox("Centre app bar titles")
        form.addRow("", self.center)
        self.dark_prev = QCheckBox("Preview dark")
        form.addRow("", self.dark_prev)
        lay.addWidget(form_w, 3)
        right = QVBoxLayout()
        self.preview = ThemePreview()
        right.addWidget(self.preview, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        right.addWidget(bb)
        lay.addLayout(right, 2)
        self._load_ui()
        for w in (self.variant, self.mode, self.hweight, self.i_style):
            w.currentIndexChanged.connect(self._changed)
        for w in (self.b_radius, self.b_height, self.b_elev, self.i_radius, self.c_radius, self.c_elev):
            w.valueChanged.connect(self._changed)
        self.center.toggled.connect(self._changed)
        self.dark_prev.toggled.connect(self._changed)
        self._changed()

    @staticmethod
    def _spin(a, b):
        s = QSpinBox()
        s.setRange(a, b)
        return s

    @staticmethod
    def _dspin(a, b):
        s = QDoubleSpinBox()
        s.setRange(a, b)
        s.setSingleStep(0.5)
        return s

    def _load_ui(self):
        t = TH.normalize(self.spec)
        self._loading = True
        self._seed = t["seedColor"]
        self.seed.setText(self._seed)
        self.seed.setStyleSheet(f"background: #{self._seed[3:]}; color: white;")
        self.variant.setCurrentText(t["variant"])
        self.mode.setCurrentText(t["mode"])
        f = t.get("font") or {}
        self._font = {"family": f.get("family"), "source": f.get("source", "google"),
                      "headings": f.get("headings"), "headingsSource": f.get("headingsSource", "google")}
        self.font.setText(f.get("family") or "(default)")
        self.hfont.setText(f.get("headings") or "(same as text)")
        self.hweight.setCurrentIndex(max(0, self.hweight.findData(f.get("headingWeight"))))
        b, i, c = t["buttons"], t["inputs"], t["cards"]
        self.b_radius.setValue(int(b.get("radius", 14)))
        self.b_height.setValue(int(b.get("height", 48)))
        self.b_elev.setValue(float(b.get("elevation", 0)))
        self.i_style.setCurrentText(i.get("style", "outline"))
        self.i_radius.setValue(int(i.get("radius", 12)))
        self.c_radius.setValue(int(c.get("radius", 12)))
        self.c_elev.setValue(float(c.get("elevation", 1)))
        self.center.setChecked(bool(t["appBar"].get("centerTitle", True)))
        self._loading = False

    def current_spec(self) -> dict:
        t = copy.deepcopy(TH.normalize(self.spec))
        t["seedColor"] = self._seed
        t["variant"] = self.variant.currentText()
        t["mode"] = self.mode.currentText()
        font = {k: v for k, v in self._font.items() if v}
        if not font.get("family"):
            font.pop("source", None)
        if not font.get("headings"):
            font.pop("headingsSource", None)
        if self.hweight.currentData():
            font["headingWeight"] = self.hweight.currentData()
        t["font"] = font
        t["buttons"].update(radius=self.b_radius.value(), height=self.b_height.value(),
                            elevation=self.b_elev.value())
        t["inputs"].update(style=self.i_style.currentText(), radius=self.i_radius.value())
        t["cards"].update(radius=self.c_radius.value(), elevation=self.c_elev.value())
        t["appBar"]["centerTitle"] = self.center.isChecked()
        return TH.normalize(t)

    def _changed(self, *_):
        if getattr(self, "_loading", False):
            return
        self.preview.set_spec(self.current_spec(), self.dark_prev.isChecked())

    def _preset(self, _i):
        name = self.preset.currentData()
        if name:
            self.spec = TH.apply_preset(self.current_spec(), name)
            self._load_ui()
            self._changed()

    def _pick_seed(self):
        c = QColorDialog.getColor(QColor("#" + self._seed[3:]), self, "Seed colour")
        if c.isValid():
            self._seed = "#FF" + c.name()[1:].upper()
            self.seed.setText(self._seed)
            self.seed.setStyleSheet(f"background: {c.name()}; color: white;")
            self._changed()

    def _pick_font(self, which: str):
        e = pick_font(self, self.folder, self._font.get(which))
        if not e:
            return
        self._font[which] = e["family"]
        self._font["source" if which == "family" else "headingsSource"] = e["source"]
        (self.font if which == "family" else self.hfont).setText(e["family"])
        self._changed()

    def _save(self):
        try:
            TH.save(self.folder, self.current_spec())
            TH.write_project_theme(self.folder)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "App Theme", str(e))
            return
        self.accept()


def edit_theme(parent, project_folder) -> bool:
    """Show the theme editor; True when the theme was saved."""
    return ThemeEditorDialog(parent, project_folder).exec() == QDialog.DialogCode.Accepted
