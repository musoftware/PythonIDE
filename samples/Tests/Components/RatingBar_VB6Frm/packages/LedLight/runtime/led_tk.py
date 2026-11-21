"""LedLight - python-tk runtime (a Canvas with one circle)."""
import tkinter as tk


class LedLight(tk.Canvas):
    def __init__(self, master, On=False, Color="#FF0000", **kw):
        super().__init__(master, highlightthickness=0, bd=0)
        self._on, self._color = bool(On), Color
        self._cb = {}
        self.bind("<Configure>", lambda e: self._draw())

    def rad_bind(self, event, callback):
        self._cb[event] = callback

    @property
    def On(self):
        return self._on

    @On.setter
    def On(self, v):
        self._on = bool(v)
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        self.create_oval(2, 2, w - 2, h - 2, fill=self._color if self._on else "#404040", outline="#202020")
