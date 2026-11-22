"""Fast approximate Flutter preview drawn with Qt (the designer's fallback when Flutter / the live preview host
is not available, and the instant first frame while the live preview starts).

It implements a small version of Flutter's box layout protocol (min/max constraints down, sizes up) for the
catalog widgets of ``model.CATALOG`` - Scaffold, AppBar, Container + BoxDecoration (gradients, images, borders,
radius, shadows), Padding / Center / Align, Row / Column / Flex with main / cross alignment and Expanded /
Flexible / Spacer, Stack + Positioned, SizedBox, scroll views, Text with TextStyle, Icon (the SDK's Material
icon font), Image, TextField + InputDecoration, the buttons, Card, ListTile, navigation bars, inputs ... - and
paints a Material 3 look (ColorScheme from the screen's seed colour, light / dark, text scale). It also returns
the bounds of every node (selection overlay) and plays the screen's entrance animations (``anim``).

It is an approximation: the real rendering comes from the Flutter preview host (live.py).

Package layout (one job per module; each imports only the ones above it - core reaches paint.default_font at
call time - so there are no import cycles):

    colors.py       flutter_colors, named_color, color_scheme (+ _FALLBACK_COLORS, _hex_color, _hsl)
    core.py         INF, C (BoxConstraints), Box, at, Env, Ctx and the value parsers num / edge / radii / align /
                    enum_val / color / props / slot (+ _ALIGN)
    paint.py        default_font, make_font, merge_style, rrect_path, gradient_brush, shadows, paint_image,
                    paint_decoration, paint_border, shape_path / shape_side, ImageCache
    registry.py     LAYOUTS + @reg, layout_node, _error_box / _unknown, first_child, passthrough, pad_box,
                    align_box, child_fn
    w_layout.py     Container, Padding, SafeArea, Center, Align, SizedBox ... Row / Column / Flex, Wrap, Stack,
                    scroll views, ListView, GridView, PageView
    w_content.py    Text / RichText, Icon, Image, CircleAvatar, Divider, Placeholder, FlutterLogo, progress
    w_inputs.py     Chip, Badge, text fields, Checkbox, Switch, Slider, DropdownButton, list tiles, Radio, buttons
    w_structure.py  Card, Material, DecoratedBox, Opacity, clips, AppBar, navigation / tab bars, Drawer,
                    Cupertino scaffold widgets, Code, Scaffold
    w_motion.py     implicit animations / transitions, Lottie / Rive, RadTwoPane
    render.py       anim_state / anim_end, paint_box, bounds, hit_test, render_tree, make_ctx, render_image

The widget modules register their layout functions with @reg when imported; they are imported below in the
order the single-file module defined them, so LAYOUTS (keys, order, the winner of a repeated type) is unchanged.
Every name of the former single-file module (public and private, e.g. ``qtpreview._text_box``) is re-exported
here, so ``qtpreview.<name>`` keeps working for every caller.
"""
from __future__ import annotations

# colorsys ... QTransform, iconfont, M: names of the former single-file module, kept (see __all__)
import colorsys
import math
import re
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import (QBrush, QColor, QConicalGradient, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter,
                         QPainterPath, QPen, QRadialGradient, QTextLayout, QTextOption, QTransform)

from .. import iconfont
from .. import model as M
from .colors import _FALLBACK_COLORS, flutter_colors, _hex_color, named_color, _hsl, color_scheme
from .core import INF, C, Box, at, Env, Ctx, num, edge, radii, _ALIGN, align, enum_val, color, props, slot
from .paint import (default_font, _WEIGHTS, make_font, merge_style, rrect_path, gradient_brush, paint_shadows,
                    drop_shadow, QPainterPathStrokerCompat, paint_image, paint_decoration, paint_border, shape_path,
                    shape_side, ImageCache)
from .registry import (LAYOUTS, reg, layout_node, _error_box, _unknown, first_child, passthrough, pad_box,
                       align_box, child_fn)
from .w_layout import (_container, _padding, _safearea, _center, _align, _sizedbox, _constrainedbox, _aspect,
                       _fraction, _fitted, _transform, _rotated, _visibility, _pass, _inkwell, _spacer, flex_of,
                       flex_layout, _row, _column, _flex, _wrap, _stack, _scroll_axis, _scv, _listview, _grid,
                       _pageview)
