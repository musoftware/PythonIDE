# الدرس 9: مشروع: تشخيص كامل لسيارة بتقرير

**في هذا الدرس:**

- خطة تشخيص كاملة كما تفعلها الورشة: من شكوى صاحب السيارة إلى التقرير.
- **فحص كل الوحدات** ولمباتها وأعطالها ولقطة التجميد والجاهزية.
- **معالج الأعراض** («العربية بتسخن») و**الشرح بالذكاء الاصطناعي**.
- برنامج بايثون يكتب **تقرير فحص** HTML، وزر **حفظ التقرير** في المنضدة.

## القصة

صاحب السيارة يقول: «لمبة المحرك منوّرة من أسبوع، ولمبة ABS ظهرت امبارح، والعربية بتسخن في الزحمة». خطة العمل:

1. **الاتصال** وقراءة رقم الشاسيه (الدرس 2).
2. **اللمبات**: ما المنوّر وما معناه (الدرس 3).
3. **فحص كل وحدات التحكم** وقراءة الشرح والأسباب (الدرس 4).
4. **لقطة التجميد** لكل عطل مهم، ثم **البيانات الحية** لما نشك فيه (الدرس 5).
5. **معالج الأعراض** لشكوى السخونة، و**الشرح بالذكاء الاصطناعي** لمن يريد رأيًا ثانيًا.
6. **وظائف الخدمة** للتأكد: اختبار المروحة (الدرس 7).
7. **الإصلاح** ثم **مسح العطل المعيّن** والتحقق (الدرس 8)، و**الجاهزية** (الدرس 6).
8. **التقرير** لصاحب السيارة.

## في الواجهة

1. **أدوات > تشخيص السيارات...**، المحوّل: **السيارة التجريبية عبر محاكي ELM327**، ثم **اتصال**.
2. تبويب **الدليل > لمبات التحذير > اقرأ لمبات العربية**: تتحدد اللمبات المنوّرة ويظهر لكل واحدة ماذا تفعل.
3. تبويب **الأعطال > فحص كل وحدات التحكم**: أكواد المحرك ومعها `C0035-1F` من ABS و `B0001-1A` من الوسائد. اضغط كل كود لترى الشرح والأسباب.
4. **لقطة التجميد** ثم **البيانات الحية**: اختر حرارة سائل التبريد وسرعة الدوران وابدأ.
5. **الدليل > الأعراض**: اكتب «العربية بتسخن» وأجب الأسئلة (متى؟ في الخامل. المروحة؟ لا تعمل) فتصبح **المروحة** السبب الأول.
6. **الدليل > شرح بالذكاء الاصطناعي > استخدم بيانات السيارة** ثم **اسأل الذكاء الاصطناعي** (يعمل مع مزوّد الذكاء الاصطناعي في الخيارات، أو يعطيك شرحًا من قاعدة المعارف دون إنترنت).
7. **الخدمة > اختبار مروحة الردياتير**: المروحة لا تدور في الحقيقة؟ إذًا الفيوز أو الريلاي أو الموتور.
8. بعد الإصلاح: **الخدمة > مسح عطل معيّن**، ثم **الأعطال > حفظ التقرير...**.

## معالج الأعراض

```carpy run
from radide.cardiag.kb import symptoms

found = symptoms.match("العربية بتسخن")
print("العَرَض:", found[0])
result = symptoms.evaluate(found[0], {"when": "idle", "fan": "no"}, lang="ar")
print(result["name"], "- توقف فورًا؟", result["stop"])
for c in result["causes"][:3]:
    print(f"  {c['percent']:3}٪  {c['name']}")
print("راقب:", result["watch"][0][1])
print("أكواد مرتبطة:", ", ".join(code for code, _t in result["codes"][:3]))
```

```text output
العَرَض: overheating
المحرك يسخن (سخونية) - توقف فورًا؟ True
   50٪  مروحة الردياتير لا تعمل
   18٪  نقص سائل التبريد / تسريب
    9٪  الثرموستات عالق مقفول
راقب: حرارة سائل التبريد: طبيعي حوالي 85-105 °م والمحرك ساخن؛ المروحة غالبًا تشتغل قرب 95-105 °م.
أكواد مرتبطة: P0217, P0298, P2600
```

## الشرح بالذكاء الاصطناعي

الشرح يرسل للذكاء الاصطناعي **حقائق** قاعدة المعارف مع بيانات السيارة (الأكواد، لقطة التجميد، القيم الحية، اللمبات، الأعراض)، ويطلب منه أن يقول **مدى ثقته**، ويضع السلامة أولًا، ولا يخمّن معاني الأكواد الخاصة بالشركات، و**يرفض** أي طلب عن مانع التشغيل أو عداد المسافات أو تعطيل الانبعاثات. وبدون ذكاء اصطناعي يبقى **الشرح من قاعدة المعارف**:

```carpy run
from radide.cardiag.kb import ai

ctx = ai.Context(dtcs=["P0217"], lights=["coolant"], symptoms=["overheating"])
system, user = ai.build_prompt(ctx, lang="ar")
print("التعليمات تمنع مانع التشغيل وعداد المسافات؟", "immobili" in system.lower() and "odometer" in system.lower())
print("الإجابة المطلوبة بالعربية؟", "Arabic" in system)
text = ai.offline_explanation(ctx, lang="ar")
print(text.splitlines()[0])
print(next(line for line in text.splitlines() if line.startswith("P0217")))
```

