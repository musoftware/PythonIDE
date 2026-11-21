# الدرس 2: تعرّف على بيئة التطوير

**في هذا الدرس ستتعلم:**

- أجزاء بيئة RAD IDE: مصمّم النماذج، وصندوق الأدوات، ونافذة الخصائص، ونافذة الكود، ونافذة المخرجات.
- كيف تنشئ مشروعًا جديدًا بلغة BASIC وتشغّله.
- الفرق بين برنامج "وحدة" (Module) يبدأ من `Sub Main` وبرنامج "نموذج" (Form) له نافذة وأزرار.

## الورشة والأدوات

تخيّل ورشة نجارة: فيها طاولة عمل، وصندوق أدوات، ودفتر ملاحظات تسجّل فيه مقاسات كل قطعة.
بيئة التطوير المتكاملة (IDE) هي ورشة المبرمج:

| الجزء | اسمه في البيئة | وظيفته |
|---|---|---|
| مصمّم النماذج | Designer | "طاولة العمل" التي ترسم عليها نافذة برنامجك |
| صندوق الأدوات | Toolbox | الأدوات الجاهزة: زر، مربع نص، عنوان، قائمة... |
| نافذة الخصائص | Properties | "دفتر المقاسات": اسم الأداة، ونصها، ولونها، ومكانها |
| مستكشف الحل | Solution Explorer | قائمة ملفات المشروع: النماذج والوحدات |
| نافذة الكود | Code | المكان الذي تكتب فيه الأوامر |
| نافذة المخرجات | Output | تظهر فيها نتائج `Debug.Print` ورسائل الأخطاء |

> 💡 **ملاحظة:** إذا كانت واجهة البيئة بالعربية ستجد الأسماء العربية، وإذا كانت بالإنجليزية ستجد الأسماء المكتوبة بين القوسين.

## إنشاء مشروع جديد

1. من قائمة **File** اختر **New Project...** (مشروع جديد).
2. اختر اللغة **Visual Basic 6 (BASIC)**.
3. اكتب اسم المشروع واختر مجلّد الحفظ ثم اضغط **OK**.

ستجد نموذجًا فارغًا اسمه `Form1` في مصمّم النماذج. هذا هو "الشبّاك" الذي سيراه مستخدم برنامجك.

## مفاتيح مهمة

| المفتاح | الوظيفة |
|---|---|
| F5 | تشغيل البرنامج (مع مصحّح الأخطاء) |
| Ctrl+F5 | تشغيل بدون مصحّح الأخطاء |
| Shift+F5 | إيقاف البرنامج |
| F9 | وضع نقطة توقّف (Breakpoint) على السطر الحالي |
| F10 / F11 | التنفيذ خطوة بخطوة |

## نوعان من البرامج

### 1) برنامج وحدة يبدأ من `Sub Main`

**الوحدة** (Module) ملف كود فقط، بلا نافذة. أضِفها من قائمة **Project** ثم **Add Module...**، ثم اجعل بداية المشروع `Sub Main` من خصائص المشروع.
سنستخدم هذا النوع كثيرًا في الدروس الأولى لأنه بسيط: نكتب، ونشغّل، ونقرأ النتيجة في نافذة المخرجات.

```vb run
Sub Main()
    Debug.Print "هذا برنامج وحدة"
    Debug.Print "يبدأ من Sub Main وينتهي عند End Sub"
End Sub
```

```text output
هذا برنامج وحدة
يبدأ من Sub Main وينتهي عند End Sub
```

### 2) برنامج نموذج له نافذة

في برامج النماذج لا يوجد `Sub Main`. البرنامج ينتظر المستخدم: عندما **يضغط زرًّا** يحدث **حدث** (Event)، فيُنفَّذ الكود المرتبط بهذا الحدث.
جرّب هذا: ارسم زرًّا (CommandButton) على النموذج، ثم انقر عليه نقرًا مزدوجًا. ستفتح نافذة الكود وفيها:

```vb
Private Sub Command1_Click()

End Sub
```

اسم الإجراء = اسم الأداة + شرطة سفلية + اسم الحدث. أي كود تكتبه بين السطرين يُنفَّذ عند الضغط على الزر.

## كيف نكتب النموذج في الدروس؟

