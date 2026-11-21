"""Animations (motion presets) and layout sizes of WinForms forms opened from Visual Studio projects (plan
MOTION_VARIANTS_FOLDABLES, slice D, phase 2).

``Form1.Designer.cs`` / ``.vb`` cannot hold RAD IDE data and is never touched for this: the animations
(``form.extra["animations"]`` / ``["motion"]``), the layout sizes (``form.extra["variants"]``) and the
per-control size overrides are kept in the sidecar ``Form1.radide.json`` next to it, and a generated
partial class ``Form1.RadFx.cs`` / ``Form1.RadFx.vb`` plays them (SDK-style projects compile every file of
the folder):

* a nested ``RadFxEngine`` (System.Windows.Forms.Timer, 15 ms) with the same keyframes / easings / relative
  values as the Python runtime; triggers Click / MouseEnter / MouseLeave / Timer / chains / SetVisible;
  no transparency or transforms in WinForms: fade = colour blend into the parent, rotate = wobble, scale /
  flip = Bounds around the centre (``motion.expand(form, "winforms")`` reports these fallbacks);
* layout sizes are applied on the form's ``Layout`` event (controls a size moves are placed by the engine
  with their per-size Anchor spec; Text / Visible / colours / font size are set and restored);
* reduced motion: ``RADIDE_REDUCED_MOTION=1`` or Windows' "Show animations" off (SPI_GETCLIENTAREAANIMATION);
* ``OnLoad`` is overridden to call ``RadFxAttach()`` - unless the user's Form1.cs / Form1.vb overrides it
  already: then the report says to call ``RadFxAttach()`` there.

API for user code: ``BeginAnimation("fx1")``, ``StopAnimation("fx1")``, ``SetVisible("lblInfo", false)``,
``CurrentSizes``.  ``RADIDE_FX_SELFTEST=<file>`` (tests): writes the controls' state after 1.5 s, clicks the
controls listed in ``RADIDE_FX_CLICK``, writes again after 0.15 s and 1.2 s and closes the form.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..fxtargets import fx_plan, managed_controls, trigger_of, variant_plan, when_tuple

MARK = "RAD IDE: animations / layout sizes"
SIDE_KEYS = ("animations", "motion", "variants")


# ============================================================================================ sidecar
def sidecar_path(designer: Path) -> Path:
    name = Path(designer).name
    stem = re.sub(r"\.designer\.(cs|vb)$", "", name, flags=re.I)
    return Path(designer).with_name(f"{stem}.radide.json")


def partial_path(designer: Path, lang: str) -> Path:
    name = Path(designer).name
    stem = re.sub(r"\.designer\.(cs|vb)$", "", name, flags=re.I)
    return Path(designer).with_name(f"{stem}.RadFx.{lang}")


def load_sidecar(form, designer) -> None:
    """Form1.radide.json -> form.extra / Control.variants (nothing when missing or broken)."""
    p = sidecar_path(designer)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(data, dict):
        return
    for k in SIDE_KEYS:
        if k in data:
            form.extra[k] = data[k]
    for name, ov in (data.get("controls") or {}).items():
        c = form.find(name)
        if c is not None and isinstance(ov, dict):
            c.variants = ov


def _sidecar_data(form) -> dict:
    data = {k: form.extra[k] for k in SIDE_KEYS if form.extra.get(k)}
    ctl = {c.name: c.variants for c in form.controls if getattr(c, "variants", None)}
    if ctl:
        data["controls"] = ctl
    return data


def save(form, designer, lang: str, code_text: str | None = None) -> list[str]:
    """Writes / updates / removes Form1.radide.json and Form1.RadFx.cs|vb; returns report lines."""
    designer = Path(designer)
    data = _sidecar_data(form)
    side, part = sidecar_path(designer), partial_path(designer, lang)
    report: list[str] = []
    if not data:
        for p in (side, part):
            if p.is_file() and (p is side or MARK in p.read_text(encoding="utf-8", errors="replace")):
                p.unlink()
                report.append(f"removed {p.name} (no animations / layout sizes left)")
        return report
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if not side.is_file() or side.read_text(encoding="utf-8", errors="replace") != text:
        side.write_text(text, encoding="utf-8")
        report.append(f"wrote {side.name}")
    if code_text is None:
        code = designer.with_name(re.sub(r"\.designer\.", ".", designer.name, flags=re.I))
        code_text = code.read_text(encoding="utf-8", errors="replace") if code.is_file() else ""
    designer_text = designer.read_text(encoding="utf-8-sig", errors="replace")
    src, notes = generate(form, designer_text, code_text, lang)
    if part.is_file() and part.read_text(encoding="utf-8", errors="replace") == src:
        return report + notes
    part.write_text(src, encoding="utf-8")
    return report + [f"wrote {part.name}"] + notes


def overrides_onload(code_text: str, lang: str) -> bool:
    if lang == "vb":
        return bool(re.search(r"Overrides\s+Sub\s+OnLoad\s*\(", code_text or "", re.I))
    return bool(re.search(r"override\s+void\s+OnLoad\s*\(", code_text or ""))


# ============================================================================================ data
def _ns_class(designer_text: str, lang: str, form_name: str) -> tuple[str, str, bool]:
    """(namespace, class name, file-scoped namespace) of the Designer file."""
    if lang == "vb":
        m = re.search(r"^\s*Namespace\s+([\w.]+)", designer_text, re.M | re.I)
        c = re.search(r"Partial\s+(?:Public\s+|Friend\s+)?Class\s+(\w+)", designer_text, re.I)
        return (m.group(1) if m else ""), (c.group(1) if c else form_name), False
    m = re.search(r"^\s*namespace\s+([\w.]+)\s*(;|\{|$)", designer_text, re.M)
    c = re.search(r"partial\s+class\s+(\w+)", designer_text)
    return (m.group(1) if m else ""), (c.group(1) if c else form_name), bool(m and m.group(2) == ";")


def _key(k) -> tuple:
    """keyframe -> (ms, kind, a, b, c, s, ease) like the Ring runtime."""
    ms, v = int(k[0]), k[1]
    ease = str(k[2]) if len(k) > 2 and k[2] else ""
    if isinstance(v, bool):
        return ms, 5, 1.0 if v else 0.0, 0.0, 0.0, "", ease
    if isinstance(v, dict):
        if "reveal" in v:
            return ms, 4, float(v.get("reveal", 1)), 0.0, 0.0, "", ease
        return ms, 1, float(v.get("m", 1)), float(v.get("d", 0)), float(v.get("f", 0)), str(v.get("of") or ""), ease
    if isinstance(v, str):
        return (ms, 3, 0.0, 0.0, 0.0, "", ease) if v == "$parent" else (ms, 2, 0.0, 0.0, 0.0, v, ease)
    return ms, 0, float(v), 0.0, 0.0, "", ease


def _num(v: float) -> str:
    v = float(v)
    return str(int(v)) if v.is_integer() else repr(round(v, 4))


def _cs_str(s) -> str:
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _vb_str(s) -> str:
    return '"' + str(s).replace('"', '""') + '"'


def setup_calls(form) -> list[tuple]:
    """The engine set-up as neutral calls: (method, [args]) - written in C# or VB by generate()."""
    calls: list[tuple] = []
    plan = fx_plan(form, "winforms")
    if plan:
        respect = bool(plan.get("reduced_motion", True))
        calls.append(("Respect", [respect]))
        for sb in plan["storyboards"]:
            t = trigger_of(plan, sb["fx"])
            calls.append(("Sb", [sb["fx"], sb["target"], int(sb["duration"]), int(sb["count"]), bool(sb["repeat"]),
                                 bool(sb["autoreverse"]), int(sb.get("delayMs", 0)), t["on"],
                                 t.get("source") or "", int(t.get("intervalMs") or 0), t.get("leave", "reverse"),
                                 ",".join(sb["chain"])]))
            for _t, prop, keys in sb["tracks"]:
                calls.append(("Track", [sb["fx"], prop]))
                for k in keys:
                    calls.append(("Key", [sb["fx"], *_key(k)]))
    vplan = variant_plan(form)
    if vplan:
        offset = int((form.extra.get("winforms") or {}).get("offset", 0) or 0)
        calls.append(("Offset", [offset]))
        for s in vplan["sizes"]:
            mw, xw, mh, xh, orient, posture, span, fold = when_tuple(s.get("when") or {})
            calls.append(("Size", [s["id"], -1.0 if mw is None else mw, -1.0 if xw is None else xw,
                                   -1.0 if mh is None else mh, -1.0 if xh is None else xh, orient or "",
                                   posture or "", span or "", fold or ""]))
        for name, spec in (vplan.get("base") or {}).items():
            calls.append(("Base", [name, *[float(x) for x in spec]]))
        for vid, ctl in (vplan.get("controls") or {}).items():
            for name, ov in ctl.items():
                if ov.get("place") is not None:
                    calls.append(("Place", [name, vid, *[float(x) for x in ov["place"]]]))
                for k, v in (ov.get("props") or {}).items():
                    calls.append(("Prop", [name, vid, k, _prop_text(k, v)]))
        for vid, ov in (vplan.get("form") or {}).items():
            for k, v in ov.items():
                calls.append(("Prop", ["", vid, k, _prop_text(k, v)]))
    return calls


