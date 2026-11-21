# الدرس 3: معالج ترحيل المشاريع إلى لغة أخرى

**في هذا الدرس ستتعلم:**

- صفحات معالج **File > Migrate Project...** واحدة واحدة.
- أنواع المشاريع التي يقرؤها المعالج، واللغات التي يكتب إليها.
- قراءة **معاينة التحويل** قبل البدء، و**تقرير الترحيل** بعد الانتهاء.
- كيف يبدو كود VB6 بعد ترحيله إلى Python وإلى VB.NET (ناتج حقيقي من المعالج).
- لماذا يضيف المعالج الملف `vb6compat.py` إلى مشروعك.

## ما الذي يرحّله المعالج؟

**من:** مشاريع VB6 (`.vbp` و`.frm`)، ومشاريع Visual Studio بنماذج Windows Forms (`.sln` و`.csproj` بلغة C#، و`.vbproj` بلغة VB.NET)، وDelphi وLazarus (`.dpr` و`.lpi`)، وملفات Qt Designer (`.ui`)، وغيرها. الصفحة الأولى في المعالج تعرض القائمة الكاملة تحت عنوان **Supported**.

**إلى:**

| الهدف | النتيجة |
|---|---|
| Keep (نفس اللغة) | مشروع RAD IDE بنفس لغة الأصل |
| Python (Tkinter) / Python (PySide6 / Qt) | الكود يُترجم إلى Python بالقواعد |
| Visual Basic 6 (BASIC) | مشروع يعمل على مفسّر BASIC المدمج |
| C# (GUI Bridge) | نماذج RAD IDE وكود C# |
| VB.NET | مشروع Visual Studio بنماذج Windows Forms يُبنى بالأمر `dotnet build` |

## صفحات المعالج

افتح **File > Migrate Project...** (ملف > ترحيل المشروع...):

**الصفحة 1: Project to migrate.** اختر الملف بزر **File...** أو المجلد بزر **Folder...**. تظهر معلومات المشروع الذي تعرّف عليه المعالج.

**الصفحة 2: Target.** اختر الهدف من الجدول السابق.

**الصفحة 3: Options.**

- مكان الكتابة: **Write the project into a new folder (recommended)** (مجلد جديد، وهو المستحسن)، أو **In place** بجانب الملفات الأصلية (فقط إذا لم يُستبدل أي ملف).
- طريقة تحويل الكود:
  - **Convert the event code by rules**: بالقواعد فقط.
  - **Rules + AI for what the rules cannot convert**: القواعد، ثم الذكاء الاصطناعي لما لم تستطع القواعد تحويله.
  - **Keep the original code as comments only**: يبقى الكود الأصلي تعليقات فقط.
- **Copy the original project into _original/ for reference**: نسخة من الأصل للرجوع إليها.

**الصفحة 4: Preview of the mapping.** جدول بكل نموذج وأداة وحدث ووحدة، وكيف سيتحول، وحالته.

**الصفحة 5: Migrating.** سجل التقدم.

**الصفحة 6: Migration report.** الملخص، مع خيارين: **Open the migrated project** و**Open MIGRATION_REPORT.md in the editor**.

## حالات التحويل الخمس

في المعاينة وفي التقرير، كل عنصر له حالة من خمس:

| الحالة | المعنى | ماذا تفعل |
|---|---|---|
| Exact | نُسخ كما هو بدقة (النماذج ومواقع الأدوات) | لا شيء |
| Rules | تُرجم بقواعد مؤكدة | راجع سريعًا |
| Approximate | تُرجم، لكن السلوك قد يختلف قليلًا | اختبره جيدًا |
| AI | ترجمه الذكاء الاصطناعي | راجعه بعناية |
| Manual TODO | لم يُترجم، وبقي تعليقًا مع رقم الملف والسطر | أكمله بنفسك |

> **تشبيه:** المترجم المحترف لكتاب لا يترجم الأمثال الشعبية حرفيًا. يكتب بجانبها ملاحظة: «ترجمة تقريبية» أو «تحتاج مراجعة». تقرير الترحيل هو هذه الملاحظات.

## مثال حقيقي: VB6 إلى Python

هذا نموذج VB6 بسيط (نفس نموذج الدرس السابق):

<!-- test: {"migrate": [["python-tk", "Form1.py"], ["vbnet", "Form1.vb"]], "report": ["| 2 | 1 | 0 | 0 | 0 |"]} -->
```vb
VERSION 5.00
Begin VB.Form Form1
   Caption         =   "Greeter"
   ClientHeight    =   1800
   ClientLeft      =   60
   ClientTop       =   345
   ClientWidth     =   4680
   Begin VB.TextBox txtName
      Height          =   375
      Left            =   240
      TabIndex        =   0
      Top             =   240
      Width           =   2655
   End
   Begin VB.CommandButton cmdGreet
      Caption         =   "Greet"
      Height          =   375
      Left            =   3120
      TabIndex        =   1
      Top             =   240
      Width           =   1215
   End
   Begin VB.Label lblOut
      Height          =   375
      Left            =   240
      TabIndex        =   2
      Top             =   960
      Width           =   4095
   End
End
Attribute VB_Name = "Form1"
Option Explicit

Private Sub cmdGreet_Click()
    Dim n As String
    n = Trim$(txtName.Text)
    If Len(n) = 0 Then
        MsgBox "Type your name", vbExclamation
        Exit Sub
    End If
    lblOut.Caption = "Hello, " & n & "! (" & Len(n) & " letters)"
End Sub
```

وهذا هو الملف `Form1.py` الذي كتبه المعالج بالضبط عند اختيار **Python (Tkinter)**:

```python
from Form1_designer import Form1Designer, EventArgs  # noqa: F401
from vb6compat import *  # noqa: F401,F403 - VB6 functions (Val, MsgBox, Format, file I/O ...)

App.Title = "Form1"  # VB6 App.Title (default title of MsgBox / InputBox)


class Form1(Form1Designer):
    """Write your event handlers here."""

    def cmdGreet_Click(self):
        n = ""
        n = Trim(self.txtName_var.get())
        if len(n) == 0:
            MsgBox("Type your name", vbExclamation)
            return
        self.lblOut.config(text="Hello, " + n + "! (" + CStr(len(n)) + " letters)")

    def Form1_Load(self):
        pass


if __name__ == "__main__":
    Form1().show()
```

لاحظ:

- `txtName.Text` صار `self.txtName_var.get()` (طريقة Tkinter لقراءة الخانة).
- `lblOut.Caption = ...` صار `self.lblOut.config(text=...)`.
- `&` لربط النصوص صار `+`، و`Exit Sub` صار `return`.
- `Trim` و`MsgBox` و`CStr` تأتي من `vb6compat.py`، وهو ملف يضيفه المعالج إلى المشروع.

وفي التقرير `MIGRATION_REPORT.md` جدول الحالات لهذا النموذج:

```text
| Exact | Rules | Approximate | AI | Manual TODO |
|---|---|---|---|---|
| 2 | 1 | 0 | 0 | 0 |
```

وعند اختيار الهدف **VB.NET** يكتب المعالج مشروع Visual Studio (`Form1.vb` و`Form1.Designer.vb` و`Form1.vbproj` و`Program.vb`). هذا `Form1.vb` الذي كتبه:

```vb
Public Class Form1


    Private Sub cmdGreet_Click(sender As Object, e As EventArgs) Handles cmdGreet.Click
        Dim n As String
        n = Trim(txtName.Text)
        If Len(n) = 0 Then
            MsgBox("Type your name", vbExclamation)
            Exit Sub
        End If
        lblOut.Text = "Hello, " & n & "! (" & Len(n) & " letters)"
    End Sub

End Class
```

التغييرات هنا مثل «معالج الترقية» في Visual Basic 2005: `Caption` صار `Text`، والحدث صار له `sender` و`e` و`Handles`، و`MsgBox` صار بأقواس.

## لماذا `vb6compat.py`؟

بعض دوال VB6 تختلف عن Python في سلوكها. مثلًا `Mid` في VB6 يبدأ العد من **1**، و`InStr` يرجع **0** إذا لم يجد النص، و`Val("12abc")` يرجع `12` دون خطأ. لو ترجمها المعالج إلى دوال Python العادية لتغيّر سلوك البرنامج. لذلك يضيف `vb6compat.py` الذي فيه دوال بنفس أسماء VB6 وسلوكها. هذا مثال مصغّر لفكرته:

```python run
import re

def Mid(s, start, length=None):
    start -= 1                      # VB6 يبدأ من 1
    return s[start:] if length is None else s[start:start + length]

def InStr(s, find):
    return s.find(find) + 1         # 0 = غير موجود، مثل VB6

def Val(s):
    m = re.match(r"\s*[-+]?\d+(\.\d+)?", s)
    return float(m.group()) if m else 0

print(Mid("RAD IDE", 1, 3))
print(Mid("RAD IDE", 5))
print(InStr("RAD IDE", "IDE"), InStr("RAD IDE", "xyz"))
print(Val("12abc"), Val("abc"))
```

```text output
RAD
IDE
5 0
12.0 0
```

> **مهم:** المشروع المرحَّل **لا يعتمد على البيئة** وقت التشغيل: `vb6compat.py` ملف عادي داخل المشروع، فتستطيع تشغيل البرنامج بـ Python وحده.

## أخطاء شائعة

- **الترحيل «In place» على مشروع مهم:** اختر مجلدًا جديدًا دائمًا (الخيار المستحسن).
- **تخطي صفحة المعاينة:** فيها كل ما سيحتاج تدخلك (Manual TODO) قبل أن تبدأ.
- **حذف `vb6compat.py`:** الكود المترجم يستخدمه. يمكنك لاحقًا استبدال دواله بدوال Python أصلية إذا أردت، مع الاختبار.
- **تجاهل Approximate:** مثل `On Error Resume Next`، قد يتصرف بشكل مختلف قليلًا. اختبر هذه المواضع بالذات.

## تمارين

### تمرين 1: Left وRight

أضف دالتي `Left(s, n)` و`Right(s, n)` بسلوك VB6 (أول n حروف، وآخر n حروف)، واطبع `Left("RAD IDE", 3)` و`Right("RAD IDE", 3)`.

```python exercise
def Left(s, n):
    pass  # أكمل

def Right(s, n):
    pass  # أكمل

print(Left("RAD IDE", 3))
print(Right("RAD IDE", 3))
```

```python solution
def Left(s, n):
    return s[:n]

def Right(s, n):
    return s[-n:] if n > 0 else ""

print(Left("RAD IDE", 3))
print(Right("RAD IDE", 3))
```

```text output
RAD
IDE
```

### تمرين 2 (عملي في البيئة)

احفظ نموذج VB6 من هذا الدرس في ملف `Form1.frm`، ثم افتح **File > Migrate Project...**، واختر الهدف **Python (Tkinter)**، وانظر إلى صفحة المعاينة. بعد الترحيل افتح `MIGRATION_REPORT.md` وتأكد أن الجدول مثل الموجود في الدرس، ثم شغّل المشروع بـ `F5`.

## اختبر نفسك

```quiz
{"question": "ما معنى الحالة Manual TODO في تقرير الترحيل؟", "choices": ["تُرجم بدقة", "لم يُترجم وبقي تعليقًا مع رقم الملف والسطر لتكمله بنفسك", "ترجمه الذكاء الاصطناعي", "حُذف"], "answer": 1, "explanation": "Manual TODO = عمل يدوي مطلوب منك."}
```

```quiz
{"question": "إلى ماذا تحوّل txtName.Text عند الترحيل إلى Python (Tkinter)؟", "choices": ["txtName.Text", "self.txtName_var.get()", "input()", "txtName()"], "answer": 1, "explanation": "في Tkinter تُقرأ الخانة من متغيرها المرتبط txtName_var."}
```

```quiz
{"question": "لماذا يضيف المعالج vb6compat.py؟", "choices": ["للزينة", "لأن دوال مثل Mid وInStr وVal تختلف في VB6 عن Python، فيحافظ على سلوك البرنامج", "لتشغيل البيئة", "لأنه مطلوب لـ Git"], "answer": 1, "explanation": "الملف يحافظ على سلوك VB6 في الكود المترجم."}
```

```quiz
{"question": "أي هدف يكتب مشروع Visual Studio يُبنى بـ dotnet build؟", "choices": ["Python (Tkinter)", "VB.NET", "Keep", "Visual Basic 6 (BASIC)"], "answer": 1, "explanation": "هدف VB.NET يكتب Form1.vb وForm1.Designer.vb وملف .vbproj."}
```

## الخلاصة

- **File > Migrate Project...**: المصدر، ثم الهدف، ثم الخيارات، ثم المعاينة، ثم التقرير.
- كل عنصر حالته: Exact أو Rules أو Approximate أو AI أو Manual TODO.
- VB6 إلى Python: الأدوات بطريقة Tkinter، ودوال VB6 من `vb6compat.py`.
- VB6 إلى VB.NET: مشروع Visual Studio حقيقي.
