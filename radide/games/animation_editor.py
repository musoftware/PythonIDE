"""Sprite sheet + animation editor: cut a sheet image into frames, build named animations
(frames, fps, loop) and preview them playing."""
from __future__ import annotations

import copy
import time
from pathlib import Path

from PyQt6.QtCore import QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox,
                             QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QPushButton, QScrollArea, QSpinBox, QSplitter, QVBoxLayout, QWidget)

from .. import theme
from .model import animation_frame, frame_rect, sheet_grid
from .tiles import IMAGE_FILTER


class FrameGrid(QWidget):
    """The sheet image cut into numbered frames.  Click adds a frame to the current animation,
    right-click removes it."""
    frameClicked = pyqtSignal(int, bool)          # index, add (False = remove)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pm: QPixmap | None = None
        self.fw = self.fh = 32
        self.marked: list[int] = []
        self.zoom = 2

    def set_sheet(self, pm, fw: int, fh: int) -> None:
        self.pm, self.fw, self.fh = pm, max(1, fw), max(1, fh)
        self.zoom = 3 if max(self.fw, self.fh) <= 24 else (2 if max(self.fw, self.fh) <= 64 else 1)
        self.adjustSize()
        self.update()

    def grid(self) -> tuple[int, int]:
        if self.pm is None:
            return 0, 0
        return sheet_grid({"frame_w": self.fw, "frame_h": self.fh}, self.pm.width(), self.pm.height())

    def sizeHint(self) -> QSize:
        c, r = self.grid()
        return QSize(max(200, c * self.fw * self.zoom + 1), max(120, r * self.fh * self.zoom + 1))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def index_at(self, pos) -> int:
        c, r = self.grid()
        col, row = int(pos.x() // (self.fw * self.zoom)), int(pos.y() // (self.fh * self.zoom))
        return row * c + col if 0 <= col < c and 0 <= row < r else -1

    def mousePressEvent(self, e) -> None:
        i = self.index_at(e.position())
        if i >= 0:
            self.frameClicked.emit(i, e.button() != Qt.MouseButton.RightButton)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.color("stage")))
        if self.pm is None:
            p.setPen(QColor(theme.color("muted")))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Choose the sprite sheet image")
            return
        c, r = self.grid()
        fw, fh, z = self.fw, self.fh, self.zoom
        p.drawPixmap(QRectF(0, 0, c * fw * z, r * fh * z), self.pm, QRectF(0, 0, c * fw, r * fh))
        p.setPen(QPen(QColor(255, 255, 255, 110), 1))
        for i in range(c + 1):
            p.drawLine(i * fw * z, 0, i * fw * z, r * fh * z)
        for j in range(r + 1):
            p.drawLine(0, j * fh * z, c * fw * z, j * fh * z)
        f = QFont("Segoe UI")
        f.setPixelSize(10)
        p.setFont(f)
        acc = QColor(theme.color("accent"))
        for idx in range(c * r):
            x, y = (idx % c) * fw * z, (idx // c) * fh * z
            p.setPen(QColor(255, 255, 255))
            p.drawText(int(x + 3), int(y + 12), str(idx))
            if idx in self.marked:
                p.setPen(QPen(acc, 3))
                p.drawRect(QRectF(x + 1.5, y + 1.5, fw * z - 3, fh * z - 3))
                order = ",".join(str(k + 1) for k, v in enumerate(self.marked) if v == idx)
                p.fillRect(QRectF(x + fw * z - 6 - 7 * len(order), y + fh * z - 15, 6 + 7 * len(order), 14), acc)
                p.setPen(QColor(theme.color("accent_text")))
                p.drawText(QRectF(x, y + fh * z - 15, fw * z - 3, 14),
                           Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, order)


class AnimPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pm = None
        self.src = None
        self.setMinimumSize(128, 128)

    def show_frame(self, pm, src) -> None:
        self.pm, self.src = pm, src
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.color("stage")))
        if self.pm is None or self.src is None:
            return
        w, h = self.src.width(), self.src.height()
        k = max(1, int(min((self.width() - 8) / max(1, w), (self.height() - 8) / max(1, h))))
        tgt = QRectF((self.width() - w * k) / 2, (self.height() - h * k) / 2, w * k, h * k)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        p.drawPixmap(tgt, self.pm, self.src)


