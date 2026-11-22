// RadIDE.Controls - (c) 2026 Musoftware - https://musoftwares.com - MIT License
// Core: drawing helpers, the animated owner-drawn base control, item model + JSON, glyph icons and the
// VB-style scripting bridge (RmScript) the RAD IDE runtime uses for Get / Set / Call by name.
#nullable disable
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Text;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

namespace RadIDE.Controls
{
    // ====================================================================== drawing
    public static class RmDraw
    {
        public static Color Blend(Color a, Color b, double t)
        {
            t = Math.Max(0, Math.Min(1, t));
            return Color.FromArgb((int)(a.A + (b.A - a.A) * t + 0.5), (int)(a.R + (b.R - a.R) * t + 0.5),
                                  (int)(a.G + (b.G - a.G) * t + 0.5), (int)(a.B + (b.B - a.B) * t + 0.5));
        }

        public static double Luma(Color c) { return (0.299 * c.R + 0.587 * c.G + 0.114 * c.B) / 255.0; }

        public static Color Alpha(Color c, int a) { return Color.FromArgb(Math.Max(0, Math.Min(255, a)), c.R, c.G, c.B); }

        public static Color Contrast(Color back) { return Luma(back) > 0.6 ? Color.FromArgb(30, 30, 30) : Color.White; }

        public static GraphicsPath Round(RectangleF r, float radius)
        {
            var p = new GraphicsPath();
            if (radius <= 0.5f || r.Width < 2 || r.Height < 2) { p.AddRectangle(r); return p; }
            float d = Math.Min(radius * 2, Math.Min(r.Width, r.Height));
            p.AddArc(r.X, r.Y, d, d, 180, 90);
            p.AddArc(r.Right - d, r.Y, d, d, 270, 90);
            p.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
            p.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
            p.CloseFigure();
            return p;
        }

        /// <summary>Anti-aliased rounded rectangle: fill (Empty = none) and border (Empty = none).</summary>
        public static void Box(Graphics g, RectangleF r, Color fill, Color border, float borderWidth, float radius)
        {
            var old = g.SmoothingMode;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            if (!fill.IsEmpty && fill.A > 0)
                using (var p = Round(r, radius)) using (var b = new SolidBrush(fill)) g.FillPath(b, p);
            if (!border.IsEmpty && border.A > 0 && borderWidth > 0)
            {
                var h = borderWidth / 2f;
                var rr = new RectangleF(r.X + h, r.Y + h, r.Width - borderWidth, r.Height - borderWidth);
                using (var p = Round(rr, Math.Max(0, radius - h))) using (var pen = new Pen(border, borderWidth)) g.DrawPath(pen, p);
            }
            g.SmoothingMode = old;
        }

        public static void Shadow(Graphics g, RectangleF r, float radius, int depth, bool dark)
        {
            var old = g.SmoothingMode;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            for (int i = depth; i >= 1; i--)
            {
                var rr = new RectangleF(r.X - i + 1, r.Y - i + 2, r.Width + 2 * i - 2, r.Height + 2 * i - 2);
                using (var p = Round(rr, radius + i)) using (var b = new SolidBrush(Color.FromArgb((dark ? 40 : 18) / i + 2, 0, 0, 0)))
                    g.FillPath(b, p);
            }
            g.SmoothingMode = old;
        }

        public static TextFormatFlags Flags(ContentAlignment a, bool rtl, bool wrap = false)
        {
            var f = TextFormatFlags.NoPrefix | TextFormatFlags.PreserveGraphicsClipping;
            f |= wrap ? TextFormatFlags.WordBreak : (TextFormatFlags.SingleLine | TextFormatFlags.EndEllipsis);
            switch (a)
            {
                case ContentAlignment.TopLeft: case ContentAlignment.MiddleLeft: case ContentAlignment.BottomLeft: f |= TextFormatFlags.Left; break;
                case ContentAlignment.TopRight: case ContentAlignment.MiddleRight: case ContentAlignment.BottomRight: f |= TextFormatFlags.Right; break;
                default: f |= TextFormatFlags.HorizontalCenter; break;
            }
            switch (a)
            {
                case ContentAlignment.TopLeft: case ContentAlignment.TopCenter: case ContentAlignment.TopRight: f |= TextFormatFlags.Top; break;
                case ContentAlignment.BottomLeft: case ContentAlignment.BottomCenter: case ContentAlignment.BottomRight: f |= TextFormatFlags.Bottom; break;
                default: f |= TextFormatFlags.VerticalCenter; break;
            }
            if (rtl) f |= TextFormatFlags.RightToLeft;
            return f;
        }

        /// <summary>Text with GDI (ClearType, correct Arabic shaping, right-to-left reading order).</summary>
        public static void Text(Graphics g, string text, Font font, Rectangle r, Color color, ContentAlignment a, bool rtl = false, bool wrap = false)
        {
            if (string.IsNullOrEmpty(text) || r.Width <= 0 || r.Height <= 0) return;
            if (rtl)
            {   // mirror the horizontal alignment
                if (a == ContentAlignment.MiddleLeft) a = ContentAlignment.MiddleRight; else if (a == ContentAlignment.MiddleRight) a = ContentAlignment.MiddleLeft;
                else if (a == ContentAlignment.TopLeft) a = ContentAlignment.TopRight; else if (a == ContentAlignment.TopRight) a = ContentAlignment.TopLeft;
                else if (a == ContentAlignment.BottomLeft) a = ContentAlignment.BottomRight; else if (a == ContentAlignment.BottomRight) a = ContentAlignment.BottomLeft;
            }
            TextRenderer.DrawText(g, text, font, r, color, Flags(a, rtl, wrap));
        }

