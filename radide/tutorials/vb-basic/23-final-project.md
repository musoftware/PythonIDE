# الدرس 23: المشروع النهائي - دفتر العناوين

**في هذا الدرس:**

سنبني برنامجًا كاملًا يجمع أغلب ما تعلمته: **دفتر عناوين** يحفظ أسماء وأرقام هواتف، ويبحث فيها، ويحفظها في ملف ويسترجعها.

| ما تعلمته | أين يظهر في المشروع |
|---|---|
| النماذج والأدوات (13، 14) | مربعات النص، والقائمة، والأزرار |
| القوائم (17) | قائمة "ملف" وقائمة "مساعدة" |
| الأصناف (22) | الصنف `CContact` لكل جهة اتصال |
| المجموعات (21) | مجموعة `contacts` تحفظ كل الجهات |
| النصوص (10) | البحث بـ `InStr` و`LCase` |
| الملفات (19) | الحفظ بـ `Write #` والتحميل بـ `Input #` |
| معالجة الأخطاء (18) | حماية الحفظ والتحميل |
| الإجراءات والنطاق (11، 12) | إجراءات مساعدة ومتغيرات على مستوى النموذج |

## خطة العمل

قبل الكتابة، يخطط المبرمج المحترف مثل المهندس قبل البناء:

1. **البيانات:** كل جهة اتصال لها اسم وهاتف، فنصنع الصنف `CContact` بهاتين الخاصيتين، مع دالة `Display` تُرجع النص الذي يظهر في القائمة.
2. **التخزين في الذاكرة:** مجموعة `contacts` على مستوى النموذج.
3. **الواجهة:** مربعا نص (`txtName` و`txtPhone`)، وقائمة `lstContacts`، وأزرار: إضافة، حذف، بحث، وعنوان حالة `lblStatus`.
4. **الملف:** `contacts.txt` في مجلد البرنامج، كل سطر فيه `"الاسم","الهاتف"`.
5. **الإجراءات المساعدة:** `RefreshList` تعيد ملء القائمة من المجموعة، و`SaveContacts` و`LoadContacts` للملف.

## الصنف `CContact`

```vb
Option Explicit
Private mName As String
Private mPhone As String

Public Property Get FullName() As String
    FullName = mName
End Property

Public Property Let FullName(ByVal value As String)
    mName = Trim(value)
End Property

Public Property Get Phone() As String
    Phone = mPhone
End Property

Public Property Let Phone(ByVal value As String)
    mPhone = Trim(value)
End Property

Public Function Display() As String
    Display = mName & " - " & mPhone
End Function

Public Function Matches(ByVal text As String) As Boolean
    Matches = InStr(LCase(mName & " " & mPhone), LCase(text)) > 0
End Function
```

`Matches` تخبرنا هل جهة الاتصال تحتوي نص البحث في الاسم أو الهاتف، دون اعتبار حالة الحروف.

## البرنامج الكامل

اضغط **جرّبه**: سيُنشأ مشروع فيه النموذج `Form1` والصنف `CContact.cls`. أضف بعض الأسماء، ثم احفظ من قائمة **ملف**، وأغلق البرنامج وافتحه من جديد: ستجد الأسماء محمّلة!

