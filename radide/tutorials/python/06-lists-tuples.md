# الدرس 6: القوائم والصفوف (list و tuple)

تخيّل أنك تريد حفظ درجات 30 طالبًا. هل ستنشئ 30 متغيرًا؟ بالطبع لا! **القائمة** (list) تحفظ عناصر كثيرة تحت اسم واحد.

> **تشبيه:** القائمة مثل **قطار** له عربات مرقّمة. كل عربة فيها قيمة، وترقيم العربات يبدأ من **صفر**.

## إنشاء قائمة والوصول لعناصرها

```python run
grades = [85, 92, 78, 95, 60]
names = ["Ali", "Sara", "Omar"]
empty = []

print(grades)
print(grades[0])      # العنصر الأول
print(grades[2])      # العنصر الثالث
print(grades[-1])     # العنصر الأخير
print(len(grades))    # عدد العناصر
```

```text output
[85, 92, 78, 95, 60]
85
78
60
5
```

- العنصر الأول رقمه (فهرسه) `0`، والثاني `1`، وهكذا.
- الفهرس السالب يعدّ من النهاية: `-1` هو الأخير، و`-2` الذي قبله.
- `len()` تُرجع عدد العناصر.

## تعديل القائمة

القوائم **قابلة للتغيير** (mutable): يمكنك تعديل عناصرها وإضافة عناصر وحذفها.

```python run
fruits = ["تفاح", "موز"]
fruits.append("برتقال")        # إضافة في النهاية
fruits.insert(0, "مانجو")      # إضافة في موضع محدد
print(fruits)
fruits[1] = "عنب"              # تغيير عنصر
print(fruits)
fruits.remove("موز")           # حذف بالقيمة
last = fruits.pop()            # حذف الأخير وإرجاعه
print("حُذف:", last)
print(fruits)
```

```text output
['مانجو', 'تفاح', 'موز', 'برتقال']
['مانجو', 'عنب', 'موز', 'برتقال']
حُذف: برتقال
['مانجو', 'عنب']
```

### أهم دوال القوائم

| الدالة | وظيفتها |
|---|---|
| `lst.append(x)` | تضيف `x` في النهاية |
| `lst.insert(i, x)` | تضيف `x` في الموضع `i` |
| `lst.remove(x)` | تحذف أول ظهور لـ `x` |
| `lst.pop()` / `lst.pop(i)` | تحذف الأخير (أو العنصر `i`) وترجعه |
| `lst.sort()` | ترتّب القائمة نفسها |
| `lst.reverse()` | تعكس ترتيبها |
| `lst.index(x)` | موضع `x` |
| `lst.count(x)` | كم مرة يظهر `x` |
| `x in lst` | هل `x` موجود؟ (`True`/`False`) |

```python run
numbers = [5, 3, 8, 1, 9, 3]
print(sum(numbers), max(numbers), min(numbers))
print(numbers.count(3))
print(8 in numbers, 7 in numbers)
numbers.sort()
print(numbers)
print(sorted(numbers, reverse=True))   # نسخة مرتبة تنازليًا
```

```text output
29 9 1
2
True False
[1, 3, 3, 5, 8, 9]
[9, 8, 5, 3, 3, 1]
```

> **الفرق بين `sort` و`sorted`:** `lst.sort()` تغيّر القائمة نفسها ولا ترجع شيئًا، أما `sorted(lst)` فترجع **قائمة جديدة** مرتبة وتترك الأصلية كما هي.

## التقطيع (Slicing)

يمكنك أخذ جزء من القائمة بالصيغة `lst[بداية:نهاية]`، والنهاية غير مشمولة:

```python run
letters = ["a", "b", "c", "d", "e", "f"]
print(letters[1:4])    # من 1 حتى قبل 4
print(letters[:3])     # أول ثلاثة
print(letters[3:])     # من 3 حتى النهاية
print(letters[::2])    # كل عنصر ثانٍ
print(letters[::-1])   # معكوسة
```

```text output
['b', 'c', 'd']
['a', 'b', 'c']
['d', 'e', 'f']
['a', 'c', 'e']
['f', 'e', 'd', 'c', 'b', 'a']
```

## المرور على القائمة

```python run
grades = [85, 92, 78]
for g in grades:
    print("الدرجة:", g)

for i, g in enumerate(grades, start=1):
    print(f"الطالب {i}: {g}")
```

```text output
الدرجة: 85
الدرجة: 92
الدرجة: 78
الطالب 1: 85
الطالب 2: 92
الطالب 3: 78
```

`enumerate` تعطيك الرقم والعنصر معًا، وهذا مفيد جدًا عند الترقيم.

## بناء القوائم بطريقة مختصرة (List Comprehension)

بدل حلقة كاملة لبناء قائمة، تتيح Python صيغة مختصرة وأنيقة:

```python run
squares = [n * n for n in range(1, 6)]
print(squares)

grades = [85, 42, 78, 95, 30]
passed = [g for g in grades if g >= 50]
print(passed)
```

