# الدرس 14: القوائم والاختيارات

**في هذا الدرس ستتعلم:**

- **مربع القائمة** (ListBox): إضافة العناصر وحذفها ومعرفة المحدد منها.
- **القائمة المنسدلة** (ComboBox).
- **مربع الاختيار** (CheckBox) للخيارات المستقلة.
- **زر الخيار** (OptionButton) لاختيار واحد من عدة، و**الإطار** (Frame) لتجميعها.

## ListBox: قائمة المشتريات

مربع القائمة مثل ورقة قائمة المشتريات: تضيف إليها عناصر، وتشطب منها، وتعرف عدد ما فيها.

| الخاصية / الطريقة | الوظيفة |
|---|---|
| `AddItem "نص"` | إضافة عنصر في آخر القائمة |
| `RemoveItem i` | حذف العنصر رقم i |
| `Clear` | مسح كل العناصر |
| `ListCount` | عدد العناصر |
| `ListIndex` | رقم العنصر المحدد (**-1** إذا لم يُحدد شيء) |
| `List(i)` | نص العنصر رقم i |
| `Text` | نص العنصر المحدد |

> ⚠️ ترقيم عناصر القائمة يبدأ من **0**، مثل المصفوفات.

<!-- test: {"steps": [["set", "txtItem", "Text", "خبز"], ["click", "cmdAdd"], ["set", "txtItem", "Text", "لبن"], ["click", "cmdAdd"], ["set", "txtItem", "Text", "جبن"], ["click", "cmdAdd"], ["set", "lstItems", "ListIndex", "1"], ["click", "cmdRemove"]], "expect": {"lstItems.ListCount": "2", "lblCount.Caption": "عدد العناصر: 2"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "قائمة المشتريات"
   ClientWidth     =   5400
   ClientHeight    =   3600
   Begin VB.TextBox txtItem
      Left            =   240
      Top             =   240
      Width           =   2600
      Height          =   400
   End
   Begin VB.CommandButton cmdAdd
      Caption         =   "أضف"
      Left            =   3000
      Top             =   200
      Width           =   1000
      Height          =   500
   End
   Begin VB.CommandButton cmdRemove
      Caption         =   "احذف"
      Left            =   4100
      Top             =   200
      Width           =   1000
      Height          =   500
   End
   Begin VB.ListBox lstItems
      Left            =   240
      Top             =   900
      Width           =   2600
      Height          =   2000
   End
   Begin VB.Label lblCount
      Left            =   3000
      Top             =   900
      Width           =   2200
      Height          =   400
   End
End

Option Explicit

Private Sub UpdateCount()
    lblCount.Caption = "عدد العناصر: " & lstItems.ListCount
End Sub

Private Sub cmdAdd_Click()
    If Trim(txtItem.Text) <> "" Then
        lstItems.AddItem txtItem.Text
        txtItem.Text = ""
        UpdateCount
    End If
End Sub

Private Sub cmdRemove_Click()
    If lstItems.ListIndex = -1 Then
        MsgBox "اختر عنصرًا أولًا"
    Else
        lstItems.RemoveItem lstItems.ListIndex
        UpdateCount
    End If
End Sub
```

### المرور على كل العناصر

نستخدم حلقة من 0 إلى `ListCount - 1`:

<!-- test: {"steps": [["click", "cmdTotal"]], "expect": {"lblTotal.Caption": "الإجمالي: 60"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "مجموع القائمة"
   ClientWidth     =   4800
   ClientHeight    =   3000
   Begin VB.ListBox lstPrices
      Left            =   240
      Top             =   240
      Width           =   2000
      Height          =   2000
   End
   Begin VB.CommandButton cmdTotal
      Caption         =   "اجمع"
      Left            =   2600
      Top             =   240
      Width           =   1400
      Height          =   500
   End
   Begin VB.Label lblTotal
      Left            =   2600
      Top             =   1000
      Width           =   2000
      Height          =   400
   End
End

Private Sub Form_Load()
    lstPrices.AddItem "10"
    lstPrices.AddItem "20"
    lstPrices.AddItem "30"
End Sub

Private Sub cmdTotal_Click()
    Dim i As Integer, total As Double
    For i = 0 To lstPrices.ListCount - 1
        total = total + Val(lstPrices.List(i))
    Next i
    lblTotal.Caption = "الإجمالي: " & total
End Sub
```

## ComboBox: القائمة المنسدلة

القائمة المنسدلة توفّر المساحة: تُظهر عنصرًا واحدًا، وعند النقر تنفتح بقية العناصر. لها طرق `ListBox` نفسها (`AddItem` و`ListIndex` و`Text`...).
إذا ضبطت خاصية `Style = 2` (Dropdown List) لا يستطيع المستخدم كتابة نص من عنده، بل يختار من القائمة فقط. وحدث `Click` يقع عند اختيار عنصر:

<!-- test: {"steps": [["set", "cboCity", "ListIndex", "2"]], "expect": {"lblInfo.Caption": "اخترت: أسوان (رقم 2)"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "اختر مدينتك"
   ClientWidth     =   4800
   ClientHeight    =   1800
   Begin VB.ComboBox cboCity
      Style           =   2
      Left            =   240
      Top             =   240
      Width           =   2600
      Height          =   400
   End
   Begin VB.Label lblInfo
      Left            =   240
      Top             =   1000
      Width           =   4200
      Height          =   400
   End
End

Private Sub Form_Load()
    cboCity.AddItem "القاهرة"
    cboCity.AddItem "الإسكندرية"
    cboCity.AddItem "أسوان"
    cboCity.ListIndex = 0          ' اختر أول عنصر مبدئيًّا
End Sub

Private Sub cboCity_Click()
    lblInfo.Caption = "اخترت: " & cboCity.Text & " (رقم " & cboCity.ListIndex & ")"
End Sub
```

## CheckBox و OptionButton و Frame

- **مربع الاختيار** (CheckBox): خيارات **مستقلة**، يمكن تحديد أي عدد منها. مثل إضافات البيتزا: جبن، زيتون، فلفل. خاصيته `Value`: `vbChecked` (1) أو `vbUnchecked` (0).
- **زر الخيار** (OptionButton): اختيار **واحد فقط** من مجموعة، مثل حجم البيتزا: صغير أو وسط أو كبير. خاصيته `Value`: `True` أو `False`.
- **الإطار** (Frame): صندوق يجمع أزرار الخيار. كل إطار مجموعة مستقلة، فيمكنك اختيار حجم من إطار ونوع عجينة من إطار آخر.

<!-- test: {"steps": [["set", "optLarge", "Value", "True"], ["set", "chkCheese", "Value", "1"], ["set", "chkOlives", "Value", "1"], ["click", "cmdOrder"]], "expect": {"lblPrice.Caption": "السعر: 140 جنيه"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "اطلب البيتزا"
   ClientWidth     =   5400
   ClientHeight    =   3400
   Begin VB.Frame fraSize
      Caption         =   "الحجم"
      Left            =   240
      Top             =   240
      Width           =   2400
      Height          =   1800
      Begin VB.OptionButton optSmall
         Caption         =   "صغير (60)"
         Left            =   200
         Top             =   350
         Width           =   2000
         Height          =   350
         Value           =   -1  'True
      End
      Begin VB.OptionButton optMedium
         Caption         =   "وسط (80)"
         Left            =   200
         Top             =   800
         Width           =   2000
         Height          =   350
      End
      Begin VB.OptionButton optLarge
         Caption         =   "كبير (100)"
         Left            =   200
         Top             =   1250
         Width           =   2000
         Height          =   350
      End
   End
   Begin VB.Frame fraExtras
      Caption         =   "إضافات (20 لكل إضافة)"
      Left            =   2800
      Top             =   240
      Width           =   2400
      Height          =   1800
      Begin VB.CheckBox chkCheese
         Caption         =   "جبن"
         Left            =   200
         Top             =   350
         Width           =   2000
         Height          =   350
      End
      Begin VB.CheckBox chkOlives
         Caption         =   "زيتون"
         Left            =   200
         Top             =   800
         Width           =   2000
         Height          =   350
      End
      Begin VB.CheckBox chkPepper
         Caption         =   "فلفل"
         Left            =   200
         Top             =   1250
         Width           =   2000
         Height          =   350
      End
   End
   Begin VB.CommandButton cmdOrder
      Caption         =   "احسب السعر"
      Left            =   240
      Top             =   2300
      Width           =   2000
      Height          =   500
   End
   Begin VB.Label lblPrice
      Left            =   2800
      Top             =   2350
      Width           =   2400
      Height          =   400
   End
End

Option Explicit

Private Sub cmdOrder_Click()
    Dim price As Integer
    If optSmall.Value Then price = 60
    If optMedium.Value Then price = 80
    If optLarge.Value Then price = 100
    If chkCheese.Value = vbChecked Then price = price + 20
    If chkOlives.Value = vbChecked Then price = price + 20
    If chkPepper.Value = vbChecked Then price = price + 20
    lblPrice.Caption = "السعر: " & price & " جنيه"
End Sub
```

لاحظ: `If optSmall.Value Then` تكفي، لأن `Value` نفسها `True` أو `False`، ولا داعي لكتابة `= True`.

### حدث Click لمربع الاختيار

مربع الاختيار يطلق حدث `Click` كلما تغيّرت حالته. مثال مشهور: زر "التالي" لا يعمل إلا بعد الموافقة على الشروط:

<!-- test: {"steps": [["set", "chkAgree", "Value", "1"]], "expect": {"cmdNext.Enabled": "True", "lblState.Caption": "شكرًا لموافقتك"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "الشروط والأحكام"
   ClientWidth     =   4800
   ClientHeight    =   2200
   Begin VB.CheckBox chkAgree
      Caption         =   "أوافق على الشروط"
      Left            =   240
      Top             =   240
      Width           =   3000
      Height          =   400
   End
   Begin VB.CommandButton cmdNext
      Caption         =   "التالي"
      Enabled         =   0   'False
      Left            =   240
      Top             =   800
      Width           =   1600
      Height          =   500
   End
   Begin VB.Label lblState
      Left            =   240
      Top             =   1500
      Width           =   4200
      Height          =   400
   End
End

Private Sub chkAgree_Click()
    cmdNext.Enabled = (chkAgree.Value = vbChecked)
    If chkAgree.Value = vbChecked Then
        lblState.Caption = "شكرًا لموافقتك"
    Else
        lblState.Caption = ""
    End If
End Sub
```

## أخطاء شائعة

- **استخدام `ListIndex` بدون التحقق من -1:** `lst.RemoveItem lst.ListIndex` بدون تحديد عنصر تعطي خطأ.
- **الحلقة حتى `ListCount` بدل `ListCount - 1`:** آخر فهرس هو `ListCount - 1`.
- **حذف عناصر داخل حلقة تصاعدية:** عند حذف عنصر تتحرك العناصر التالية للأمام فتتخطى بعضها. احذف بحلقة تنازلية `Step -1`.
- **مقارنة CheckBox بـ True:** قيمة مربع الاختيار 0 أو 1 (أو 2 للحالة الرمادية)، فقارنها بـ `vbChecked`.
- **وضع كل أزرار الخيار مباشرة على النموذج** مع أنها مجموعتان مختلفتان: استخدم إطارًا لكل مجموعة.

## تمارين

### تمرين 1: أطول اسم

عند الضغط على `cmdLongest` اعرض في `lblResult` أطول اسم في القائمة `lstNames` (التي تُملأ في `Form_Load`).

```vb form exercise
Begin VB.Form Form1
   Caption         =   "أطول اسم"
   ClientWidth     =   4800
   ClientHeight    =   3000
   Begin VB.ListBox lstNames
      Left            =   240
      Top             =   240
      Width           =   2000
      Height          =   2000
   End
   Begin VB.CommandButton cmdLongest
      Caption         =   "ابحث"
      Left            =   2600
      Top             =   240
      Width           =   1400
      Height          =   500
   End
   Begin VB.Label lblResult
      Left            =   2600
      Top             =   1000
      Width           =   2000
      Height          =   400
   End
End

Private Sub Form_Load()
    lstNames.AddItem "Ali"
    lstNames.AddItem "Abdelrahman"
    lstNames.AddItem "Mona"
End Sub

Private Sub cmdLongest_Click()

End Sub
```

<!-- test: {"steps": [["click", "cmdLongest"]], "expect": {"lblResult.Caption": "Abdelrahman"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "أطول اسم"
   ClientWidth     =   4800
   ClientHeight    =   3000
   Begin VB.ListBox lstNames
      Left            =   240
      Top             =   240
      Width           =   2000
      Height          =   2000
   End
   Begin VB.CommandButton cmdLongest
      Caption         =   "ابحث"
      Left            =   2600
      Top             =   240
      Width           =   1400
      Height          =   500
   End
   Begin VB.Label lblResult
      Left            =   2600
      Top             =   1000
      Width           =   2000
      Height          =   400
   End
End

Private Sub Form_Load()
    lstNames.AddItem "Ali"
    lstNames.AddItem "Abdelrahman"
    lstNames.AddItem "Mona"
End Sub

Private Sub cmdLongest_Click()
    Dim i As Integer, best As String
    For i = 0 To lstNames.ListCount - 1
        If Len(lstNames.List(i)) > Len(best) Then best = lstNames.List(i)
    Next i
    lblResult.Caption = best
End Sub
```

### تمرين 2: نقل بين قائمتين

نموذج فيه قائمتان `lstLeft` و`lstRight`، وزر `cmdMove` ينقل العنصر المحدد من اليسرى إلى اليمنى.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "نقل"
   ClientWidth     =   5400
   ClientHeight    =   3000
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
      Height          =   500
   End
   Begin VB.ListBox lstRight
      Left            =   3150
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

End Sub
```

<!-- test: {"steps": [["set", "lstLeft", "ListIndex", "1"], ["click", "cmdMove"]], "expect": {"lstLeft.ListCount": "2", "lstRight.ListCount": "1", "lstRight.List(0)": "أخضر"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "نقل"
   ClientWidth     =   5400
   ClientHeight    =   3000
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
      Height          =   500
   End
   Begin VB.ListBox lstRight
      Left            =   3150
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
        lstRight.AddItem lstLeft.Text
        lstLeft.RemoveItem lstLeft.ListIndex
    End If
End Sub
```

## اختبر نفسك

```quiz
{"question": "ما قيمة ListIndex إذا لم يُحدد أي عنصر؟", "choices": ["0", "-1", "1", "Empty"], "answer": 1, "explanation": "ListIndex = -1 تعني لا يوجد عنصر محدد."}
```

```quiz
{"question": "أي أداة تناسب اختيار \"الجنس: ذكر / أنثى\"؟", "choices": ["CheckBox", "OptionButton", "ListBox", "TextBox"], "answer": 1, "explanation": "الاختيار واحد فقط من عدة خيارات، فنستخدم أزرار الخيار."}
```

```quiz
{"question": "ما فائدة الإطار (Frame) مع أزرار الخيار؟", "choices": ["تلوينها", "جعل كل مجموعة مستقلة باختيار واحد خاص بها", "حذفها", "تكبير الخط"], "answer": 1, "explanation": "أزرار الخيار داخل كل إطار تشكّل مجموعة مستقلة."}
```

```quiz
{"question": "قائمة فيها 5 عناصر. ما فهرس آخر عنصر؟", "choices": ["5", "4", "6", "-1"], "answer": 1, "explanation": "الترقيم من 0، فآخر فهرس هو ListCount - 1 = 4."}
```

## الخلاصة

- `ListBox` و`ComboBox`: `AddItem` و`RemoveItem` و`Clear` و`ListIndex` و`List(i)` و`ListCount`.
- `CheckBox` لخيارات مستقلة (`vbChecked`)، و`OptionButton` لاختيار واحد (`True`).
- `Frame` يجمع أزرار الخيار في مجموعات مستقلة.
