"""Service-function definition packs (JSON / CSV, docs/CARDIAG.md "Service functions").

A pack describes, for one vehicle family, the control units and the service functions RAD IDE may run:

* ``routines``     - RoutineControl 0x31 (KWP2000: 0x31 / 0x33 / 0x32) with preconditions shown as a checklist
                     (optionally checked automatically with a DID read), start parameters, result polling
                     with progress / timeout, stop, and interpretation of the result bytes;
* ``io_controls``  - actuator tests with InputOutputControlByIdentifier 0x2F (KWP2000: 0x30); control is
                     always returned to the control unit afterwards;
* ``adaptations``  - service resets / adaptation values / feature coding written with WriteDataByIdentifier
                     0x2E (read back to verify);
* ``dids``         - how to read / show data identifiers 0x22 (used by preconditions and adaptations).

RAD IDE ships definitions only for its own Demo car simulator (packs/demo_car.json) and an annotated template
(packs/template.json). Packs for real vehicles are imported by the user from documentation they are entitled
to use - RAD IDE never ships guessed manufacturer routine / data identifiers as facts.

**Policy.** The framework is for diagnosis, repairs and normal workshop service. Definitions for immobiliser /
key / PIN functions, odometer changes, or switching off / masking emissions systems and monitors (DPF / EGR /
AdBlue-SCR / lambda "off", readiness faking) are rejected on import (``policy_problems``). A DPF *service
regeneration* is a normal service routine and is allowed.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
from pathlib import Path

from .text import BiText, ui_language
from .transport import Ecu

FORMAT = "radide-cardiag-service-pack"
HERE = Path(__file__).resolve().parent
BUILTIN_DIR = HERE / "packs"

CATEGORIES = {
    "cooling": ("Cooling system", "نظام التبريد"),
    "service": ("Service / maintenance", "الصيانة الدورية"),
    "throttle": ("Throttle / idle", "الخانق / الرالنتي"),
    "battery": ("Battery", "البطارية"),
    "brakes": ("Brakes", "الفرامل"),
    "steering": ("Steering", "التوجيه"),
    "injectors": ("Injectors / fuel", "البخاخات / الوقود"),
    "actuator": ("Actuator tests", "اختبار المشغلات"),
    "dpf_service": ("DPF service regeneration", "تجديد فلتر الجزيئات (صيانة)"),
    "transmission": ("Transmission", "ناقل الحركة"),
    "suspension": ("Suspension", "نظام التعليق"),
    "lighting": ("Lighting", "الإضاءة"),
    "hvac": ("Air conditioning / heating", "التكييف والتدفئة"),
    "airbag": ("Airbag / restraints (service)", "الوسائد الهوائية (صيانة)"),
    "coding": ("Feature coding (user definitions)", "برمجة الخصائص (تعريفات المستخدم)"),
    "adaptation": ("Adaptation", "المواءمة"),
    "other": ("Other", "أخرى"),
}
SAFETY = {
    "brakes": ("Brakes: test the brakes carefully before driving.",
               "الفرامل: اختبر الفرامل بحذر قبل القيادة."),
    "airbag": ("Airbag: a wrong repair can stop the airbag from working or fire it. Ignition off before touching "
               "connectors.", "الوسائد الهوائية: الإصلاح الخاطئ قد يمنع الوسادة من العمل أو يطلقها. أطفئ الإشعال قبل لمس "
               "الموصلات."),
    "steering": ("Steering: check the steering and the steering-angle sensor before driving.",
                 "التوجيه: افحص التوجيه وحساس زاوية المقود قبل القيادة."),
    "overheating": ("Overheating: never open a hot cooling system; an engine that overheats can be damaged "
                    "quickly.", "ارتفاع الحرارة: لا تفتح نظام تبريد ساخنًا أبدًا؛ المحرك الذي ترتفع حرارته قد يتلف بسرعة."),
}

# ---------------------------------------------------------------------------------------------- policy
_EMI = r"(dpf|fap|gpf|opf|egr|adblue|ad-blue|scr|def\s*system|nox|lambda|o2\s*sensor|catalyst|catalytic|cat|evap|swirl|emission\w*)"
_OFF = r"(delet\w*|removal|remove|disabl\w*|kill|bypass\w*|emulat\w*|defeat\w*)"
_BLOCKED_EN = [
    (r"immobili[sz]\w*|\bimmo\b|\bimmo[\s_-]?off\b|transponder|\bwfs\b|\bkessy\b", "immobiliser"),
    (r"\bkey\s*(learn\w*|program\w*|teach\w*|adapt\w*|cod\w*|match\w*|add\w*)\b|\b(pin|cs|safe)[\s_-]?code\b|"
     r"\bsecret\s*key\b|\bkey\s*fob\s*program", "key / PIN"),
    (r"odomet\w*|\bmileage\b|\bodo\b|\b(km|kilomet\w*|miles?|distance)[\s_-]*(reset|change|correct\w*|adjust\w*|set|"
     r"edit|write|clear)\b|\bcluster[\s_-]*(km|mileage|miles)\b", "odometer"),
    (r"\b" + _EMI + r"[\s_-]*(off|aus)\b|\boff[\s_-]*" + _EMI + r"\b", "emissions defeat"),
    (r"\b" + _EMI + r"\b[\s\S]{0,24}\b" + _OFF + r"\b", "emissions defeat"),
    (r"\b" + _OFF + r"\b[\s\S]{0,24}\b" + _EMI + r"\b", "emissions defeat"),
    (r"\breadiness\b[\s\S]{0,24}\b(set|fake\w*|force\w*|complete\w*|spoof\w*|ready)\b|\bfake\w*\s+readiness",
     "readiness faking"),
    (r"\b(dtc|fault|code|monitor|mil|check\s*engine)s?[\s_-]*(off|disable\w*|mask\w*|suppress\w*|hide|hiding)\b|"
     r"\b(disable|mask|suppress|hide)\w*\s+(the\s+)?(dtc|fault|code|monitor|mil|check\s*engine)", "fault masking"),
    (r"\bseed[\s_-]*key\s*(calc\w*|crack\w*|brute\w*|algorithm)|\bbrute[\s_-]?force", "security cracking"),
]
_BLOCKED_AR = [
    (r"إيموبيلايزر|ايموبيلايزر|ايموبلايزر|إيموبلايزر|مانع\s*التشغيل|منع\s*التشغيل", "immobiliser"),
    (r"(برمجة|تعليم|تعريف|إضافة|اضافة)\s*(ال)?مفات?يح|(برمجة|تعليم)\s*(ال)?مفتاح|الرقم\s*السري|كود\s*(ال)?PIN|رمز\s*PIN",
     "key / PIN"),
    (r"عداد\s*(ال)?(مسافات|كيلو\w*|كم|أميال|اميال)|(تعديل|ترجيع|تغيير|تظبيط|ضبط)\s*(ال)?عداد(?!\s*(ال)?صيانة)|"
     r"(تعديل|ترجيع|تغيير|تصفير)\s*(ال)?كيلو\w*", "odometer"),
    (r"(إلغاء|الغاء|حذف|تعطيل|فصل|إزالة|ازالة|قفل|إيقاف|ايقاف)\s*(نظام\s*|صمام\s*|حساس\s*|فلتر\s*)?(الـ?\s*)?"
     r"(DPF|EGR|AdBlue|SCR|FAP|جزيئات|أكسجين|اكسجين|شكمان|كتلايزر|كاتلايزر|انبعاث\w*|ادبلو|أدبلو)",
     "emissions defeat"),
    (r"(إخفاء|اخفاء|تعطيل|كتم)\s*(دائم\s*)?(ال)?(أعطال|اعطال|عطل|كود|أكواد|اكواد|لمبة)\s*(ال)?(انبعاث\w*|المحرك)?\s*دائم",
     "fault masking"),
    (r"(تزييف|تزوير)\s*(ال)?(جاهزية|readiness)", "readiness faking"),
]
_RX = [(re.compile(p, re.I), why) for p, why in _BLOCKED_EN + _BLOCKED_AR]
_POLICY_TEXT = {
    "immobiliser": ("immobiliser functions are not supported", "وظائف مانع التشغيل (الإيموبيلايزر) غير مدعومة"),
    "key / PIN": ("key / PIN programming is not supported", "برمجة المفاتيح أو الرقم السري غير مدعومة"),
    "odometer": ("odometer / mileage changes are not supported", "تعديل عداد المسافات غير مدعوم"),
    "emissions defeat": ("switching off or bypassing emissions systems is not supported",
                         "إلغاء أنظمة الانبعاثات أو تجاوزها غير مدعوم"),
    "readiness faking": ("faking readiness monitors is not supported", "تزييف جاهزية أنظمة المراقبة غير مدعوم"),
    "fault masking": ("permanently hiding / disabling faults or monitors is not supported (clearing faults after a "
                      "repair is supported)", "إخفاء الأعطال أو تعطيل المراقبة بشكل دائم غير مدعوم (مسح الأعطال بعد الإصلاح مدعوم)"),
    "security cracking": ("security-access algorithm cracking is not supported",
                          "كسر خوارزميات الوصول الأمني غير مدعوم"),
}


def policy_reason(text: str) -> str | None:
    """The policy rule *text* breaks ("odometer", "emissions defeat" ...) or None."""
    t = str(text or "")
    if re.search(r"regenerat|تجديد|حرق\s*(ال)?فلتر", t, re.I) and not re.search(
            r"\b(off|delete|removal|remove|disable|bypass)\b|إلغاء|الغاء|حذف|تعطيل|إزالة|ازالة", t, re.I):
        return None                                     # DPF service regeneration is a normal routine
    for rx, why in _RX:
        if rx.search(t):
            if why == "odometer" and re.search(r"service|oil|inspection|interval|maintenance|صيانة|زيت", t, re.I) \
                    and not re.search(r"odomet|mileage|\bodo\b|cluster|عداد\s*(ال)?(مسافات|كيلو)", t, re.I):
                continue                                # "oil service km reset" is a service-interval reset
            return why
    return None


def policy_text(why: str) -> BiText:
    en, ar = _POLICY_TEXT.get(why, (why, why))
    return BiText(f"Not allowed: {en}.", f"غير مسموح: {ar}.")


def _texts_of(entry: dict) -> str:
    keys = ("id", "name", "name_ar", "description", "description_ar", "category", "label", "label_ar")
    return " | ".join(str(entry.get(k) or "") for k in keys if entry.get(k))


def _state_reason(entry: dict) -> str | None:
    for st in entry.get("states") or entry.get("options") or (entry.get("input") or {}).get("options") or []:
        if isinstance(st, dict):
            for k in ("label", "label_ar"):
                why = policy_reason(str(st.get(k) or ""))
                if why:
                    return why
    return None


def policy_problems(pack: dict) -> list[BiText]:
    out = []
    for kind in ("routines", "io_controls", "adaptations", "dids"):
        for e in pack.get(kind) or []:
            if not isinstance(e, dict):
                continue
            why = policy_reason(_texts_of(e)) or _state_reason(e)
            if why:
                t = policy_text(why)
                out.append(BiText(f"{kind} '{e.get('id') or e.get('did')}': {t.en}",
                                  f"{kind} '{e.get('id') or e.get('did')}': {t.ar}"))
    why = policy_reason(" | ".join(str(pack.get(k) or "") for k in ("name", "name_ar", "description")))
    if why:
        out.append(policy_text(why))
    return out


# ---------------------------------------------------------------------------------------------- helpers
def hexbytes(s) -> bytes:
    """'31 01 02 03' / '0x0203' / '' -> bytes (ValueError for bad text)."""
    if s is None:
        return b""
    if isinstance(s, (bytes, bytearray)):
        return bytes(s)
    if isinstance(s, int):
        n = max(1, (s.bit_length() + 7) // 8)
        return s.to_bytes(n, "big")
    t = re.sub(r"0x", "", str(s), flags=re.I)
    t = re.sub(r"[\s,:_-]", "", t)
    if len(t) % 2:
        raise ValueError(f"odd number of hex digits: {s!r}")
    return bytes.fromhex(t)


def ident(s, width: int = 2) -> int:
    """'F405' / '0xF405' / 62469 -> int, checked against width bytes."""
    if isinstance(s, int):
        v = s
    else:
        t = re.sub(r"[\s,:_-]", "", re.sub(r"0x", "", str(s or ""), flags=re.I))
        b = hexbytes(("0" + t) if len(t) % 2 else t)
        if not b:
            raise ValueError("empty identifier")
        v = int.from_bytes(b, "big")
    if v < 0 or v >= 1 << (8 * width):
        raise ValueError(f"identifier {s!r} does not fit in {width} byte(s)")
    return v


def home() -> Path:
    """Where the user's packs, vehicle profiles and audit logs live (RADIDE_CARDIAG_HOME overrides)."""
    env = os.environ.get("RADIDE_CARDIAG_HOME")
    if env:
        p = Path(env)
    else:
        try:
            from ...paths import user_data_dir
            p = user_data_dir() / "cardiag"
        except Exception:  # noqa: BLE001
            p = Path.home() / ".radide" / "cardiag"
    p.mkdir(parents=True, exist_ok=True)
    return p


