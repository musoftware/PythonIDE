# الدرس 10: الأخطاء والاستثناءات والملفات

البرنامج الجيد لا ينهار عندما يكتب المستخدم حروفًا بدل رقم، أو عندما لا يجد ملفًا. في هذا الدرس نتعلم **معالجة الاستثناءات**، ثم نتعلم **قراءة الملفات وكتابتها** لكي تبقى بياناتنا محفوظة بعد إغلاق البرنامج.

## أنواع الأخطاء

1. **أخطاء الصياغة** (`SyntaxError`): كتابة غير صحيحة للغة، مثل نسيان `:`. تظهر قبل أن يبدأ البرنامج.
2. **الاستثناءات** (exceptions): أخطاء تحدث **أثناء التشغيل**، مثل القسمة على صفر أو تحويل `"abc"` إلى عدد.

| الاستثناء | متى يحدث |
|---|---|
| `ValueError` | قيمة غير مناسبة، مثل `int("abc")` |
| `ZeroDivisionError` | القسمة على صفر |
| `TypeError` | نوع غير مناسب، مثل `"a" + 1` |
| `NameError` | اسم غير معرّف |
| `IndexError` | فهرس خارج مدى القائمة |
| `KeyError` | مفتاح غير موجود في القاموس |
| `FileNotFoundError` | الملف غير موجود |

## `try` و `except`

> **تشبيه:** `try` مثل **شبكة الأمان تحت لاعب السيرك**: يحاول اللاعب الحركة، وإن سقط تلتقطه الشبكة بدل أن يقع على الأرض.

```python run
text = "abc"
try:
    n = int(text)
    print("العدد هو", n)
except ValueError:
    print(f"«{text}» ليس عددًا صحيحًا")
print("البرنامج مستمر")
```

```text output
«abc» ليس عددًا صحيحًا
البرنامج مستمر
```

عندما يحدث الاستثناء داخل `try`، تقفز Python فورًا إلى `except` المناسب، ثم يكمل البرنامج بعدها.

### عدة أنواع، و `else` و `finally`

```python run
def divide(a, b):
    try:
        result = a / b
    except ZeroDivisionError:
        print("لا يمكن القسمة على صفر")
    except TypeError:
        print("القيم يجب أن تكون أعدادًا")
    else:
        print("الناتج:", result)      # إذا لم يحدث خطأ
    finally:
        print("--- انتهت المحاولة")    # يُنفذ دائمًا

divide(10, 4)
divide(10, 0)
divide(10, "x")
```

```text output
الناتج: 2.5
--- انتهت المحاولة
لا يمكن القسمة على صفر
--- انتهت المحاولة
القيم يجب أن تكون أعدادًا
--- انتهت المحاولة
```

### الحصول على رسالة الخطأ

```python run
try:
    numbers = [1, 2, 3]
    print(numbers[10])
except IndexError as e:
    print("حدث خطأ:", e)
```

```text output
حدث خطأ: list index out of range
```

### مثال عملي: طلب رقم حتى يكون صحيحًا

```python run
while True:
    try:
        age = int(input("كم عمرك؟ "))
        break
    except ValueError:
        print("من فضلك اكتب رقمًا")
print(f"عمرك {age} سنة")
```

```text input
عشرون
20
```

```text output
كم عمرك؟ من فضلك اكتب رقمًا
كم عمرك؟ عمرك 20 سنة
```

> **نصيحة:** لا تكتب `except:` وحدها بدون نوع، لأنها تبتلع كل الأخطاء حتى التي لم تتوقعها فتخفي مشاكل حقيقية. حدد النوع الذي تتوقعه.

## رفع استثناء بنفسك: `raise`

```python run
def set_age(age):
    if age < 0:
        raise ValueError("العمر لا يمكن أن يكون سالبًا")
    return age

try:
    set_age(-5)
except ValueError as e:
    print("مرفوض:", e)
```

```text output
مرفوض: العمر لا يمكن أن يكون سالبًا
```

## الملفات

### الكتابة في ملف

```python run
with open("notes.txt", "w", encoding="utf-8") as f:
    f.write("السطر الأول\n")
    f.write("السطر الثاني\n")
print("تم الحفظ")

with open("notes.txt", encoding="utf-8") as f:
    content = f.read()
print(content)
```

```text output
تم الحفظ
السطر الأول
السطر الثاني
```

- `open(اسم_الملف, الوضع, encoding="utf-8")` تفتح الملف.
- `with` تغلق الملف تلقائيًا عند الانتهاء حتى لو حدث خطأ. استخدمها دائمًا.
- `encoding="utf-8"` ضرورية لكي تُحفظ العربية وتُقرأ بشكل صحيح في Windows.
- الملف يُنشأ في **مجلد المشروع** (المجلد الحالي للبرنامج). يمكنك رؤيته من **Project ← Open Project Folder**.

### أوضاع فتح الملف

| الوضع | معناه |
|---|---|
| `"r"` | قراءة (الافتراضي) |
| `"w"` | كتابة: ينشئ الملف أو **يمسح** محتواه القديم |
| `"a"` | إضافة في نهاية الملف |

### القراءة سطرًا سطرًا

```python run
with open("shopping.txt", "w", encoding="utf-8") as f:
    for item in ["خبز", "لبن", "جبن"]:
        f.write(item + "\n")

with open("shopping.txt", "a", encoding="utf-8") as f:
    f.write("بيض\n")

with open("shopping.txt", encoding="utf-8") as f:
    for number, line in enumerate(f, start=1):
        print(number, line.strip())
```

