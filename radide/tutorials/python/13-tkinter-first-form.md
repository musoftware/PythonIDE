# الدرس 13: أول نافذة بـ Tkinter في مصمم النماذج

حتى الآن كانت برامجنا تعمل في نافذة **Output** فقط. اليوم نبني برنامجًا حقيقيًا **بنافذة وأزرار ومربعات نص**، بنفس أسلوب Visual Basic الشهير: ترسم النافذة بالسحب والإفلات، ثم تكتب كود Python الذي يعمل عند الضغط على الأزرار.

## Tkinter: مكتبة النوافذ المدمجة في Python

**Tkinter** مكتبة النوافذ الرسومية التي تأتي مع Python نفسها، فلا تحتاج إلى تثبيت أي شيء. وهي بسيطة وخفيفة ومناسبة جدًا للبدء.

## البرمجة بالأحداث (Event-Driven Programming)

في برامج الكونسول، **البرنامج** هو الذي يقود: يسأل ثم ينتظر الإجابة ثم يكمل بالترتيب. أما في البرامج الرسومية فـ **المستخدم** هو الذي يقود: قد يضغط أي زر في أي وقت. لذلك نكتب الكود على شكل **معالجات أحداث** (event handlers): دالة لكل **حدث** تقول «عندما يحدث كذا، افعل كذا».

> **تشبيه:** برنامج الكونسول مثل **موظف يملأ استمارة معك** سؤالًا بعد سؤال. البرنامج الرسومي مثل **النادل في المطعم**: لا يفعل شيئًا حتى تناديه، فإذا طلبت عصيرًا أحضر العصير، وإذا طلبت الحساب أحضر الحساب.

## مشروعك الأول خطوة بخطوة: برنامج الترحيب

### 1) إنشاء المشروع

1. **File ← New Project** (ملف ← مشروع جديد...).
2. اختر **Python ← Python (Tkinter)**، والقالب **Windows Application** (تطبيق Windows).
3. سمّ المشروع `HelloForm` واضغط **OK**.

تفتح الـ IDE النموذج **Form1** في **المصمم** (Designer)، وفي **مستكشف الحلول** (Solution Explorer) ترى ثلاثة ملفات للنموذج:

| الملف | ما فيه |
|---|---|
| `Form1.form` | تصميم النافذة: الأدوات ومواضعها وخصائصها (تعدّله بالمصمم) |
| `Form1_designer.py` | كود Tkinter الذي **تولّده الـ IDE** من التصميم: لا تعدّله بيدك، فهو يُعاد توليده عند كل حفظ |
| `Form1.py` | **كودك أنت**: معالجات الأحداث |

### 2) رسم النافذة

من **صندوق الأدوات** (Toolbox) اسحب إلى النموذج الأدوات التالية، ثم غيّر خصائصها من نافذة **الخصائص** (Properties). وانقر على مكان فارغ في النموذج لتغيّر خاصية `Text` للنموذج نفسه إلى `برنامج الترحيب`:

| الأداة | Name | Text |
|---|---|---|
| `Label` | `lblPrompt` | `اكتب اسمك:` |
| `TextBox` | `txtName` | (فارغ) |
| `Button` | `btnHello` | `رحّب بي` |
| `Label` | `lblResult` | (فارغ) |

> **نصيحة:** اعتد على **البادئات** في أسماء الأدوات: `txt` لمربع النص، و`btn` للزر، و`lbl` للعنوان، و`lst` للقائمة، و`chk` لمربع الاختيار. ستعرف نوع الأداة من اسمها فورًا في الكود.

### 3) كتابة الكود

**انقر مرتين** على الزر في المصمم، فتنشئ الـ IDE دالة الحدث `btnHello_Click` في `Form1.py` وتنقلك إليها. أكمل الكود ليصبح هكذا:

