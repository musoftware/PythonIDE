# الدرس 4: الأدوات الشائعة والمكونات غير المرئية

**في هذا الدرس ستتعلم:**

- متى تستخدم كل أداة من الأدوات الشائعة، وخاصيتها وحدثها الأهم.
- القوائم: `ListBox` و `ComboBox`، والاختيارات: `CheckBox` و `RadioButton` داخل `GroupBox`.
- الحاويات: `Panel` و `GroupBox` و `TabControl`.
- المكونات غير المرئية في الصينية: `Timer` والحوارات.

## علبة العُدّة

لكل أداة وظيفة، مثل أدوات النجار: المطرقة للمسامير والمنشار للخشب. اختيار الأداة الصحيحة يجعل برنامجك سهلًا على مستخدمه.

| الأداة | اسمها في VB6 | متى تستخدمها؟ | الخاصية الأهم | الحدث الأهم |
|---|---|---|---|---|
| `Label` | Label | نص ثابت يقرؤه المستخدم | `Text` (`Caption`) | — |
| `TextBox` | TextBox | المستخدم يكتب نصًا | `Text` | `TextChanged` (`Change`) |
| `Button` | CommandButton | المستخدم يأمر بفعل | `Text` (`Caption`) | `Click` |
| `CheckBox` | CheckBox | نعم / لا مستقلة | `Checked` (`Value`) | `CheckedChanged` (`Click`) |
| `RadioButton` | OptionButton | اختيار **واحد** من عدة | `Checked` (`Value`) | `CheckedChanged` (`Click`) |
| `ListBox` | ListBox | قائمة ظاهرة | `Items`، `SelectedIndex` (`ListIndex`) | `SelectedIndexChanged` (`Click`) |
| `ComboBox` | ComboBox | قائمة منسدلة توفر المساحة | `Items`، `Text` | `SelectedIndexChanged` (`Click`) |
| `PictureBox` | PictureBox | صورة | `Image` (`Picture`) | `Click` |
| `ProgressBar` | ProgressBar | شريط تقدم | `Value` | — |
| `NumericUpDown` | — | رقم بأسهم زيادة ونقص | `Value` | `ValueChanged` |
| `DateTimePicker` | DTPicker | اختيار تاريخ | `Value` | `ValueChanged` |
| `DataGridView` | DataGrid | جدول صفوف وأعمدة | `Rows`، `Columns` | `SelectedIndexChanged` |

## عناصر القوائم في وقت التصميم

لملء `ListBox` أو `ComboBox` بدون كود: حدد الأداة، وفي نافذة الخصائص اختر `Items` واكتب عنصرًا في كل سطر.
أو املأها بالكود في `Form_Load` كما في المثال التالي.

## الحاويات

- **`GroupBox`** (Frame في VB6): إطار بعنوان. أزرار الاختيار داخله تكوّن **مجموعة واحدة**: اختيار أحدها يلغي الآخر.
- **`Panel`**: حاوية بلا عنوان، مفيدة للتجميع ولـ `Dock`.
- **`TabControl`**: صفحات بألسنة. انقر اللسان في المصمم ثم ضع الأدوات في صفحته. أضف الصفحات من خاصية `TabPages`.

لو وضعت زرّي اختيار في `GroupBox` واثنين في آخر، يستطيع المستخدم اختيار واحد من **كل** مجموعة.

## المكونات غير المرئية

بعض الأدوات لا تظهر للمستخدم بل تعمل في الخلفية. عند وضعها تذهب إلى **الصينية** (Tray) تحت النموذج:

| المكون | وظيفته |
|---|---|
| `Timer` | ينفّذ حدث `Tick` (`Timer` في VB6) كل `Interval` ميلي ثانية |
| `MenuStrip` | شريط القوائم (الدرس التالي) |
| `ToolStrip` | شريط أدوات بأزرار. انقره بالزر الأيمن > **Edit Buttons...** (تحرير الأزرار...) |
| `OpenFileDialog` / `SaveFileDialog` | نافذة فتح ملف / حفظ ملف |
| `ColorDialog` / `FontDialog` / `FolderBrowserDialog` | اختيار لون / خط / مجلد |

انقر المكوّن في الصينية لترى خصائصه في نافذة الخصائص كأي أداة.

## مثال: طلب بيتزا

المثال يجمع أدوات كثيرة: `ComboBox` للحجم، و `CheckBox` للإضافات، و `ListBox` للطلبات، وزر يحسب السعر.