```text output
1 خبز
2 لبن
3 جبن
4 بيض
```

`line.strip()` تحذف رمز السطر الجديد `\n` من نهاية كل سطر.

### ملف غير موجود

```python run
try:
    with open("missing.txt", encoding="utf-8") as f:
        print(f.read())
except FileNotFoundError:
    print("الملف غير موجود، سننشئه لاحقًا")
```

```text output
الملف غير موجود، سننشئه لاحقًا
```

## حفظ البيانات بصيغة JSON

لحفظ قوائم وقواميس كاملة، أسهل طريقة هي صيغة **JSON**، والوحدة `json` تأتي مع Python:

```python run
import json

contacts = [
    {"name": "Ali", "phone": "0100000001"},
    {"name": "Nour", "phone": "0100000002"},
]
with open("contacts.json", "w", encoding="utf-8") as f:
    json.dump(contacts, f, ensure_ascii=False, indent=2)

with open("contacts.json", encoding="utf-8") as f:
    loaded = json.load(f)
for c in loaded:
    print(c["name"], c["phone"])
```

```text output
Ali 0100000001
Nour 0100000002
```

`ensure_ascii=False` تحفظ العربية كما هي بدل رموز مثل `\u0639`، و`indent=2` تجعل الملف مرتبًا سهل القراءة.

## ملفات CSV

ملفات CSV جداول نصية تفتحها برامج مثل Excel. الوحدة `csv` تقرؤها وتكتبها:

```python run
import csv

rows = [["name", "score"], ["Ali", 90], ["Sara", 85]]
with open("scores.csv", "w", newline="", encoding="utf-8") as f:
    csv.writer(f).writerows(rows)

with open("scores.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        print(row["name"], "->", row["score"])
```

```text output
Ali -> 90
Sara -> 85
```

## أخطاء شائعة

- **نسيان `encoding="utf-8"`**: قد تظهر العربية رموزًا غريبة أو يحدث `UnicodeDecodeError`.
- **فتح ملف بالوضع `"w"` وأنت تريد الإضافة**: يمسح كل ما فيه! استخدم `"a"`.
- **مسارات Windows**: اكتب `r"C:\data\file.txt"` أو `"C:/data/file.txt"`، لأن `\n` داخل `"C:\new"` تعني سطرًا جديدًا.

## تمارين

### التمرين 1

اكتب دالة `safe_divide(a, b)` ترجع ناتج القسمة، أو ترجع النص `"خطأ"` إذا كان `b` صفرًا (باستخدام `try`).

```python exercise
def safe_divide(a, b):
    pass

print(safe_divide(9, 3))
print(safe_divide(1, 0))
```

```python solution
def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return "خطأ"

print(safe_divide(9, 3))
print(safe_divide(1, 0))
```

```text output
3.0
خطأ
```

### التمرين 2

اكتب الأعداد من 1 إلى 5 في ملف `numbers.txt` (كل عدد في سطر)، ثم اقرأ الملف واطبع مجموعها.

```python exercise
# اكتب الملف ثم اقرأه
```

```python solution
with open("numbers.txt", "w", encoding="utf-8") as f:
    for n in range(1, 6):
        f.write(f"{n}\n")

total = 0
with open("numbers.txt", encoding="utf-8") as f:
    for line in f:
        total += int(line)
print("المجموع:", total)
```

```text output
المجموع: 15
```

### التمرين 3

احفظ القاموس `settings` في ملف `settings.json`، ثم اقرأه واطبع قيمة `"theme"`.

```python exercise
import json
settings = {"theme": "dark", "font_size": 14}
```

```python solution
import json
settings = {"theme": "dark", "font_size": 14}
with open("settings.json", "w", encoding="utf-8") as f:
    json.dump(settings, f)
with open("settings.json", encoding="utf-8") as f:
    loaded = json.load(f)
print(loaded["theme"])
```

```text output
dark
```

## اختبر نفسك

```quiz
{"question": "متى يُنفذ جزء finally؟", "choices": ["عند حدوث خطأ فقط", "عند عدم حدوث خطأ فقط", "دائمًا", "أبدًا"], "answer": 2, "explanation": "finally يُنفذ دائمًا، سواء حدث خطأ أم لا، ويُستخدم للتنظيف."}
```

```quiz
{"question": "ماذا يحدث عند فتح ملف موجود بالوضع \"w\"؟", "choices": ["يُضاف إلى نهايته", "يُمسح محتواه ويُكتب من جديد", "يحدث خطأ", "يُفتح للقراءة"], "answer": 1, "explanation": "الوضع w يمسح المحتوى القديم، أما a فيضيف في النهاية."}
```

```quiz
{"question": "لماذا نستخدم with open(...) as f؟", "choices": ["لأنها أسرع فقط", "لكي يُغلق الملف تلقائيًا", "لكي يُقرأ الملف بالعربية", "لا فائدة لها"], "answer": 1, "explanation": "with تضمن إغلاق الملف عند الانتهاء حتى لو حدث استثناء."}
```

## الخلاصة

- `try` / `except نوع` تلتقط الاستثناءات، و`else` عند النجاح، و`finally` دائمًا، و`raise` لرفع خطأ بنفسك.
- `with open(name, mode, encoding="utf-8") as f:` لقراءة الملفات وكتابتها، والأوضاع `r` و`w` و`a`.
- `json` لحفظ القوائم والقواميس، و`csv` للجداول.