<!-- test: {"form": {"Text": "برنامج الترحيب", "Width": 360, "Height": 200}, "controls": [["Label", "lblPrompt", {"Text": "اكتب اسمك:", "Left": 20, "Top": 20, "Width": 100}], ["TextBox", "txtName", {"Text": "", "Left": 120, "Top": 18, "Width": 200}], ["Button", "btnHello", {"Text": "رحّب بي", "Left": 120, "Top": 52, "Width": 100, "Height": 28}], ["Label", "lblResult", {"Text": "", "Left": 20, "Top": 100, "Width": 300}]], "set": {"txtName": "ريم"}, "click": ["btnHello"], "expect": {"lblResult": "أهلًا يا ريم!"}} -->
```python form run
from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Write your event handlers here."""

    def Form1_Load(self):
        self.lblResult.config(text="اكتب اسمك ثم اضغط الزر")

    def btnHello_Click(self):
        name = self.txtName.get().strip()
        if name:
            self.lblResult.config(text=f"أهلًا يا {name}!")
        else:
            self.lblResult.config(text="من فضلك اكتب اسمك أولًا")


if __name__ == "__main__":
    Form1().show()
```

### 4) التشغيل

اضغط **F5** (أو **Ctrl+F5**). تظهر نافذتك؛ اكتب اسمك (مثلًا «ريم») واضغط الزر، فيظهر: **أهلًا يا ريم!**

## كيف يعمل هذا الكود؟

- `class Form1(Form1Designer):` صنف نافذتك **يرث** من الصنف الذي ولّدته الـ IDE. هذا تطبيق مباشر لدرس الوراثة! الصنف الأب ينشئ الأدوات، وأنت تضيف السلوك.
- كل أداة صارت **خاصية** في الكائن: `self.txtName` و`self.lblResult`... باسمها الذي كتبته في خاصية `Name`.
- اسم الدالة يجب أن يكون بالضبط **`اسمالأداة_اسمالحدث`** مثل `btnHello_Click`، وبهذا تربطها الـ IDE بالحدث.
- `Form1_Load` حدث خاص بالنموذج يعمل مرة واحدة عند ظهوره، ومكانه المناسب لضبط القيم الابتدائية.
- `Form1().show()` تنشئ النافذة وتبدأ **حلقة الأحداث** التي تنتظر ضغطات المستخدم حتى يغلق النافذة.

## قراءة الأدوات وتغييرها في Tkinter

الأدوات في Tkinter لها دوال خاصة بها:

| الأداة في المصمم | الأداة في Tkinter | القراءة | التغيير |
|---|---|---|---|
| `TextBox` | `tk.Entry` | `self.txtName.get()` | `self.txtName_var.set("نص")` |
| `Label` | `tk.Label` | `self.lblX.cget("text")` | `self.lblX.config(text="نص")` |
| `Button` | `tk.Button` | `self.btnX.cget("text")` | `self.btnX.config(text="نص")` |
| `CheckBox` | `tk.Checkbutton` | `self.chkX_var.get()` | `self.chkX_var.set(True)` |

> **لاحظ:** لكل `TextBox` متغير مرتبط اسمه `اسمالأداة_var` (مثل `self.txtName_var`) تولّده الـ IDE. القراءة منه أو من الأداة نفسها سواء، والكتابة فيه تغيّر النص الظاهر فورًا.

وأي شيء تطبعه بـ `print` يظهر في نافذة **Output**، وهذا مفيد جدًا لتتبع ما يحدث أثناء التطوير.

## مثال ثانٍ: آلة حاسبة

ارسم النموذج التالي:

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtA` | `0` |
| `TextBox` | `txtB` | `0` |
| `Button` | `btnAdd` | `+` |
| `Button` | `btnSub` | `-` |
| `Button` | `btnMul` | `×` |
| `Button` | `btnDiv` | `÷` |
| `Label` | `lblResult` | (فارغ) |

ثم اكتب الكود. لاحظ كيف نستخدم دالة مساعدة عادية `calculate` لكي لا نكرر الكود في الأزرار الأربعة، ونستخدم `try` لنتعامل مع الإدخال الخاطئ كما تعلمنا:

<!-- test: {"form": {"Text": "آلة حاسبة", "Width": 330, "Height": 190}, "controls": [["TextBox", "txtA", {"Text": "0", "Left": 20, "Top": 20, "Width": 130}], ["TextBox", "txtB", {"Text": "0", "Left": 170, "Top": 20, "Width": 130}], ["Button", "btnAdd", {"Text": "+", "Left": 20, "Top": 56, "Width": 60, "Height": 28}], ["Button", "btnSub", {"Text": "-", "Left": 90, "Top": 56, "Width": 60, "Height": 28}], ["Button", "btnMul", {"Text": "×", "Left": 160, "Top": 56, "Width": 60, "Height": 28}], ["Button", "btnDiv", {"Text": "÷", "Left": 230, "Top": 56, "Width": 60, "Height": 28}], ["Label", "lblResult", {"Text": "", "Left": 20, "Top": 104, "Width": 280}]], "steps": [["set", "txtA", "12"], ["set", "txtB", "4"], ["click", "btnMul"]], "expect": {"lblResult": "الناتج = 48"}} -->
```python form run
from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def calculate(self, op):
        """دالة مساعدة (ليست حدثًا): تقرأ العددين وتحسب وتعرض الناتج."""
        try:
            a = float(self.txtA.get())
            b = float(self.txtB.get())
        except ValueError:
            self.lblResult.config(text="اكتب أعدادًا صحيحة")
            return
        if op == "+":
            result = a + b
        elif op == "-":
            result = a - b
        elif op == "*":
            result = a * b
        else:
            if b == 0:
                self.lblResult.config(text="لا يمكن القسمة على صفر")
                return
            result = a / b
        self.lblResult.config(text=f"الناتج = {result:g}")
        print("حساب:", a, op, b, "=", result)

    def btnAdd_Click(self):
        self.calculate("+")

    def btnSub_Click(self):
        self.calculate("-")

    def btnMul_Click(self):
        self.calculate("*")

    def btnDiv_Click(self):
        self.calculate("/")


