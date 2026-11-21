"""VB6 .frm mapping read from the component manifests' ``"vb6"`` sections (docs/COMPONENTS.md).

::

    "vb6": {"class": "MSComctlLib.ProgressBar",            written for a new control (frm_writer)
            "library": "MSComctlLib",                       OCX library of that class ("Object =" line)
            "imports": ["mscomctllib.progressbar", ...],    VB6 / ActiveX classes imported as this control
            "approx": [...],                                the imports that are approximations (a warning)
            "properties": {"Minimum": "Min", ...},          neutral -> VB6 name of plain integer properties
            "object": "{GUID}#1.0#0; STARS.OCX"}            'Object =' line of a third-party OCX library

Used by radide/importers/vb6_import.py (CLASS_MAP, APPROX) and radide/foreign/frm_writer.py (NEW_CLASS). The
built-in packages give the tables; installed packages with a ``vb6`` section are added when they are loaded.

**Package controls** (installed component packages) are written into a .frm as

* the VB6 class of their ``vb6`` section (``"class": "StarLib.StarRating"``, ``"library"`` + ``"object"`` for
  the OCX line), or
* without one, a **UserControl reference** ``<Project>.<Type>`` (``Begin Project1.RatingBar rate1``):
  :func:`usercontrol_source` writes ``<Type>.ctl`` - a VB6 UserControl with the manifest's properties
  (PropertyBag persistence), events and method stubs - and it is added to the .vbp (``UserControl=``), so VB6
  loads the form;

and their manifest properties are written as property lines (``Value = 3``, ``StarColor = &H0000B4FF&``,
``ReadOnly = -1 'True``; :func:`prop_edits`), the way VB6 saves a UserControl's PropertyBag. Importing reads
them back (:func:`import_type`, :func:`read_props`): ``<anything>.<Type>`` of an installed package becomes
that package's control. Pure Python (no Qt).
"""
from __future__ import annotations


def _packages() -> list:
    """Built-in packages first, then the installed ones registered in CONTROL_TYPES (they may add mappings)."""
    from . import builtin_packages, package_of
    pkgs = list(builtin_packages().values())
    seen = {id(p) for p in pkgs}
    try:
        from ..controls import CONTROL_TYPES
        for name in list(CONTROL_TYPES):
            pkg = package_of(name)
            if pkg is not None and id(pkg) not in seen:
                seen.add(id(pkg))
                pkgs.append(pkg)
    except ImportError:
        pass
    return pkgs


def _section(pkg) -> dict:
    v = pkg.manifest.get("vb6")
    return v if isinstance(v, dict) else {}


def import_map() -> dict[str, str]:
    """lower-case VB6 class -> control type (the first package that claims a class keeps it)."""
    out: dict[str, str] = {}
    for pkg in _packages():
        for cls in _section(pkg).get("imports") or []:
            out.setdefault(str(cls).lower(), pkg.name)
    return out


def approx_classes() -> set[str]:
    return {str(c).lower() for pkg in _packages() for c in _section(pkg).get("approx") or []}


def new_class_map() -> dict[str, str]:
    """control type -> VB6 class written for a new control."""
    return {pkg.name: str(_section(pkg)["class"]) for pkg in _packages() if _section(pkg).get("class")}


def property_name(type_name: str, prop: str) -> str | None:
    """VB6 name of a plain integer property of *type_name* (``"vb6": {"properties": {...}}``), or None."""
    from . import package_of
    pkg = package_of(type_name)
    if pkg is None:
        return None
    m = _section(pkg).get("properties") or {}
    v = m.get(prop) if isinstance(m, dict) else None
    return str(v) if v else None


def new_class(type_name: str) -> str | None:
    """VB6 class written for a new control of *type_name* (its package's ``vb6.class``), or None."""
    from . import package_of
    pkg = package_of(type_name)
    v = _section(pkg).get("class") if pkg is not None else None
    return str(v) if v else None


def object_line(lib: str) -> tuple[str, str] | None:
    """(GUID, OCX file) of a third-party OCX library a package declares (``"library"`` + ``"object"``)."""
    for pkg in _packages():
        sec = _section(pkg)
        if str(sec.get("library") or "").lower() == str(lib).lower() and sec.get("object"):
            guid, _, ocx = str(sec["object"]).partition(";")
            return guid.strip(), ocx.strip()
    return None


