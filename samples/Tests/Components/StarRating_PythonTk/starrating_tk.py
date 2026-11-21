"""StarRating - python-tk runtime of the StarRating component package.

Copied into the project by RAD IDE. The generated form code does::

    self.Rating1 = StarRating(master, Value=3, MaxStars=5, ...)
    self.Rating1.rad_bind("ValueChanged", callback)

Use it from code like any control: ``self.Rating1.Value = 4``, ``self.Rating1.Reset()``.
"""
import math
import tkinter as tk


def _padding(value):
    nums = [int(float(x)) for x in str(value or "0").replace(",", " ").split() if x.strip()] or [0]
    if len(nums) == 1:
        nums = nums * 4
    elif len(nums) == 2:
        nums = nums * 2
    elif len(nums) == 3:
        nums.append(nums[1])
    return nums[:4]


def _darker(color, f=0.75):
    try:
        c = color.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))
    except (ValueError, IndexError):
        return "#606060"


class StarRating(tk.Canvas):
    def __init__(self, master, Value=0, MaxStars=5, ReadOnly=False, StarColor="#FFB400", EmptyColor="#C8CDD5",
                 Shape="Star", Spacing=4, Padding="2, 2, 2, 2", ShowValue=False, BackColor="", ForeColor="",
                 FontName="Segoe UI", FontSize=9, FontBold=False, FontItalic=False, Enabled=True, **_ignored):
        bg = BackColor
        if not bg:
            try:
                bg = master.cget("bg")                 # blend in with the form / container
            except (tk.TclError, AttributeError):
                bg = "#f0f0f0"
        super().__init__(master, highlightthickness=0, bd=0, bg=bg or "#f0f0f0")
        self._handlers = {}
        self._max = max(1, min(10, int(MaxStars)))
        self._value = max(0, min(self._max, int(Value)))
        self.ReadOnly = bool(ReadOnly)
        self._star, self._empty = StarColor or "#FFB400", EmptyColor or "#C8CDD5"
        self._shape, self._spacing, self._padding = Shape, int(Spacing), _padding(Padding)
        self._show_value, self._fore = bool(ShowValue), ForeColor or "#404040"
        self._font = (FontName or "Segoe UI", int(FontSize or 9),
                      " ".join(s for s, on in (("bold", FontBold), ("italic", FontItalic)) if on) or "normal")
        self._enabled = bool(Enabled)
        self.HoverValue = 0
        self._cells = []
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Button-1>", self._click, add="+")
        self.bind("<Motion>", self._motion, add="+")
        self.bind("<Leave>", lambda _e: self._set_hover(0), add="+")

    # ------------------------------------------------------------ events
    def rad_bind(self, event, callback):
        self._handlers[event] = callback

    def _raise(self, event, *args):
        fn = self._handlers.get(event)
        if fn is not None:
            fn(*args)

    # ------------------------------------------------------------ properties
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
        return self._star

    @StarColor.setter
    def StarColor(self, c):
        self._star = c
        self._draw()

    @property
    def Enabled(self):
        return self._enabled

    @Enabled.setter
    def Enabled(self, on):
        self._enabled = bool(on)
        self._draw()

    # ------------------------------------------------------------ methods
    def Reset(self):
        self.Value = 0

    def SetValue(self, value):
        self.Value = value

    # ------------------------------------------------------------ drawing / input
    def _geometry(self):
        w, h = max(1, self.winfo_width()), max(1, self.winfo_height())
        left, top, right, bottom = self._padding
        text_w = 34 if self._show_value else 0
        avail_h = h - top - bottom
        size = max(4, min(avail_h, (w - left - right - text_w - self._spacing * (self._max - 1)) / self._max))
        return left, top, size, avail_h

    def _shape_points(self, x, y, s):
        if self._shape == "Star":
            cx, cy, outer = x + s / 2, y + s / 2, s / 2
            pts = []
            for i in range(10):
                r = outer if i % 2 == 0 else outer * 0.45
                a = -math.pi / 2 + i * math.pi / 5
                pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
            return pts
        return None

    def _draw(self):
        self.delete("all")
        left, top, size, avail_h = self._geometry()
        self._cells = []
        for i in range(self._max):
            x = left + i * (size + self._spacing)
            y = top + (avail_h - size) / 2
            on = i < self._value
            if not self._enabled:
                color = "#B0B0B0" if on else "#E0E0E0"
            else:
                color = self._star if on else self._empty
            if self._enabled and self.HoverValue and not self.ReadOnly and i < self.HoverValue and not on:
                color = _darker(self._star, 1.0)
            pts = self._shape_points(x, y, size)
            if pts:
                self.create_polygon(pts, fill=color, outline=_darker(color))
            elif self._shape == "Circle":
                self.create_oval(x + 1, y + 1, x + size - 1, y + size - 1, fill=color, outline=_darker(color))
            else:
                self.create_rectangle(x + 1, y + 1, x + size - 1, y + size - 1, fill=color, outline=_darker(color))
            self._cells.append((x, x + size + self._spacing))
        if self._show_value:
            x = left + self._max * (size + self._spacing)
            self.create_text(x, top + avail_h / 2, anchor="w", text=f"{self._value}/{self._max}",
                             fill=self._fore, font=self._font)

    def _star_at(self, x):
        for i, (a, b) in enumerate(self._cells):
            if a <= x < b:
                return i + 1
        return 0

    def _click(self, e):
        if self.ReadOnly or not self._enabled:
            return
        i = self._star_at(e.x)
        if i:
            self.Value = 0 if i == self._value == 1 else i

    def _set_hover(self, i):
        if i != self.HoverValue:
            self.HoverValue = i
            self._draw()
            self._raise("Hover")

    def _motion(self, e):
        if self._enabled:
            self._set_hover(self._star_at(e.x))
