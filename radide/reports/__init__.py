"""Banded reports (Report Designer, ReportViewer control).

* ``radreport.py`` - the runtime/engine, copied into every project that uses reports (``copy_runtime``).
* ``designer.py`` - the Report Designer document (PyQt6).
* ``radide/features/report_designer.py`` - IDE integration (Project > Add Report, Solution Explorer, Toolbox).
"""
from __future__ import annotations

from pathlib import Path

from . import radreport

RUNTIME = Path(__file__).with_name("radreport.py")
REPORT_EXT = ".rpt.json"


def list_reports(folder) -> list[Path]:
    folder = Path(folder)
    if not folder.is_dir():
        return []
    return sorted(folder.glob("*" + REPORT_EXT), key=lambda p: p.name.lower())


def copy_runtime(folder) -> Path | None:
    """Copy radreport.py into *folder* when missing or different. Returns the target (None on error)."""
    dst = Path(folder) / "radreport.py"
    try:
        src = RUNTIME.read_bytes()
        if not dst.exists() or dst.read_bytes() != src:
            dst.write_bytes(src)
        return dst
    except OSError:
        return None


def uses_reports(folder, forms=()) -> bool:
    """True when the project has reports or a form with a ReportViewer control."""
    if list_reports(folder):
        return True
    for f in forms:
        try:
            if any(c.type == "ReportViewer" for c in f.controls):
                return True
        except AttributeError:
            continue
    return False


def report_name(path) -> str:
    n = Path(path).name
    return n[:-len(REPORT_EXT)] if n.lower().endswith(REPORT_EXT) else Path(path).stem


def _is_number(rows, col) -> bool:
    vals = [r.get(col) for r in rows[:100] if r.get(col) not in (None, "")]
    return bool(vals) and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals)


def wizard_report(name: str, title: str, data_source: dict, columns: list[str], rows: list[dict],
                  group_by: str = "", totals: bool = True, rtl: bool = False, landscape: bool = False,
                  chart: bool = False) -> dict:
    """A ready-made tabular report: title, column headers, detail fields, optional group with subtotals,
    grand totals, page numbers.  *rows* (a sample of the data) tells which columns are numbers."""
    d = radreport.new_report(name)
    d["title"] = title or name
    d["dataSource"] = data_source
    d["rightToLeft"] = bool(rtl)
    d["mirrorLayout"] = bool(rtl)
    if landscape:
        d["page"]["orientation"] = "Landscape"
    pw, _ph = radreport.page_size(d)
    ml, _mt, mr, _mb = radreport.margins(d)
    cw = pw - ml - mr
    cols = [c for c in columns if c != group_by] or list(columns)
    nums = {c for c in cols if _is_number(rows, c)}
    # widths: text columns weigh 2, numbers 1
    weights = [1.0 if c in nums else 2.0 for c in cols] or [1.0]
    unit = cw / sum(weights)
    xs, x = [], 0.0
    for wgt in weights:
        xs.append((round(x, 1), round(wgt * unit, 1)))
        x += wgt * unit
    accent = "#1F3D7A"
    align = lambda c: "right" if c in nums and not rtl else ("left" if c in nums else ("right" if rtl else "left"))
    b = d["bands"]
    b["reportHeader"] = {"height": 52, "items": [
        {"type": "text", "name": "txtTitle", "x": 0, "y": 0, "w": cw, "h": 30, "text": title or name,
         "fontSize": 18, "bold": True, "color": accent, "align": "right" if rtl else "left"},
        {"type": "text", "name": "txtDate", "x": 0, "y": 30, "w": cw, "h": 16, "text": "{Today():yyyy-MM-dd}",
         "color": "#606060", "align": "right" if rtl else "left"}]}
    head = [{"type": "box", "name": "boxHeader", "x": 0, "y": 1, "w": round(cw, 1), "h": 20, "fill": accent,
             "lineWidth": 0}]
    det = []
    for i, c in enumerate(cols):
        x0, w = xs[i]
        head.append({"type": "text", "name": f"hd{i + 1}", "x": x0, "y": 1, "w": w, "h": 20, "text": c,
                     "bold": True, "color": "#FFFFFF", "align": align(c)})
        det.append({"type": "field", "name": f"fld{i + 1}", "x": x0, "y": 0, "w": w, "h": 18, "field": c,
                    "align": align(c), "format": "N2" if c in nums and any(isinstance(r.get(c), float)
                                                                          for r in rows[:100]) else ""})
    b["pageHeader"] = {"height": 22, "items": head}
    b["detail"] = {"height": 18, "alternateColor": "#F3F6FA", "items": det}

    def sums(prefix):
        out = []
        for i, c in enumerate(cols):
            if c in nums and totals:
                x0, w = xs[i]
                out.append({"type": "expression", "name": f"{prefix}{i + 1}", "x": x0, "y": 4, "w": w, "h": 18,
                            "expression": f"Sum({c!r})", "format": "N2", "bold": True, "align": align(c)})
        return out

    if group_by:
        g = radreport.new_group(group_by, "Group1")
        g["header"] = {"height": 26, "back": "#E8EEF7", "items": [
            {"type": "text", "name": "txtGroup", "x": 4, "y": 3, "w": cw - 8, "h": 20,
             "text": f"{group_by}: {{Fields[{group_by!r}]}}", "bold": True, "fontSize": 11, "color": accent,
             "align": "right" if rtl else "left"}]}
        g["footer"] = {"height": 26, "items": [
            {"type": "line", "name": "lnGroup", "x": 0, "y": 1, "w": cw, "h": 2, "lineColor": "#A0A0A0"},
            {"type": "text", "name": "txtGroupCount", "x": 0, "y": 4, "w": xs[0][1], "h": 18,
             "text": "{Count()} rows", "color": "#606060", "align": "right" if rtl else "left"}] + sums("gsum")}
        d["groups"] = [g]
    rf = [{"type": "line", "name": "lnTotal", "x": 0, "y": 1, "w": cw, "h": 2, "lineWidth": 1.5,
           "lineColor": accent},
          {"type": "text", "name": "txtTotal", "x": 0, "y": 4, "w": xs[0][1], "h": 18, "text": "Total: {Count()} rows",
           "bold": True, "align": "right" if rtl else "left"}] + sums("tot")
    height = 30
    if chart and nums:
        cat = group_by or next((c for c in cols if c not in nums), "")
        if cat:
            rf.append({"type": "chart", "name": "chart1", "x": 0, "y": 32, "w": cw, "h": 180, "chartType": "bar",
                       "category": cat, "valueField": sorted(nums, key=cols.index)[0], "aggregate": "sum",
                       "title": f"{sorted(nums, key=cols.index)[0]} by {cat}"})
            height = 220
    b["reportFooter"] = {"height": height, "items": rf}
    b["pageFooter"] = {"height": 22, "items": [
        {"type": "text", "name": "txtPage", "x": 0, "y": 4, "w": cw, "h": 16, "text": "Page {PageNumber} of {TotalPages}",
         "align": "center", "fontSize": 8, "color": "#606060"}]}
    return d


def new_report_file(folder, name: str, definition: dict | None = None) -> Path:
    path = Path(folder) / f"{name}{REPORT_EXT}"
    radreport.save_definition(definition or radreport.new_report(name), path)
    copy_runtime(folder)
    return path


__all__ = ["radreport", "RUNTIME", "REPORT_EXT", "list_reports", "copy_runtime", "uses_reports", "report_name",
           "wizard_report", "new_report_file"]