```text output
التعليمات تمنع مانع التشغيل وعداد المسافات؟ True
الإجابة المطلوبة بالعربية؟ True
تنبيه سلامة: عطل واحد على الأقل يخص السلامة أو قد يتلف المحرك - اقرأ "هل القيادة آمنة؟" بالأسفل قبل استكمال القيادة.
P0217 - حالة ارتفاع حرارة سائل التبريد
```

## البرنامج الكامل: فحص وتقرير

هذا البرنامج يفعل خطوات المنضدة كلها ويكتب **تقرير HTML** بالعربية (من اليمين لليسار) يمكنك فتحه في المتصفح وطباعته لصاحب السيارة:

```carpy run
import html
from pathlib import Path
from radide.cardiag.sim.car import VirtualCar, LAMPS
from radide.cardiag.link import demo_link, discovery
from radide.cardiag.link.uds import UdsClient
from radide.cardiag.obd.client import ObdClient
from radide.cardiag.obd.transport import LinkTransport
from radide.cardiag import kb

car = VirtualCar(time_scale=0)
link = demo_link(car)
obd = ObdClient(LinkTransport(link))
vin = obd.vehicle_info().vin

# 1) اللمبات المنوّرة (لوحة العدادات في السيارة التجريبية)
bits = int.from_bytes(UdsClient(link, 0x720, 0x728).read_did(0x2220)[:2], "big")
lamps = [ar for bit, _k, _en, ar in LAMPS if bits >> bit & 1]

# 2) كل الأعطال: OBD-II للمحرك + UDS لباقي الوحدات
faults = [("المحرك", e.code) for e in obd.read_all_dtcs()]
for ecu in discovery.discover(link, identify=False):
    if not ecu.obd:
        for d in UdsClient(link, ecu.tx, ecu.rx).read_dtcs(0xFF):
            if d.confirmed or d.pending:
                faults.append((ecu.name_ar, d.text))

# 3) لقطة التجميد والجاهزية
ff = obd.freeze_frames()["7E8"]
ffv = {r.pid: r.values[0].value for r in ff.readings()}      # PID -> القيمة
ready = obd.readiness()["7E8"]
not_ready = [m.name for m in ready.monitors if m.supported and not m.complete]

# 4) التقرير
rows = []
for unit, code in faults:
    info = kb.lookup(code)
    causes = "<br>".join(html.escape(c) for c in info["causes_ar"][:3]) or "-"
    safety = " ⚠" if info["safety"] else ""
    rows.append(f"<tr><td>{code}{safety}</td><td>{html.escape(unit)}</td>"
                f"<td>{html.escape(info['title_ar'])}</td><td>{causes}</td></tr>")
page = (f"<!doctype html><html dir='rtl' lang='ar'><meta charset='utf-8'><title>تقرير فحص</title>"
        f"<h1>تقرير فحص السيارة {vin}</h1>"
        f"<p>اللمبات المنوّرة: {'، '.join(lamps)}</p>"
        f"<table border=1><tr><th>الكود</th><th>الوحدة</th><th>العطل</th><th>أشهر الأسباب</th></tr>{''.join(rows)}</table>"
        f"<p>لقطة التجميد ({ff.dtc}): {round(ffv[0x0C])} لفة، الحرارة {ffv[0x05]} °م، السرعة {ffv[0x0D]} كم/س</p>"
        f"<p>اختبارات غير مكتملة: {', '.join(not_ready) or 'لا شيء'}</p></html>")
Path("report.html").write_text(page, encoding="utf-8")
link.close()

print("رقم الشاسيه:", vin)
print("لمبات منوّرة:", len(lamps))
for unit, code in faults:
    print(f"  {code:9} {unit}")
print("التقرير:", Path("report.html").stat().st_size > 1500, "- صفوف الأعطال:", page.count("<tr>") - 1)
```

```text output
رقم الشاسيه: XRDDEM0CAR0123456
لمبات منوّرة: 5
  P0301     المحرك
  P0420     المحرك
  P0171     المحرك
  U0121-00  لوحة العدادات
  B1424-00  التكييف
  C0035-1F  الفرامل ABS / ESP
  B0001-1A  الوسائد الهوائية (SRS)
التقرير: True - صفوف الأعطال: 7
```

في المنضدة زر **الأعطال > حفظ التقرير...** يكتب تقريرًا أكمل من هذا: بيانات السيارة، وكل الأكواد بشرحها وأسبابها وخطوات فحصها وتحذيرات السلامة، ولقطات التجميد، والجاهزية، والقيم الحية التي سجلتها - بلغة الواجهة.

## الخاتمة: التشخيص في جملة

**اقرأ ← افهم ← افحص ← أصلح ← امسح العطل المعيّن ← تحقّق ← وثّق.** أداة التشخيص لا تصلح السيارة؛ هي تختصر عليك الطريق إلى السبب. وكل ما تعلمته هنا يعمل كما هو مع سيارة حقيقية ومحوّل ELM327 أو J2534، مع ملاحظة واحدة: وظائف الخدمة في السيارات الحقيقية تحتاج **ملف تعريفات** للطراز (الدرس 7).

```quiz
{"question": "أي ترتيب هو الصحيح في التشخيص؟",
 "choices": ["امسح ثم انتظر هل يرجع الكود", "اقرأ الكود والشرح ولقطة التجميد، افحص وأصلح، امسح العطل المعيّن، تحقّق ووثّق", "غيّر القطع المذكورة في الكود مباشرة", "اسأل الذكاء الاصطناعي ونفّذ دون فحص"],
 "answer": 1,
 "explanation": "الكود يدلّك على النظام وليس على القطعة دائمًا؛ الفحص بالبيانات الحية ولقطة التجميد يحدد السبب قبل تغيير أي شيء."}
```
