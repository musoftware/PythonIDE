# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Paint & Live Chart - mouse drawing and a Timer-driven chart on two TabControl pages.

Paint page: a PictureBox hosts a Tk canvas; MouseDown / MouseMove / MouseUp draw with the pen, or rubber-band a
line, box or oval (RadioButtons).  Color from a ComboBox or the ColorDialog, pen size from a TrackBar,
Edit > Undo Last Stroke, File > Save Drawing (PostScript, via SaveFileDialog).
Live Chart page: a Timer adds a simulated sensor reading every Interval ms (NumericUpDown), the chart is redrawn
with a grid, the min / max / average are shown and a ProgressBar shows the last value.
"""
import math
import random
from collections import deque

import tkinter as tk

from frmPaint_designer import frmPaintDesigner, EventArgs  # noqa: F401

COLORS = {"Black": "#000000", "Red": "#D62828", "Green": "#2A9D8F", "Blue": "#1F6FB2", "Orange": "#F77F00",
          "Purple": "#7B2CBF"}
POINTS = 120                     # samples visible on the chart


class frmPaint(frmPaintDesigner):
    """Event handlers of the Paint & Live Chart window."""

    def frmPaint_Load(self):
        # --- paint: a canvas fills the PictureBox; its mouse events go to the PictureBox handlers
        self.canvas = tk.Canvas(self.picCanvas, bg="#FFFFFF", highlightthickness=0, cursor="pencil")
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.canvas.bind("<ButtonPress-1>", lambda ev: self.picCanvas_MouseDown(EventArgs(ev)))
        self.canvas.bind("<B1-Motion>", lambda ev: self.picCanvas_MouseMove(EventArgs(ev)))
        self.canvas.bind("<ButtonRelease-1>", lambda ev: self.picCanvas_MouseUp(EventArgs(ev)))
        self.color = COLORS["Black"]
        self.cboColor.set("Black")
        self.strokes = []            # one list of canvas item ids per stroke (for Undo)
        self.start = None            # where the mouse went down
        self.preview = None          # rubber-band item while dragging a shape
        # --- chart
        self.chart = tk.Canvas(self.picChart, bg="#10151F", highlightthickness=0)
        self.chart.place(x=0, y=0, relwidth=1, relheight=1)
        self.samples = deque(maxlen=POINTS)
        self.t = 0
        self.level = 50.0
        self.draw_chart()

    # ================================================================== paint
    def tool(self) -> str:
        return {"optPen": "pen", "optLine": "line", "optRect": "rect", "optOval": "oval"}.get(self._radio.get(), "pen")

    def picCanvas_MouseDown(self, e):
        self.start = (e.X, e.Y)
        self.strokes.append([])
        if self.tool() == "pen":                  # a dot, so a single click draws something
            r = max(1, self.trkSize_var.get() // 2)
            self.strokes[-1].append(self.canvas.create_oval(e.X - r, e.Y - r, e.X + r, e.Y + r,
                                                            fill=self.color, outline=""))
        self.sbInfo.config(text=f"{self.tool()} at {e.X}, {e.Y}")

    def picCanvas_MouseMove(self, e):
        if self.start is None:
            return
        size = self.trkSize_var.get()
        x0, y0 = self.start
        if self.tool() == "pen":
            self.strokes[-1].append(self.canvas.create_line(x0, y0, e.X, e.Y, fill=self.color, width=size,
                                                            capstyle="round", smooth=True))
            self.start = (e.X, e.Y)
        else:
            if self.preview is not None:
                self.canvas.delete(self.preview)
            self.preview = self.shape(x0, y0, e.X, e.Y, dash=(4, 2))
        self.sbInfo.config(text=f"{self.tool()} {e.X}, {e.Y}    strokes: {len(self.strokes)}")

    def picCanvas_MouseUp(self, e):
        if self.start is None:
            return
        if self.tool() != "pen":
            if self.preview is not None:
                self.canvas.delete(self.preview)
                self.preview = None
            x0, y0 = self.start
            self.strokes[-1].append(self.shape(x0, y0, e.X, e.Y))
        self.start = None

    def shape(self, x0, y0, x1, y1, dash=None):
        opts = {"width": self.trkSize_var.get(), "dash": dash or ()}
        t = self.tool()
        if t == "line":
            return self.canvas.create_line(x0, y0, x1, y1, fill=self.color, capstyle="round", **opts)
        make = self.canvas.create_rectangle if t == "rect" else self.canvas.create_oval
        return make(x0, y0, x1, y1, outline=self.color, **opts)

    def cboColor_SelectedIndexChanged(self):
        self.color = COLORS.get(self.cboColor_var.get(), "#000000")

    def btnPickColor_Click(self):
        self.dlgColor.Color = self.color
        if self.dlgColor.ShowDialog() == "OK":
            self.color = self.dlgColor.Color
            self.cboColor.set(self.color)

    def trkSize_ValueChanged(self):
        self.sbInfo.config(text=f"Pen size {self.trkSize_var.get()}")

    def mnuEditClear_Click(self):
        self.canvas.delete("all")
        self.strokes.clear()

    def mnuEditUndo_Click(self):
        if self.strokes:
            for item in self.strokes.pop():
                self.canvas.delete(item)

    def mnuFileSave_Click(self):
        if self.dlgSave.ShowDialog() == "OK":
            self.canvas.postscript(file=self.dlgSave.FileName, colormode="color")
            self.sbInfo.config(text=f"Saved {self.dlgSave.FileName}")

    def mnuFileExit_Click(self):
        self.root.destroy()

    # ================================================================== live chart
    def btnStart_Click(self):
        self.tmrChart.Interval = int(self.numInterval_var.get())
        self.tmrChart.Enabled = True
        self.sbInfo.config(text="Chart running")

    def btnStop_Click(self):
        self.tmrChart.Enabled = False
        self.sbInfo.config(text="Chart stopped")

    def numInterval_ValueChanged(self):
        self.tmrChart.Interval = max(50, int(self.numInterval_var.get()))

    def tmrChart_Tick(self):
        self.add_sample(self.next_reading())

    def next_reading(self) -> float:
        """A simulated sensor: a slow sine wave plus a random walk, kept between 0 and 100."""
        self.t += 1
        self.level += random.uniform(-4, 4)
        self.level = min(95.0, max(5.0, self.level))
        return round(min(100.0, max(0.0, self.level + 15 * math.sin(self.t / 9))), 1)

    def add_sample(self, value: float):
        self.samples.append(value)
        self.prgLevel["value"] = value
        vals = list(self.samples)
        self.lblStats.config(text=f"now {value:.1f}   min {min(vals):.1f}   max {max(vals):.1f}   "
                                  f"avg {sum(vals) / len(vals):.1f}   n={len(vals)}")
        self.draw_chart()

    def draw_chart(self):
        c = self.chart
        c.delete("all")
        w = max(c.winfo_width(), 784)
        h = max(c.winfo_height(), 400)
        pad = 30
        for i in range(0, 101, 25):                # grid + labels
            y = h - pad - (h - 2 * pad) * i / 100
            c.create_line(pad, y, w - 10, y, fill="#24324A")
            c.create_text(pad - 6, y, text=str(i), fill="#8FA3BF", anchor="e", font=("Segoe UI", 8))
        if len(self.samples) < 2:
            c.create_text(w / 2, h / 2, text="Press Start", fill="#8FA3BF", font=("Segoe UI", 14))
            return
        step = (w - pad - 10) / (POINTS - 1)
        pts = []
        for i, v in enumerate(self.samples):
            pts += [pad + i * step, h - pad - (h - 2 * pad) * v / 100]
        c.create_polygon(pad, h - pad, *pts, pts[-2], h - pad, fill="#173A5E", outline="")
        c.create_line(*pts, fill="#4CC9F0", width=2, smooth=True)
        c.create_oval(pts[-2] - 4, pts[-1] - 4, pts[-2] + 4, pts[-1] + 4, fill="#F72585", outline="")


if __name__ == "__main__":
    frmPaint().show()
