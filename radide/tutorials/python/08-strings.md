# الدرس 8: التعامل مع النصوص

النصوص (strings) في كل مكان: أسماء المستخدمين، والرسائل، وعناوين البريد، ومحتوى الملفات. وPython تقدم أدوات كثيرة وسهلة للتعامل معها.

## النص سلسلة من الحروف

النص في Python يشبه القائمة: كل حرف له فهرس يبدأ من صفر، ويمكنك التقطيع والمرور عليه:

```python run
word = "Python"
print(word[0])
print(word[-1])
print(word[0:3])
print(len(word))
for ch in word:
    print(ch, end="-")
print()
```

```text output
P
n
Pyt
6
P-y-t-h-o-n-
```

لكن النص **غير قابل للتغيير**: لا يمكنك كتابة `word[0] = "J"`. بدلًا من ذلك تنشئ نصًا جديدًا: `word = "J" + word[1:]`.

## أهم دوال النصوص

| الدالة | وظيفتها | مثال ← الناتج |
|---|---|---|
| `upper()` / `lower()` | أحرف كبيرة / صغيرة | `"Ab".upper()` ← `"AB"` |
| `title()` | أول حرف من كل كلمة كبير | `"ali hassan".title()` ← `"Ali Hassan"` |
| `strip()` | حذف المسافات من الطرفين | `"  hi ".strip()` ← `"hi"` |
| `replace(a, b)` | استبدال | `"a-b".replace("-", "+")` ← `"a+b"` |
| `split(sep)` | تقسيم إلى قائمة | `"a,b".split(",")` ← `["a", "b"]` |
| `sep.join(lst)` | دمج قائمة في نص | `"-".join(["a", "b"])` ← `"a-b"` |
| `find(x)` | موضع `x` (أو `-1`) | `"hello".find("l")` ← `2` |
| `count(x)` | عدد مرات الظهور | `"banana".count("a")` ← `3` |
| `startswith(x)` / `endswith(x)` | يبدأ / ينتهي بـ | `"file.py".endswith(".py")` ← `True` |
| `isdigit()` | كله أرقام؟ | `"123".isdigit()` ← `True` |

```python run
email = "  Ahmed.Ali@Example.COM  "
clean = email.strip().lower()
print(clean)
print(clean.endswith(".com"))
user, domain = clean.split("@")
print("المستخدم:", user)
print("النطاق:", domain)
print(clean.replace("example", "mail"))
```

```text output
ahmed.ali@example.com
True
المستخدم: ahmed.ali
النطاق: example.com
ahmed.ali@mail.com
```

> **مهم:** دوال النصوص **لا تغير النص الأصلي**، بل ترجع نصًا جديدًا. لذلك نكتب `clean = email.strip().lower()` ونحفظ الناتج في متغير.

## `split` و `join`

ثنائي قوي جدًا لتحويل النص إلى قائمة والعكس:

```python run
line = "Cairo,Giza,Luxor,Aswan"
cities = line.split(",")
print(cities)
print(len(cities))
print(" | ".join(cities))

sentence = "Python  is   easy"
print(sentence.split())        # بدون فاصل: يقسم على أي مسافات
```

```text output
['Cairo', 'Giza', 'Luxor', 'Aswan']
4
Cairo | Giza | Luxor | Aswan
['Python', 'is', 'easy']
```

## تنسيق النصوص بـ f-string

تعرفنا على f-string في الدرس 2. إليك خيارات تنسيق أكثر:

```python run
name = "Laila"
price = 1234.5
ratio = 0.756
print(f"[{name:>10}]")      # محاذاة لليمين في 10 خانات
print(f"[{name:<10}]")      # لليسار
print(f"[{name:^10}]")      # في المنتصف
print(f"{price:,.2f}")      # فاصل الآلاف وخانتان عشريتان
print(f"{ratio:.1%}")       # نسبة مئوية
print(f"{7:03d}")           # أصفار في البداية
```

```text output
[     Laila]
[Laila     ]
[  Laila   ]
1,234.50
75.6%
007
```

## النصوص متعددة الأسطر ورموز الهروب

```python run
poem = """السطر الأول
السطر الثاني
السطر الثالث"""
print(poem)
print("عمود1\tعمود2")
print("قال: \"مرحبًا\"")
print('C:\\Users\\Ali')
print(r"C:\new\test")       # نص خام: \ لا تعامَل كرمز خاص
```