```text output
[1, 4, 9, 16, 25]
[85, 78, 95]
```

اقرأها هكذا: «قائمة من `n * n` لكل `n` في `range(1, 6)`».

## القوائم المتداخلة (جدول)

```python run
table = [
    [1, 2, 3],
    [4, 5, 6],
]
print(table[1][2])      # الصف 1، العمود 2
for row in table:
    print(row)
```

```text output
6
[1, 2, 3]
[4, 5, 6]
```

## الصفوف (tuple)

**الصف** (tuple) مثل القائمة لكنه **غير قابل للتغيير** (immutable). يُكتب بأقواس عادية:

```python run
point = (3, 4)
print(point[0], point[1])

x, y = point           # فك الصف إلى متغيرين
print(f"x={x}, y={y}")

colors = ("أحمر", "أخضر", "أزرق")
print(len(colors), colors[-1])
```

```text output
3 4
x=3, y=4
3 أزرق
```

متى نستخدم الصف؟ عندما تكون البيانات ثابتة بطبيعتها: إحداثيات نقطة، أو تاريخ (سنة، شهر، يوم)، أو ألوان RGB. ومحاولة تغييره تعطي خطأ:

```python run
point = (3, 4)
point[0] = 10
```

```text output
Traceback (most recent call last):
  File "main.py", line 2, in <module>
    point[0] = 10
TypeError: 'tuple' object does not support item assignment
```

## خطأ شائع: الفهرس خارج المدى

```python run
names = ["Ali", "Sara", "Omar"]
print(names[3])
```

```text output
Traceback (most recent call last):
  File "main.py", line 2, in <module>
    print(names[3])
IndexError: list index out of range
```

القائمة فيها 3 عناصر، فهارسها `0` و`1` و`2` فقط. تذكّر: **آخر فهرس = الطول - 1**.

### خطأ آخر: النسخ بالإسناد

```python run
a = [1, 2, 3]
b = a            # b ليست نسخة! بل اسم آخر لنفس القائمة
b.append(4)
print(a)
c = a.copy()     # هذه نسخة حقيقية
c.append(5)
print(a, c)
```

```text output
[1, 2, 3, 4]
[1, 2, 3, 4] [1, 2, 3, 4, 5]
```

## تمارين

### التمرين 1

عندك قائمة درجات. اطبع المتوسط (المجموع ÷ العدد) بخانتين عشريتين، وأعلى درجة.

```python exercise
grades = [70, 85, 90, 65, 88]
```

```python solution
grades = [70, 85, 90, 65, 88]
average = sum(grades) / len(grades)
print(f"المتوسط: {average:.2f}")
print("الأعلى:", max(grades))
```

```text output
المتوسط: 79.60
الأعلى: 90
```

### التمرين 2

اقرأ 3 أسماء من المستخدم وضعها في قائمة، ثم اطبعها مرتبة أبجديًا كل اسم في سطر.

```python exercise
names = []
```

```python solution
names = []
for i in range(3):
    names.append(input())
for name in sorted(names):
    print(name)
```

```text input
Zainab
Ahmed
Mariam
```

```text output
Ahmed
Mariam
Zainab
```

### التمرين 3

باستخدام List Comprehension، كوّن قائمة بالأعداد من 1 إلى 30 التي تقبل القسمة على 15 (أي على 3 و5 معًا) أو على 7، ثم اطبعها.

```python exercise
result = []
print(result)
```

```python solution
result = [n for n in range(1, 31) if n % 15 == 0 or n % 7 == 0]
print(result)
```

```text output
[7, 14, 15, 21, 28, 30]
```

## اختبر نفسك

```quiz
{"question": "إذا كانت lst = [10, 20, 30, 40]، ما قيمة lst[-2]؟", "choices": ["20", "30", "40", "خطأ"], "answer": 1, "explanation": "-1 هو 40، و-2 هو الذي قبله 30."}
```

```quiz
{"question": "ما الفرق الأساسي بين list و tuple؟", "choices": ["tuple أسرع في الطباعة فقط", "list غير قابلة للتغيير", "tuple غير قابلة للتغيير بعد إنشائها", "لا فرق"], "answer": 2, "explanation": "الصف tuple لا يمكن تعديل عناصره، أما القائمة فيمكن."}
```

```quiz
{"question": "ما ناتج [1, 2, 3, 4, 5][1:3]؟", "choices": ["[1, 2, 3]", "[2, 3]", "[2, 3, 4]", "[1, 2]"], "answer": 1, "explanation": "من الفهرس 1 حتى قبل الفهرس 3، أي العنصران 2 و3."}
```

## الخلاصة

- القائمة `[ ]` تحفظ عناصر مرتبة وقابلة للتغيير، والفهرسة تبدأ من 0.
- `append` و`insert` و`remove` و`pop` و`sort` أهم دوالها، و`in` للبحث.
- التقطيع `lst[a:b]`، و`enumerate` للترقيم، وList Comprehension لبناء القوائم باختصار.
- الصف `( )` مثل القائمة لكنه ثابت.
