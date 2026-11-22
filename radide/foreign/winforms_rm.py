"""RadIDE.Controls (the RAD Modern Rm* controls, radide/runtimes/dotnet/RadIDE.Controls, MIT) inside Visual Studio
WinForms projects - C# and VB.NET - that RAD IDE opens in place (winforms_cs.py / winforms_vb.py).

* designer code <-> neutral controls: ``Me.RmButton1 = New RadIDE.Controls.RmButton()`` is read as the neutral
  RmButton (when its designer package is installed) with the properties of the .NET control map
  (radide/deploy/native/dotnet/RadIDE.Controls.controls.json: "Kind" <-> ``Kind = RadIDE.Controls.RmButtonKind.Accent``),
  and new / changed Rm controls are written back with the same table;
* the reference: when a form uses an Rm control, the project gets ``lib\\RadIDE.Controls.dll`` (the build for its
  target framework: .NET Framework 4.x -> net48, .NET 8+ -> net8.0-windows) and a ``<Reference>`` with a HintPath,
  so the project builds in RAD IDE, with dotnet / MSBuild and in Visual Studio (whose designer shows the controls too).
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

NS = "RadIDE.Controls"
LIB = "RadIDE.Controls"
ITEM_ARGS = f"{NS}.RmItemEventArgs"
# events whose delegate is EventHandler<RmItemEventArgs> (the others are EventHandler / WinForms delegates)
ITEM_EVENTS = ("ItemClick", "DropDownItemClicked", "TabClosing", "PanelClick", "ButtonCellClick", "NodeClick",
               "NodeExpanding", "NodeChecked", "WindowClosed", "ActiveWindowChanged")
_MAP: dict | None = None


def control_map() -> dict:
    """Rm type -> control map entry (props / events) of RadIDE.Controls."""
    global _MAP
    if _MAP is None:
        try:
            from ..deploy.native.dotnet_winforms import control_map as cm
            _MAP = {k: v for k, v in cm().items() if k.startswith("Rm") and isinstance(v, dict) and v.get("reference") == LIB}
        except Exception:  # noqa: BLE001
            _MAP = {}
    return _MAP


def _installed(nt: str) -> bool:
    from ..controls import CONTROL_TYPES
    t = CONTROL_TYPES.get(nt)
    if t is None:
        return False
    try:
        from ..components import is_missing
        return not is_missing(nt)
    except Exception:  # noqa: BLE001
        return True


def neutral(wtype: str) -> str | None:
    """The neutral Rm type of a designer type (RadIDE.Controls.RmButton, global::..., or RmButton with a using)."""
    t = (wtype or "").replace("global::", "")
    short = t.split(".")[-1]
    if short not in control_map() or not (t == short or t == f"{NS}.{short}"):
        return None
    return short if _installed(short) else None


def wf_type(nt: str) -> str | None:
    return f"{NS}.{nt}" if nt in control_map() else None


def is_rm(nt: str) -> bool:
    return nt in control_map()


def is_component(nt: str) -> bool:
    return bool((control_map().get(nt) or {}).get("nonvisual"))


def event_signature(event: str) -> tuple[str, str] | None:
    """(delegate, EventArgs type) of an item event of the library."""
    if event in ITEM_EVENTS:
        return f"System.EventHandler<{ITEM_ARGS}>", ITEM_ARGS
    return None


# ---------------------------------------------------------------------- read
def read_props(nt: str, name: str, v, p: dict) -> None:
    """Mapped properties of an Rm control from designer code; v(owner, prop) = parsed value (winforms_cs.wf_value)."""
    from .winforms_cs import _color_hex, _enum_last
    for fprop, spec in ((control_map().get(nt) or {}).get("props") or {}).items():
        net, _, kind = str(spec).partition(":")
        x = v(name, net)
        if x is None:
            continue
        if kind.startswith("enum:"):
            val = _enum_last(x)
            if not val:
                continue
        elif kind == "color":
            val = _color_hex(x)
        elif kind == "date":
            if isinstance(x, tuple) and len(x) > 1 and all(isinstance(a, (int, float)) for a in x[1:4]):
                val = f"{int(x[1]):04d}-{int(x[2]):02d}-{int(x[3]):02d}"
            elif isinstance(x, str):
                val = x
            else:
                continue
        elif isinstance(x, (str, bool, int, float)):
            val = x
            if kind == "json" and isinstance(x, str) and x.strip()[:1] in "[{":
                try:
                    val = json.loads(x)
                except ValueError:
                    val = x
        else:
            continue
        p[fprop] = val


# ---------------------------------------------------------------------- write
def value_code(renderer, nt: str, fprop: str, value) -> str | None:
    """Designer code of a property value (C# or VB through the renderer's dialect); None = remove the line."""
    spec = ((control_map().get(nt) or {}).get("props") or {}).get(fprop)
    if spec is None or value is None or value == "":
        return None
    d = renderer.doc.d
    _net, _, kind = str(spec).partition(":")
    if kind.startswith("enum:"):
        member = re.sub(r"[^A-Za-z0-9_]", "", str(value))
        return f"{kind[5:]}.{member}" if member else None
    if kind == "color":
        return renderer.v_color(str(value)) if re.fullmatch(r"#[0-9A-Fa-f]{6}", str(value)) else None
    if kind == "date":
        m = re.match(r"(\d{4})-(\d\d)-(\d\d)(?:[ T](\d\d):(\d\d)(?::(\d\d))?)?", str(value))
        if not m:
            return None
        nums = [int(g or 0) for g in m.groups()]
        return d.new("System.DateTime", ", ".join(str(n) for n in nums) + ", 0")
    if isinstance(value, bool):
        return d.lit_bool(value)
    if isinstance(value, (list, dict)):
        return d.lit_str(json.dumps(value, ensure_ascii=False))
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() and kind != "float" else repr(value)
    if isinstance(value, int):
        return str(value)
    return d.lit_str(str(value))


def _defaults(nt: str, name: str) -> dict:
    from ..controls import CONTROL_TYPES
    try:
        return CONTROL_TYPES[nt].default_props(name)
    except Exception:  # noqa: BLE001
        return {}


def new_props(renderer, c) -> dict[str, str]:
    """{net property: code} of a new Rm control (values that differ from the package defaults)."""
    out: dict[str, str] = {}
    dflt = _defaults(c.type, c.name)
    for fprop, spec in ((control_map().get(c.type) or {}).get("props") or {}).items():
        if fprop not in c.props or c.props[fprop] == dflt.get(fprop, None):
            continue
        code = value_code(renderer, c.type, fprop, c.props[fprop])
        if code is not None:
            out[str(spec).partition(":")[0]] = code
    return out


def update_props(renderer, c, changed: set) -> set:
    """Writes the changed mapped properties of an existing Rm control; returns the handled neutral names."""
    props = (control_map().get(c.type) or {}).get("props") or {}
    done = set()
    for fprop in sorted(changed & set(props)):
        renderer.set_prop(c.name, str(props[fprop]).partition(":")[0], value_code(renderer, c.type, fprop, c.props.get(fprop)))
        done.add(fprop)
    return done


# ---------------------------------------------------------------------- the project reference
def project_file_of(designer: Path) -> Path | None:
    for folder in [designer.parent, *designer.parents][:6]:
        hits = sorted(folder.glob("*.csproj")) + sorted(folder.glob("*.vbproj"))
        if hits:
            return hits[0]
    return None


def target_of(proj_text: str) -> str:
    """"net48" for .NET Framework projects, "net8.0-windows" for .NET 8+, "" when the library cannot be used."""
    m = re.search(r"<TargetFrameworks?>([^<]+)</TargetFrameworks?>", proj_text)
    if m:
        tfm = m.group(1).split(";")[0].strip().lower()
        if re.fullmatch(r"net4\d+", tfm):
            return "net48"
        n = re.match(r"net(\d+)\.", tfm)
        if n and int(n.group(1)) >= 8:
            return "net8.0-windows"
        return ""
    if re.search(r"<TargetFrameworkVersion>v4\.", proj_text):
        return "net48"
    return ""


def library_project() -> Path | None:
    from ..deploy.native.dotnet_winforms import control_map as cm
    ref = (cm().get("__references__") or {}).get(LIB) or {}
    p = Path(ref.get("project") or "")
    return p if p.is_file() else None


def library_dll(target: str, log=print) -> Path | None:
    """The library built for a target ("net48": csc, no SDK; "net8.0-windows": dotnet build), cached."""
    from ..deploy.native import dotnet_winforms as D
    proj = library_project()
    if proj is None:
        return None
    if target == "net48":
        return D.library_dll(proj, LIB, log)
    import hashlib
    h = hashlib.sha256()
    for p in D._library_sources(proj) + [proj]:
        h.update(p.name.encode("utf-8"))
        h.update(p.read_bytes())
    out = D._local() / "cache" / "dotnet" / LIB / h.hexdigest()[:16] / target / f"{LIB}.dll"
    if out.is_file():
        return out
    dn = D.dotnet()
    if not dn or not D._sdk_dirs():
        log("RadIDE.Controls: the .NET SDK is needed to build the library for " + target)
        return None
    work = out.parent.parent / "src"
    copy = D._copy_library(proj, work, log)
    code, text = D._run([dn, "build", str(copy), "-c", "Release", "-nologo", "-v", "q", f"-p:RadIDEControlsTargets={target}",
                         "-o", str(out.parent)], copy.parent, log, env=D._quiet_env())
    shutil.rmtree(work, ignore_errors=True)
    if code != 0 or not out.is_file():
        log("RadIDE.Controls: build failed: " + " | ".join(D._errors(text, copy.parent)))
        return None
    return out


def ensure_reference(designer: Path, log=print) -> str | None:
    """Give the project of a form lib\\RadIDE.Controls.dll + a <Reference> (once). Returns a report line or None."""
    proj = project_file_of(Path(designer))
    if proj is None:
        return "RadIDE.Controls: no .csproj / .vbproj found - add a reference to RadIDE.Controls.dll yourself"
    text = proj.read_text(encoding="utf-8-sig", errors="replace")
    if re.search(r'Include="RadIDE\.Controls[",\s]', text) or "RadIDE.Controls.csproj" in text:
        return None
    target = target_of(text)
    if not target:
        return f"RadIDE.Controls: {proj.name} targets a framework the library does not support (.NET Framework 4.x or .NET 8+)"
    dll = library_dll(target, log)
    if dll is None:
        return "RadIDE.Controls: the library could not be built - reference not added"
    lib = proj.parent / "lib"
    lib.mkdir(exist_ok=True)
    shutil.copy2(dll, lib / dll.name)
    nl = "\r\n" if "\r\n" in text else "\n"
    item = (f"  <ItemGroup>{nl}    <Reference Include=\"{LIB}\">{nl}      <HintPath>lib\\{LIB}.dll</HintPath>{nl}"
            f"    </Reference>{nl}  </ItemGroup>{nl}")
    i = text.rfind("</Project>")
    if i < 0:
        return f"RadIDE.Controls: {proj.name} is not an MSBuild project file"
    proj.write_text(text[:i] + item + text[i:], encoding="utf-8")
    return f"RadIDE.Controls: lib\\{LIB}.dll ({target}) added to {proj.name}"


__all__ = ["ITEM_EVENTS", "NS", "control_map", "ensure_reference", "event_signature", "is_component", "is_rm",
           "library_dll", "neutral", "new_props", "read_props", "target_of", "update_props", "value_code", "wf_type"]
