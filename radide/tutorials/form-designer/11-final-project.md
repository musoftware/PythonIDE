# الدرس 11: المشروع النهائي: قائمة المهام

**في هذا الدرس:**

- تبني برنامجًا كاملًا بالمصمم خطوة بخطوة: **قائمة مهام** (To-Do list).
- تستخدم كل ما تعلمته: الأدوات، والخصائص، والأحداث، والقوائم، والترتيب، و Anchor.
- تختبره بزر «جرّبه»، ثم تطوّره بتمرين.

## ما الذي سنبنيه؟

نافذة فيها:

- مربع نص `txtTask` تكتب فيه المهمة، وزر `cmdAdd` "أضف".
- مربع اختيار `chkUrgent` "عاجلة": المهمة العاجلة تبدأ بعلامة ⚠.
- قائمة `lstTasks` فيها المهام.
- زر `cmdDone` "تمت" يحذف المهمة المحددة، وزر `cmdClear` "امسح الكل".
- عنوان `lblCount` يعرض عدد المهام.
- قائمة "ملف" فيها "خروج".

## الخطوة 1: التصميم

1. **File > New Project...** > **Visual Basic 6 (BASIC)** > **Windows Application**، والاسم `TodoList`.
2. حدد النموذج، واجعل `Text` = `قائمة المهام` و `StartPosition` = `CenterScreen`.
3. ضع الأدوات وسمّها كما في الجدول:

| الأداة | Name | Text | Anchor |
|---|---|---|---|
| `TextBox` | `txtTask` | (فارغ) | `Top, Left, Right` |
| `Button` | `cmdAdd` | `أضف` | `Top, Right` |
| `CheckBox` | `chkUrgent` | `عاجلة` | `Top, Left` |
| `ListBox` | `lstTasks` | — | `Top, Bottom, Left, Right` |
| `Button` | `cmdDone` | `تمت` | `Bottom, Left` |
| `Button` | `cmdClear` | `امسح الكل` | `Bottom, Left` |
| `Label` | `lblCount` | `لا توجد مهام` | `Bottom, Left, Right` |

4. حدد `cmdDone` و `cmdClear` و **Format > Make Same Size > Both** ثم **Format > Align > Tops**.
5. **View > Tab Order**: `txtTask` ثم `chkUrgent` ثم `cmdAdd` ثم `lstTasks` ثم `cmdDone` ثم `cmdClear`.
6. ضع `MenuStrip`، وبـ **Edit Menu...** أنشئ قائمة "ملف" (`mnuFile`) فيها "خروج" (`mnuFileExit`).
7. اسحب حافة النموذج في المصمم: القائمة تتمدد، والأزرار تلحق بحوافها.

## الخطوة 2: الكود

انقر كل زر مرتين واكتب معالجه. ونقطة مهمة: نجمع تحديث العنوان والأزرار في إجراء واحد `UpdateUI` نستدعيه بعد كل تغيير، بدل تكرار الكود.

## البرنامج كاملًا

اضغط «جرّبه»، ثم «افتح في المحرر» لترى التصميم في المصمم وتجرّب Anchor بتغيير حجم النافذة:

<!-- test: {"steps": [["set", "txtTask", "Text", "شراء خبز"], ["click", "cmdAdd"], ["set", "txtTask", "Text", "دفع الفاتورة"], ["set", "chkUrgent", "Value", "1"], ["click", "cmdAdd"], ["set", "txtTask", "Text", "   "], ["click", "cmdAdd"], ["set", "lstTasks", "ListIndex", "0"], ["click", "cmdDone"]], "expect": {"lstTasks.ListCount": "1", "lstTasks.List(0)": "⚠ دفع الفاتورة", "lblCount.Caption": "عدد المهام: 1", "chkUrgent.Value": "0", "txtTask.Text": "   ", "cmdClear.Enabled": "True"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "قائمة المهام"
   ClientWidth     =   5400
   ClientHeight    =   4200
   Begin VB.TextBox txtTask
      TabIndex        =   0
      Left            =   240
      Top             =   240
      Width           =   3600
      Height          =   400
   End
   Begin VB.CheckBox chkUrgent
      Caption         =   "عاجلة"
      TabIndex        =   1
      Left            =   240
      Top             =   780
      Width           =   1500
      Height          =   400
   End
   Begin VB.CommandButton cmdAdd
      Caption         =   "أضف"
      TabIndex        =   2
      Left            =   3960
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.ListBox lstTasks
      TabIndex        =   3
      Left            =   240
      Top             =   1320
      Width           =   4920
      Height          =   1800
   End
   Begin VB.CommandButton cmdDone
      Caption         =   "تمت"
      TabIndex        =   4
      Left            =   240
      Top             =   3240
      Width           =   1200
      Height          =   400
   End
   Begin VB.CommandButton cmdClear
      Caption         =   "امسح الكل"
      TabIndex        =   5
      Left            =   1560
      Top             =   3240
      Width           =   1200
      Height          =   400
   End
   Begin VB.Label lblCount
      Left            =   2880
      Top             =   3300
      Width           =   2280
      Height          =   400
   End
   Begin VB.Menu mnuFile
      Caption         =   "ملف"
      Begin VB.Menu mnuFileExit
         Caption         =   "خروج"
      End
   End
End

Option Explicit

Private Sub Form_Load()
    UpdateUI
End Sub

Private Sub UpdateUI()
    If lstTasks.ListCount = 0 Then
        lblCount.Caption = "لا توجد مهام"
    Else
        lblCount.Caption = "عدد المهام: " & lstTasks.ListCount
    End If
    cmdClear.Enabled = (lstTasks.ListCount > 0)
End Sub

Private Sub cmdAdd_Click()
    Dim task As String
    task = Trim(txtTask.Text)
    If task = "" Then Exit Sub
    If chkUrgent.Value = vbChecked Then task = "⚠ " & task
    lstTasks.AddItem task
    txtTask.Text = ""
    chkUrgent.Value = vbUnchecked
    UpdateUI
End Sub

Private Sub cmdDone_Click()
    If lstTasks.ListIndex >= 0 Then
        lstTasks.RemoveItem lstTasks.ListIndex
        UpdateUI
    End If
End Sub

Private Sub cmdClear_Click()
    lstTasks.Clear
    UpdateUI
End Sub

Private Sub mnuFileExit_Click()
    Unload Me
End Sub
```

### لاحظ

- `Trim` يحذف المسافات، فالمهمة المكونة من مسافات فقط لا تُضاف (الاختبار جرّب ذلك).
- `UpdateUI` يجعل زر "امسح الكل" معطّلًا عندما تكون القائمة فارغة: الواجهة تمنع الخطأ قبل أن يحدث.
- الأسماء الواضحة (`cmdDone` و `lstTasks`) تجعل الكود يُقرأ كجمل عادية.

## أفكار للتطوير

- **States** (في مشروع Python): زر "أضف" يتوهج عند وقوف الفأرة.
- **الترجمة**: نسخة إنجليزية من النموذج، و `RightToLeftLayout` للعربية.
- **الحفظ في قاعدة بيانات**: تجده في دليل البيانات والتقارير.

## تمرين

### تمرين 1: زر "عاجلة أولًا"

أضف زرًّا `cmdUrgentFirst` نصه "العاجلة أولًا"، يكتب في `lblCount` عدد المهام العاجلة بهذا الشكل: `المهام العاجلة: 2`.
المهمة العاجلة هي التي تبدأ بـ `"⚠ "`. استخدم حلقة `For` على `lstTasks.List(i)` و `Left(..., 2)`.
(لتسهيل الاختبار، يملأ `Form_Load` القائمة بثلاث مهام جاهزة.)

```vb form exercise
Begin VB.Form Form1
   Caption         =   "قائمة المهام"
   ClientWidth     =   5400
   ClientHeight    =   3000
   Begin VB.ListBox lstTasks
      Left            =   240
      Top             =   240
      Width           =   4920
      Height          =   1800
   End
   Begin VB.Label lblCount
      Left            =   240
      Top             =   2200
      Width           =   3000
      Height          =   400
   End
End

Private Sub Form_Load()
    lstTasks.AddItem "⚠ دفع الفاتورة"
    lstTasks.AddItem "شراء خبز"
    lstTasks.AddItem "⚠ موعد الطبيب"
End Sub

' أضف الزر cmdUrgentFirst في التصميم واكتب معالجه
```

<!-- test: {"steps": [["click", "cmdUrgentFirst"]], "expect": {"lblCount.Caption": "المهام العاجلة: 2"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "قائمة المهام"
   ClientWidth     =   5400
   ClientHeight    =   3000
   Begin VB.ListBox lstTasks
      Left            =   240
      Top             =   240
      Width           =   4920
      Height          =   1800
   End
   Begin VB.Label lblCount
      Left            =   240
      Top             =   2200
      Width           =   3000
      Height          =   400
   End
   Begin VB.CommandButton cmdUrgentFirst
      Caption         =   "العاجلة أولًا"
      Left            =   3360
      Top             =   2160
      Width           =   1800
      Height          =   400
   End
End

Private Sub Form_Load()
    lstTasks.AddItem "⚠ دفع الفاتورة"
    lstTasks.AddItem "شراء خبز"
    lstTasks.AddItem "⚠ موعد الطبيب"
End Sub

Private Sub cmdUrgentFirst_Click()
    Dim i As Integer
    Dim n As Integer
    For i = 0 To lstTasks.ListCount - 1
        If Left(lstTasks.List(i), 2) = "⚠ " Then n = n + 1
    Next i
    lblCount.Caption = "المهام العاجلة: " & n
End Sub
```

## اختبر نفسك

```quiz
{"question": "لماذا جمعنا تحديث العنوان والأزرار في إجراء واحد `UpdateUI`؟", "choices": ["لأن VB يشترط ذلك", "لنستدعيه بعد كل تغيير بدل تكرار الكود نفسه في كل معالج", "لتسريع البرنامج فقط", "لا سبب"], "answer": 1, "explanation": "إجراء واحد يُستدعى من كل مكان: إذا أردت تغيير الشكل غيّرته في مكان واحد."}
```

```quiz
{"question": "أي Anchor يجعل القائمة `lstTasks` تتمدد في الاتجاهين مع النافذة؟", "choices": ["`Top, Left`", "`Top, Bottom, Left, Right`", "`Bottom, Right`", "`Dock = None`"], "answer": 1, "explanation": "الحواف الأربع تمدها عرضًا وارتفاعًا."}
```

```quiz
{"question": "ما فائدة `Trim(txtTask.Text)` قبل الإضافة؟", "choices": ["تحويل النص إلى حروف كبيرة", "حذف المسافات من الطرفين حتى لا تُضاف مهمة فارغة", "ترجمة النص", "حفظ النص"], "answer": 1, "explanation": "Trim يحذف المسافات، فنص من مسافات فقط يصبح فارغًا ولا يُضاف."}
```

## الخلاصة

- صممت نافذة كاملة: أدوات بأسماء واضحة، و Anchor للتمدد، وترتيب Tab، وقائمة "ملف".
- كتبت معالجات الأحداث، وجمعت تحديث الواجهة في `UpdateUI`.
- أنهيت دليل مصمم النماذج. الخطوة التالية: **دليل البيانات والتقارير** لحفظ المهام في قاعدة بيانات وطباعة تقرير بها.
- ودرسان إضافيان في هذا الدليل: **الحركات الجاهزة ومقاسات النافذة** (الدرس 12)، و**حزم المكونات** (الدرس 13).
