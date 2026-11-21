# الدرس 8: مشروع عملي: برنامج بنافذة نصنعه مع الذكاء الاصطناعي

**في هذا المشروع سنصنع:** محوّل درجات الحرارة من سلسيوس إلى فهرنهايت، بنافذة فيها خانة وزر ونتيجة. سنستخدم الأدوات التي تعلمناها:

- **Generate Form with AI...** لتصميم النافذة بالكلام.
- **Generate Event Handler** لكتابة الكود الذي يعمل عند الضغط على الزر.
- **AI Chat** و`Ctrl+I` للمراجعة والتحسين.
- وفي كل خطوة: **نراجع ونشغّل بأنفسنا**.

## الخطوة 1: مشروع جديد

**File > New Project...** (ملف > مشروع جديد...)، واختر اللغة **Python (Tkinter)**، وسمّ المشروع `TempConverter`. ستفتح البيئة النموذج `Form1` في المصمم.

## الخطوة 2: صمّم النافذة بالكلام

افتح **Project > Generate Form with AI...** (مشروع > إنشاء نموذج بالذكاء الاصطناعي...). في مربع الوصف اكتب، بالعربية أو الإنجليزية:

```text
نافذة عنوانها "محوّل الحرارة" فيها:
عنوان lblTitle نصه "درجة الحرارة بالسلسيوس:"
خانة نص txtCelsius
زر btnConvert نصه "حوّل"
عنوان lblResult للنتيجة
```

اترك **Name** على `Form1` أو اختر اسمًا جديدًا، وتأكد أن **Language** هي **Python (Tkinter)**، ثم اضغط **Generate**. تظهر قائمة الأدوات المقترحة، وبعد الموافقة يُنشأ النموذج في المصمم.

> **نصيحة:** اكتب **أسماء الأدوات** بنفسك في الوصف (`txtCelsius`، `btnConvert` ...). هكذا يكون الكود الذي يأتي بعد ذلك واضحًا ومتوقعًا. البادئات المعتادة: `txt` لخانة النص، و`btn` للزر، و`lbl` للعنوان.

وإذا لم يعجبك التصميم: انقر بالزر الأيمن على النموذج > **AI > Redesign This Form with AI...** (إعادة تصميم هذا النموذج بالذكاء الاصطناعي...) واطلب التعديل، مثل «كبّر الخط واجعل الزر في المنتصف». ويمكنك التراجع بـ `Ctrl+Z`.

## الخطوة 3: كود الزر

انقر بالزر الأيمن على الزر `btnConvert` في المصمم واختر **AI > Generate Event Handler for btnConvert...**، واكتب:

```text
اقرأ الرقم من txtCelsius، وحوّله إلى فهرنهايت (F = C * 9 / 5 + 32)،
واكتب النتيجة في lblResult بالشكل "100 °C = 212 °F".
إذا لم يكن المدخل رقمًا اكتب "اكتب رقمًا صحيحًا".
```

هذا الكود الذي حصلنا عليه **بعد مراجعته**. اضغط «جرّبه» لتشغيله:

<!-- test: {"form": {"Text": "محوّل الحرارة", "Width": 320, "Height": 200}, "controls": [["Label", "lblTitle", {"Text": "درجة الحرارة بالسلسيوس:"}], ["TextBox", "txtCelsius"], ["Button", "btnConvert", {"Text": "حوّل"}], ["Label", "lblResult"]], "set": {"txtCelsius": "100"}, "click": ["btnConvert"], "expect": {"lblResult": "100 °C = 212 °F"}} -->
```python form run
from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """محوّل درجات الحرارة."""

    def btnConvert_Click(self):
        text = self.txtCelsius_var.get().strip()
        try:
            c = float(text)
        except ValueError:
            self.lblResult.config(text="اكتب رقمًا صحيحًا")
            return
        f = c * 9 / 5 + 32
        self.lblResult.config(text=f"{c:g} °C = {f:g} °F")


if __name__ == "__main__":
    Form1().show()
```

**ماذا راجعنا قبل القبول؟**

- أن النموذج استخدم أسماء أدواتنا الصحيحة (`txtCelsius_var` هو متغير النص المرتبط بالخانة في Tkinter).
- أن المعادلة صحيحة: `c * 9 / 5 + 32`.
- أن المدخل غير الرقمي لا يوقف البرنامج (`try` / `except ValueError`).
- أن `:g` يطبع `100` بدل `100.0`.

## الخطوة 4: شغّل وجرّب الحالات الصعبة

اضغط `F5` وجرّب: `100` ثم `0` ثم `-40` ثم كلمة مثل `abc` ثم خانة فارغة. يجب ألا يتوقف البرنامج في أي حالة.

| المدخل | الناتج المتوقع |
|---|---|
| `100` | `100 °C = 212 °F` |
| `0` | `0 °C = 32 °F` |
| `-40` | `-40 °C = -40 °F` |
| `abc` | `اكتب رقمًا صحيحًا` |

## الخطوة 5: اطلب مراجعة من الذكاء الاصطناعي

افتح `Ctrl+Alt+I` واكتب:

```text
أنت مراجع كود. راجع @current وابحث عن حالات قد تسبب أخطاء، واقترح تحسينًا واحدًا فقط.
```

