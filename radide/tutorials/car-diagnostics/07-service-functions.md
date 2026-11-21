# الدرس 7: وظائف الخدمة: دورة التبريد واختبار المروحة

**في هذا الدرس:**

- ما هي **وظائف الخدمة**: الروتينات واختبار المشغّلات والتصفير والتكييفات (Adaptations).
- **دورة تنفيس التبريد** خطوة خطوة: الشروط المسبقة، والتقدم، والتعليمات، والنتيجة.
- لماذا **ترفض** السيارة الوظيفة أحيانًا، وكيف يشرح RAD IDE السبب بالعربية.
- **اختبار مروحة الردياتير** وإعادة التحكم إلى الكمبيوتر.
- **ملفات التعريفات** للسيارات الحقيقية، و**الوصول الأمني** بإضافتك أنت فقط.

## أنواع وظائف الخدمة

| النوع | خدمة UDS | أمثلة |
|---|---|---|
| **روتين** | `31` (بدء، نتيجة، إيقاف) | تنفيس التبريد، تصفير الصيانة، تصفير تعلّم البوابة، تسجيل البطارية، وضع خدمة الفرامل، معايرة زاوية الدركسيون، الحرق الخدمي لفلتر الجزيئات |
| **اختبار مشغّل** | `2F` | مروحة الردياتير، طلمبة المياه الكهربائية، الرشاشات، موتور ABS، البلاور |
| **تكييف / ترميز** | `2E` | قيمة افتراضية، تفعيل ميزة - **فقط** من تعريفات يقدمها المستخدم |

في RAD IDE تجدها في **أدوات > وظائف خدمة السيارة...** أو تبويب **الخدمة** في منضدة التشخيص. الوظائف مرتبة في مجموعات، ولكل وظيفة صفحة: الوصف، تحذيرات السلامة، **قائمة الشروط المسبقة** (بعضها يُفحص تلقائيًا من السيارة، وبعضها تؤكده أنت بعلامة)، وشريط التقدم، وزر الإيقاف، والسجل.

## دورة تنفيس التبريد

بعد تغيير سائل التبريد أو طلمبة المياه أو الردياتير يبقى **هواء** في الدورة، والهواء يسبب سخونة وتدفئة باردة. في كثير من السيارات الحديثة (طلمبة مياه كهربائية وصمامات إلكترونية) لا يخرج الهواء إلا بروتين من الكمبيوتر يشغّل الطلمبة والصمامات بترتيب معيّن.

**الشروط المسبقة** في السيارة التجريبية: الإشعال يعمل والمحرك **متوقف**، والبطارية 12 فولت على الأقل، والمحرك **بارد** (لا تفتح غطاء دورة تبريد ساخنة أبدًا)، والقربة مملوءة حتى MAX وغطاؤها مفتوح، والتدفئة على أعلى درجة.

```carpy run
from radide.cardiag.sim.car import VirtualCar
from radide.cardiag.link import demo_link
from radide.cardiag.service import definitions as D
from radide.cardiag.service.transport import ServiceClient
from radide.cardiag.service.runner import RoutineRunner

car = VirtualCar(time_scale=4.0, engine_running=False)    # الزمن في المحاكي أسرع 4 مرات
client = ServiceClient(demo_link(car))
pack = D.workbench_pack()                                  # تعريفات السيارة التجريبية
bleed = dict(D.find(pack, "routines", "cooling_bleed"))
bleed["poll"] = dict(bleed["poll"], interval_s=0.2)
print("الوظيفة:", bleed["name_ar"])

events = []
result = RoutineRunner(client, pack, emit=events.append).run(bleed, confirmed=[2, 3, 4])   # 2-4: أكّدها المستخدم
for e in events:
    if e.kind == "precondition":
        print("  شرط:", e.text.get("ar"))
    elif e.kind == "instruction":
        print("  ➜", e.text.get("ar"))
print("وصل التقدم إلى 100٪؟", max(e.progress for e in events if e.kind == "progress") == 100)
print("النتيجة:", result.status.get("ar"))
for name, value in result.values:
    print(f"  {name.get('ar')}: {value}")
```

