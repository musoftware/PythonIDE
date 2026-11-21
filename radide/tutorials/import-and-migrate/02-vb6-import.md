# الدرس 2: استيراد مشروع Visual Basic 6

**في هذا الدرس ستتعلم:**

- استيراد مشروع VB6 (`.vbp`) أو نموذج واحد (`.frm`) خطوة بخطوة.
- ماذا يحدث للنماذج والأدوات والكود أثناء الاستيراد.
- وحدة القياس **twips** في VB6 وكيف تتحول إلى بكسلات.
- تجربة الاستيراد على نموذج VB6 حقيقي داخل هذا الدرس.

## ما الذي تحتويه ملفات VB6؟

مشروع VB6 القديم مجموعة ملفات نصية:

| الملف | ما فيه |
|---|---|
| `.vbp` | ملف المشروع: قائمة النماذج والوحدات، ونموذج البداية، والمراجع |
| `.frm` | نموذج: وصف الأدوات (`Begin VB.CommandButton ... End`) ثم كود الأحداث |
| `.bas` | وحدة كود عامة (Module) |
| `.cls` | وحدة صنف (Class Module) |
| `.frx` | بيانات ثنائية للنموذج (صور وأيقونات) |

## الخطوات

**الخطوة 1:** **File > Import > Visual Basic 6 Project (.vbp / .frm)...** (ملف > استيراد > مشروع Visual Basic 6).

**الخطوة 2:** اختر ملف `.vbp` (المشروع كله) أو ملف `.frm` واحد.

**الخطوة 3:** اختر مجلد المشروع الجديد. البيئة تقترح مجلدًا بجانب الأصل ينتهي بـ `_RAD`.

**الخطوة 4:** اختر **اللغة الهدف** (Target language):

| الاختيار | النتيجة |
|---|---|
| **Visual Basic 6 (BASIC)** (الافتراضي) | الكود يبقى **كما هو** ويعمل على مفسّر BASIC المدمج في البيئة |
| **Python (Tkinter)** أو **Python (PySide6 / Qt)** | الكود **يُترجم إلى Python بالقواعد** (نفس محرك الترحيل في الدرس التالي) |
| أي لغة أخرى | النماذج تُستورد، وكود VB6 يُضاف **كتعليقات مرجعية** لتعيد كتابته |

**الخطوة 5:** يظهر **تقرير الاستيراد**: عدد النماذج والأدوات والأحداث، وأي تحذيرات (مثل أدوات ActiveX/OCX غير معروفة تتحول إلى أدوات بديلة). ويُحفظ نسخة من الملفات الأصلية في المجلد `_original_vb6`.

## `twips`: وحدة القياس في VB6

VB6 يقيس المواقع والأحجام بوحدة اسمها **twip**، وفي الشاشة العادية **15 twip = 1 بكسل**. لذلك `Left = 240` في ملف `.frm` تعني 16 بكسلًا. البيئة تحوّلها تلقائيًا:

```python run
TWIP = 15

def px(twips):
    return round(twips / TWIP)

controls = {"txtName": (240, 240, 2655, 375), "cmdGreet": (3120, 240, 1215, 375)}
for name, (left, top, width, height) in controls.items():
    print(f"{name}: x={px(left)} y={px(top)} w={px(width)} h={px(height)}")
```

```text output
txtName: x=16 y=16 w=177 h=25
cmdGreet: x=208 y=16 w=81 h=25
```

## جرّب: نموذج VB6 حقيقي

هذا نموذج `.frm` كما يحفظه VB6 تمامًا: الرأس `VERSION 5.00`، ثم وصف الأدوات، ثم سطور `Attribute`، ثم الكود. عندما تضغط «جرّبه» يمر النموذج **بنفس طريق** **File > Import > Visual Basic 6 Project**: يتحول إلى نموذج `.form` في المصمم، ويبقى الكود كما هو ويعمل على مفسّر BASIC:

<!-- test: {"steps": [["set", "txtName", "Text", "Sara"], ["click", "cmdGreet"]], "expect": {"lblOut.Caption": "Hello, Sara! (4 letters)", "Form1.Caption": "Greeter"}} -->
```vb form run
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
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
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

بعد الاستيراد ستجد في المشروع:

- `Form1.form`: النموذج بأدواته الثلاث، بمواقع بالبكسل.
- `Form1.bas`: كود الأحداث نفسه (`Private Sub cmdGreet_Click()` ...).
- `project.radproj` ولغته **Visual Basic 6 (BASIC)**، فتضغط `F5` ويعمل البرنامج.

## ماذا عن الكود الذي لا يدعمه المفسّر؟

مفسّر BASIC في البيئة يدعم الجزء الأكبر من VB6 (المتغيرات، والشروط، والحلقات، والدوال، والملفات، والأصناف، والمجموعات ...). وما قد لا يعمل:

- أدوات **ActiveX/OCX** الخارجية: تظهر كأدوات بديلة، ويذكرها التقرير.
- استدعاءات `Declare` لمكتبات ويندوز المعقدة.
- بعض التفاصيل الدقيقة في سلوك VB6 الأصلي.

لهذا اقرأ التقرير دائمًا، وشغّل البرنامج وجرّب كل نافذة.

## أخطاء شائعة

- **استيراد `.frm` وحده بينما يحتاج وحدات `.bas`:** إذا كان النموذج يستدعي دوال من وحدة، استورد ملف `.vbp` ليأتي المشروع كاملًا.
- **فقد ملف `.frx`:** الصور والأيقونات محفوظة فيه. انسخه بجانب `.frm` قبل الاستيراد.
- **اختيار لغة أخرى وتوقع ترجمة كاملة:** مع اللغات غير Python يبقى كود VB6 تعليقات مرجعية. للترجمة الكاملة إلى Python استخدم **Migrate Project** (الدرس التالي).

## تمارين

### تمرين 1: من البكسل إلى `twips`

اكتب الدالة العكسية `twips(px)` التي تحوّل البكسلات إلى twips، واطبع قيمة 16 و200 بكسل.

```python exercise
TWIP = 15

