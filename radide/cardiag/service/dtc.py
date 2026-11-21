"""Clearing a specific fault - the flow a workshop follows after a repair.

1. The fault is explained first (fault knowledge base of radide/cardiag when available, otherwise a short
   built-in description) with possible causes, and safety warnings when it concerns the brakes, airbags,
   steering or overheating.
2. The user must confirm that the repair was done.
3. ClearDiagnosticInformation 0x14 with that DTC (3 bytes: the 2-byte code + failure-type byte) when the
   control unit supports it; when it answers that it does not (NRC 0x31 / 0x12 / 0x11), RAD IDE offers to
   clear **all** faults of that control unit instead, with a warning. OBD-II-only connections use mode 04
   (clears every emissions fault and resets the readiness monitors).
4. The fault memory is read again (0x19 02) to show whether the fault came straight back (cause still
   present).

Clearing never hides a fault permanently: if the cause is still there the control unit stores it again.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .runner import Result
from .text import BiText, bi, ui_language
from .transport import Ecu, NegativeResponse, ServiceClient, ServiceError

CLEAR_ALL = b"\xFF\xFF\xFF"
_CODE = re.compile(r"^\s*([PCBU])([0-3])([0-9A-F]{3})(?:[-\s]?([0-9A-F]{2}))?\s*$", re.I)


def parse_code(text: str) -> tuple[str, int | None]:
    """'P0217' / 'p0217-00' / 'C0035 1F' -> ('P0217', ftb or None); ValueError otherwise."""
    m = _CODE.match(str(text or ""))
    if not m:
        raise ValueError(f"not a DTC: {text!r}")
    code = (m.group(1) + m.group(2) + m.group(3)).upper()
    return code, (int(m.group(4), 16) if m.group(4) else None)


def code_bytes(code: str, ftb: int | None = None) -> bytes:
    code, f = parse_code(code) if len(code) != 5 else (code.upper(), None)
    letter = "PCBU".index(code[0])
    v = (letter << 14) | (int(code[1]) << 12) | int(code[2:5], 16)
    return bytes([v >> 8, v & 0xFF, (ftb if ftb is not None else (f or 0)) & 0xFF])


def code_text(b: bytes) -> str:
    """2 or 3 DTC bytes -> 'P0217'."""
    return "PCBU"[b[0] >> 6] + str((b[0] >> 4) & 3) + f"{b[0] & 0xF:X}{b[1]:02X}"


@dataclass
class StoredDtc:
    code: str
    ftb: int
    status: int
    raw: bytes

    @property
    def label(self) -> str:
        return f"{self.code}-{self.ftb:02X}" if self.ftb else self.code

    @property
    def active(self) -> bool:
        return bool(self.status & 0x01)

    @property
    def confirmed(self) -> bool:
        return bool(self.status & 0x08)


# ---------------------------------------------------------------------------------------------- knowledge
_BUILTIN = {      # RAD IDE's own short texts for the Demo car's faults (the full base is radide/cardiag's KB)
    "P0217": ("Engine coolant over-temperature condition", "حالة ارتفاع حرارة سائل تبريد المحرك",
              "The engine got hotter than the control unit allows. Driving on can warp the cylinder head.",
              "وصلت حرارة المحرك إلى أعلى مما تسمح به وحدة التحكم. الاستمرار في القيادة قد يسبب اعوجاج رأس السلندر.",
              ["Low coolant / leak", "Cooling fan not running", "Thermostat stuck closed", "Water pump failure",
               "Air in the cooling system"],
              ["نقص سائل التبريد أو تسريب", "مروحة التبريد لا تعمل", "الثرموستات عالق مغلقًا", "عطل مضخة المياه",
               "هواء في نظام التبريد"]),
    "P0128": ("Coolant thermostat (coolant temperature below thermostat regulating temperature)",
              "ثرموستات التبريد (حرارة السائل أقل من حرارة تنظيم الثرموستات)",
              "The engine warms up too slowly, usually because the thermostat opens too early.",
              "يسخن المحرك ببطء شديد، غالبًا لأن الثرموستات يفتح مبكرًا.",
              ["Thermostat stuck open", "Coolant temperature sensor", "Fan running all the time"],
              ["الثرموستات عالق مفتوحًا", "حساس حرارة السائل", "المروحة تعمل طوال الوقت"]),
    "C0035": ("Left front wheel speed sensor circuit", "دائرة حساس سرعة العجلة الأمامية اليسرى",
              "The ABS unit gets no plausible speed signal from the left front wheel; ABS / ESP may be off.",
              "وحدة ABS لا تستقبل إشارة سرعة منطقية من العجلة الأمامية اليسرى؛ قد يتوقف ABS / ESP.",
              ["Sensor or wiring damaged", "Dirty / damaged tone ring", "Wheel bearing play"],
              ["تلف الحساس أو الأسلاك", "اتساخ أو تلف الحلقة المسننة", "خلوص في رولمان العجلة"]),
    "B0001": ("Driver frontal stage 1 deployment control", "التحكم في انطلاق المرحلة الأولى للوسادة الأمامية للسائق",
              "The airbag unit sees a fault in the driver airbag circuit; the airbag may not deploy.",
              "وحدة الوسائد ترى عطلًا في دائرة وسادة السائق؛ قد لا تنطلق الوسادة.",
              ["Clock spring (steering-wheel coil) worn", "Connector under the steering wheel", "Airbag module"],
              ["تآكل الشريط الحلزوني (الإسبايرال) في المقود", "موصل أسفل المقود", "وحدة الوسادة نفسها"]),
}
_SYS = {"P": ("Powertrain", "نظام الدفع (المحرك وناقل الحركة)"), "C": ("Chassis", "الشاسيه (الفرامل والتوجيه والتعليق)"),
        "B": ("Body", "الهيكل (الوسائد والراحة والإضاءة)"), "U": ("Network", "شبكة الاتصال بين الوحدات")}


def _in(code: str, *ranges) -> bool:
    if code[0] != ranges[0][0][0]:
        return False
    n = int(code[1:], 16)
    return any(int(a[1:], 16) <= n <= int(b[1:], 16) for a, b in ranges)


def safety_topics(code: str, ecu: Ecu | None = None) -> list[str]:
    """'brakes' / 'airbag' / 'steering' / 'overheating' topics of a fault code (and its control unit)."""
    out = []
    name = f"{getattr(ecu, 'key', '')} {getattr(ecu, 'name', '')}".lower()
    if _in(code, ("C0000", "C03FF")) or _in(code, ("P0570", "P0573")) or "abs" in name or "brake" in name:
        out.append("brakes")
    if _in(code, ("B0000", "B01FF")) or "airbag" in name or "srs" in name or "restraint" in name:
        out.append("airbag")
    if _in(code, ("C0400", "C05FF")) or _in(code, ("C0050", "C0052")) or _in(code, ("P0550", "P0554")) \
            or "steer" in name:
        out.append("steering")
    if _in(code, ("P0115", "P0119")) or _in(code, ("P0125", "P0125")) or _in(code, ("P0128", "P0128")) or \
            _in(code, ("P0217", "P0218")) or _in(code, ("P0480", "P0485")) or _in(code, ("P0526", "P0528")) or \
            _in(code, ("P0597", "P0599")) or _in(code, ("P2181", "P2185")) or _in(code, ("P2560", "P2560")):
        out.append("overheating")
    return out


def emissions_related(code: str) -> bool:
    """Generic powertrain codes (P0xxx, P2xxx, P34xx) are OBD / emissions related."""
    return code[0] == "P" and (code[1] in "02" or code[1:3] == "34")


def lookup(code: str) -> dict:
    """Explanation of *code*: {title, title_ar, text, text_ar, causes, causes_ar, source, specific}."""
    try:                                              # the fault knowledge base slice (radide/cardiag/kb*)
        from .. import kb as _kb                     # type: ignore[attr-defined]
        for name in ("lookup", "explain", "get", "describe"):
            fn = getattr(_kb, name, None)
            if callable(fn):
                info = fn(code)
                if info:
                    d = info if isinstance(info, dict) else getattr(info, "__dict__", {})
                    if d:
                        d = dict(d)
                        d.setdefault("source", "kb")
                        return d
    except Exception:  # noqa: BLE001 - the KB is optional for this slice
        pass
    if code in _BUILTIN:
        t, ta, x, xa, c, ca = _BUILTIN[code]
        return {"code": code, "title": t, "title_ar": ta, "text": x, "text_ar": xa, "causes": c, "causes_ar": ca,
                "source": "builtin"}
    sys_en, sys_ar = _SYS[code[0]]
    specific = code[1] in "13" and not code.startswith("P3")
    if specific:
        t, ta = (f"Manufacturer-specific code ({sys_en})", f"كود خاص بالشركة المصنّعة ({sys_ar})")
    else:
        t, ta = (f"Generic {sys_en.lower()} code", f"كود عام - {sys_ar}")
    return {"code": code, "title": t, "title_ar": ta,
            "text": "No description in RAD IDE's knowledge base. Check the manufacturer's service information.",
            "text_ar": "لا يوجد وصف في قاعدة معارف RAD IDE. راجع معلومات الخدمة من الشركة المصنّعة.",
            "causes": [], "causes_ar": [], "source": "none", "specific": specific}


def safety_warnings(topics: list[str]) -> list[BiText]:
    from .definitions import SAFETY
    return [BiText(*SAFETY[t]) for t in topics if t in SAFETY]


# ---------------------------------------------------------------------------------------------- flow
@dataclass
class ClearPlan:
    ecu: Ecu
    code: str
    ftb: int | None
    info: dict
    topics: list = field(default_factory=list)
    warnings: list = field(default_factory=list)          # BiText
    emissions: bool = False

    def explanation(self, lang: str | None = None) -> str:
        lang = lang or ui_language()
        i = self.info
        ar = lang == "ar"
        title = (i.get("title_ar") if ar else i.get("title")) or i.get("title") or ""
        text = (i.get("text_ar") if ar else i.get("text")) or i.get("text") or i.get("explanation") or ""
        causes = (i.get("causes_ar") if ar else i.get("causes")) or i.get("causes") or []
        lines = [f"{self.code}: {title}", "", text]
        if causes:
            lines += ["", "الأسباب المحتملة:" if ar else "Possible causes:"] + [f"- {c}" for c in causes]
        if self.warnings:
            lines += ["", "تحذيرات السلامة:" if ar else "Safety warnings:"] + [f"! {w.get(lang)}" for w in self.warnings]
        if self.emissions:
            lines += ["", ("ملاحظة: مسح أكواد الانبعاثات يعيد ضبط مؤشرات الجاهزية (Readiness)، فقد لا تجتاز السيارة الفحص "
                           "حتى تكتمل اختبارات المراقبة أثناء القيادة. إذا بقي السبب سيعود الكود ولمبة المحرك.") if ar else
                      ("Note: clearing an emissions code resets the readiness monitors, so the car may not pass an "
                       "inspection until the monitors have run again while driving. If the cause is still present the "
                       "code and the warning light come back.")]
        return "\n".join(lines)


class ClearFaultFlow:
    def __init__(self, client: ServiceClient, emit=None):
        self.client = client
        self._emit = emit

    def emit(self, kind, text, **data):
        if self._emit is not None:
            from .runner import Event
            try:
                self._emit(Event(kind, text if isinstance(text, BiText) else BiText(str(text)), None, data))
            except Exception:  # noqa: BLE001
                pass

    def read(self, ecu: Ecu) -> list[StoredDtc]:
        if ecu.protocol == "obd":
            resp = self.client.request(ecu, b"\x03", note="read DTC (mode 03)")
            body = resp[2:] if len(resp) % 2 == 0 else resp[1:]
            return [StoredDtc(code_text(body[i:i + 2]), 0, 0x08, body[i:i + 2])
                    for i in range(0, len(body) - 1, 2) if body[i:i + 2] != b"\0\0"]
        resp = self.client.request(ecu, b"\x19\x02\xFF", note="read DTC")
        out = []
        for i in range(3, len(resp) - 3, 4):
            raw = resp[i:i + 3]
            out.append(StoredDtc(code_text(raw), raw[2], resp[i + 3], raw))
        return out

    def plan(self, ecu: Ecu, code: str) -> ClearPlan:
        c, ftb = parse_code(code)
        topics = safety_topics(c, ecu)
        return ClearPlan(ecu, c, ftb, lookup(c), topics, safety_warnings(topics), emissions_related(c))

    def clear(self, plan: ClearPlan, *, repair_confirmed: bool, allow_clear_all: bool = False) -> Result:
        """Clear the fault of *plan*. Without ``repair_confirmed`` nothing is sent. When the control unit cannot
        clear a single fault, the result has ``data['needs_clear_all']`` unless ``allow_clear_all`` was given."""
        ecu = plan.ecu
        self.client.context = {"action": "clear_dtc", "id": plan.code, "repair_confirmed": bool(repair_confirmed),
                               "clear_all_allowed": bool(allow_clear_all)}
        try:
            if not repair_confirmed:
                raise ServiceError(bi("Confirm that the cause was repaired before clearing the fault.",
                                      "أكّد أنه تم إصلاح السبب قبل مسح العطل."), code="confirm")
            if ecu.protocol == "obd":
                if not allow_clear_all:
                    return Result(False, bi("OBD-II can only clear every emissions fault at once (mode 04).",
                                            "OBD-II يمسح كل أعطال الانبعاثات مرة واحدة فقط (الوضع 04)."),
                                  data={"needs_clear_all": True})
                self.client.request(ecu, b"\x04", note="clear all (mode 04)")
                how = "all"
            else:
                how = "single"
                group = code_bytes(plan.code, plan.ftb if plan.ftb is not None else 0)
                try:
                    self.client.request(ecu, b"\x14" + group, note="clear single DTC")
                except NegativeResponse as e:
                    if e.nrc not in (0x31, 0x12, 0x11, 0x13):
                        raise
                    warn = bi("This control unit cannot clear a single fault; clearing ALL its faults instead "
                              "removes every stored fault and its freeze-frame data.",
                              "وحدة التحكم هذه لا تستطيع مسح عطل واحد فقط؛ مسح كل أعطالها بدلًا من ذلك يحذف كل الأعطال "
                              "المخزنة وبيانات اللحظة المجمدة (Freeze Frame) الخاصة بها.")
                    self.emit("warning", warn)
                    if not allow_clear_all:
                        return Result(False, warn, data={"needs_clear_all": True})
                    self.client.request(ecu, b"\x14" + CLEAR_ALL, note="clear all DTC (fallback)")
                    how = "all"
            back = []
            try:
                back = [d for d in self.read(ecu) if d.code == plan.code]
            except ServiceError:
                pass
            if back:
                txt = bi(f"{plan.code} came back at once: the cause is still present. Check the repair.",
                         f"عاد {plan.code} فورًا: السبب ما زال موجودًا. راجع الإصلاح.")
                self.emit("warning", txt)
                return Result(False, txt, data={"how": how, "returned": True})
            txt = (bi(f"{plan.code} cleared.", f"تم مسح {plan.code}.") if how == "single" else
                   bi(f"All faults of {ecu.name or ecu.key} cleared.", f"تم مسح كل أعطال {ecu.name_ar or ecu.name or ecu.key}."))
            self.emit("status", txt)
            return Result(True, txt, 100, data={"how": how, "returned": False})
        except ServiceError as e:
            self.emit("status", e.text)
            return Result(False, e.text, error=e)
        finally:
            self.client.context = {}