```text output
الوظيفة: تنفيس نظام التبريد / دورة مضخة التبريد
  شرط: الإشعال يعمل والمحرك متوقف  [0 rpm]  (متحقق)
  شرط: جهد البطارية 12.0 فولت على الأقل (وصّل شاحنًا داعمًا)  [12.5 V]  (متحقق)
  شرط: المحرك بارد - لا تفتح غطاء نظام تبريد ساخن أبدًا  (تم التأكيد)
  شرط: خزان التمدد ممتلئ حتى علامة MAX والغطاء مفتوح  (تم التأكيد)
  شرط: التدفئة على أعلى درجة حرارة  (تم التأكيد)
  ➜ راقب مستوى السائل في خزان التمدد وأضف عندما ينخفض.
  ➜ منتصف المدة: أضف السائل حتى MAX مرة أخرى.
  ➜ أغلق الغطاء. افحص المستوى مرة أخرى بعد أول قيادة.
وصل التقدم إلى 100٪؟ True
النتيجة: اكتمل.
  نسبة تشغيل مضخة التبريد: 0 %
  حرارة سائل التبريد: 27 °C
```

لاحظ أن RAD IDE **فحص بنفسه** الشرطين الأولين من السيارة (0 لفة و 12.5 فولت)، والثلاثة الباقية **أكّدها المستخدم** لأن السيارة لا تعرفها (هل غطاء القربة مفتوح؟). وفي الواجهة لا يبدأ الروتين قبل تأكيد كل الشروط.

## عندما ترفض السيارة

الكمبيوتر نفسه يحمي السيارة: لو المحرك دائر يرفض دورة التبريد بـ **كود رفض** (NRC). RAD IDE يفحص الشروط قبل الإرسال، ويشرح أي رفض بالعربية:

```carpy run
from radide.cardiag.sim.car import VirtualCar
from radide.cardiag.link import demo_link
from radide.cardiag.service import definitions as D
from radide.cardiag.service.transport import ServiceClient
from radide.cardiag.service.runner import RoutineRunner

car = VirtualCar(time_scale=4.0, engine_running=True)      # المحرك دائر
client = ServiceClient(demo_link(car))
pack = D.workbench_pack()
bleed = D.find(pack, "routines", "cooling_bleed")

r = RoutineRunner(client, pack).run(bleed, confirmed=[2, 3, 4])
print("فحص RAD IDE:", r.error.code)
r = RoutineRunner(client, pack).run(bleed, confirmed=[2, 3, 4], enforce_checks=False)   # لو أرسلنا رغم ذلك
print("رد السيارة:", r.status.get("ar"))
```

```text output
فحص RAD IDE: preconditions
رد السيارة: NRC 0x22 conditionsNotCorrect: شروط السيارة اللازمة لهذه الوظيفة غير متحققة. راجع الشروط المسبقة مرة أخرى (حالة المحرك، درجة الحرارة، السرعة، ناقل الحركة، جهد البطارية).
```

أشهر أكواد الرفض: `22` الشروط غير متحققة، `33` يحتاج وصولًا أمنيًا، `7F` الخدمة غير متاحة في الجلسة الحالية، `81`/`82`/`84` سرعة الدوران عالية/منخفضة، أو المحرك لا يدور، `86` الحرارة عالية، `88` السيارة تتحرك.

## اختبار مروحة الردياتير

**اختبار المشغّل** يجعل الكمبيوتر يشغّل جزءًا بأمرك لتعرف هل هو سليم: هل المروحة تدور؟ هل الطلمبة تعمل؟ أهم قاعدة: في النهاية **يُعاد التحكم إلى الكمبيوتر** دائمًا (حتى عند الإيقاف أو الخطأ)، وإلا قد تبقى المروحة متوقفة والمحرك يسخن. ابتعد عن المروحة والسيور أثناء الاختبار.

```carpy run
from radide.cardiag.sim.car import VirtualCar
from radide.cardiag.link import demo_link
from radide.cardiag.service import definitions as D
from radide.cardiag.service.transport import ServiceClient
from radide.cardiag.service.iocontrol import ActuatorTest

car = VirtualCar(time_scale=4.0, engine_running=False)
client = ServiceClient(demo_link(car))
pack = D.workbench_pack()
fan = D.find(pack, "io_controls", "fan_test")
print("الاختبار:", fan["name_ar"])
print("الحالات:", ", ".join(s["label_ar"] for s in fan["states"]))

seen = []


def watch(event):
    car.update()
    seen.append(car.fan_duty)


result = ActuatorTest(client, pack, emit=watch).run(fan, "64", confirmed=[0], duration_s=1)   # 64 = 100٪
car.update()
print("أعلى تشغيل للمروحة أثناء الاختبار:", max(seen), "%")
print("النتيجة:", result.status.get("ar"))
print("المروحة بعد الاختبار:", car.fan_duty, "% - التحكم مع الكمبيوتر؟", not car.engine.ios[0x4001].controlled)
```

