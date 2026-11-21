# الدرس 12: الوحدات والحزم والبيئة الافتراضية .venv

قوة Python الحقيقية في **المكتبات**: آلاف الوحدات الجاهزة تحت يدك. في هذا الدرس نتعلم كيف نستورد الوحدات، وكيف نقسم برنامجنا إلى عدة ملفات، وكيف نثبّت مكتبات خارجية في **بيئة افتراضية** خاصة بالمشروع.

## ما هي الوحدة (Module)؟

**الوحدة** أي ملف `.py` فيه دوال وأصناف ومتغيرات. **المكتبة القياسية** (standard library) مجموعة ضخمة من الوحدات تأتي مع Python نفسها.

> **تشبيه:** الوحدة مثل **صندوق أدوات** متخصص: صندوق للرياضيات، وصندوق للتواريخ، وصندوق للأرقام العشوائية. `import` تعني «أحضر هذا الصندوق إلى طاولتي».

## طرق الاستيراد

```python run
import math
print(math.sqrt(81))

from math import pi, floor
print(floor(pi * 100) / 100)

import datetime as dt
d = dt.date(2026, 1, 15)
print(d.strftime("%d/%m/%Y"))
print(d.isoweekday())
```

```text output
9.0
3.14
15/01/2026
4
```

| الصيغة | الاستخدام بعدها |
|---|---|
| `import math` | `math.sqrt(9)` |
| `from math import sqrt` | `sqrt(9)` |
| `import datetime as dt` | `dt.date(...)` (اسم مختصر) |

> **تجنّب** `from math import *` لأنها تُحضر كل الأسماء فلا تعرف من أين جاء كل اسم، وقد تتعارض الأسماء.

## جولة سريعة في المكتبة القياسية

```python run
import random
import statistics
from collections import Counter
from pathlib import Path

random.seed(1)                       # لكي يتكرر نفس الناتج في كل تشغيل
print(random.randint(1, 6))
print(random.choice(["أحمر", "أخضر", "أزرق"]))

data = [3, 7, 7, 2, 9]
print(statistics.mean(data), statistics.median(data))

print(Counter("mississippi").most_common(2))

p = Path("report.final.txt")
print(p.stem, p.suffix)
```

```text output
2
أزرق
5.6 7
[('i', 4), ('s', 4)]
report.final .txt
```

| الوحدة | فيمَ تُستخدم |
|---|---|
| `math` | دوال رياضية |
| `random` | أرقام واختيارات عشوائية |
| `datetime` | التواريخ والأوقات |
| `os` و `pathlib` | الملفات والمجلدات والمسارات |
| `json` و `csv` | حفظ البيانات وقراءتها |
| `statistics` | المتوسط والوسيط والانحراف |
| `collections` | `Counter` و`defaultdict` وغيرها |
| `sqlite3` | قاعدة بيانات صغيرة في ملف |
| `tkinter` | النوافذ الرسومية (الدرس القادم!) |

## وحدتك الخاصة: تقسيم البرنامج إلى ملفات

عندما يكبر برنامجك، قسّمه إلى ملفات. في المثال التالي ملفان: `helpers.py` فيه الدوال، و`main.py` يستوردها:

```python run
# #file: main.py
import helpers
from helpers import VAT

print(helpers.add_vat(100))
print(helpers.format_money(1234.5))
print("نسبة الضريبة:", VAT)

# #file: helpers.py
"""دوال مساعدة للحسابات."""
VAT = 14


def add_vat(price):
    return price + price * VAT / 100


def format_money(amount):
    return f"{amount:,.2f} EGP"
```

```text output
114.0
1,234.50 EGP
نسبة الضريبة: 14
```

> **في الأمثلة:** السطر `# #file: helpers.py` علامة في هذه الدروس فقط تفصل الملفات؛ زر «جرّبه» ينشئ ملفين في المشروع. أما في مشروعك فأضف الملف من **Project ← Add Module...** (مشروع ← إضافة وحدة برمجية...)، واكتب اسمه، فتنشئه الـ IDE وتضيف سطر الاستيراد إلى ملف البداية تلقائيًا.

