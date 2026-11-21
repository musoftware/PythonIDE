"""Flutter designer model: the *.fscreen.json format, the widget catalog and undo-friendly tree operations.

The schema is documented in docs/FLUTTER_DESIGNER.md (sections 1-3 and 6). Everything here is plain Python
(no Qt) so the designer, the code generator, the importer and the tests share it.
"""
from __future__ import annotations

import copy
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 1
SCREEN_EXT = ".fscreen.json"

# =========================================================================================== enums
ENUMS: dict[str, list[str]] = {
    "MainAxisAlignment": ["start", "end", "center", "spaceBetween", "spaceAround", "spaceEvenly"],
    "CrossAxisAlignment": ["start", "end", "center", "stretch", "baseline"],
    "MainAxisSize": ["min", "max"],
    "Axis": ["horizontal", "vertical"],
    "WrapAlignment": ["start", "end", "center", "spaceBetween", "spaceAround", "spaceEvenly"],
    "WrapCrossAlignment": ["start", "end", "center"],
    "StackFit": ["loose", "expand", "passthrough"],
    "FlexFit": ["tight", "loose"],
    "Clip": ["none", "hardEdge", "antiAlias", "antiAliasWithSaveLayer"],
    "TextAlign": ["left", "right", "center", "justify", "start", "end"],
    "TextOverflow": ["clip", "fade", "ellipsis", "visible"],
    "FontWeight": ["w100", "w200", "w300", "w400", "w500", "w600", "w700", "w800", "w900", "normal", "bold"],
    "FontStyle": ["normal", "italic"],
    "TextDecoration": ["none", "underline", "overline", "lineThrough"],
    "BoxFit": ["fill", "contain", "cover", "fitWidth", "fitHeight", "none", "scaleDown"],
    "BoxShape": ["rectangle", "circle"],
    "Alignment": ["topLeft", "topCenter", "topRight", "centerLeft", "center", "centerRight", "bottomLeft",
                  "bottomCenter", "bottomRight"],
    "TextInputType": ["text", "multiline", "number", "phone", "datetime", "emailAddress", "url",
                      "visiblePassword", "name", "streetAddress"],
    "TextInputAction": ["done", "go", "next", "search", "send", "newline"],
    "FloatingActionButtonLocation": ["endFloat", "centerFloat", "startFloat", "endDocked", "centerDocked",
                                     "endTop", "startTop", "centerTop"],
    "BottomNavigationBarType": ["fixed", "shifting"],
    "ListTileControlAffinity": ["leading", "trailing", "platform"],
    "TabBarIndicatorSize": ["tab", "label"],
    "HitTestBehavior": ["deferToChild", "opaque", "translucent"],
    "Curves": ["linear", "ease", "easeIn", "easeOut", "easeInOut", "easeOutCubic", "easeInOutCubic",
               "fastOutSlowIn", "decelerate", "bounceOut", "elasticOut", "easeOutBack"],
    "Physics": ["BouncingScrollPhysics", "ClampingScrollPhysics", "NeverScrollableScrollPhysics",
                "AlwaysScrollableScrollPhysics"],
    "CrossFadeState": ["showFirst", "showSecond"],
    "RadPaneMode": ["auto", "horizontal", "vertical"],
    "RadPane": ["start", "end"],
    "AutovalidateMode": ["disabled", "always", "onUserInteraction", "onUnfocus"],
}
ANIM_TYPES = ["fadeIn", "fadeInUp", "fadeInDown", "fadeInLeft", "fadeInRight", "slideUp", "slideDown",
              "slideLeft", "slideRight", "scaleIn", "zoomIn", "bounceIn",
              # attention seekers / text / colour / keyframes (flutterdesign/motion.py)
              "shake", "pulse", "bounce", "flipX", "flipY", "rotate", "swing", "heartBeat", "typewriter",
              "colorTo", "keyframes"]

PROP_KINDS = {"string", "int", "double", "bool", "color", "enum", "edge_insets", "border_radius", "alignment",
              "icon", "offset", "duration", "string_list", "image", "gradient", "box_shadows", "border",
              "box_decoration", "text_style", "shape", "button_style", "input_decoration", "nav_items",
              "constraints", "physics", "code",
              "timeline", "timeline_offset",    # Animation<double> / Animation<Offset> (explicit transitions)
              "text_spans", "validators"}       # Text.rich / RichText spans, TextFormField validator rules
# validator rules of TextFormField.validators (lib/radform.dart RadRule.<rule>)
VALIDATOR_RULES = ["required", "email", "minLength", "maxLength", "regex"]


# ========================================================================================= catalog
@dataclass
class PropSpec:
    kind: str
    default: Any = None
    enum: str = ""                    # enum name for kind "enum" (values in ENUMS[enum])
    positional: int | None = None     # positional argument index
    required: bool = False
    group: str = ""                   # inspector group (Layout, Style, Text, Behaviour ...)
    help: str = ""

    @property
    def values(self) -> list[str]:
        return [f"{self.enum}.{v}" for v in ENUMS.get(self.enum, [])] if self.enum else []


@dataclass
class SlotSpec:
    multi: bool = False               # a list of widgets (AppBar.actions)
    required: bool = False
    accepts: tuple[str, ...] | None = None   # preferred child types (palette hint), None = any widget


@dataclass
class CtorSpec:
    props: dict[str, PropSpec] = field(default_factory=dict)
    slots: dict[str, SlotSpec] = field(default_factory=dict)
    drop_props: tuple[str, ...] = ()  # props of the default constructor not valid here
    drop_slots: tuple[str, ...] = ()
    const_ctor: bool | None = None    # None = same as the default constructor
    children: str | None | bool = False   # False = same as the default constructor
    help: str = ""


@dataclass
class WidgetSpec:
    type: str
    category: str
    help: str = ""
    props: dict[str, PropSpec] = field(default_factory=dict)
    slots: dict[str, SlotSpec] = field(default_factory=dict)
    children: str | None = None
    events: dict[str, str] = field(default_factory=dict)
    ctors: dict[str, CtorSpec] = field(default_factory=dict)
    default_ctor: str | None = None   # the ctor new nodes use (Image -> "network"); "" allowed = unnamed
    unnamed_ctor: bool = True         # Type(...) exists (Image/Transform/GridView: named ctors only)
    parent: tuple[str, ...] = ()
    needs_name: bool = False
    name_prefix: str = "w"
    value_prop: str = ""              # prop holding the state value (Checkbox.value, Slider.value ...)
    value_type: str = ""              # Dart type of the state field ("bool", "TextEditingController" ...)
    required_events: tuple[str, ...] = ()   # emitted as () {} when not wired
    event_returns: dict[str, str] = field(default_factory=dict)   # handler return types (default void)
    const_ctor: bool = True
    library: str = "material"
    template: dict = field(default_factory=dict)

    def resolved(self, ctor: str | None) -> "WidgetSpec":
        """The spec of a named constructor (props/slots merged); the spec itself for the default one."""
        if not ctor or ctor not in self.ctors:
            return self
        c = self.ctors[ctor]
        props = {k: v for k, v in self.props.items() if k not in c.drop_props}
        props.update(c.props)
        slots = {k: v for k, v in self.slots.items() if k not in c.drop_slots}
        slots.update(c.slots)
        out = copy.copy(self)
        out.props, out.slots = props, slots
        if c.const_ctor is not None:
            out.const_ctor = c.const_ctor
        if c.children is not False:
            out.children = c.children
        return out


def P(kind: str, default=None, *, pos: int | None = None, req=False, group="", help="") -> PropSpec:
    """Property spec shorthand. ``kind`` "enum:Name" sets the enum."""
    enum = ""
    if kind.startswith("enum:"):
        kind, enum = "enum", kind[5:]
    assert kind in PROP_KINDS, kind
    return PropSpec(kind, default, enum, pos, req, group, help)


S = SlotSpec
CATALOG: dict[str, WidgetSpec] = {}


def _w(type_: str, category: str, help: str, props=None, slots=None, children=None, events=None, **kw):
    spec = WidgetSpec(type_, category, help, dict(props or {}), dict(slots or {}), children, dict(events or {}),
                      **kw)
    CATALOG[type_] = spec
    return spec


def T(type_: str, props=None, slots=None, children=None, ctor=None, **extra) -> dict:
    """Template node (no ids yet)."""
    n: dict = {"type": type_}
    if ctor:
        n["ctor"] = ctor
    if props:
        n["props"] = props
    if slots:
        n["slots"] = slots
    if children:
        n["children"] = children
    n.update(extra)
    return n


def _txt(s: str) -> dict:
    return T("Text", {"data": s})


def _ico(name: str) -> dict:
    return T("Icon", {"icon": f"Icons.{name}"})


# ---- shared prop groups
_FLEX = {"mainAxisAlignment": P("enum:MainAxisAlignment", "MainAxisAlignment.start", group="Layout"),
         "crossAxisAlignment": P("enum:CrossAxisAlignment", "CrossAxisAlignment.center", group="Layout"),
         "mainAxisSize": P("enum:MainAxisSize", "MainAxisSize.max", group="Layout"),
         "spacing": P("double", 0, group="Layout", help="gap between children")}
_SIZE = {"width": P("double", group="Layout"), "height": P("double", group="Layout")}
_CHILD = {"child": S()}
_CHILD_REQ = {"child": S(required=True)}
_SCROLL = {"scrollDirection": P("enum:Axis", "Axis.vertical", group="Layout"),
           "padding": P("edge_insets", group="Layout"), "reverse": P("bool", False),
           "physics": P("physics"), "shrinkWrap": P("bool", False)}
_BUTTON_EVENTS = {"onPressed": "", "onLongPress": ""}
_TEXTFIELD = {"decoration": P("input_decoration", {"hintText": "Enter text"}, group="Style"),
              "obscureText": P("bool", False, group="Behaviour"),
              "keyboardType": P("enum:TextInputType", group="Behaviour"),
              "textInputAction": P("enum:TextInputAction", group="Behaviour"),
              "maxLines": P("int", 1, group="Behaviour"), "minLines": P("int", group="Behaviour"),
              "maxLength": P("int", group="Behaviour"), "style": P("text_style", group="Text"),
              "textAlign": P("enum:TextAlign", "TextAlign.start", group="Text"),
              "enabled": P("bool", group="Behaviour"), "autofocus": P("bool", False, group="Behaviour"),
              "readOnly": P("bool", False, group="Behaviour"), "cursorColor": P("color", group="Style")}
_BTN_ICON = CtorSpec(slots={"icon": S(), "label": S(required=True)}, drop_slots=("child",), const_ctor=False,
                     help="button with an icon and a label")

