"""Fault knowledge base for the car diagnostics tools (docs/CARDIAG.md "Fault knowledge base").

    from radide.cardiag import kb
    kb.lookup("P0217")            # dict: title / title_ar, explain / explain_ar, causes / causes_ar (ranked),
                                  #       checks / checks_ar (step by step), severity, drive, safety, related ...
    kb.lookup("C0035-1F")         # UDS DTC with a failure-type byte: base code + the failure type explained
    kb.search("سخونية")           # [(code, score)] by code, words or symptom - English and Arabic
    kb.import_pack("vw.csv")      # manufacturer-specific definitions supplied by the user (CSV / JSON)

The generic entries live in JSON shards (data/*.json, built by ``python -m radide.cardiag.kb.builder``). Entry fields
in a shard: title [en, ar], explain [en, ar], causes / checks (text ids into the shard's "texts"), severity
(green / amber / red), drive (yes / caution / no), related, system, monitor, tags (symptom ids, vocab.TAGS), pids
(OBD mode 01 PIDs worth watching), safety, emissions, source. Titles of generic codes follow SAE J2012; every
explanation, cause and check is RAD IDE's own text.

Manufacturer-specific codes (P1xxx, P30-P33, B1/B2, C1/C2, U1/U2) are only described from packs the user imports;
otherwise lookup() says "manufacturer-specific - meaning varies".
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import threading
from pathlib import Path

from . import vocab
from .ftb import ftb_text

DATA = Path(__file__).resolve().parent / "data"
SHARDS = ("p0", "p2", "p3", "u", "b", "c")
SEVERITIES = ("green", "amber", "red")
DRIVES = ("yes", "caution", "no")
PACK_FORMAT = "radide-cardiag-dtc-pack"

_CODE = re.compile(r"^([PCBU])([0-3])([0-9A-F])([0-9A-F]{2})(?:[-\s:]?([0-9A-F]{2}))?$")
_lock = threading.RLock()
_codes: dict[str, dict] | None = None          # code -> raw entry with texts resolved
_meta: dict = {}
_index: list | None = None                     # [(code, norm_en, norm_ar, tags)]
_packs: list[dict] | None = None               # user packs [{name, make, codes: {code: entry}}]


# ============================================================================================ loading
def _load() -> dict[str, dict]:
    global _codes, _meta
    with _lock:
        if _codes is not None:
            return _codes
        codes: dict[str, dict] = {}
        for sh in SHARDS:
            p = DATA / f"{sh}.json"
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            texts = d.get("texts", {})
            for code, e in d.get("codes", {}).items():
                e = dict(e)
                e["causes"] = [list(texts.get(t, [t, t])) for t in e.get("causes", [])]
                e["checks"] = [list(texts.get(t, [t, t])) for t in e.get("checks", [])]
                codes[code] = e
        try:
            _meta = json.loads((DATA / "meta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _meta = {}
        _codes = codes
        return codes


def reload() -> None:
    """Forget cached shards, packs and the search index (after a rebuild or a pack import)."""
    global _codes, _index, _packs
    with _lock:
        _codes = _index = _packs = None


def codes() -> list[str]:
    return sorted(_load())


def normalize_code(code: str) -> tuple[str, int | None] | None:
    """("P0217", None) / ("C0035", 0x1F) for "p0217", "C0035-1F", "C0035 1F", "C00351F"; None if not a DTC."""
    c = re.sub(r"\s+", "", str(code or "").upper())
    c = c.replace("–", "-")
    m = _CODE.match(c) if len(c) != 7 or "-" in c else _CODE.match(c[:5] + "-" + c[5:])
    if not m:
        return None
    base = "".join(m.group(i) for i in range(1, 5))
    return base, (int(m.group(5), 16) if m.group(5) else None)


def manufacturer_specific(code: str) -> bool:
    c = (code or "").upper()
    return c[:2] in ("P1", "C1", "C2", "B1", "B2", "U1", "U2") or c[:3] in ("P30", "P31", "P32", "P33")


def range_of(code: str) -> list | None:
    """[first, last, "sae"|"mfr", system, en, ar] of the J2012 range that contains *code*."""
    _load()
    c = code.upper()
    best = None
    for r in _meta.get("ranges", []):
        if r[0][0] == c[0] and r[0] <= c <= r[1]:
            if best is None or (int(r[1][1:], 16) - int(r[0][1:], 16)) < (int(best[1][1:], 16) - int(best[0][1:], 16)):
                best = r
    return best


# ============================================================================================ lookup
def _pair(v, default="") -> list:
    if isinstance(v, (list, tuple)):
        if len(v) >= 2:
            return [str(v[0] or ""), str(v[1] or v[0] or "")]
        if len(v) == 1:
            return [str(v[0]), str(v[0])]
    if isinstance(v, dict):
        return [str(v.get("en", "") or ""), str(v.get("ar", "") or v.get("en", "") or "")]
    s = str(v or default)
    return [s, s]


def _flat(code: str, e: dict, ftb: int | None, source: str, make: str = "") -> dict:
    title, explain = _pair(e.get("title")), _pair(e.get("explain"))
    causes = [_pair(c) for c in e.get("causes", [])]
    checks = [_pair(c) for c in e.get("checks", [])]
    sev = e.get("severity", "") if e.get("severity", "") in SEVERITIES else ""
    drive = e.get("drive", "") if e.get("drive", "") in DRIVES else ""
    drive_txt = _pair(_meta.get("drive", {}).get(drive, ["", ""])) if drive else ["", ""]
    sys_ = e.get("system", "")
    mon = e.get("monitor", "")
    full = code + (f"-{ftb:02X}" if ftb is not None else "")
    out = {
        "code": full, "base": code, "ftb": ftb, "ftb_text": ftb_text(ftb) if ftb is not None else ["", ""],
        "title": title[0], "title_ar": title[1], "explain": explain[0], "explain_ar": explain[1],
        "causes": [c[0] for c in causes], "causes_ar": [c[1] for c in causes],
        "checks": [c[0] for c in checks], "checks_ar": [c[1] for c in checks],
        "severity": sev, "severity_text": vocab.name(vocab.SEVERITY, sev, "en") if sev else "",
        "severity_text_ar": vocab.name(vocab.SEVERITY, sev, "ar") if sev else "",
        "drive": drive, "drive_text": drive_txt[0], "drive_text_ar": drive_txt[1],
        "safe_to_drive": {"yes": True, "no": False}.get(drive), "related": list(e.get("related", [])),
        "system": sys_, "system_name": vocab.name(vocab.SYSTEMS, sys_, "en") if sys_ else "",
        "system_name_ar": vocab.name(vocab.SYSTEMS, sys_, "ar") if sys_ else "",
        "monitor": mon, "monitor_name": vocab.name(vocab.MONITORS, mon, "en") if mon else "",
        "monitor_name_ar": vocab.name(vocab.MONITORS, mon, "ar") if mon else "",
        "tags": list(e.get("tags", [])), "pids": [int(p) for p in e.get("pids", [])],
        "safety": bool(e.get("safety")), "emissions": bool(e.get("emissions")),
        "obd_emissions": code[0] == "P" and (code[1] in "02" or code[1:3] == "34"),
        "source": source, "specific": manufacturer_specific(code), "make": make, "known": source != "range",
    }
    out["text"], out["text_ar"] = out["explain"], out["explain_ar"]          # aliases used by other slices
    out["name"], out["name_ar"] = out["title"], out["title_ar"]
    return out


def _fallback(code: str, ftb: int | None) -> dict:
    r = range_of(code)
    specific = manufacturer_specific(code)
    grp = [r[4], r[5]] if r else ["Unknown group", "مجموعة غير معروفة"]
    if specific:
        title = ["Manufacturer-specific code - meaning varies", "كود خاص بالشركة المصنّعة - المعنى يختلف"]
        explain = [f"{code} is in a range that each manufacturer defines for itself ({grp[0]}). The same number means "
                   "different things on different makes, so RAD IDE cannot say what it means without the "
                   "manufacturer's definition. Import a definition pack for this make (Packs tab) or check the "
                   "manufacturer's service information.",
                   f"{code} يقع في مدى تحدده كل شركة مصنّعة بنفسها ({grp[1]}). نفس الرقم معناه مختلف من ماركة "
                   "لأخرى، لذلك لا يستطيع RAD IDE معرفة معناه بدون تعريف الشركة. استورد حزمة تعريفات لهذه الماركة "
                   "(تبويب الحزم) أو راجع معلومات الخدمة من الشركة المصنّعة."]
    else:
        title = [f"Generic code ({grp[0]})", f"كود عام ({grp[1]})"]
        explain = [f"{code} is a generic (SAE) code in the group \"{grp[0]}\", but it is not described in RAD IDE's "
                   "knowledge base yet. Look at the related system and at the freeze frame to narrow it down.",
                   f"{code} كود عام (SAE) في مجموعة \"{grp[1]}\"، لكنه غير موصوف في قاعدة معارف RAD IDE بعد. "
                   "انظر للنظام المرتبط به ولقطة التجميد (Freeze frame) لتحديد السبب."]
    e = {"title": title, "explain": explain, "system": r[3] if r else "", "causes": [], "checks": [],
         "severity": "", "drive": ""}
    out = _flat(code, e, ftb, "range")
    out["group"], out["group_ar"] = grp
    return out


def lookup(code: str, make: str = "") -> dict | None:
    """Everything known about *code* (see the module docstring), or None when *code* is not a DTC.

    User packs come first for manufacturer-specific codes (a pack with a matching *make* before a pack without one);
    a pack can also add text to generic codes when the generic entry is missing."""
    n = normalize_code(code)
    if n is None:
        return None
    base, ftb = n
    data = _load()
    specific = manufacturer_specific(base)
    pk = _pack_entry(base, make)
    if pk is not None and (specific or base not in data):
        entry, pname, pmake = pk
        return _flat(base, entry, ftb, f"pack:{pname}", pmake)
    e = data.get(base)
    if e is not None:
        return _flat(base, e, ftb, e.get("source", "generic"))
    return _fallback(base, ftb)


explain = lookup          # names other slices try (service/dtc.py, features/cardiag_scan.py)
get = lookup


def text(info: dict, field: str, lang: str = "en"):
    """info[field] in *lang* (falls back to English)."""
    if lang == "ar":
        v = info.get(field + "_ar")
        if v:
            return v
    return info.get(field, "")


def describe(code: str, lang: str = "en") -> str:
    """One line: "P0217 - Engine Coolant Over Temperature Condition"."""
    info = lookup(code)
    if info is None:
        return str(code)
    return f"{info['code']} - {text(info, 'title', lang)}"


def related_codes(code: str) -> list[str]:
    info = lookup(code)
    return info["related"] if info else []


def codes_for_system(system: str) -> list[str]:
    return sorted(c for c, e in _load().items() if e.get("system") == system)


def codes_for_tag(tag: str) -> list[str]:
    return sorted(c for c, e in _load().items() if tag in e.get("tags", []))


# ============================================================================================ search
def _build_index() -> list:
    global _index
    with _lock:
        if _index is not None:
            return _index
        idx = []
        for code, e in _load().items():
            t = _pair(e.get("title"))
            x = _pair(e.get("explain"))
            idx.append((code, vocab.norm(t[0]), vocab.norm(t[1]), vocab.norm(x[0] + " " + x[1]),
                        list(e.get("tags", [])), e.get("system", "")))
        for p in _packs_loaded():
            for code, e in p["codes"].items():
                t = _pair(e.get("title"))
                x = _pair(e.get("explain"))
                idx.append((code, vocab.norm(t[0]), vocab.norm(t[1]), vocab.norm(x[0] + " " + x[1]),
                            list(e.get("tags", [])), e.get("system", "")))
        _index = idx
        return idx


def symptom_tags(query: str) -> list[str]:
    """Symptom ids (vocab.TAGS) whose words appear in *query* ("الموتور بيسخن" -> ["overheating"])."""
    q = " " + vocab.norm(query) + " "
    found = []
    for tag, words in vocab.tag_words().items():
        for w in words:
            if not w:
                continue
            if (len(w) <= 3 and f" {w} " in q) or (len(w) > 3 and w in q):
                found.append(tag)
                break
    return found


_STOP = {"the", "a", "an", "is", "of", "and", "or", "in", "on", "my", "car", "engine", "code", "في", "من", "على",
         "عربيه", "العربيه", "سياره", "السياره", "الموتور", "المحرك", "كود", "و", "مع", "ال", "هي", "عندي"}
_WEAK = {"لمبه", "لمبة", "light", "lamp", "circuit", "دائره", "الدائره", "sensor", "حساس", "system", "نظام", "منوره",
         "on", "high", "low", "عالي", "منخفض"}


def search(query: str, limit: int = 60, system: str = "", severity: str = "") -> list[tuple[str, float]]:
    """[(code, score)] best first. Matches a code or a code prefix ("P01", "c0035-1f"), symptom words in English or
    Arabic (incl. Egyptian colloquial: "سخونية", "بترج", "مش بتدور") and words of the titles / explanations."""
    q = (query or "").strip()
    if not q and not system and not severity:
        return []
    data = _load()
    scores: dict[str, float] = {}
    uq = q.upper().replace(" ", "")
    n = normalize_code(uq)
    if n is not None:
        scores[n[0]] = 1000.0
        for r in (lookup(n[0]) or {}).get("related", []):
            scores.setdefault(r, 50.0)
    elif re.fullmatch(r"[PCBU][0-3][0-9A-F]{0,3}", uq):
        for c in data:
            if c.startswith(uq):
                scores[c] = 500.0 - len(scores) * 0.001
    else:
        tags = symptom_tags(q)
        words = [w for w in vocab.norm(q).split() if w not in _STOP and len(w) > 1]
        for code, ten, tar, tx, etags, _sys in _build_index():
            s = 0.0
            for t in tags:
                if t in etags:
                    s += 40.0 if etags[0] == t else (25.0 if etags.index(t) == 1 else 15.0)
            for w in words:
                weak = w in _WEAK
                if w in ten or w in tar:
                    s += 2.0 if weak else (12.0 if len(w) > 3 else 6.0)
                elif len(w) > 3 and not weak and w in tx:
                    s += 3.0
            if words and all(w in ten or w in tar for w in words):
                s += 20.0
            if s:
                e = data.get(code, {})
                s += {"red": 1.5, "amber": 1.0}.get(e.get("severity", ""), 0.0)
                scores[code] = max(scores.get(code, 0.0), s)
    if system or severity:
        if not q:
            scores = {c: 1.0 for c in data}
        scores = {c: s for c, s in scores.items()
                  if (not system or data.get(c, {}).get("system") == system)
                  and (not severity or data.get(c, {}).get("severity") == severity)}
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]


# ============================================================================================ stats / validation
def stats() -> dict:
    """Coverage: {"total", "by_prefix": {"P0": n, ...}, "by_severity", "by_system", "safety", "packs"}."""
    data = _load()
    by_prefix: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    by_sys: dict[str, int] = {}
    for c, e in data.items():
        k = c[:2] if c[:3] != "P34" else "P34"
        by_prefix[k] = by_prefix.get(k, 0) + 1
        by_sev[e.get("severity", "")] = by_sev.get(e.get("severity", ""), 0) + 1
        by_sys[e.get("system", "")] = by_sys.get(e.get("system", ""), 0) + 1
    return {"total": len(data), "by_prefix": by_prefix, "by_severity": by_sev, "by_system": by_sys,
            "safety": sum(1 for e in data.values() if e.get("safety")),
            "packs": [(p["name"], p.get("make", ""), len(p["codes"])) for p in _packs_loaded()]}


_ARABIC = re.compile(r"[؀-ۿ]")


def validate_entry(code: str, e: dict, pack: bool = False) -> list[str]:
    """Problems with one entry (empty list = valid)."""
    errs = []
    if normalize_code(code) is None or normalize_code(code)[1] is not None:
        errs.append(f"{code}: not a 5-character DTC")
    for f in ("title", "explain"):
        v = e.get(f)
        if not (isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, str) and x.strip() for x in v)):
            errs.append(f"{code}: {f} must be [English, Arabic]")
        elif not _ARABIC.search(v[1]):
            errs.append(f"{code}: {f} Arabic text missing")
    if pack:
        return errs
    for f in ("causes", "checks"):
        v = e.get(f)
        if not isinstance(v, list) or not v:
            errs.append(f"{code}: {f} empty")
        else:
            for item in v:
                p = _pair(item)
                if not p[0].strip() or not _ARABIC.search(p[1]):
                    errs.append(f"{code}: {f} item needs English + Arabic")
                    break
    if e.get("severity") not in SEVERITIES:
        errs.append(f"{code}: severity {e.get('severity')!r}")
    if e.get("drive") not in DRIVES:
        errs.append(f"{code}: drive {e.get('drive')!r}")
    if e.get("system") not in vocab.SYSTEMS:
        errs.append(f"{code}: unknown system {e.get('system')!r}")
    if e.get("monitor") and e.get("monitor") not in vocab.MONITORS:
        errs.append(f"{code}: unknown monitor {e.get('monitor')!r}")
    for t in e.get("tags", []):
        if t not in vocab.TAGS:
            errs.append(f"{code}: unknown tag {t!r}")
    for r in e.get("related", []):
        if normalize_code(r) is None:
            errs.append(f"{code}: related {r!r} is not a DTC")
    if not all(isinstance(p, int) and 0 < p < 0xE0 for p in e.get("pids", [])):
        errs.append(f"{code}: pids must be OBD mode 01 PID numbers")
    if e.get("severity") == "red" and e.get("drive") == "yes":
        errs.append(f"{code}: red severity but 'safe to drive'")
    return errs


def validate() -> list[str]:
    """Validate every shard entry; returns the problems found."""
    errs = []
    for code, e in _load().items():
        errs.extend(validate_entry(code, e))
    return errs


# ============================================================================================ user packs
def home() -> Path:
    """Folder for the user's DTC packs (RADIDE_CARDIAG_HOME overrides, shared with the service slice)."""
    env = os.environ.get("RADIDE_CARDIAG_HOME")
    if env:
        p = Path(env)
    else:
        try:
            from ...paths import user_data_dir
            p = user_data_dir() / "cardiag"
        except Exception:  # noqa: BLE001
            p = Path.home() / ".radide" / "cardiag"
    p = p / "dtc-packs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _split_list(v) -> list:
    if isinstance(v, list):
        return v
    if not v:
        return []
    return [s.strip() for s in str(v).split("|") if s.strip()]