```text output
السطر الأول
السطر الثاني
السطر الثالث
عمود1	عمود2
قال: "مرحبًا"
C:\Users\Ali
C:\new\test
```

| الرمز | معناه |
|---|---|
| `\n` | سطر جديد |
| `\t` | مسافة جدولة (Tab) |
| `\"` و `\'` | علامة تنصيص داخل النص |
| `\\` | شرطة مائلة عكسية |

النص الخام `r"..."` مفيد جدًا لمسارات الملفات في Windows.

## النصوص العربية

Python تتعامل مع العربية بشكل كامل (بترميز Unicode):

```python run
greeting = "السلام عليكم ورحمة الله"
words = greeting.split()
print(len(words), "كلمات")
print(words[0])
print(greeting.replace("السلام", "سلام"))
print("الله" in greeting)
```

```text output
4 كلمات
السلام
سلام عليكم ورحمة الله
True
```

## مثال: التحقق من كلمة مرور

```python run
password = "Py2026code"
has_digit = any(ch.isdigit() for ch in password)
has_upper = any(ch.isupper() for ch in password)
long_enough = len(password) >= 8
if has_digit and has_upper and long_enough:
    print("كلمة مرور قوية")
else:
    print("كلمة مرور ضعيفة")
```

```text output
كلمة مرور قوية
```

`any(...)` ترجع `True` إذا كان أي عنصر صحيحًا، وأختها `all(...)` ترجع `True` إذا كانت كل العناصر صحيحة.

## أخطاء شائعة

- **محاولة تعديل حرف:** `word[0] = "J"` تعطي `TypeError: 'str' object does not support item assignment`.
- **نسيان حفظ الناتج:** كتابة `name.strip()` وحدها لا تغير `name`.
- **مقارنة نصين بحالة أحرف مختلفة:** `"Ali" == "ali"` تعطي `False`؛ قارن بعد `lower()`.

## تمارين

### التمرين 1

اقرأ اسمًا كاملًا (مثلًا `  mohamed   salah `) ونظّفه: احذف المسافات الزائدة واجعل أول حرف من كل كلمة كبيرًا.

```python exercise
full = input("الاسم: ")
```

```python solution
full = input("الاسم: ")
clean = " ".join(full.split()).title()
print(clean)
```

```text input
  mohamed   salah 
```

```text output
الاسم: Mohamed Salah
```

### التمرين 2

اكتب برنامجًا يحدد هل الكلمة **متناظرة** (palindrome)، أي تُقرأ من الجهتين بنفس الشكل مثل `level`.

```python exercise
word = "level"
```

```python solution
word = "level"
if word == word[::-1]:
    print(f"{word} متناظرة")
else:
    print(f"{word} ليست متناظرة")
```

```text output
level متناظرة
```

### التمرين 3

حوّل التاريخ `2026-11-21` إلى الشكل `21/11/2026` باستخدام `split` و`join`.

```python exercise
date = "2026-11-21"
```

```python solution
date = "2026-11-21"
parts = date.split("-")
print("/".join(reversed(parts)))
```

```text output
21/11/2026
```

## اختبر نفسك

```quiz
{"question": "ما ناتج \"a,b,c\".split(\",\")؟", "choices": ["\"abc\"", "[\"a\", \"b\", \"c\"]", "(\"a\", \"b\", \"c\")", "3"], "answer": 1, "explanation": "split تقسم النص عند الفاصل وترجع قائمة."}
```

```quiz
{"question": "بعد تنفيذ s = \"hi\" ثم s.upper()، ما قيمة s؟", "choices": ["\"HI\"", "\"hi\"", "None", "خطأ"], "answer": 1, "explanation": "upper ترجع نصًا جديدًا ولا تغير s، فيجب كتابة s = s.upper()."}
```

```quiz
{"question": "ماذا يطبع print(f\"{3.14159:.2f}\")؟", "choices": ["3.14159", "3.1", "3.14", "3"], "answer": 2, "explanation": ".2f تعني خانتين بعد العلامة العشرية."}
```

## الخلاصة

- النص سلسلة حروف تدعم الفهرسة والتقطيع، لكنه غير قابل للتغيير.
- `strip` و`lower` و`upper` و`replace` و`split` و`join` و`find` أهم الدوال، وكلها ترجع نصًا جديدًا.
- f-string تدعم المحاذاة `:>10` وفاصل الآلاف `:,` والنسبة `:.1%`.
- النص الخام `r"..."` مفيد لمسارات Windows.