        public static Size Measure(string text, Font font)
        {
            if (string.IsNullOrEmpty(text)) return new Size(0, font.Height);
            return TextRenderer.MeasureText(text, font, new Size(int.MaxValue, int.MaxValue), TextFormatFlags.NoPrefix | TextFormatFlags.SingleLine);
        }

        public static void Chevron(Graphics g, RectangleF r, Color c, float w, bool down = true, bool right = false, bool left = false)
        {
            var old = g.SmoothingMode;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            float cx = r.X + r.Width / 2, cy = r.Y + r.Height / 2, s = Math.Min(r.Width, r.Height) / 4f;
            using (var p = new Pen(c, w) { StartCap = LineCap.Round, EndCap = LineCap.Round, LineJoin = LineJoin.Round })
            {
                if (right) g.DrawLines(p, new[] { new PointF(cx - s / 2, cy - s), new PointF(cx + s / 2, cy), new PointF(cx - s / 2, cy + s) });
                else if (left) g.DrawLines(p, new[] { new PointF(cx + s / 2, cy - s), new PointF(cx - s / 2, cy), new PointF(cx + s / 2, cy + s) });
                else if (down) g.DrawLines(p, new[] { new PointF(cx - s, cy - s / 2), new PointF(cx, cy + s / 2), new PointF(cx + s, cy - s / 2) });
                else g.DrawLines(p, new[] { new PointF(cx - s, cy + s / 2), new PointF(cx, cy - s / 2), new PointF(cx + s, cy + s / 2) });
            }
            g.SmoothingMode = old;
        }

        public static void Cross(Graphics g, RectangleF r, Color c, float w)
        {
            var old = g.SmoothingMode;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            float s = Math.Min(r.Width, r.Height) / 4f, cx = r.X + r.Width / 2, cy = r.Y + r.Height / 2;
            using (var p = new Pen(c, w) { StartCap = LineCap.Round, EndCap = LineCap.Round })
            {
                g.DrawLine(p, cx - s, cy - s, cx + s, cy + s);
                g.DrawLine(p, cx - s, cy + s, cx + s, cy - s);
            }
            g.SmoothingMode = old;
        }

        public static void Check(Graphics g, RectangleF r, Color c, float w)
        {
            var old = g.SmoothingMode;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            using (var p = new Pen(c, w) { StartCap = LineCap.Round, EndCap = LineCap.Round, LineJoin = LineJoin.Round })
                g.DrawLines(p, new[] { new PointF(r.X + r.Width * 0.22f, r.Y + r.Height * 0.52f), new PointF(r.X + r.Width * 0.42f, r.Y + r.Height * 0.72f),
                                       new PointF(r.X + r.Width * 0.78f, r.Y + r.Height * 0.3f) });
            g.SmoothingMode = old;
        }

        public static Color Parse(string v)
        {
            v = (v ?? "").Trim();
            if (v.Length == 0) return Color.Empty;
            try
            {
                if (v.StartsWith("#"))
                {
                    var h = v.Substring(1);
                    if (h.Length == 3) h = new string(new[] { h[0], h[0], h[1], h[1], h[2], h[2] });
                    if (h.Length == 6) return Color.FromArgb(int.Parse(h.Substring(0, 2), NumberStyles.HexNumber), int.Parse(h.Substring(2, 2), NumberStyles.HexNumber), int.Parse(h.Substring(4, 2), NumberStyles.HexNumber));
                    if (h.Length == 8) return Color.FromArgb(int.Parse(h.Substring(0, 2), NumberStyles.HexNumber), int.Parse(h.Substring(2, 2), NumberStyles.HexNumber), int.Parse(h.Substring(4, 2), NumberStyles.HexNumber), int.Parse(h.Substring(6, 2), NumberStyles.HexNumber));
                }
                long n;
                if (long.TryParse(v, NumberStyles.Integer, CultureInfo.InvariantCulture, out n))
                    return Color.FromArgb((int)(n & 0xFF), (int)((n >> 8) & 0xFF), (int)((n >> 16) & 0xFF));
                var c = Color.FromName(v);
                return c.IsKnownColor ? c : Color.Empty;
            }
            catch (Exception) { return Color.Empty; }
        }

        public static string Hex(Color c) { return c.IsEmpty ? "" : "#" + c.R.ToString("X2") + c.G.ToString("X2") + c.B.ToString("X2"); }
    }