```text output
الاختبار: اختبار مروحة الردياتير
الحالات: إيقاف, 50 ٪, 100 ٪
أعلى تشغيل للمروحة أثناء الاختبار: 100 %
النتيجة: انتهى الاختبار وأُعيد التحكم إلى وحدة التحكم.
المروحة بعد الاختبار: 0.0 % - التحكم مع الكمبيوتر؟ True
```

## وظائف أخرى في السيارة التجريبية

```carpy run
from radide.cardiag.service import definitions as D

pack = D.workbench_pack()
print("روتينات:")
for e in pack["routines"]:
    print("  -", e["name_ar"])
print("اختبارات المشغّلات:")
for e in pack["io_controls"]:
    print("  -", e["name_ar"])
```

```text output
روتينات:
  - تنفيس نظام التبريد / دورة مضخة التبريد
  - إعادة ضبط مواءمة جسم الخانق (البوابة)
  - إعادة ضبط مواءمة تصحيح الوقود
  - اختبار البخاخ (أسطوانة واحدة)
  - تسجيل البطارية الجديدة
  - وضع صيانة تيل الفرامل - فتح (سحب فرامل اليد الكهربائية)
  - وضع صيانة تيل الفرامل - إغلاق (تفعيل فرامل اليد الكهربائية)
  - معايرة حساس زاوية المقود
  - تصفير مؤشر صيانة الزيت
اختبارات المشغّلات:
  - اختبار مروحة الردياتير
  - اختبار مضخة التبريد الكهربائية
  - فصل البخاخ 1 (اتزان الأسطوانات)
  - اختبار موتور مضخة ABS
  - اختبار موتور مروحة التكييف الداخلية
  - اختبار كلتش كمبروسر التكييف
```

## السيارات الحقيقية: ملفات التعريفات

عناوين الوحدات وأرقام الروتينات **تختلف من شركة لأخرى** وأحيانًا من طراز لآخر، ولذلك لا يأتي RAD IDE بتعريفات لسيارات حقيقية. تستورد أنت **ملف تعريفات** (JSON أو CSV أو جزء من ODX) من **استيراد حزمة**، وزر **قالب** يكتب ملفًا موثقًا تبدأ منه. كل ملف يُفحص قبل قبوله، وتُرفض أي وظيفة لمانع التشغيل أو المفاتيح أو عداد المسافات أو تعطيل الانبعاثات أو إخفاء الأعطال:

```carpy run
from radide.cardiag.service import definitions as D

for name in ("Coolant bleed routine", "DPF service regeneration", "Odometer correction", "EGR delete",
             "Immobilizer key learning", "تعديل العداد"):
    problems = D.policy_problems({"routines": [{"id": "x", "name": name, "ecu": "engine"}]})
    print(f"{name:28} -> {'مرفوض: ' + problems[0].get('ar') if problems else 'مقبول'}")
```

```text output
Coolant bleed routine        -> مقبول
DPF service regeneration     -> مقبول
Odometer correction          -> مرفوض: routines 'x': غير مسموح: تعديل عداد المسافات غير مدعوم.
EGR delete                   -> مرفوض: routines 'x': غير مسموح: إلغاء أنظمة الانبعاثات أو تجاوزها غير مدعوم.
Immobilizer key learning     -> مرفوض: routines 'x': غير مسموح: وظائف مانع التشغيل (الإيموبيلايزر) غير مدعومة.
تعديل العداد                 -> مرفوض: routines 'x': غير مسموح: تعديل عداد المسافات غير مدعوم.
```

**الوصول الأمني** (الخدمة `27`): بعض الوظائف تحتاج «مفتاحًا» يحسبه برنامج من «بذرة» ترسلها الوحدة. RAD IDE **لا يحتوي أي خوارزمية** لذلك ولا يحاول كسرها؛ إن كان عندك برنامج مرخّص من الشركة (ملف DLL أو وحدة بايثون) تختاره من **إضافة الوصول الأمني** وتؤكد أنك مرخّص باستعماله. وكل إجراء يُسجَّل في **سجل التدقيق** للسيارة (الوقت، الوحدة، الطلب والرد، تأكيدك).

```quiz
{"question": "انتهى اختبار مروحة الردياتير بخطأ في منتصفه. ما الذي يجب أن يحدث؟",
 "choices": ["تبقى المروحة على آخر حالة", "يُعاد التحكم في المروحة إلى كمبيوتر المحرك دائمًا", "تُمسح أعطال المحرك", "يُعاد تشغيل السيارة"],
 "answer": 1,
 "explanation": "اختبار المشغّل ينتهي دائمًا بإعادة التحكم (returnControlToECU) حتى عند الإيقاف أو الخطأ، حتى لا تبقى المروحة متوقفة."}
```
