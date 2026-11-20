# الدرس 17: القوائم (Menus)

**في هذا الدرس ستتعلم:**

- إضافة **شريط قوائم** إلى النموذج باستخدام **محرر القوائم** (Menu Editor).
- القوائم الفرعية والخط الفاصل.
- كتابة كود عناصر القوائم بحدث `Click`.
- الخاصيتين `Checked` و`Enabled` لعناصر القائمة.

## قائمة الطعام في المطعم

قائمة المطعم مقسّمة إلى أقسام: مشروبات، ومقبلات، وأطباق رئيسية، وتحت كل قسم أصناف.
شريط القوائم في البرامج مثلها تمامًا: أقسام مثل **ملف** و**تحرير** و**مساعدة**، وتحت كل قسم أوامر مثل **جديد** و**حفظ** و**خروج**. كل عنصر قائمة يتصرف مثل زر: له اسم، ونص، وحدث `Click`.

## إنشاء القائمة في البيئة

1. من **صندوق الأدوات** (Toolbox) اسحب أداة **MenuStrip** إلى النموذج.
2. يفتح **محرر القوائم** (Menu Editor) تلقائيًّا. لكل عنصر تكتب:
   - **النص** (Text): ما يراه المستخدم، مثل "ملف".
   - **الاسم** (Name): ما تستخدمه في الكود، ويبدأ عادة بـ `mnu`، مثل `mnuFile`.
3. استخدم أزرار الإزاحة لجعل عنصر **فرعيًّا** تحت عنصر آخر، واكتب `-` كنص لعنصر يكون **خطًّا فاصلًا**.
4. لإعادة فتح المحرر لاحقًا: حدد شريط القوائم واضغط زر التحرير بجانب خاصية العناصر في نافذة الخصائص.

> 💡 **عادة جيدة:** سمِّ العناصر الفرعية باسم القسم ثم الأمر: `mnuFileNew` و`mnuFileSave` و`mnuHelpAbout`. هكذا تعرف مكان كل عنصر من اسمه.

## القائمة في ملف النموذج

في صيغة `.frm` تُوصف القائمة بأدوات `VB.Menu` متداخلة. الحرف `&` قبل حرف في النص يجعله **حرف اختصار** في فيجوال بيسك 6 (`&File` تظهر File مع خط تحت F).
عنصر القائمة نكتب له إجراء `Click` مثل الزر تمامًا: `mnuFileExit_Click`.

<!-- test: {"steps": [["menu", "mnuEditUpper"], ["menu", "mnuHelpAbout"]], "expect": {"txtNote.Text": "HELLO MENUS"}, "msgbox": ["محرر النصوص الصغير - الإصدار 1.0"]} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "محرر النصوص الصغير"
   ClientWidth     =   5400
   ClientHeight    =   3000
   Begin VB.TextBox txtNote
      Text            =   "hello menus"
      MultiLine       =   -1  'True
      Left            =   120
      Top             =   120
      Width           =   5100
      Height          =   2700
   End
   Begin VB.Menu mnuFile
      Caption         =   "ملف"
      Begin VB.Menu mnuFileNew
         Caption         =   "جديد"
      End
      Begin VB.Menu mnuFileSep
         Caption         =   "-"
      End
      Begin VB.Menu mnuFileExit
         Caption         =   "خروج"
      End
   End
   Begin VB.Menu mnuEdit
      Caption         =   "تحرير"
      Begin VB.Menu mnuEditUpper
         Caption         =   "حروف كبيرة"
      End
      Begin VB.Menu mnuEditLower
         Caption         =   "حروف صغيرة"
      End
   End
   Begin VB.Menu mnuHelp
      Caption         =   "مساعدة"
      Begin VB.Menu mnuHelpAbout
         Caption         =   "حول البرنامج"
      End
   End
End

Option Explicit

Private Sub mnuFileNew_Click()
    txtNote.Text = ""
End Sub

Private Sub mnuFileExit_Click()
    Unload Me
End Sub

Private Sub mnuEditUpper_Click()
    txtNote.Text = UCase(txtNote.Text)
End Sub

Private Sub mnuEditLower_Click()
    txtNote.Text = LCase(txtNote.Text)
End Sub

Private Sub mnuHelpAbout_Click()
    MsgBox "محرر النصوص الصغير - الإصدار 1.0", vbInformation, "حول"