def _pack_from_rows(rows: list[dict], name: str, make: str) -> dict:
    out: dict[str, dict] = {}
    for r in rows:
        r = {str(k or "").strip().lower(): (v or "").strip() if isinstance(v, str) else v for k, v in r.items()}
        code = str(r.get("code", "")).strip().upper()
        if not code:
            continue
        t_en = r.get("title") or r.get("title_en") or r.get("description") or ""
        t_ar = r.get("title_ar") or t_en
        x_en = r.get("explain") or r.get("explain_en") or t_en
        x_ar = r.get("explain_ar") or t_ar
        causes_en, causes_ar = _split_list(r.get("causes")), _split_list(r.get("causes_ar"))
        checks_en, checks_ar = _split_list(r.get("checks")), _split_list(r.get("checks_ar"))
        e = {"title": [t_en, t_ar], "explain": [x_en, x_ar],
             "causes": [[c, causes_ar[i] if i < len(causes_ar) else c] for i, c in enumerate(causes_en)],
             "checks": [[c, checks_ar[i] if i < len(checks_ar) else c] for i, c in enumerate(checks_en)],
             "severity": r.get("severity", "") or "", "drive": r.get("drive", "") or "",
             "system": r.get("system", "") or "", "related": _split_list(r.get("related")),
             "tags": [t for t in _split_list(r.get("tags")) if t in vocab.TAGS],
             "safety": str(r.get("safety", "")).lower() in ("1", "true", "yes"),
             "make": r.get("make", "") or make}
        out[code] = e
    return {"format": PACK_FORMAT, "version": 1, "name": name, "make": make, "codes": out}