class SpriteSheetDialog(QDialog):
    """Edit one sprite sheet asset: {"image", "frame_w", "frame_h", "animations": {...}}."""

    def __init__(self, sheet: dict | None = None, sheet_id: str = "", resolve=None, base_dir: str = "",
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sprite Sheet and Animations")
        self.resize(900, 600)
        self.sheet = copy.deepcopy(sheet or {"image": "", "frame_w": 32, "frame_h": 32, "animations": {}})
        self.sheet.setdefault("animations", {})
        self._resolve = resolve or (lambda p: QPixmap(p) if p else None)
        self.base_dir = base_dir
        self.pm: QPixmap | None = None
        self._t0 = 0.0
        self.preview_index = -1
        self._loading = False

        lay = QVBoxLayout(self)
        form = QFormLayout()
        row = QHBoxLayout()
        self.image = QLineEdit(self.sheet.get("image", ""))
        b = QPushButton("Browse...")
        b.clicked.connect(self._browse)
        row.addWidget(self.image, 1)
        row.addWidget(b)
        form.addRow("Image:", row)
        self.sid = QLineEdit(sheet_id)
        self.sid.setPlaceholderText("from the file name")
        form.addRow("Name (id):", self.sid)
        self.fw, self.fh = QSpinBox(), QSpinBox()
        for s, k in ((self.fw, "frame_w"), (self.fh, "frame_h")):
            s.setRange(1, 2048)
            s.setSuffix(" px")
            s.setValue(int(self.sheet.get(k) or 32))
            s.valueChanged.connect(self._sheet_changed)
        sz = QHBoxLayout()
        sz.addWidget(self.fw)
        sz.addWidget(QLabel("x"))
        sz.addWidget(self.fh)
        self.grid_info = theme.role(QLabel(""), "muted")
        sz.addWidget(self.grid_info)
        sz.addStretch(1)
        form.addRow("Frame size:", sz)
        lay.addLayout(form)

        split = QSplitter()
        self.frames_view = FrameGrid()
        self.frames_view.frameClicked.connect(self._frame_clicked)
        sa = QScrollArea()
        sa.setWidget(self.frames_view)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(theme.role(QLabel("Click frames to add them to the animation, right-click removes."), "muted"))
        ll.addWidget(sa, 1)
        split.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        g = QGroupBox("Animations")
        gl = QVBoxLayout(g)
        self.anims = QListWidget()
        self.anims.currentItemChanged.connect(self._anim_selected)
        self.anims.itemDoubleClicked.connect(lambda _i: self._rename())
        gl.addWidget(self.anims)
        br = QHBoxLayout()
        for text, slot in (("Add...", self._add), ("Rename...", self._rename), ("Remove", self._remove)):
            bt = QPushButton(text)
            bt.clicked.connect(slot)
            br.addWidget(bt)
        gl.addLayout(br)
        af = QFormLayout()
        self.frames_edit = QLineEdit()
        self.frames_edit.setPlaceholderText("0, 1, 2, 3")
        self.frames_edit.editingFinished.connect(self._frames_typed)
        af.addRow("Frames:", self.frames_edit)
        self.fps = QSpinBox()
        self.fps.setRange(1, 120)
        self.fps.setSuffix(" fps")
        self.fps.valueChanged.connect(self._anim_props)
        af.addRow("Speed:", self.fps)
        self.loop = QCheckBox("Loop")
        self.loop.toggled.connect(self._anim_props)
        af.addRow("", self.loop)
        clear = QPushButton("Clear frames")
        clear.clicked.connect(self._clear_frames)
        af.addRow("", clear)
        gl.addLayout(af)
        rl.addWidget(g)
        pg = QGroupBox("Preview")
        pl = QVBoxLayout(pg)
        self.preview = AnimPreview()
        pl.addWidget(self.preview, 1)
        self.play_btn = QPushButton("Play")
        self.play_btn.setCheckable(True)
        self.play_btn.toggled.connect(self.play)
        pl.addWidget(self.play_btn)
        rl.addWidget(pg, 1)
        split.addWidget(right)
        split.setSizes([560, 320])
        lay.addWidget(split, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.image.editingFinished.connect(self._load_image)
        self._load_image()
        self._fill_anims()

    # ---------------------------------------------------------------- data
    def current_name(self) -> str | None:
        it = self.anims.currentItem()
        return it.text() if it is not None else None

    def current_anim(self) -> dict | None:
        n = self.current_name()
        return self.sheet["animations"].get(n) if n else None

    def _browse(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Sprite sheet image", self.base_dir, IMAGE_FILTER)
        if f:
            self.image.setText(f)
            self._load_image()

    def _load_image(self) -> None:
        self.sheet["image"] = self.image.text().strip()
        pm = self._resolve(self.sheet["image"]) if self.sheet["image"] else None
        self.pm = pm if pm is not None and not pm.isNull() else None
        if self.pm is not None and not self.sheet["animations"] and self.fw.value() == 32 == self.fh.value():
            # a guess for a strip: square frames of the image height
            if self.pm.width() > self.pm.height() and self.pm.width() % self.pm.height() == 0:
                self.fw.setValue(self.pm.height())
                self.fh.setValue(self.pm.height())
        self._sheet_changed()

    def _sheet_changed(self) -> None:
        self.sheet["frame_w"], self.sheet["frame_h"] = self.fw.value(), self.fh.value()
        self.frames_view.set_sheet(self.pm, self.fw.value(), self.fh.value())
        c, r = self.frames_view.grid()
        self.grid_info.setText(f"  {c} x {r} = {c * r} frames" if self.pm is not None else "")
        self._show_marks()

    def _fill_anims(self, select: str | None = None) -> None:
        self.anims.blockSignals(True)
        self.anims.clear()
        for n in self.sheet["animations"]:
            self.anims.addItem(QListWidgetItem(n))
        self.anims.blockSignals(False)
        names = list(self.sheet["animations"])
        if names:
            self.anims.setCurrentRow(names.index(select) if select in names else 0)
        else:
            self._anim_selected()

    def _anim_selected(self, *_a) -> None:
        a = self.current_anim()
        self._loading = True
        self.frames_edit.setEnabled(a is not None)
        self.fps.setEnabled(a is not None)
        self.loop.setEnabled(a is not None)
        self.frames_edit.setText(", ".join(str(f) for f in (a or {}).get("frames", [])))
        self.fps.setValue(int((a or {}).get("fps") or 8))
        self.loop.setChecked(bool((a or {}).get("loop", True)))
        self._loading = False
        self._t0 = time.monotonic()
        self._show_marks()
        self._tick()

    def _show_marks(self) -> None:
        a = self.current_anim()
        self.frames_view.marked = list((a or {}).get("frames", []))
        self.frames_view.update()

    def add_animation(self, name: str, frames=None, fps: int = 8, loop: bool = True) -> None:
        self.sheet["animations"][name] = {"frames": list(frames or []), "fps": fps, "loop": loop}
        self._fill_anims(name)

    def _add(self) -> None:
        base = "idle" if not self.sheet["animations"] else "walk" if "walk" not in self.sheet["animations"] else "anim"
        n, ok = QInputDialog.getText(self, "New animation", "Name:", text=base)
        if ok and n.strip() and n.strip() not in self.sheet["animations"]:
            self.add_animation(n.strip())

    def _rename(self) -> None:
        old = self.current_name()
        if not old:
            return
        n, ok = QInputDialog.getText(self, "Rename animation", "Name:", text=old)
        n = n.strip()
        if ok and n and n != old and n not in self.sheet["animations"]:
            self.sheet["animations"] = {(n if k == old else k): v for k, v in self.sheet["animations"].items()}
            self._fill_anims(n)

    def _remove(self) -> None:
        n = self.current_name()
        if n:
            self.sheet["animations"].pop(n, None)
            self._fill_anims()

    def _frame_clicked(self, idx: int, add: bool) -> None:
        a = self.current_anim()
        if a is None:
            self.add_animation("idle" if not self.sheet["animations"] else f"anim{len(self.sheet['animations']) + 1}")
            a = self.current_anim()
        if add:
            a["frames"].append(idx)
        elif idx in a["frames"]:
            a["frames"].reverse()
            a["frames"].remove(idx)
            a["frames"].reverse()
        self._anim_selected()

    def _frames_typed(self) -> None:
        a = self.current_anim()
        if a is None:
            return
        a["frames"] = [int(x) for x in self.frames_edit.text().replace(";", ",").replace(" ", ",").split(",")
                       if x.strip().lstrip("-").isdigit() and int(x) >= 0]
        self._anim_selected()

    def _clear_frames(self) -> None:
        a = self.current_anim()
        if a is not None:
            a["frames"] = []
            self._anim_selected()

    def _anim_props(self, *_a) -> None:
        a = self.current_anim()
        if a is None or self._loading:
            return
        a["fps"], a["loop"] = self.fps.value(), self.loop.isChecked()
        if self.timer.isActive():
            self.timer.start(max(10, int(1000 / self.fps.value())))

    # ---------------------------------------------------------------- preview
    def play(self, on: bool = True) -> None:
        self.play_btn.blockSignals(True)
        self.play_btn.setChecked(on)
        self.play_btn.setText("Stop" if on else "Play")
        self.play_btn.blockSignals(False)
        self._t0 = time.monotonic()
        if on:
            self.timer.start(max(10, int(1000 / max(1, self.fps.value()))))
        else:
            self.timer.stop()
        self._tick()

    def frame_at(self, t: float) -> int:
        """The frame the preview shows t seconds after Play (uses the shared runtime rule)."""
        a = self.current_anim()
        return animation_frame(a, t) if a and a.get("frames") else -1

    def show_time(self, t: float) -> int:
        idx = self.frame_at(t)
        self.preview_index = idx
        if idx >= 0 and self.pm is not None:
            self.preview.show_frame(self.pm, QRectF(*frame_rect(self.sheet, idx, self.pm.width())))
        else:
            self.preview.show_frame(None, None)
        return idx

    def _tick(self) -> None:
        self.show_time(time.monotonic() - self._t0 if self.timer.isActive() else 0.0)

    def _ok(self) -> None:
        self.timer.stop()
        self.sheet["image"] = self.image.text().strip()
        self.accept()

    def result_sheet(self) -> tuple[str, dict]:
        sid = self.sid.text().strip() or Path(self.sheet.get("image") or "sheet").stem
        return sid, self.sheet

    def done(self, r) -> None:
        self.timer.stop()
        super().done(r)