def packs_dir() -> Path:
    p = home() / "packs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _err(en: str, ar: str) -> BiText:
    return BiText(en, ar)


# ---------------------------------------------------------------------------------------------- validation
_OPS = {"<", "<=", ">", ">=", "==", "!=", "in"}


def _check_bilingual(e: dict, where: str, warnings: list) -> None:
    if not e.get("name"):
        warnings.append(_err(f"{where}: no English name", f"{where}: لا يوجد اسم بالإنجليزية"))
    if not e.get("name_ar"):
        warnings.append(_err(f"{where}: no Arabic name (name_ar)", f"{where}: لا يوجد اسم بالعربية (name_ar)"))


def _check_preconditions(e: dict, where: str, dids: dict, errors: list) -> None:
    pcs = e.get("preconditions") or []
    if not isinstance(pcs, list):
        errors.append(_err(f"{where}: preconditions must be a list", f"{where}: يجب أن تكون الشروط المسبقة قائمة"))
        return
    for i, pc in enumerate(pcs):
        if isinstance(pc, str):
            continue
        if not isinstance(pc, dict) or not (pc.get("text") or pc.get("text_ar")):
            errors.append(_err(f"{where}: precondition {i + 1} needs a text", f"{where}: الشرط {i + 1} يحتاج إلى نص"))
            continue
        chk = pc.get("check")
        if chk:
            try:
                did = ident(chk.get("did"))
            except (ValueError, AttributeError):
                errors.append(_err(f"{where}: precondition {i + 1}: check.did is not a valid identifier",
                                   f"{where}: الشرط {i + 1}: check.did ليس معرّفًا صالحًا"))
                continue
            if f"{did:04X}" not in dids:
                errors.append(_err(f"{where}: precondition {i + 1}: DID {did:04X} is not described in 'dids'",
                                   f"{where}: الشرط {i + 1}: المعرّف {did:04X} غير موصوف في 'dids'"))
            if chk.get("op") not in _OPS:
                errors.append(_err(f"{where}: precondition {i + 1}: op must be one of {' '.join(sorted(_OPS))}",
                                   f"{where}: الشرط {i + 1}: يجب أن تكون op واحدة من {' '.join(sorted(_OPS))}"))