def _prop_text(k, v) -> str:
    if isinstance(v, bool):
        return "True" if v else "False"
    return str(v)


def _arg_cs(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return _num(v) + ("" if isinstance(v, int) else "")
    return _cs_str(v)


def _arg_vb(v) -> str:
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, (int, float)):
        return _num(v)
    return _vb_str(v)


def generate(form, designer_text: str, code_text: str, lang: str) -> tuple[str, list[str]]:
    """(source of Form1.RadFx.cs|vb, report notes)."""
    ns, cls, file_scoped = _ns_class(designer_text, lang, form.name)
    onload = not overrides_onload(code_text, lang)
    notes = [] if onload else [f"{cls} overrides OnLoad: call RadFxAttach() in it to start the animations / "
                               f"layout sizes"]
    calls = setup_calls(form)
    managed = sorted(managed_controls(variant_plan(form)))
    if lang == "vb":
        body = [f"        fx.{m}({', '.join(_arg_vb(a) for a in args)})" for m, args in calls]
        src = VB_TEMPLATE.replace("%CLASS%", cls).replace("%SETUP%", "\n".join(body)) \
            .replace("%MANAGED%", ", ".join(_vb_str(n) for n in managed) or "")
        src = src.replace("%ONLOAD%", VB_ONLOAD if onload else "")
        if ns:
            src = src.replace("%NS_OPEN%", f"Namespace {ns}\n").replace("%NS_CLOSE%", "\nEnd Namespace")
        else:
            src = src.replace("%NS_OPEN%", "").replace("%NS_CLOSE%", "")
        return src, notes
    body = [f"        fx.{m}({', '.join(_arg_cs(a) for a in args)});" for m, args in calls]
    src = CS_TEMPLATE.replace("%CLASS%", cls).replace("%SETUP%", "\n".join(body)) \
        .replace("%MANAGED%", ", ".join(_cs_str(n) for n in managed))
    src = src.replace("%ONLOAD%", CS_ONLOAD if onload else "")
    if ns and file_scoped:
        src = src.replace("%NS_OPEN%", f"namespace {ns};\n\n").replace("%NS_CLOSE%", "")
    elif ns:
        src = src.replace("%NS_OPEN%", f"namespace {ns}\n{{\n").replace("%NS_CLOSE%", "\n}")
    else:
        src = src.replace("%NS_OPEN%", "").replace("%NS_CLOSE%", "")
    return src, notes


# ============================================================================================ C#
CS_ONLOAD = """
    protected override void OnLoad(System.EventArgs e)
    {
        base.OnLoad(e);
        RadFxAttach();
    }
"""

