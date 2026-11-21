# الدرس 7: تغطية الكود

**في هذا الدرس ستتعلم:**

- ما هي **تغطية الكود** (Code coverage)، ولماذا لا يكفي أن تكون كل الاختبارات خضراء.
- تشغيل الاختبارات مع التغطية من **Test > Run All Tests with Coverage**.
- قراءة تبويب **Coverage** في مستكشف الاختبارات، وألوان الهامش في المحرر: أخضر وأحمر وكهرماني.
- إضافة الاختبار الناقص حتى تصل التغطية إلى 100%.

## المفتش والغرف المغلقة

تخيّل مفتشًا يفحص عمارة، فكتب في تقريره: "كل الغرف التي دخلتها سليمة". تقرير مطمئن... لكن كم غرفة دخل؟ ربما دخل غرفتين من عشر!
الاختبارات الخضراء تشبه هذا التقرير: تقول إن ما فحصته سليم، لكنها لا تقول **ما الذي لم تفحصه**.
**تغطية الكود** هي خريطة العمارة: تلوّن كل سطر نفّذته الاختبارات **بالأخضر**، وكل سطر لم تدخله أبدًا **بالأحمر**. الأسطر الحمراء غرف لم يفتشها أحد، والأخطاء تختبئ فيها عادةً.

## اللغات التي تدعم التغطية

| اللغة | الأداة التي تستخدمها البيئة |
|---|---|
| Python | `coverage.py` مع pytest (يُثبَّت في بيئة المشروع أو تستخدم البيئة نسختها) |
| JavaScript / TypeScript | Jest (`--coverage`) |
| Go | `go test -coverprofile` |
| Flutter | `flutter test --coverage` |

لذلك سنعمل في هذا الدرس بلغة **Python**. الفكرة نفسها في كل اللغات.

## المثال: متجر صغير

مشروع Python فيه ملفان: `shop.py` فيه دالتان (الخصم ومصاريف الشحن)، و `test_shop.py` فيه اختباران بأسلوب pytest: دالة اسمها يبدأ بـ `test_` وفيها `assert`.

<!-- test: {"pytest": {"test_discount_big": "passed", "test_shipping_free": "passed"}, "coverage": {"shop.py": 60}, "missed": {"shop.py": [4, 10, 11, 12]}} -->
```python
# #file: shop.py
def price_after_discount(amount):
    if amount >= 1000:
        return amount - amount // 10
    return amount


def shipping(amount):
    if amount >= 500:
        return 0
    if amount >= 200:
        return 20
    return 50
# #file: test_shop.py
from shop import price_after_discount, shipping


def test_discount_big():
    assert price_after_discount(2000) == 1800


def test_shipping_free():
    assert shipping(800) == 0
```

اضغط «افتح في المحرر»، ثم:

1. افتح **Test > Test Explorer** (اختبار > مستكشف الاختبارات) أو `Ctrl+E` ثم `T`.
2. اختر **Test > Run All Tests with Coverage** (تشغيل كل الاختبارات مع التغطية)، أو زر **Coverage** في شريط النافذة.
3. الاختباران **أخضران**. ممتاز؟ انتظر...
4. افتح تبويب **Coverage** (التغطية) في أسفل النافذة:

```text
File            Covered   Lines   Missed   %
shop.py         6         10      4        60
test_shop.py    5         5       0        100
```

أعمدة الجدول: **File** الملف، و **Covered** عدد الأسطر التي نُفّذت، و **Lines** عدد الأسطر القابلة للتنفيذ، و **Missed** الأسطر التي لم تُنفّذ، و **%** النسبة. **انقر الملف مرتين** لتفتحه.

## ألوان الهامش في المحرر

افتح `shop.py` بعد التشغيل مع التغطية. في الهامش بجوار أرقام الأسطر:

| اللون | المعنى | في مثالنا |
|---|---|---|
| أخضر | السطر نُفّذ أثناء الاختبارات | الأسطر 1 و 2 و 3 و 7 و 8 و 9 |
| أحمر | السطر **لم يُنفّذ أبدًا** | السطر 4 (`return amount`) والأسطر 10 و 11 و 12 |
| كهرماني (برتقالي) | فرع جزئي: الشرط جُرّب في اتجاه واحد فقط | السطر 2 (`if amount >= 1000`) جُرّب "صحيح" فقط، والسطر 8 كذلك |

إذن الاختبارات لم تجرّب أبدًا: مبلغًا **أقل** من 1000 في الخصم، ولا شحنًا لمبلغ **أقل** من 500. لو كان في هذه الأسطر خطأ، فلن يكشفه أحد.

- لإخفاء الألوان أو إظهارها: **Test > Show Code Coverage Colouring** (عرض تلوين تغطية الكود)، أو زر **Show colours in the editor** في تبويب Coverage.
- لمسح النتائج: **Test > Clear Coverage Results** (مسح نتائج التغطية).

## سد الثغرات

نضيف اختبارًا لكل سطر أحمر. لاحظ أن كل اختبار جديد يفحص **حالة** لم نفحصها:

<!-- test: {"pytest": {"test_discount_big": "passed", "test_no_discount": "passed", "test_shipping_free": "passed", "test_shipping_medium": "passed", "test_shipping_small": "passed"}, "coverage": {"shop.py": 100}, "missed": {"shop.py": []}} -->
```python
# #file: shop.py
def price_after_discount(amount):
    if amount >= 1000:
        return amount - amount // 10
    return amount


def shipping(amount):
    if amount >= 500:
        return 0
    if amount >= 200:
        return 20
    return 50
# #file: test_shop.py
from shop import price_after_discount, shipping


def test_discount_big():
    assert price_after_discount(2000) == 1800


def test_no_discount():
    assert price_after_discount(999) == 999


def test_shipping_free():
    assert shipping(800) == 0


def test_shipping_medium():
    assert shipping(300) == 20


def test_shipping_small():
    assert shipping(100) == 50
```

