# الدرس 9: الدوال (Functions)

كلما كبر البرنامج ستجد نفسك تكرر نفس الأسطر في أماكن مختلفة. **الدالة** تجمع هذه الأسطر تحت اسم واحد، وتستدعيها متى شئت.

> **تشبيه:** الدالة مثل **ماكينة العصير**: تضع فيها فاكهة (المدخلات)، فتعمل بطريقتها الداخلية، وتخرج لك عصيرًا (الناتج). لا تحتاج أن تعرف كيف تعمل من الداخل في كل مرة؛ يكفي أن تعرف ماذا تضع وماذا تأخذ.

## تعريف دالة واستدعاؤها

```python run
def greet():
    print("أهلًا بك!")
    print("نتمنى لك يومًا سعيدًا")

greet()
greet()
```

```text output
أهلًا بك!
نتمنى لك يومًا سعيدًا
أهلًا بك!
نتمنى لك يومًا سعيدًا
```

- `def` تعني «عرّف دالة»، ثم الاسم، ثم الأقواس، ثم النقطتان `:`.
- جسم الدالة مزاح، ولا يُنفذ إلا عند **استدعائها** بكتابة اسمها مع الأقواس `greet()`.

## المعاملات (Parameters)

المعاملات هي «فتحات» تستقبل بها الدالة القيم:

```python run
def greet(name, times):
    for i in range(times):
        print(f"أهلًا يا {name}")

greet("Huda", 2)
greet(times=1, name="Karim")    # تمرير القيم بالاسم
```

```text output
أهلًا يا Huda
أهلًا يا Huda
أهلًا يا Karim
```

القيم التي نمررها عند الاستدعاء (`"Huda"` و`2`) تسمى **الوسائط** (arguments).

## إرجاع قيمة بـ `return`

أغلب الدوال تحسب شيئًا و**ترجعه** لمن استدعاها:

```python run
def area(width, height):
    return width * height

a = area(4, 5)
print("المساحة:", a)
print("مجموع مساحتين:", area(2, 3) + area(1, 1))
```

```text output
المساحة: 20
مجموع مساحتين: 7
```

> **الفرق بين `print` و`return`:** `print` تعرض القيمة على الشاشة فقط، أما `return` فتسلّم القيمة للبرنامج لكي يستخدمها في حسابات أخرى. الدالة التي ليس فيها `return` ترجع `None`.

`return` تنهي الدالة فورًا، ويمكن أن تُرجع عدة قيم على شكل صف:

```python run
def min_max(numbers):
    if not numbers:
        return None, None
    return min(numbers), max(numbers)

low, high = min_max([4, 9, 1, 7])
print(low, high)
print(min_max([]))
```

```text output
1 9
(None, None)
```

## القيم الافتراضية للمعاملات

```python run
def price_with_tax(price, tax=14):
    return price + price * tax / 100

print(price_with_tax(100))        # تستخدم 14
print(price_with_tax(100, 5))     # تستخدم 5
```

```text output
114.0
105.0
```

## نطاق المتغيرات (Scope)

المتغير الذي تنشئه **داخل** الدالة **محلي** (local): يولد عند بدء الدالة ويختفي عند انتهائها، ولا يراه باقي البرنامج.

```python run
counter = 100          # متغير عام (global)

def test():
    counter = 5        # متغير محلي جديد بنفس الاسم
    print("داخل الدالة:", counter)

test()
print("خارج الدالة:", counter)
```

```text output
داخل الدالة: 5
خارج الدالة: 100
```

> **نصيحة:** بدل أن تعدّل متغيرات عامة من داخل الدوال، مرّر القيم كمعاملات وأرجع النتائج بـ `return`. هذا يجعل الكود أوضح وأسهل في الاختبار. (توجد الكلمة `global` لتعديل متغير عام، لكن استخدمها نادرًا.)

## توثيق الدالة (Docstring)

النص الذي تكتبه في أول سطر من الدالة بين علامات تنصيص ثلاثية يسمى **docstring**، وتعرضه الـ IDE في التلميح عندما تكتب اسم الدالة:

```python run
def bmi(weight, height):
    """يحسب مؤشر كتلة الجسم: الوزن بالكيلو ÷ مربع الطول بالمتر."""
    return weight / height ** 2

print(f"{bmi(70, 1.75):.1f}")
print(bmi.__doc__)
```

```text output
22.9
يحسب مؤشر كتلة الجسم: الوزن بالكيلو ÷ مربع الطول بالمتر.
```

## عدد غير محدد من الوسائط: `*args`

```python run
def total(*numbers):
    s = 0
    for n in numbers:
        s += n
    return s

print(total(1, 2))
print(total(5, 10, 15, 20))
```

```text output
3
50
```

`*numbers` تجمع كل الوسائط في صف واحد. (وتوجد أيضًا `**kwargs` لجمع الوسائط المسماة في قاموس.)

## دوال `lambda` الصغيرة

`lambda` دالة قصيرة بلا اسم في سطر واحد، تُستخدم غالبًا مع `sorted` و`max`:

```python run
square = lambda x: x * x
print(square(6))

people = [("Ali", 30), ("Mona", 25), ("Sami", 35)]
by_age = sorted(people, key=lambda p: p[1])
print(by_age)
```

```text output
36
[('Mona', 25), ('Ali', 30), ('Sami', 35)]
```

## الدالة التي تستدعي نفسها (Recursion)

```python run
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(5))
```

```text output
120
```

`factorial(5)` = `5 × factorial(4)` = `5 × 4 × factorial(3)`... حتى نصل إلى `1`. لا بد من **شرط توقف** (`n <= 1`) وإلا استمرت الاستدعاءات بلا نهاية.

## مثال منظّم: برنامج بدالة `main`

البرامج الحقيقية تقسّم العمل إلى دوال صغيرة، ودالة رئيسية `main` تستدعيها:

```python run
def read_grades():
    return [80, 95, 67, 73]

def average(values):
    return sum(values) / len(values)

def report(values):
    print("الدرجات:", values)
    print(f"المتوسط: {average(values):.1f}")
    print("الناجحون:", len([v for v in values if v >= 70]))

def main():
    grades = read_grades()
    report(grades)

if __name__ == "__main__":
    main()
```

```text output
الدرجات: [80, 95, 67, 73]
المتوسط: 78.8
الناجحون: 3
```

السطر `if __name__ == "__main__":` معناه «شغّل `main` فقط إذا كان هذا الملف هو الذي بدأ التشغيل، وليس إذا استورده ملف آخر». ستفهم قيمته في درس الوحدات.

## أخطاء شائعة

### نسيان الأقواس عند الاستدعاء

```python run
def hello():
    return "مرحبًا"

result = hello          # بدون أقواس: هذه هي الدالة نفسها، وليست ناتجها!
print(type(result))
result = hello()        # مع الأقواس: نستدعيها فنحصل على ناتجها
print(result)
```

```text output
<class 'function'>
مرحبًا
```

### عدد خاطئ من الوسائط

```python run
def add(a, b):
    return a + b

print(add(1))
```

```text output
Traceback (most recent call last):
  File "main.py", line 4, in <module>
    print(add(1))
TypeError: add() missing 1 required positional argument: 'b'
```

### نسيان `return`

إذا نسيت `return` ستحصل على `None`، فمثلًا `x = area(2, 3)` تجعل `x` تساوي `None` لو كانت الدالة تطبع ولا ترجع.

## تمارين

### التمرين 1

اكتب دالة `is_even(n)` ترجع `True` إذا كان العدد زوجيًا، ثم اطبع نتيجتها للعددين `4` و`7`.

```python exercise
def is_even(n):
    pass

print(is_even(4))
print(is_even(7))
```

```python solution
def is_even(n):
    return n % 2 == 0

print(is_even(4))
print(is_even(7))
```

```text output
True
False
```

### التمرين 2

اكتب دالة `count_vowels(text)` ترجع عدد الحروف المتحركة الإنجليزية (`a e i o u`) في نص.

```python exercise
def count_vowels(text):
    pass

print(count_vowels("Programming is fun"))
```

```python solution
def count_vowels(text):
    count = 0
    for ch in text.lower():
        if ch in "aeiou":
            count += 1
    return count

print(count_vowels("Programming is fun"))
```

```text output
5
```

### التمرين 3

اكتب دالة `grade(score)` ترجع التقدير: `A` من 90 فأكثر، و`B` من 80، و`C` من 70، و`F` لما دون ذلك. ثم اطبع التقديرات للدرجات `[95, 83, 71, 40]` في سطر واحد.

```python exercise
def grade(score):
    pass

scores = [95, 83, 71, 40]
```

```python solution
def grade(score):
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    return "F"

scores = [95, 83, 71, 40]
print(" ".join(grade(s) for s in scores))
```

```text output
A B C F
```

## اختبر نفسك

```quiz
{"question": "ماذا ترجع الدالة التي ليس فيها return؟", "choices": ["0", "\"\"", "None", "خطأ"], "answer": 2, "explanation": "أي دالة لا تنفذ return ترجع None تلقائيًا."}
```

```quiz
{"question": "إذا عُرّفت def f(a, b=2): return a * b، فما قيمة f(5)؟", "choices": ["5", "7", "10", "خطأ"], "answer": 2, "explanation": "b تأخذ القيمة الافتراضية 2، فالناتج 5 × 2 = 10."}
```

```quiz
{"question": "المتغير الذي يُنشأ داخل دالة...", "choices": ["يراه البرنامج كله", "محلي ويختفي بعد انتهاء الدالة", "يُحفظ في ملف", "يصبح ثابتًا"], "answer": 1, "explanation": "متغيرات الدالة محلية؛ لا توجد خارجها."}
```

## الخلاصة

- `def اسم(معاملات):` لتعريف دالة، و`return` لإرجاع الناتج.
- القيم الافتراضية `tax=14`، والوسائط بالاسم `name="..."`، و`*args` لعدد غير محدد.
- متغيرات الدالة محلية، والـ docstring يوثّق الدالة.
- `lambda` لدالة قصيرة، والاستدعاء الذاتي يحتاج شرط توقف.
