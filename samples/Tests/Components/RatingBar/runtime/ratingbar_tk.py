"""RatingBar - python-tk runtime of the RatingBar component package.

Also used for VB6 forms (vb-basic) and every GUI Bridge language (C#, Java, JavaScript, ...): the IDE draws
those forms with Tk, and ``RatingBar1.Value = 4`` / ``set("rate1", "Value", 4)`` reach these attributes.
"""
import tkinter as tk


class RatingBar(tk.Canvas):
    def __init__(self, master, Value=3, MaxStars=5, ReadOnly=False, StarColor="#FFB400", EmptyColor="#C8CDD5",
                 BackColor="", Enabled=True, **_ignored):
        bg = BackColor
        if not bg:
            try:
                bg = master.cget("bg")
            except (tk.TclError, AttributeError):
                bg = "#f0f0f0"
        super().__init__(master, highlightthickness=0, bd=0, bg=bg or "#f0f0f0")
        self._handlers = {}
        self._max = max(1, min(10, int(MaxStars)))
        self._value = max(0, min(self._max, int(Value)))
        self.ReadOnly = bool(ReadOnly)
        self._on, self._off = StarColor or "#FFB400", EmptyColor or "#C8CDD5"
        self._enabled = bool(Enabled)
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Button-1>", self._click, add="+")

    def rad_bind(self, event, callback):
        self._handlers[event] = callback

    def _raise(self, event):
        fn = self._handlers.get(event)
        if fn is not None:
            fn()

    @property
    def Value(self):
        return self._value

    @Value.setter
    def Value(self, v):
        v = max(0, min(self._max, int(v or 0)))
        if v != self._value:
            self._value = v
            self._draw()
            self._raise("ValueChanged")

    @property
    def MaxStars(self):
        return self._max

    @MaxStars.setter
    def MaxStars(self, n):
        self._max = max(1, min(10, int(n)))
        self._value = min(self._value, self._max)
        self._draw()

    @property
    def StarColor(self):
        return self._on

    @StarColor.setter
    def StarColor(self, c):
        self._on = c
        self._draw()

    @property
    def EmptyColor(self):
        return self._off

    @EmptyColor.setter
    def EmptyColor(self, c):
        self._off = c
        self._draw()

    def Reset(self):
        self.Value = 0

    def SetValue(self, value):
        self.Value = value

    def _size(self):
        w, h = max(1, self.winfo_width()), max(1, self.winfo_height())
        return max(6, min(h - 2, w / self._max - 2)), h

    def _draw(self):
        self.delete("all")
        s, h = self._size()
        for i in range(self._max):
            on = i < self._value
            color = (self._on if on else self._off) if self._enabled else ("#B0B0B0" if on else "#E0E0E0")
            self.create_text(i * (s + 2) + s / 2 + 1, h / 2, text="★", fill=color,
                             font=("Segoe UI Symbol", -int(s)))

    def _click(self, e):
        if self.ReadOnly or not self._enabled:
            return
        s, _h = self._size()
        i = int(e.x // (s + 2)) + 1
        if 1 <= i <= self._max:
            self.Value = 0 if i == self._value == 1 else i