    /// <summary>Dark scroll bars / headers of native child windows (list, tree, grid, edit) in dark themes.</summary>
    public static class RmNativeTheme
    {
        [System.Runtime.InteropServices.DllImport("uxtheme.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
        static extern int SetWindowTheme(IntPtr hwnd, string app, string idList);

        public static void Apply(Control c, bool dark)
        {
            if (c == null || !c.IsHandleCreated) return;
            try { SetWindowTheme(c.Handle, dark ? "DarkMode_Explorer" : "Explorer", null); } catch (Exception) { }
        }
    }

    // ====================================================================== images and glyphs
    /// <summary>Image properties: a file (relative to the program folder) or a built-in glyph "icon:name"
    /// (drawn with the Segoe MDL2 Assets / Segoe Fluent Icons font of Windows 10/11).</summary>
    public static class RmImages
    {
        static readonly Dictionary<string, Image> cache = new Dictionary<string, Image>(StringComparer.OrdinalIgnoreCase);
        static readonly Dictionary<string, char> glyphs = new Dictionary<string, char>(StringComparer.OrdinalIgnoreCase)
        {
            {"home", ''}, {"save", ''}, {"open", ''}, {"folder", ''}, {"new", ''}, {"add", ''},
            {"file", ''}, {"settings", ''}, {"user", ''}, {"people", ''}, {"chart", ''},
            {"mail", ''}, {"calendar", ''}, {"search", ''}, {"close", ''}, {"check", ''},
            {"info", ''}, {"warning", ''}, {"error", ''}, {"bold", ''}, {"italic", ''},
            {"underline", ''}, {"cut", ''}, {"copy", ''}, {"paste", ''}, {"print", ''},
            {"refresh", ''}, {"star", ''}, {"grid", ''}, {"bell", ''}, {"play", ''},
            {"pause", ''}, {"stop", ''}, {"delete", ''}, {"edit", ''}, {"undo", ''},
            {"redo", ''}, {"filter", ''}, {"sort", ''}, {"list", ''}, {"tiles", ''},
            {"globe", ''}, {"lock", ''}, {"phone", ''}, {"cart", ''}, {"money", ''},
            {"heart", ''}, {"tag", ''}, {"clock", ''}, {"database", ''}, {"cloud", ''},
            {"download", ''}, {"upload", ''}, {"share", ''}, {"zoom", ''}, {"help", ''},
            {"menu", ''}, {"more", ''}, {"back", ''}, {"forward", ''}, {"pin", ''},
            {"color", ''}, {"font", ''}, {"table", ''}, {"report", ''}, {"document", ''},
        };
        static string fontName;

        static string GlyphFont()
        {
            if (fontName != null) return fontName;
            fontName = "";
            using (var fonts = new InstalledFontCollection())
                foreach (var f in fonts.Families)
                {
                    if (f.Name == "Segoe Fluent Icons") { fontName = f.Name; break; }
                    if (f.Name == "Segoe MDL2 Assets") fontName = f.Name;
                }
            return fontName;
        }

        public static bool IsGlyph(string spec)
        {
            if (string.IsNullOrEmpty(spec)) return false;
            var s = spec.StartsWith("icon:", StringComparison.OrdinalIgnoreCase) ? spec.Substring(5) : spec;
            return glyphs.ContainsKey(s) && (spec.StartsWith("icon:", StringComparison.OrdinalIgnoreCase) || Path.GetExtension(spec).Length == 0);
        }

        public static string BaseDir = AppDomain.CurrentDomain.BaseDirectory;

        /// <summary>A file image (cached); null for glyphs / missing files.</summary>
        public static Image Load(string spec)
        {
            if (string.IsNullOrEmpty(spec) || IsGlyph(spec)) return null;
            Image img;
            if (cache.TryGetValue(spec, out img)) return img;
            try
            {
                var p = Path.IsPathRooted(spec) ? spec : Path.Combine(BaseDir, spec);
                img = File.Exists(p) ? Image.FromStream(new MemoryStream(File.ReadAllBytes(p))) : null;
            }
            catch (Exception) { img = null; }
            cache[spec] = img;
            return img;
        }

        /// <summary>Draws an image spec (glyph or file, or an Image object) centred in r.</summary>
        public static bool Draw(Graphics g, string spec, Image image, Rectangle r, Color color, bool enabled = true)
        {
            if (image == null && string.IsNullOrEmpty(spec)) return false;
            if (image == null && IsGlyph(spec))
            {
                var name = spec.StartsWith("icon:", StringComparison.OrdinalIgnoreCase) ? spec.Substring(5) : spec;
                var font = GlyphFont();
                var ch = glyphs[name];
                if (font.Length == 0)
                {   // no icon font: a letter in a circle
                    using (var f = new Font("Segoe UI", Math.Max(6, r.Height * 0.45f), FontStyle.Bold, GraphicsUnit.Pixel))
                        TextRenderer.DrawText(g, name.Substring(0, 1).ToUpperInvariant(), f, r, color, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.NoPadding);
                    return true;
                }
                using (var f = new Font(font, Math.Max(6, Math.Min(r.Width, r.Height) * 0.72f), FontStyle.Regular, GraphicsUnit.Pixel))
                    TextRenderer.DrawText(g, ch.ToString(), f, r, color, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.NoPadding | TextFormatFlags.SingleLine);
                return true;
            }
            var img = image ?? Load(spec);
            if (img == null) return false;
            float sc = Math.Min(1f, Math.Min((float)r.Width / img.Width, (float)r.Height / img.Height));
            int w = (int)(img.Width * sc), h = (int)(img.Height * sc);
            var dst = new Rectangle(r.X + (r.Width - w) / 2, r.Y + (r.Height - h) / 2, w, h);
            if (enabled) g.DrawImage(img, dst);
            else ControlPaint.DrawImageDisabled(g, img, dst.X, dst.Y, Color.Transparent);
            return true;
        }
    }

    // ====================================================================== items + JSON
    /// <summary>An item of a list-like property (ribbon, side bar, menus, tabs, nodes ...).</summary>
    public class RmItem
    {
        public string Text = "", Name = "", Image = "", Kind = "", ToolTip = "", Group = "", Value = "";
        public bool Checked, Enabled = true, Visible = true, Expanded;
        public int Count;
        public List<RmItem> Items = new List<RmItem>();
        public Dictionary<string, object> Extra = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
        public object Tag;

        public RmItem() { }
        public RmItem(string text) { Text = text; Name = text; }

        public override string ToString() { return Text; }

        public string Key { get { return string.IsNullOrEmpty(Name) ? Text : Name; } }

        public IEnumerable<RmItem> All()
        {
            foreach (var i in Items) { yield return i; foreach (var k in i.All()) yield return k; }
        }

        /// <summary>JSON array of {Text, Name, Image, Items, ...} or a ';' list ("a;b;c", "Group:a,b;Group2:c").</summary>
        public static List<RmItem> Parse(string spec)
        {
            var list = new List<RmItem>();
            spec = (spec ?? "").Trim();
            if (spec.Length == 0) return list;
            if (spec.StartsWith("[") || spec.StartsWith("{"))
            {
                object v;
                try { v = RmJson.Parse(spec); } catch (Exception) { return list; }
                var arr = v as List<object> ?? new List<object> { v };
                foreach (var o in arr) { var it = FromJson(o); if (it != null) list.Add(it); }
                return list;
            }
            foreach (var part in spec.Split(';'))
            {
                var s = part.Trim();
                if (s.Length == 0) continue;
                var colon = s.IndexOf(':');
                if (colon > 0 && s.IndexOf(',') > colon || colon > 0 && colon == s.Length - 1)
                {
                    var g = new RmItem(s.Substring(0, colon).Trim());
                    foreach (var k in s.Substring(colon + 1).Split(','))
                        if (k.Trim().Length > 0) g.Items.Add(new RmItem(k.Trim()));
                    list.Add(g);
                }
                else list.Add(new RmItem(s));
            }
            return list;
        }

        public static RmItem FromJson(object o)
        {
            if (o is string) return new RmItem((string)o);
            var d = o as Dictionary<string, object>;
            if (d == null) return null;
            var it = new RmItem();
            foreach (var kv in d)
            {
                switch (kv.Key.ToLowerInvariant())
                {
                    case "text": case "title": case "caption": it.Text = Str(kv.Value); break;
                    case "name": case "key": case "id": it.Name = Str(kv.Value); break;
                    case "image": case "icon": it.Image = Str(kv.Value); break;
                    case "kind": case "type": case "style": it.Kind = Str(kv.Value); break;
                    case "tooltip": case "tip": it.ToolTip = Str(kv.Value); break;
                    case "group": it.Group = Str(kv.Value); break;
                    case "value": it.Value = Str(kv.Value); break;
                    case "checked": it.Checked = Bool(kv.Value); break;
                    case "enabled": it.Enabled = Bool(kv.Value); break;
                    case "visible": it.Visible = Bool(kv.Value); break;
                    case "expanded": it.Expanded = Bool(kv.Value); break;
                    case "count": case "badge": int n; int.TryParse(Str(kv.Value), NumberStyles.Integer, CultureInfo.InvariantCulture, out n); it.Count = n; break;
                    case "items": case "children": case "nodes": case "groups":
                        var arr = kv.Value as List<object>;
                        if (arr != null) foreach (var k in arr) { var c = FromJson(k); if (c != null) it.Items.Add(c); }
                        else if (kv.Value is string) it.Items.AddRange(Parse((string)kv.Value));
                        break;
                    default: it.Extra[kv.Key] = kv.Value; break;
                }
            }
            if (string.IsNullOrEmpty(it.Name)) it.Name = it.Text;
            return it;
        }

        public string ExtraStr(string key, string def = "")
        {
            object v;
            return Extra.TryGetValue(key, out v) && v != null ? Str(v) : def;
        }

        public static string Str(object v)
        {
            if (v == null) return "";
            if (v is double) return ((double)v).ToString(CultureInfo.InvariantCulture);
            if (v is bool) return (bool)v ? "True" : "False";
            if (v is List<object> || v is Dictionary<string, object>) return RmJson.Write(v);
            return v.ToString();
        }

        public static bool Bool(object v)
        {
            if (v is bool) return (bool)v;
            if (v is double) return (double)v != 0;
            var s = Str(v).Trim().ToLowerInvariant();
            return s == "true" || s == "1" || s == "yes" || s == "-1";
        }

        public Dictionary<string, object> ToJson()
        {
            var d = new Dictionary<string, object>();
            d["Text"] = Text;
            if (Name != Text && Name.Length > 0) d["Name"] = Name;
            if (Image.Length > 0) d["Image"] = Image;
            if (Kind.Length > 0) d["Kind"] = Kind;
            if (Checked) d["Checked"] = true;
            if (!Enabled) d["Enabled"] = false;
            if (Count != 0) d["Count"] = (double)Count;
            foreach (var kv in Extra) d[kv.Key] = kv.Value;
            if (Items.Count > 0) d["Items"] = Items.Select(i => (object)i.ToJson()).ToList();
            return d;
        }

        public static string Write(IEnumerable<RmItem> items) { return RmJson.Write(items.Select(i => (object)i.ToJson()).ToList()); }
    }

    /// <summary>A small JSON reader / writer (the .NET Framework has none built in).</summary>
    public static class RmJson
    {
        public static object Parse(string s)
        {
            int i = 0;
            var v = Value(s, ref i);
            return v;
        }

        static void Ws(string s, ref int i) { while (i < s.Length && char.IsWhiteSpace(s[i])) i++; }

        static object Value(string s, ref int i)
        {
            Ws(s, ref i);
            if (i >= s.Length) throw new FormatException("unexpected end of JSON");
            char c = s[i];
            if (c == '{')
            {
                var d = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
                i++; Ws(s, ref i);
                if (i < s.Length && s[i] == '}') { i++; return d; }
                while (true)
                {
                    Ws(s, ref i);
                    var k = (string)Value(s, ref i);
                    Ws(s, ref i);
                    if (i >= s.Length || s[i] != ':') throw new FormatException("':' expected");
                    i++;
                    d[k] = Value(s, ref i);
                    Ws(s, ref i);
                    if (i < s.Length && s[i] == ',') { i++; continue; }
                    if (i < s.Length && s[i] == '}') { i++; return d; }
                    throw new FormatException("',' or '}' expected");
                }
            }
            if (c == '[')
            {
                var l = new List<object>();
                i++; Ws(s, ref i);
                if (i < s.Length && s[i] == ']') { i++; return l; }
                while (true)
                {
                    l.Add(Value(s, ref i));
                    Ws(s, ref i);
                    if (i < s.Length && s[i] == ',') { i++; continue; }
                    if (i < s.Length && s[i] == ']') { i++; return l; }
                    throw new FormatException("',' or ']' expected");
                }
            }
            if (c == '"')
            {
                var sb = new StringBuilder();
                i++;
                while (i < s.Length && s[i] != '"')
                {
                    if (s[i] == '\\' && i + 1 < s.Length)
                    {
                        i++;
                        switch (s[i])
                        {
                            case 'n': sb.Append('\n'); break;
                            case 'r': sb.Append('\r'); break;
                            case 't': sb.Append('\t'); break;
                            case 'b': sb.Append('\b'); break;
                            case 'f': sb.Append('\f'); break;
                            case 'u': sb.Append((char)int.Parse(s.Substring(i + 1, 4), NumberStyles.HexNumber)); i += 4; break;
                            default: sb.Append(s[i]); break;
                        }
                    }
                    else sb.Append(s[i]);
                    i++;
                }
                i++;
                return sb.ToString();
            }
            if (s.Substring(i).StartsWith("true")) { i += 4; return true; }
            if (s.Substring(i).StartsWith("false")) { i += 5; return false; }
            if (s.Substring(i).StartsWith("null")) { i += 4; return null; }
            int st = i;
            while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
            if (i == st) throw new FormatException("bad JSON at " + i);
            return double.Parse(s.Substring(st, i - st), NumberStyles.Float, CultureInfo.InvariantCulture);
        }

        public static string Write(object v)
        {
            var sb = new StringBuilder();
            W(sb, v);
            return sb.ToString();
        }

        static void W(StringBuilder sb, object v)
        {
            if (v == null) { sb.Append("null"); return; }
            if (v is bool) { sb.Append((bool)v ? "true" : "false"); return; }
            if (v is double || v is int || v is float || v is long || v is decimal) { sb.Append(Convert.ToDouble(v).ToString("R", CultureInfo.InvariantCulture)); return; }
            var d = v as IDictionary<string, object>;
            if (d != null)
            {
                sb.Append('{');
                bool first = true;
                foreach (var kv in d) { if (!first) sb.Append(','); first = false; W(sb, kv.Key); sb.Append(':'); W(sb, kv.Value); }
                sb.Append('}');
                return;
            }
            var l = v as System.Collections.IEnumerable;
            if (l != null && !(v is string))
            {
                sb.Append('[');
                bool first = true;
                foreach (var o in l) { if (!first) sb.Append(','); first = false; W(sb, o); }
                sb.Append(']');
                return;
            }
            sb.Append('"');
            foreach (var ch in v.ToString())
            {
                switch (ch)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default: if (ch < ' ') sb.Append("\\u" + ((int)ch).ToString("x4")); else sb.Append(ch); break;
                }
            }
            sb.Append('"');
        }
    }