def normalize(pack: dict) -> tuple[dict, list[BiText], list[BiText]]:
    """Check and normalise a pack. Returns (pack, errors, warnings); a pack with errors must not be used."""
    errors: list[BiText] = []
    warnings: list[BiText] = []
    if not isinstance(pack, dict):
        return {}, [_err("The pack must be a JSON object.", "يجب أن تكون الحزمة كائن JSON.")], []
    pack = json.loads(json.dumps(pack))           # private deep copy
    if pack.get("format") not in (None, FORMAT):
        errors.append(_err(f"Unknown format {pack.get('format')!r} (expected {FORMAT})",
                           f"صيغة غير معروفة {pack.get('format')!r} (المتوقع {FORMAT})"))
    pack["format"] = FORMAT
    pack.setdefault("version", 1)
    if not pack.get("name"):
        errors.append(_err("The pack needs a name.", "الحزمة تحتاج إلى اسم."))
    # control units
    ecus = pack.get("ecus") or {}
    if not isinstance(ecus, dict) or not ecus:
        errors.append(_err("The pack needs at least one control unit in 'ecus'.",
                           "الحزمة تحتاج إلى وحدة تحكم واحدة على الأقل في 'ecus'."))
        ecus = {}
    for key in [k for k in ecus if str(k).startswith("_")]:
        del ecus[key]                              # "_help" notes
    for key, ecu in ecus.items():
        if not isinstance(ecu, dict):
            errors.append(_err(f"ecus.{key}: must be an object", f"ecus.{key}: يجب أن يكون كائنًا"))
            continue
        try:
            ecu["tx"] = f"{ident(ecu.get('tx'), 4):03X}"
            ecu["rx"] = f"{ident(ecu.get('rx'), 4):03X}"
        except (ValueError, AttributeError, TypeError):
            errors.append(_err(f"ecus.{key}: tx / rx must be CAN ids in hex (e.g. 7E0 / 7E8)",
                               f"ecus.{key}: يجب أن تكون tx / rx معرّفات CAN بالست عشري (مثل 7E0 / 7E8)"))
            continue
        ecu.setdefault("protocol", "uds")
        if ecu["protocol"] not in ("uds", "kwp"):
            errors.append(_err(f"ecus.{key}: protocol must be 'uds' or 'kwp'", f"ecus.{key}: يجب أن يكون البروتوكول 'uds' أو 'kwp'"))
    # data identifiers
    dids = {}
    for i, d in enumerate(pack.get("dids") or []):
        try:
            did = ident(d.get("did"))
        except (ValueError, AttributeError, TypeError):
            errors.append(_err(f"dids[{i}]: 'did' is not a valid 2-byte identifier",
                               f"dids[{i}]: 'did' ليس معرّفًا صالحًا من بايتين"))
            continue
        d["did"] = f"{did:04X}"
        d.setdefault("bytes", 1)
        d.setdefault("type", "num")
        dids[d["did"]] = d
    pack["dids"] = list(dids.values())

    def ecu_ok(e, where):
        if e.get("ecu") not in ecus:
            errors.append(_err(f"{where}: unknown control unit {e.get('ecu')!r}", f"{where}: وحدة تحكم غير معروفة {e.get('ecu')!r}"))
        if e.get("security_level") not in (None, 0, "") and not isinstance(e.get("security_level"), int):
            errors.append(_err(f"{where}: security_level must be a number", f"{where}: يجب أن يكون security_level رقمًا"))
        if e.get("category", "other") not in CATEGORIES:
            warnings.append(_err(f"{where}: unknown category {e.get('category')!r} (shown as Other)",
                                 f"{where}: فئة غير معروفة {e.get('category')!r} (تُعرض كـ أخرى)"))
            e["category"] = "other"
        e.setdefault("category", "other")

    seen = set()
    for kind in ("routines", "io_controls", "adaptations"):
        lst = pack.get(kind) or []
        if not isinstance(lst, list):
            errors.append(_err(f"'{kind}' must be a list", f"يجب أن تكون '{kind}' قائمة"))
            lst = []
        pack[kind] = lst
        for i, e in enumerate(lst):
            where = f"{kind}[{i}]" + (f" '{e.get('id')}'" if isinstance(e, dict) and e.get("id") else "")
            if not isinstance(e, dict):
                errors.append(_err(f"{where}: must be an object", f"{where}: يجب أن يكون كائنًا"))
                continue
            if not e.get("id"):
                errors.append(_err(f"{where}: needs an 'id'", f"{where}: يحتاج إلى 'id'"))
            elif e["id"] in seen:
                errors.append(_err(f"{where}: duplicate id", f"{where}: معرّف مكرر"))
            seen.add(e.get("id"))
            _check_bilingual(e, where, warnings)
            ecu_ok(e, where)
            _check_preconditions(e, where, dids, errors)
            proto = (ecus.get(e.get("ecu")) or {}).get("protocol", "uds")
            try:
                if kind == "routines":
                    e["rid"] = f"{ident(e.get('rid'), 1 if proto == 'kwp' else 2):0{2 if proto == 'kwp' else 4}X}"
                    hexbytes(e.get("start_params", ""))
                    hexbytes((e.get("stop") or {}).get("params", ""))
                    poll = e.get("poll")
                    if poll:
                        poll.setdefault("interval_s", 1.0)
                        poll.setdefault("timeout_s", 120)
                        poll.setdefault("status_byte", 0)
                        for k in ("running", "done", "failed"):
                            poll[k] = [f"{ident(x, 1):02X}" for x in poll.get(k) or []]
                        if not poll["done"]:
                            errors.append(_err(f"{where}: poll.done must list the status byte(s) meaning 'finished'",
                                               f"{where}: يجب أن تذكر poll.done بايت (أو بايتات) الحالة التي تعني 'انتهى'"))
                elif kind == "io_controls":
                    e["did"] = f"{ident(e.get('did'), 1 if proto == 'kwp' else 2):0{2 if proto == 'kwp' else 4}X}"
                    states = e.get("states") or []
                    if not states:
                        errors.append(_err(f"{where}: needs at least one state to set", f"{where}: يحتاج إلى حالة واحدة على الأقل"))
                    for st in states:
                        hexbytes(st.get("value"))
                    e.setdefault("control", "03")
                    e["max_duration_s"] = max(1, min(float(e.get("max_duration_s", 30)), 600))
                elif kind == "adaptations":
                    e["did"] = f"{ident(e.get('did')):04X}"
                    if "value" in e:
                        hexbytes(e["value"])
                    elif not isinstance(e.get("input"), dict):
                        errors.append(_err(f"{where}: needs a fixed 'value' or an 'input' description",
                                           f"{where}: يحتاج إلى 'value' ثابتة أو وصف 'input'"))
                    e.setdefault("read_back", True)
            except (ValueError, AttributeError, TypeError) as ex:
                errors.append(_err(f"{where}: {ex}", f"{where}: {ex}"))
    errors.extend(policy_problems(pack))
    return pack, errors, warnings