if __name__ == "__main__":
    Form1().show()
```

`{result:g}` تعرض العدد بدون أصفار زائدة: `48.0` تظهر `48`، و`2.5` تبقى `2.5`.

## مربعات الرسائل: `messagebox`

لعرض رسالة منبثقة أو سؤال نعم/لا، استخدم الوحدة `tkinter.messagebox`:

<!-- test: {"form": {"Text": "تأكيد"}, "controls": [["Button", "btnDelete", {"Text": "احذف الملف", "Left": 20, "Top": 20, "Width": 140, "Height": 30}], ["Label", "lblStatus", {"Text": "", "Left": 20, "Top": 70, "Width": 300}]], "click": ["btnDelete"], "msgbox": ["هل تريد حذف الملف فعلًا؟", "تم الحذف (تجريبيًا)"], "expect": {"lblStatus": "تم الحذف"}} -->
```python form run
from tkinter import messagebox

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def btnDelete_Click(self):
        if messagebox.askyesno("تأكيد", "هل تريد حذف الملف فعلًا؟"):
            messagebox.showinfo("تم", "تم الحذف (تجريبيًا)")
            self.lblStatus.config(text="تم الحذف")
        else:
            self.lblStatus.config(text="أُلغيت العملية")


if __name__ == "__main__":
    Form1().show()
```

| الدالة | ماذا تعرض | ماذا ترجع |
|---|---|---|
| `messagebox.showinfo(عنوان, رسالة)` | رسالة معلومات | `"ok"` |
| `messagebox.showwarning(...)` | تحذير | `"ok"` |
| `messagebox.showerror(...)` | خطأ | `"ok"` |
| `messagebox.askyesno(...)` | سؤال نعم/لا | `True` أو `False` |

## خصائص مفيدة في المصمم

- **Text** للنموذج: عنوان النافذة.
- **FontName** و**FontSize** و**FontBold**: الخط، و**ForeColor** و**BackColor**: الألوان.
- **TextAlign** لمربع النص: اجعلها `Right` إذا كان المستخدم سيكتب بالعربية.
- **Enabled**: تعطيل الأداة. **Visible**: إخفاؤها.
- **ToolTip**: تلميح يظهر عند الوقوف بالفأرة على الأداة.

ويمكنك تغيير أغلبها من الكود أيضًا، مثل `self.btnHello.config(state="disabled")` لتعطيل الزر.

## أخطاء شائعة

- **تعديل `Form1_designer.py` بيدك:** ستضيع تعديلاتك عند الحفظ التالي. اكتب كودك في `Form1.py` فقط.
- **اسم دالة لا يطابق اسم الأداة:** إذا غيّرت `Name` للزر إلى `btnGreet` فلن تُستدعى `btnHello_Click`. انقر الزر مرتين من جديد لتنشئ الدالة الصحيحة.
- **نسيان `self.`**: داخل الدوال تصل للأدوات بـ `self.txtName` وليس `txtName`.
- **كتابة `self.lblResult.text = "..."`**: هذا لا يغير شيئًا في Tkinter؛ استخدم `config(text=...)`.

## تمارين

### التمرين 1

صمّم نموذجًا فيه `TextBox` اسمه `txtCelsius`، وزر `btnConvert`، و`Label` اسمه `lblResult`. عند الضغط اعرض الحرارة بالفهرنهايت بالشكل `98.6 °F` (القانون: `C × 9 / 5 + 32`).

<!-- test: {"controls": [["TextBox", "txtCelsius", {"Text": ""}], ["Button", "btnConvert", {"Text": "حوّل"}], ["Label", "lblResult", {}]], "set": {"txtCelsius": "37"}, "click": ["btnConvert"], "expect": {"lblResult": "98.6 °F"}} -->
```python form exercise
from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def btnConvert_Click(self):
        pass