# ------------------------------------------------------------------------------------------ Layout
_w("Scaffold", "Layout", "Page structure: app bar, body, floating button, drawer, bottom bar",
   {"backgroundColor": P("color", group="Style"),
    "extendBodyBehindAppBar": P("bool", False, group="Layout"),
    "extendBody": P("bool", False, group="Layout"),
    "resizeToAvoidBottomInset": P("bool", group="Behaviour"),
    "floatingActionButtonLocation": P("enum:FloatingActionButtonLocation", group="Layout")},
   {"appBar": S(accepts=("AppBar", "Code")), "body": S(), "floatingActionButton": S(),
    "drawer": S(accepts=("Drawer",)), "endDrawer": S(accepts=("Drawer",)),
    "bottomNavigationBar": S(accepts=("BottomNavigationBar", "NavigationBar")), "bottomSheet": S(),
    "persistentFooterButtons": S(multi=True)},
   template=T("Scaffold", slots={"appBar": T("AppBar", slots={"title": _txt("Screen")}),
                                 "body": T("Center", slots={"child": _txt("Hello")})}))
_w("SafeArea", "Layout", "Keeps the child away from notches and system bars",
   {"top": P("bool", True), "bottom": P("bool", True), "left": P("bool", True), "right": P("bool", True),
    "minimum": P("edge_insets")}, _CHILD_REQ)
_w("Container", "Layout", "Box with size, padding, margin, colour, gradient, border, radius and shadows",
   {"alignment": P("alignment", group="Layout"), "padding": P("edge_insets", group="Layout"),
    "margin": P("edge_insets", group="Layout"), **_SIZE, "color": P("color", group="Style"),
    "decoration": P("box_decoration", group="Style"), "constraints": P("constraints", group="Layout"),
    "clipBehavior": P("enum:Clip", "Clip.none", group="Style")}, _CHILD, const_ctor=False,
   template=T("Container", {"width": 120, "height": 120}))
_w("Padding", "Layout", "Empty space around the child",
   {"padding": P("edge_insets", {"all": 8}, req=True, group="Layout")}, _CHILD,
   template=T("Padding", {"padding": {"all": 16}}))
_w("Center", "Layout", "Centres the child", {"widthFactor": P("double"), "heightFactor": P("double")}, _CHILD)
_w("Align", "Layout", "Places the child at an alignment",
   {"alignment": P("alignment", "Alignment.center", group="Layout"), "widthFactor": P("double"),
    "heightFactor": P("double")}, _CHILD)
_w("Column", "Layout", "Children in a vertical line", _FLEX, children="children")
_w("Row", "Layout", "Children in a horizontal line", _FLEX, children="children")
_w("Flex", "Layout", "Row or column chosen by direction",
   {"direction": P("enum:Axis", "Axis.horizontal", req=True, group="Layout"), **_FLEX}, children="children",
   template=T("Flex", {"direction": "Axis.horizontal"}))
_w("Wrap", "Layout", "Children in rows that wrap to the next line",
   {"direction": P("enum:Axis", "Axis.horizontal", group="Layout"),
    "alignment": P("enum:WrapAlignment", "WrapAlignment.start", group="Layout"),
    "spacing": P("double", 0, group="Layout"), "runSpacing": P("double", 0, group="Layout"),
    "runAlignment": P("enum:WrapAlignment", "WrapAlignment.start", group="Layout"),
    "crossAxisAlignment": P("enum:WrapCrossAlignment", "WrapCrossAlignment.start", group="Layout")},
   children="children", template=T("Wrap", {"spacing": 8, "runSpacing": 8}))
_w("Stack", "Layout", "Children on top of each other (use Positioned to place them)",
   {"alignment": P("alignment", group="Layout"), "fit": P("enum:StackFit", "StackFit.loose", group="Layout"),
    "clipBehavior": P("enum:Clip", "Clip.hardEdge", group="Style")}, children="children")
_w("Positioned", "Layout", "Places a child of a Stack by its edges",
   {"left": P("double", group="Layout"), "top": P("double", group="Layout"), "right": P("double", group="Layout"),
    "bottom": P("double", group="Layout"), **_SIZE}, _CHILD_REQ, parent=("Stack",),
   ctors={"fill": CtorSpec(drop_props=("width", "height"), help="fills the Stack")},
   template=T("Positioned", {"left": 0, "top": 0}))
_FLEXPARENT = ("Row", "Column", "Flex")
_w("Expanded", "Layout", "Fills the remaining space of a Row / Column",
   {"flex": P("int", 1, group="Layout")}, _CHILD_REQ, parent=_FLEXPARENT)
_w("Flexible", "Layout", "Shares the space of a Row / Column",
   {"flex": P("int", 1, group="Layout"), "fit": P("enum:FlexFit", "FlexFit.loose", group="Layout")}, _CHILD_REQ,
   parent=_FLEXPARENT)
_w("Spacer", "Layout", "Empty flexible space in a Row / Column", {"flex": P("int", 1, group="Layout")},
   parent=_FLEXPARENT)
_w("SizedBox", "Layout", "Fixed size box or a gap", _SIZE, _CHILD,
   ctors={"expand": CtorSpec(drop_props=("width", "height"), help="as big as the parent allows"),
          "shrink": CtorSpec(drop_props=("width", "height"), help="zero size"),
          "square": CtorSpec(props={"dimension": P("double", 50, group="Layout")}, drop_props=("width", "height"))},
   template=T("SizedBox", {"width": 16, "height": 16}))
_w("ConstrainedBox", "Layout", "Min / max size for the child",
   {"constraints": P("constraints", {"maxWidth": 400}, req=True, group="Layout")}, _CHILD, const_ctor=False)
_w("AspectRatio", "Layout", "Child with a width / height ratio",
   {"aspectRatio": P("double", 1.0, req=True, group="Layout")}, _CHILD,
   template=T("AspectRatio", {"aspectRatio": 1.7778}))
_w("FractionallySizedBox", "Layout", "Child sized as a fraction of the parent",
   {"widthFactor": P("double", group="Layout"), "heightFactor": P("double", group="Layout"),
    "alignment": P("alignment", group="Layout")}, _CHILD, template=T("FractionallySizedBox", {"widthFactor": 0.8}))
_w("FittedBox", "Layout", "Scales the child to fit",
   {"fit": P("enum:BoxFit", "BoxFit.contain"), "alignment": P("alignment")}, _CHILD)
_w("Transform", "Layout", "Rotates, scales or moves the child",
   {"alignment": P("alignment")}, _CHILD, unnamed_ctor=False, default_ctor="rotate", const_ctor=False,
   ctors={"rotate": CtorSpec(props={"angle": P("double", 0.0, req=True, help="radians")}),
          "scale": CtorSpec(props={"scale": P("double", 1.0)}),
          "translate": CtorSpec(props={"offset": P("offset", [0, 0], req=True)}, drop_props=("alignment",))},
   template=T("Transform", {"angle": 0.1}, ctor="rotate"))
_w("Visibility", "Layout", "Shows or hides the child", {"visible": P("bool", True, req=True)}, _CHILD_REQ)
_w("IntrinsicHeight", "Layout", "Sizes the child to its natural height (rows of equal height)", {}, _CHILD)

# ------------------------------------------------------------------------------------------ Scroll
_w("SingleChildScrollView", "Scroll", "Scrolls one child (e.g. a long Column / a form)",
   {k: v for k, v in _SCROLL.items() if k != "shrinkWrap"}, _CHILD)
_BUILDER_PROPS = {"itemCount": P("int", 5, req=True, group="Data", help="number of items"),
                  "items": P("string_list", group="Data",
                             help="sample data: the template reads `item` (and `index`) in Dart values")}
_w("ListView", "Scroll", "Scrolling list of children",
   {**_SCROLL, "itemExtent": P("double", group="Layout")}, children="children", const_ctor=False,
   ctors={"builder": CtorSpec(props=dict(_BUILDER_PROPS), slots={"itemBuilder": S(required=True)}, children=None,
                              help="items built on demand from one template (variables index / item)")})
_w("GridView", "Scroll", "Scrolling grid", {**_SCROLL, "mainAxisSpacing": P("double", 0, group="Layout"),
                                             "crossAxisSpacing": P("double", 0, group="Layout"),
                                             "childAspectRatio": P("double", 1.0, group="Layout")},
   children="children", const_ctor=False, unnamed_ctor=False, default_ctor="count",
   ctors={"count": CtorSpec(props={"crossAxisCount": P("int", 2, req=True, group="Layout")},
                            help="a fixed number of columns"),
          "extent": CtorSpec(props={"maxCrossAxisExtent": P("double", 150, req=True, group="Layout")},
                             help="columns of a maximum width"),
          "builder": CtorSpec(props={"crossAxisCount": P("int", 2, req=True, group="Layout"), **_BUILDER_PROPS},
                              slots={"itemBuilder": S(required=True)}, children=None,
                              help="cells built on demand from one template (variables index / item)")},
   template=T("GridView", {"crossAxisCount": 2, "mainAxisSpacing": 8, "crossAxisSpacing": 8}, ctor="count"))
_w("PageView", "Scroll", "Swipeable pages",
   {"scrollDirection": P("enum:Axis", "Axis.horizontal"), "physics": P("physics"),
    "pageSnapping": P("bool", True), "reverse": P("bool", False)},
   children="children", events={"onPageChanged": "int index"}, const_ctor=False)

# ----------------------------------------------------------------------------------------- Content
_TEXT_PROPS = {"data": P("string", "Text", pos=0, req=True, group="Text"),
               "style": P("text_style", group="Text"), "textAlign": P("enum:TextAlign", group="Text"),
               "maxLines": P("int", group="Text"), "overflow": P("enum:TextOverflow", group="Text"),
               "softWrap": P("bool", group="Text")}
_SPANS_HELP = 'TextSpan list: [{"text": "Hello ", "style": {...}}, ...]'
_w("Text", "Content", "A run of text with a style (font, size, weight, colour)", _TEXT_PROPS,
   ctors={"rich": CtorSpec(props={"spans": P("text_spans", [{"text": "Rich "}, {"text": "text", "style": {
       "fontWeight": "FontWeight.bold"}}], pos=0, req=True, group="Text", help=_SPANS_HELP)}, drop_props=("data",),
       help="text made of spans with their own styles (TextSpan children)")},
   template=_txt("Text"))
_w("RichText", "Content", "Text made of styled spans (no default theme style: give the spans a colour)",
   {"spans": P("text_spans", [{"text": "Rich "}, {"text": "text", "style": {"fontWeight": "FontWeight.bold"}}],
               req=True, group="Text", help=_SPANS_HELP),
    "style": P("text_style", group="Text", help="style of the root TextSpan (inherited by the spans)"),
    "textAlign": P("enum:TextAlign", group="Text"), "maxLines": P("int", group="Text"),
    "overflow": P("enum:TextOverflow", group="Text"), "softWrap": P("bool", group="Text")},
   const_ctor=False,
   template=T("RichText", {"spans": [{"text": "Rich ", "style": {"color": "#FF1F1F1F", "fontSize": 16}},
                                     {"text": "text", "style": {"color": "#FF6750A4", "fontSize": 16,
                                                                "fontWeight": "FontWeight.bold"}}]}))