CS_TEMPLATE = """// <auto-generated>
// RAD IDE: animations / layout sizes of this form (from the .radide.json next to it) - do not edit: the file is
// rewritten when the form is saved in RAD IDE. Form1.Designer.cs is never changed for them.
// </auto-generated>
#nullable disable
%NS_OPEN%partial class %CLASS%
{
    private RadFxEngine _radFx;
%ONLOAD%
    /// <summary>Starts the animations and layout sizes (OnLoad calls it).</summary>
    public void RadFxAttach()
    {
        if (_radFx != null) return;
        _radFx = new RadFxEngine(this);
        RadFxSetup(_radFx);
        _radFx.Start(new string[] { %MANAGED% });
    }

    /// <summary>Plays an animation of the Animations window ("fx1").</summary>
    public void BeginAnimation(string id) { _radFx?.Begin(id, false); }

    public void StopAnimation(string id) { _radFx?.Stop(id); }

    /// <summary>Visible with the On show / On hide animations of the control.</summary>
    public void SetVisible(string name, bool on) { _radFx?.SetVisible(name, on); }

    /// <summary>The layout sizes that apply now.</summary>
    public string[] CurrentSizes => _radFx == null ? new string[0] : _radFx.Active.ToArray();

    private static void RadFxSetup(RadFxEngine fx)
    {
%SETUP%
    }

    private sealed class RadFxEngine
    {
        private sealed class FxKey { public int Ms, Kind; public double A, B, C; public string S, Ease; }
        private sealed class FxTrack { public string Prop; public System.Collections.Generic.List<FxKey> Keys = new(); }
        private sealed class FxSb
        {
            public string Id, Target, Trigger, Source, Leave; public int Dur, Count, Delay, Interval;
            public bool Forever, AutoReverse; public string[] Chain;
            public System.Collections.Generic.List<FxTrack> Tracks = new();
            public System.Collections.Generic.Dictionary<string, object> Last;
        }
        private sealed class FxRun
        {
            public FxSb S; public long T0; public bool Back; public double From; public bool HideAfter; public long Seq;
            public System.Collections.Generic.Dictionary<string, object> Starts;
        }
        private sealed class SizeRow { public string Id, Orient, Posture, Span, Fold; public double MinW, MaxW, MinH, MaxH; }

        private readonly %CLASS% _form;
        private readonly System.Collections.Generic.Dictionary<string, FxSb> _sbs = new();
        private readonly System.Collections.Generic.List<string> _order = new();
        private readonly System.Collections.Generic.Dictionary<string, FxRun> _runs = new();
        private readonly System.Windows.Forms.Timer _timer = new() { Interval = 15 };
        private readonly System.Diagnostics.Stopwatch _clock = System.Diagnostics.Stopwatch.StartNew();
        private long _seq;
        private bool _final;
        private readonly System.Collections.Generic.List<SizeRow> _sizes = new();
        private readonly System.Collections.Generic.Dictionary<string, double[]> _base = new();
        private readonly System.Collections.Generic.Dictionary<string, System.Collections.Generic.Dictionary<string, double[]>> _place = new();
        private readonly System.Collections.Generic.Dictionary<string, System.Collections.Generic.Dictionary<string, System.Collections.Generic.Dictionary<string, string>>> _props = new();
        private readonly System.Collections.Generic.Dictionary<string, object> _baseProps = new();
        private readonly System.Collections.Generic.HashSet<string> _held = new();
        private bool _respect = true, _reduced;
        private int _offset;
        private string _activeKey = "\\u0000";
        public System.Collections.Generic.List<string> Active = new();

        public RadFxEngine(%CLASS% form) { _form = form; _timer.Tick += (s, e) => Tick(); }

        // ---------------------------------------------------------------- set-up (RadFxSetup)
        public void Respect(bool on) { _respect = on; }
        public void Sb(string id, string target, int dur, int count, bool forever, bool autoReverse, int delay,
                       string trigger, string source, int interval, string leave, string chain)
        {
            _sbs[id] = new FxSb { Id = id, Target = target, Dur = System.Math.Max(1, dur), Count = System.Math.Max(1, count),
                Forever = forever, AutoReverse = autoReverse, Delay = delay, Trigger = trigger, Source = source,
                Interval = interval, Leave = leave,
                Chain = chain.Length == 0 ? new string[0] : chain.Split(',') };
            _order.Add(id);
        }
        public void Track(string id, string prop) { _sbs[id].Tracks.Add(new FxTrack { Prop = prop }); }
        public void Key(string id, int ms, int kind, double a, double b, double c, string s, string ease)
        {
            var t = _sbs[id].Tracks; t[t.Count - 1].Keys.Add(new FxKey { Ms = ms, Kind = kind, A = a, B = b, C = c, S = s, Ease = ease });
        }
        public void Offset(int v) { _offset = v; }
        public void Size(string id, double minW, double maxW, double minH, double maxH, string orient, string posture,
                         string span, string fold)
        {
            _sizes.Add(new SizeRow { Id = id, MinW = minW, MaxW = maxW, MinH = minH, MaxH = maxH, Orient = orient,
                Posture = posture, Span = span, Fold = fold });
        }
        public void Base(string name, double x, double y, double w, double h, double rx, double ry, double rw, double rh)
        { _base[name] = new[] { x, y, w, h, rx, ry, rw, rh }; }
        public void Place(string name, string size, double x, double y, double w, double h, double rx, double ry, double rw, double rh)
        {
            if (!_place.TryGetValue(name, out var d)) _place[name] = d = new();
            d[size] = new[] { x, y, w, h, rx, ry, rw, rh };
        }
        public void Prop(string name, string size, string prop, string value)
        {
            if (!_props.TryGetValue(name, out var d)) _props[name] = d = new();
            if (!d.TryGetValue(size, out var p)) d[size] = p = new();
            p[prop] = value;
        }

        // ---------------------------------------------------------------- start
        public void Start(string[] managed)
        {
            string env = System.Environment.GetEnvironmentVariable("RADIDE_REDUCED_MOTION");
            _reduced = _respect && (env == "1" || (env != "0" && !ClientAreaAnimation()));
            foreach (string n in managed)
            {
                var c = Find(n);
                if (c != null) c.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left;
            }
            foreach (var kv in _props)
                foreach (var size in kv.Value.Values)
                    foreach (string p in size.Keys)
                    {
                        var c = Find(kv.Key);
                        string k = kv.Key + "." + p;
                        if (c != null && !_baseProps.ContainsKey(k)) _baseProps[k] = Get(c, kv.Key, p);
                    }
            if (_sizes.Count > 0)
            {
                _form.Layout += (s, e) => ApplySizes();
                ApplySizes();
            }
            foreach (string id in _order)
            {
                FxSb sb = _sbs[id];
                var src = Find(sb.Source.Length > 0 ? sb.Source : sb.Target);
                switch (sb.Trigger)
                {
                    case "load": Begin(id, false); break;
                    case "click": if (src != null) src.Click += (s, e) => Begin(id, false); break;
                    case "hover":
                        if (src != null)
                        {
                            src.MouseEnter += (s, e) => Begin(id, false);
                            src.MouseLeave += (s, e) => Leave(id, sb.Leave);
                        }
                        break;
                    case "timer":
                        if (sb.Interval > 0)
                        {
                            var t = new System.Windows.Forms.Timer { Interval = sb.Interval };
                            t.Tick += (s, e) => Begin(id, false);
                            t.Start();
                            _form.FormClosed += (s, e) => t.Dispose();
                        }
                        break;
                }
            }
            string test = System.Environment.GetEnvironmentVariable("RADIDE_FX_SELFTEST");
            if (!string.IsNullOrEmpty(test)) SelfTest(test);
        }

        [System.Runtime.InteropServices.DllImport("user32.dll")]
        private static extern bool SystemParametersInfo(uint action, uint param, ref bool value, uint ini);

        private static bool ClientAreaAnimation()
        {
            bool on = true;
            try { if (!SystemParametersInfo(0x1042, 0, ref on, 0)) return true; } catch (System.Exception) { return true; }
            return on;
        }

        private System.Windows.Forms.Control Find(string name)
        {
            if (string.IsNullOrEmpty(name)) return _form;
            var a = _form.Controls.Find(name, true);
            return a.Length > 0 ? a[0] : null;
        }

        // ---------------------------------------------------------------- properties
        private object Get(System.Windows.Forms.Control c, string name, string prop)
        {
            bool isForm = c == _form;
            switch (prop)
            {
                case "Left": return (double)c.Left;
                case "Top": return (double)(c.Top - (c.Parent == _form ? _offset : 0));
                case "Width": return (double)(isForm ? _form.ClientSize.Width : c.Width);
                case "Height": return (double)(isForm ? _form.ClientSize.Height - _offset : c.Height);
                case "Opacity": return isForm ? _form.Opacity : 1.0;
                case "BackColor": return Hex(c.BackColor);
                case "ForeColor": return Hex(c.ForeColor);
                case "FontSize": return (double)c.Font.SizeInPoints;
                case "FontBold": return c.Font.Bold;
                case "Text": return c.Text;
                case "Visible": return c.Visible;
            }
            return 0.0;
        }

        private void Set(System.Windows.Forms.Control c, string prop, object v)
        {
            bool isForm = c == _form;
            switch (prop)
            {
                case "Left": c.Left = (int)System.Math.Round(D(v)); break;
                case "Top": c.Top = (int)System.Math.Round(D(v)) + (c.Parent == _form ? _offset : 0); break;
                case "Width":
                    if (isForm) _form.ClientSize = new System.Drawing.Size(System.Math.Max(0, (int)System.Math.Round(D(v))), _form.ClientSize.Height);
                    else c.Width = System.Math.Max(0, (int)System.Math.Round(D(v)));
                    break;
                case "Height":
                    if (isForm) _form.ClientSize = new System.Drawing.Size(_form.ClientSize.Width, System.Math.Max(0, (int)System.Math.Round(D(v)) + _offset));
                    else c.Height = System.Math.Max(0, (int)System.Math.Round(D(v)));
                    break;
                case "Opacity": if (isForm) _form.Opacity = System.Math.Max(0, System.Math.Min(1, D(v))); break;
                case "BackColor": c.BackColor = Col(v as string, c.BackColor); break;
                case "ForeColor": c.ForeColor = Col(v as string, c.ForeColor); break;
                case "FontSize":
                    float size = (float)System.Math.Max(1, D(v));
                    if (System.Math.Abs(c.Font.SizeInPoints - size) > 0.01) c.Font = new System.Drawing.Font(c.Font.FontFamily, size, c.Font.Style);
                    break;
                case "FontBold":
                    bool bold = v is bool bb ? bb : string.Equals(v as string, "True", System.StringComparison.OrdinalIgnoreCase);
                    if (c.Font.Bold != bold) c.Font = new System.Drawing.Font(c.Font, bold ? c.Font.Style | System.Drawing.FontStyle.Bold : c.Font.Style & ~System.Drawing.FontStyle.Bold);
                    break;
                case "Text": c.Text = v as string ?? ""; break;
                case "Visible":
                    c.Visible = v is bool vb ? vb : v is double vd ? vd >= 0.5 : string.Equals(v as string, "True", System.StringComparison.OrdinalIgnoreCase);
                    break;
            }
        }

        private static double D(object v) => v is double d ? d : v is bool b ? (b ? 1 : 0) : 0;
        private static string Hex(System.Drawing.Color c) => "#" + c.R.ToString("x2") + c.G.ToString("x2") + c.B.ToString("x2");
        private static System.Drawing.Color Col(string s, System.Drawing.Color dflt)
        {
            try { return string.IsNullOrEmpty(s) ? dflt : System.Drawing.ColorTranslator.FromHtml(s); } catch (System.Exception) { return dflt; }
        }

        // ---------------------------------------------------------------- keyframes
        private static double Ease(double f, string e)
        {
            switch (e)
            {
                case "in": return f * f;
                case "out": return 1 - (1 - f) * (1 - f);
                case "inout": return f < 0.5 ? 2 * f * f : 1 - 2 * (1 - f) * (1 - f);
                case "sine": return -(System.Math.Cos(System.Math.PI * f) - 1) / 2;
                case "back": return 1 + 2.70158 * System.Math.Pow(f - 1, 3) + 1.70158 * System.Math.Pow(f - 1, 2);
                case "elastic":
                    if (f <= 0) return 0;
                    if (f >= 1) return 1;
                    return System.Math.Pow(2, -10 * f) * System.Math.Sin((f * 10 - 0.75) * (2 * System.Math.PI / 3)) + 1;
                case "bounce":
                    const double n = 7.5625, d = 2.75;
                    if (f < 1 / d) return n * f * f;
                    if (f < 2 / d) { f -= 1.5 / d; return n * f * f + 0.75; }
                    if (f < 2.5 / d) { f -= 2.25 / d; return n * f * f + 0.9375; }
                    f -= 2.625 / d; return n * f * f + 0.984375;
            }
            return f;
        }

        private object Value(System.Windows.Forms.Control c, string prop, FxKey k, object start, System.Collections.Generic.Dictionary<string, object> starts)
        {
            switch (k.Kind)
            {
                case 0: return k.A;
                case 1:
                    if (!(start is double s0)) return start;
                    double v = s0 * k.A + k.B;
                    if (k.S.Length > 0 && starts.TryGetValue(k.S, out var o) && o is double od) v += k.C * od;
                    else if (k.S.Length > 0 && Get(c, "", k.S) is double gd) v += k.C * gd;
                    return prop == "Opacity" ? System.Math.Max(0, System.Math.Min(1, v)) : v;
                case 2: return k.S;
                case 3: return Hex((c.Parent ?? c).BackColor);
                case 4: return k.A;
                case 5: return k.A >= 0.5;
            }
            return start;
        }

        private object Mix(string prop, object a, object b, double f)
        {
            if (f <= 0) return a;
            if (prop == "BackColor" || prop == "ForeColor")
            {
                if (f >= 1) return b;
                var ca = Col(a as string, System.Drawing.Color.Empty); var cb = Col(b as string, System.Drawing.Color.Empty);
                if (ca.IsEmpty || cb.IsEmpty) return a;
                int L(int x, int y) => System.Math.Max(0, System.Math.Min(255, (int)System.Math.Round(x + (y - x) * f)));
                return Hex(System.Drawing.Color.FromArgb(L(ca.R, cb.R), L(ca.G, cb.G), L(ca.B, cb.B)));
            }
            if (a is double da && b is double db2) return da + (db2 - da) * f;
            return f >= 1 ? b : a;
        }

        private object At(System.Windows.Forms.Control c, FxTrack tr, double t, object start, System.Collections.Generic.Dictionary<string, object> starts)
        {
            if (tr.Keys.Count == 0) return start;
            double t0 = 0; object v0 = start;
            int i0 = 0;
            if (tr.Keys[0].Ms <= 0) { v0 = Value(c, tr.Prop, tr.Keys[0], start, starts); i0 = 1; if (t <= 0 || tr.Keys.Count == 1) return v0; }
            for (int i = i0; i < tr.Keys.Count; i++)
            {
                FxKey k = tr.Keys[i];
                object v1 = Value(c, tr.Prop, k, start, starts);
                if (t <= k.Ms)
                {
                    double f = k.Ms > t0 ? (t - t0) / (k.Ms - t0) : 1;
                    return Mix(tr.Prop, v0, v1, Ease(System.Math.Max(0, System.Math.Min(1, f)), k.Ease));
                }
                t0 = k.Ms; v0 = v1;
            }
            return v0;
        }

        private void Apply(FxRun r, double t)
        {
            var c = Find(r.S.Target);
            if (c == null) return;
            c.SuspendLayout();
            foreach (FxTrack tr in r.S.Tracks)
            {
                // two animations on one property: the one that started first keeps it until it ends
                if (!_final && tr.Prop != "Text" && Owner(r, r.S.Target, tr.Prop) != null) continue;
                object v = At(c, tr, t, r.Starts[tr.Prop], r.Starts);
                if (tr.Prop == "Text")
                {
                    string full = r.Starts["Text"] as string ?? "";
                    c.Text = full.Substring(0, (int)System.Math.Round(full.Length * System.Math.Max(0, System.Math.Min(1, D(v)))));
                }
                else Set(c, tr.Prop, v);
            }
            c.ResumeLayout();
        }

        // ---------------------------------------------------------------- playing
        private long Now => _clock.ElapsedMilliseconds;

        public void Begin(string id, bool hideAfter)
        {
            if (!_sbs.TryGetValue(id, out FxSb sb)) return;
            var c = Find(sb.Target);
            if (c == null) return;
            System.Collections.Generic.Dictionary<string, object> starts;
            if (_runs.TryGetValue(id, out FxRun old)) { starts = old.Starts; _runs.Remove(id); }
            else
            {
                starts = new();
                foreach (FxTrack tr in sb.Tracks)
                    starts[tr.Prop] = tr.Prop == "Text" ? c.Text : Owner(null, sb.Target, tr.Prop) is FxRun ow ? RestOf(ow, tr.Prop)
                        : Get(c, sb.Target, tr.Prop);
                foreach (FxTrack tr in sb.Tracks)
                    foreach (FxKey k in tr.Keys)
                        if (k.S.Length > 0 && k.Kind == 1 && !starts.ContainsKey(k.S)) starts[k.S] = Get(c, sb.Target, k.S);
            }
            var r = new FxRun { S = sb, T0 = Now, HideAfter = hideAfter, Starts = starts, Seq = ++_seq };
            if (_reduced) { Finish(r); return; }
            _runs[id] = r;
            _held.Add(sb.Target);
            if (sb.Delay <= 0) Apply(r, 0);
            _timer.Start();
        }

        public void Stop(string id)
        {
            if (_runs.TryGetValue(id, out FxRun r)) { _runs.Remove(id); _held.Remove(r.S.Target); }
        }

        public void Leave(string id, string mode)
        {
            if (mode == "none" || !_sbs.TryGetValue(id, out FxSb sb)) return;
            if (mode == "stop") { Stop(id); return; }
            if (_runs.TryGetValue(id, out FxRun r))
            {
                double t = Time(r);
                r.Back = true; r.From = t < 0 ? 0 : t; r.T0 = Now;
            }
            else if (!sb.AutoReverse && sb.Last != null)
            {
                _runs[id] = new FxRun { S = sb, T0 = Now, Back = true, From = sb.Dur, Starts = sb.Last };
                _held.Add(sb.Target);
                _timer.Start();
            }
        }

        // position (ms) of run r: -1 waiting for its delay, -2 finished
        private double Time(FxRun r)
        {
            FxSb sb = r.S;
            if (r.Back) { double tb = r.From - (Now - r.T0); return tb <= 0 ? -2 : tb; }
            double e = Now - r.T0 - sb.Delay;
            if (e < 0) return -1;
            double cycle = sb.AutoReverse ? sb.Dur * 2 : sb.Dur;
            long iter = (long)System.Math.Floor(e / cycle);
            if (!sb.Forever && iter >= sb.Count) return -2;
            double lt = e - iter * cycle;
            return sb.AutoReverse && lt > sb.Dur ? 2 * sb.Dur - lt : lt;
        }

        private void Tick()
        {
            var done = new System.Collections.Generic.List<FxRun>();
            foreach (FxRun r in new System.Collections.Generic.List<FxRun>(_runs.Values))
            {
                double t = Time(r);
                if (t == -2) done.Add(r);
                else if (t >= 0) Apply(r, t);
            }
            foreach (FxRun r in done)
            {
                _runs.Remove(r.S.Id);
                _held.Remove(r.S.Target);
                if (r.Back) Apply(r, 0); else Finish(r);
            }
            if (_runs.Count == 0) _timer.Stop();
        }

        // a playing run that started before *me* (null = any) and animates prop of the same control
        private FxRun Owner(FxRun me, string target, string prop)
        {
            foreach (FxRun o in _runs.Values)
                if (o != me && o.S.Target == target && (me == null || o.Seq < me.Seq) && Time(o) != -1
                    && o.S.Tracks.Exists(t => t.Prop == prop)) return o;
            return null;
        }

        // where run o leaves prop when it ends
        private object RestOf(FxRun o, string prop)
        {
            FxTrack tr = o.S.Tracks.Find(t => t.Prop == prop);
            var c = Find(o.S.Target);
            if (tr == null || c == null || o.S.Forever) return o.Starts[prop];
            return At(c, tr, o.S.AutoReverse ? 0 : o.S.Dur, o.Starts[prop], o.Starts);
        }

        private void Finish(FxRun r)
        {
            _final = true;
            Apply(r, r.S.AutoReverse ? 0 : r.S.Dur);
            _final = false;
            var c = Find(r.S.Target);
            if (c != null && r.S.Tracks.Exists(t => t.Prop == "Text")) c.Text = r.Starts["Text"] as string ?? "";
            if (c != null && r.HideAfter) c.Visible = false;
            if (c != null && !c.Visible)            // hidden at the end (exit): the colours come back for the next show
                foreach (string p in new[] { "BackColor", "ForeColor" })
                    if (r.Starts.TryGetValue(p, out var col)) Set(c, p, col);
            r.S.Last = r.Starts;
            foreach (string n in r.S.Chain) Begin(n, false);
        }

        public void SetVisible(string name, bool on)
        {
            var c = Find(name);
            if (c == null) return;
            var show = new System.Collections.Generic.List<string>();
            var hide = new System.Collections.Generic.List<string>();
            foreach (string id in _order)
            {
                if (_sbs[id].Target != name) continue;
                if (_sbs[id].Trigger == "show") show.Add(id);
                if (_sbs[id].Trigger == "hide") hide.Add(id);
            }
            if (on) { c.Visible = true; foreach (string id in show) Begin(id, false); }
            else if (hide.Count == 0) c.Visible = false;
            else for (int i = 0; i < hide.Count; i++) Begin(hide[i], i == hide.Count - 1);
        }

        // ---------------------------------------------------------------- layout sizes
        private static string Posture()
        {
            string s = (System.Environment.GetEnvironmentVariable("RADIDE_POSTURE") ?? "").Trim().ToLowerInvariant()
                .Replace("-", "").Replace("_", "").Replace(" ", "");
            if (s == "halfopened" || s == "halfopen" || s == "half" || s == "tabletop" || s == "book") return "half-opened";
            if (s == "folded" || s == "closed" || s == "fold" || s == "cover") return "folded";
            return "flat";
        }

        public void ApplySizes()
        {
            int w = _form.ClientSize.Width, h = _form.ClientSize.Height - _offset;
            string posture = Posture();
            string spanEnv = (System.Environment.GetEnvironmentVariable("RADIDE_SPAN") ?? "").Trim().ToLowerInvariant();
            string span = spanEnv == "dual" || spanEnv == "2" || spanEnv == "spanned" || posture == "half-opened" ? "dual" : "single";
            string orient = w > h ? "landscape" : "portrait";
            var act = new System.Collections.Generic.List<string>();
            foreach (SizeRow s in _sizes)
            {
                if (s.MinW >= 0 && w < s.MinW) continue;
                if (s.MaxW >= 0 && w > s.MaxW) continue;
                if (s.MinH >= 0 && h < s.MinH) continue;
                if (s.MaxH >= 0 && h > s.MaxH) continue;
                if (s.Orient.Length > 0 && s.Orient != orient) continue;
                if (s.Posture.Length > 0 && s.Posture != posture) continue;
                if (s.Span.Length > 0 && s.Span != span) continue;
                if (s.Fold.Length > 0) continue;
                act.Add(s.Id);
            }
            string key = string.Join("|", act);
            Active = act;
            foreach (var kv in _base)
            {
                double[] spec = kv.Value;
                if (_place.TryGetValue(kv.Key, out var bySize))
                    foreach (string id in act) if (bySize.TryGetValue(id, out var sp)) spec = sp;
                var c = Find(kv.Key);
                if (c == null || _held.Contains(kv.Key) || c.Parent == null) continue;
                int cw = c.Parent.ClientSize.Width, ch = c.Parent.ClientSize.Height;
                int dy = 0;
                if (c.Parent == _form) { ch -= _offset; dy = _offset; }
                var b = new System.Drawing.Rectangle((int)System.Math.Round(spec[0] + spec[4] * cw),
                    (int)System.Math.Round(spec[1] + spec[5] * ch) + dy,
                    System.Math.Max(0, (int)System.Math.Round(spec[2] + spec[6] * cw)),
                    System.Math.Max(0, (int)System.Math.Round(spec[3] + spec[7] * ch)));
                if (c.Bounds != b) c.Bounds = b;
            }
            if (key == _activeKey) return;
            _activeKey = key;
            foreach (var kv in _props)
            {
                var c = Find(kv.Key);
                if (c == null) continue;
                var vals = new System.Collections.Generic.Dictionary<string, object>();
                foreach (var size in kv.Value.Values)
                    foreach (string p in size.Keys) vals[p] = _baseProps.TryGetValue(kv.Key + "." + p, out var bv) ? bv : null;
                foreach (string id in act)
                    if (kv.Value.TryGetValue(id, out var p2))
                        foreach (var pv in p2) vals[pv.Key] = pv.Value;
                foreach (var pv in vals)
                {
                    if (pv.Value == null) continue;
                    object v = pv.Value;
                    if (v is string sv && pv.Key == "FontSize" && double.TryParse(sv, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out double fs)) v = fs;
                    Set(c, pv.Key, v);
                }
            }
        }

        // ---------------------------------------------------------------- tests (RADIDE_FX_SELFTEST=<file>)
        private void SelfTest(string file)
        {
            var lines = new System.Collections.Generic.List<string>();
            void Dump(string tag)
            {
                foreach (System.Windows.Forms.Control c in All(_form))
                    lines.Add(tag + " " + c.Name + " " + c.Left + " " + c.Top + " " + c.Width + " " + c.Height + " " +
                              (c.Visible ? 1 : 0) + " " + Hex(c.BackColor) + " " + c.Font.SizeInPoints.ToString(System.Globalization.CultureInfo.InvariantCulture) + " " + c.Text.Replace(' ', '_'));
                lines.Add(tag + " @sizes " + string.Join(",", Active) + " " + _form.ClientSize.Width + " " + _form.ClientSize.Height);
            }
            void After(int ms, System.Action a)
            {
                var t = new System.Windows.Forms.Timer { Interval = ms };
                t.Tick += (s, e) => { t.Stop(); t.Dispose(); a(); };
                t.Start();
            }
            After(1500, () =>
            {
                Dump("t1");
                foreach (string n in (System.Environment.GetEnvironmentVariable("RADIDE_FX_CLICK") ?? "").Split(',', System.StringSplitOptions.RemoveEmptyEntries))
                {
                    var c = Find(n);
                    if (c != null) _form.InvokeOnClick(c, System.EventArgs.Empty);
                }
                After(150, () =>
                {
                    Dump("t2");
                    After(1200, () =>
                    {
                        Dump("t3");
                        string resize = System.Environment.GetEnvironmentVariable("RADIDE_FX_RESIZE") ?? "";
                        var parts = resize.Split(',');
                        if (parts.Length == 2)
                        {
                            _form.ClientSize = new System.Drawing.Size(int.Parse(parts[0]), int.Parse(parts[1]) + _offset);
                            System.Windows.Forms.Application.DoEvents();
                            Dump("t4");
                        }
                        System.IO.File.WriteAllLines(file, lines);
                        _form.Close();
                    });
                });
            });
        }

        private static System.Collections.Generic.IEnumerable<System.Windows.Forms.Control> All(System.Windows.Forms.Control root)
        {
            foreach (System.Windows.Forms.Control c in root.Controls)
            {
                yield return c;
                foreach (var k in All(c)) yield return k;
            }
        }
    }
}%NS_CLOSE%
"""


