"""C# WinForms code -> the RAD IDE C# (GUI Bridge) plugin, by rules ("keep the language").

The bridge's form class is ``public static partial class Form1`` whose controls are RadControl fields
(``lblOut.Text = "Hi"; lstLog.AddItem("x");``) - see radide/runtimes/clients/csharp/Rad.cs.  The WinForms
handler bodies are kept as C# and rewritten where the APIs differ (this., Items.Add, Checked, MessageBox.Show,
Focus, Close ...).  Instance fields and helper methods become static.
"""
from __future__ import annotations

import re


def _rewrite(body: str, controls: dict) -> tuple[str, list[str]]:
    todo = []
    s = re.sub(r"\bthis\.", "", body)
    s = re.sub(r"\b(\w+)\.Items\.Add\(", r"\1.AddItem(", s)
    s = re.sub(r"\b(\w+)\.Items\.Clear\(\)", r"\1.Clear()", s)
    s = re.sub(r"\b(\w+)\.Items\.RemoveAt\(", r"\1.RemoveItem(", s)
    s = re.sub(r"\b(\w+)\.Items\.Count\b", r"\1.ListCount", s)
    s = re.sub(r"\b(\w+)\.SelectedIndex\b", r"\1.ListIndex", s)
    s = re.sub(r"\b(\w+)\.Focus\(\)", r"\1.SetFocus()", s)
    s = re.sub(r"\bMessageBox\.Show\(([^;]*?)(?:,\s*MessageBox\w+\.\w+)*\)", lambda m: f"MsgBox({m.group(1).split(',')[0]})",
               s)
    s = re.sub(r"\bApplication\.Exit\(\)", "End()", s)
    s = re.sub(r"(?<![\w.])Close\(\)", "End()", s)

    def checked(m):
        name = m.group(1)
        if controls.get(name) in ("CheckBox", "RadioButton"):
            return f"Rad.ToBool({name}[\"Checked\"])"
        return m.group(0)
    # assignments first: chk.Checked = x;
    s = re.sub(r"\b(\w+)\.Checked\s*=\s*([^;=][^;]*);", lambda m: f"{m.group(1)}[\"Checked\"] = ({m.group(2)}).ToString();"
               if controls.get(m.group(1)) in ("CheckBox", "RadioButton") else m.group(0), s)
    s = re.sub(r"\b(\w+)\.Checked\b", checked, s)
    s = re.sub(r"\b(\w+)\.Value\b(?!\s*=)", lambda m: f"Rad.ToNumber({m.group(1)}.Value)"
               if controls.get(m.group(1)) in ("NumericUpDown", "TrackBar", "ProgressBar") else m.group(0), s)
    for word in ("Controls", "Invoke", "BeginInvoke", "Paint", "Graphics", "CreateGraphics"):
        if re.search(rf"\b{word}\b", s):
            todo.append(word)
    return s, todo


def cs_form_to_bridge(sf, plugin, is_startup: bool, notes) -> str | None:
    from ..importers.exe import dotnet
    cls = sf.extra.get("cls")
    if cls is None:
        return None
    wiring = sf.extra.get("wiring") or {}
    controls = {c.name: c.type for c in sf.form.controls}
    methods = [m for m in dotnet.class_methods(cls.body) if m["name"] not in ("InitializeComponent", "Dispose",
                                                                               cls.name)]
    fields = {k: v for k, v in dotnet.class_fields(cls.body).items() if k not in controls and k != "components"}
    code = plugin.new_code(sf.form, is_startup)
    fname = sf.code_file.name if sf.code_file else sf.file.name
    # fields -> static fields
    field_lines = []
    for k, (typ, init) in fields.items():
        field_lines.append(f"    static {typ} {k}{' = ' + init if init else ''};")
    handled = {}
    for handler, meth in wiring.items():
        if isinstance(meth, str):
            handled.setdefault(meth, []).append(handler)
    out_methods = []
    for m in methods:
        body, todo = _rewrite(m["body"], controls)
        line = sf.code.find(m["header"].split("(")[0].strip())
        line = sf.code.count("\n", 0, line) + 1 if line >= 0 else 0
        for t in todo:
            notes.add("manual", fname, line, f"{m['name']}: '{t}' is WinForms-only - not available through the GUI "
                                             "Bridge")
        hs = handled.get(m["name"], [])
        if hs:
            first = hs[0]
            i = plugin.find_handler(code, first)
            block = [f"    static void {first}(RadEvent e)", "    {"] + \
                ["        " + ln.strip() if ln.strip() else "" for ln in body.strip("\n").splitlines()] + ["    }"]
            if i >= 0:
                lines = code.splitlines()
                j = i
                while j < len(lines) and lines[j].strip() != "}":
                    j += 1
                lines[i:j + 1] = block
                code = "\n".join(lines) + "\n"
            else:
                out_methods += [""] + block
            for other in hs[1:]:
                out_methods += ["", f"    static void {other}(RadEvent e) => {first}(e);"]
            notes.add("rules", fname, line, f"{m['name']} -> {first}: C# kept, WinForms calls rewritten for the "
                                            "GUI Bridge")
        else:
            header = re.sub(r"\b(private|public|protected|internal)\s+", "", m["header"]).strip()
            header = re.sub(r"^(static\s+)?", "static ", header)
            out_methods += ["", f"    {header}", "    {"] + \
                ["        " + ln.strip() if ln.strip() else "" for ln in body.strip("\n").splitlines()] + ["    }"]
            notes.add("rules", fname, line, f"{m['name']}: helper method kept as a static C# method")
    idx = code.rstrip().rfind("}")
    extra = ([""] + field_lines if field_lines else []) + out_methods
    code = code[:idx].rstrip("\n") + "\n" + "\n".join(extra) + "\n}\n"
    notes.add("approx", fname, 0, f"{sf.name}: GUI Bridge controls exchange text values (RadControl): numbers and "
                                  "booleans read from controls are strings - check conversions")
    return code