# ---------------------------------------------------------------------------------------------- loading
class PackError(Exception):
    def __init__(self, errors: list[BiText]):
        self.errors = errors
        super().__init__("; ".join(e.en for e in errors[:5]))

    def text(self, lang: str | None = None) -> str:
        return "\n".join(e.get(lang) for e in self.errors)


def load_pack_text(text: str, name: str = "") -> tuple[dict, list[BiText]]:
    try:
        data = json.loads(text)
    except ValueError as e:
        raise PackError([_err(f"{name}: not valid JSON ({e})", f"{name}: ليس JSON صالحًا ({e})")]) from None
    pack, errors, warnings = normalize(data)
    if errors:
        raise PackError(errors)
    return pack, warnings


def load_pack_file(path) -> tuple[dict, list[BiText]]:
    p = Path(path)
    if p.suffix.lower() == ".csv":
        return pack_from_csv(p.read_text(encoding="utf-8-sig"), name=p.stem)
    if p.suffix.lower() in (".odx", ".odx-d", ".pdx"):
        from .odx import pack_from_odx
        return pack_from_odx(p)
    pack, warnings = load_pack_text(p.read_text(encoding="utf-8-sig"), p.name)
    pack["_path"] = str(p)
    return pack, warnings


CSV_COLUMNS = ["kind", "id", "name", "name_ar", "category", "ecu", "tx", "rx", "protocol", "session",
               "security_level", "identifier", "data", "timeout_s", "preconditions", "preconditions_ar"]