def parse_pack(path_or_text, name: str = "", make: str = "", fmt: str = "") -> dict:
    """Read a CSV or JSON pack -> {"name", "make", "codes": {code: entry}}. Raises ValueError with the problems.

    CSV columns: code,title,title_ar,explain,explain_ar,causes,causes_ar,checks,checks_ar,severity,drive,system,
    related,tags,make (lists separated by "|"). JSON: {"format": "radide-cardiag-dtc-pack", "name", "make",
    "codes": {code: {title: [en, ar], explain: [en, ar], causes: [[en, ar]...], ...}}} or a list of CSV-like rows."""
    if isinstance(path_or_text, Path) or (isinstance(path_or_text, str) and "\n" not in path_or_text
                                          and Path(path_or_text).is_file()):
        p = Path(path_or_text)
        raw = p.read_text(encoding="utf-8-sig")
        stem = p.stem
        fmt = fmt or ("json" if p.suffix.lower() == ".json" else "csv")
    else:
        raw = str(path_or_text)
        stem = ""
        fmt = fmt or ("json" if raw.lstrip().startswith(("{", "[")) else "csv")
    if fmt == "json":
        d = json.loads(raw)
        if isinstance(d, list):
            pack = _pack_from_rows(d, name or stem or "pack", make)
        else:
            if d.get("format") not in (PACK_FORMAT, None):
                raise ValueError(f"not a DTC pack (format {d.get('format')!r})")
            make = make or d.get("make", "")
            cs = d.get("codes", {})
            if isinstance(cs, list):
                pack = _pack_from_rows(cs, name or d.get("name") or stem or "pack", make)
            else:
                pack = _pack_from_rows([], name or d.get("name") or stem or "pack", make)
                for code, e in cs.items():
                    pack["codes"][str(code).strip().upper()] = {
                        "title": _pair(e.get("title")), "explain": _pair(e.get("explain") or e.get("title")),
                        "causes": [_pair(c) for c in e.get("causes", [])],
                        "checks": [_pair(c) for c in e.get("checks", [])],
                        "severity": e.get("severity", ""), "drive": e.get("drive", ""),
                        "system": e.get("system", ""), "related": list(e.get("related", [])),
                        "tags": [t for t in e.get("tags", []) if t in vocab.TAGS],
                        "safety": bool(e.get("safety")), "make": e.get("make", "") or make}
            pack["name"] = name or d.get("name") or stem or "pack"
    else:
        pack = _pack_from_rows(list(csv.DictReader(io.StringIO(raw))), name or stem or "pack", make)
    errs = []
    for code, e in pack["codes"].items():
        errs.extend(validate_entry(code, e, pack=True))
        if e.get("severity") and e["severity"] not in SEVERITIES:
            errs.append(f"{code}: severity must be green / amber / red")
    if not pack["codes"]:
        errs.append("the pack has no codes")
    if errs:
        raise ValueError("\n".join(errs[:30]))
    for e in pack["codes"].values():
        if e.get("severity") not in SEVERITIES:
            e["severity"] = ""
        if e.get("drive") not in DRIVES:
            e["drive"] = ""
    return pack


