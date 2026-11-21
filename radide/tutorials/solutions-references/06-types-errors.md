# الدرس 6: أنواع البيانات والأخطاء بين اللغات

**في هذا الدرس ستتعلم:**

- أي أنواع البيانات تعبر بين اللغات: الأرقام، والنصوص، والقيم المنطقية، و`null`، والقوائم، والقواميس.
- كيف تتحول القوائم والقواميس من C# إلى Python والعكس (ناتج حقيقي).
- ماذا يحدث عندما ترمي المكتبة **استثناء**، وكيف تلتقطه في برنامجك.
- الوكلاء **المكتوبة الأنواع** في C# وJava.

## القاعدة: كل ما يُكتب بـ JSON

الاستدعاءات تمر كرسائل JSON (الدرس السابق)، لذلك يعبر بين اللغات كل ما يمكن كتابته بـ JSON:

| JSON | Python | C# | VB6 |
|---|---|---|---|
| رقم | `int` / `float` | `int` / `double` | `Long` / `Double` |
| نص | `str` | `string` | `String` |
| `true` / `false` | `True` / `False` | `bool` | `Boolean` |
| `null` | `None` | `null` | `Null` / `Empty` |
| قائمة `[...]` | `list` | `List<...>` | `Collection` / مصفوفة |
| كائن `{...}` | `dict` | `Dictionary<string, object>` | `Dictionary` |

> **ما لا يعبر:** الكائنات المعقدة (نافذة، أو ملف مفتوح، أو اتصال قاعدة بيانات). مرر **البيانات** نفسها (نصوص وأرقام وقوائم)، لا الكائنات.

## مثال حقيقي: قوائم وقواميس وأخطاء

هذه مكتبة C# فيها أربع دوال: واحدة ترجع قائمة، وواحدة ترجع قاموسًا، وواحدة تستقبل قائمة، وواحدة ترمي استثناء:

<!-- test: {"sln": "TextLib/TextLib.cs", "lang": "csharp-bridge", "kind": "library"} -->
```csharp
using System.Collections.Generic;

public static class TextLib
{
    public static List<string> Words(string text) => new List<string>(text.Split(' '));

    public static Dictionary<string, object> Info(string name, int age) =>
        new Dictionary<string, object> { ["name"] = name, ["age"] = age, ["adult"] = age >= 18 };

    public static int Count(List<object> xs) => xs.Count;

    public static double Divide(double a, double b)
    {
        if (b == 0) throw new System.ArgumentException("b must not be zero");
        return a / b;
    }
}
```

وهذا برنامج Python في نفس الحل يستخدمها بعد **Add Reference**:

<!-- test: {"sln": "App/main.py", "lang": "python-tk", "main": true} -->
```python
import TextLib

print(TextLib.Words("one two three"))
print(TextLib.Info("Sara", 20))
print(TextLib.Count([1, "a", None]))

try:
    TextLib.Divide(1, 0)
except Exception as e:
    print(type(e).__name__, e)

print(TextLib.Divide(1, 4))
```

والناتج الحقيقي:

```text
['one', 'two', 'three']
{'name': 'Sara', 'age': 20, 'adult': True}
3
RadCallError TextLib.Divide: ArgumentException: b must not be zero
0.25
```

لاحظ:

- `List<string>` في C# وصلت إلى Python **قائمة** `list`.
- `Dictionary<string, object>` وصل **قاموسًا** `dict`، و`bool` صار `True`.
- القائمة `[1, "a", None]` من Python وصلت إلى C# `List<object>` فيها ثلاثة عناصر (و`None` صار `null`).
- الاستثناء `ArgumentException` في C# وصل إلى Python **استثناء** من النوع `RadCallError`، ورسالته فيها اسم الدالة ونوع الخطأ الأصلي ونصه.

## التقاط الأخطاء

لأن الخطأ يصل استثناء عاديًا، تتعامل معه بطريقة لغتك المعتادة: `try` / `except` في Python، و`try` / `catch` في C#، و`On Error` في VB6. ونصيحة: تحقق من المدخلات **قبل** الاستدعاء إذا كان ذلك سهلًا، وأبقِ `try` للحالات غير المتوقعة.

هذا مثال (دون مكتبة حقيقية) لدالة تحوّل رسالة الخطأ القادمة من الـ Hub إلى رسالة عربية مفهومة للمستخدم:

```python run
def friendly(error_text):
    target, _, rest = error_text.partition(": ")
    kind, _, message = rest.partition(": ")
    messages = {"ArgumentException": "قيمة غير مقبولة",
                "DivideByZeroException": "قسمة على صفر",
                "FileNotFoundException": "الملف غير موجود"}
    return f"{messages.get(kind, 'خطأ غير متوقع')} في {target} ({message})"

print(friendly("TextLib.Divide: ArgumentException: b must not be zero"))
print(friendly("Store.Load: FileNotFoundException: data.json"))
print(friendly("Store.Save: IOException: disk full"))
```

```text output
قيمة غير مقبولة في TextLib.Divide (b must not be zero)
الملف غير موجود في Store.Load (data.json)
خطأ غير متوقع في Store.Save (disk full)
```

## الوكلاء المكتوبة الأنواع

في اللغات **المكتوبة الأنواع** مثل C# وJava، يكتب الوكيل الأنواع أيضًا عندما تكون المكتبة مكتوبة الأنواع: إذا استدعى مشروع C# مكتبة C# أو Java فيها `double Add(double a, double b)`، يكون في الوكيل `double Add(double a, double b)` نفسه، فيكتشف المترجم الأخطاء قبل التشغيل.

أما إذا كانت المكتبة **غير مكتوبة الأنواع** (Python أو Ring ...)، فالوكيل في C# يرجع `dynamic`، وفي Java يرجع `Object`، وتتحقق أنت من النوع.

## أخطاء شائعة

- **تمرير كائن بدل بيانات:** مثل نافذة أو ملف مفتوح. مرر النص أو المسار أو الأرقام.
- **الاعتماد على `int` مقابل `float`:** JSON لا يفرق دائمًا بين `170` و`170.0`. إذا كان الفرق مهمًا، حوّل بنفسك (`int(...)` أو `float(...)`).
- **ابتلاع الأخطاء بصمت:** `except: pass` يخفي المشكلة. اعرض رسالة أو سجّلها.
- **عدد معاملات خاطئ:** يظهر خطأ واضح فيه اسم الدالة. قارن مع تعريفها في المكتبة (أو مع الوكيل بـ **View (generated)**).

## تمرين

### تمرين 1: رسالة لكل نوع خطأ

أضف إلى القاموس `messages` النوع `KeyError` برسالة «مفتاح غير موجود»، ثم اطبع `friendly("Settings.Get: KeyError: theme")`.

```python exercise
def friendly(error_text):
    target, _, rest = error_text.partition(": ")
    kind, _, message = rest.partition(": ")
    messages = {"ArgumentException": "قيمة غير مقبولة"}
    return f"{messages.get(kind, 'خطأ غير متوقع')} في {target} ({message})"

print(friendly("Settings.Get: KeyError: theme"))
```

```python solution
def friendly(error_text):
    target, _, rest = error_text.partition(": ")
    kind, _, message = rest.partition(": ")
    messages = {"ArgumentException": "قيمة غير مقبولة", "KeyError": "مفتاح غير موجود"}
    return f"{messages.get(kind, 'خطأ غير متوقع')} في {target} ({message})"

print(friendly("Settings.Get: KeyError: theme"))
```

```text output
مفتاح غير موجود في Settings.Get (theme)
```

## اختبر نفسك

```quiz
{"question": "إلى ماذا تتحول List<string> من C# عند وصولها إلى Python؟", "choices": ["str", "list", "dict", "لا تصل"], "answer": 1, "explanation": "القوائم تعبر كقوائم JSON فتصبح list."}
```

```quiz
{"question": "مكتبة C# رمت ArgumentException. ماذا يحدث في برنامج Python؟", "choices": ["يتوقف الحل كله", "يُرمى استثناء RadCallError فيه اسم الدالة ونوع الخطأ ونصه", "لا شيء", "تُرجع الدالة None دائمًا"], "answer": 1, "explanation": "الخطأ يصل استثناء تلتقطه بـ try / except."}
```

```quiz
{"question": "أيها لا يمكن تمريره بين اللغات؟", "choices": ["نص", "قائمة أرقام", "قاموس", "نافذة مفتوحة"], "answer": 3, "explanation": "تعبر البيانات فقط (ما يُكتب بـ JSON)، لا الكائنات المعقدة."}
```

## الخلاصة

- يعبر بين اللغات كل ما يُكتب بـ JSON: أرقام، ونصوص، وقيم منطقية، و`null`، وقوائم، وقواميس.
- استثناءات المكتبة تصل إلى برنامجك استثناءات عادية (`RadCallError` في Python).
- مع C# وJava قد تكون الوكلاء مكتوبة الأنواع.