def twips(px):
    pass  # أكمل

print(twips(16), twips(200))
```

```python solution
TWIP = 15

def twips(px):
    return px * TWIP

print(twips(16), twips(200))
```

```text output
240 3000
```

### تمرين 2: عدّل النموذج

عدّل كود النموذج بحيث يكتب البرنامج الاسم **بحروف كبيرة** في `lblOut` (استخدم `UCase$`). مثلًا للاسم `Sara` يكتب `Hello, SARA! (4 letters)`.

```vb form exercise
VERSION 5.00
Begin VB.Form Form1
   Caption         =   "Greeter"
   ClientHeight    =   1800
   ClientWidth     =   4680
   Begin VB.TextBox txtName
      Height          =   375
      Left            =   240
      Top             =   240
      Width           =   2655
   End
   Begin VB.CommandButton cmdGreet
      Caption         =   "Greet"
      Height          =   375
      Left            =   3120
      Top             =   240
      Width           =   1215
   End
   Begin VB.Label lblOut
      Height          =   375
      Left            =   240
      Top             =   960
      Width           =   4095
   End
End
Attribute VB_Name = "Form1"
Option Explicit

Private Sub cmdGreet_Click()
    Dim n As String
    n = Trim$(txtName.Text)
    lblOut.Caption = "Hello, " & n & "! (" & Len(n) & " letters)"
End Sub
```

<!-- test: {"steps": [["set", "txtName", "Text", "Sara"], ["click", "cmdGreet"]], "expect": {"lblOut.Caption": "Hello, SARA! (4 letters)"}} -->
```vb form solution
VERSION 5.00
Begin VB.Form Form1
   Caption         =   "Greeter"
   ClientHeight    =   1800
   ClientWidth     =   4680
   Begin VB.TextBox txtName
      Height          =   375
      Left            =   240
      Top             =   240
      Width           =   2655
   End
   Begin VB.CommandButton cmdGreet
      Caption         =   "Greet"
      Height          =   375
      Left            =   3120
      Top             =   240
      Width           =   1215
   End
   Begin VB.Label lblOut
      Height          =   375
      Left            =   240
      Top             =   960
      Width           =   4095
   End
End
Attribute VB_Name = "Form1"
Option Explicit

Private Sub cmdGreet_Click()
    Dim n As String
    n = UCase$(Trim$(txtName.Text))
    lblOut.Caption = "Hello, " & n & "! (" & Len(n) & " letters)"
End Sub
```

## اختبر نفسك

```quiz
{"question": "كم twip في البكسل الواحد على الشاشة العادية؟", "choices": ["1", "10", "15", "96"], "answer": 2, "explanation": "15 twip = 1 بكسل، فـ Left = 240 تعني 16 بكسلًا."}
```

```quiz
{"question": "إذا اخترت اللغة الهدف Visual Basic 6 (BASIC) عند الاستيراد، ماذا يحدث للكود؟", "choices": ["يُحذف", "يبقى كما هو ويعمل على مفسّر BASIC المدمج", "يُترجم إلى C++", "يتحول إلى تعليقات"], "answer": 1, "explanation": "الكود يُحفظ في Form1.bas ويعمل كما هو."}
```

```quiz
{"question": "أين تُحفظ نسخة من ملفات VB6 الأصلية بعد الاستيراد؟", "choices": ["لا تُحفظ", "في المجلد _original_vb6 داخل المشروع الجديد", "في سلة المحذوفات", "في Git"], "answer": 1, "explanation": "الملفات الأصلية تُنسخ إلى _original_vb6 للرجوع إليها."}
```

## الخلاصة

- **File > Import > Visual Basic 6 Project** يستورد `.vbp` أو `.frm`.
- مع **Visual Basic 6 (BASIC)** يعمل الكود كما هو، ومع Python يُترجم بالقواعد.
- المواقع تتحول من twips إلى بكسلات (÷ 15).
- اقرأ تقرير الاستيراد وجرّب كل نافذة.