    // ====================================================================== events
    /// <summary>Item-level events: ItemName / Index / Text of the item (Cancel for the -ing events).</summary>
    public class RmItemEventArgs : EventArgs
    {
        public string ItemName { get; set; }
        public int Index { get; set; }
        public string Text { get; set; }
        public bool Cancel { get; set; }
        public RmItem Item { get; set; }
        public RmItemEventArgs(string name, int index, string text = null, RmItem item = null)
        {
            ItemName = name ?? ""; Index = index; Text = text ?? name ?? ""; Item = item;
        }

        /// <summary>Raises an item event and records EventItem / EventIndex on the sender first.</summary>
        public static void Raise(object sender, EventHandler<RmItemEventArgs> handler, RmItemEventArgs a)
        {
            var t = sender.GetType();
            var pi = t.GetProperty("EventItem"); var px = t.GetProperty("EventIndex");
            if (pi != null && pi.CanWrite) pi.SetValue(sender, a.ItemName, null);
            if (px != null && px.CanWrite) px.SetValue(sender, a.Index, null);
            if (handler != null) handler(sender, a);
        }
    }

    // ====================================================================== animation
    /// <summary>One UI timer that advances every running animation (hover / press fades, toggles, toasts).</summary>
    public static class RmAnimator
    {
        static readonly List<Func<bool>> running = new List<Func<bool>>();
        static Timer timer;

