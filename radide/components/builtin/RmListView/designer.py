"""RmListView on the design surface: radide/components/rmpaint.py draws every Rm* control like the native runtime."""
from radide.components.rmpaint import paint_control


def paint(painter, rect, props, ctx):
    paint_control("RmListView", painter, rect, props, ctx)
