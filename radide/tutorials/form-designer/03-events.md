# الدرس 3: الأحداث ومعالجاتها

**في هذا الدرس ستتعلم:**

- ما هو **الحدث** (Event) و**معالج الحدث** (Event handler).
- إنشاء معالج بالنقر المزدوج على الأداة، أو من لسان **Events** في نافذة الخصائص.
- أهم الأحداث: `Click` و `Load` و `Change` و `KeyPress` و `DblClick` و `MouseMove`.
- كيف تعرف أي الأحداث لها معالج، وكيف تحذف معالجًا.

## الجرس والباب

**الحدث** شيء يحدث للأداة: ضغطة زر، أو كتابة حرف، أو فتح نافذة. مثل **جرس الباب**: يرن عندما يضغطه أحد.
**معالج الحدث** هو ما تفعله عندما يرن الجرس: تقوم وتفتح الباب. في البرمجة هو إجراء (`Sub`) تكتب فيه الأوامر.

البرنامج المرئي لا يعمل من أعلى إلى أسفل مرة واحدة ثم ينتهي، بل **ينتظر** الأحداث، وكلما حدث شيء نفّذ معالجه. هذا اسمه **البرمجة الموجّهة بالأحداث** (Event-driven programming).

## إنشاء معالج: ثلاث طرق

### 1) النقر المزدوج (الأسرع)

انقر الأداة في المصمم **مرتين**: تفتح البيئة الكود، وتكتب معالج **الحدث الافتراضي** للأداة، وتضع المؤشر داخله:

| الأداة | الحدث الافتراضي | المعالج في BASIC | المعالج في Python |
|---|---|---|---|
| `Button` | Click | `cmdSave_Click()` | `def cmdSave_Click(self):` |
| `TextBox` | Change (TextChanged) | `txtName_Change()` | `def txtName_TextChanged(self):` |
| `CheckBox` | Click (CheckedChanged) | `chkAgree_Click()` | `def chkAgree_CheckedChanged(self):` |
| `ListBox` / `ComboBox` | Click (SelectedIndexChanged) | `lstItems_Click()` | `def lstItems_SelectedIndexChanged(self):` |
| `Timer` | Timer (Tick) | `tmrClock_Timer()` | `def tmrClock_Tick(self):` |
| النموذج نفسه | Load | `Form_Load()` | `def Form1_Load(self):` |

لاحظ أن اسم المعالج = **اسم الأداة** + `_` + **اسم الحدث**. لذلك غيّر اسم الأداة **قبل** النقر المزدوج.
والبيئة تكتب أسماء الأحداث بأسلوب كل لغة: BASIC يستخدم أسماء Visual Basic 6 (`Change`، `Timer`)، و Python يستخدم أسماء Visual Basic 2005 (`TextChanged`، `Tick`).

### 2) لسان Events في نافذة الخصائص

1. حدد الأداة.
2. في نافذة الخصائص انقر لسان **Events** (الأحداث). يظهر جدول: **Event** (الحدث) و **Handler** (المعالج).
3. انقر الحدث الذي تريده **مرتين** (مثل `KeyPress` أو `MouseMove`): يُنشأ المعالج ويفتح الكود.

الأحداث التي لها معالج مكتوب تظهر **بخط عريض**، وعمود Handler يعرض اسمه. انقر حدثًا عريضًا مرتين لتقفز إلى معالجه.

### 3) الكتابة باليد

يمكنك كتابة `Private Sub txtName_KeyPress(KeyAscii As Integer)` بنفسك. المهم أن يطابق الاسم والمعاملات ما تتوقعه اللغة، لذلك الطريقتان الأوليان أضمن.

## أحداث النموذج

- `Load`: قبل ظهور النافذة. مكان مناسب لملء القوائم ووضع القيم الأولية.
- `Resize`: عند تغيير حجم النافذة.
- `Unload` أو `FormClosing`: عند الإغلاق. مكان مناسب لسؤال "هل تريد الحفظ؟".

انقر مكانًا فارغًا من النموذج مرتين لتحصل على معالج `Form_Load`.

## مثال: ثلاثة أحداث في نموذج واحد

- `Form_Load` يكتب قيمة أولية.
- `txtName_Change` يعدّ الحروف مع كل حرف تكتبه.
- `cmdShow_Click` يعرض رسالة.

<!-- test: {"steps": [["set", "txtName", "Text", "هدى"], ["click", "cmdShow"]], "expect": {"lblCount.Caption": "عدد الحروف: 3", "lblStatus.Caption": "جاهز"}, "msgbox": ["مرحبًا يا هدى"]} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "الأحداث"
   ClientWidth     =   4800
   ClientHeight    =   2400
   Begin VB.TextBox txtName
      Left            =   240
      Top             =   240
      Width           =   3000
      Height          =   400
   End
   Begin VB.CommandButton cmdShow
      Caption         =   "اعرض"
      Left            =   3360
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.Label lblCount
      Left            =   240
      Top             =   840
      Width           =   4200
      Height          =   400
   End
   Begin VB.Label lblStatus
      Left            =   240
      Top             =   1440
      Width           =   4200
      Height          =   400
   End
End

Private Sub Form_Load()
    lblStatus.Caption = "جاهز"
    lblCount.Caption = "عدد الحروف: 0"
End Sub

Private Sub txtName_Change()
    lblCount.Caption = "عدد الحروف: " & Len(txtName.Text)
End Sub

Private Sub cmdShow_Click()
    MsgBox "مرحبًا يا " & txtName.Text