def pack_from_csv(text: str, name: str = "CSV pack") -> tuple[dict, list[BiText]]:
    """A simple pack from a CSV table (one row per function; see CSV_COLUMNS and docs/CARDIAG.md):
    kind = routine | io | adaptation | did; identifier = RID / DID; data = start parameters (routine),
    'label=value;label=value' states (io) or the value to write (adaptation); preconditions separated by '|'."""
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise PackError([_err("The CSV file has no rows.", "ملف CSV لا يحتوي على صفوف.")])
    missing = [c for c in ("kind", "id", "identifier") if c not in (rows[0].keys() or [])]
    if missing:
        raise PackError([_err(f"CSV columns missing: {', '.join(missing)}", f"أعمدة CSV ناقصة: {', '.join(missing)}")])
    pack = {"format": FORMAT, "version": 1, "name": name, "name_ar": name, "source": "CSV import",
            "ecus": {}, "routines": [], "io_controls": [], "adaptations": [], "dids": []}
    for r in rows:
        r = {k: (v or "").strip() for k, v in r.items() if k}
        ecu = r.get("ecu") or "ecu"
        if ecu not in pack["ecus"]:
            pack["ecus"][ecu] = {"name": ecu, "tx": r.get("tx") or "7E0", "rx": r.get("rx") or "7E8",
                                 "protocol": r.get("protocol") or "uds"}
        pcs_en = [t.strip() for t in r.get("preconditions", "").split("|") if t.strip()]
        pcs_ar = [t.strip() for t in r.get("preconditions_ar", "").split("|") if t.strip()]
        pcs = [{"text": en, "text_ar": pcs_ar[i] if i < len(pcs_ar) else ""} for i, en in enumerate(pcs_en)]
        base = {"id": r["id"], "name": r.get("name") or r["id"], "name_ar": r.get("name_ar", ""),
                "category": r.get("category") or "other", "ecu": ecu, "session": r.get("session") or "extended",
                "preconditions": pcs}
        if r.get("security_level"):
            try:
                base["security_level"] = int(r["security_level"], 0)
            except ValueError:
                base["security_level"] = r["security_level"]
        kind = r["kind"].lower()
        if kind == "routine":
            base.update(rid=r["identifier"], start_params=r.get("data", ""))
            if r.get("timeout_s"):
                base["poll"] = {"timeout_s": float(r["timeout_s"]), "done": ["02"], "running": ["01"], "failed": ["03"]}
            pack["routines"].append(base)
        elif kind in ("io", "io_control", "actuator"):
            states = []
            for part in r.get("data", "").split(";"):
                if "=" in part:
                    lab, val = part.split("=", 1)
                    states.append({"label": lab.strip(), "value": val.strip()})
            base.update(did=r["identifier"], states=states)
            if r.get("timeout_s"):
                base["max_duration_s"] = float(r["timeout_s"])
            pack["io_controls"].append(base)
        elif kind == "adaptation":
            base.update(did=r["identifier"], value=r.get("data", ""))
            pack["adaptations"].append(base)
        elif kind == "did":
            pack["dids"].append({"did": r["identifier"], "name": base["name"], "name_ar": base["name_ar"],
                                 "bytes": int(r.get("data") or 1)})
        else:
            raise PackError([_err(f"Unknown kind {kind!r} in row {r['id']}", f"نوع غير معروف {kind!r} في الصف {r['id']}")])
    pack, errors, warnings = normalize(pack)
    if errors:
        raise PackError(errors)
    return pack, warnings