في البيئة أنت **ترسم** النموذج بالفأرة. لكن في الدروس نحتاج طريقة لوصف النموذج كتابةً، فنستخدم صيغة ملفات فيجوال بيسك 6 (`.frm`):
الجزء الأول يصف النافذة وأدواتها (`Begin ... End`)، وبعده يأتي الكود. لا تقلق من الأرقام: `Left` و`Top` مكان الأداة، و`Width` و`Height` حجمها، بوحدة اسمها **تويب** (Twip)، وكل 15 تويب تساوي نقطة واحدة على الشاشة تقريبًا.

عند الضغط على **جرّبه** تحوّل البيئة هذا الوصف إلى نموذج حقيقي وتشغّله:

<!-- test: {"steps": [["click", "cmdHello"]], "msgbox": ["أهلًا! هذا أول نموذج لك"]} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "أول نموذج"
   ClientWidth     =   4200
   ClientHeight    =   1800
   Begin VB.CommandButton cmdHello
      Caption         =   "اضغطني"
      Left            =   1200
      Top             =   600
      Width           =   1800
      Height          =   500
   End
End

Private Sub cmdHello_Click()
    MsgBox "أهلًا! هذا أول نموذج لك"
End Sub
```

اضغط الزر في النافذة التي تظهر: سيظهر **صندوق رسالة** (MsgBox). سنتعرّف عليه بالتفصيل في الدرس القادم.

## تغيير الخصائص من الكود

كل أداة لها **خصائص** (Properties) مثل `Caption` (النص الظاهر عليها). يمكن تغييرها من نافذة الخصائص قبل التشغيل، أو من الكود أثناء التشغيل بكتابة: اسم الأداة ثم نقطة ثم اسم الخاصية.

<!-- test: {"steps": [["click", "cmdChange"]], "expect": {"lblMsg.Caption": "تغيّر النص!", "cmdChange.Caption": "تم"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "الخصائص"
   ClientWidth     =   4200
   ClientHeight    =   1800
   Begin VB.Label lblMsg
      Caption         =   "النص الأصلي"
      Left            =   240
      Top             =   240
      Width           =   3600
      Height          =   400
   End
   Begin VB.CommandButton cmdChange
      Caption         =   "غيّر النص"
      Left            =   1200
      Top             =   900
      Width           =   1800
      Height          =   500
   End
End

Private Sub cmdChange_Click()
    lblMsg.Caption = "تغيّر النص!"
    cmdChange.Caption = "تم"
End Sub
```

## أخطاء شائعة

- **تغيير اسم الأداة بعد كتابة الكود:** إذا غيّرت `Name` من `Command1` إلى `cmdOK` يجب تغيير اسم الإجراء أيضًا إلى `cmdOK_Click`، وإلا لن يعمل الزر.
- **الخلط بين `Name` و`Caption`:** `Name` هو الاسم الذي تستخدمه في الكود، و`Caption` هو النص الذي يراه المستخدم.
- **نسيان الحفظ:** احفظ مشروعك دائمًا (Ctrl+S) قبل التجارب الكبيرة.
- **مشروع وحدة بدون Sub Main:** إذا كانت بداية المشروع `Sub Main` ولا يوجد إجراء بهذا الاسم ستظهر رسالة: "No startup form and no Sub Main found".

> 💡 **عادة جيدة:** سمِّ الأدوات بأسماء واضحة تبدأ ببادئة تدل على نوعها: `cmd` للزر، و`lbl` للعنوان، و`txt` لمربع النص. هكذا تفهم الكود بسرعة.

## تمارين

### تمرين 1: زر الترحيب

أنشئ نموذجًا فيه زر اسمه `cmdWelcome` مكتوب عليه "ترحيب"، وعند الضغط عليه يتغير عنوان النافذة (`Form1.Caption`) إلى "مرحبا".

```vb form exercise
Begin VB.Form Form1
   Caption         =   "تمرين"
   ClientWidth     =   4200
   ClientHeight    =   1800
   Begin VB.CommandButton cmdWelcome
      Caption         =   "ترحيب"
      Left            =   1200
      Top             =   600
      Width           =   1800
      Height          =   500
   End
End

Private Sub cmdWelcome_Click()
    ' اكتب هنا
End Sub
```