_w("SelectableText", "Content", "Text the user can select and copy",
   {k: v for k, v in _TEXT_PROPS.items() if k not in ("overflow", "softWrap")})
_w("Icon", "Content", "A Material / Cupertino icon",
   {"icon": P("icon", "Icons.star", pos=0, req=True), "size": P("double"), "color": P("color")},
   template=_ico("star"))
_w("Image", "Content", "Picture from the app assets or the network",
   {"src": P("string", "https://picsum.photos/400/300", pos=0, req=True, help="asset path or URL"),
    **_SIZE, "fit": P("enum:BoxFit"), "alignment": P("alignment"), "color": P("color")},
   unnamed_ctor=False, default_ctor="network", const_ctor=False,
   ctors={"asset": CtorSpec(help="assets/... file of the app"), "network": CtorSpec(help="https:// URL")},
   template=T("Image", {"src": "https://picsum.photos/400/300", "fit": "BoxFit.cover"}, ctor="network"))
_w("CircleAvatar", "Content", "Round picture, initials or icon",
   {"radius": P("double", 20), "backgroundColor": P("color"), "foregroundColor": P("color"),
    "backgroundImage": P("image")}, _CHILD, template=T("CircleAvatar", {"radius": 24}, {"child": _txt("AB")}))
_DIV = {"thickness": P("double"), "indent": P("double"), "endIndent": P("double"), "color": P("color")}
_w("Divider", "Content", "Thin horizontal line", {"height": P("double"), **_DIV})
_w("VerticalDivider", "Content", "Thin vertical line", {"width": P("double"), **_DIV})
_w("Placeholder", "Content", "A box drawn with a cross (where something will go)",
   {"color": P("color"), "fallbackWidth": P("double", 400), "fallbackHeight": P("double", 400),
    "strokeWidth": P("double", 2)})
_w("CircularProgressIndicator", "Content", "Spinning progress circle",
   {"value": P("double"), "color": P("color"), "backgroundColor": P("color"), "strokeWidth": P("double", 4)})
_w("LinearProgressIndicator", "Content", "Progress bar",
   {"value": P("double"), "color": P("color"), "backgroundColor": P("color"), "minHeight": P("double")})
_w("Chip", "Content", "Compact label with an optional avatar and delete icon",
   {"backgroundColor": P("color"), "padding": P("edge_insets"), "labelStyle": P("text_style")},
   {"label": S(required=True), "avatar": S(), "deleteIcon": S()}, events={"onDeleted": ""},
   template=T("Chip", slots={"label": _txt("Chip")}))
_w("Badge", "Content", "Small count / dot on top of the child",
   {"backgroundColor": P("color"), "textColor": P("color"), "isLabelVisible": P("bool", True)},
   {"label": S(), "child": S()}, template=T("Badge", slots={"label": _txt("3"), "child": _ico("notifications")}))
_w("Tooltip", "Content", "Hint shown on long press / hover", {"message": P("string", "Tooltip", req=True)}, _CHILD)
_w("FlutterLogo", "Content", "The Flutter logo", {"size": P("double")})

# ------------------------------------------------------------------------------------------- Input
_w("TextField", "Input", "Text input with a decoration (hint, label, icons, border)", _TEXTFIELD,
   events={"onChanged": "String value", "onSubmitted": "String value", "onTap": ""},
   needs_name=True, name_prefix="txt", value_type="TextEditingController",
   template=T("TextField", {"decoration": {"hintText": "Enter text", "border": "outline"}}))
_w("TextFormField", "Input", "Text input inside a Form (validation)",
   {**_TEXTFIELD, "decoration": P("input_decoration", {"labelText": "Label"}, group="Style"),
    "validators": P("validators", group="Validation",
                    help='rules: [{"rule": "required" | "email" | "minLength" | "maxLength" | "regex", '
                         '"value": n / pattern, "message": "..."}]; event validator = custom handler')},
   events={"onChanged": "String value", "onFieldSubmitted": "String value", "onTap": "",
           "validator": "String? value"}, event_returns={"validator": "String?"},
   needs_name=True, name_prefix="txt", value_type="TextEditingController", const_ctor=False,
   template=T("TextFormField", {"decoration": {"labelText": "Label", "border": "outline"}}))
_w("Checkbox", "Input", "On / off box", {"value": P("bool", False), "activeColor": P("color"),
                                         "checkColor": P("color")},
   events={"onChanged": "bool? value"}, needs_name=True, name_prefix="chk", value_prop="value",
   value_type="bool")
_w("Switch", "Input", "On / off switch",
   {"value": P("bool", False), "activeThumbColor": P("color"), "activeTrackColor": P("color"),
    "inactiveThumbColor": P("color"), "inactiveTrackColor": P("color")},
   events={"onChanged": "bool value"}, needs_name=True, name_prefix="swt", value_prop="value",
   value_type="bool")
_w("Slider", "Input", "Pick a value by dragging",
   {"value": P("double", 0.5), "min": P("double", 0.0), "max": P("double", 1.0), "divisions": P("int"),
    "label": P("string"), "activeColor": P("color"), "inactiveColor": P("color")},
   events={"onChanged": "double value", "onChangeEnd": "double value"}, needs_name=True, name_prefix="sld",
   value_prop="value", value_type="double")
_w("DropdownButton", "Input", "Pick one item of a list",
   {"value": P("string"), "items": P("string_list", ["One", "Two", "Three"], req=True),
    "hint": P("string", "Choose"), "isExpanded": P("bool", False)},
   events={"onChanged": "String? value"}, needs_name=True, name_prefix="cbo", value_prop="value",
   value_type="String?", const_ctor=False,
   template=T("DropdownButton", {"items": ["One", "Two", "Three"], "hint": "Choose"}))
_LISTTILE_SLOTS = {"title": S(), "subtitle": S(), "secondary": S()}
_w("CheckboxListTile", "Input", "List row with a checkbox",
   {"value": P("bool", False), "controlAffinity": P("enum:ListTileControlAffinity"), "activeColor": P("color")},
   _LISTTILE_SLOTS, events={"onChanged": "bool? value"}, needs_name=True, name_prefix="chk", value_prop="value",
   value_type="bool", template=T("CheckboxListTile", slots={"title": _txt("Option")}))
_w("SwitchListTile", "Input", "List row with a switch",
   {"value": P("bool", False), "controlAffinity": P("enum:ListTileControlAffinity"),
    "activeThumbColor": P("color")},
   _LISTTILE_SLOTS, events={"onChanged": "bool value"}, needs_name=True, name_prefix="swt", value_prop="value",
   value_type="bool", template=T("SwitchListTile", slots={"title": _txt("Setting")}))
_w("Form", "Input", "Groups form fields: name it to get a GlobalKey<FormState>; a button event validate:<name> "
   "(or validate:<name>:<handler>) checks every field",
   {"autovalidateMode": P("enum:AutovalidateMode", group="Behaviour")}, _CHILD_REQ, name_prefix="form",
   value_type="GlobalKey<FormState>", template=T("Form", name="form1"))
_w("RadioGroup", "Input", "Holds the selected value of the Radio / RadioListTile widgets inside it",
   {"groupValue": P("string", group="Behaviour", help="initially selected value (null = none)")}, _CHILD_REQ,
   events={"onChanged": "String? value"}, needs_name=True, name_prefix="rdo", value_prop="groupValue",
   value_type="String?", const_ctor=False,
   template=T("RadioGroup", slots={"child": T("Column", {"mainAxisSize": "MainAxisSize.min"}, children=[
       T("RadioListTile", {"value": "One"}, {"title": _txt("One")}),
       T("RadioListTile", {"value": "Two"}, {"title": _txt("Two")})])}))
_w("Radio", "Input", "Round choice button (inside a RadioGroup)",
   {"value": P("string", "One", req=True), "activeColor": P("color"), "toggleable": P("bool", False),
    "enabled": P("bool")}, template=T("Radio", {"value": "One"}))
_w("RadioListTile", "Input", "List row with a radio button (inside a RadioGroup)",
   {"value": P("string", "One", req=True), "controlAffinity": P("enum:ListTileControlAffinity"),
    "activeColor": P("color"), "toggleable": P("bool", False), "enabled": P("bool")},
   _LISTTILE_SLOTS, template=T("RadioListTile", {"value": "One"}, {"title": _txt("Option")}))
_w("InkWell", "Input", "Makes the child tappable with a ripple",
   {"borderRadius": P("border_radius"), "splashColor": P("color")}, _CHILD,
   events={"onTap": "", "onDoubleTap": "", "onLongPress": ""})
_w("GestureDetector", "Input", "Tap / long press / double tap on the child (no ripple)",
   {"behavior": P("enum:HitTestBehavior")}, _CHILD, events={"onTap": "", "onDoubleTap": "", "onLongPress": ""},
   const_ctor=False)

# ----------------------------------------------------------------------------------------- Buttons
for _b, _h in (("ElevatedButton", "Raised button"), ("FilledButton", "Filled (primary) button"),
               ("TextButton", "Flat text button"), ("OutlinedButton", "Button with an outline")):
    _ctors = {"icon": _BTN_ICON}
    if _b == "FilledButton":
        _ctors["tonal"] = CtorSpec(help="secondary colour")
        _ctors["tonalIcon"] = _BTN_ICON
    _w(_b, "Buttons", _h, {"style": P("button_style", group="Style")}, {"child": S(required=True)},
       events=dict(_BUTTON_EVENTS), required_events=("onPressed",), ctors=_ctors,
       template=T(_b, slots={"child": _txt("Button")}))
_w("IconButton", "Buttons", "Tappable icon",
   {"iconSize": P("double"), "color": P("color"), "tooltip": P("string"), "padding": P("edge_insets")},
   {"icon": S(required=True)}, events={"onPressed": ""}, required_events=("onPressed",),
   ctors={"filled": CtorSpec(), "filledTonal": CtorSpec(), "outlined": CtorSpec()},
   template=T("IconButton", slots={"icon": _ico("favorite_border")}))
_w("MaterialButton", "Buttons", "Classic Material button (colour, shape, height)",
   {"color": P("color", group="Style"), "textColor": P("color", group="Style"), "elevation": P("double"),
    "padding": P("edge_insets"), "minWidth": P("double"), "height": P("double"), "shape": P("shape")},
   {"child": S()}, events=dict(_BUTTON_EVENTS), required_events=("onPressed",),
   template=T("MaterialButton", {"color": "#FF6750A4", "textColor": "Colors.white"},
              {"child": _txt("Button")}))