        /// <summary>step() returns true while it wants more frames.</summary>
        public static void Run(Func<bool> step)
        {
            if (!running.Contains(step)) running.Add(step);
            if (timer == null) { timer = new Timer { Interval = 15 }; timer.Tick += Tick; }
            timer.Enabled = true;
        }

        static void Tick(object s, EventArgs e)
        {
            foreach (var f in running.ToArray())
            {
                bool more;
                try { more = f(); } catch (Exception) { more = false; }
                if (!more) running.Remove(f);
            }
            if (running.Count == 0) timer.Enabled = false;
        }

        public static double Step(double value, double target, int ms)
        {
            double d = 15.0 / Math.Max(15, ms);
            return value < target ? Math.Min(target, value + d) : Math.Max(target, value - d);
        }
    }

    // ====================================================================== the base control
    /// <summary>Owner-drawn, double-buffered, themed control with animated hover / press, DPI-aware metrics and RTL.</summary>
    [ToolboxItem(false)]
    public class RmControl : Control, IRmThemed
    {
        RmStyle style = RmStyle.Inherit;
        Color accent = Color.Empty;
        protected double hover, press;
        bool hot, down;
        readonly Func<bool> animStep;

        public RmControl()
        {
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer |
                     ControlStyles.ResizeRedraw | ControlStyles.SupportsTransparentBackColor, true);
            animStep = AnimStep;
            RmThemeManager.ThemeChanged += OnThemeChanged;
            base.BackColor = Color.Transparent;
            Font = new Font("Segoe UI", 9f);
        }