شغّل **Run All Tests with Coverage** مرة أخرى: كل أسطر `shop.py` خضراء، والنسبة **100%**.

وهذه الدوال نفسها في برنامج عادي، لترى قيمها بعينك:

```python run
# #file: main.py
from shop import price_after_discount, shipping

for amount in (100, 300, 999, 2000):
    print(amount, "->", price_after_discount(amount), "+ شحن", shipping(amount))
# #file: shop.py
def price_after_discount(amount):
    if amount >= 1000:
        return amount - amount // 10
    return amount


def shipping(amount):
    if amount >= 500:
        return 0
    if amount >= 200:
        return 20
    return 50
```

```text output
100 -> 100 + شحن 50
300 -> 300 + شحن 20
999 -> 999 + شحن 0
2000 -> 1800 + شحن 0
```

## هل 100% تعني أن البرنامج بلا أخطاء؟

**لا.** التغطية تقول إن السطر **نُفّذ**، لا إن نتيجته **صحيحة**. اختبار يستدعي الدالة بلا `assert` يرفع التغطية ولا يفحص شيئًا!
استخدم التغطية **مصباحًا** يكشف الغرف المظلمة، لا **شهادة** بأن العمارة سليمة. هدف معقول: 80% فأكثر للكود المهم، مع اختبارات لها `assert` حقيقية.

## أخطاء شائعة

- **زر التغطية لا يظهر أو لا يعمل:** الإطار لا يدعم التغطية في البيئة (مثل اختبارات BASIC حاليًا). استخدم Python أو Jest أو Go أو Flutter.
- **`coverage` غير مثبت في بيئة المشروع:** البيئة تستخدم نسختها الخاصة تلقائيًا، أو ثبّته: `pip install coverage pytest` في **View > Terminal**.
- **ملفات الاختبار نفسها في التقرير:** طبيعي؛ ركّز على ملفات الكود (`shop.py`).
- **السعي إلى 100% بأي ثمن:** اختبار بلا `assert` لمجرد تلوين السطر بالأخضر يخدعك أنت.

## تمرين

### تمرين 1: من الأحمر إلى الأخضر

الدالة `grade` تحوّل الدرجة إلى تقدير. التقرير أظهر أن الاختبارات تمر على `"ممتاز"` فقط. اكتب برنامجًا يطبع تقدير الدرجات `95` و `75` و `40` حتى تمر على كل الفروع (هذا ما سيفعله اختبارك أيضًا).

```python exercise
def grade(score):
    if score >= 85:
        return "ممتاز"
    if score >= 65:
        return "جيد"
    return "راسب"


print(grade(95))
```

```python solution
def grade(score):
    if score >= 85:
        return "ممتاز"
    if score >= 65:
        return "جيد"
    return "راسب"


for s in (95, 75, 40):
    print(s, grade(s))
```

```text output
95 ممتاز
75 جيد
40 راسب
```

### مهمة عملية

1. أنشئ مجلدًا فيه `shop.py` و `test_shop.py` من المثال الأول، وافتحه بـ **File > Open Folder...**.
2. `Ctrl+E, T` ثم **Coverage**: اقرأ النسبة 60% وابحث عن الأسطر الحمراء.
3. أضف الاختبارات الثلاثة الناقصة، وأعد التشغيل حتى 100%.
4. جرّب **Test > Clear Coverage Results** ولاحظ اختفاء الألوان.

## اختبر نفسك

```quiz
{"question": "ماذا يعني السطر الأحمر بعد التشغيل مع التغطية؟", "choices": ["السطر فيه خطأ", "الاختبارات لم تنفّذ هذا السطر أبدًا", "السطر بطيء", "السطر محذوف"], "answer": 1, "explanation": "الأحمر = لم يُنفّذ أثناء الاختبارات، أي لم يفحصه أي اختبار."}
```

```quiz
{"question": "التغطية 100% وكل الاختبارات خضراء. هل البرنامج بلا أخطاء بالتأكيد؟", "choices": ["نعم دائمًا", "لا، التغطية تقول إن الأسطر نُفّذت لا إن نتائجها صحيحة", "نعم إذا كان المشروع صغيرًا", "لا يمكن الوصول إلى 100%"], "answer": 1, "explanation": "اختبار بلا assert يرفع التغطية دون أن يفحص النتيجة."}
```

```quiz
{"question": "ماذا يعني اللون الكهرماني على سطر `if`؟", "choices": ["الشرط جُرّب في اتجاه واحد فقط (صحيح أو خطأ)", "السطر لم يُنفّذ", "خطأ في الصياغة", "نقطة توقف"], "answer": 0, "explanation": "فرع جزئي: يلزمك اختبار يجعل الشرط في الاتجاه الآخر."}
```

## الخلاصة

- **Test > Run All Tests with Coverage** يشغّل الاختبارات ويقيس الأسطر التي نُفّذت.
- تبويب **Coverage**: الملف والأسطر المغطاة والناقصة والنسبة؛ والهامش: أخضر نُفّذ، أحمر لم يُنفّذ، كهرماني فرع جزئي.
- كل سطر أحمر يحتاج اختبارًا يمر عليه؛ والتغطية مصباح لا شهادة.