_w("FloatingActionButton", "Buttons", "Round floating action button",
   {"backgroundColor": P("color"), "foregroundColor": P("color"), "tooltip": P("string"),
    "mini": P("bool", False), "elevation": P("double"), "shape": P("shape")},
   {"child": S()}, events={"onPressed": ""}, required_events=("onPressed",),
   ctors={"extended": CtorSpec(slots={"label": S(required=True), "icon": S()}, drop_slots=("child",),
                               drop_props=("mini",))},
   template=T("FloatingActionButton", slots={"child": _ico("add")}))

# ---------------------------------------------------------------------------------------- Material
_w("AppBar", "Material", "Top bar with a title, leading button and actions",
   {"backgroundColor": P("color", group="Style"), "foregroundColor": P("color", group="Style"),
    "elevation": P("double", group="Style"), "centerTitle": P("bool"),
    "automaticallyImplyLeading": P("bool", True), "toolbarHeight": P("double")},
   {"title": S(), "leading": S(), "actions": S(multi=True), "flexibleSpace": S(),
    "bottom": S(accepts=("TabBar",))}, const_ctor=False,
   template=T("AppBar", slots={"title": _txt("Title")}))
_w("BottomNavigationBar", "Navigation", "Bottom bar with 2-5 destinations",
   {"currentIndex": P("int", 0), "items": P("nav_items", req=True),
    "type": P("enum:BottomNavigationBarType"), "backgroundColor": P("color"),
    "selectedItemColor": P("color"), "unselectedItemColor": P("color"), "iconSize": P("double", 24),
    "showUnselectedLabels": P("bool")}, events={"onTap": "int index"}, needs_name=True, name_prefix="nav",
   value_prop="currentIndex", value_type="int", const_ctor=False,
   template=T("BottomNavigationBar", {"items": [{"icon": "Icons.home", "label": "Home"},
                                                {"icon": "Icons.search", "label": "Search"},
                                                {"icon": "Icons.person", "label": "Profile"}]}))
_w("NavigationBar", "Navigation", "Material 3 bottom navigation",
   {"selectedIndex": P("int", 0), "destinations": P("nav_items", req=True), "backgroundColor": P("color"),
    "indicatorColor": P("color")}, events={"onDestinationSelected": "int index"}, needs_name=True,
   name_prefix="nav", value_prop="selectedIndex", value_type="int", const_ctor=False,
   template=T("NavigationBar", {"destinations": [{"icon": "Icons.home", "label": "Home"},
                                                 {"icon": "Icons.settings", "label": "Settings"}]}))
_w("Drawer", "Navigation", "Side menu (Scaffold.drawer)",
   {"backgroundColor": P("color"), "width": P("double"), "elevation": P("double")}, _CHILD,
   template=T("Drawer", slots={"child": T("ListView", {"padding": {"all": 0}}, children=[
       T("DrawerHeader", slots={"child": _txt("Menu")}), T("ListTile", slots={"leading": _ico("home"),
                                                                              "title": _txt("Home")})])}))
_w("DrawerHeader", "Navigation", "Header area at the top of a Drawer",
   {"decoration": P("box_decoration"), "padding": P("edge_insets"), "margin": P("edge_insets")}, _CHILD)
_w("TabBar", "Navigation", "Row of tabs (inside a DefaultTabController)",
   {"isScrollable": P("bool", False), "indicatorColor": P("color"), "labelColor": P("color"),
    "unselectedLabelColor": P("color"), "indicatorSize": P("enum:TabBarIndicatorSize")},
   children="tabs", events={"onTap": "int index"},
   template=T("TabBar", children=[T("Tab", {"text": "One"}), T("Tab", {"text": "Two"})]))
_w("Tab", "Navigation", "One tab of a TabBar", {"text": P("string", "Tab"), "height": P("double")},
   {"icon": S(), "child": S()}, parent=("TabBar",), template=T("Tab", {"text": "Tab"}))
_w("TabBarView", "Navigation", "The pages of the tabs", {"physics": P("physics")}, children="children")
_w("DefaultTabController", "Navigation", "Connects a TabBar to a TabBarView",
   {"length": P("int", 2, req=True), "initialIndex": P("int", 0)}, _CHILD_REQ,
   template=T("DefaultTabController"))
_w("Card", "Material", "Raised panel with rounded corners",
   {"color": P("color", group="Style"), "elevation": P("double", group="Style"),
    "margin": P("edge_insets", group="Layout"), "shape": P("shape", group="Style"),
    "clipBehavior": P("enum:Clip", group="Style"), "shadowColor": P("color", group="Style")}, _CHILD,
   template=T("Card", slots={"child": T("Padding", {"padding": {"all": 16}}, {"child": _txt("Card")})}))
_w("ListTile", "Material", "List row: leading, title, subtitle, trailing",
   {"dense": P("bool"), "contentPadding": P("edge_insets"), "tileColor": P("color"), "selected": P("bool", False),
    "enabled": P("bool", True)},
   {"leading": S(), "title": S(), "subtitle": S(), "trailing": S()}, events={"onTap": "", "onLongPress": ""},
   template=T("ListTile", slots={"leading": _ico("person"), "title": _txt("Title"),
                                 "subtitle": _txt("Subtitle")}))
_w("ExpansionTile", "Material", "List row that expands to show children",
   {"initiallyExpanded": P("bool", False), "backgroundColor": P("color"),
    "collapsedBackgroundColor": P("color")},
   {"title": S(required=True), "subtitle": S(), "leading": S(), "trailing": S()}, children="children",
   events={"onExpansionChanged": "bool expanded"}, template=T("ExpansionTile", slots={"title": _txt("More")}))
_w("Material", "Material", "Material surface (colour, elevation, ink)",
   {"color": P("color"), "elevation": P("double", 0), "borderRadius": P("border_radius"),
    "shadowColor": P("color")}, _CHILD)

# ----------------------------------------------------------------------------------------- Effects
_w("Opacity", "Effects", "Makes the child transparent", {"opacity": P("double", 1.0, req=True)}, _CHILD,
   template=T("Opacity", {"opacity": 0.5}))
_w("ClipRRect", "Effects", "Clips the child with rounded corners",
   {"borderRadius": P("border_radius", 12), "clipBehavior": P("enum:Clip")}, _CHILD,
   template=T("ClipRRect", {"borderRadius": 12}))
_w("ClipOval", "Effects", "Clips the child to a circle / oval", {"clipBehavior": P("enum:Clip")}, _CHILD)
_w("Hero", "Effects", "Flies the child to the next screen (same tag)",
   {"tag": P("string", "hero", req=True)}, _CHILD_REQ, template=T("Hero", {"tag": "hero"}))
_w("DecoratedBox", "Effects", "Paints a decoration behind the child",
   {"decoration": P("box_decoration", {"color": "#FFE3E7FF"}, req=True)}, _CHILD)
_w("RotatedBox", "Effects", "Rotates the child by quarter turns", {"quarterTurns": P("int", 1, req=True)},
   _CHILD)

# --------------------------------------------------------------------------------------- Animation
_w("AnimatedContainer", "Animation", "Container that animates changes of its properties",
   {"duration": P("duration", 300, req=True), "curve": P("enum:Curves"),
    **{k: v for k, v in CATALOG["Container"].props.items()}}, _CHILD, const_ctor=False,
   template=T("AnimatedContainer", {"duration": 300, "width": 120, "height": 120, "color": "#FFE3E7FF"}))
_w("AnimatedOpacity", "Animation", "Animates the transparency of the child",
   {"opacity": P("double", 1.0, req=True), "duration": P("duration", 300, req=True), "curve": P("enum:Curves")},
   _CHILD, template=T("AnimatedOpacity", {"opacity": 1.0, "duration": 300}))
_w("AnimatedSwitcher", "Animation", "Cross-fades when the child changes",
   {"duration": P("duration", 300, req=True)}, _CHILD, template=T("AnimatedSwitcher", {"duration": 300}))
_ANIM_DUR = {"duration": P("duration", 300, req=True), "curve": P("enum:Curves")}
_w("AnimatedPadding", "Animation", "Padding that animates to a new value",
   {"padding": P("edge_insets", {"all": 16}, req=True, group="Layout"), **_ANIM_DUR}, _CHILD,
   template=T("AnimatedPadding", {"padding": {"all": 16}, "duration": 300}))
_w("AnimatedAlign", "Animation", "Align that animates to a new alignment",
   {"alignment": P("alignment", "Alignment.center", req=True, group="Layout"), "widthFactor": P("double"),
    "heightFactor": P("double"), **_ANIM_DUR}, _CHILD,
   template=T("AnimatedAlign", {"alignment": "Alignment.center", "duration": 300}))
_w("AnimatedPositioned", "Animation", "Positioned (inside a Stack) that animates to a new place",
   {"left": P("double", group="Layout"), "top": P("double", group="Layout"), "right": P("double", group="Layout"),
    "bottom": P("double", group="Layout"), "width": P("double", group="Layout"),
    "height": P("double", group="Layout"), **_ANIM_DUR}, _CHILD_REQ, parent=("Stack",),
   template=T("AnimatedPositioned", {"left": 0, "top": 0, "duration": 300}))
_w("AnimatedScale", "Animation", "Scales the child, animating changes",
   {"scale": P("double", 1.0, req=True), "alignment": P("alignment"), **_ANIM_DUR}, _CHILD,
   template=T("AnimatedScale", {"scale": 1.0, "duration": 300}))
_w("AnimatedRotation", "Animation", "Rotates the child (turns), animating changes",
   {"turns": P("double", 0.0, req=True, help="1 = one full turn"), "alignment": P("alignment"), **_ANIM_DUR},
   _CHILD, template=T("AnimatedRotation", {"turns": 0.0, "duration": 300}))
_w("AnimatedSlide", "Animation", "Moves the child by a fraction of its size, animating changes",
   {"offset": P("offset", [0, 0], req=True, help="(1, 0) = one child width to the right"), **_ANIM_DUR},
   _CHILD, template=T("AnimatedSlide", {"offset": [0, 0], "duration": 300}))
_w("AnimatedSize", "Animation", "Animates its size when the child's size changes",
   {"alignment": P("alignment"), **_ANIM_DUR}, _CHILD, template=T("AnimatedSize", {"duration": 300}))
_w("AnimatedDefaultTextStyle", "Animation", "Text style for the texts inside, animating changes",
   {"style": P("text_style", {"fontSize": 16}, req=True, group="Text"), "textAlign": P("enum:TextAlign"),
    **_ANIM_DUR}, _CHILD_REQ,
   template=T("AnimatedDefaultTextStyle", {"style": {"fontSize": 16}, "duration": 300},
              {"child": _txt("Text")}))
