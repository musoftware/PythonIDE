# الدرس 8: مسح الأعطال بالطريقة الصحيحة

**في هذا الدرس:**

- القاعدة الذهبية: **المسح لا يصلح شيئًا**.
- **مسح الكل** (الوضع 04 لأكواد المحرك) و**مسح عطل معيّن** (خدمة UDS ‏`14`).
- الترتيب الصحيح: اقرأ الشرح، أصلح، **أكّد الإصلاح**، امسح، تحقّق.
- أعطال **السلامة**: الفرامل والوسائد والتوجيه والسخونة.
- عندما لا تدعم الوحدة مسح عطل واحد.

## المسح لا يصلح شيئًا

مسح الكود يطفئ اللمبة **مؤقتًا**. لو السبب موجود سيرجع الكود ومعه اللمبة بعد دقائق أو بعد مشوار، وفي الطريق تكون قد **فقدت** لقطة التجميد التي كانت ستساعدك، وأعدت اختبارات الجاهزية إلى الصفر (الدرس 6). لذلك:

1. **اقرأ** الكود وشرحه وأسبابه، واحفظ **التقرير** (معه لقطة التجميد).
2. **أصلح** السبب (أو افحص حتى تتأكد أن العطل كان عابرًا، مثل غطاء تانك مفتوح).
3. **امسح** العطل، ويفضّل العطل المعيّن فقط.
4. **تحقّق**: اقرأ الأكواد مرة أخرى، وجرّب السيارة، وراقب البيانات الحية.

## في RAD IDE

- **تبويب الأعطال > مسح الأكواد...**: يمسح أكواد **المحرك** (الوضع 04). نافذة التأكيد تعرض كل ما سيُمسح، وتحذّر من إعادة ضبط الجاهزية ومسح لقطات التجميد، وتذكر أن الأكواد الدائمة تبقى، وتعرض تحذيرات السلامة أولًا، ولا يعمل زر المسح قبل أن تؤكد أنك قرأت.
- **تبويب الخدمة > مسح عطل معيّن**: اختر الوحدة (المحرك، الفرامل، الوسائد...)، اقرأ أعطالها، اختر عطلًا فيظهر **شرحه وأسبابه أولًا**، ثم علّم **«تم إصلاح السبب»** واضغط **مسح العطل**. يُمسح هذا العطل وحده إن كانت الوحدة تدعم ذلك، وإلا يسألك قبل مسح كل أعطال الوحدة. بعد المسح تُحدَّث قائمة الأعطال في تبويب الأعطال تلقائيًا.

نفس الخطوات بالكود: عطل `P0171` (خليط فقير) بعد إصلاح تسريب الهواء:

```carpy run
from radide.cardiag.sim.car import VirtualCar
from radide.cardiag.link import demo_link
from radide.cardiag.service import definitions as D
from radide.cardiag.service.transport import ServiceClient
from radide.cardiag.service.dtc import ClearFaultFlow

car = VirtualCar(time_scale=4.0, engine_running=False)
client = ServiceClient(demo_link(car))
pack = D.workbench_pack()
engine = D.ecu_of(pack, "engine")
flow = ClearFaultFlow(client)
print("أعطال المحرك:", [d.label for d in flow.read(engine)])

plan = flow.plan(engine, "P0171")
print(plan.explanation("ar").splitlines()[0])          # الشرح يظهر دائمًا قبل المسح
r = flow.clear(plan, repair_confirmed=False)
print("بدون تأكيد الإصلاح:", r.status.get("ar"))
r = flow.clear(plan, repair_confirmed=True)
print("بعد تأكيد الإصلاح:", r.status.get("ar"), "- الطريقة:", r.data.get("how"))
print("أعطال المحرك الآن:", [d.label for d in flow.read(engine)])
```

```text output
أعطال المحرك: ['P0301', 'P0171', 'P0420']
P0171: النظام فقير جدًا (خليط فقير) (البنك 1)
بدون تأكيد الإصلاح: أكّد أنه تم إصلاح السبب قبل مسح العطل.
بعد تأكيد الإصلاح: تم مسح P0171. - الطريقة: single
أعطال المحرك الآن: ['P0301', 'P0420']
```

مُسح `P0171` **وحده** (خدمة `14` ومعها الكود)، وبقي `P0301` و `P0420` لأنهما لم يُصلحا بعد. هذا أفضل من مسح الكل: لا تضيع معلومات الأعطال الأخرى.

## أعطال السلامة

بعض الأعطال تمس **سلامتك مباشرة**: الفرامل و ABS، والوسائد الهوائية، والتوجيه، وسخونة المحرك. قبل مسحها يعرض RAD IDE تحذيرًا خاصًا ويطلب تأكيدًا إضافيًا، لأن مسحها دون إصلاح قد يعني فرامل لا تعمل كما تتوقع أو وسادة لا تنفخ:

```carpy run
from radide.cardiag.sim.car import VirtualCar
from radide.cardiag.link import demo_link
from radide.cardiag.service import definitions as D
from radide.cardiag.service.transport import ServiceClient
from radide.cardiag.service.dtc import ClearFaultFlow

client = ServiceClient(demo_link(VirtualCar(time_scale=4.0, engine_running=False)))
pack = D.workbench_pack()
flow = ClearFaultFlow(client)
for key in ("abs", "airbag"):
    ecu = D.ecu_of(pack, key)
    for d in flow.read(ecu):
        plan = flow.plan(ecu, d.label)
        print(f"{d.label}: موضوع السلامة = {', '.join(plan.topics)}")
        for w in plan.warnings:
            print("  ⚠", w.get("ar"))

bag = D.ecu_of(pack, "airbag")
plan = flow.plan(bag, flow.read(bag)[0].label)
r = flow.clear(plan, repair_confirmed=True)
print("وحدة الوسائد:", r.status.get("ar"))
print("تحتاج تأكيد مسح الكل؟", bool(r.data.get("needs_clear_all")))
```

```text output
C0035-1F: موضوع السلامة = brakes
  ⚠ الفرامل: اختبر الفرامل بحذر قبل القيادة.
B0001-1A: موضوع السلامة = airbag
  ⚠ الوسائد الهوائية: الإصلاح الخاطئ قد يمنع الوسادة من العمل أو يطلقها. أطفئ الإشعال قبل لمس الموصلات.
وحدة الوسائد: وحدة التحكم هذه لا تستطيع مسح عطل واحد فقط؛ مسح كل أعطالها بدلًا من ذلك يحذف كل الأعطال المخزنة وبيانات اللحظة المجمدة (Freeze Frame) الخاصة بها.
تحتاج تأكيد مسح الكل؟ True
```

وحدة الوسائد في السيارة التجريبية **لا تدعم** مسح عطل واحد (مثل وحدات كثيرة حقيقية)، فلا يمسح RAD IDE كل أعطالها من تلقاء نفسه: يسألك أولًا ويشرح أن **كل** أعطال الوحدة ولقطاتها ستُمسح.

> **تنبيه مهم عن الوسائد الهوائية:** لا تفصل موصّلات الوسائد والإشعال يعمل، وافصل البطارية وانتظر حسب تعليمات الشركة قبل أي عمل عليها. عطل الوسادة يعود فورًا إذا بقيت الدائرة معطّلة - وهذا مقصود.

## ما الذي لا تفعله أبدًا

- لا تمسح عطلًا **لتطفئ اللمبة** قبل بيع السيارة أو قبل الفحص الفني: هذا غش، ولا ينجح غالبًا (الجاهزية والأكواد الدائمة).
- لا تبحث عن طريقة «لإخفاء» كود انبعاثات بشكل دائم أو تعطيل اختباره: RAD IDE لا يقدم ذلك ويرفض أي تعريفات تحاوله.

### تمرين

اكتب دالة `can_clear(code, repaired, safety_ok)` بالمكتبة القياسية ترجع نصًا: «اقرأ الشرح وأصلح أولًا» إن لم يُصلح، و«أكّد تحذير السلامة» إن كان الكود يبدأ بـ `C0` أو `B00` ولم يؤكد المستخدم، وإلا «يمكن المسح». جرّبها على ثلاث حالات.

```python exercise
def can_clear(code: str, repaired: bool, safety_ok: bool) -> str:
    return ""


print(can_clear("P0171", False, False))
print(can_clear("C0035", True, False))
print(can_clear("C0035", True, True))
```

```python solution
def can_clear(code: str, repaired: bool, safety_ok: bool) -> str:
    if not repaired:
        return "اقرأ الشرح وأصلح أولًا"
    if code.startswith(("C0", "B00")) and not safety_ok:
        return "أكّد تحذير السلامة"
    return "يمكن المسح"


print(can_clear("P0171", False, False))
print(can_clear("C0035", True, False))
print(can_clear("C0035", True, True))
```

```text output
اقرأ الشرح وأصلح أولًا
أكّد تحذير السلامة
يمكن المسح
```

```quiz
{"question": "عندك ثلاثة أعطال في المحرك وأصلحت سبب واحد منها فقط. ما الأفضل؟",
 "choices": ["مسح الكل بالوضع 04", "مسح العطل الذي أصلحته فقط (UDS 14 مع الكود) إن كانت الوحدة تدعمه", "عدم المسح أبدًا", "فصل البطارية"],
 "answer": 1,
 "explanation": "مسح العطل المعيّن يحتفظ بمعلومات الأعطال الأخرى ولقطاتها حتى تصلحها."}
```
