"""Build the DTC knowledge base shards (radide/cardiag/kb/data/*.json) from the sources in this package.

    python -m radide.cardiag.kb.builder          # writes the shards and prints coverage
    python -m radide.cardiag.kb.builder --check  # fails when the shards on disk are out of date

Shard format: {"version": 1, "texts": {id: [en, ar]}, "codes": {code: entry}}; an entry's "causes" / "checks" are lists
of text ids (shared texts are stored once). See radide/cardiag/kb/__init__.py for the entry fields."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from .codes import ROWS
from .components import C
from .extra import EXTRA, RANGES
from .faults import CAUSES, CHECKS, DRIVE, FAULTS
from .special import SPECIAL

DATA = Path(__file__).resolve().parent.parent / "data"
VERSION = 1

# Arabic for the last words of titles (suffix strings used in codes.py)
SFX_AR = {
    "Circuit": "الدائرة", "Circuit/Open": "الدائرة مفتوحة", "Control Circuit/Open": "دائرة التحكم مفتوحة",
    "Control Circuit": "دائرة التحكم", "Control Circuit Low": "دائرة التحكم - جهد منخفض",
    "Control Circuit High": "دائرة التحكم - جهد مرتفع", "Control Circuit Range/Performance": "دائرة التحكم - خارج المدى/أداء",
    "Circuit Range/Performance": "الدائرة - خارج المدى/أداء", "Range/Performance": "خارج المدى/أداء",
    "Circuit Low": "الدائرة - جهد منخفض", "Circuit High": "الدائرة - جهد مرتفع", "Low": "منخفض", "High": "مرتفع",
    "Circuit Intermittent": "الدائرة - متقطعة", "Intermittent": "متقطع", "Intermittent/Erratic": "متقطع/غير منتظم",
    "Circuit Intermittent/Erratic": "الدائرة - متقطعة/غير منتظمة", "Circuit Low Input": "الدائرة - إشارة منخفضة",
    "Intermittent/Erratic/High": "متقطع/غير منتظم/مرتفع", "Circuit No Signal": "الدائرة - لا توجد إشارة",
    "Circuit Malfunction": "عطل في الدائرة", "Electrical": "عطل كهربائي", "Performance": "الأداء",
    "Performance or Stuck Off": "أداء ضعيف أو عالق على الإيقاف", "Stuck On": "عالق على التشغيل", "Stuck Open": "عالق مفتوحًا",
    "Stuck Closed": "عالق مغلقًا", "Stuck Off": "عالق على الإيقاف", "Circuit Open": "الدائرة مفتوحة",
    "Circuit Shorted": "قصر في الدائرة", "Heater Resistance": "مقاومة السخان", "Incorrect Ratio": "نسبة غير صحيحة",
    "Incorrect Flow Detected": "تم اكتشاف تدفق غير صحيح", "Flow": "التدفق", "Circuit or Circuit Low": "الدائرة أو جهد منخفض",
    "Circuit Low Voltage": "جهد منخفض", "Circuit High Voltage": "جهد مرتفع", "Circuit Slow Response": "استجابة بطيئة",
    "Circuit No Activity Detected": "لا يوجد نشاط", "Heater Circuit": "دائرة السخان", "Too Many Pulses": "نبضات زائدة",
    "Too Few Pulses": "نبضات ناقصة", "Intermittent/Erratic Pulses": "نبضات متقطعة/غير منتظمة", "No Pulse": "لا توجد نبضات",
    "Circuit Performance or Stuck Off": "الدائرة - أداء ضعيف أو عالق على الإيقاف", "Circuit Stuck On": "الدائرة - عالق على التشغيل",
    "Circuit Electrical": "الدائرة - عطل كهربائي",
}
# Arabic names for title bases that the component name does not describe well
BASE_AR = {
    "Glow Plug Module Control": "التحكم في وحدة بوجيهات التسخين", "Glow Plug/Heater Indicator Circuit": "دائرة لمبة بوجيهات التسخين",
    "Generator Lamp \"L\" Control": "التحكم في لمبة الدينامو \"L\"", "Generator Lamp Control": "التحكم في لمبة الدينامو",
    "Fuel Cap Lamp Control": "التحكم في لمبة غطاء التانك", "Driver Display Serial Communication": "الاتصال التسلسلي لشاشة السائق",
    "Immobilizer Lamp Control": "التحكم في لمبة منع السرقة", "Speed Control Lamp Control": "التحكم في لمبة مثبت السرعة",
    "Malfunction Indicator Lamp (MIL) Control": "التحكم في لمبة الأعطال (لمبة المحرك MIL)",
    "Engine Hot Lamp Output Control": "التحكم في لمبة سخونة المحرك",
    "1-4 Upshift (Skip Shift) Lamp Control": "التحكم في لمبة التبديل 1-4 (تخطي الغيار)",
    "Transmission Range Display": "شاشة وضع الفتيس", "Control Module VSS Output \"A\"": "مخرج إشارة السرعة \"A\" من وحدة التحكم",
    "Control Module VSS Output \"B\"": "مخرج إشارة السرعة \"B\" من وحدة التحكم",
    "Fuel Injector Control Module Relay Control": "التحكم في ريلاي وحدة الرشاشات", "Engine RPM Output": "مخرج إشارة لفات المحرك",
    "Starter Request": "طلب التشغيل (المارش)", "Starter Disable": "منع التشغيل (المارش)",
    "Generator Field \"F\" Control": "التحكم في ملف مجال الدينامو \"F\"", "Generator Field Terminal": "طرف مجال الدينامو",
    "Cruise Control Servo Control": "التحكم في سيرفو مثبت السرعة",
    "Cruise Control Multi-Function Input \"A\"": "مدخل مفاتيح مثبت السرعة متعددة الوظائف \"A\"",
    "Cruise Control On Signal": "إشارة تشغيل مثبت السرعة", "Cruise Control Off Signal": "إشارة إيقاف مثبت السرعة",
    "Cruise Control Resume Signal": "إشارة استئناف مثبت السرعة", "Cruise Control Set Signal": "إشارة ضبط مثبت السرعة",
    "Cruise Control Coast Signal": "إشارة تخفيض مثبت السرعة", "Cruise Control Accel Signal": "إشارة زيادة مثبت السرعة",
    "Cruise Control Input": "مدخل مثبت السرعة", "Closed Throttle Position Switch": "مفتاح وضع الثروتل المغلق",
    "Throttle/Pedal Position Sensor \"A\" Minimum Stop": "الحد الأدنى لحساس وضع الثروتل/الدواسة \"A\"",
    "Fuel Level Output": "مخرج إشارة مستوى الوقود", "Normal/Performance Switch": "مفتاح الوضع العادي/الرياضي",
    "Reverse Inhibit Control": "التحكم في منع الغيار الخلفي", "Reverse Input": "مدخل الغيار الخلفي", "Reverse Output": "مخرج الغيار الخلفي",
    "Upshift Switch": "مفتاح رفع الغيار", "Downshift Switch": "مفتاح تنزيل الغيار",
    "Traction Control Input Signal": "إشارة مدخل التحكم في الجر",
    "1-4 Upshift (Skip Shift) Solenoid Control": "التحكم في سولينويد التبديل 1-4 (تخطي الغيار)",
    "Transmission Control System": "نظام التحكم في الفتيس", "Clutch Switch Input": "مدخل مفتاح الكلاتش",
    "Incorrect Gear Ratio": "نسبة الغيار غير صحيحة", "Reverse": "الغيار الخلفي", "Shift Error": "خطأ في التبديل",
    "Fan Rationality Check": "فحص منطقية المروحة", "Fan Circuit Over Current": "تيار زائد في دائرة المروحة",
    "Fan Overspeed": "سرعة المروحة زائدة", "Fan Speed Low": "سرعة المروحة منخفضة", "Fan Speed High": "سرعة المروحة مرتفعة",
    "Clutch Position Control Error": "خطأ في التحكم في وضع الكلاتش", "Exhaust Gas Recirculation": "إعادة تدوير العادم (EGR)",
    "Fuel Pump Primary": "طرمبة البنزين (الدائرة الابتدائية)", "Fuel Pump Secondary": "طرمبة البنزين (الدائرة الثانوية)",
    "Injector Circuit/Open": "رشاش الوقود", "Cold Start Injector 1": "رشاش التشغيل على البارد 1",
    "Cold Start Injector 2": "رشاش التشغيل على البارد 2", "Secondary Air Injection System": "نظام حقن الهواء الثانوي",
}


def _fmt(s: str, comp: dict) -> str:
    return s.replace("{part}", comp["part"]).replace("{part_ar}", comp["part_ar"])


class Texts:
    def __init__(self):
        self.t: dict[str, list[str]] = {}

    def add(self, en: str, ar: str) -> str:
        key = hashlib.sha1((en + "\x00" + ar).encode("utf-8")).hexdigest()[:8]
        self.t.setdefault(key, [en, ar])
        return key


def _text(item, comp, texts: Texts, table) -> str:
    if isinstance(item, str):
        en, ar = table[item]
    else:
        en, ar = item
    return texts.add(_fmt(en, comp), _fmt(ar, comp))


def _ident(base: str) -> tuple[str, str]:
    """Specific numbers / letters of a title base for sentences: ('cylinder 3, "B"', 'الأسطوانة 3، "B"')."""
    en, ar = [], []
    m = re.search(r"Cylinder (\d+)", base)
    if m:
        en.append(f"cylinder {m.group(1)}"); ar.append(f"الأسطوانة {m.group(1)}")
    for L in re.findall(r"\"([A-L])\"", base)[:1]:
        en.append(f"\"{L}\""); ar.append(f"\"{L}\"")
    m = re.search(r"\b(?:Fan|Gear|Sensor|Regulator|Injector) (\d+)\b", base)
    if m and not re.search(r"Cylinder (\d+)", base):
        en.append(m.group(1)); ar.append(m.group(1))
    return ", ".join(en), "، ".join(ar)


def _base_ar(row, comp) -> str:
    base = row["base"]
    if row.get("base_ar"):
        return row["base_ar"]
    if base in BASE_AR:
        return BASE_AR[base]
    name = re.sub(r"\s*\"[A-L]\"", "", comp["n_ar"]).strip()
    if base.startswith("Secondary Air Injection System Switching Valve"):
        name = "صمام تحويل " + name
    elif base.startswith("Secondary Air Injection System Relay"):
        name = "ريلاي " + name
    elif base.startswith("Secondary Air Injection System Pump"):
        name = "طرمبة " + name
    for L in re.findall(r"\"([A-L])\"", base)[:1]:
        name += f" \"{L}\""
    if " Sense" in base:
        name += " - دائرة الاستشعار"
    if "Power/Ground" in base:
        name += " - التغذية/الأرضي"
    if "Primary/Secondary" in base:
        name += " (الابتدائية/الثانوية)"
    elif "Primary" in base:
        name += " - الدائرة الابتدائية"
    if "Relay" in base and "ريلاي" not in name and comp is not C.get("ecm_relay"):
        name += " - الريلاي"
    if "Apply Time" in base:
        name += " - زمن التعشيق"
    if "Motor Current" in base:
        name += " - تيار الموتور"
    elif "Motor" in base and "موتور" not in name:
        name += " - الموتور"
    if "Supply Voltage" in base and "جهد" not in name:
        name += " - جهد التغذية"
    if comp is C["gear"]:
        m = re.match(r"(\d)-(\d) Shift", base)
        if m:
            return f"التبديل من {m.group(1)} إلى {m.group(2)}"
    m = re.search(r"Cylinder (\d+)", base)
    if m:
        name += f" - الأسطوانة {m.group(1)}"
    m = re.search(r"\b(?:Fan|Gear|Sensor|Regulator) (\d+)\b", base)
    if m and not re.search(r"\d$", name):
        name += f" {m.group(1)}"
    return name


def build() -> dict[str, dict]:
    shards: dict[str, dict] = {}
    texts_by_shard: dict[str, Texts] = defaultdict(Texts)

    def shard_of(code: str) -> str:
        return code[:2].lower() if code[0] == "P" else code[0].lower()

    # base = title without suffix and qualifier
    for r in ROWS:
        t = r["title_en"][:len(r["title_en"]) - len(r["q"])] if r["q"] else r["title_en"]
        r["base"] = t[:len(t) - len(r["sfx"])].strip() if r["sfx"] and t.endswith(r["sfx"]) else t.strip()

    groups = defaultdict(list)
    for r in ROWS:
        groups[(r["comp"], r["base"], r["q"])].append(r["code"])
    by_comp = defaultdict(list)
    for r in ROWS:
        by_comp[r["comp"]].append(r["code"])

    for r in ROWS:
        code, comp = r["code"], C[r["comp"]]
        sh = shard_of(code)
        texts = texts_by_shard[sh]
        kind = comp["kind"]
        sp = SPECIAL.get(code)
        if r["fault"] == "special" and sp is None:
            raise SystemExit(f"{code}: special row without an entry in special.py")
        if sp is not None:
            title_ar = sp["title_ar"] + r["q_ar"]
            explain = [sp["en"], sp["ar"]]
            causes = [_text(c, comp, texts, CAUSES) for c in sp["causes"]]
            checks = [_text(c, comp, texts, CHECKS) for c in sp["checks"]]
            sev, drive = sp["sev"], sp["drive"]
            tags = sp["tags"] or comp["tags"]
            related = sp["related"]
            monitor = sp["monitor"] or comp["monitor"]
            safety = sp["safety"] or comp["safety"]
            pids = sp["pids"] if sp["pids"] is not None else comp["pids"]
            emissions = comp["emissions"] if sp["emissions"] is None else sp["emissions"]
        else:
            f = FAULTS[r["fault"]]
            k = kind if kind in f else ("a" if kind == "s" else "s")
            ident_en, ident_ar = _ident(r["base"])
            qq = r["q"].strip().strip("()").lstrip("- ").strip()
            qq_ar = r["q_ar"].strip().strip("()").lstrip("- ").strip()
            spec_en = ", ".join(x for x in (ident_en, qq) if x)
            spec_ar = "، ".join(x for x in (ident_ar, qq_ar) if x)
            module_en = "transmission computer" if comp["system"] == "transmission" else "engine computer"
            module_ar = "كمبيوتر الفتيس" if comp["system"] == "transmission" else "كمبيوتر المحرك"
            if kind == "s":
                intro = (f"The {module_en} reads the {comp['n']}" + (f" ({spec_en})" if spec_en else "") + ".",
                         f"{module_ar} يقرأ إشارة {comp['n_ar']}" + (f" ({spec_ar})" if spec_ar else "") + ".")
            else:
                intro = (f"The {module_en} controls the {comp['n']}" + (f" ({spec_en})" if spec_en else "") + ".",
                         f"{module_ar} يتحكم في {comp['n_ar']}" + (f" ({spec_ar})" if spec_ar else "") + ".")
            fe, fa = f[k]
            explain = [f"{intro[0]} {comp['what']} {fe}", f"{intro[1]} {comp['what_ar']} {fa}"]
            sfx_ar = SFX_AR.get(r["sfx"]) if r["sfx"] else f["ar"]
            if sfx_ar is None:
                sfx_ar = f["ar"]
            title_ar = _base_ar(r, comp) + (" - " + sfx_ar if sfx_ar else "") + r["q_ar"]
            fc = list(f.get("causes_" + k, []))
            cc = list(comp["causes"])
            ordered = (cc + fc) if r["fault"] in ("rp", "perf", "stuck_off", "stuck_on", "ratio", "shift") else fc[:1] + cc + fc[1:]
            causes = []
            for c in ordered:
                tid = _text(c, comp, texts, CAUSES)
                if tid not in causes:
                    causes.append(tid)
            causes = causes[:6]
            fk = list(f.get("checks_" + k, []))
            extra = [c for c in comp["checks"]]
            if "clear" in fk:
                i = fk.index("clear")
                fk = fk[:i] + extra + fk[i:]
            else:
                fk += extra
            checks = []
            for c in fk:
                tid = _text(c, comp, texts, CHECKS)
                if tid not in checks:
                    checks.append(tid)
            checks = checks[:7]
            sev, drive = comp["sev"], comp["drive"]
            if r["fault"] in ("heater", "heater_res"):
                sev, drive = "green", "yes"
            tags, monitor, safety, pids, emissions = comp["tags"], comp["monitor"], comp["safety"], comp["pids"], comp["emissions"]
            sib = [c for c in groups[(r["comp"], r["base"], r["q"])] if c != code]
            if len(sib) < 3:
                n = int(code[1:]) if code[1:].isdigit() else 0
                near = sorted((c for c in by_comp[r["comp"]] if c != code and c not in sib and c[1:].isdigit()),
                              key=lambda c: abs(int(c[1:]) - n))
                sib += near[:4 - len(sib)]
            related = sib[:6]
        entry = dict(title=[r["title_en"], title_ar], explain=explain, causes=causes, checks=checks, severity=sev,
                     drive=drive, related=related, system=comp["system"], monitor=monitor, tags=list(tags), pids=list(pids),
                     safety=bool(safety), emissions=bool(emissions), source="generic")
        shards.setdefault(sh, {})[code] = entry

    for x in EXTRA:
        code = x["code"]
        sh = shard_of(code)
        texts = texts_by_shard[sh]
        dummy = dict(part="part", part_ar="القطعة")
        entry = dict(title=[x["title_en"], x["title_ar"]], explain=[x["en"], x["ar"]],
                     causes=[_text(c, dummy, texts, CAUSES) for c in x["causes"]],
                     checks=[_text(c, dummy, texts, CHECKS) for c in x["checks"]], severity=x["sev"], drive=x["drive"],
                     related=x["related"], system=x["system"], monitor=x["monitor"], tags=x["tags"], pids=[],
                     safety=x["safety"], emissions=False, source=x["source"])
        if code in shards.get(sh, {}):
            raise SystemExit(f"duplicate {code}")
        shards.setdefault(sh, {})[code] = entry

    out = {}
    for sh, codes in shards.items():
        all_codes = set().union(*[set(v) for v in shards.values()])
        for e in codes.values():
            e["related"] = [c for c in e["related"] if c in all_codes]
        out[f"{sh}.json"] = {"version": VERSION, "texts": texts_by_shard[sh].t, "codes": dict(sorted(codes.items()))}
    out["meta.json"] = {"version": VERSION, "drive": {k: list(v) for k, v in DRIVE.items()},
                        "ranges": [list(r) for r in RANGES]}
    return out


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=0, sort_keys=False, separators=(",", ":")) + "\n"


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    out = build()
    stale = []
    for name, obj in out.items():
        p = DATA / name
        text = dumps(obj)
        if "--check" in argv:
            if not p.is_file() or p.read_text(encoding="utf-8") != text:
                stale.append(name)
            continue
        DATA.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    total = 0
    for name, obj in sorted(out.items()):
        if "codes" in obj:
            total += len(obj["codes"])
            print(f"{name}: {len(obj['codes'])} codes, {len(obj['texts'])} shared texts")
    print(f"total {total} codes")
    if stale:
        print("STALE:", stale)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