def import_pack(path, name: str = "", make: str = "") -> dict:
    """Validate a CSV / JSON pack and store it in home(); returns the pack."""
    pack = parse_pack(path, name, make)
    safe = re.sub(r"[^\w.-]+", "_", pack["name"]).strip("_") or "pack"
    (home() / f"{safe}.json").write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
    reload()
    return pack


def remove_pack(name: str) -> bool:
    for p in home().glob("*.json"):
        try:
            if json.loads(p.read_text(encoding="utf-8")).get("name") == name:
                p.unlink()
                reload()
                return True
        except (OSError, ValueError):
            continue
    return False


def packs() -> list[dict]:
    return list(_packs_loaded())


def _packs_loaded() -> list[dict]:
    global _packs
    with _lock:
        if _packs is not None:
            return _packs
        out = []
        try:
            files = sorted(home().glob("*.json"))
        except OSError:
            files = []
        for p in files:
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                if d.get("format") == PACK_FORMAT and isinstance(d.get("codes"), dict):
                    out.append(d)
            except (OSError, ValueError):
                continue
        _packs = out
        return out


def _pack_entry(code: str, make: str = ""):
    best = None
    mk = (make or "").strip().lower()
    for p in _packs_loaded():
        e = p["codes"].get(code)
        if e is None:
            continue
        emake = (e.get("make") or p.get("make") or "").strip().lower()
        if mk and emake == mk:
            return e, p["name"], e.get("make") or p.get("make", "")
        if best is None and (not emake or not mk):
            best = (e, p["name"], e.get("make") or p.get("make", ""))
    return best


TEMPLATE_CSV = ("code,make,title,title_ar,explain,explain_ar,causes,causes_ar,checks,checks_ar,severity,drive,"
                "system,related,tags\n"
                "P1234,ExampleMake,Example fault title,عنوان العطل كمثال,What the fault means in plain words,"
                "معنى العطل بكلمات بسيطة,First cause|Second cause,السبب الأول|السبب الثاني,"
                "First check|Second check,الفحص الأول|الفحص الثاني,amber,caution,fuel-air,P0171,low-power\n")