def _component(type_name: str):
    from . import package_of
    pkg = package_of(type_name)
    return pkg if pkg is not None and not pkg.builtin else None


def import_type(cls: str) -> str | None:
    """Control type of an imported VB6 class (lower or any case): a package's ``vb6.imports``, else
    ``<Library or Project>.<Type>`` of an installed component package (a UserControl reference written by
    the IDE, or the package's own OCX class)."""
    c = str(cls).lower()
    t = import_map().get(c)
    if t:
        return t
    if "." not in c:
        return None
    tail = c.rsplit(".", 1)[1]
    from ..controls import CONTROL_TYPES
    for name in list(CONTROL_TYPES):
        if name.lower() == tail and _component(name) is not None:
            return name
    return None


def _vb_name(type_name: str, prop: str) -> str:
    return property_name(type_name, prop) or prop


def _defs(type_name: str) -> dict:
    from ..controls import CONTROL_TYPES
    ct = CONTROL_TYPES.get(type_name)
    return {d.name: d for d in ct.extra} if ct is not None else {}


def frm_value(d, value) -> str | None:
    """A manifest property value as a .frm property line value (None = cannot be stored)."""
    k = d.kind
    try:
        if k == "bool":
            return "-1  'True" if value else "0   'False"
        if k == "int":
            return str(int(value))
        if k == "float":
            v = float(value)
            return str(int(v)) if v.is_integer() else repr(v)
        if k == "color":
            s = str(value or "").lstrip("#")
            if len(s) != 6:
                return None
            r, g, b = s[0:2], s[2:4], s[4:6]
            return f"&H00{b.upper()}{g.upper()}{r.upper()}&"
    except (TypeError, ValueError):
        return None
    if k in ("custom", "menu"):
        return None
    s = str(value if value is not None else "")
    if "\n" in s or len(s) > 255:
        return None
    return '"' + s.replace('"', '""') + '"'


def prop_edits(type_name: str, prop: str, value) -> list | None:
    """[(VB6 property, formatted value | None)] of a component package property (None value = the default:
    the line is removed, like VB6's PropertyBag), or None when it is not a package property / cannot be
    stored."""
    if _component(type_name) is None:
        return None
    d = _defs(type_name).get(prop)
    if d is None or (d.meta and d.meta.get("designOnly")):
        return None
    if value == d.default:
        return [(_vb_name(type_name, prop), None)]
    v = frm_value(d, value)
    return None if v is None else [(_vb_name(type_name, prop), v)]


def read_props(type_name: str, frm_props: dict) -> dict:
    """The manifest property values found in an imported .frm block (*frm_props*: lower-case keys, values
    parsed by the importer: str / int / float)."""
    out = {}
    if _component(type_name) is None:
        return out
    for name, d in _defs(type_name).items():
        key = _vb_name(type_name, name).lower()
        if key not in frm_props:
            continue
        v = frm_props[key]
        try:
            if d.kind == "bool":
                out[name] = (int(v) != 0) if not isinstance(v, str) else v.strip().lower() in ("true", "-1", "1")
            elif d.kind == "int":
                out[name] = int(v)
            elif d.kind == "float":
                out[name] = float(v)
            elif d.kind == "color":
                if isinstance(v, int) and not v & 0x80000000:
                    out[name] = f"#{v & 0xFF:02X}{(v >> 8) & 0xFF:02X}{(v >> 16) & 0xFF:02X}"
            elif not isinstance(v, tuple):
                out[name] = str(v)
        except (TypeError, ValueError):
            continue
    return out


def _vb_type(d) -> tuple[str, str]:
    """(VB6 type, default literal) of a manifest property for the UserControl stand-in."""
    if d.kind == "bool":
        return "Boolean", "True" if d.default else "False"
    if d.kind == "int":
        return "Long", str(int(d.default or 0))
    if d.kind == "float":
        return "Double", repr(float(d.default or 0))
    if d.kind == "color":
        v = frm_value(d, d.default)
        return "OLE_COLOR", v if v else "&H0&"
    s = str(d.default if d.default is not None else "")
    return "String", '"' + s.replace('"', '""').replace("\n", " ") + '"'