End Sub
```

- `Unload Me` تغلق النموذج الحالي، وعندما يُغلق آخر نموذج ينتهي البرنامج.
- الخاصية `MultiLine = True` تجعل مربع النص يقبل عدة أسطر.

## Checked: علامة الاختيار

الخاصية `Checked` تضع علامة ✓ بجانب العنصر، وتُستخدم للخيارات التي تُشغَّل وتُطفأ، مثل "التفاف النص" أو "الوضع الليلي":

<!-- test: {"steps": [["menu", "mnuViewDark"]], "expect": {"mnuViewDark.Checked": "True", "lblText.BackColor": "0"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "الوضع الليلي"
   ClientWidth     =   4800
   ClientHeight    =   2000
   Begin VB.Label lblText
      Caption         =   "جرّب قائمة عرض"
      Left            =   240
      Top             =   400
      Width           =   4200
      Height          =   800
   End
   Begin VB.Menu mnuView
      Caption         =   "عرض"
      Begin VB.Menu mnuViewDark
         Caption         =   "الوضع الليلي"
      End
   End
End

Private Sub mnuViewDark_Click()
    mnuViewDark.Checked = Not mnuViewDark.Checked
    If mnuViewDark.Checked Then
        lblText.BackColor = vbBlack
        lblText.ForeColor = vbWhite
    Else
        lblText.BackColor = vbWhite
        lblText.ForeColor = vbBlack
    End If
End Sub
```

`mnuViewDark.Checked = Not mnuViewDark.Checked` حيلة مشهورة **لعكس** قيمة `Boolean`: إذا كانت `True` تصبح `False` والعكس.

## Enabled: تعطيل عنصر القائمة

مثل الأزرار، يمكن تعطيل عنصر القائمة حتى يصبح استخدامه منطقيًّا. مثال: "حذف" لا يعمل إلا إذا كانت القائمة فيها عناصر:

<!-- test: {"steps": [["click", "cmdAdd"], ["menu", "mnuEditClear"]], "expect": {"lstItems.ListCount": "0", "mnuEditClear.Enabled": "False"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "تعطيل القوائم"
   ClientWidth     =   4800
   ClientHeight    =   2800
   Begin VB.ListBox lstItems
      Left            =   240
      Top             =   240
      Width           =   2600
      Height          =   2000
   End
   Begin VB.CommandButton cmdAdd
      Caption         =   "أضف عنصرًا"
      Left            =   3000
      Top             =   240
      Width           =   1600
      Height          =   500
   End
   Begin VB.Menu mnuEdit
      Caption         =   "تحرير"
      Begin VB.Menu mnuEditClear
         Caption         =   "امسح الكل"
      End
   End
End

Option Explicit

Private Sub Form_Load()
    mnuEditClear.Enabled = False
End Sub

Private Sub cmdAdd_Click()
    lstItems.AddItem "عنصر " & (lstItems.ListCount + 1)
    mnuEditClear.Enabled = True
End Sub

Private Sub mnuEditClear_Click()
    lstItems.Clear
    mnuEditClear.Enabled = False
End Sub
```

## أخطاء شائعة

- **تكرار الاسم نفسه لعنصرين:** كل عنصر قائمة يحتاج اسمًا فريدًا (`Name`).
- **نسيان تسمية العنصر:** العنصر بلا اسم لا يمكن ربطه بكود.
- **وضع أوامر كثيرة في القسم الأول:** رتّب الأوامر في أقسام منطقية، واستخدم الخط الفاصل `-` لتجميع الأوامر المتقاربة.
- **كتابة الكود في قسم رئيسي له قائمة فرعية:** القسم الرئيسي مثل "ملف" يفتح القائمة فقط؛ اكتب الكود للعناصر الفرعية.

## تمارين

### تمرين 1: قائمة الألوان

نموذج فيه عنوان `lblSample`، وقائمة "لون" فيها ثلاثة عناصر: `mnuColorRed` و`mnuColorGreen` و`mnuColorBlue`. كل عنصر يغيّر لون خلفية العنوان.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "الألوان"
   ClientWidth     =   4800
   ClientHeight    =   2000
   Begin VB.Label lblSample
      Caption         =   "نص تجريبي"
      Left            =   240
      Top             =   400
      Width           =   4200
      Height          =   800
   End
   Begin VB.Menu mnuColor
      Caption         =   "لون"
      Begin VB.Menu mnuColorRed
         Caption         =   "أحمر"
      End
      Begin VB.Menu mnuColorGreen
         Caption         =   "أخضر"
      End
      Begin VB.Menu mnuColorBlue
         Caption         =   "أزرق"
      End
   End
End

' اكتب إجراءات Click الثلاثة
```

<!-- test: {"steps": [["menu", "mnuColorBlue"]], "expect": {"lblSample.BackColor": "16711680"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "الألوان"
   ClientWidth     =   4800
   ClientHeight    =   2000
   Begin VB.Label lblSample
      Caption         =   "نص تجريبي"
      Left            =   240
      Top             =   400
      Width           =   4200
      Height          =   800
   End
   Begin VB.Menu mnuColor
      Caption         =   "لون"
      Begin VB.Menu mnuColorRed
         Caption         =   "أحمر"
      End
      Begin VB.Menu mnuColorGreen
         Caption         =   "أخضر"
      End
      Begin VB.Menu mnuColorBlue
         Caption         =   "أزرق"
      End
   End
End

Private Sub mnuColorRed_Click()
    lblSample.BackColor = vbRed
End Sub

Private Sub mnuColorGreen_Click()
    lblSample.BackColor = vbGreen
End Sub

Private Sub mnuColorBlue_Click()
    lblSample.BackColor = vbBlue
End Sub
```

### تمرين 2: حروف كبيرة بعلامة اختيار

أضف قائمة "تنسيق" فيها عنصر اسمه `mnuFormatUpper` ونصه "حروف كبيرة" له علامة اختيار: عند تفعيله يتحول نص `lblTitle` إلى حروف كبيرة، وعند إلغائه يعود صغيرًا.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "تنسيق"
   ClientWidth     =   4800
   ClientHeight    =   2000
   Begin VB.Label lblTitle
      Caption         =   "visual basic"
      Left            =   240
      Top             =   400
      Width           =   4200
      Height          =   800
   End
   Begin VB.Menu mnuFormat
      Caption         =   "تنسيق"
      Begin VB.Menu mnuFormatUpper
         Caption         =   "حروف كبيرة"
      End
   End
End

Private Sub mnuFormatUpper_Click()

End Sub
```

<!-- test: {"steps": [["menu", "mnuFormatUpper"]], "expect": {"lblTitle.Caption": "VISUAL BASIC", "mnuFormatUpper.Checked": "True"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "تنسيق"
   ClientWidth     =   4800
   ClientHeight    =   2000
   Begin VB.Label lblTitle
      Caption         =   "visual basic"
      Left            =   240
      Top             =   400
      Width           =   4200
      Height          =   800
   End
   Begin VB.Menu mnuFormat
      Caption         =   "تنسيق"
      Begin VB.Menu mnuFormatUpper
         Caption         =   "حروف كبيرة"
      End
   End
End

Private Sub mnuFormatUpper_Click()
    mnuFormatUpper.Checked = Not mnuFormatUpper.Checked
    If mnuFormatUpper.Checked Then
        lblTitle.Caption = UCase(lblTitle.Caption)
    Else
        lblTitle.Caption = LCase(lblTitle.Caption)
    End If
End Sub
```

## اختبر نفسك

```quiz
{"question": "ما اسم الإجراء الذي يُنفَّذ عند اختيار عنصر قائمة اسمه mnuFileSave؟", "choices": ["mnuFileSave_Select", "mnuFileSave_Click", "mnuFile_Save", "Save_Click"], "answer": 1, "explanation": "عناصر القائمة تستخدم حدث Click مثل الأزرار."}
```

```quiz
{"question": "ماذا نكتب في نص العنصر ليظهر خطًّا فاصلًا؟", "choices": ["_", "-", "|", "Sep"], "answer": 1, "explanation": "العنصر الذي نصه - يظهر كخط فاصل."}
```

```quiz
{"question": "ما الخاصية التي تضع علامة ✓ بجانب العنصر؟", "choices": ["Enabled", "Visible", "Checked", "Selected"], "answer": 2, "explanation": "Checked = True تُظهر علامة الاختيار."}
```

```quiz
{"question": "ماذا يفعل  x = Not x  إذا كانت x = True؟", "choices": ["تبقى True", "تصبح False", "خطأ", "تصبح 0 ثم 1"], "answer": 1, "explanation": "Not تعكس القيمة المنطقية."}
```

## الخلاصة

- شريط القوائم يُصمَّم بمحرر القوائم: لكل عنصر نص واسم، والخط الفاصل نصه `-`.
- كل عنصر له إجراء `Click` مثل الزر.
- `Checked` لعلامة الاختيار، و`Enabled` للتعطيل، و`Unload Me` لإغلاق النموذج.