<!-- test: {"steps": [["click", "cmdWelcome"]], "expect": {"Form1.Caption": "مرحبا"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "تمرين"
   ClientWidth     =   4200
   ClientHeight    =   1800
   Begin VB.CommandButton cmdWelcome
      Caption         =   "ترحيب"
      Left            =   1200
      Top             =   600
      Width           =   1800
      Height          =   500
   End
End

Private Sub cmdWelcome_Click()
    Form1.Caption = "مرحبا"
End Sub
```

### تمرين 2: زرّان وعنوان

نموذج فيه عنوان `lblColor` وزرّان: `cmdDay` يكتب في العنوان "صباح الخير"، و`cmdNight` يكتب "مساء الخير".

```vb form exercise
Begin VB.Form Form1
   Caption         =   "صباح ومساء"
   ClientWidth     =   4200
   ClientHeight    =   1800
   Begin VB.Label lblColor
      Caption         =   ""
      Left            =   240
      Top             =   240
      Width           =   3600
      Height          =   400
   End
   Begin VB.CommandButton cmdDay
      Caption         =   "صباح"
      Left            =   240
      Top             =   900
      Width           =   1600
      Height          =   500
   End
   Begin VB.CommandButton cmdNight
      Caption         =   "مساء"
      Left            =   2200
      Top             =   900
      Width           =   1600
      Height          =   500
   End
End

' اكتب الإجراءين cmdDay_Click و cmdNight_Click
```

<!-- test: {"steps": [["click", "cmdDay"]], "expect": {"lblColor.Caption": "صباح الخير"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "صباح ومساء"
   ClientWidth     =   4200
   ClientHeight    =   1800
   Begin VB.Label lblColor
      Caption         =   ""
      Left            =   240
      Top             =   240
      Width           =   3600
      Height          =   400
   End
   Begin VB.CommandButton cmdDay
      Caption         =   "صباح"
      Left            =   240
      Top             =   900
      Width           =   1600
      Height          =   500
   End
   Begin VB.CommandButton cmdNight
      Caption         =   "مساء"
      Left            =   2200
      Top             =   900
      Width           =   1600
      Height          =   500
   End
End

Private Sub cmdDay_Click()
    lblColor.Caption = "صباح الخير"
End Sub

Private Sub cmdNight_Click()
    lblColor.Caption = "مساء الخير"
End Sub
```

## اختبر نفسك

```quiz
{"question": "أين تغيّر النص الظاهر على زر قبل تشغيل البرنامج؟", "choices": ["نافذة المخرجات", "نافذة الخصائص (Properties)", "مستكشف الحل", "قائمة Debug"], "answer": 1, "explanation": "نافذة الخصائص تعرض خصائص الأداة المحددة مثل Caption وName."}
```

```quiz
{"question": "زر اسمه cmdSave. ما اسم الإجراء الذي يُنفَّذ عند الضغط عليه؟", "choices": ["Click_cmdSave", "cmdSave_Click", "cmdSave.Click", "Save_Click"], "answer": 1, "explanation": "اسم إجراء الحدث = اسم الأداة + _ + اسم الحدث."}
```

```quiz
{"question": "أي مفتاح يشغّل البرنامج؟", "choices": ["F1", "F5", "F9", "Esc"], "answer": 1, "explanation": "F5 للتشغيل، وF9 لنقطة التوقف، وShift+F5 للإيقاف."}
```

```quiz
{"question": "ما الفرق بين Name و Caption؟", "choices": ["لا فرق", "Name للكود وCaption للنص الظاهر للمستخدم", "Caption للكود وName للنص الظاهر", "كلاهما للون"], "answer": 1, "explanation": "تستخدم Name داخل الكود، بينما Caption هو ما يراه المستخدم على الأداة."}
```

## الخلاصة

- مصمّم النماذج لرسم النافذة، وصندوق الأدوات للأدوات، ونافذة الخصائص لضبطها، ونافذة الكود للأوامر.
- برنامج الوحدة يبدأ من `Sub Main`، وبرنامج النموذج ينتظر الأحداث مثل `Click`.
- نغيّر الخاصية من الكود بالصيغة: `اسم_الأداة.الخاصية = القيمة`.