from .w_content import (_text_box, _rich_box, _richtext, _text, _icon, _image, _avatar, _divider, _placeholder,
                        _flutterlogo, _cpi, _lpi)
from .w_inputs import (_chip_like, _chip, _badge, _field_box, _textfield, _cuptf, _checkbox, _switch_paint, _switch,
                       _cupswitch, _slider, _dropdown, _list_tile, _listtile, _icon_box, _radio_group, _radio_paint,
                       _radio, _radio_tile, _ctrl_tile, _BTN_KIND, _button, _iconbutton, _matbutton, _fab,
                       _cupbutton)
from .w_structure import (_card, _material, _decorated, _opacity, _cliprrect, _clipoval, _appbar, _bottomnav,
                          _tabbar, _tab, _drawer, _drawerheader, _cupnav, _cupscaffold, _cupspin, _code, _scaffold)
from .w_motion import (_xform_box, _pair, _anim_scale, _anim_rotation, _anim_slide, _fade_transition,
                       _size_transition, _anim_text_style, _cross_fade, _anim_asset, _two_pane)
from .render import (_curve, anim_state, anim_end, paint_box, _paint_frame, _paint_overflow, bounds, hit_test,
                     render_tree, make_ctx, render_image)

# `from .qtpreview import *` exports exactly what the single-file module exported (its public names) ...
__all__ = [
    "Box", "C", "Ctx", "Env", "INF", "ImageCache", "LAYOUTS", "M", "Path", "QBrush", "QColor", "QConicalGradient",
    "QFont", "QFontMetricsF", "QImage", "QLinearGradient", "QObject", "QPainter", "QPainterPath",
    "QPainterPathStrokerCompat", "QPen", "QPointF", "QRadialGradient", "QRectF", "QTextLayout", "QTextOption",
    "QTransform", "QUrl", "Qt", "align", "align_box", "anim_end", "anim_state", "annotations", "at", "bounds",
    "child_fn", "color", "color_scheme", "colorsys", "dataclass", "default_font", "drop_shadow", "edge", "enum_val",
    "field", "first_child", "flex_layout", "flex_of", "flutter_colors", "gradient_brush", "hit_test", "iconfont",
    "layout_node", "lru_cache", "make_ctx", "make_font", "math", "merge_style", "named_color", "num", "pad_box",
    "paint_border", "paint_box", "paint_decoration", "paint_image", "paint_shadows", "passthrough", "props",
    "pyqtSignal", "radii", "re", "reg", "render_image", "render_tree", "replace", "rrect_path", "shape_path",
    "shape_side", "slot",
]
# ... and the private helpers stay importable by name (from .qtpreview import _text_box, ...).
_PRIVATE_REEXPORTS = (_FALLBACK_COLORS, _hex_color, _hsl, _ALIGN, _WEIGHTS, _error_box, _unknown, _container,
                      _padding, _safearea, _center, _align, _sizedbox, _constrainedbox, _aspect, _fraction, _fitted,
                      _transform, _rotated, _visibility, _pass, _inkwell, _spacer, _row, _column, _flex, _wrap,
                      _stack, _scroll_axis, _scv, _listview, _grid, _pageview, _text_box, _rich_box, _richtext,
                      _text, _icon, _image, _avatar, _divider, _placeholder, _flutterlogo, _cpi, _lpi, _chip_like,
                      _chip, _badge, _field_box, _textfield, _cuptf, _checkbox, _switch_paint, _switch, _cupswitch,
                      _slider, _dropdown, _list_tile, _listtile, _icon_box, _radio_group, _radio_paint, _radio,
                      _radio_tile, _ctrl_tile, _BTN_KIND, _button, _iconbutton, _matbutton, _fab, _cupbutton, _card,
                      _material, _decorated, _opacity, _cliprrect, _clipoval, _appbar, _bottomnav, _tabbar, _tab,
                      _drawer, _drawerheader, _cupnav, _cupscaffold, _cupspin, _code, _scaffold, _xform_box, _pair,
                      _anim_scale, _anim_rotation, _anim_slide, _fade_transition, _size_transition,
                      _anim_text_style, _cross_fade, _anim_asset, _two_pane, _curve, _paint_frame, _paint_overflow)


def __getattr__(name: str):
    """Module globals the code rebinds at run time (``global``) are read live from their module."""
    if name in _LIVE:
        from . import paint
        return getattr(paint, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_LIVE = ("_fonts_loaded",)