_w("AnimatedCrossFade", "Animation", "Cross-fades between two children (crossFadeState)",
   {"crossFadeState": P("enum:CrossFadeState", "CrossFadeState.showFirst", req=True),
    "duration": P("duration", 300, req=True), "firstCurve": P("enum:Curves"), "secondCurve": P("enum:Curves"),
    "sizeCurve": P("enum:Curves")},
   {"firstChild": S(required=True), "secondChild": S(required=True)},
   template=T("AnimatedCrossFade", {"crossFadeState": "CrossFadeState.showFirst", "duration": 300},
              {"firstChild": _txt("First"), "secondChild": _txt("Second")}))
# explicit transitions: driven by a screen timeline ({"$timeline": "intro", ...})
_w("FadeTransition", "Animation", "Fades the child with a screen timeline",
   {"opacity": P("timeline", req=True, help='{"$timeline": "intro", "from": 0, "to": 1}')}, _CHILD,
   template=T("FadeTransition", {"opacity": 1.0}))
_w("SlideTransition", "Animation", "Moves the child (fractions of its size) with a screen timeline",
   {"position": P("timeline_offset", req=True, help='{"$timeline": "intro", "from": [0, 1], "to": [0, 0]}')},
   _CHILD, template=T("SlideTransition", {"position": [0, 0]}))
_w("ScaleTransition", "Animation", "Scales the child with a screen timeline",
   {"scale": P("timeline", req=True), "alignment": P("alignment")}, _CHILD,
   template=T("ScaleTransition", {"scale": 1.0}))
_w("RotationTransition", "Animation", "Rotates the child (turns) with a screen timeline",
   {"turns": P("timeline", req=True), "alignment": P("alignment")}, _CHILD,
   template=T("RotationTransition", {"turns": 0.0}))
_w("SizeTransition", "Animation", "Reveals the child (size factor 0..1) with a screen timeline",
   {"sizeFactor": P("timeline", req=True), "axis": P("enum:Axis", "Axis.vertical"),
    "axisAlignment": P("double", 0.0)}, _CHILD, template=T("SizeTransition", {"sizeFactor": 1.0}))
_w("Lottie", "Animation", "Lottie animation (assets/animations/*.json or a URL; package:lottie)",
   {"name": P("string", "assets/animations/anim.json", pos=0, req=True, help="asset path / URL"),
    "width": P("double", group="Layout"), "height": P("double", group="Layout"), "fit": P("enum:BoxFit"),
    "repeat": P("bool"), "reverse": P("bool"), "animate": P("bool")},
   ctors={"asset": CtorSpec(), "network": CtorSpec()}, default_ctor="asset", unnamed_ctor=False,
   const_ctor=False, library="lottie",
   template=T("Lottie", {"name": "assets/animations/anim.json", "width": 160, "height": 160}, ctor="asset"))
_w("RiveAnimation", "Animation", "Rive animation (*.riv asset or URL; package:rive)",
   {"name": P("string", "assets/animations/anim.riv", pos=0, req=True, help="asset path / URL"),
    "artboard": P("string"), "animations": P("string_list"), "stateMachines": P("string_list"),
    "fit": P("enum:BoxFit"), "alignment": P("alignment")},
   ctors={"asset": CtorSpec(), "network": CtorSpec()}, default_ctor="asset", unnamed_ctor=False,
   const_ctor=False, library="rive",
   template=T("RiveAnimation", {"name": "assets/animations/anim.riv"}, ctor="asset"))

# ---------------------------------------------------------------------------------------- Cupertino
_w("CupertinoPageScaffold", "Cupertino", "iOS page with a navigation bar",
   {"backgroundColor": P("color")}, {"navigationBar": S(accepts=("CupertinoNavigationBar",)),
                                     "child": S(required=True)}, library="cupertino",
   template=T("CupertinoPageScaffold", slots={
       "navigationBar": T("CupertinoNavigationBar", slots={"middle": _txt("Page")}),
       "child": T("Center", slots={"child": _txt("Hello")})}))
_w("CupertinoNavigationBar", "Cupertino", "iOS top bar", {"backgroundColor": P("color")},
   {"leading": S(), "middle": S(), "trailing": S()}, library="cupertino",
   template=T("CupertinoNavigationBar", slots={"middle": _txt("Title")}))
_w("CupertinoButton", "Cupertino", "iOS button",
   {"color": P("color"), "padding": P("edge_insets")}, {"child": S(required=True)},
   events={"onPressed": ""}, required_events=("onPressed",), library="cupertino",
   ctors={"filled": CtorSpec(drop_props=("color",))},
   template=T("CupertinoButton", slots={"child": _txt("Button")}))
_w("CupertinoTextField", "Cupertino", "iOS text input",
   {"placeholder": P("string", "Text"), "obscureText": P("bool", False), "padding": P("edge_insets"),
    "keyboardType": P("enum:TextInputType"), "style": P("text_style")},
   events={"onChanged": "String value", "onSubmitted": "String value"}, needs_name=True, name_prefix="txt",
   value_type="TextEditingController", library="cupertino",
   template=T("CupertinoTextField", {"placeholder": "Text"}))
_w("CupertinoSwitch", "Cupertino", "iOS switch", {"value": P("bool", False), "activeTrackColor": P("color")},
   events={"onChanged": "bool value"}, needs_name=True, name_prefix="swt", value_prop="value",
   value_type="bool", library="cupertino")
_w("CupertinoSlider", "Cupertino", "iOS slider",
   {"value": P("double", 0.5), "min": P("double", 0.0), "max": P("double", 1.0), "divisions": P("int"),
    "activeColor": P("color")}, events={"onChanged": "double value"}, needs_name=True, name_prefix="sld",
   value_prop="value", value_type="double", library="cupertino")
_w("CupertinoActivityIndicator", "Cupertino", "iOS spinner",
   {"radius": P("double", 10), "color": P("color"), "animating": P("bool", True)}, library="cupertino")
_w("CupertinoListTile", "Cupertino", "iOS list row",
   {"backgroundColor": P("color")}, {"title": S(required=True), "subtitle": S(), "leading": S(), "trailing": S()},
   events={"onTap": ""}, library="cupertino", template=T("CupertinoListTile", slots={"title": _txt("Title")}))

# ------------------------------------------------------------------------------------------ Special
_w("Code", "Special", "Dart code the designer does not model (kept verbatim)",
   {"code": P("code", "const SizedBox()", req=True, help="a Dart expression; #{slot:name} = a designed child")},
   const_ctor=False, library="widgets", template=T("Code", {"code": "const SizedBox()"}))

_w("RadTwoPane", "Layout", "Two panes side by side / stacked, split at a foldable's hinge (lib/radlayout.dart)",
   {"paneMode": P("enum:RadPaneMode", "RadPaneMode.auto", group="Layout"),
    "ratio": P("double", 0.5, group="Layout", help="share of the start pane without a hinge"),
    "singlePane": P("enum:RadPane", "RadPane.start", group="Layout", help="pane shown on a narrow screen"),
    "hingeAware": P("bool", True, group="Layout"), "minDualWidth": P("double", 600, group="Layout")},
   {"start": S(required=True), "end": S(required=True)}, library="radlayout",
   template=T("RadTwoPane", slots={"start": T("Center", slots={"child": _txt("List")}),
                                   "end": T("Center", slots={"child": _txt("Details")})}))

# widgets that live in package:flutter/widgets (no Material needed) - informational for the preview host
for _t in ("SafeArea", "Container", "Padding", "Center", "Align", "Column", "Row", "Flex", "Wrap", "Stack",
           "Positioned", "Expanded", "Flexible", "Spacer", "SizedBox", "ConstrainedBox", "AspectRatio",
           "FractionallySizedBox", "FittedBox", "Transform", "Visibility", "IntrinsicHeight",
           "SingleChildScrollView", "ListView", "GridView", "PageView", "Text", "Icon", "Image", "Placeholder",
           "Form", "GestureDetector", "Opacity", "ClipRRect", "ClipOval", "Hero", "DecoratedBox", "RotatedBox",
           "AnimatedContainer", "AnimatedOpacity", "AnimatedSwitcher", "FlutterLogo", "AnimatedPadding",
           "AnimatedAlign", "AnimatedPositioned", "AnimatedScale", "AnimatedRotation", "AnimatedSlide",
           "AnimatedSize", "AnimatedDefaultTextStyle", "AnimatedCrossFade", "FadeTransition",
           "SlideTransition", "ScaleTransition", "RotationTransition", "SizeTransition"):
    CATALOG[_t].library = "widgets" if _t != "FlutterLogo" else "material"

# the wrappers offered by "Wrap with" (designer context menu)
WRAPPERS = ["Padding", "Center", "Align", "Container", "SizedBox", "Expanded", "Flexible", "Column", "Row",
            "Stack", "Positioned", "Card", "SingleChildScrollView", "SafeArea", "ClipRRect", "Opacity", "InkWell",
            "GestureDetector", "Hero", "Visibility", "AspectRatio", "FittedBox", "Material"]
CATEGORY_ORDER = ["Layout", "Scroll", "Content", "Input", "Buttons", "Material", "Navigation", "Effects",
                  "Animation", "Cupertino", "Special"]


def widget_spec(type_: str, ctor: str | None = None) -> WidgetSpec | None:
    spec = CATALOG.get(type_)
    return spec.resolved(ctor) if spec else None


def categories() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {c: [] for c in CATEGORY_ORDER}
    for t, s in CATALOG.items():
        out.setdefault(s.category, []).append(t)
    return {k: v for k, v in out.items() if v}


def default_props(type_: str, ctor: str | None = None) -> dict:
    spec = widget_spec(type_, ctor)
    return {k: copy.deepcopy(p.default) for k, p in spec.props.items() if p.default is not None} if spec else {}


def can_have_child(type_: str, ctor: str | None = None) -> bool:
    spec = widget_spec(type_, ctor)
    return bool(spec and (spec.children or spec.slots))


def accepts(parent_type: str, child_type: str, where: "Where | None" = None, ctor: str | None = None) -> bool:
    """Can *child_type* go into *parent_type* at *where* (None = anywhere)?"""
    spec = widget_spec(parent_type, ctor)
    child = CATALOG.get(child_type)
    if spec is None or child is None:
        return False
    if child.parent and parent_type not in child.parent and parent_type != "Code":
        return False
    if parent_type == "Code":
        return True
    if where is None:
        return bool(spec.children or spec.slots)
    if where.slot is not None:
        return where.slot in spec.slots
    return bool(spec.children)


