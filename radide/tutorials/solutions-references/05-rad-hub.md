# الدرس 5: كيف يعمل RAD Hub من الداخل

**في هذا الدرس ستفهم:**

- ما **RAD Hub**، ومتى تشغّله البيئة.
- الرسائل التي تمر بين برنامجك والمكتبة: **JSON سطرًا سطرًا**.
- ما **العامل** (worker)، وكيف يعرف الـ Hub أي لغة يشغّل.
- كيف تشغّل برنامجًا يستخدم مراجع **من الطرفية** دون البيئة.

هذا الدرس «تحت الغطاء». لا تحتاجه لتستخدم المراجع، لكنه يساعدك كثيرًا عندما يحدث خطأ وتريد أن تفهم سببه.

## الفكرة: مقسّم هاتف

تخيّل شركة قديمة فيها **مقسّم هاتف** (سنترال): كل موظف يرفع السماعة ويطلب «قسم الحسابات، التحويلة Discount»، فيصله المقسّم بالقسم، ويعيد إليه الرد. الموظف لا يعرف أين مكتب الحسابات ولا لغته.

**RAD Hub** هو هذا المقسّم:

- عند كل **تشغيل** أو **تصحيح** (`F5`)، تشغّل البيئة Hub صغيرًا يستمع على عنوان محلي مثل `127.0.0.1:<منفذ>`.
- تعطي برنامجك متغيري البيئة `RAD_HUB` (عنوان الـ Hub) و`RAD_PROJECT` (مجلد المشروع).
- كل استدعاء في ملف الوكيل (`_radcall('PriceLib.Discount', 200, 15)`) يُرسل إلى الـ Hub.
- الـ Hub يجد الملف `PriceLib.cs`، ويعرف من الامتداد `.cs` أن لغته C#، ويشغّل له **عاملًا** (worker) بتلك اللغة إن لم يكن يعمل، ويرسل إليه الطلب، ثم يعيد الرد.

## شكل الرسائل

كل رسالة **كائن JSON واحد في سطر واحد**. من برنامجك إلى الـ Hub:

```text
{"id": 1, "call": "PriceLib.Discount", "args": [200, 15]}
```

ورد الـ Hub:

```text
{"id": 1, "result": 170}
```

أو عند الخطأ:

```text
{"id": 1, "error": "PriceLib.Discount: ..."}
```

ومن الـ Hub إلى العامل، الرسالة أبسط (اسم الدالة فقط، لأن العامل يعرف وحدته):

```text
{"id": 7, "func": "Discount", "args": [200, 15]}
```

الرقم `id` يربط كل رد بطلبه، حتى لو وصلت ردود كثيرة.

## محاكاة كاملة في برنامج واحد

هذا مثال يحاكي الرحلة كلها **في الذاكرة**: «وكيل» يكتب طلبًا، و«Hub» يوجّهه، و«عامل» ينفّذ الدالة. لا شبكة ولا عمليات حقيقية، لكن الرسائل بنفس الشكل:

```python run
import json

# ---- العامل: يعرف دوال وحدة واحدة (مثل PriceLib.cs)
def Discount(price, pct):
    return price - price * pct / 100

def worker(line):
    msg = json.loads(line)
    funcs = {"Discount": Discount}
    try:
        result = funcs[msg["func"]](*msg["args"])
        return json.dumps({"id": msg["id"], "result": result})
    except Exception as e:
        return json.dumps({"id": msg["id"], "error": f"{type(e).__name__}: {e}"})

# ---- الـ Hub: يقسم "PriceLib.Discount" إلى وحدة ودالة ويرسل إلى العامل
def hub(line):
    msg = json.loads(line)
    module, func = msg["call"].split(".", 1)
    print("Hub: الوحدة", module, "| الدالة", func)
    answer = json.loads(worker(json.dumps({"id": 7, "func": func, "args": msg["args"]})))
    answer["id"] = msg["id"]
    return json.dumps(answer)

# ---- الوكيل في برنامجك
def radcall(target, *args):
    reply = json.loads(hub(json.dumps({"id": 1, "call": target, "args": list(args)})))
    if "error" in reply:
        raise RuntimeError(reply["error"])
    return reply["result"]

print(radcall("PriceLib.Discount", 200, 15))
try:
    radcall("PriceLib.Discount", 200)
except RuntimeError as e:
    print("خطأ:", e)
```

```text output
Hub: الوحدة PriceLib | الدالة Discount
170.0
Hub: الوحدة PriceLib | الدالة Discount
خطأ: TypeError: Discount() missing 1 required positional argument: 'pct'
```

لاحظ في الاستدعاء الثاني: نسينا معاملًا، فحدث الخطأ **داخل العامل**، فأرسله ردًا بـ `"error"`، والوكيل حوّله إلى **استثناء** في برنامجك. هذا بالضبط ما يحدث في الحقيقة (الدرس التالي).

## أين يبحث الـ Hub عن الوحدة؟