### فائدة `if __name__ == "__main__":`

كل ملف Python له متغير خاص اسمه `__name__`:

- إذا شغّلت الملف مباشرة تكون قيمته `"__main__"`.
- إذا استورده ملف آخر تكون قيمته اسم الوحدة، مثل `"tools"`.

لذلك نضع كود التجربة تحت هذا الشرط، فلا يُنفذ عند الاستيراد:

```python run
# #file: main.py
import tools
print("في main:", tools.double(21))

# #file: tools.py
def double(x):
    return x * 2


if __name__ == "__main__":
    print("تجربة tools مباشرة:", double(5))
else:
    print("تم استيراد tools، و__name__ =", __name__)
```

```text output
تم استيراد tools، و__name__ = tools
في main: 42
```

## الحزم (Packages)

**الحزمة** مجلد يضم عدة وحدات. نستورد منها بالنقطة:

```python run
# #file: main.py
from shop.prices import discount
from shop import stock

print(discount(200, 25))
print(stock.available("pen"))

# #file: shop/__init__.py
"""حزمة المتجر."""

# #file: shop/prices.py
def discount(price, percent):
    return price - price * percent / 100

# #file: shop/stock.py
ITEMS = {"pen": 12, "book": 0}


def available(name):
    return ITEMS.get(name, 0) > 0
```

```text output
150.0
True
```

الملف `__init__.py` يجعل المجلد `shop` حزمة (ويمكن أن يكون فارغًا).

## المكتبات الخارجية و pip

بجانب المكتبة القياسية يوجد موقع **PyPI** (pypi.org) فيه مئات الآلاف من المكتبات التي كتبها مبرمجون حول العالم، مثل `requests` للإنترنت، و`pandas` لتحليل البيانات، و`PySide6` للنوافذ. نثبّتها بأداة اسمها **pip**.

### البيئة الافتراضية .venv

إذا ثبّتّ كل المكتبات في Python الرئيسية لجهازك، فستتعارض مشاريعك: مشروع يحتاج الإصدار 1 من مكتبة، وآخر يحتاج الإصدار 2. الحل هو **البيئة الافتراضية** (virtual environment): نسخة خفيفة من Python **خاصة بكل مشروع** في مجلد اسمه `.venv` داخل المشروع، ولها مكتباتها الخاصة.

> **تشبيه:** البيئة الافتراضية مثل **درج خاص لكل مشروع** على مكتبك: أدوات مشروع الرسم في درجه، وأدوات مشروع الحسابات في درج آخر، فلا تختلط.

### تثبيت مكتبة من داخل RAD IDE

1. افتح مشروعك، ثم **Project ← Manage Packages...** (مشروع ← إدارة الحزم...).
2. في الأعلى اختر **Install into:** ← **Project virtual environment (.venv) - recommended**.
3. اكتب اسم المكتبة في خانة البحث، مثلًا `python-dateutil`، واضغط **Search** أو Enter.
4. اختر الإصدار واضغط **Install**.

في أول تثبيت تنشئ الـ IDE المجلد `.venv` داخل المشروع بنفسها، ثم تثبّت المكتبة فيه، وتكتب اسمها وإصدارها في الملف `requirements.txt` لكي يستطيع أي شخص آخر تثبيت نفس المكتبات. ومن الآن فصاعدًا، **Run** و**Debug** يستخدمان Python الموجودة في `.venv` تلقائيًا.

ما تفعله الـ IDE يعادل هذه الأوامر في سطر الأوامر:

```text
python -m venv .venv
.venv\Scripts\python -m pip install python-dateutil
.venv\Scripts\python -m pip freeze > requirements.txt
```

ولو نقلت المشروع إلى جهاز آخر، يكفي أمر واحد لإعادة تثبيت كل شيء:

```text
.venv\Scripts\python -m pip install -r requirements.txt
```

### استخدام المكتبة بعد تثبيتها

```python run
from datetime import date
from dateutil.relativedelta import relativedelta

birth = date(2000, 5, 20)
today = date(2026, 11, 21)
age = relativedelta(today, birth)
print(f"العمر: {age.years} سنة و {age.months} شهر و {age.days} يوم")
print("بعد 3 أشهر:", today + relativedelta(months=3))
```