def catalog_json() -> dict:
    """The catalog as JSON (for the preview host / tools)."""
    def prop(p: PropSpec) -> dict:
        d = {"kind": p.kind}
        if p.default is not None:
            d["default"] = p.default
        if p.enum:
            d["enum"] = p.enum
        if p.positional is not None:
            d["positional"] = p.positional
        if p.required:
            d["required"] = True
        if p.group:
            d["group"] = p.group
        return d

    def slots(sl: dict[str, SlotSpec]) -> dict:
        return {k: {"multi": s.multi, "required": s.required, **({"accepts": list(s.accepts)} if s.accepts else {})}
                for k, s in sl.items()}
    out = {}
    for t, s in CATALOG.items():
        out[t] = {"category": s.category, "help": s.help, "library": s.library, "constCtor": s.const_ctor,
                  "props": {k: prop(p) for k, p in s.props.items()}, "slots": slots(s.slots),
                  "children": s.children, "events": s.events, "unnamedCtor": s.unnamed_ctor,
                  "defaultCtor": s.default_ctor, "parent": list(s.parent), "needsName": s.needs_name,
                  "valueProp": s.value_prop, "valueType": s.value_type,
                  "requiredEvents": list(s.required_events), "template": s.template,
                  "ctors": {c: {"props": {k: prop(p) for k, p in cs.props.items()}, "slots": slots(cs.slots),
                                "dropProps": list(cs.drop_props), "dropSlots": list(cs.drop_slots),
                                "help": cs.help} for c, cs in s.ctors.items()}}
    return {"version": SCHEMA_VERSION, "enums": ENUMS, "animTypes": ANIM_TYPES, "widgets": out}


