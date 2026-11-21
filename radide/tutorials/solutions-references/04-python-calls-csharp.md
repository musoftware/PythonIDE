# الدرس 4: مثال كامل: برنامج Python يستدعي مكتبة C#

**في هذا الدرس سنبني** حلًا حقيقيًا خطوة بخطوة:

- مكتبة **C#** اسمها `PriceLib` فيها حسابات الأسعار.
- برنامج **Python** اسمه `App` يستخدمها كأنها مكتوبة بـ Python.
- ثم نربط الحساب بزر في نافذة.

كل الكود في هذا الدرس **جُرّب فعلًا** كحل حقيقي في البيئة، والناتج المعروض هو ناتجه.

## ما الذي تحتاجه؟

- **.NET SDK** مثبت (الأمر `dotnet` يعمل في الطرفية)، لأن مكتبة C# تُبنى وتعمل به.
- Python (موجود مع البيئة).

## الخطوة 1: الحل والمشروعان

كما في الدرس 2:

**أ.** **File > New Project...** > **Python (Tkinter)** > **Windows Application**، الاسم `App`، والحل `Shop` (**Create new solution**).

**ب.** **File > Add > New Project...** > **C# (GUI Bridge, .NET)** > **Class Library**، الاسم `PriceLib`، و**Add to solution 'Shop'**.

## الخطوة 2: كود المكتبة

افتح `PriceLib.cs` واستبدل محتواه بهذا:

<!-- test: {"sln": "PriceLib/PriceLib.cs", "lang": "csharp-bridge", "kind": "library"} -->
```csharp
public static class PriceLib
{
    /// <summary>Price after a discount percent.</summary>
    public static double Discount(double price, double percent) => price - price * percent / 100;

    /// <summary>A price label like "Book: 170 EGP".</summary>
    public static string Label(string name, double price) => $"{name}: {price} EGP";
}
```

دالتان **عامتان ساكنتان** (`public static`): `Discount` تحسب السعر بعد الخصم، و`Label` تكتب ملصق السعر. احفظ الملف (`Ctrl+S`).

## الخطوة 3: إضافة المرجع

بالزر الأيمن على `App` > **Add > Reference...** > تبويب **Projects** > ضع علامة على `PriceLib` > **OK**.

يظهر في مجلد `App` الملف `PriceLib.py` (الوكيل)، فيه دالتان بنفس الاسمين: `Discount(price, percent)` و`Label(name, price)`.

## الخطوة 4: الاستدعاء من Python

أضف إلى `App` وحدة جديدة (**Project > Add Module...**) اسمها `main.py`، واكتب:

<!-- test: {"sln": "App/main.py", "lang": "python-tk", "main": true} -->
```python
import PriceLib

price = PriceLib.Discount(200, 15)
print(price)
print(PriceLib.Label("Book", price))

for p in (100, 250, 999):
    print(p, "->", PriceLib.Discount(p, 10))
```

عند التشغيل، هذا هو الناتج في نافذة **Output**:

```text
170
Book: 170 EGP
100 -> 90
250 -> 225
999 -> 899.1
```

ماذا حدث؟ `import PriceLib` استورد **ملف الوكيل** وليس كود C#. وكل استدعاء مثل `PriceLib.Discount(200, 15)` أُرسل إلى **RAD Hub**، الذي شغّل مكتبة C# في عملية منفصلة بـ .NET، ونفّذ الدالة، وأرجع النتيجة `170`. وفي **Output** ستلاحظ أيضًا سطرًا مثل `[RAD Hub] starting C# (GUI Bridge, .NET) worker for PriceLib.cs` عند أول استدعاء.

> **ملاحظة:** C# أرجع `170` كرقم عشري (`double`)، وطُبع في Python `170` لأن القيمة وصلت عبر JSON كرقم صحيح الشكل. سنفهم أنواع البيانات بين اللغات في الدرس 6.

## الخطوة 5: من نافذة

الآن نربطها بالنافذة. صمّم في `Form1`: خانة `txtPrice`، وخانة `txtPercent`، وزرًا `btnCalc`، وعنوانًا `lblResult`. ثم في `Form1.py`:

```python
from Form1_designer import Form1Designer, EventArgs  # noqa: F401
import PriceLib


class Form1(Form1Designer):
    def btnCalc_Click(self):
        try:
            price = float(self.txtPrice_var.get())
            percent = float(self.txtPercent_var.get())
        except ValueError:
            self.lblResult.config(text="اكتب أرقامًا صحيحة")
            return
        new_price = PriceLib.Discount(price, percent)
        self.lblResult.config(text=PriceLib.Label("السعر بعد الخصم", new_price))


if __name__ == "__main__":
    Form1().show()
```

تأكد أن `App` هو مشروع البدء، واضغط `F5`. اكتب `200` و`15` واضغط الزر: يظهر `السعر بعد الخصم: 170 EGP`.

## والاتجاه المعاكس؟

يعمل أيضًا: مشروع C# أو VB6 أو Java أو C++ ... يستخدم مكتبة **Python**. أضف المرجع بنفس الطريقة، فتكتب البيئة وكيلًا بلغة ذلك المشروع (مثل `PyLib.ref.cs` في C#). وفي مجلد البيئة أمثلة جاهزة جربناها:

| المجلد | ماذا فيه |
|---|---|
| `samples\Tests\Solutions\PyApp_CallsAllLanguages` | برنامج Python يستدعي مكتبات بـ 19 لغة |
| `samples\Tests\Solutions\AllLanguages_CallPyLib` | برامج بـ 15 لغة تستدعي مكتبة Python واحدة |
| `samples\Tests\Solutions\CSharp_Java_PowerShell` | C# وJava وPowerShell وPython يستخدم بعضها بعضًا |

افتح ملف `.radsln` في أي منها، واختر مشروع البدء، واضغط `F5`.

## أخطاء شائعة

- **dotnet غير مثبت:** تظهر رسالة خطأ عند أول استدعاء للمكتبة. ثبّت .NET SDK.
- **الدالة ليست public static:** لا تظهر في الوكيل، ويظهر في Python خطأ `AttributeError`.
- **نسيان الحفظ بعد تعديل المكتبة:** الوكيل لا يعرف الدالة الجديدة. احفظ، أو **Build > Refresh References**.
- **تشغيل `main.py` من خارج البيئة مباشرة:** الاستدعاءات تحتاج RAD Hub الذي تشغّله البيئة مع `F5`. من الطرفية يمكن تشغيله هكذا: `python -m radide.runtimes.radhub <مجلد المشروع> -- python main.py`.

## تمرين

### تمرين 1: دالة الضريبة

أضف إلى `PriceLib` دالة `WithTax(double price)` ترجع السعر بعد إضافة ضريبة 14%، ثم استدعها من Python للسعر `100`. هذا التمرين عملي في البيئة؛ وللتأكد من الحساب نفسه، هذه نفس المعادلة بـ Python:

```python exercise
def with_tax(price):
    pass  # السعر + 14%

print(with_tax(100))
print(with_tax(50))
```

```python solution
def with_tax(price):
    return round(price * 1.14, 2)

print(with_tax(100))
print(with_tax(50))
```

```text output
114.0
57.0
```

وفي C# تكون الدالة:

```csharp
public static double WithTax(double price) => System.Math.Round(price * 1.14, 2);
```

## اختبر نفسك

```quiz
{"question": "ماذا يستورد السطر import PriceLib في App؟", "choices": ["كود C# نفسه", "ملف الوكيل PriceLib.py الذي كتبته البيئة", "مكتبة من الإنترنت", "لا شيء"], "answer": 1, "explanation": "الوكيل يمرر كل استدعاء إلى المكتبة عبر RAD Hub."}
```

```quiz
{"question": "ماذا تحتاج لتعمل مكتبة C# في الحل؟", "choices": [".NET SDK (dotnet)", "Visual Studio كاملًا", "اتصالًا بالإنترنت", "لا شيء"], "answer": 0, "explanation": "المكتبة تُبنى وتعمل بـ dotnet."}
```

```quiz
{"question": "أين يظهر ناتج print في البرنامج؟", "choices": ["في Solution Explorer", "في نافذة Output", "في ملف الوكيل", "لا يظهر"], "answer": 1, "explanation": "مخرجات البرنامج تظهر في Output."}
```

## الخلاصة

- مكتبة C# بدوال `public static` + مرجع من مشروع Python = استدعاء طبيعي مثل `PriceLib.Discount(200, 15)`.
- الوكيل يمرر الاستدعاء، وRAD Hub يشغّل المكتبة بلغتها ويرجع النتيجة.
- الاتجاه المعاكس يعمل بنفس الطريقة، والأمثلة في `samples\Tests\Solutions`.