```text output
العمر: 26 سنة و 6 شهر و 1 يوم
بعد 3 أشهر: 2027-02-21
```

إذا ظهر لك `ModuleNotFoundError: No module named 'dateutil'` فمعناه أن المكتبة غير مثبتة في Python التي يعمل بها المشروع: ثبّتها من **Manage Packages**.

> **ملحوظة:** اسم المكتبة عند التثبيت قد يختلف عن اسمها عند الاستيراد: نثبّت `python-dateutil` ونستورد `dateutil`، ونثبّت `PySide6` ونستورد `PySide6`، ونثبّت `pillow` ونستورد `PIL`.

## أخطاء شائعة

- **تسمية ملفك باسم وحدة قياسية**، مثل `random.py` أو `math.py`: عندها `import random` تستورد ملفك أنت بدل المكتبة! اختر أسماء مختلفة.
- **`ModuleNotFoundError`**: المكتبة غير مثبتة في بيئة المشروع، أو الاسم مكتوب خطأ.
- **الاستيراد الدائري**: ملفان يستورد كل منهما الآخر. انقل الكود المشترك إلى ملف ثالث.

## تمارين

### التمرين 1

استخدم الوحدة `datetime` لتطبع عدد الأيام بين `2026-01-01` و`2026-12-31`.

```python exercise
from datetime import date
```

```python solution
from datetime import date
days = (date(2026, 12, 31) - date(2026, 1, 1)).days
print("عدد الأيام:", days)
```

```text output
عدد الأيام: 364
```

### التمرين 2

أنشئ وحدة `geometry.py` فيها الدالة `rect_area(w, h)`، واستدعها من `main.py` لتطبع مساحة مستطيل `5 × 3`.

```python exercise
# #file: main.py
import geometry

# #file: geometry.py
def rect_area(w, h):
    pass
```

```python solution
# #file: main.py
import geometry
print(geometry.rect_area(5, 3))

# #file: geometry.py
def rect_area(w, h):
    return w * h
```

```text output
15
```

### التمرين 3

استخدم `Counter` من `collections` لتطبع أكثر 3 كلمات تكرارًا في النص.

```python exercise
from collections import Counter
text = "a b c a b a d e a b c"
```

```python solution
from collections import Counter
text = "a b c a b a d e a b c"
print(Counter(text.split()).most_common(3))
```

```text output
[('a', 4), ('b', 3), ('c', 2)]
```

## اختبر نفسك

```quiz
{"question": "ما فائدة البيئة الافتراضية .venv؟", "choices": ["تسريع Python", "عزل مكتبات كل مشروع عن المشاريع الأخرى", "حماية الكود من النسخ", "ترجمة الكود إلى exe"], "answer": 1, "explanation": "كل مشروع يحصل على مكتباته وإصداراته الخاصة دون تعارض."}
```

```quiz
{"question": "من أين تثبّت مكتبة خارجية في RAD IDE؟", "choices": ["Tools > Options", "Project > Manage Packages...", "File > Open Folder", "Debug > Start"], "answer": 1, "explanation": "Project > Manage Packages تثبّت المكتبة في .venv المشروع وتحدّث requirements.txt."}
```

```quiz
{"question": "ماذا يحدث للكود تحت if __name__ == \"__main__\": عند استيراد الملف من ملف آخر؟", "choices": ["يُنفذ مرتين", "لا يُنفذ", "يحدث خطأ", "يُنفذ مرة واحدة"], "answer": 1, "explanation": "عند الاستيراد تكون __name__ اسم الوحدة وليس \"__main__\"، فلا يُنفذ."}
```

## الخلاصة

- `import` و`from ... import` و`as` لاستيراد الوحدات، والمكتبة القياسية غنية جدًا.
- قسّم برنامجك إلى ملفات (Project ← Add Module...)، والحزمة مجلد فيه `__init__.py`.
- المكتبات الخارجية من PyPI تُثبّت بـ pip في `.venv` المشروع عبر **Project ← Manage Packages...**، وتُسجَّل في `requirements.txt`.
