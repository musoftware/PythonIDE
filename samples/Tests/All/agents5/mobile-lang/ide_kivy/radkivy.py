"""RAD IDE runtime for Kivy apps (copied into the project by the IDE - do not edit, it is replaced).

    self.ShowForm("Details", args)   open another screen     self.CloseForm(result)  go back
    self.FormArgs                    the args of ShowForm      RadApp.data             shared values
    self.MsgBox(text) / self.Toast(text) / self.InputBox(prompt, callback)
"""
import inspect
import json
import os
import sys
import webbrowser

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty, ObjectProperty,
                             StringProperty)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.dropdown import DropDown
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.switch import Switch
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton

PRIMARY = (0.25, 0.32, 0.71, 1)       # indigo
ON_PRIMARY = (1, 1, 1, 1)


class RadEvent:
    """What happened: e.Index (list row / tab), e.Action (app bar action), e.Text, e.Value."""
    def __init__(self, Index=-1, Action="", Text="", Value=None):
        self.Index, self.Action, self.Text, self.Value = Index, Action, Text, Value

    def __repr__(self):
        return f"RadEvent(Index={self.Index!r}, Action={self.Action!r}, Text={self.Text!r}, Value={self.Value!r})"


class RadApp(App):
    data = {}                          # values shared by every screen
    bg = ListProperty([0.98, 0.98, 1, 1])
    fg = ListProperty([0.1, 0.1, 0.12, 1])

    def __init__(self, startup, **kw):
        super().__init__(**kw)
        self.startup = startup
        self.history = []

    def build(self):
        self.title = _project_name()
        self.sm = ScreenManager(transition=SlideTransition(duration=0.2))
        self.sm.add_widget(_load_screen(self.startup))
        return self.sm


def _project_name():
    try:
        with open("project.radproj", encoding="utf-8") as f:
            return json.load(f).get("name", "Kivy App")
    except (OSError, ValueError):
        return "Kivy App"


def _load_screen(name):
    if name not in sys.modules:
        __import__(name)
    cls = getattr(sys.modules[name], name)
    return cls(name=name)


def run_app(startup):
    """Start the app with the screen *startup* (the window gets the phone size of its form)."""
    try:
        mod = sys.modules.get(startup) or sys.modules.get("__main__")
        cls = getattr(mod, startup + "Designer", None) or getattr(mod, startup, None)
        w, h = getattr(cls, "design_size", (360, 640))
        if os.environ.get("RADKIVY_WINDOW", "1") == "1" and sys.platform not in ("android", "ios"):
            Window.size = (dp(w), dp(h))
    except Exception:  # noqa: BLE001
        pass
    if "__main__" in sys.modules and startup not in sys.modules:
        sys.modules[startup] = sys.modules["__main__"]      # ShowForm finds the start screen by name
    secs = float(os.environ.get("RADKIVY_AUTOSTOP", "0") or 0)
    app = RadApp(startup)
    if secs > 0:                                             # tests: close after a few seconds
        Clock.schedule_once(lambda dt: app.stop(), secs)
    code, shot = os.environ.get("RADKIVY_EXEC"), os.environ.get("RADKIVY_SHOT")
    if code:                                                 # tests: run code with scr = the screen
        Clock.schedule_once(lambda dt: exec(code, {"scr": app.sm.current_screen, "app": app}), 1.0)
    if shot:
        Clock.schedule_once(lambda dt: Window.screenshot(name=shot), max(1.5, secs - 1.0) if secs else 2.0)
    app.run()