# ============================================================================================ VB.NET
VB_ONLOAD = """
    Protected Overrides Sub OnLoad(e As System.EventArgs)
        MyBase.OnLoad(e)
        RadFxAttach()
    End Sub
"""

VB_TEMPLATE = """' <auto-generated>
' RAD IDE: animations / layout sizes of this form (from the .radide.json next to it) - do not edit: the file is
' rewritten when the form is saved in RAD IDE. Form1.Designer.vb is never changed for them.
' </auto-generated>
Option Strict Off
Option Infer On
%NS_OPEN%Partial Class %CLASS%
    Private _radFx As RadFxEngine
%ONLOAD%
    ''' <summary>Starts the animations and layout sizes (OnLoad calls it).</summary>
    Public Sub RadFxAttach()
        If _radFx IsNot Nothing Then Return
        _radFx = New RadFxEngine(Me)
        RadFxSetup(_radFx)
        _radFx.Start(New String() {%MANAGED%})
    End Sub

    ''' <summary>Plays an animation of the Animations window ("fx1").</summary>
    Public Sub BeginAnimation(id As String)
        If _radFx IsNot Nothing Then _radFx.Begin(id, False)
    End Sub

    Public Sub StopAnimation(id As String)
        If _radFx IsNot Nothing Then _radFx.StopFx(id)
    End Sub

    ''' <summary>Visible with the On show / On hide animations of the control.</summary>
    Public Sub SetVisible(name As String, isOn As Boolean)
        If _radFx IsNot Nothing Then _radFx.SetVisible(name, isOn)
    End Sub

    ''' <summary>The layout sizes that apply now.</summary>
    Public ReadOnly Property CurrentSizes As String()
        Get
            If _radFx Is Nothing Then Return New String() {}
            Return _radFx.Active.ToArray()
        End Get
    End Property

    Private Shared Sub RadFxSetup(fx As RadFxEngine)
%SETUP%
    End Sub

    Private NotInheritable Class RadFxEngine
        Private Class FxKey
            Public Ms As Integer, Kind As Integer, A As Double, B As Double, C As Double, S As String, Ease As String
        End Class
        Private Class FxTrack
            Public Prop As String
            Public Keys As New System.Collections.Generic.List(Of FxKey)
        End Class
        Private Class FxSb
            Public Id As String, Target As String, Trigger As String, Source As String, LeaveMode As String
            Public Dur As Integer, Count As Integer, Delay As Integer, Interval As Integer
            Public Forever As Boolean, AutoReverse As Boolean, Chain As String()
            Public Tracks As New System.Collections.Generic.List(Of FxTrack)
            Public Last As System.Collections.Generic.Dictionary(Of String, Object)
        End Class
        Private Class FxRun
            Public S As FxSb, T0 As Long, Back As Boolean, From As Double, HideAfter As Boolean, Seq As Long
            Public Starts As System.Collections.Generic.Dictionary(Of String, Object)
        End Class
        Private Class SizeRow
            Public Id As String, Orient As String, Posture As String, Span As String, Fold As String
            Public MinW As Double, MaxW As Double, MinH As Double, MaxH As Double
        End Class

        Private ReadOnly _form As %CLASS%
        Private ReadOnly _sbs As New System.Collections.Generic.Dictionary(Of String, FxSb)
        Private ReadOnly _order As New System.Collections.Generic.List(Of String)
        Private ReadOnly _runs As New System.Collections.Generic.Dictionary(Of String, FxRun)
        Private WithEvents _timer As New System.Windows.Forms.Timer With {.Interval = 15}
        Private ReadOnly _clock As System.Diagnostics.Stopwatch = System.Diagnostics.Stopwatch.StartNew()
        Private _seq As Long
        Private _final As Boolean
        Private ReadOnly _sizes As New System.Collections.Generic.List(Of SizeRow)
        Private ReadOnly _base As New System.Collections.Generic.Dictionary(Of String, Double())
        Private ReadOnly _place As New System.Collections.Generic.Dictionary(Of String, System.Collections.Generic.Dictionary(Of String, Double()))
        Private ReadOnly _props As New System.Collections.Generic.Dictionary(Of String, System.Collections.Generic.Dictionary(Of String, System.Collections.Generic.Dictionary(Of String, String)))
        Private ReadOnly _baseProps As New System.Collections.Generic.Dictionary(Of String, Object)
        Private ReadOnly _held As New System.Collections.Generic.HashSet(Of String)
        Private _respect As Boolean = True, _reduced As Boolean, _offset As Integer, _activeKey As String = ChrW(0)
        Public Active As New System.Collections.Generic.List(Of String)

        Public Sub New(form As %CLASS%)
            _form = form
        End Sub

        ' ---------------------------------------------------------------- set-up (RadFxSetup)
        Public Sub Respect(isOn As Boolean)
            _respect = isOn
        End Sub
        Public Sub Sb(id As String, target As String, dur As Integer, count As Integer, forever As Boolean, autoReverse As Boolean,
                      delay As Integer, trigger As String, source As String, interval As Integer, leaveMode As String, chain As String)
            _sbs(id) = New FxSb With {.Id = id, .Target = target, .Dur = Math.Max(1, dur), .Count = Math.Max(1, count),
                .Forever = forever, .AutoReverse = autoReverse, .Delay = delay, .Trigger = trigger, .Source = source,
                .Interval = interval, .LeaveMode = leaveMode,
                .Chain = If(chain.Length = 0, New String() {}, chain.Split(","c))}
            _order.Add(id)
        End Sub
        Public Sub Track(id As String, prop As String)
            _sbs(id).Tracks.Add(New FxTrack With {.Prop = prop})
        End Sub
        Public Sub Key(id As String, ms As Integer, kind As Integer, a As Double, b As Double, c As Double, s As String, ease As String)
            Dim t = _sbs(id).Tracks
            t(t.Count - 1).Keys.Add(New FxKey With {.Ms = ms, .Kind = kind, .A = a, .B = b, .C = c, .S = s, .Ease = ease})
        End Sub
        Public Sub Offset(v As Integer)
            _offset = v
        End Sub
        Public Sub Size(id As String, minW As Double, maxW As Double, minH As Double, maxH As Double, orient As String,
                        posture As String, span As String, fold As String)
            _sizes.Add(New SizeRow With {.Id = id, .MinW = minW, .MaxW = maxW, .MinH = minH, .MaxH = maxH, .Orient = orient,
                .Posture = posture, .Span = span, .Fold = fold})
        End Sub
        Public Sub Base(name As String, x As Double, y As Double, w As Double, h As Double, rx As Double, ry As Double, rw As Double, rh As Double)
            _base(name) = New Double() {x, y, w, h, rx, ry, rw, rh}
        End Sub
        Public Sub Place(name As String, sizeId As String, x As Double, y As Double, w As Double, h As Double, rx As Double, ry As Double, rw As Double, rh As Double)
            If Not _place.ContainsKey(name) Then _place(name) = New System.Collections.Generic.Dictionary(Of String, Double())
            _place(name)(sizeId) = New Double() {x, y, w, h, rx, ry, rw, rh}
        End Sub
        Public Sub Prop(name As String, sizeId As String, propName As String, value As String)
            If Not _props.ContainsKey(name) Then _props(name) = New System.Collections.Generic.Dictionary(Of String, System.Collections.Generic.Dictionary(Of String, String))
            If Not _props(name).ContainsKey(sizeId) Then _props(name)(sizeId) = New System.Collections.Generic.Dictionary(Of String, String)
            _props(name)(sizeId)(propName) = value
        End Sub

        ' ---------------------------------------------------------------- start
        Public Sub Start(managed As String())
            Dim env = System.Environment.GetEnvironmentVariable("RADIDE_REDUCED_MOTION")
            _reduced = _respect AndAlso (env = "1" OrElse (env <> "0" AndAlso Not ClientAreaAnimation()))
            For Each n In managed
                Dim c = Find(n)
                If c IsNot Nothing Then c.Anchor = System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Left
            Next
            For Each kv In _props
                For Each sz In kv.Value.Values
                    For Each p In sz.Keys
                        Dim c = Find(kv.Key)
                        Dim k = kv.Key & "." & p
                        If c IsNot Nothing AndAlso Not _baseProps.ContainsKey(k) Then _baseProps(k) = GetProp(c, p)
                    Next
                Next
            Next
            If _sizes.Count > 0 Then
                AddHandler _form.Layout, Sub(s, e) ApplySizes()
                ApplySizes()
            End If
            For Each id In _order
                Dim sb = _sbs(id)
                Dim fid = id
                Dim src = Find(If(sb.Source.Length > 0, sb.Source, sb.Target))
                Select Case sb.Trigger
                    Case "load"
                        Begin(fid, False)
                    Case "click"
                        If src IsNot Nothing Then AddHandler src.Click, Sub(s, e) Begin(fid, False)
                    Case "hover"
                        If src IsNot Nothing Then
                            AddHandler src.MouseEnter, Sub(s, e) Begin(fid, False)
                            AddHandler src.MouseLeave, Sub(s, e) LeaveFx(fid, sb.LeaveMode)
                        End If
                    Case "timer"
                        If sb.Interval > 0 Then
                            Dim t As New System.Windows.Forms.Timer With {.Interval = sb.Interval}
                            AddHandler t.Tick, Sub(s, e) Begin(fid, False)
                            t.Start()
                            AddHandler _form.FormClosed, Sub(s, e) t.Dispose()
                        End If
                End Select
            Next
            Dim test = System.Environment.GetEnvironmentVariable("RADIDE_FX_SELFTEST")
            If Not String.IsNullOrEmpty(test) Then SelfTest(test)
        End Sub

        <System.Runtime.InteropServices.DllImport("user32.dll")>
        Private Shared Function SystemParametersInfo(action As UInteger, param As UInteger, ByRef value As Boolean, ini As UInteger) As Boolean
        End Function

        Private Shared Function ClientAreaAnimation() As Boolean
            Dim isOn As Boolean = True
            Try
                If Not SystemParametersInfo(&H1042UI, 0UI, isOn, 0UI) Then Return True
            Catch
                Return True
            End Try
            Return isOn
        End Function

        Private Function Find(name As String) As System.Windows.Forms.Control
            If String.IsNullOrEmpty(name) Then Return _form
            Dim a = _form.Controls.Find(name, True)
            Return If(a.Length > 0, a(0), Nothing)
        End Function

        ' ---------------------------------------------------------------- properties
        Private Function GetProp(c As System.Windows.Forms.Control, prop As String) As Object
            Dim isForm = c Is _form
            Select Case prop
                Case "Left" : Return CDbl(c.Left)
                Case "Top" : Return CDbl(c.Top - If(c.Parent Is _form, _offset, 0))
                Case "Width" : Return CDbl(If(isForm, _form.ClientSize.Width, c.Width))
                Case "Height" : Return CDbl(If(isForm, _form.ClientSize.Height - _offset, c.Height))
                Case "Opacity" : Return If(isForm, _form.Opacity, 1.0)
                Case "BackColor" : Return Hex6(c.BackColor)
                Case "ForeColor" : Return Hex6(c.ForeColor)
                Case "FontSize" : Return CDbl(c.Font.SizeInPoints)
                Case "FontBold" : Return c.Font.Bold
                Case "Text" : Return c.Text
                Case "Visible" : Return c.Visible
            End Select
            Return 0.0
        End Function

        Private Sub SetProp(c As System.Windows.Forms.Control, prop As String, v As Object)
            Dim isForm = c Is _form
            Select Case prop
                Case "Left" : c.Left = CInt(Math.Round(D(v)))
                Case "Top" : c.Top = CInt(Math.Round(D(v))) + If(c.Parent Is _form, _offset, 0)
                Case "Width"
                    If isForm Then
                        _form.ClientSize = New System.Drawing.Size(Math.Max(0, CInt(Math.Round(D(v)))), _form.ClientSize.Height)
                    Else
                        c.Width = Math.Max(0, CInt(Math.Round(D(v))))
                    End If
                Case "Height"
                    If isForm Then
                        _form.ClientSize = New System.Drawing.Size(_form.ClientSize.Width, Math.Max(0, CInt(Math.Round(D(v)))) + _offset)
                    Else
                        c.Height = Math.Max(0, CInt(Math.Round(D(v))))
                    End If
                Case "Opacity" : If isForm Then _form.Opacity = Math.Max(0, Math.Min(1, D(v)))
                Case "BackColor" : c.BackColor = Col(TryCast(v, String), c.BackColor)
                Case "ForeColor" : c.ForeColor = Col(TryCast(v, String), c.ForeColor)
                Case "FontSize"
                    Dim sz = CSng(Math.Max(1, D(v)))
                    If Math.Abs(c.Font.SizeInPoints - sz) > 0.01 Then c.Font = New System.Drawing.Font(c.Font.FontFamily, sz, c.Font.Style)
                Case "FontBold"
                    Dim bold = If(TypeOf v Is Boolean, CBool(v), String.Equals(TryCast(v, String), "True", StringComparison.OrdinalIgnoreCase))
                    If c.Font.Bold <> bold Then c.Font = New System.Drawing.Font(c.Font, If(bold, c.Font.Style Or System.Drawing.FontStyle.Bold, c.Font.Style And Not System.Drawing.FontStyle.Bold))
                Case "Text" : c.Text = If(TryCast(v, String), "")
                Case "Visible"
                    If TypeOf v Is Boolean Then
                        c.Visible = CBool(v)
                    ElseIf TypeOf v Is Double Then
                        c.Visible = CDbl(v) >= 0.5
                    Else
                        c.Visible = String.Equals(TryCast(v, String), "True", StringComparison.OrdinalIgnoreCase)
                    End If
            End Select
        End Sub

        Private Shared Function D(v As Object) As Double
            If TypeOf v Is Double Then Return CDbl(v)
            If TypeOf v Is Boolean Then Return If(CBool(v), 1.0, 0.0)
            Return 0
        End Function
        Private Shared Function Hex6(c As System.Drawing.Color) As String
            Return "#" & c.R.ToString("x2") & c.G.ToString("x2") & c.B.ToString("x2")
        End Function
        Private Shared Function Col(s As String, dflt As System.Drawing.Color) As System.Drawing.Color
            Try
                Return If(String.IsNullOrEmpty(s), dflt, System.Drawing.ColorTranslator.FromHtml(s))
            Catch
                Return dflt
            End Try
        End Function

        ' ---------------------------------------------------------------- keyframes
        Private Shared Function Ease(f As Double, e As String) As Double
            Select Case e
                Case "in" : Return f * f
                Case "out" : Return 1 - (1 - f) * (1 - f)
                Case "inout" : Return If(f < 0.5, 2 * f * f, 1 - 2 * (1 - f) * (1 - f))
                Case "sine" : Return -(Math.Cos(Math.PI * f) - 1) / 2
                Case "back" : Return 1 + 2.70158 * Math.Pow(f - 1, 3) + 1.70158 * Math.Pow(f - 1, 2)
                Case "elastic"
                    If f <= 0 Then Return 0
                    If f >= 1 Then Return 1
                    Return Math.Pow(2, -10 * f) * Math.Sin((f * 10 - 0.75) * (2 * Math.PI / 3)) + 1
                Case "bounce"
                    Const n As Double = 7.5625, dd As Double = 2.75
                    If f < 1 / dd Then Return n * f * f
                    If f < 2 / dd Then
                        f -= 1.5 / dd : Return n * f * f + 0.75
                    End If
                    If f < 2.5 / dd Then
                        f -= 2.25 / dd : Return n * f * f + 0.9375
                    End If
                    f -= 2.625 / dd : Return n * f * f + 0.984375
            End Select
            Return f
        End Function

        Private Function Value(c As System.Windows.Forms.Control, prop As String, k As FxKey, start As Object, starts As System.Collections.Generic.Dictionary(Of String, Object)) As Object
            Select Case k.Kind
                Case 0 : Return k.A
                Case 1
                    If Not TypeOf start Is Double Then Return start
                    Dim v = CDbl(start) * k.A + k.B
                    If k.S.Length > 0 Then
                        Dim o As Object = Nothing
                        If starts.TryGetValue(k.S, o) AndAlso TypeOf o Is Double Then v += k.C * CDbl(o) Else v += k.C * D(GetProp(c, k.S))
                    End If
                    Return If(prop = "Opacity", Math.Max(0, Math.Min(1, v)), v)
                Case 2 : Return k.S
                Case 3 : Return Hex6(If(c.Parent, c).BackColor)
                Case 4 : Return k.A
                Case 5 : Return k.A >= 0.5
            End Select
            Return start
        End Function

        Private Function Mix(prop As String, a As Object, b As Object, f As Double) As Object
            If f <= 0 Then Return a
            If prop = "BackColor" OrElse prop = "ForeColor" Then
                If f >= 1 Then Return b
                Dim ca = Col(TryCast(a, String), System.Drawing.Color.Empty), cb = Col(TryCast(b, String), System.Drawing.Color.Empty)
                If ca.IsEmpty OrElse cb.IsEmpty Then Return a
                Dim L = Function(x As Integer, y As Integer) Math.Max(0, Math.Min(255, CInt(Math.Round(x + (y - x) * f))))
                Return Hex6(System.Drawing.Color.FromArgb(L(ca.R, cb.R), L(ca.G, cb.G), L(ca.B, cb.B)))
            End If
            If TypeOf a Is Double AndAlso TypeOf b Is Double Then Return CDbl(a) + (CDbl(b) - CDbl(a)) * f
            Return If(f >= 1, b, a)
        End Function

        Private Function At(c As System.Windows.Forms.Control, tr As FxTrack, t As Double, start As Object, starts As System.Collections.Generic.Dictionary(Of String, Object)) As Object
            If tr.Keys.Count = 0 Then Return start
            Dim t0 As Double = 0, v0 As Object = start, i0 = 0
            If tr.Keys(0).Ms <= 0 Then
                v0 = Value(c, tr.Prop, tr.Keys(0), start, starts) : i0 = 1
                If t <= 0 OrElse tr.Keys.Count = 1 Then Return v0
            End If
            For i = i0 To tr.Keys.Count - 1
                Dim k = tr.Keys(i)
                Dim v1 = Value(c, tr.Prop, k, start, starts)
                If t <= k.Ms Then
                    Dim f = If(k.Ms > t0, (t - t0) / (k.Ms - t0), 1.0)
                    Return Mix(tr.Prop, v0, v1, Ease(Math.Max(0, Math.Min(1, f)), k.Ease))
                End If
                t0 = k.Ms : v0 = v1
            Next
            Return v0
        End Function

        Private Sub Apply(r As FxRun, t As Double)
            Dim c = Find(r.S.Target)
            If c Is Nothing Then Return
            c.SuspendLayout()
            For Each tr In r.S.Tracks
                ' two animations on one property: the one that started first keeps it until it ends
                If Not _final AndAlso tr.Prop <> "Text" AndAlso Owner(r, r.S.Target, tr.Prop) IsNot Nothing Then Continue For
                Dim v = At(c, tr, t, r.Starts(tr.Prop), r.Starts)
                If tr.Prop = "Text" Then
                    Dim full = If(TryCast(r.Starts("Text"), String), "")
                    c.Text = full.Substring(0, CInt(Math.Round(full.Length * Math.Max(0, Math.Min(1, D(v))))))
                Else
                    SetProp(c, tr.Prop, v)
                End If
            Next
            c.ResumeLayout()
        End Sub

        ' ---------------------------------------------------------------- playing
        Private ReadOnly Property Now As Long
            Get
                Return _clock.ElapsedMilliseconds
            End Get
        End Property

        Public Sub Begin(id As String, hideAfter As Boolean)
            Dim sb As FxSb = Nothing
            If Not _sbs.TryGetValue(id, sb) Then Return
            Dim c = Find(sb.Target)
            If c Is Nothing Then Return
            Dim starts As System.Collections.Generic.Dictionary(Of String, Object)
            Dim old As FxRun = Nothing
            If _runs.TryGetValue(id, old) Then
                starts = old.Starts : _runs.Remove(id)
            Else
                starts = New System.Collections.Generic.Dictionary(Of String, Object)
                For Each tr In sb.Tracks
                    Dim ow = Owner(Nothing, sb.Target, tr.Prop)
                    starts(tr.Prop) = If(tr.Prop = "Text", CObj(c.Text), If(ow IsNot Nothing, RestOf(ow, tr.Prop), GetProp(c, tr.Prop)))
                Next
                For Each tr In sb.Tracks
                    For Each k In tr.Keys
                        If k.S.Length > 0 AndAlso k.Kind = 1 AndAlso Not starts.ContainsKey(k.S) Then starts(k.S) = GetProp(c, k.S)
                    Next
                Next
            End If
            _seq += 1
            Dim r As New FxRun With {.S = sb, .T0 = Now, .HideAfter = hideAfter, .Starts = starts, .Seq = _seq}
            If _reduced Then
                Finish(r) : Return
            End If
            _runs(id) = r
            _held.Add(sb.Target)
            If sb.Delay <= 0 Then Apply(r, 0)
            _timer.Start()
        End Sub

        Public Sub StopFx(id As String)
            Dim r As FxRun = Nothing
            If _runs.TryGetValue(id, r) Then
                _runs.Remove(id) : _held.Remove(r.S.Target)
            End If
        End Sub

        Public Sub LeaveFx(id As String, mode As String)
            Dim sb As FxSb = Nothing
            If mode = "none" OrElse Not _sbs.TryGetValue(id, sb) Then Return
            If mode = "stop" Then
                StopFx(id) : Return
            End If
            Dim r As FxRun = Nothing
            If _runs.TryGetValue(id, r) Then
                Dim t = Time(r)
                r.Back = True : r.From = If(t < 0, 0, t) : r.T0 = Now
            ElseIf Not sb.AutoReverse AndAlso sb.Last IsNot Nothing Then
                _runs(id) = New FxRun With {.S = sb, .T0 = Now, .Back = True, .From = sb.Dur, .Starts = sb.Last}
                _held.Add(sb.Target)
                _timer.Start()
            End If
        End Sub

        Private Function Time(r As FxRun) As Double
            Dim sb = r.S
            If r.Back Then
                Dim tb = r.From - (Now - r.T0)
                Return If(tb <= 0, -2, tb)
            End If
            Dim e As Double = Now - r.T0 - sb.Delay
            If e < 0 Then Return -1
            Dim cycle As Double = If(sb.AutoReverse, sb.Dur * 2, sb.Dur)
            Dim iter = CLng(Math.Floor(e / cycle))
            If Not sb.Forever AndAlso iter >= sb.Count Then Return -2
            Dim lt = e - iter * cycle
            Return If(sb.AutoReverse AndAlso lt > sb.Dur, 2 * sb.Dur - lt, lt)
        End Function

        Private Sub Tick() Handles _timer.Tick
            Dim done As New System.Collections.Generic.List(Of FxRun)
            For Each r In New System.Collections.Generic.List(Of FxRun)(_runs.Values)
                Dim t = Time(r)
                If t = -2 Then
                    done.Add(r)
                ElseIf t >= 0 Then
                    Apply(r, t)
                End If
            Next
            For Each r In done
                _runs.Remove(r.S.Id) : _held.Remove(r.S.Target)
                If r.Back Then Apply(r, 0) Else Finish(r)
            Next
            If _runs.Count = 0 Then _timer.Stop()
        End Sub

        ' a playing run that started before me (Nothing = any) and animates prop of the same control
        Private Function Owner(mine As FxRun, target As String, prop As String) As FxRun
            For Each o In _runs.Values
                If o IsNot mine AndAlso o.S.Target = target AndAlso (mine Is Nothing OrElse o.Seq < mine.Seq) AndAlso
                   Time(o) <> -1 AndAlso o.S.Tracks.Exists(Function(t) t.Prop = prop) Then Return o
            Next
            Return Nothing
        End Function

        ' where run o leaves prop when it ends
        Private Function RestOf(o As FxRun, prop As String) As Object
            Dim tr = o.S.Tracks.Find(Function(t) t.Prop = prop)
            Dim c = Find(o.S.Target)
            If tr Is Nothing OrElse c Is Nothing OrElse o.S.Forever Then Return o.Starts(prop)
            Return At(c, tr, If(o.S.AutoReverse, 0, o.S.Dur), o.Starts(prop), o.Starts)
        End Function

        Private Sub Finish(r As FxRun)
            _final = True
            Apply(r, If(r.S.AutoReverse, 0, r.S.Dur))
            _final = False
            Dim c = Find(r.S.Target)
            If c IsNot Nothing AndAlso r.S.Tracks.Exists(Function(t) t.Prop = "Text") Then c.Text = If(TryCast(r.Starts("Text"), String), "")
            If c IsNot Nothing AndAlso r.HideAfter Then c.Visible = False
            If c IsNot Nothing AndAlso Not c.Visible Then
                For Each p In New String() {"BackColor", "ForeColor"}
                    Dim col As Object = Nothing
                    If r.Starts.TryGetValue(p, col) Then SetProp(c, p, col)
                Next
            End If
            r.S.Last = r.Starts
            For Each n In r.S.Chain
                Begin(n, False)
            Next
        End Sub

        Public Sub SetVisible(name As String, isOn As Boolean)
            Dim c = Find(name)
            If c Is Nothing Then Return
            Dim show As New System.Collections.Generic.List(Of String), hide As New System.Collections.Generic.List(Of String)
            For Each id In _order
                If _sbs(id).Target <> name Then Continue For
                If _sbs(id).Trigger = "show" Then show.Add(id)
                If _sbs(id).Trigger = "hide" Then hide.Add(id)
            Next
            If isOn Then
                c.Visible = True
                For Each id In show
                    Begin(id, False)
                Next
            ElseIf hide.Count = 0 Then
                c.Visible = False
            Else
                For i = 0 To hide.Count - 1
                    Begin(hide(i), i = hide.Count - 1)
                Next
            End If
        End Sub

        ' ---------------------------------------------------------------- layout sizes
        Private Shared Function Posture() As String
            Dim s = If(System.Environment.GetEnvironmentVariable("RADIDE_POSTURE"), "").Trim().ToLowerInvariant().Replace("-", "").Replace("_", "").Replace(" ", "")
            If s = "halfopened" OrElse s = "halfopen" OrElse s = "half" OrElse s = "tabletop" OrElse s = "book" Then Return "half-opened"
            If s = "folded" OrElse s = "closed" OrElse s = "fold" OrElse s = "cover" Then Return "folded"
            Return "flat"
        End Function

        Public Sub ApplySizes()
            Dim w = _form.ClientSize.Width, h = _form.ClientSize.Height - _offset
            Dim post = Posture()
            Dim spanEnv = If(System.Environment.GetEnvironmentVariable("RADIDE_SPAN"), "").Trim().ToLowerInvariant()
            Dim span = If(spanEnv = "dual" OrElse spanEnv = "2" OrElse spanEnv = "spanned" OrElse post = "half-opened", "dual", "single")
            Dim orient = If(w > h, "landscape", "portrait")
            Dim act As New System.Collections.Generic.List(Of String)
            For Each s In _sizes
                If s.MinW >= 0 AndAlso w < s.MinW Then Continue For
                If s.MaxW >= 0 AndAlso w > s.MaxW Then Continue For
                If s.MinH >= 0 AndAlso h < s.MinH Then Continue For
                If s.MaxH >= 0 AndAlso h > s.MaxH Then Continue For
                If s.Orient.Length > 0 AndAlso s.Orient <> orient Then Continue For
                If s.Posture.Length > 0 AndAlso s.Posture <> post Then Continue For
                If s.Span.Length > 0 AndAlso s.Span <> span Then Continue For
                If s.Fold.Length > 0 Then Continue For
                act.Add(s.Id)
            Next
            Dim key = String.Join("|", act)
            Active = act
            For Each kv In _base
                Dim spec = kv.Value
                Dim bySize As System.Collections.Generic.Dictionary(Of String, Double()) = Nothing
                If _place.TryGetValue(kv.Key, bySize) Then
                    For Each id In act
                        If bySize.ContainsKey(id) Then spec = bySize(id)
                    Next
                End If
                Dim c = Find(kv.Key)
                If c Is Nothing OrElse _held.Contains(kv.Key) OrElse c.Parent Is Nothing Then Continue For
                Dim cw = c.Parent.ClientSize.Width, ch = c.Parent.ClientSize.Height, dy = 0
                If c.Parent Is _form Then
                    ch -= _offset : dy = _offset
                End If
                Dim b As New System.Drawing.Rectangle(CInt(Math.Round(spec(0) + spec(4) * cw)), CInt(Math.Round(spec(1) + spec(5) * ch)) + dy,
                    Math.Max(0, CInt(Math.Round(spec(2) + spec(6) * cw))), Math.Max(0, CInt(Math.Round(spec(3) + spec(7) * ch))))
                If c.Bounds <> b Then c.Bounds = b
            Next
            If key = _activeKey Then Return
            _activeKey = key
            For Each kv In _props
                Dim c = Find(kv.Key)
                If c Is Nothing Then Continue For
                Dim vals As New System.Collections.Generic.Dictionary(Of String, Object)
                For Each sz In kv.Value.Values
                    For Each p In sz.Keys
                        Dim bv As Object = Nothing
                        vals(p) = If(_baseProps.TryGetValue(kv.Key & "." & p, bv), bv, Nothing)
                    Next
                Next
                For Each id In act
                    If kv.Value.ContainsKey(id) Then
                        For Each kvp In kv.Value(id)
                            vals(kvp.Key) = kvp.Value
                        Next
                    End If
                Next
                For Each kvp In vals
                    If kvp.Value Is Nothing Then Continue For
                    Dim v As Object = kvp.Value
                    Dim fs As Double
                    If TypeOf v Is String AndAlso kvp.Key = "FontSize" AndAlso Double.TryParse(CStr(v), Globalization.NumberStyles.Float, Globalization.CultureInfo.InvariantCulture, fs) Then v = fs
                    SetProp(c, kvp.Key, v)
                Next
            Next
        End Sub

        ' ---------------------------------------------------------------- tests (RADIDE_FX_SELFTEST=<file>)
        Private Sub SelfTest(file As String)
            Dim lines As New System.Collections.Generic.List(Of String)
            Dim dump = Sub(tag As String)
                           For Each c In All(_form)
                               lines.Add(tag & " " & c.Name & " " & c.Left & " " & c.Top & " " & c.Width & " " & c.Height & " " &
                                         If(c.Visible, 1, 0) & " " & Hex6(c.BackColor) & " " & c.Font.SizeInPoints.ToString(Globalization.CultureInfo.InvariantCulture) & " " & c.Text.Replace(" "c, "_"c))
                           Next
                           lines.Add(tag & " @sizes " & String.Join(",", Active) & " " & _form.ClientSize.Width & " " & _form.ClientSize.Height)
                       End Sub
            Dim after = Sub(ms As Integer, a As Action)
                            Dim t As New System.Windows.Forms.Timer With {.Interval = ms}
                            AddHandler t.Tick, Sub(s, e)
                                                   t.Stop() : t.Dispose() : a()
                                               End Sub
                            t.Start()
                        End Sub
            after(1500, Sub()
                            dump("t1")
                            For Each n In If(System.Environment.GetEnvironmentVariable("RADIDE_FX_CLICK"), "").Split(New Char() {","c}, StringSplitOptions.RemoveEmptyEntries)
                                Dim c = Find(n)
                                If c IsNot Nothing Then _form.InvokeOnClick(c, EventArgs.Empty)
                            Next
                            after(150, Sub()
                                           dump("t2")
                                           after(1200, Sub()
                                                           dump("t3")
                                                           Dim parts = If(System.Environment.GetEnvironmentVariable("RADIDE_FX_RESIZE"), "").Split(","c)
                                                           If parts.Length = 2 Then
                                                               _form.ClientSize = New System.Drawing.Size(CInt(parts(0)), CInt(parts(1)) + _offset)
                                                               System.Windows.Forms.Application.DoEvents()
                                                               dump("t4")
                                                           End If
                                                           System.IO.File.WriteAllLines(file, lines)
                                                           _form.Close()
                                                       End Sub)
                                       End Sub)
                        End Sub)
        End Sub

        Private Shared Iterator Function All(root As System.Windows.Forms.Control) As System.Collections.Generic.IEnumerable(Of System.Windows.Forms.Control)
            For Each c As System.Windows.Forms.Control In root.Controls
                Yield c
                For Each k In All(c)
                    Yield k
                Next
            Next
        End Function
    End Class
End Class%NS_CLOSE%
"""


__all__ = ["load_sidecar", "save", "generate", "setup_calls", "sidecar_path", "partial_path", "overrides_onload"]