<!-- test: {"steps": [["set", "txtName", "Text", "Ahmed Ali"], ["set", "txtPhone", "Text", "0100111"], ["click", "cmdAdd"], ["set", "txtName", "Text", "Mona Hassan"], ["set", "txtPhone", "Text", "0122333"], ["click", "cmdAdd"], ["set", "txtName", "Text", ""], ["click", "cmdAdd"], ["menu", "mnuFileSave"], ["menu", "mnuFileNew"], ["menu", "mnuFileOpen"], ["set", "txtSearch", "Text", "mona"], ["click", "cmdSearch"]], "expect": {"lstContacts.ListCount": "1", "lstContacts.List(0)": "Mona Hassan - 0122333", "lblStatus.Caption": "نتائج البحث: 1"}, "msgbox": ["اكتب الاسم ورقم الهاتف"]} -->
```vb form run
'#file: Form1.frm
Begin VB.Form Form1
   Caption         =   "دفتر العناوين"
   ClientWidth     =   6600
   ClientHeight    =   4800
   Begin VB.Label lblName
      Caption         =   "الاسم:"
      Left            =   240
      Top             =   240
      Width           =   1000
      Height          =   400
   End
   Begin VB.TextBox txtName
      Left            =   1300
      Top             =   200
      Width           =   2800
      Height          =   400
   End
   Begin VB.Label lblPhone
      Caption         =   "الهاتف:"
      Left            =   240
      Top             =   760
      Width           =   1000
      Height          =   400
   End
   Begin VB.TextBox txtPhone
      Left            =   1300
      Top             =   720
      Width           =   2800
      Height          =   400
   End
   Begin VB.CommandButton cmdAdd
      Caption         =   "أضف"
      Left            =   4400
      Top             =   200
      Width           =   1900
      Height          =   450
   End
   Begin VB.CommandButton cmdDelete
      Caption         =   "احذف المحدد"
      Left            =   4400
      Top             =   720
      Width           =   1900
      Height          =   450
   End
   Begin VB.TextBox txtSearch
      Left            =   240
      Top             =   1350
      Width           =   3860
      Height          =   400
   End
   Begin VB.CommandButton cmdSearch
      Caption         =   "ابحث"
      Left            =   4400
      Top             =   1320
      Width           =   900
      Height          =   450
   End
   Begin VB.CommandButton cmdShowAll
      Caption         =   "الكل"
      Left            =   5400
      Top             =   1320
      Width           =   900
      Height          =   450
   End
   Begin VB.ListBox lstContacts
      Left            =   240
      Top             =   1900
      Width           =   6060
      Height          =   2200
   End
   Begin VB.Label lblStatus
      Left            =   240
      Top             =   4250
      Width           =   6060
      Height          =   400
   End
   Begin VB.Menu mnuFile
      Caption         =   "ملف"
      Begin VB.Menu mnuFileNew
         Caption         =   "دفتر جديد"
      End
      Begin VB.Menu mnuFileOpen
         Caption         =   "تحميل"
      End
      Begin VB.Menu mnuFileSave
         Caption         =   "حفظ"
      End
      Begin VB.Menu mnuFileSep
         Caption         =   "-"
      End
      Begin VB.Menu mnuFileExit
         Caption         =   "خروج"
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

Private contacts As New Collection        ' كل جهات الاتصال (كائنات CContact)

' ---------------------------------------------------------- إجراءات مساعدة
Private Function DataFile() As String
    DataFile = App.Path & "\contacts.txt"
End Function

Private Sub RefreshList(Optional ByVal filter As String = "")
    Dim c As CContact, shown As Integer
    lstContacts.Clear
    For Each c In contacts
        If filter = "" Or c.Matches(filter) Then
            lstContacts.AddItem c.Display()
            shown = shown + 1
        End If
    Next c
    If filter = "" Then
        lblStatus.Caption = "عدد جهات الاتصال: " & contacts.Count
    Else
        lblStatus.Caption = "نتائج البحث: " & shown
    End If
End Sub

Private Sub SaveContacts()
    Dim f As Integer, c As CContact
    On Error GoTo Failed
    f = FreeFile
    Open DataFile() For Output As #f
    For Each c In contacts
        Write #f, c.FullName, c.Phone
    Next c
    Close #f
    lblStatus.Caption = "تم الحفظ (" & contacts.Count & ")"
    Exit Sub
Failed:
    MsgBox "تعذّر الحفظ: " & Err.Description, vbCritical
End Sub

Private Sub LoadContacts()
    Dim f As Integer, n As String, p As String, c As CContact
    Set contacts = New Collection
    If Dir(DataFile()) <> "" Then
        On Error GoTo Failed
        f = FreeFile
        Open DataFile() For Input As #f
        Do While Not EOF(f)
            Input #f, n, p
            Set c = New CContact
            c.FullName = n
            c.Phone = p
            contacts.Add c
        Loop
        Close #f
    End If
    RefreshList
    Exit Sub
Failed:
    MsgBox "تعذّر تحميل الملف: " & Err.Description, vbCritical
End Sub

' ---------------------------------------------------------- الأحداث
Private Sub Form_Load()
    LoadContacts
End Sub

Private Sub cmdAdd_Click()
    Dim c As CContact
    If Trim(txtName.Text) = "" Or Trim(txtPhone.Text) = "" Then
        MsgBox "اكتب الاسم ورقم الهاتف", vbExclamation
        Exit Sub
    End If
    Set c = New CContact
    c.FullName = txtName.Text
    c.Phone = txtPhone.Text
    contacts.Add c
    txtName.Text = ""
    txtPhone.Text = ""
    RefreshList
End Sub

Private Sub cmdDelete_Click()
    Dim i As Integer
    i = lstContacts.ListIndex
    If i = -1 Then
        MsgBox "اختر جهة اتصال من القائمة أولًا"
    ElseIf txtSearch.Text <> "" Then
        MsgBox "اضغط ""الكل"" قبل الحذف"
    Else
        contacts.Remove i + 1                  ' القائمة تبدأ من 0 والمجموعة من 1
        RefreshList
    End If
End Sub

Private Sub cmdSearch_Click()
    RefreshList Trim(txtSearch.Text)
End Sub

Private Sub cmdShowAll_Click()
    txtSearch.Text = ""
    RefreshList
End Sub

Private Sub mnuFileNew_Click()
    Set contacts = New Collection
    RefreshList
End Sub

Private Sub mnuFileOpen_Click()
    LoadContacts
End Sub

Private Sub mnuFileSave_Click()
    SaveContacts
End Sub

Private Sub mnuFileExit_Click()
    Unload Me
End Sub

Private Sub mnuHelpAbout_Click()
    MsgBox "دفتر العناوين - المشروع النهائي لدورة BASIC", vbInformation, "حول"
End Sub

'#file: CContact.cls
Option Explicit
Private mName As String
Private mPhone As String

Public Property Get FullName() As String
    FullName = mName
End Property

Public Property Let FullName(ByVal value As String)
    mName = Trim(value)
End Property

Public Property Get Phone() As String
    Phone = mPhone
End Property

Public Property Let Phone(ByVal value As String)
    mPhone = Trim(value)
End Property

Public Function Display() As String
    Display = mName & " - " & mPhone
End Function

Public Function Matches(ByVal text As String) As Boolean
    Matches = InStr(LCase(mName & " " & mPhone), LCase(text)) > 0
End Function
```

