"""MiniGauge - python-tk runtime (a Canvas bar)."""
import tkinter as tk


class MiniGauge(tk.Canvas):
    def __init__(self, master, Value=40, BackColor="", ForeColor="", Enabled=True, **kw):
        super().__init__(master, highlightthickness=0, bd=0, bg=BackColor or "#E0E0E0")
        self._value = int(Value)
        self._fore = ForeColor or "#2E7D32"
        self._cb = {}
        self.bind("<Configure>", lambda e: self._draw())

    def rad_bind(self, event, callback):
        self._cb[event] = callback

    @property
    def Value(self):
        return self._value

    @Value.setter
    def Value(self, v):
        self._value = max(0, min(100, int(v)))
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        self.create_rectangle(0, 0, w * self._value / 100, h, fill=self._fore, width=0)