End Sub
```

بعد «افتح في المحرر»: حدد `txtName` في المصمم، وافتح لسان **Events**. ستجد `Change` بخط عريض لأن له معالجًا.

## حدث بمعاملات: KeyPress

بعض الأحداث تعطيك معلومات. `KeyPress` يعطيك رمز الحرف المضغوط في `KeyAscii`، وإذا جعلته `0` يُلغى الحرف. هكذا تمنع الحروف في خانة رقم الهاتف:

<!-- test: {"steps": [["key", "txtPhone", "5"], ["key", "txtPhone", "a"]], "keys": [null, "break"], "expect": {"lblInfo.Caption": "مسموح بالأرقام فقط"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "رقم الهاتف"
   ClientWidth     =   4800
   ClientHeight    =   1600
   Begin VB.TextBox txtPhone
      Left            =   240
      Top             =   240
      Width           =   3000
      Height          =   400
   End
   Begin VB.Label lblInfo
      Left            =   240
      Top             =   840
      Width           =   4200
      Height          =   400
   End
End

Private Sub txtPhone_KeyPress(KeyAscii As Integer)
    If KeyAscii >= 32 And (KeyAscii < Asc("0") Or KeyAscii > Asc("9")) Then
        KeyAscii = 0
        lblInfo.Caption = "مسموح بالأرقام فقط"
    End If
End Sub
```

## حذف معالج

احذف الإجراء من الكود (من `Private Sub` إلى `End Sub`). عند الحفظ يختفي الخط العريض من لسان Events. لا تحذف الأداة وتترك معالجها: سيبقى كود "يتيم" لا يستدعيه أحد.

## أخطاء شائعة

- **النقر المزدوج قبل تغيير الاسم:** ينتج `Command1_Click`. إذا غيّرت الاسم بعدها فغيّر اسم المعالج أيضًا.
- **كتابة الكود في معالج الأداة الخطأ:** تأكد من الاسم في سطر `Private Sub`.
- **حلقة لا تنتهي في Change:** إذا غيّرت `txtName.Text` داخل `txtName_Change` نفسه، يُستدعى الحدث مرة أخرى.
- **انتظار Click من Label:** العنوان يستقبل `Click` أيضًا، لكن المستخدم لا يتوقع ذلك. استخدم زرًّا.

## تمرين

### تمرين 1: آلة جمع صغيرة

عند الضغط على `cmdAdd` اعرض في `lblResult` مجموع الرقمين في `txtA` و `txtB` بالشكل: `النتيجة = 15`. استخدم `Val` لتحويل النص إلى رقم.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "جمع"
   ClientWidth     =   4800
   ClientHeight    =   2000
   Begin VB.TextBox txtA
      Left            =   240
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.TextBox txtB
      Left            =   1680
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.CommandButton cmdAdd
      Caption         =   "اجمع"
      Left            =   3120
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.Label lblResult
      Left            =   240
      Top             =   900
      Width           =   4200
      Height          =   400
   End
End

' اكتب معالج cmdAdd_Click
```

<!-- test: {"steps": [["set", "txtA", "Text", "7"], ["set", "txtB", "Text", "8"], ["click", "cmdAdd"]], "expect": {"lblResult.Caption": "النتيجة = 15"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "جمع"
   ClientWidth     =   4800
   ClientHeight    =   2000
   Begin VB.TextBox txtA
      Left            =   240
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.TextBox txtB
      Left            =   1680
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.CommandButton cmdAdd
      Caption         =   "اجمع"
      Left            =   3120
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.Label lblResult
      Left            =   240
      Top             =   900
      Width           =   4200
      Height          =   400
   End
End

Private Sub cmdAdd_Click()
    lblResult.Caption = "النتيجة = " & (Val(txtA.Text) + Val(txtB.Text))
End Sub
```

### مهمة عملية: من لسان Events

1. في مشروع BASIC جديد ضع `TextBox` وسمِّه `txtCity`.
2. حدده، وافتح لسان **Events**، وانقر `DblClick` مرتين.
3. اكتب في المعالج: `MsgBox "نقرت مرتين"`.
4. شغّل البرنامج وانقر المربع مرتين. ثم عد إلى لسان Events ولاحظ الخط العريض.

## اختبر نفسك

```quiz
{"question": "نقرت زرًّا اسمه `btnSave` مرتين في مصمم مشروع BASIC. ما اسم المعالج الذي يُنشأ؟", "choices": ["`Save_Click`", "`btnSave_Click`", "`Click_btnSave`", "`Form_Load`"], "answer": 1, "explanation": "اسم المعالج = اسم الأداة + _ + اسم الحدث."}
```

```quiz
{"question": "كيف تعرف في لسان Events أن حدثًا له معالج؟", "choices": ["يظهر بخط عريض واسم المعالج في عمود Handler", "يظهر بلون أحمر", "يختفي من القائمة", "لا يمكن معرفة ذلك"], "answer": 0, "explanation": "الأحداث التي لها معالج مكتوب تظهر بخط عريض."}
```

```quiz
{"question": "أين تضع الكود الذي يملأ قائمة قبل ظهور النافذة؟", "choices": ["في `Form_Load`", "في `cmdOK_Click`", "في `Form_Unload`", "في ملف `_designer`"], "answer": 0, "explanation": "حدث Load يحدث قبل ظهور النموذج، فهو مكان القيم الأولية."}
```

## الخلاصة

- الحدث = ما يحدث للأداة، والمعالج = ما تفعله عندها.
- النقر المزدوج ينشئ معالج الحدث الافتراضي، ولسان **Events** لبقية الأحداث، والعريض = له معالج.
- اسم المعالج = اسم الأداة + `_` + الحدث، فسمِّ الأداة أولًا.
- `Form_Load` للبداية، و `Click` للأزرار، و `Change` للنصوص، و `KeyPress` للتحكم في المفاتيح.