def usercontrol_source(type_name: str, newline: str = "\r\n") -> str:
    """A VB6 UserControl (.ctl) standing in for component package *type_name* in VB6 itself: its manifest
    properties (Property Get/Let, saved with the PropertyBag under the names the .frm uses), its events and
    its methods (stubs). Drawn as a labelled box. RAD IDE runs the form with the package's runtime."""
    from ..controls import CONTROL_TYPES
    pkg = _component(type_name)
    ct = CONTROL_TYPES[type_name]
    w, h = ct.size
    defs = [d for d in ct.extra if not (d.meta and d.meta.get("designOnly")) and frm_value(d, d.default) is not None]
    L = ["VERSION 5.00", f"Begin VB.UserControl {type_name} ",
         f"   ClientHeight    =   {max(1, h) * 15}", "   ClientLeft      =   0", "   ClientTop       =   0",
         f"   ClientWidth     =   {max(1, w) * 15}", f"   ScaleHeight     =   {max(1, h) * 15}",
         f"   ScaleWidth      =   {max(1, w) * 15}", "End",
         f'Attribute VB_Name = "{type_name}"', "Attribute VB_GlobalNameSpace = False",
         "Attribute VB_Creatable = True", "Attribute VB_PredeclaredId = False", "Attribute VB_Exposed = False",
         "Option Explicit",
         f"' Stand-in of the RAD IDE component package {type_name} {pkg.version if pkg else ''} (written by RAD IDE):",
         "' its properties are kept in the .frm; RAD IDE runs the form with the package's own runtime.", ""]
    for e in pkg.manifest.get("events") or [] if pkg else []:
        if isinstance(e, dict) and e.get("name"):
            L.append(f"Event {e['name']}()")
    L.append("")
    for d in defs:
        t, dv = _vb_type(d)
        L += [f"Private m_{d.name} As {t}", f"Const m_def_{d.name} = {dv}"]
    L.append("")
    for d in defs:
        t, _dv = _vb_type(d)
        vb = _vb_name(type_name, d.name)
        L += [f"Public Property Get {vb}() As {t}", f"    {vb} = m_{d.name}", "End Property", "",
              f"Public Property Let {vb}(ByVal New_{vb} As {t})", f"    m_{d.name} = New_{vb}",
              f'    PropertyChanged "{vb}"', "    UserControl.Refresh", "End Property", ""]
    for m in pkg.manifest.get("methods") or [] if pkg else []:
        if not isinstance(m, dict) or not m.get("name"):
            continue
        sig = str(m.get("signature") or m["name"] + "()")
        args = sig[sig.find("(") + 1:sig.rfind(")")] if "(" in sig else ""
        params = ", ".join(f"ByVal {a.strip().split('=')[0].strip()} As Variant" for a in args.split(",") if a.strip())
        L += [f"Public Sub {m['name']}({params})", f"    ' {str(m.get('description') or '')}".rstrip(), "End Sub", ""]
    L += ["Private Sub UserControl_InitProperties()"] + [f"    m_{d.name} = m_def_{d.name}" for d in defs] + \
         ["End Sub", "", "Private Sub UserControl_ReadProperties(PropBag As PropertyBag)"] + \
         [f'    m_{d.name} = PropBag.ReadProperty("{_vb_name(type_name, d.name)}", m_def_{d.name})' for d in defs] + \
         ["End Sub", "", "Private Sub UserControl_WriteProperties(PropBag As PropertyBag)"] + \
         [f'    Call PropBag.WriteProperty("{_vb_name(type_name, d.name)}", m_{d.name}, m_def_{d.name})' for d in defs] + \
         ["End Sub", "", "Private Sub UserControl_Paint()", "    UserControl.Cls",
          "    UserControl.Line (0, 0)-(UserControl.ScaleWidth - 15, UserControl.ScaleHeight - 15), , B",
          f'    UserControl.CurrentX = 60: UserControl.CurrentY = 30: UserControl.Print Ambient.DisplayName & " ({type_name})"',
          "End Sub", ""]
    return newline.join(L)


__all__ = ["import_map", "approx_classes", "new_class_map", "property_name", "new_class", "object_line",
           "import_type", "frm_value", "prop_edits", "read_props", "usercontrol_source"]