## شرح أهم الأفكار

- **مصدر واحد للحقيقة:** البيانات الحقيقية في المجموعة `contacts`، والقائمة على الشاشة مجرد "عرض" لها. لذلك بعد أي تغيير نستدعي `RefreshList` لإعادة رسم القائمة من المجموعة.
- **`ListIndex + 1`:** القائمة ترقّم من 0، والمجموعة من 1. هذا الفرق مصدر خطأ مشهور جدًّا.
- **الحذف أثناء البحث ممنوع:** عند البحث تعرض القائمة جزءًا من الجهات فقط، فلا يتطابق رقم السطر مع رقم العنصر في المجموعة. لذلك نطلب من المستخدم عرض الكل أولًا (ويمكنك تحسين ذلك في التمارين).
- **`Optional ByVal filter`:** الإجراء نفسه يعرض الكل أو نتائج البحث فقط (الدرس 11).
- **`""` داخل النص:** لكتابة علامة تنصيص داخل نص نكررها مرتين: `"اضغط ""الكل"""`.

## اختبر البرنامج بنفسك

جرّب هذه الخطوات وتأكد أن كل شيء يعمل:

1. أضف ثلاث جهات اتصال.
2. اضغط "أضف" ومربع الاسم فارغ: يجب أن تظهر رسالة تنبيه.
3. ابحث عن جزء من اسم، ثم اضغط "الكل".
4. احذف جهة اتصال.
5. احفظ من **ملف > حفظ**، ثم **ملف > دفتر جديد** (تفرغ القائمة)، ثم **ملف > تحميل**: تعود الجهات.
6. أغلق البرنامج وشغّله مرة أخرى: تُحمَّل الجهات تلقائيًّا.

> 💡 تذكّر ملاحظة الدرس 19: إذا كتبت الأسماء بالعربية، تُحفظ في الملف بشكل صحيح فقط عندما تكون لغة البرامج غير الداعمة لـ Unicode في ويندوز هي العربية.

## تمارين التطوير

### تمرين 1: منع التكرار

عدّل البرنامج بحيث لا يقبل إضافة رقم هاتف موجود مسبقًا. اكتب أولًا دالة `PhoneExists(phone)` تمر على المجموعة. جرّبها في هذا البرنامج الصغير قبل نقلها للمشروع:

```vb exercise
'#file: Module1.bas
Private phones As New Collection

Sub Main()
    phones.Add "0100111"
    phones.Add "0122333"
    Debug.Print PhoneExists("0122333")
    Debug.Print PhoneExists("0999999")
End Sub

Function PhoneExists(ByVal phone As String) As Boolean
    ' مُرّ على phones بـ For Each
End Function
```

