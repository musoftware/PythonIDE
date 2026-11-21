""""Explain with AI" for the car diagnostics tools (docs/CARDIAG.md "Fault knowledge base").

    from radide.cardiag.kb import ai as kbai
    ctx = kbai.Context(dtcs=["P0217", "P0128"], freeze=[...], live=[("Coolant temperature", 112, "°C")],
                       vehicle={"vin": "...", "make": "...", "year": 2015}, lights=["coolant"], symptoms=["overheating"])
    system, user = kbai.build_prompt(ctx, lang="ar")      # the careful prompt (knowledge-base facts included)
    job = kbai.ask(ctx, lang="ar")                         # radide.ai ChatJob (default "chat" provider)
    kbai.offline_explanation(ctx, lang="ar")               # knowledge base only - works without any AI

The prompt gives the model the knowledge-base entries as grounding, asks for an answer a non-expert can follow, makes
it say how sure it is, puts safety first (brakes / airbag / steering / overheating) and keeps it inside RAD IDE's scope
(no immobiliser, odometer or emissions-defeat advice). The answer is shown as returned; the offline explanation is
always available next to it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

MAX_CODES = 20
MAX_LIVE = 40


@dataclass
class Context:
    dtcs: list = field(default_factory=list)      # "P0217" / {"code", "ecu", "kinds"} / objects with .code
    freeze: list = field(default_factory=list)    # [{"dtc": code, "values": [(name, value, unit)]}]
    live: list = field(default_factory=list)      # [(name, value, unit)] or [{"name", "value", "unit"}]
    vehicle: dict = field(default_factory=dict)   # vin, make, model, year, engine, mileage, fuel
    lights: list = field(default_factory=list)    # warning-light ids (lights.LIGHTS)
    symptoms: list = field(default_factory=list)  # symptom ids (symptoms.SYMPTOMS) or free text
    readiness: list = field(default_factory=list)  # [(monitor name, status)]
    question: str = ""                            # the user's own question
    make: str = ""                                # for manufacturer packs


def _code_items(dtcs) -> list[dict]:
    out, seen = [], set()
    for d in dtcs or []:
        if isinstance(d, str):
            item = {"code": d.strip().upper(), "ecu": "", "kinds": []}
        elif isinstance(d, dict):
            item = {"code": str(d.get("code", "")).upper(), "ecu": str(d.get("ecu", "") or ""),
                    "kinds": list(d.get("kinds", []) or [])}
        else:
            item = {"code": str(getattr(d, "code", "")).upper(), "ecu": str(getattr(d, "ecu", "") or ""),
                    "kinds": list(getattr(d, "kinds", []) or [])}
        key = (item["code"], item["ecu"])
        if item["code"] and key not in seen:
            seen.add(key)
            out.append(item)
    return out[:MAX_CODES]


def _triples(rows) -> list[tuple]:
    out = []
    for r in rows or []:
        if isinstance(r, dict):
            out.append((str(r.get("name", "")), r.get("value", ""), str(r.get("unit", "") or "")))
        elif isinstance(r, (list, tuple)):
            r = list(r) + ["", "", ""]
            out.append((str(r[0]), r[1], str(r[2] or "")))
    return out


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


SYSTEM_EN = """You are an experienced, careful car diagnostic technician helping a car owner or a junior mechanic \
who uses the RAD IDE scan tool. Rules:
1. Base the answer on the data given (fault codes, freeze frame, live data, warning lights, symptoms) and on the \
knowledge-base notes. Say clearly when something is a guess and how sure you are (high / medium / low).
2. Safety first: if anything points to brakes, airbags, steering, overheating, low oil pressure, fuel leaks or a \
heavy misfire (flashing check-engine light), say at the top whether the car should be driven and what to do now.
3. Explain in plain words for a non-expert. Order the likely causes from most to least likely, with the reason taken \
from the data (e.g. which live value supports it). Give simple checks first (look, listen, measure with a \
multimeter), expensive parts last. Do not recommend replacing parts without a check that confirms the fault.
4. Manufacturer-specific codes (P1xxx, B1/B2, C1/C2, U1/U2, P30-P33) mean different things on different makes: if \
no definition is given, say so instead of guessing a meaning.
5. Clearing codes does not repair anything: recommend clearing only after the repair, and mention that clearing \
resets the readiness monitors and erases freeze frames.
6. Stay inside legal, normal workshop work. Do not give instructions for immobiliser / key bypass, odometer \
changes, removing or disabling emissions equipment (DPF, EGR, catalyst, AdBlue / SCR, O2 sensors) or hiding \
emissions faults; if asked, decline briefly and suggest the proper repair.
7. Structure: Summary (2-3 sentences) - Is it safe to drive? - Most likely causes - What to check first (numbered \
steps) - Live data to watch - When to see a workshop."""

SYSTEM_AR_TAIL = """
Answer in clear Arabic that an Egyptian car owner understands easily (Modern Standard Arabic with common workshop \
words is fine, e.g. ردياتير، ثرموستات، بوجيهات، حساس). Keep fault codes, units and part names that are usually \
written in English (MAF, ABS, DPF) as they are."""


def build_prompt(ctx: Context, lang: str = "ar") -> tuple[str, str]:
    """(system, user) messages for the AI provider."""
    from .. import kb
    from . import lights as L
    from . import symptoms as S
    system = SYSTEM_EN + (SYSTEM_AR_TAIL if lang == "ar" else "\nAnswer in English.")
    parts = []
    v = {k: x for k, x in (ctx.vehicle or {}).items() if x not in (None, "")}
    if v:
        parts.append("Vehicle: " + ", ".join(f"{k}={_fmt(x)}" for k, x in v.items()))
    items = _code_items(ctx.dtcs)
    if items:
        parts.append("Fault codes read from the car (with RAD IDE knowledge-base notes):")
        for it in items:
            info = kb.lookup(it["code"], ctx.make or v.get("make", "")) or {}
            head = f"- {it['code']}"
            if it["ecu"]:
                head += f" (control unit {it['ecu']})"
            if it["kinds"]:
                head += f" [{', '.join(it['kinds'])}]"
            head += f": {info.get('title', 'unknown')}"
            parts.append(head)
            if info.get("specific") and not str(info.get("source", "")).startswith("pack:"):
                parts.append("  note: manufacturer-specific code, no definition available - meaning varies by make")
                continue
            if info.get("ftb") is not None and info.get("ftb_text", ["", ""])[0]:
                parts.append(f"  failure type: {info['ftb_text'][0]}")
            if info.get("explain"):
                parts.append(f"  meaning: {info['explain']}")
            if info.get("causes"):
                parts.append("  common causes (most likely first): " + "; ".join(info["causes"][:5]))
            if info.get("severity"):
                parts.append(f"  severity: {info['severity']}; drive: {info.get('drive') or '?'}"
                             + ("; SAFETY-RELEVANT" if info.get("safety") else ""))
    elif not ctx.lights and not ctx.symptoms:
        parts.append("No fault codes are stored.")
    for ff in ctx.freeze or []:
        vals = _triples(ff.get("values", []) if isinstance(ff, dict) else [])
        if vals:
            dtc = ff.get("dtc", "") if isinstance(ff, dict) else ""
            parts.append(f"Freeze frame (engine data when {dtc or 'the fault'} was stored):")
            parts.extend(f"- {n}: {_fmt(x)} {u}".rstrip() for n, x, u in vals[:MAX_LIVE])
    live = _triples(ctx.live)
    if live:
        parts.append("Live data now:")
        parts.extend(f"- {n}: {_fmt(x)} {u}".rstrip() for n, x, u in live[:MAX_LIVE])
    if ctx.readiness:
        parts.append("Readiness monitors: " + "; ".join(f"{n}={s}" for n, s in ctx.readiness))
    for lid in ctx.lights or []:
        light = L.get(lid)
        if light is not None:
            parts.append(f"Warning light on: {light.name[0]} - {light.meaning[0]}")
    for s in ctx.symptoms or []:
        if s in S.SYMPTOMS:
            parts.append(f"Symptom reported by the driver: {S.SYMPTOMS[s]['name'][0]}")
        elif str(s).strip():
            parts.append(f"Symptom reported by the driver: {s}")
    if ctx.question.strip():
        parts.append(f"The user's question: {ctx.question.strip()}")
    else:
        parts.append("Explain what is most likely wrong, whether the car can be driven, and what to check first.")
    return system, "\n".join(parts)


def offline_explanation(ctx: Context, lang: str = "ar") -> str:
    """Plain-text explanation from the knowledge base only (no AI)."""
    from .. import kb
    from . import lights as L
    from . import symptoms as S
    ar = lang == "ar"
    t = (lambda en, a: a if ar else en)
    out = []
    items = _code_items(ctx.dtcs)
    infos = [(it, kb.lookup(it["code"], ctx.make or (ctx.vehicle or {}).get("make", "")) or {}) for it in items]
    if any(i.get("safety") or i.get("drive") == "no" for _it, i in infos):
        out.append(t("SAFETY: at least one fault concerns safety or can damage the engine - read 'Safe to drive?' "
                     "below before driving on.",
                     "تنبيه سلامة: عطل واحد على الأقل يخص السلامة أو قد يتلف المحرك - اقرأ \"هل القيادة آمنة؟\" بالأسفل "
                     "قبل استكمال القيادة."))
        out.append("")
    for it, info in infos:
        out.append(f"{it['code']} - {kb.text(info, 'title', lang)}")
        if info.get("explain"):
            out.append(kb.text(info, "explain", lang))
        if info.get("drive_text"):
            out.append(t("Safe to drive? ", "هل القيادة آمنة؟ ") + kb.text(info, "drive_text", lang))
        cs = kb.text(info, "causes", lang)
        if cs:
            out.append(t("Likely causes:", "الأسباب المحتملة:"))
            out.extend(f"  {n}. {c}" for n, c in enumerate(cs[:5], 1))
        ch = kb.text(info, "checks", lang)
        if ch:
            out.append(t("Check first:", "افحص أولاً:"))
            out.extend(f"  {n}. {c}" for n, c in enumerate(ch[:5], 1))
        out.append("")
    for lid in ctx.lights or []:
        light = L.get(lid)
        if light is not None:
            out.append(f"{L.text(light.name, lang)}: {L.text(light.meaning, lang)}")
            out.append("  " + L.text(light.do_now[light.colours[0]], lang))
            out.append("")
    for s in ctx.symptoms or []:
        if s in S.SYMPTOMS:
            r = S.evaluate(s, {}, lang)
            out.append(r["name"] + ":")
            out.extend(f"  - {c['name']}: {c['check']}" for c in r["causes"][:4])
            out.append("")
    if not out:
        out.append(t("No fault codes, lights or symptoms were given.", "لا توجد أكواد أو لمبات أو أعراض."))
    out.append(t("Clear the codes only after the repair - clearing resets the readiness monitors and erases the "
                 "freeze frames.",
                 "امسح الأكواد فقط بعد الإصلاح - المسح يعيد اختبارات الجاهزية ويمسح لقطات التجميد."))
    return "\n".join(out).strip()


def ask(ctx: Context, lang: str = "ar", provider=None, model: str | None = None):
    """Start the AI request -> radide.ai ChatJob (delta / finished / failed signals).

    *provider*: a radide.ai Provider (default: the user's "chat" provider, Tools > Options > AI)."""
    from ... import ai
    system, user = build_prompt(ctx, lang)
    if provider is None:
        provider, dm = ai.default("chat")
        model = model or dm
    return provider.chat([ai.Message("user", user)], model=model, system=system, temperature=0.2,
                         purpose="chat")