اسم الوحدة (`PriceLib`) هو اسم ملف (دون امتداد). الـ Hub يبحث عنه:

1. في مجلد المشروع نفسه (وحدة أو كود نموذج).
2. ثم في مجلدات المشاريع **المرجعية**، بالترتيب، ومراجعها أيضًا.

ويتجاهل ملفات الوكيل (`AUTO-GENERATED ... reference to`)، حتى لا يستدعي الوكيل نفسه.

> **معلومة:** حتى داخل **مشروع واحد** يمكنك أن تضع وحدات بلغات مختلفة (مثلًا نموذج Python ووحدة VB6 `MathVB.bas` ووحدة Ring)، والـ Hub يوصل بينها بنفس الطريقة. انظر المثال `samples\HelloPolyglot`.

## التشغيل من الطرفية

البيئة تشغّل الـ Hub تلقائيًا مع `F5`. وإذا أردت تشغيل البرنامج من الطرفية (للاختبار الآلي مثلًا)، شغّل الـ Hub بنفسك ومرّر له البرنامج:

```text
python -m radide.runtimes.radhub "C:\Shop\App" -- python -u main.py
```

ما بعد `--` هو البرنامج الذي يعمل والـ Hub جاهز له. وهكذا جرّبنا مثال الدرس السابق آليًا.

## أخطاء شائعة

- **تشغيل البرنامج مباشرة بـ `python main.py`:** الوكيل لا يجد الـ Hub (لا يوجد `RAD_HUB`)، فيفشل الاستدعاء. استخدم `F5` أو الأمر السابق.
- **ملفان بنفس الاسم في مشروعين:** الـ Hub يأخذ أول ما يجده بالترتيب. اجعل أسماء الوحدات فريدة.
- **دالة تطبع في المخرجات القياسية داخل المكتبة:** مخرجات العامل التي ليست رسائل JSON تظهر في **Output** كنص عادي، وهذا مفيد للتتبع. لكن الأفضل استخدام مخرجات الأخطاء (stderr) للسجلات.

## تمرين

### تمرين 1: دالة ثانية في العامل

أضف إلى العامل دالة `Label(name, price)` ترجع النص `name + ": " + str(price) + " EGP"`، ثم استدعها عبر `radcall` بالقيم `"Pen"` و`5`.

```python exercise
import json

def worker(line):
    msg = json.loads(line)
    funcs = {"Discount": lambda price, pct: price - price * pct / 100}
    return json.dumps({"id": msg["id"], "result": funcs[msg["func"]](*msg["args"])})

def radcall(target, *args):
    module, func = target.split(".", 1)
    return json.loads(worker(json.dumps({"id": 1, "func": func, "args": list(args)})))["result"]

print(radcall("PriceLib.Discount", 100, 10))
```

```python solution
import json

def worker(line):
    msg = json.loads(line)
    funcs = {"Discount": lambda price, pct: price - price * pct / 100,
             "Label": lambda name, price: name + ": " + str(price) + " EGP"}
    return json.dumps({"id": msg["id"], "result": funcs[msg["func"]](*msg["args"])})

def radcall(target, *args):
    module, func = target.split(".", 1)
    return json.loads(worker(json.dumps({"id": 1, "func": func, "args": list(args)})))["result"]

print(radcall("PriceLib.Discount", 100, 10))
print(radcall("PriceLib.Label", "Pen", 5))
```

```text output
90.0
Pen: 5 EGP
```

## اختبر نفسك

```quiz
{"question": "بأي شكل تمر الرسائل بين برنامجك وRAD Hub؟", "choices": ["XML", "كائن JSON واحد في كل سطر", "ملفات نصية", "صور"], "answer": 1, "explanation": "JSON سطرًا سطرًا، مع id يربط الرد بالطلب."}
```

```quiz
{"question": "كيف يعرف الـ Hub لغة الوحدة PriceLib؟", "choices": ["من اسمها", "من امتداد الملف (.cs = C#)", "يسأل المستخدم", "من الإنترنت"], "answer": 1, "explanation": "الامتداد يحدد اللغة والعامل المناسب."}
```

```quiz
{"question": "كيف تشغّل برنامجًا يستخدم المراجع من الطرفية؟", "choices": ["python main.py فقط", "python -m radide.runtimes.radhub <المجلد> -- python main.py", "لا يمكن", "بإعادة تشغيل الجهاز"], "answer": 1, "explanation": "الـ Hub يجب أن يعمل حتى يجد الوكيل من يوصله بالمكتبة."}
```

## الخلاصة

- **RAD Hub** مقسّم يوصل الاستدعاءات بين اللغات، وتشغّله البيئة مع كل `F5`.
- الرسائل JSON سطرًا سطرًا: `call` و`args`، ثم `result` أو `error`.
- العامل يشغّل الوحدة بلغتها، والامتداد يحدد اللغة.
- من الطرفية: `python -m radide.runtimes.radhub <المجلد> -- <البرنامج>`.