        protected override void Dispose(bool disposing)
        {
            RmThemeManager.ThemeChanged -= OnThemeChanged;
            base.Dispose(disposing);
        }

        void OnThemeChanged(object s, EventArgs e) { if (!IsDisposed) { ThemeChanged(); if (fore.IsEmpty) OnForeColorChanged(EventArgs.Empty); Invalidate(); } }

        protected virtual void ThemeChanged() { }

        [Category("Appearance"), DefaultValue(RmStyle.Inherit), Description("Inherit = the form / application theme.")]
        public RmStyle Style { get { return style; } set { style = value; ThemeChanged(); Invalidate(); } }

        [Category("Appearance"), Description("Accent colour (Empty = the theme accent).")]
        public Color AccentColor { get { return accent; } set { accent = value; ThemeChanged(); Invalidate(); } }
        public bool ShouldSerializeAccentColor() { return !accent.IsEmpty; }
        public void ResetAccentColor() { AccentColor = Color.Empty; }

        [Browsable(false)]
        public RmTheme Theme { get { return RmThemeManager.Resolve(style, accent); } }

        [DefaultValue(typeof(Color), "Transparent")]
        public override Color BackColor { get { return base.BackColor; } set { base.BackColor = value; } }

        Color fore = Color.Empty;

        /// <summary>Text colour: set = used as it is; not set = the theme's (it does not follow the parent's ForeColor).</summary>
        public override Color ForeColor
        {
            get { return fore.IsEmpty ? Theme.WindowText : fore; }
            set { if (fore == value) return; fore = value; OnForeColorChanged(EventArgs.Empty); Invalidate(); }
        }
        public bool ShouldSerializeForeColor() { return !fore.IsEmpty; }
        public override void ResetForeColor() { ForeColor = Color.Empty; }

        /// <summary>True when ForeColor was set (code / designer).</summary>
        protected bool HasFore { get { return !fore.IsEmpty; } }

        /// <summary>96-DPI units to device pixels.</summary>
        protected int S(float v) { return (int)Math.Round(v * DeviceDpiScale); }
        protected float Sf(float v) { return v * DeviceDpiScale; }
        protected float DeviceDpiScale { get { return Math.Max(1f, DeviceDpi / 96f); } }

        protected bool Rtl { get { return RightToLeft == RightToLeft.Yes; } }

        /// <summary>Mirrors a rectangle horizontally inside the client area when RightToLeft is on.</summary>
        protected Rectangle M(Rectangle r) { return Rtl ? new Rectangle(ClientSize.Width - r.Right, r.Y, r.Width, r.Height) : r; }

        protected bool IsHot { get { return hot; } }
        protected bool IsDown { get { return down; } }

        protected void Animate() { RmAnimator.Run(animStep); }

        bool AnimStep()
        {
            if (IsDisposed) return false;
            int ms = Theme.AnimMs;
            hover = RmAnimator.Step(hover, hot && Enabled ? 1 : 0, ms);
            press = RmAnimator.Step(press, down ? 1 : 0, ms / 2);
            bool more = AnimateMore();
            Invalidate();
            return more || hover != (hot && Enabled ? 1 : 0) || press != (down ? 1 : 0);
        }

        /// <summary>Extra per-frame animation of a control (return true for more frames).</summary>
        protected virtual bool AnimateMore() { return false; }