```vb solution
'#file: Module1.bas
Private phones As New Collection

Sub Main()
    phones.Add "0100111"
    phones.Add "0122333"
    Debug.Print PhoneExists("0122333")
    Debug.Print PhoneExists("0999999")
End Sub

Function PhoneExists(ByVal phone As String) As Boolean
    Dim p As Variant
    PhoneExists = False                 ' نبدأ بافتراض أنه غير موجود
    For Each p In phones
        If p = Trim(phone) Then
            PhoneExists = True
            Exit Function
        End If
    Next p
End Function
```

```text output
True
False
```

في المشروع، استبدل `phones` بـ `contacts` وقارن بـ `c.Phone`، ثم في `cmdAdd_Click` اكتب: `If PhoneExists(txtPhone.Text) Then MsgBox "الرقم موجود": Exit Sub`.

### تمرين 2: الترتيب الأبجدي

اكتب إجراء يرتّب مصفوفة أسماء أبجديًّا بطريقة **الفقاعات** (Bubble Sort): قارن كل عنصرين متجاورين وبدّلهما إذا كان الأول أكبر، وكرّر ذلك. ثم يمكنك استخدام الفكرة نفسها لترتيب جهات الاتصال قبل عرضها.

```vb exercise
Sub Main()
    Dim names As Variant, i As Integer
    names = Array("Mona", "Ahmed", "Zeinab", "Karim")
    SortNames names
    For i = 0 To UBound(names)
        Debug.Print names(i)
    Next i
End Sub

Sub SortNames(arr As Variant)
    ' حلقتان متداخلتان + تبديل
End Sub
```

```vb solution
Sub Main()
    Dim names As Variant, i As Integer
    names = Array("Mona", "Ahmed", "Zeinab", "Karim")
    SortNames names
    For i = 0 To UBound(names)
        Debug.Print names(i)
    Next i
End Sub

Sub SortNames(arr As Variant)
    Dim i As Integer, j As Integer, tmp As Variant
    For i = 0 To UBound(arr) - 1
        For j = 0 To UBound(arr) - 1 - i
            If arr(j) > arr(j + 1) Then
                tmp = arr(j)
                arr(j) = arr(j + 1)
                arr(j + 1) = tmp
            End If
        Next j
    Next i
End Sub
```

```text output
Ahmed
Karim
Mona
Zeinab
```

### تمرين 3 (تحدٍّ): حذف آمن أثناء البحث

بدل منع الحذف أثناء البحث، احفظ لكل سطر في القائمة رقم العنصر الحقيقي في المجموعة (مثلًا في مصفوفة `shownIndex()` تملؤها `RefreshList`)، واستخدمها في `cmdDelete_Click`. هذا التمرين بلا حل جاهز: إنه مشروعك أنت!

## اختبر نفسك

```quiz
{"question": "لماذا نكتب contacts.Remove i + 1 وليس i؟", "choices": ["خطأ مطبعي", "لأن ترقيم القائمة من 0 وترقيم المجموعة من 1", "لحذف عنصرين", "لأن Remove تحذف التالي"], "answer": 1, "explanation": "ListIndex يبدأ من 0 بينما عناصر Collection تبدأ من 1."}
```

```quiz
{"question": "ما فائدة الإجراء RefreshList؟", "choices": ["حفظ الملف", "إعادة رسم القائمة من المجموعة بعد أي تغيير", "حذف كل شيء", "تغيير الألوان"], "answer": 1, "explanation": "المجموعة هي مصدر البيانات، والقائمة تُعاد كتابتها منها."}
```

```quiz
{"question": "كيف تكتب علامة تنصيص داخل نص في BASIC؟", "choices": ["\\\"", "\"\" (مرتين)", "'", "Chr(0)"], "answer": 1, "explanation": "تكرار علامة التنصيص مرتين داخل النص يكتب علامة واحدة."}
```

## ماذا بعد؟

مبروك! أنهيت دورة BASIC. الآن تعرف المتغيرات، والشروط، والحلقات، والمصفوفات، والدوال، والنماذج، والملفات، والأصناف. هذه الأفكار نفسها موجودة في كل لغات البرمجة تقريبًا.
اقتراحات للخطوة التالية:

- طوّر دفتر العناوين: أضف بريدًا إلكترونيًّا، أو ترتيبًا، أو تصديرًا إلى ملف CSV.
- اصنع مشاريعك: آلة حاسبة علمية، لعبة "خمّن الرقم" بـ `Rnd`، أو برنامج لإدارة مصروفاتك.
- ابدأ دورة **C++** في RAD IDE: ستجد أن أغلب الأفكار مألوفة لك، مع صيغة كتابة مختلفة.