def builtin_packs() -> list[dict]:
    out = []
    for p in sorted(BUILTIN_DIR.glob("*.json")):
        if p.stem == "template":
            continue
        try:
            pack, _ = load_pack_file(p)
            pack["_builtin"] = True
            out.append(pack)
        except (PackError, OSError):
            continue
    return out


def demo_pack() -> dict:
    pack, _ = load_pack_file(BUILTIN_DIR / "demo_car.json")
    pack["_builtin"] = True
    return pack


def user_packs() -> list[tuple[dict | None, Path, list[BiText]]]:
    """Every imported pack: (pack or None, path, problems)."""
    out = []
    for p in sorted(packs_dir().glob("*.json")):
        try:
            pack, warnings = load_pack_file(p)
            out.append((pack, p, warnings))
        except PackError as e:
            out.append((None, p, e.errors))
        except OSError as e:
            out.append((None, p, [_err(str(e), str(e))]))
    return out


def import_pack(src) -> tuple[dict, Path, list[BiText]]:
    """Validate *src* (.json / .csv / .odx / .pdx) and copy it (as JSON) into the user's packs folder."""
    pack, warnings = load_pack_file(src)
    pack.pop("_path", None)
    safe = re.sub(r"[^\w.-]+", "_", str(pack.get("name") or Path(src).stem)).strip("_") or "pack"
    dest = packs_dir() / f"{safe}.json"
    dest.write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
    pack["_path"] = str(dest)
    return pack, dest, warnings