<!-- test: {"steps": [["set", "cboSize", "ListIndex", "2"], ["set", "chkCheese", "Value", "1"], ["click", "cmdOrder"]], "expect": {"lblPrice.Caption": "السعر: 130 جنيه", "lstOrders.ListCount": "1", "lstOrders.List(0)": "كبير + جبنة"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "طلب بيتزا"
   ClientWidth     =   5400
   ClientHeight    =   3600
   Begin VB.ComboBox cboSize
      Left            =   240
      Top             =   240
      Width           =   2400
      Height          =   400
   End
   Begin VB.CheckBox chkCheese
      Caption         =   "جبنة إضافية (+20)"
      Left            =   240
      Top             =   840
      Width           =   2400
      Height          =   400
   End
   Begin VB.CommandButton cmdOrder
      Caption         =   "اطلب"
      Left            =   240
      Top             =   1440
      Width           =   1200
      Height          =   400
   End
   Begin VB.Label lblPrice
      Left            =   240
      Top             =   2100
      Width           =   2400
      Height          =   400
   End
   Begin VB.ListBox lstOrders
      Left            =   2880
      Top             =   240
      Width           =   2280
      Height          =   2400
   End
End

Private Sub Form_Load()
    cboSize.AddItem "صغير"
    cboSize.AddItem "وسط"
    cboSize.AddItem "كبير"
    cboSize.ListIndex = 0
End Sub

Private Sub cmdOrder_Click()
    Dim price As Integer
    Dim desc As String
    Select Case cboSize.ListIndex
        Case 0: price = 60
        Case 1: price = 85
        Case 2: price = 110
    End Select
    desc = cboSize.Text
    If chkCheese.Value = vbChecked Then
        price = price + 20
        desc = desc & " + جبنة"
    End If
    lblPrice.Caption = "السعر: " & price & " جنيه"
    lstOrders.AddItem desc
End Sub
```

## أخطاء شائعة

- **أزرار اختيار لا تلغي بعضها:** ليست في حاوية واحدة. ضعها داخل `GroupBox` واحد.
- **`ListIndex = -1`:** يعني "لا شيء محدد". افحصه قبل استخدام العنصر المحدد.
- **`Timer` لا يعمل:** تأكد أن `Enabled = True` وأن `Interval` أكبر من صفر.
- **قائمة منسدلة يكتب فيها المستخدم ما يشاء:** إذا أردت الاختيار فقط فاضبط نمطها على "قائمة منسدلة فقط" (`DropDownStyle` / `Style`).

## تمرين

### تمرين 1: نقل عنصر بين قائمتين

عند الضغط على `cmdMove` انقل العنصر المحدد من `lstLeft` إلى `lstRight`: أضفه إلى اليمنى ثم احذفه من اليسرى بـ `RemoveItem`.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "نقل"
   ClientWidth     =   5400
   ClientHeight    =   2600
   Begin VB.ListBox lstLeft
      Left            =   240
      Top             =   240
      Width           =   2000
      Height          =   2000
   End
   Begin VB.CommandButton cmdMove
      Caption         =   ">>"
      Left            =   2400
      Top             =   900
      Width           =   600
      Height          =   400
   End
   Begin VB.ListBox lstRight
      Left            =   3120
      Top             =   240
      Width           =   2000
      Height          =   2000
   End
End

Private Sub Form_Load()
    lstLeft.AddItem "أحمر"
    lstLeft.AddItem "أخضر"
    lstLeft.AddItem "أزرق"
End Sub

Private Sub cmdMove_Click()
    ' اكتب هنا
End Sub
```

<!-- test: {"steps": [["set", "lstLeft", "ListIndex", "1"], ["click", "cmdMove"]], "expect": {"lstLeft.ListCount": "2", "lstRight.ListCount": "1", "lstRight.List(0)": "أخضر"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "نقل"
   ClientWidth     =   5400
   ClientHeight    =   2600
   Begin VB.ListBox lstLeft
      Left            =   240
      Top             =   240
      Width           =   2000
      Height          =   2000
   End
   Begin VB.CommandButton cmdMove
      Caption         =   ">>"
      Left            =   2400
      Top             =   900
      Width           =   600
      Height          =   400
   End
   Begin VB.ListBox lstRight
      Left            =   3120
      Top             =   240
      Width           =   2000
      Height          =   2000
   End
End

Private Sub Form_Load()
    lstLeft.AddItem "أحمر"
    lstLeft.AddItem "أخضر"
    lstLeft.AddItem "أزرق"
End Sub

Private Sub cmdMove_Click()
    If lstLeft.ListIndex >= 0 Then
        lstRight.AddItem lstLeft.List(lstLeft.ListIndex)
        lstLeft.RemoveItem lstLeft.ListIndex
    End If
End Sub
```

### مهمة عملية: ساعة بمؤقت

1. ضع `Label` باسم `lblClock` و `Timer` باسم `tmrClock` (لاحظ أنه يذهب إلى الصينية).
2. اجعل `Interval` يساوي `1000` و `Enabled` يساوي `True`.
3. انقر المؤقت في الصينية مرتين واكتب: `lblClock.Caption = Time`.
4. شغّل البرنامج: الساعة تتحدث كل ثانية.

## اختبر نفسك

```quiz
{"question": "تريد أن يختار المستخدم جنسًا واحدًا فقط: ذكر أو أنثى. أي أداة تستخدم؟", "choices": ["`CheckBox` مرتين", "`RadioButton` مرتين داخل `GroupBox` واحد", "`TextBox`", "`Timer`"], "answer": 1, "explanation": "أزرار الاختيار في حاوية واحدة لا يُختار منها إلا واحد."}
```

```quiz
{"question": "ماذا يعني `ListIndex = -1`؟", "choices": ["العنصر الأخير محدد", "لا يوجد عنصر محدد", "القائمة ممتلئة", "خطأ في البرنامج"], "answer": 1, "explanation": "-1 تعني أن المستخدم لم يختر شيئًا بعد."}
```

```quiz
{"question": "أين يظهر `OpenFileDialog` في المصمم؟", "choices": ["في وسط النموذج", "في الصينية تحت النموذج", "في شريط القوائم", "لا يظهر"], "answer": 1, "explanation": "الحوارات مكونات غير مرئية، فتظهر في الصينية."}
```

## الخلاصة

- `Label` للعرض، و `TextBox` للكتابة، و `Button` للأوامر، و `CheckBox` لنعم/لا، و `RadioButton` لاختيار واحد.
- `ListBox` و `ComboBox` للقوائم: `AddItem` و `ListIndex` و `List(i)` و `RemoveItem`.
- `GroupBox` و `Panel` و `TabControl` حاويات، وأزرار الاختيار داخل حاوية واحدة مجموعة واحدة.
- `Timer` والحوارات و `MenuStrip` في الصينية تحت النموذج.
