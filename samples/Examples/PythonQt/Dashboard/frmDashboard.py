# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""System Dashboard - a Timer-driven PySide6 dashboard with tabs, progress bars and custom painting.

Shows: a Timer control (QTimer) refreshing real readings (CPU from GetSystemTimes, memory from
GlobalMemoryStatusEx, disk from shutil.disk_usage - simulated values on other systems), ProgressBars,
a TabControl with three pages, two PictureBoxes painted with QPainter through an event filter
(arc gauges and a history chart), a to-do list (ListBox) and Pause / Fast refresh controls.
"""
import ctypes
import os
import random
import shutil
import sys
import time
from collections import deque

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: F401

from frmDashboard_designer import frmDashboardDesigner, EventArgs  # noqa: F401

HISTORY = 120


# ---------------------------------------------------------------------------- readings
class _FILETIME(ctypes.Structure):
    _fields_ = [("lo", ctypes.c_uint32), ("hi", ctypes.c_uint32)]


class _MEMSTAT(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_uint32), ("dwMemoryLoad", ctypes.c_uint32)] + \
               [(n, ctypes.c_uint64) for n in ("total", "avail", "ptotal", "pavail", "vtotal", "vavail", "x")]


class Readings:
    """CPU / memory / disk usage in percent (Windows APIs; a gentle simulation elsewhere)."""

    def __init__(self):
        self.win = os.name == "nt"
        self.prev = self._times() if self.win else None
        self.sim = 30.0

    def _times(self):
        idle, kern, user = _FILETIME(), _FILETIME(), _FILETIME()
        ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user))
        f = lambda t: (t.hi << 32) | t.lo                     # noqa: E731
        return f(idle), f(kern), f(user)

    def cpu(self) -> float:
        if not self.win:
            self.sim = min(95, max(3, self.sim + random.uniform(-8, 8)))
            return self.sim
        now = self._times()
        idle, kern, user = (a - b for a, b in zip(now, self.prev))
        self.prev = now
        total = kern + user                                    # kernel time includes idle time
        return 0.0 if total <= 0 else max(0.0, min(100.0, 100.0 * (total - idle) / total))

    def memory(self) -> float:
        if not self.win:
            return 55.0
        m = _MEMSTAT()
        m.dwLength = ctypes.sizeof(_MEMSTAT)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return float(m.dwMemoryLoad)

    @staticmethod
    def disk() -> float:
        u = shutil.disk_usage(os.path.abspath(os.sep))
        return 100.0 * u.used / u.total


# ---------------------------------------------------------------------------- painting
class _Painter(QObject):
    """Event filter: calls draw(widget, painter) when the PictureBox paints."""

    def __init__(self, widget, draw):
        super().__init__(widget)
        self.draw = draw
        widget.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.Paint:
            p = QPainter(obj)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.draw(obj, p)
            p.end()
            return True
        return False


class frmDashboard(frmDashboardDesigner):
    """Event handlers of the dashboard window."""

    def frmDashboard_Load(self):
        self.started = time.time()
        self.readings = Readings()
        self.values = {"CPU": 0.0, "Memory": 0.0, "Disk": 0.0}
        self.history = {k: deque(maxlen=HISTORY) for k in self.values}
        self.ticks = 0
        _Painter(self.picGauge, self.draw_gauges)
        _Painter(self.picHistory, self.draw_history)
        self.txtTask.returnPressed.connect(self.btnAddTask_Click)
        for t in ("Check the backups", "Update the price list"):
            self.lstTasks.addItem(t)
        self.tmrRefresh_Tick()

    # ------------------------------------------------------------------ timer
    def tmrRefresh_Tick(self):
        self.ticks += 1
        r = self.readings
        self.values = {"CPU": r.cpu(), "Memory": r.memory(), "Disk": r.disk()}
        for k, v in self.values.items():
            self.history[k].append(v)
        for bar, key in ((self.prgCpu, "CPU"), (self.prgMem, "Memory"), (self.prgDisk, "Disk")):
            bar.setValue(int(round(self.values[key])))
            bar.setFormat(f"{self.values[key]:.0f} %")
        self.lblClock.setText(time.strftime("%H:%M:%S"))
        up = int(time.time() - self.started)
        self.lblUptime.setText(f"running {up // 3600:02d}:{up % 3600 // 60:02d}:{up % 60:02d}  -  "
                               f"{self.ticks} refreshes")
        cpu = list(self.history["CPU"])
        self.lblHistory.setText(f"CPU last {len(cpu)} samples: min {min(cpu):.0f} %  max {max(cpu):.0f} %  "
                                f"avg {sum(cpu) / len(cpu):.0f} %")
        self.picGauge.update()
        self.picHistory.update()

    def btnPause_Click(self):
        running = self.tmrRefresh.isActive()
        if running:
            self.tmrRefresh.stop()
        else:
            self.tmrRefresh.start()
        self.btnPause.setText("Resume" if running else "Pause")
        self.sbInfo.setText("Paused" if running else "Running")

    def chkFast_CheckedChanged(self):
        self.tmrRefresh.setInterval(200 if self.chkFast.isChecked() else 500)
        self.sbInfo.setText(f"Refresh every {self.tmrRefresh.interval()} ms")

    # ------------------------------------------------------------------ painting
    def draw_gauges(self, w, p: QPainter):
        p.fillRect(w.rect(), QColor("#FFFFFF"))
        colors = {"CPU": "#1F6FB2", "Memory": "#2A9D8F", "Disk": "#F77F00"}
        size = min(w.height() - 40, (w.width() - 80) // 3)
        for i, (name, value) in enumerate(self.values.items()):
            x = 20 + i * (size + 20) + (w.width() - 3 * size - 80) // 2
            rect = QRectF(x, 10, size, size)
            p.setPen(QPen(QColor("#E5E9F0"), 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect.adjusted(10, 10, -10, -10), 225 * 16, -270 * 16)
            p.setPen(QPen(QColor(colors[name]), 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect.adjusted(10, 10, -10, -10), 225 * 16, int(-270 * 16 * value / 100))
            p.setPen(QColor("#222222"))
            p.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{value:.0f}%")
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(QRectF(x, 10 + size, size, 24), Qt.AlignmentFlag.AlignCenter, name)

    def draw_history(self, w, p: QPainter):
        p.fillRect(w.rect(), QColor("#0F1724"))
        pad, W, H = 34, w.width(), w.height()
        p.setFont(QFont("Segoe UI", 8))
        for pct in range(0, 101, 25):
            y = H - pad - (H - 2 * pad) * pct / 100
            p.setPen(QColor("#24324A"))
            p.drawLine(pad, int(y), W - 10, int(y))
            p.setPen(QColor("#8FA3BF"))
            p.drawText(4, int(y) + 4, f"{pct}%")
        colors = {"CPU": "#4CC9F0", "Memory": "#80ED99", "Disk": "#FFB703"}
        step = (W - pad - 10) / (HISTORY - 1)
        for i, (name, values) in enumerate(self.history.items()):
            if len(values) < 2:
                continue
            path = QPainterPath()
            for j, v in enumerate(values):
                pt = (pad + j * step, H - pad - (H - 2 * pad) * v / 100)
                path.moveTo(*pt) if j == 0 else path.lineTo(*pt)
            p.setPen(QPen(QColor(colors[name]), 2))
            p.drawPath(path)
            p.drawText(pad + 10 + i * 90, 16, f"■ {name}")

    # ------------------------------------------------------------------ tasks
    def btnAddTask_Click(self):
        text = self.txtTask.text().strip()
        if text:
            self.lstTasks.addItem(text)
            self.txtTask.clear()
            self.sbInfo.setText(f"{self.lstTasks.count()} tasks")

    def btnDoneTask_Click(self):
        row = self.lstTasks.currentRow()
        if row >= 0:
            item = self.lstTasks.takeItem(row)
            self.sbInfo.setText(f"Done: {item.text()}")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = frmDashboard()
    form.show()
    sys.exit(app.exec())