قد يقترح مثلًا قبول الفاصلة العشرية العربية `٫` أو الفاصلة `,`. إذا أعجبك الاقتراح، حدد الدالة واضغط `Ctrl+I` واطلب التعديل، ثم راجع الفرق وشغّل من جديد.

## الخطوة 6: إيداع في Git

افتح **Git Changes** (`Ctrl+Alt+G`) واضغط **Generate Message with AI** لتحصل على رسالة إيداع مقترحة، وعدّلها إن لزم، ثم أودع.

## تمرين: زر المسح

أضف زرًا اسمه `btnClear` نصه «مسح»، يفرّغ خانة `txtCelsius` ويفرّغ `lblResult`. جرّب أن تطلبه بـ `Ctrl+I` أولًا، ثم قارن بالحل.

<!-- test: {"controls": [["TextBox", "txtCelsius"], ["Button", "btnConvert", {"Text": "حوّل"}], ["Button", "btnClear", {"Text": "مسح"}], ["Label", "lblResult"]], "steps": [["set", "txtCelsius", "25"], ["click", "btnConvert"], ["click", "btnClear"]], "expect": {"txtCelsius": "", "lblResult": ""}} -->
```python form exercise
from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    def btnConvert_Click(self):
        text = self.txtCelsius_var.get().strip()
        try:
            c = float(text)
        except ValueError:
            self.lblResult.config(text="اكتب رقمًا صحيحًا")
            return
        self.lblResult.config(text=f"{c:g} °C = {c * 9 / 5 + 32:g} °F")

    # أضف هنا الدالة btnClear_Click


if __name__ == "__main__":
    Form1().show()
```

<!-- test: {"controls": [["TextBox", "txtCelsius"], ["Button", "btnConvert", {"Text": "حوّل"}], ["Button", "btnClear", {"Text": "مسح"}], ["Label", "lblResult"]], "steps": [["set", "txtCelsius", "25"], ["click", "btnConvert"], ["click", "btnClear"]], "expect": {"txtCelsius": "", "lblResult": ""}} -->
```python form solution
from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    def btnConvert_Click(self):
        text = self.txtCelsius_var.get().strip()
        try:
            c = float(text)
        except ValueError:
            self.lblResult.config(text="اكتب رقمًا صحيحًا")
            return
        self.lblResult.config(text=f"{c:g} °C = {c * 9 / 5 + 32:g} °F")

    def btnClear_Click(self):
        self.txtCelsius_var.set("")
        self.lblResult.config(text="")


if __name__ == "__main__":
    Form1().show()
```

## تمرين: المنطق وحده أولًا

من العادات الجيدة أن تفصل **الحساب** عن **النافذة**، فيسهل اختباره (ويسهل على الذكاء الاصطناعي أيضًا أن يكتب له اختبارات). اكتب دالة `to_fahrenheit(c)` واطبع نتيجتها لـ `100` و`0` و`-40`.

```python exercise
def to_fahrenheit(c):
    pass  # أكمل

for c in (100, 0, -40):
    print(c, "->", to_fahrenheit(c))
```

```python solution
def to_fahrenheit(c):
    return c * 9 / 5 + 32

for c in (100, 0, -40):
    print(c, "->", to_fahrenheit(c))
```

```text output
100 -> 212.0
0 -> 32.0
-40 -> -40.0
```

## اختبر نفسك

```quiz
{"question": "لماذا نكتب أسماء الأدوات بأنفسنا في وصف Generate Form with AI؟", "choices": ["لأن البيئة لا تقبل وصفًا دونها", "ليكون الكود الذي يأتي بعدها واضحًا ومتوقعًا", "لتصغير حجم الملف", "لا داعي لذلك"], "answer": 1, "explanation": "الأسماء الواضحة مثل txtCelsius تجعل الكود المولد والمراجعة أسهل."}
```

```quiz
{"question": "أين تجد Generate Event Handler لزر معين؟", "choices": ["Help > About", "بالزر الأيمن على الأداة في المصمم > AI", "Build > Publish", "Git > Push"], "answer": 1, "explanation": "قائمة AI بالزر الأيمن في المصمم فيها Generate Event Handler for ..."}
```

```quiz
{"question": "ما أهم خطوة بعد قبول كود من الذكاء الاصطناعي؟", "choices": ["حذف التعليقات", "تشغيل البرنامج وتجربة الحالات الصعبة", "إغلاق البيئة", "إعادة تسمية المشروع"], "answer": 1, "explanation": "التشغيل والتجربة هما الدليل الوحيد على أن الكود صحيح."}
```

## الخلاصة

- صممنا نافذة كاملة بالكلام (**Generate Form with AI...**)، وكتبنا كود الزر بـ **Generate Event Handler**.
- راجعنا الكود سطرًا سطرًا، وجرّبنا الحالات الصعبة، ثم طلبنا مراجعة إضافية في **AI Chat**.
- الذكاء الاصطناعي أسرع في الكتابة، لكن **الفهم والمراجعة والاختبار** مسؤوليتك أنت.

## قاموس مصطلحات الدليل

| المصطلح | بالعربية |
|---|---|
| Provider | مزود |
| Model | نموذج |
| Prompt | طلب (موجّه) |
| Context | سياق |
| Inline completion | إكمال مضمّن |
| Agent | وكيل |
| Checkpoint | نقطة استعادة |
| Diff | فرق (مقارنة) |
| Token | رمز (وحدة نص) |
| Streaming | بث (إرسال قطعة قطعة) |
