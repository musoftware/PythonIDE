# الدرس 7: القواميس والمجموعات (dict و set)

في القائمة نصل للعنصر برقمه: `grades[0]`. لكن ماذا لو أردنا أن نصل لدرجة الطالب **باسمه**؟ هنا يأتي **القاموس** (dictionary).

> **تشبيه:** القاموس مثل **دليل الهاتف**: تبحث بالاسم (المفتاح) فتجد الرقم (القيمة). أو مثل القاموس الحقيقي: تبحث بالكلمة فتجد معناها.

## إنشاء قاموس

القاموس مجموعة من أزواج **مفتاح: قيمة** (key: value) بين أقواس معقوصة:

```python run
student = {
    "name": "Sara",
    "age": 21,
    "city": "Alexandria",
}
print(student["name"])
print(student["age"])
print(len(student))
print(student)
```

```text output
Sara
21
3
{'name': 'Sara', 'age': 21, 'city': 'Alexandria'}
```

- المفتاح غالبًا نص أو عدد، ولا يتكرر في نفس القاموس.
- القيمة يمكن أن تكون أي شيء: عدد أو نص أو قائمة أو حتى قاموس آخر.

## الإضافة والتعديل والحذف

```python run
prices = {"شاي": 10, "قهوة": 25}
prices["عصير"] = 30        # مفتاح جديد = إضافة
prices["شاي"] = 12         # مفتاح موجود = تعديل
print(prices)
del prices["قهوة"]          # حذف
print(prices)
print("قهوة" in prices)     # هل المفتاح موجود؟
```

```text output
{'شاي': 12, 'قهوة': 25, 'عصير': 30}
{'شاي': 12, 'عصير': 30}
False
```

## القراءة الآمنة بـ `get`

إذا قرأت مفتاحًا غير موجود بالأقواس `[ ]` يحدث خطأ `KeyError`. أما `get` فترجع `None` أو قيمة افتراضية تحددها:

```python run
stock = {"pen": 40, "book": 12}
print(stock.get("pen"))
print(stock.get("bag"))
print(stock.get("bag", 0))
```

```text output
40
None
0
```

```python run
stock = {"pen": 40, "book": 12}
print(stock["bag"])
```

```text output
Traceback (most recent call last):
  File "main.py", line 2, in <module>
    print(stock["bag"])
KeyError: 'bag'
```

## المرور على القاموس

```python run
capitals = {"Egypt": "Cairo", "Morocco": "Rabat", "Jordan": "Amman"}

for country in capitals:                     # المفاتيح
    print(country)

for country, city in capitals.items():       # المفتاح والقيمة معًا
    print(f"عاصمة {country} هي {city}")

print(list(capitals.keys()))
print(list(capitals.values()))
```

```text output
Egypt
Morocco
Jordan
عاصمة Egypt هي Cairo
عاصمة Morocco هي Rabat
عاصمة Jordan هي Amman
['Egypt', 'Morocco', 'Jordan']
['Cairo', 'Rabat', 'Amman']
```

## مثال: عدّ تكرار الكلمات

هذا من أشهر استخدامات القواميس:

```python run
text = "the cat and the dog and the bird"
counts = {}
for word in text.split():
    counts[word] = counts.get(word, 0) + 1
print(counts)

for word, n in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
    print(word, n)
```

```text output
{'the': 3, 'cat': 1, 'and': 2, 'dog': 1, 'bird': 1}
the 3
and 2
cat 1
dog 1
bird 1
```

- `text.split()` تقسم النص إلى كلمات (سنراها في درس النصوص).
- `counts.get(word, 0) + 1`: خذ العدد الحالي (أو صفرًا إن لم توجد الكلمة) وزِد واحدًا.
- `key=lambda kv: kv[1]` تعني «رتّب حسب القيمة (العدد)». سنشرح `lambda` في درس الدوال.

## قائمة من القواميس

بهذه الطريقة نمثل **جدولًا** من السجلات، مثل قاعدة بيانات صغيرة:

```python run
students = [
    {"name": "Ali", "grade": 88},
    {"name": "Mona", "grade": 95},
    {"name": "Hassan", "grade": 72},
]
for s in students:
    print(f"{s['name']:<8} {s['grade']}")

best = max(students, key=lambda s: s["grade"])
print("الأول:", best["name"])
```

```text output
Ali      88
Mona     95
Hassan   72
الأول: Mona
```

`{s['name']:<8}` تعني: اطبع الاسم في مساحة عرضها 8 حروف ومحاذاة لليسار، حتى تظهر الأعمدة مرتبة.

## المجموعات (set)

**المجموعة** (set) تحفظ عناصر **بدون تكرار** وبدون ترتيب ثابت:

```python run
numbers = [1, 2, 2, 3, 3, 3]
unique = set(numbers)
print(unique)
print(len(unique))

tags = {"python", "code"}
tags.add("ide")
tags.add("python")       # موجود بالفعل: لا يتكرر
print(sorted(tags))
```

```text output
{1, 2, 3}
3
['code', 'ide', 'python']
```

### عمليات المجموعات

```python run
a = {"Ali", "Sara", "Omar"}
b = {"Sara", "Mona"}
print(sorted(a & b))     # التقاطع: في الاثنين
print(sorted(a | b))     # الاتحاد: في أي منهما
print(sorted(a - b))     # الفرق: في a وليس في b
```

```text output
['Sara']
['Ali', 'Mona', 'Omar', 'Sara']
['Ali', 'Omar']
```

> **ملحوظة:** استخدمنا `sorted` عند طباعة المجموعات لأن ترتيب عناصر المجموعة غير مضمون، و`sorted` يجعل الناتج ثابتًا ومرتبًا.

## متى أستخدم أيّها؟

| تحتاج إلى... | استخدم |
|---|---|
| عناصر مرتبة تصل إليها بالرقم | `list` |
| بيانات ثابتة لا تتغير | `tuple` |
| البحث بمفتاح (اسم، كود...) | `dict` |
| عناصر بلا تكرار، أو التحقق السريع من الوجود | `set` |

## أخطاء شائعة

- **`KeyError`:** قراءة مفتاح غير موجود بـ `[ ]`. استخدم `in` أو `get`.
- **المجموعة الفارغة:** `{}` تنشئ **قاموسًا** فارغًا وليس مجموعة. المجموعة الفارغة تُكتب `set()`.
- **القائمة لا تصلح مفتاحًا:** `{[1, 2]: "x"}` خطأ لأن القائمة قابلة للتغيير. استخدم صفًا `(1, 2)`.

## تمارين

### التمرين 1

عندك قاموس أسعار. اطبع كل منتج وسعره، ثم مجموع الأسعار.

```python exercise
menu = {"فول": 15, "طعمية": 10, "بطاطس": 20}
```

```python solution
menu = {"فول": 15, "طعمية": 10, "بطاطس": 20}
for item, price in menu.items():
    print(f"{item}: {price}")
print("المجموع:", sum(menu.values()))
```

```text output
فول: 15
طعمية: 10
بطاطس: 20
المجموع: 45
```

### التمرين 2

عُدّ تكرار كل حرف في الكلمة `banana` باستخدام قاموس، واطبع القاموس.

```python exercise
word = "banana"
counts = {}
```

```python solution
word = "banana"
counts = {}
for ch in word:
    counts[ch] = counts.get(ch, 0) + 1
print(counts)
```

```text output
{'b': 1, 'a': 3, 'n': 2}
```

### التمرين 3

طالبان سجّلا في مواد مختلفة. اطبع المواد المشتركة بينهما مرتبة، باستخدام المجموعات.

```python exercise
ali = ["math", "physics", "art", "python"]
sara = ["python", "biology", "math"]
```

```python solution
ali = ["math", "physics", "art", "python"]
sara = ["python", "biology", "math"]
common = set(ali) & set(sara)
print(sorted(common))
```

```text output
['math', 'python']
```

## اختبر نفسك

```quiz
{"question": "إذا كان d = {\"a\": 1}، ماذا يحدث عند تنفيذ d[\"b\"] = 2؟", "choices": ["خطأ KeyError", "يُضاف المفتاح b بالقيمة 2", "تتغير قيمة a", "لا شيء"], "answer": 1, "explanation": "الإسناد لمفتاح غير موجود يضيفه إلى القاموس."}
```

```quiz
{"question": "ماذا ترجع d.get(\"x\", 0) إذا لم يكن المفتاح x موجودًا؟", "choices": ["None", "خطأ", "0", "\"x\""], "answer": 2, "explanation": "get ترجع القيمة الافتراضية التي أعطيتها (0) بدل الخطأ."}
```

```quiz
{"question": "ما ناتج len(set([1, 1, 2, 2, 2]))؟", "choices": ["5", "2", "3", "1"], "answer": 1, "explanation": "المجموعة تحذف التكرار، فيبقى العنصران 1 و2."}
```

## الخلاصة

- القاموس `{مفتاح: قيمة}` للبحث بالمفتاح، و`get` للقراءة الآمنة، و`items()` للمرور على الأزواج.
- قائمة من القواميس تمثل جدولًا من السجلات.
- المجموعة `set` بلا تكرار، وتدعم التقاطع `&` والاتحاد `|` والفرق `-`.