if __name__ == "__main__":
    Form1().show()
```

<!-- test: {"controls": [["TextBox", "txtCelsius", {"Text": ""}], ["Button", "btnConvert", {"Text": "حوّل"}], ["Label", "lblResult", {}]], "set": {"txtCelsius": "37"}, "click": ["btnConvert"], "expect": {"lblResult": "98.6 °F"}} -->
```python form solution
from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def btnConvert_Click(self):
        c = float(self.txtCelsius.get())
        f = c * 9 / 5 + 32
        self.lblResult.config(text=f"{f:.1f} °F")


if __name__ == "__main__":
    Form1().show()
```

### التمرين 2

نموذج عدّاد: `Label` اسمه `lblCount` يبدأ بـ `0`، وزر `btnPlus` يزيده واحدًا، وزر `btnReset` يعيده صفرًا. (احفظ العدد في `self.count` واضبطه في `Form1_Load`.)

<!-- test: {"controls": [["Label", "lblCount", {}], ["Button", "btnPlus", {"Text": "+1"}], ["Button", "btnReset", {"Text": "صفّر"}]], "click": ["btnPlus", "btnPlus", "btnPlus"], "expect": {"lblCount": "3"}} -->
```python form exercise
from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def Form1_Load(self):
        pass


if __name__ == "__main__":
    Form1().show()
```

<!-- test: {"controls": [["Label", "lblCount", {}], ["Button", "btnPlus", {"Text": "+1"}], ["Button", "btnReset", {"Text": "صفّر"}]], "click": ["btnPlus", "btnPlus", "btnPlus"], "expect": {"lblCount": "3"}} -->
```python form solution
from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):

    def Form1_Load(self):
        self.count = 0
        self.lblCount.config(text="0")

    def btnPlus_Click(self):
        self.count += 1
        self.lblCount.config(text=str(self.count))

    def btnReset_Click(self):
        self.count = 0
        self.lblCount.config(text="0")


if __name__ == "__main__":
    Form1().show()
```

## اختبر نفسك

```quiz
{"question": "في أي ملف تكتب معالجات الأحداث لمشروع Python (Tkinter)؟", "choices": ["Form1.form", "Form1_designer.py", "Form1.py", "project.radproj"], "answer": 2, "explanation": "Form1.py ملفك أنت، أما Form1_designer.py فتولّده الـ IDE من التصميم."}
```

```quiz
{"question": "زر اسمه btnSave، ما اسم الدالة التي تعمل عند الضغط عليه؟", "choices": ["Click_btnSave", "btnSave_Click", "on_btnSave", "btnSave()"], "answer": 1, "explanation": "الصيغة دائمًا اسمالأداة_اسمالحدث."}
```

```quiz
{"question": "كيف تغيّر نص Label اسمه lblInfo في Tkinter؟", "choices": ["self.lblInfo.text = \"x\"", "self.lblInfo.config(text=\"x\")", "lblInfo = \"x\"", "self.lblInfo.setText(\"x\")"], "answer": 1, "explanation": "في Tkinter نغيّر الخصائص بـ config. أما setText فهي أسلوب Qt الذي سنراه في الدرس 15."}
```

## الخلاصة

- مشروع النوافذ: **File ← New Project ← Python (Tkinter) ← Windows Application**.
- ارسم الأدوات من **Toolbox**، وسمّها من **Properties**، وانقر مرتين لتنشئ معالج الحدث.
- كودك في `Form1.py` داخل صنف يرث من `Form1Designer`، والدالة `اسمالأداة_الحدث`.
- `get()` لقراءة مربع النص، و`config(text=...)` لتغيير النصوص، و`messagebox` للرسائل.