def template_text() -> str:
    return (BUILTIN_DIR / "template.json").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------------------------- accessors
def ecu_of(pack: dict, key: str) -> Ecu:
    e = (pack.get("ecus") or {}).get(key)
    if e is None:
        raise KeyError(key)
    return Ecu(key=key, name=e.get("name", key), name_ar=e.get("name_ar", ""), tx=int(e["tx"], 16),
               rx=int(e["rx"], 16), protocol=e.get("protocol", "uds"),
               extra={k: v for k, v in e.items() if k not in ("name", "name_ar", "tx", "rx", "protocol")})


def did_info(pack: dict, did) -> dict | None:
    key = f"{ident(did):04X}"
    return next((d for d in pack.get("dids") or [] if d.get("did") == key), None)


def find(pack: dict, kind: str, ident_: str) -> dict | None:
    return next((e for e in pack.get(kind) or [] if e.get("id") == ident_), None)


def decode_value(info: dict, data: bytes):
    """Decode DID / result bytes with a description {type, bytes, signed, scale, offset, map, unit}."""
    t = info.get("type", "num")
    if t == "ascii":
        return data.decode("ascii", "replace").strip("\x00 ")
    if t == "hex":
        return data.hex(" ").upper()
    n = int.from_bytes(data, "big", signed=bool(info.get("signed")))
    if t == "enum" or info.get("map"):
        m = info.get("map") or {}
        hit = m.get(f"{n:02X}") or m.get(str(n))
        if hit is not None:
            if isinstance(hit, dict):
                return hit.get("ar" if ui_language() == "ar" else "en") or hit.get("en") or str(n)
            return hit
        return n
    v = n * float(info.get("scale", 1)) + float(info.get("offset", 0))
    return int(v) if float(v).is_integer() else round(v, 3)


def numeric_value(info: dict, data: bytes) -> float:
    """The physical number of *data* (scale / offset applied, enum maps ignored) for precondition checks."""
    n = int.from_bytes(data, "big", signed=bool(info.get("signed")))
    v = n * float(info.get("scale", 1)) + float(info.get("offset", 0))
    return int(v) if float(v).is_integer() else v


def format_value(info: dict, value) -> str:
    unit = info.get("unit") or ""
    return f"{value} {unit}".strip()


def category_label(cat: str) -> str:
    en, ar = CATEGORIES.get(cat, CATEGORIES["other"])
    return ar if ui_language() == "ar" else en