# ======================================================================================= values
_HEX = re.compile(r"^(?:#|0x)([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_IDENT = re.compile(r"^[A-Za-z_]\w*$")
DART_KEYWORDS = set("""abstract as assert async await break case catch class const continue covariant default
    deferred do dynamic else enum export extends extension external factory false final finally for Function get
    hide if implements import in interface is late library mixin new null on operator part required rethrow
    return sealed set show static super switch sync this throw true try typedef var void when while with
    yield""".split())


def is_code(value) -> bool:
    return isinstance(value, dict) and set(value) == {"$code"}


def normalize_color(value):
    """'#rgb' / '#rrggbb' / '0xAARRGGBB' -> '#AARRGGBB'; named colours and $code unchanged."""
    if isinstance(value, str):
        m = _HEX.match(value.strip())
        if m:
            h = m.group(1).upper()
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            if len(h) == 6:
                h = "FF" + h
            return "#" + h
    return value


def normalize_value(kind: str, value):
    """Canonical JSON for a property value (unknown shapes are returned unchanged)."""
    if value is None or is_code(value):
        return value
    if kind == "color":
        return normalize_color(value)
    if kind == "double" and isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if kind == "edge_insets" and isinstance(value, (int, float)) and not isinstance(value, bool):
        return {"all": value}
    if kind == "gradient" and isinstance(value, dict):
        v = dict(value)
        v["colors"] = [normalize_color(c) for c in v.get("colors", [])]
        return v
    if kind == "box_shadows" and isinstance(value, list):
        return [dict(s, color=normalize_color(s.get("color"))) if isinstance(s, dict) and "color" in s else s
                for s in value]
    if kind in ("box_decoration", "text_style", "input_decoration", "button_style") and isinstance(value, dict):
        v = dict(value)
        for k in list(v):
            if k.lower().endswith("color"):
                v[k] = normalize_color(v[k])
        if kind == "box_decoration":
            if "gradient" in v:
                v["gradient"] = normalize_value("gradient", v["gradient"])
            if "boxShadow" in v:
                v["boxShadow"] = normalize_value("box_shadows", v["boxShadow"])
        return v
    return value


# ======================================================================================== screen
@dataclass
class Where:
    """Location inside a parent: children index, a slot, or an index in a multi slot."""
    slot: str | None = None
    index: int | None = None

    def to_json(self) -> dict:
        d = {}
        if self.slot is not None:
            d["slot"] = self.slot
        if self.index is not None:
            d["index"] = self.index
        return d

    @staticmethod
    def from_json(d: dict | None) -> "Where":
        d = d or {}
        return Where(d.get("slot"), d.get("index"))


@dataclass
class Issue:
    level: str        # "error" | "warning"
    id: str | None
    message: str

    def __str__(self) -> str:
        return f"{self.level}: {self.id or '-'}: {self.message}"


def snake(name: str) -> str:
    s = re.sub(r"[^0-9A-Za-z]+", "_", name or "")
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", s).strip("_").lower()
    s = re.sub(r"_+", "_", s)
    if not s or s[0].isdigit():
        s = "screen_" + s
    return s


def class_name(name: str) -> str:
    """A PascalCase Dart class name from any screen name."""
    parts = re.split(r"[^0-9A-Za-z]+", name or "")
    s = "".join(p[:1].upper() + p[1:] for p in parts if p)
    if not s or s[0].isdigit():
        s = "Screen" + s
    return s


def _iter_children(node: dict) -> Iterator[tuple[dict, Where]]:
    for slot, v in (node.get("slots") or {}).items():
        if isinstance(v, list):
            for i, c in enumerate(v):
                if isinstance(c, dict):
                    yield c, Where(slot, i)
        elif isinstance(v, dict):
            yield v, Where(slot, None)
    for i, c in enumerate(node.get("children") or []):
        if isinstance(c, dict):
            yield c, Where(None, i)


def walk_node(node: dict, parent: dict | None = None, where: Where | None = None,
              depth: int = 0) -> Iterator[tuple[dict, dict | None, Where | None, int]]:
    yield node, parent, where, depth
    for c, w in _iter_children(node):
        yield from walk_node(c, node, w, depth + 1)


class Screen:
    """A *.fscreen.json document (``data`` is the JSON dict; ``tree`` its root node)."""

    def __init__(self, data: dict | None = None):
        self.data = data if data is not None else {}
        self.data.setdefault("version", SCHEMA_VERSION)
        self.data.setdefault("name", "Screen1")
        self.data.setdefault("route", "/" + snake(self.data["name"]))
        self.data.setdefault("theme", {})
        self.data.setdefault("assets", [])
        self.data.setdefault("fonts", [])
        if not isinstance(self.data.get("tree"), dict):
            self.data["tree"] = {"type": "Scaffold", "id": "w1", "props": {}, "slots": {}}
        self._next = 0
        self._sync_next()

    # ---- io
    @classmethod
    def new(cls, name: str, route: str | None = None, template: str = "Scaffold") -> "Screen":
        name = class_name(name)
        scr = cls({"version": SCHEMA_VERSION, "name": name, "route": route or "/" + snake(name),
                   "theme": {}, "assets": [], "fonts": [], "tree": {"type": "Scaffold", "id": "w1"}})
        scr.data["tree"] = new_node(template, scr)
        return scr

    @classmethod
    def load(cls, path) -> "Screen":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def from_dict(cls, data: dict) -> "Screen":
        return cls(copy.deepcopy(data))

    def to_dict(self) -> dict:
        order = ["version", "name", "route", "theme", "assets", "fonts", "imports", "code", "tree"]
        out = {k: self.data[k] for k in order if k in self.data}
        out.update({k: v for k, v in self.data.items() if k not in out})
        out["tree"] = clean_node(self.data["tree"])
        return out

    def dumps(self) -> str:
        return json.dumps(self.to_dict(), indent=1, ensure_ascii=False) + "\n"

    def save(self, path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        text = self.dumps()
        if not p.exists() or p.read_text(encoding="utf-8", errors="replace") != text:
            p.write_text(text, encoding="utf-8")

    # ---- properties
    @property
    def name(self) -> str:
        return self.data["name"]

    @property
    def route(self) -> str:
        r = str(self.data.get("route") or "").strip() or "/" + snake(self.name)
        return r if r.startswith("/") else "/" + r

    @property
    def tree(self) -> dict:
        return self.data["tree"]

    @tree.setter
    def tree(self, node: dict) -> None:
        self.data["tree"] = node

    # ---- lookup
    def walk(self):
        """(node, parent, Where, depth) for every node, depth-first."""
        return walk_node(self.tree)

    def find(self, node_id: str) -> dict | None:
        for n, _p, _w, _d in self.walk():
            if n.get("id") == node_id:
                return n
        return None

    def parent_of(self, node_id: str) -> tuple[dict | None, Where | None]:
        for n, p, w, _d in self.walk():
            if n.get("id") == node_id:
                return p, w
        raise KeyError(node_id)

    def path_of(self, node_id: str) -> list[dict]:
        """Root ... node."""
        chain: list[dict] = []

        def rec(n: dict) -> bool:
            chain.append(n)
            if n.get("id") == node_id:
                return True
            for c, _w in _iter_children(n):
                if rec(c):
                    return True
            chain.pop()
            return False
        rec(self.tree)
        return chain

    def ids(self) -> set[str]:
        return {n.get("id") for n, *_ in self.walk() if n.get("id")}

    def names(self) -> set[str]:
        return {n["name"] for n, *_ in self.walk() if n.get("name")}

    def _sync_next(self) -> None:
        mx = 0
        for n, *_ in walk_node(self.data["tree"]):
            m = re.match(r"^w(\d+)$", str(n.get("id", "")))
            if m:
                mx = max(mx, int(m.group(1)))
        self._next = max(self._next, mx)

    def new_id(self) -> str:
        self._sync_next()
        self._next += 1
        return f"w{self._next}"

    def new_name(self, prefix: str) -> str:
        used = self.names()
        i = 1
        while f"{prefix}{i}" in used:
            i += 1
        return f"{prefix}{i}"

    def assign_ids(self, node: dict, fresh: bool = False) -> dict:
        """Give every node of *node* an id (fresh=True: always new ids and new names - for copies)."""
        inside = {id(m) for m, *_ in walk_node(node)}       # the node may already be part of the tree
        used, names = set(), set()
        for m, *_ in self.walk():
            if id(m) not in inside:
                if m.get("id"):
                    used.add(m["id"])
                if m.get("name"):
                    names.add(m["name"])
        for n, *_ in walk_node(node):
            if fresh or not n.get("id") or n["id"] in used:
                n["id"] = self.new_id()
                while n["id"] in used:
                    n["id"] = self.new_id()
            used.add(n["id"])
            spec = CATALOG.get(n.get("type", ""))
            needs = spec is not None and spec.needs_name
            if (needs and not n.get("name")) or (n.get("name") and (fresh or n["name"] in names)):
                base = re.sub(r"\d+$", "", n.get("name") or "") or (spec.name_prefix if spec else "w")
                i = 1
                while f"{base}{i}" in names:
                    i += 1
                n["name"] = f"{base}{i}"
            if n.get("name"):
                names.add(n["name"])
        return node

    def validate(self) -> list[Issue]:
        return validate(self)


def new_node(type_: str, screen: Screen | None = None, ctor: str | None = None, props: dict | None = None) -> dict:
    """A node of *type_* from its catalog template (ids/names assigned when *screen* is given)."""
    spec = CATALOG.get(type_)
    if spec is None:
        raise KeyError(f"unknown widget type {type_!r}")
    node = copy.deepcopy(spec.template) if spec.template else {"type": type_}
    if ctor is not None:
        if ctor and ctor not in spec.ctors:
            raise KeyError(f"{type_} has no constructor {ctor!r}")
        if ctor:
            node["ctor"] = ctor
        else:
            node.pop("ctor", None)
    elif spec.default_ctor and "ctor" not in node:
        node["ctor"] = spec.default_ctor
    if props:
        node.setdefault("props", {}).update(props)
    if screen is not None:
        screen.assign_ids(node)
    return node


def clean_node(node: dict) -> dict:
    """Copy of *node* without empty containers, keys in the documented order."""
    out: dict = {}
    for k in ("id", "type", "ctor", "name"):
        if node.get(k) not in (None, ""):
            out[k] = node[k]
    if node.get("props"):
        out["props"] = {k: v for k, v in node["props"].items() if v is not None}
        if not out["props"]:
            del out["props"]
    slots = {}
    for k, v in (node.get("slots") or {}).items():
        if isinstance(v, list):
            if v:
                slots[k] = [clean_node(c) for c in v]
        elif isinstance(v, dict):
            slots[k] = clean_node(v)
    if slots:
        out["slots"] = slots
    if node.get("children"):
        out["children"] = [clean_node(c) for c in node["children"]]
    if node.get("events"):
        out["events"] = {k: v for k, v in node["events"].items() if v}
        if not out["events"]:
            del out["events"]
    if node.get("anim"):
        out["anim"] = node["anim"]
    for k, v in node.items():
        if k not in out and k not in ("props", "slots", "children", "events", "anim", "id", "type", "ctor", "name"):
            out[k] = v
    return out


# ==================================================================================== validation
def validate(screen: Screen | dict) -> list[Issue]:
    scr = screen if isinstance(screen, Screen) else Screen(copy.deepcopy(screen))
    issues: list[Issue] = []
    d = scr.data
    if d.get("version") != SCHEMA_VERSION:
        issues.append(Issue("error", None, f"version must be {SCHEMA_VERSION}"))
    if not _IDENT.match(str(d.get("name", ""))) or str(d.get("name")) in DART_KEYWORDS:
        issues.append(Issue("error", None, f"screen name {d.get('name')!r} is not a Dart class name"))
    seen_ids: set = set()
    seen_names: set = set()
    for n, parent, where, _depth in scr.walk():
        nid = n.get("id")
        t = n.get("type")
        if not nid:
            issues.append(Issue("error", None, f"a {t} node has no id"))
        elif nid in seen_ids:
            issues.append(Issue("error", nid, "duplicate id"))
        seen_ids.add(nid)
        spec = CATALOG.get(t or "")
        if spec is None:
            issues.append(Issue("error", nid, f"unknown widget type {t!r}"))
            continue
        ctor = n.get("ctor")
        if ctor and ctor not in spec.ctors:
            issues.append(Issue("error", nid, f"{t} has no constructor {ctor!r}"))
        elif not ctor and not spec.unnamed_ctor:
            issues.append(Issue("error", nid, f"{t} needs a named constructor ({', '.join(spec.ctors)})"))
        rs = spec.resolved(ctor)
        name = n.get("name")
        if name:
            if not _IDENT.match(name) or name in DART_KEYWORDS:
                issues.append(Issue("error", nid, f"name {name!r} is not a Dart identifier"))
            elif name in seen_names:
                issues.append(Issue("error", nid, f"duplicate name {name!r}"))
            seen_names.add(name)
        elif spec.needs_name:
            issues.append(Issue("warning", nid, f"{t} has no name (a field name is generated)"))
        for k, v in (n.get("props") or {}).items():
            ps = rs.props.get(k)
            if ps is None:
                if not is_code(v) and t != "Code":
                    issues.append(Issue("warning", nid, f"{t} has no property {k!r} (use a $code value)"))
                continue
            if isinstance(v, dict) and ("$when" in v or "$timeline" in v):
                continue                   # animated values: checked by motion.validate
            if ps.kind == "enum" and isinstance(v, str) and v not in ps.values:
                issues.append(Issue("error", nid, f"{k}: {v!r} is not one of {ps.enum}"))
            if ps.kind == "color" and isinstance(v, str) and not (
                    re.match(r"^#[0-9A-Fa-f]{8}$", v) or v.startswith(("Colors.", "CupertinoColors.", "scheme."))):
                issues.append(Issue("error", nid, f"{k}: bad colour {v!r} (#AARRGGBB)"))
            if ps.kind in ("int", "double") and not (is_code(v) or v == "infinity" or (
                    isinstance(v, (int, float)) and not isinstance(v, bool))):
                issues.append(Issue("error", nid, f"{k}: number expected"))
        for k, p in rs.props.items():
            if p.required and p.default is None and k not in (n.get("props") or {}) and t != "Code":
                issues.append(Issue("warning", nid, f"{t}.{k} is required"))
        for slot, v in (n.get("slots") or {}).items():
            ss = rs.slots.get(slot)
            if t == "Code":
                continue
            if ss is None:
                issues.append(Issue("error", nid, f"{t} has no slot {slot!r}"))
            elif ss.multi != isinstance(v, list):
                issues.append(Issue("error", nid, f"slot {slot!r} must be {'a list' if ss.multi else 'one node'}"))
        for slot, ss in rs.slots.items():
            if ss.required and not (n.get("slots") or {}).get(slot):
                issues.append(Issue("warning", nid, f"{t}.{slot} is empty"))
        if n.get("children") and not rs.children:
            issues.append(Issue("error", nid, f"{t} cannot have children (use the child slot)"))
        for ev in (n.get("events") or {}):
            if ev not in rs.events:
                issues.append(Issue("warning", nid, f"{t} has no event {ev!r}"))
        for ev, h in (n.get("events") or {}).items():
            if h and not (h == "back" or h.startswith(("nav:", "replace:", "push:")) or _IDENT.match(h)
                          or _motion_handler(h)):
                issues.append(Issue("error", nid, f"{ev}: bad handler {h!r}"))
        a = n.get("anim")
        if a and a.get("type") not in ANIM_TYPES:
            issues.append(Issue("error", nid, f"unknown animation {a.get('type')!r}"))
        if parent is not None and spec.parent and parent.get("type") not in spec.parent \
                and parent.get("type") != "Code":
            issues.append(Issue("warning", nid, f"{t} should be inside {' / '.join(spec.parent)}"))
    try:                                   # motion (triggers, timelines, state) and per-size variants
        from . import datawidgets as _DW, motion as _MO, variants_fd as _VF
        issues += _MO.validate(scr) + _VF.validate(scr) + _DW.validate(scr)
    except ImportError:
        pass
    return issues


def _motion_handler(h: str) -> bool:
    try:
        from .datawidgets import handler_ok as dw_ok
        from .motion import handler_ok
    except ImportError:
        return False
    return handler_ok(h) or dw_ok(h)


# ======================================================================================= patches
Patch = list   # list of primitive change dicts (JSON)


def _node_at(scr: Screen, parent_id: str | None, where: Where):
    if parent_id is None:
        return scr.tree
    parent = scr.find(parent_id)
    if parent is None:
        raise KeyError(parent_id)
    if where.slot is not None:
        v = (parent.get("slots") or {}).get(where.slot)
        if where.index is not None:
            return v[where.index] if isinstance(v, list) and 0 <= where.index < len(v) else None
        return v
    ch = parent.get("children") or []
    return ch[where.index] if where.index is not None and 0 <= where.index < len(ch) else None


def _put(scr: Screen, parent_id: str | None, where: Where, old, new) -> None:
    """Primitive: replace / insert (old None) / remove (new None) at a location."""
    if parent_id is None:
        if new is None:
            raise ValueError("the root cannot be removed")
        scr.tree = new
        return
    parent = scr.find(parent_id)
    if parent is None:
        raise KeyError(parent_id)
    if where.slot is not None and where.index is None:
        slots = parent.setdefault("slots", {})
        if new is None:
            slots.pop(where.slot, None)
        else:
            slots[where.slot] = new
        return
    if where.slot is not None:
        lst = parent.setdefault("slots", {}).setdefault(where.slot, [])
    else:
        lst = parent.setdefault("children", [])
    i = where.index if where.index is not None else len(lst)
    if old is None:
        lst.insert(i, new)
    elif new is None:
        del lst[i]
    else:
        lst[i] = new
    if where.slot is not None and not lst:
        parent["slots"].pop(where.slot, None)


def _set(scr: Screen, node_id: str, fld: str, key, value) -> None:
    node = scr.find(node_id)
    if node is None:
        raise KeyError(node_id)
    if fld in ("props", "events"):
        d = node.setdefault(fld, {})
        if value is None:
            d.pop(key, None)
        else:
            d[key] = value
    else:
        if value is None:
            node.pop(fld, None)
        else:
            node[fld] = value


def apply_patch(screen: Screen, patch: Patch) -> None:
    """Apply primitive changes in order (redo / remote apply)."""
    for ch in patch:
        op = ch["op"]
        if op == "put":
            _put(screen, ch["parent"], Where.from_json(ch.get("where")), copy.deepcopy(ch.get("old")),
                 copy.deepcopy(ch.get("new")))
        elif op == "set":
            _set(screen, ch["id"], ch["field"], ch.get("key"), copy.deepcopy(ch.get("new")))
        elif op == "screen":
            if ch.get("new") is None:
                screen.data.pop(ch["key"], None)
            else:
                screen.data[ch["key"]] = copy.deepcopy(ch["new"])
        else:
            raise ValueError(f"unknown patch op {op!r}")


def invert(patch: Patch) -> Patch:
    """The undo patch."""
    out = []
    for ch in reversed(patch):
        c = dict(ch)
        c["old"], c["new"] = ch.get("new"), ch.get("old")
        out.append(c)
    return out


def _do(screen: Screen, patch: Patch) -> Patch:
    apply_patch(screen, patch)
    return patch


def _put_ch(parent_id, where: Where, old, new) -> dict:
    return {"op": "put", "parent": parent_id, "where": where.to_json(), "old": copy.deepcopy(old),
            "new": copy.deepcopy(new)}


def _loc(screen: Screen, node_id: str) -> tuple[str | None, Where, dict]:
    node = screen.find(node_id)
    if node is None:
        raise KeyError(node_id)
    parent, where = screen.parent_of(node_id)
    return (parent.get("id") if parent else None), (where or Where()), node


def default_where(parent: dict, child_type: str | None = None) -> Where:
    """Where a new child goes: the end of the children list, else the first free slot (child/body first)."""
    spec = widget_spec(parent.get("type", ""), parent.get("ctor"))
    if spec is None:
        raise ValueError(f"unknown parent type {parent.get('type')!r}")
    if spec.children:
        return Where(None, len(parent.get("children") or []))
    slots = parent.get("slots") or {}
    order = sorted(spec.slots, key=lambda s: (s not in ("child", "body", "title", "label"), 0))
    if child_type:   # a slot that prefers this type (AppBar -> appBar, Drawer -> drawer)
        for s in spec.slots:
            acc = spec.slots[s].accepts
            if acc and child_type in acc and not slots.get(s):
                return Where(s, len(slots.get(s) or []) if spec.slots[s].multi else None)
    for s in order:
        ss = spec.slots[s]
        if ss.accepts and child_type and child_type not in ss.accepts:
            continue
        if ss.multi:
            return Where(s, len(slots.get(s) or []))
        if not slots.get(s):
            return Where(s, None)
    raise ValueError(f"{parent.get('type')} has no free place for a child")


def insert(screen: Screen, parent_id: str, node: dict | str, where: Where | None = None) -> Patch:
    """Insert *node* (a node dict or a widget type) into *parent_id*; ids/names are assigned."""
    if isinstance(node, str):
        node = new_node(node)
    node = copy.deepcopy(node)
    screen.assign_ids(node)
    parent = screen.find(parent_id)
    if parent is None:
        raise KeyError(parent_id)
    if where is None:
        where = default_where(parent, node.get("type"))
    spec = widget_spec(parent.get("type", ""), parent.get("ctor"))
    if parent.get("type") != "Code":
        if where.slot is not None:
            ss = spec.slots.get(where.slot) if spec else None
            if ss is None:
                raise ValueError(f"{parent.get('type')} has no slot {where.slot!r}")
            if ss.multi and where.index is None:
                where = Where(where.slot, len((parent.get("slots") or {}).get(where.slot) or []))
            if not ss.multi and where.index is not None:
                where = Where(where.slot, None)
        elif not (spec and spec.children):
            raise ValueError(f"{parent.get('type')} cannot have children")
    old = None
    if where.slot is not None and where.index is None:
        old = (parent.get("slots") or {}).get(where.slot)
        if old:
            raise ValueError(f"slot {where.slot!r} of {parent.get('type')} is not empty")
    return _do(screen, [_put_ch(parent_id, where, None, node)])


def delete(screen: Screen, node_id: str) -> Patch:
    pid, where, node = _loc(screen, node_id)
    if pid is None:
        raise ValueError("the root widget cannot be deleted")
    return _do(screen, [_put_ch(pid, where, node, None)])


def replace(screen: Screen, node_id: str, new: dict) -> Patch:
    pid, where, node = _loc(screen, node_id)
    new = copy.deepcopy(new)
    return _do(screen, [_put_ch(pid, where, node, new)])


def move(screen: Screen, node_id: str, new_parent_id: str, where: Where | None = None) -> Patch:
    """Move a node (index in the destination list counted before the move, like drag & drop)."""
    pid, old_where, node = _loc(screen, node_id)
    if pid is None:
        raise ValueError("the root widget cannot be moved")
    if any(n.get("id") == new_parent_id for n, *_ in walk_node(node)):
        raise ValueError("a widget cannot be moved into itself")
    target = screen.find(new_parent_id)
    if target is None:
        raise KeyError(new_parent_id)
    if where is None:
        where = default_where(target, node.get("type"))
    same_list = (pid == new_parent_id and old_where.slot == where.slot and old_where.index is not None
                 and where.index is not None)
    if same_list and where.index > old_where.index:
        where = Where(where.slot, where.index - 1)
    if same_list and where.index == old_where.index:
        return []
    patch = [_put_ch(pid, old_where, node, None)]
    apply_patch(screen, patch)
    try:
        p2 = insert(screen, new_parent_id, node, where)
    except Exception:
        apply_patch(screen, invert(patch))
        raise
    return patch + p2


def wrap(screen: Screen, node_id: str, wrapper: str | dict, props: dict | None = None) -> Patch:
    """Wrap a node with Padding / Center / Container / Expanded / Column ... (child slot or children list)."""
    pid, where, node = _loc(screen, node_id)
    w = new_node(wrapper) if isinstance(wrapper, str) else copy.deepcopy(wrapper)
    # a fresh wrapper: no template children / content
    w.pop("children", None)
    w["slots"] = {k: v for k, v in (w.get("slots") or {}).items() if k != "child"}
    if not w["slots"]:
        w.pop("slots")
    if props:
        w.setdefault("props", {}).update(props)
    spec = widget_spec(w["type"], w.get("ctor"))
    if spec is None:
        raise KeyError(w["type"])
    tmp = copy.deepcopy(node)
    if spec.children:
        w["children"] = [tmp]
    elif "child" in spec.slots:
        w.setdefault("slots", {})["child"] = tmp
    elif spec.slots:
        first = next(iter(spec.slots))
        w.setdefault("slots", {})[first] = [tmp] if spec.slots[first].multi else tmp
    else:
        raise ValueError(f"{w['type']} cannot hold a child")
    inner = {id(m) for m, *_ in walk_node(tmp)}
    for n, *_ in walk_node(w):          # ids for the wrapper (and its template parts), not the wrapped node
        if id(n) not in inner:
            n["id"] = screen.new_id()
    return _do(screen, [_put_ch(pid, where, node, w)])


def unwrap(screen: Screen, node_id: str) -> Patch:
    """Replace a wrapper by its only child; a multi-child node inside a list is replaced by its children."""
    pid, where, node = _loc(screen, node_id)
    kids = [c for c, _w in _iter_children(node)]
    if not kids:
        raise ValueError(f"{node.get('type')} has no child to keep")
    if len(kids) == 1:
        return _do(screen, [_put_ch(pid, where, node, kids[0])])
    if pid is None or where.index is None:
        raise ValueError("a widget with several children can only be unwrapped inside a list")
    patch = [_put_ch(pid, where, node, kids[0])]
    for i, k in enumerate(kids[1:], 1):
        patch.append(_put_ch(pid, Where(where.slot, where.index + i), None, k))
    return _do(screen, patch)


def duplicate(screen: Screen, node_id: str) -> Patch:
    """Copy a node (fresh ids and names) right after it; in a single slot the pair goes into a Column."""
    pid, where, node = _loc(screen, node_id)
    dup = screen.assign_ids(copy.deepcopy(node), fresh=True)
    if pid is not None and where.index is not None:
        return _do(screen, [_put_ch(pid, Where(where.slot, where.index + 1), None, dup)])
    raise ValueError("only widgets in a list (children / actions) can be duplicated in place - wrap it in a "
                     "Column or Row first")


def set_prop(screen: Screen, node_id: str, key: str, value) -> Patch:
    node = screen.find(node_id)
    if node is None:
        raise KeyError(node_id)
    spec = widget_spec(node.get("type", ""), node.get("ctor"))
    if spec and key in spec.props:
        value = normalize_value(spec.props[key].kind, value)
    old = (node.get("props") or {}).get(key)
    if old == value:
        return []
    return _do(screen, [{"op": "set", "id": node_id, "field": "props", "key": key, "old": copy.deepcopy(old),
                         "new": copy.deepcopy(value)}])


def set_props(screen: Screen, node_id: str, values: dict) -> Patch:
    patch: Patch = []
    for k, v in values.items():
        patch += set_prop(screen, node_id, k, v)
    return patch


def set_event(screen: Screen, node_id: str, event: str, handler: str | None) -> Patch:
    node = screen.find(node_id)
    if node is None:
        raise KeyError(node_id)
    old = (node.get("events") or {}).get(event)
    handler = handler or None
    if old == handler:
        return []
    return _do(screen, [{"op": "set", "id": node_id, "field": "events", "key": event, "old": old,
                         "new": handler}])


def _set_field(screen: Screen, node_id: str, fld: str, value) -> Patch:
    node = screen.find(node_id)
    if node is None:
        raise KeyError(node_id)
    old = node.get(fld)
    if old == value:
        return []
    return _do(screen, [{"op": "set", "id": node_id, "field": fld, "key": None, "old": copy.deepcopy(old),
                         "new": copy.deepcopy(value)}])


def set_anim(screen: Screen, node_id: str, anim: dict | None) -> Patch:
    return _set_field(screen, node_id, "anim", anim or None)


def rename(screen: Screen, node_id: str, name: str | None) -> Patch:
    if name and (not _IDENT.match(name) or name in DART_KEYWORDS):
        raise ValueError(f"{name!r} is not a Dart identifier")
    if name and any(n.get("name") == name and n.get("id") != node_id for n, *_ in screen.walk()):
        raise ValueError(f"the name {name!r} is already used")
    return _set_field(screen, node_id, "name", name or None)


def set_ctor(screen: Screen, node_id: str, ctor: str | None) -> Patch:
    return _set_field(screen, node_id, "ctor", ctor or None)


def set_screen(screen: Screen, key: str, value) -> Patch:
    """Screen-level field (name, route, theme, assets, fonts, imports, code)."""
    old = screen.data.get(key)
    if old == value:
        return []
    return _do(screen, [{"op": "screen", "key": key, "old": copy.deepcopy(old), "new": copy.deepcopy(value)}])


# ====================================================================================== comparing
def strip_ids(node, keep_names: bool = True):
    """Deep copy without ids (to compare trees structurally)."""
    if isinstance(node, list):
        return [strip_ids(c, keep_names) for c in node]
    if not isinstance(node, dict):
        return node
    n = clean_node(node) if "type" in node else dict(node)
    out = {}
    for k, v in n.items():
        if k == "id" or (k == "name" and not keep_names):
            continue
        if k == "slots":
            out[k] = {s: strip_ids(c, keep_names) for s, c in v.items()}
        elif k == "children":
            out[k] = [strip_ids(c, keep_names) for c in v]
        else:
            out[k] = v
    return out


def find_screens(folder) -> list[Path]:
    """Every *.fscreen.json under a project folder (build/ and dot folders skipped)."""
    out = []
    root = Path(folder)
    for p in root.rglob("*" + SCREEN_EXT):
        rel = p.relative_to(root).parts
        if any(part.startswith(".") or part in ("build", "node_modules") for part in rel[:-1]):
            continue
        out.append(p)
    return sorted(out)


if __name__ == "__main__":
    if "--catalog-json" in sys.argv:
        sys.stdout.write(json.dumps(catalog_json(), indent=1) + "\n")
    else:
        cats = categories()
        print(f"{len(CATALOG)} widgets")
        for c, ts in cats.items():
            print(f"  {c}: {', '.join(ts)}")