        protected override void OnMouseEnter(EventArgs e) { hot = true; Animate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { hot = false; down = false; Animate(); base.OnMouseLeave(e); }
        protected override void OnMouseDown(MouseEventArgs e) { if (e.Button == MouseButtons.Left) { down = true; Animate(); if (CanFocus && TabStop) Focus(); } base.OnMouseDown(e); }
        protected override void OnMouseUp(MouseEventArgs e) { down = false; Animate(); base.OnMouseUp(e); }
        protected override void OnGotFocus(EventArgs e) { Invalidate(); base.OnGotFocus(e); }
        protected override void OnLostFocus(EventArgs e) { Invalidate(); base.OnLostFocus(e); }
        protected override void OnEnabledChanged(EventArgs e) { Invalidate(); base.OnEnabledChanged(e); }
        protected override void OnTextChanged(EventArgs e) { Invalidate(); base.OnTextChanged(e); }
        protected override void OnRightToLeftChanged(EventArgs e) { Invalidate(); base.OnRightToLeftChanged(e); }

        protected override void OnPaintBackground(PaintEventArgs e)
        {
            if (BackColor.A == 255) { using (var b = new SolidBrush(BackColor)) e.Graphics.FillRectangle(b, ClientRectangle); return; }
            base.OnPaintBackground(e);
            if (BackColor.A == 0 && Parent == null) using (var b = new SolidBrush(Theme.Window)) e.Graphics.FillRectangle(b, ClientRectangle);
        }

        /// <summary>The colour of the surface the control stands on (for anti-aliased edges / cut-outs).</summary>
        protected Color Surface()
        {
            if (BackColor.A == 255) return BackColor;
            for (var p = Parent; p != null; p = p.Parent) if (p.BackColor.A == 255) return p.BackColor;
            return Theme.Window;
        }

        protected Color Fore(RmTheme t)
        {
            if (!Enabled) return t.DisabledText;
            return HasFore ? ForeColor : t.WindowText;
        }

        protected void FocusCue(Graphics g, Rectangle r, RmTheme t, float radius)
        {
            if (!Focused || !ShowFocusCues) return;
            using (var p = new Pen(RmDraw.Alpha(t.Accent, 160), 1f) { DashStyle = DashStyle.Dot })
            {
                var old = g.SmoothingMode; g.SmoothingMode = SmoothingMode.AntiAlias;
                using (var path = RmDraw.Round(r, radius)) g.DrawPath(p, path);
                g.SmoothingMode = old;
            }
        }

        // BM_CLICK (automation, tests, accessibility tools) acts like a mouse click
        protected override void WndProc(ref Message m)
        {
            if (m.Msg == 0x00F5 && Enabled) { OnClick(EventArgs.Empty); m.Result = IntPtr.Zero; return; }
            base.WndProc(ref m);
        }

        /// <summary>Accessibility role of the control (screen readers, UI Automation).</summary>
        protected virtual AccessibleRole RmRole { get { return AccessibleRole.Client; } }

        protected override AccessibleObject CreateAccessibilityInstance() { return new RmAccessible(this); }

        /// <summary>Items exposed to accessibility tools as children (name, bounds in client coordinates, default
        /// action): ribbon / side bar / status bar items. UI Automation can Invoke them (LegacyIAccessible).</summary>
        protected internal virtual IList<RmAccessibleItem> AccessibleItems() { return null; }

        internal void DoDefault() { if (Enabled) OnClick(EventArgs.Empty); }

        internal bool? CheckedState
        {
            get
            {
                var p = GetType().GetProperty("Checked", typeof(bool));
                return p != null ? (bool?)(bool)p.GetValue(this, null) : null;
            }
        }

        class RmAccessible : ControlAccessibleObject
        {
            readonly RmControl c;
            public RmAccessible(RmControl owner) : base(owner) { c = owner; }
            public override int GetChildCount() { var l = c.AccessibleItems(); return l != null ? l.Count : base.GetChildCount(); }
            public override AccessibleObject GetChild(int index)
            {
                var l = c.AccessibleItems();
                if (l == null) return base.GetChild(index);
                return index >= 0 && index < l.Count ? new RmItemAccessible(c, this, l[index]) : null;
            }
            public override AccessibleRole Role { get { return c.AccessibleRole != AccessibleRole.Default ? c.AccessibleRole : c.RmRole; } }
            public override string Name { get { return !string.IsNullOrEmpty(c.AccessibleName) ? c.AccessibleName : (string.IsNullOrEmpty(c.Text) ? c.Name : c.Text); } set { } }
            public override string DefaultAction { get { return c.RmRole == AccessibleRole.PushButton || c.RmRole == AccessibleRole.CheckButton ? "Press" : base.DefaultAction; } }
            public override void DoDefaultAction() { if (c.RmRole == AccessibleRole.PushButton || c.RmRole == AccessibleRole.CheckButton) c.DoDefault(); else base.DoDefaultAction(); }
            public override AccessibleStates State
            {
                get
                {
                    var s = base.State;
                    var chk = c.CheckedState;
                    if (chk == true) s |= AccessibleStates.Checked;
                    return s;
                }
            }
        }

        // VB-style property protocol of the RAD IDE runtime (Get / Set / Call by name)
        public string RadGet(string prop) { return RmScript.Get(this, prop); }
        public bool RadSet(string prop, string value) { return RmScript.Set(this, prop, value); }
        public string RadCall(string method, string[] args) { return RmScript.Call(this, method, args); }
    }

    /// <summary>The neutral (.form) name of a property whose .NET name differs (Columns -> ColumnsJson ...).</summary>
    [AttributeUsage(AttributeTargets.Property)]
    public sealed class RmNameAttribute : Attribute
    {
        public string Name { get; private set; }
        public RmNameAttribute(string name) { Name = name; }
    }

    /// <summary>An item of a control as accessibility tools see it.</summary>
    public sealed class RmAccessibleItem
    {
        public string Name, Value = "";
        public Rectangle Bounds;
        public Action Invoke;
        public AccessibleRole Role = AccessibleRole.PushButton;
        public bool Checked, Selected;
        public RmAccessibleItem(string name, Rectangle bounds, Action invoke, AccessibleRole role = AccessibleRole.PushButton)
        { Name = name ?? ""; Bounds = bounds; Invoke = invoke; Role = role; }
    }