class RadScreen(Screen):
    """Base of every generated screen: navigation, dialogs and event wiring."""
    form_name = ""
    design_size = (360, 640)
    title = ""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.FormArgs = None
        self._loaded = False

    # ---------------------------------------------------------------- events
    def _call(self, names, event):
        for name in names:
            fn = getattr(self, name, None)
            if callable(fn):
                try:
                    params = [p for p in inspect.signature(fn).parameters.values()
                              if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
                except (TypeError, ValueError):
                    params = []
                return fn(event if event is not None else RadEvent()) if params else fn()
        return None

    def _bind(self, widget, signal, names, make_event=None):
        if not any(callable(getattr(self, n, None)) for n in names):
            return

        def handler(*args):
            ev = make_event(*args) if make_event else None
            self._call(names, ev)
        widget.bind(**{signal: handler})

    def on_pre_enter(self, *a):
        if not self._loaded:
            self._loaded = True
            self._call([self.form_name + "_Load"], None)

    # ---------------------------------------------------------------- navigation
    def ShowForm(self, name, args=None):
        app = App.get_running_app()
        if not app.sm.has_screen(name):
            app.sm.add_widget(_load_screen(name))
        scr = app.sm.get_screen(name)
        scr.FormArgs = args
        scr._loaded = False
        app.history.append(self.name)
        app.sm.transition.direction = "left"
        app.sm.current = name
        return scr

    def CloseForm(self, result=None):
        app = App.get_running_app()
        if not app.history:
            app.stop()
            return
        back = app.history.pop()
        app.sm.transition.direction = "right"
        app.sm.current = back
        scr = app.sm.get_screen(back)
        cb = getattr(scr, "Form_Closed", None)
        if callable(cb):
            cb(self.name, result)

    # ---------------------------------------------------------------- dialogs
    def MsgBox(self, text, title=""):
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        lbl = Label(text=str(text), halign="center", valign="middle")
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        btn = Button(text="OK", size_hint_y=None, height=dp(44))
        box.add_widget(lbl)
        box.add_widget(btn)
        pop = Popup(title=title or self.title or "Message", content=box, size_hint=(0.85, None), height=dp(220))
        btn.bind(on_release=pop.dismiss)
        pop.open()
        return pop

    def InputBox(self, prompt, callback, value=""):
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        ti = TextInput(text=value, multiline=False, size_hint_y=None, height=dp(44))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        ok, cancel = Button(text="OK"), Button(text="Cancel")
        row.add_widget(cancel)
        row.add_widget(ok)
        box.add_widget(Label(text=str(prompt)))
        box.add_widget(ti)
        box.add_widget(row)
        pop = Popup(title=self.title or "Input", content=box, size_hint=(0.85, None), height=dp(240))
        ok.bind(on_release=lambda *_: (pop.dismiss(), callback(ti.text)))
        cancel.bind(on_release=lambda *_: (pop.dismiss(), callback(None)))
        pop.open()

    def Toast(self, text, seconds=2.0):
        lbl = Label(text=str(text), size_hint=(None, None), color=(1, 1, 1, 1), padding=(dp(16), dp(10)))
        lbl.texture_update()
        lbl.size = (lbl.texture_size[0] + dp(32), lbl.texture_size[1] + dp(20))
        with lbl.canvas.before:
            Color(0.15, 0.15, 0.15, 0.92)
            rect = RoundedRectangle(radius=[dp(18)])
        lbl.bind(pos=lambda w, p: setattr(rect, "pos", p), size=lambda w, s: setattr(rect, "size", s))
        rect.pos, rect.size = lbl.pos, lbl.size
        Window.add_widget(lbl)
        lbl.pos = ((Window.width - lbl.width) / 2, dp(90))
        Clock.schedule_once(lambda dt: Window.remove_widget(lbl), seconds)


class RadTimer:
    """VB Timer: interval in ms, enabled starts it, Tick handler."""
    def __init__(self, interval, enabled, tick):
        self.Interval, self._tick, self._ev = interval, tick, None
        if enabled:
            Clock.schedule_once(lambda dt: self.start(), 0)

    @property
    def enabled(self):
        return self._ev is not None

    @enabled.setter
    def enabled(self, on):
        self.start() if on else self.stop()

    def start(self):
        self.stop()
        self._ev = Clock.schedule_interval(lambda dt: self._tick(), max(0.001, self.Interval / 1000))

    def stop(self):
        if self._ev is not None:
            self._ev.cancel()
            self._ev = None


# ==================================================================== widgets
class _Visible:
    """VB-like .visible / .enabled on every RAD widget."""
    @property
    def visible(self):
        return self.opacity > 0

    @visible.setter
    def visible(self, on):
        self.opacity = 1 if on else 0
        self.disabled = not on

    @property
    def enabled(self):
        return not self.disabled

    @enabled.setter
    def enabled(self, on):
        self.disabled = not on


for _cls in (Button, Label, TextInput, Image, FloatLayout, BoxLayout, ScrollView, Switch, CheckBox):
    for _n in ("visible", "enabled"):
        if not hasattr(_cls, _n):
            setattr(_cls, _n, getattr(_Visible, _n))


class _Tap:
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and not self.disabled and self.opacity > 0:
            if super().on_touch_down(touch):
                return True
            self.dispatch("on_tap")
            return True
        return super().on_touch_down(touch)

    def on_tap(self):
        pass


class RadLabel(_Tap, Label):
    __events__ = ("on_tap",)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.valign = "middle"
        self.bind(size=lambda w, s: setattr(w, "text_size", s))


class RadImage(_Tap, Image):
    __events__ = ("on_tap",)

    def on_source(self, *a):
        src = self.source
        if src and not src.startswith(("http://", "https://")) and not os.path.exists(src):
            alt = os.path.join("assets", os.path.basename(src))
            if os.path.exists(alt):
                self.source = alt


class RadIcon(_Tap, Label):
    __events__ = ("on_tap",)
    icon = StringProperty("star")
    SYMBOLS = {"add": "+", "close": "x", "check": "v", "menu": "=", "search": "?", "star": "*",
               "favorite": "<3", "home": "^", "info": "i", "help": "?", "more_vert": ":", "delete": "-",
               "arrow_back": "<", "arrow_forward": ">", "settings": "@", "person": "o", "edit": "/"}

    def on_icon(self, *a):
        self.text = self.SYMBOLS.get(self.icon, self.icon[:1].upper())

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bold = True
        self.on_icon()


class RadCheckBox(BoxLayout):
    text = StringProperty("")
    active = BooleanProperty(False)
    group = ObjectProperty(None, allownone=True)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.box = CheckBox(size_hint_x=None, width=dp(36), color=(0.2, 0.2, 0.3, 1))
        self.lbl = RadLabel(color=(0.1, 0.1, 0.12, 1))
        self.add_widget(self.box)
        self.add_widget(self.lbl)
        self.box.bind(active=lambda w, v: setattr(self, "active", v))
        self.lbl.bind(on_tap=lambda *_: setattr(self.box, "active", True if self.group else not self.box.active))
        self.on_text()
        self.on_active()
        self.on_group()

    def on_text(self, *a):
        if hasattr(self, "lbl"):
            self.lbl.text = self.text

    def on_active(self, *a):
        if hasattr(self, "box"):
            self.box.active = self.active

    def on_group(self, *a):
        if hasattr(self, "box"):
            self.box.group = self.group


class RadSwitch(BoxLayout):
    text = StringProperty("")
    active = BooleanProperty(False)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.lbl = RadLabel(color=(0.1, 0.1, 0.12, 1))
        self.sw = Switch(size_hint_x=None, width=dp(90))
        self.add_widget(self.lbl)
        self.add_widget(self.sw)
        self.sw.bind(active=lambda w, v: setattr(self, "active", v))
        self.on_text()
        self.on_active()

    def on_text(self, *a):
        if hasattr(self, "lbl"):
            self.lbl.text = self.text
            self.lbl.size_hint_x = 1 if self.text else 0.001

    def on_active(self, *a):
        if hasattr(self, "sw"):
            self.sw.active = self.active


class RadList(ScrollView):
    """ListBox / ListView: items "title|subtitle"; add_item, remove_at, clear, selected_index."""
    __events__ = ("on_tap",)
    items = ListProperty([])
    template = StringProperty("title")
    selected_index = NumericProperty(-1)
    font_size = NumericProperty(dp(15))
    color = ListProperty([0.1, 0.1, 0.12, 1])

    def __init__(self, **kw):
        self.box = BoxLayout(orientation="vertical", size_hint_y=None)
        super().__init__(**kw)
        self.box.bind(minimum_height=self.box.setter("height"))
        self.add_widget(self.box)
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._bg = Rectangle()
        self.bind(pos=self._paint, size=self._paint)
        self.on_items()

    def _paint(self, *a):
        self._bg.pos, self._bg.size = self.pos, self.size

    def on_items(self, *a):
        if not hasattr(self, "box"):
            return
        self.box.clear_widgets()
        fields = [f.strip().lower() for f in self.template.split("|")]
        for i, it in enumerate(self.items):
            parts = [p.strip() for p in str(it).split("|")]
            get = lambda role: parts[fields.index(role)] if role in fields and fields.index(role) < len(parts) else ""
            title = get("title") or parts[0]
            sub = get("subtitle")
            text = f"{title}\n[size={int(self.font_size * 0.8)}][color=666666]{sub}[/color][/size]" if sub else title
            row = ToggleButton(text=text, markup=True, size_hint_y=None, height=dp(64 if sub else 44),
                               halign="left", valign="middle", background_normal="", background_down="",
                               background_color=(0.85, 0.88, 1, 1) if i == self.selected_index else (1, 1, 1, 1),
                               color=self.color, font_size=self.font_size)
            row.bind(size=lambda w, s: setattr(w, "text_size", (s[0] - dp(24), s[1])))
            row.bind(on_release=lambda w, i=i: self._tap(i))
            self.box.add_widget(row)

    def on_selected_index(self, *a):
        for i, row in enumerate(reversed(self.box.children)):
            row.background_color = (0.85, 0.88, 1, 1) if i == self.selected_index else (1, 1, 1, 1)

    def _tap(self, i):
        self.selected_index = i
        self.dispatch("on_tap", i)

    def on_tap(self, index):
        pass

    @property
    def selected_item(self):
        return self.items[self.selected_index] if 0 <= self.selected_index < len(self.items) else ""

    def add_item(self, text):
        self.items.append(str(text))

    def remove_at(self, index):
        if 0 <= index < len(self.items):
            del self.items[index]

    def clear(self):
        self.items = []
        self.selected_index = -1

    def field(self, i, n):
        parts = str(self.items[i]).split("|")
        return parts[n].strip() if n < len(parts) else ""


class RadAppBar(BoxLayout):
    __events__ = ("on_action", "on_menu")
    title = StringProperty("")
    actions = ListProperty([])
    menu_items = ListProperty([])
    bar_color = ListProperty(PRIMARY)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.padding = (dp(8), 0)
        self.spacing = dp(4)
        with self.canvas.before:
            self._c = Color(*self.bar_color)
            self._r = Rectangle()
        self.bind(pos=self._paint, size=self._paint, title=self._build, actions=self._build,
                  menu_items=self._build, bar_color=self._paint)
        self._build()

    def _paint(self, *a):
        self._c.rgba = self.bar_color
        self._r.pos, self._r.size = self.pos, self.size

    def _flat(self, text, w=None):
        b = Button(text=text, background_normal="", background_color=(0, 0, 0, 0), color=ON_PRIMARY,
                   size_hint_x=None, width=w or dp(44), bold=True)
        return b

    def _build(self, *a):
        self.clear_widgets()
        if self.menu_items:
            b = self._flat("=")
            b.bind(on_release=self._open_menu)
            self.add_widget(b)
        t = Label(text=self.title, color=ON_PRIMARY, bold=True, font_size=dp(19), halign="left", valign="middle")
        t.bind(size=lambda w, s: setattr(w, "text_size", s))
        self.add_widget(t)
        for i, a in enumerate(self.actions):
            label = a.split(":")[0]
            b = self._flat(RadIcon.SYMBOLS.get(label.lower(), label), None if label.lower() in RadIcon.SYMBOLS
                           else dp(16 + 9 * len(label)))
            b.bind(on_release=lambda w, i=i, a=a: self.dispatch("on_action", i, a))
            self.add_widget(b)

    def _open_menu(self, btn):
        dd = DropDown()
        for i, it in enumerate(self.menu_items):
            label = it.split(":")[0]
            b = Button(text=label, size_hint_y=None, height=dp(44))
            b.bind(on_release=lambda w, i=i, label=label: (dd.dismiss(), self.dispatch("on_menu", i, label)))
            dd.add_widget(b)
        dd.open(btn)

    def on_action(self, index, action):
        pass

    def on_menu(self, index, item):
        pass


class RadTabs(BoxLayout):
    """BottomNav / TabBar: items, selected_index, on_changed."""
    __events__ = ("on_changed",)
    items = ListProperty([])
    selected_index = NumericProperty(0)
    bottom = BooleanProperty(False)

    def __init__(self, **kw):
        super().__init__(**kw)
        self._group = f"tabs{id(self)}"
        self.bind(items=self._build)
        self._build()

    def _build(self, *a):
        self.clear_widgets()
        for i, it in enumerate(self.items):
            label = it.split(":")[0]
            b = ToggleButton(text=label, group=self._group, allow_no_selection=False,
                             state="down" if i == self.selected_index else "normal")
            b.bind(on_release=lambda w, i=i: self._select(i))
            self.add_widget(b)

    def _select(self, i):
        self.selected_index = i
        self.dispatch("on_changed", i)

    def on_selected_index(self, *a):
        for i, b in enumerate(reversed(self.children)):
            b.state = "down" if i == self.selected_index else "normal"

    def on_changed(self, index):
        pass

    @property
    def selected_item(self):
        return self.items[self.selected_index].split(":")[0] if 0 <= self.selected_index < len(self.items) else ""


class RadFab(Button):
    icon = StringProperty("add")
    fab_color = ListProperty(PRIMARY)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.background_normal = ""
        self.background_color = (0, 0, 0, 0)
        self.font_size = dp(26)
        self.bold = True
        with self.canvas.before:
            self._c = Color(*self.fab_color)
            self._r = RoundedRectangle(radius=[dp(16)])
        self.bind(pos=self._paint, size=self._paint, fab_color=self._paint, icon=self._label)
        self._label()

    def _paint(self, *a):
        self._c.rgba = self.fab_color
        self._r.pos, self._r.size = self.pos, self.size

    def _label(self, *a):
        if not self.text:
            self.text = RadIcon.SYMBOLS.get(self.icon, "+")


class RadCard(_Tap, FloatLayout):
    __events__ = ("on_tap",)
    elevation = NumericProperty(1)
    card_color = ListProperty([1, 1, 1, 1])

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._sc = Color(0, 0, 0, 0.12)
            self._shadow = RoundedRectangle(radius=[dp(12)])
            self._c = Color(*self.card_color)
            self._r = RoundedRectangle(radius=[dp(12)])
        self.bind(pos=self._paint, size=self._paint, card_color=self._paint, elevation=self._paint)

    def _paint(self, *a):
        e = dp(self.elevation)
        self._shadow.pos, self._shadow.size = (self.x, self.y - e), self.size
        self._c.rgba = self.card_color
        self._r.pos, self._r.size = self.pos, self.size


class RadWebLink(Button):
    url = StringProperty("")

    def on_url(self, *a):
        self.text = f"Open {self.url}"

    def on_release(self):
        if self.url:
            webbrowser.open(self.url)


for _cls in (RadLabel, RadImage, RadIcon, RadCheckBox, RadSwitch, RadList, RadAppBar, RadTabs, RadFab, RadCard,
             RadWebLink):
    Factory.register(_cls.__name__, cls=_cls)
