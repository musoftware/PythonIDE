"""RmTabStrip on the design surface: radide/components/rmpaint.py draws every Rm* control like the native runtime."""
from radide.components.rmpaint import paint_control, tab_at as _tab_at


def paint(painter, rect, props, ctx):
    paint_control("RmTabStrip", painter, rect, props, ctx)


def tab_at(props, x, y, w, h):
    """Page clicked in the designer (the designer shows that page): -1 = none."""
    return _tab_at({**props, "_type": "RmTabStrip"}, x, y, w, h)