    /// <summary>Accessible object of one item (child of the control's accessible object).</summary>
    public sealed class RmItemAccessible : AccessibleObject
    {
        readonly Control owner;
        readonly AccessibleObject parent;
        readonly RmAccessibleItem item;
        public RmItemAccessible(Control owner, AccessibleObject parent, RmAccessibleItem item) { this.owner = owner; this.parent = parent; this.item = item; }
        public override string Name { get { return item.Name; } set { } }
        public override string Value { get { return item.Value; } set { } }
        public override AccessibleRole Role { get { return item.Role; } }
        public override AccessibleObject Parent { get { return parent; } }
        public override Rectangle Bounds { get { return owner.RectangleToScreen(item.Bounds); } }
        public override string DefaultAction { get { return item.Invoke != null ? "Press" : ""; } }
        public override void DoDefaultAction() { if (item.Invoke != null) owner.BeginInvoke(item.Invoke); }
        public override AccessibleStates State
        {
            get
            {
                var s = AccessibleStates.Focusable;
                if (item.Checked) s |= AccessibleStates.Checked;
                if (item.Selected) s |= AccessibleStates.Selected;
                return s;
            }
        }
    }

    // ====================================================================== scripting bridge
    /// <summary>Get / Set / Call by name for the RAD IDE runtime (and any script host): public properties and methods
    /// declared in RadIDE.Controls, values as invariant strings. Returns null / false when not handled.</summary>
    public static class RmScript
    {
        static readonly Assembly lib = typeof(RmScript).Assembly;

        static PropertyInfo Prop(object o, string name)
        {
            PropertyInfo alias = null;
            foreach (var p in o.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance))
            {
                if (p.DeclaringType.Assembly != lib || p.GetIndexParameters().Length != 0) continue;
                if (string.Equals(p.Name, name, StringComparison.OrdinalIgnoreCase)) return p;
                var a = (RmNameAttribute)Attribute.GetCustomAttribute(p, typeof(RmNameAttribute));
                if (a != null && string.Equals(a.Name, name, StringComparison.OrdinalIgnoreCase)) alias = p;
            }
            return alias;
        }

        public static string Get(object o, string prop)
        {
            if (o == null || string.IsNullOrEmpty(prop)) return null;
            var p = Prop(o, prop);
            if (p == null || !p.CanRead) return null;
            return ToStr(p.GetValue(o, null));
        }

        public static bool Set(object o, string prop, string value)
        {
            if (o == null || string.IsNullOrEmpty(prop)) return false;
            var p = Prop(o, prop);
            if (p == null || !p.CanWrite) return false;
            p.SetValue(o, FromStr(value, p.PropertyType), null);
            return true;
        }

        public static string Call(object o, string method, string[] args)
        {
            if (o == null || string.IsNullOrEmpty(method)) return null;
            args = args ?? new string[0];
            var cands = o.GetType().GetMethods(BindingFlags.Public | BindingFlags.Instance)
                .Where(m => string.Equals(m.Name, method, StringComparison.OrdinalIgnoreCase) && m.DeclaringType.Assembly == lib && !m.IsSpecialName)
                .OrderBy(m => m.GetParameters().Length == args.Length ? 0 : 1).ToList();
            foreach (var m in cands)
            {
                var ps = m.GetParameters();
                if (args.Length > ps.Length) continue;
                if (ps.Skip(args.Length).Any(x => !x.IsOptional)) continue;
                var call = new object[ps.Length];
                try
                {
                    for (int i = 0; i < ps.Length; i++) call[i] = i < args.Length ? FromStr(args[i], ps[i].ParameterType) : ps[i].DefaultValue;
                }
                catch (Exception) { continue; }
                object r;
                try { r = m.Invoke(o, call); }
                catch (TargetInvocationException ex) { throw ex.InnerException ?? ex; }
                return m.ReturnType == typeof(void) ? "" : ToStr(r);
            }
            if (args.Length == 0) return Get(o, method);
            return null;
        }

        public static string ToStr(object v)
        {
            if (v == null) return "";
            if (v is bool) return (bool)v ? "True" : "False";
            if (v is Color) return RmDraw.Hex((Color)v);
            if (v is DateTime) return ((DateTime)v).ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture);
            if (v is IFormattable) return ((IFormattable)v).ToString(null, CultureInfo.InvariantCulture);
            return v.ToString();
        }

        public static object FromStr(string s, Type t)
        {
            s = s ?? "";
            if (t == typeof(string)) return s;
            if (t == typeof(object)) return s;
            if (t == typeof(bool)) { var l = s.Trim().ToLowerInvariant(); return l == "true" || l == "1" || l == "-1" || l == "yes" || l == "on"; }
            if (t == typeof(int)) return (int)Math.Round(double.Parse(s.Trim().Length == 0 ? "0" : s, NumberStyles.Float, CultureInfo.InvariantCulture));
            if (t == typeof(double)) return double.Parse(s.Trim().Length == 0 ? "0" : s, NumberStyles.Float, CultureInfo.InvariantCulture);
            if (t == typeof(float)) return float.Parse(s.Trim().Length == 0 ? "0" : s, NumberStyles.Float, CultureInfo.InvariantCulture);
            if (t == typeof(decimal)) return decimal.Parse(s.Trim().Length == 0 ? "0" : s, NumberStyles.Float, CultureInfo.InvariantCulture);
            if (t == typeof(Color)) return RmDraw.Parse(s);
            if (t == typeof(DateTime))
            {
                DateTime d;
                return DateTime.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.None, out d) ? d : DateTime.Today;
            }
            if (t.IsEnum) return Enum.Parse(t, s.Trim().Replace(" ", ""), true);
            if (t == typeof(Image)) return RmImages.Load(s);
            if (t == typeof(string[])) return s.Split(';');
            return Convert.ChangeType(s, t, CultureInfo.InvariantCulture);
        }

        /// <summary>Text of a ';' list (trimmed, empty parts dropped).</summary>
        public static List<string> Split(string s)
        {
            return (s ?? "").Split(';').Select(x => x.Trim()).Where(x => x.Length > 0).ToList();
        }
    }
}
