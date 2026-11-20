# الدرس 19: الملفات

**في هذا الدرس ستتعلم:**

- لماذا نحتاج الملفات لحفظ البيانات.
- فتح ملف بـ `Open` بأوضاعه الثلاثة: `Output` و`Append` و`Input`.
- الكتابة بـ `Print #` و`Write #`، والقراءة بـ `Line Input #` و`Input #` حتى `EOF`.
- `FreeFile` و`Close` و`App.Path` و`Dir` و`Kill`.

## الذاكرة تنسى والملف يتذكّر

المتغيرات تعيش في **الذاكرة** (RAM)، وتختفي عند إغلاق البرنامج، مثل الكتابة على سبورة تُمسح آخر اليوم.
**الملف** مثل **دفتر** تحفظه في الدرج: تكتب فيه اليوم وتقرؤه غدًا. لكي يتذكر برنامجك قائمة الأسماء أو أعلى نتيجة في لعبة، يجب أن يحفظها في ملف.

## خطوات التعامل مع ملف

مثل استخدام دفتر حقيقي:

1. **احصل على رقم** للملف: `f = FreeFile` (مثل أخذ رقم دور، حتى لا تستخدم رقمًا مشغولًا).
2. **افتح** الدفتر: `Open المسار For الوضع As #f`.
3. **اكتب** أو **اقرأ**.
4. **أغلق** الدفتر: `Close #f`. (مهم جدًّا! بدون الإغلاق قد لا تُحفظ البيانات.)

| الوضع | المعنى |
|---|---|
| `For Output` | كتابة من جديد: **يمسح** الملف القديم إن وُجد |
| `For Append` | إضافة في **آخر** الملف، مع الاحتفاظ بالقديم |
| `For Input` | قراءة فقط (الملف يجب أن يكون موجودًا) |

`App.Path` هو مجلد البرنامج نفسه، وهو مكان مناسب لحفظ ملفات البرنامج: `App.Path & "\notes.txt"`.

## الكتابة والقراءة سطرًا سطرًا

`Print #f, نص` تكتب سطرًا، و`Line Input #f, متغير` تقرأ سطرًا كاملًا. و`EOF(f)` (اختصار End Of File) تصبح `True` عند الوصول لنهاية الملف:

```vb run
Sub Main()
    Dim f As Integer, path As String, lineText As String
    path = App.Path & "\shopping.txt"

    ' 1) كتابة
    f = FreeFile
    Open path For Output As #f
    Print #f, "Bread"
    Print #f, "Milk"
    Print #f, "Eggs"
    Close #f

    ' 2) قراءة حتى نهاية الملف
    f = FreeFile
    Open path For Input As #f
    Do While Not EOF(f)
        Line Input #f, lineText
        Debug.Print "- " & lineText
    Loop
    Close #f
End Sub
```

```text output
- Bread
- Milk
- Eggs
```

## الإضافة: Append

`Output` يمسح القديم، أما `Append` فيضيف في النهاية، مثل دفتر يوميات تكتب كل يوم في صفحة جديدة:

```vb run
Sub Main()
    Dim f As Integer, path As String, lineText As String, count As Integer
    path = App.Path & "\log.txt"

    f = FreeFile
    Open path For Output As #f
    Print #f, "Program started"
    Close #f

    f = FreeFile
    Open path For Append As #f
    Print #f, "User logged in"
    Print #f, "File saved"
    Close #f

    f = FreeFile
    Open path For Input As #f
    Do Until EOF(f)
        Line Input #f, lineText
        count = count + 1
        Debug.Print count & ": " & lineText
    Loop
    Close #f
End Sub
```

```text output
1: Program started
2: User logged in
3: File saved
```

## البيانات المنظّمة: Write # و Input #

إذا أردت حفظ **سجلات** (اسم وعمر مثلًا)، استخدم `Write #`: تكتب القيم مفصولة بفواصل، والنصوص بين علامات تنصيص. ثم تقرؤها `Input #` مباشرة في متغيرات منفصلة بالترتيب نفسه:

```vb run
Sub Main()
    Dim f As Integer, path As String
    Dim personName As String, age As Integer
    path = App.Path & "\people.txt"

    f = FreeFile
    Open path For Output As #f
    Write #f, "Ahmed", 25
    Write #f, "Mona", 31
    Write #f, "Karim", 19
    Close #f

    f = FreeFile
    Open path For Input As #f
    Do While Not EOF(f)
        Input #f, personName, age
        Debug.Print personName & " is " & age & " years old"
    Loop
    Close #f
End Sub
```

```text output
Ahmed is 25 years old
Mona is 31 years old
Karim is 19 years old
```

داخل الملف ستجد السطر هكذا: `"Ahmed",25`.

## هل الملف موجود؟ Dir و Kill

`Dir(المسار)` تُرجع اسم الملف إذا كان موجودًا، أو نصًّا فارغًا إذا لم يكن. و`Kill المسار` تحذف الملف:

```vb run
Sub Main()
    Dim path As String, f As Integer
    path = App.Path & "\temp.txt"

    f = FreeFile
    Open path For Output As #f
    Print #f, "temporary"
    Close #f
    Debug.Print "موجود؟ " & (Dir(path) <> "")

    Kill path
    Debug.Print "بعد الحذف موجود؟ " & (Dir(path) <> "")
End Sub
```

```text output
موجود؟ True
بعد الحذف موجود؟ False
```

وقبل فتح ملف للقراءة تحقّق دائمًا من وجوده، أو استخدم `On Error` (الدرس 18)، لأن فتح ملف غير موجود يعطي الخطأ 53 "File not found".

## حفظ قائمة النموذج واسترجاعها

مثال عملي: قائمة مهام تُحفظ عند الضغط على "احفظ" وتُحمَّل تلقائيًّا في `Form_Load`:

<!-- test: {"steps": [["set", "txtTask", "Text", "Study VB"], ["click", "cmdAdd"], ["set", "txtTask", "Text", "Read a book"], ["click", "cmdAdd"], ["click", "cmdSave"], ["click", "cmdClear"], ["click", "cmdLoad"]], "expect": {"lstTasks.ListCount": "2", "lstTasks.List(1)": "Read a book"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "مهامي"
   ClientWidth     =   5400
   ClientHeight    =   3600
   Begin VB.TextBox txtTask
      Left            =   240
      Top             =   240
      Width           =   3000
      Height          =   400
   End
   Begin VB.CommandButton cmdAdd
      Caption         =   "أضف"
      Left            =   3400
      Top             =   200
      Width           =   1700
      Height          =   500
   End
   Begin VB.ListBox lstTasks
      Left            =   240
      Top             =   900
      Width           =   3000
      Height          =   2400
   End
   Begin VB.CommandButton cmdSave
      Caption         =   "احفظ"
      Left            =   3400
      Top             =   900
      Width           =   1700
      Height          =   500
   End
   Begin VB.CommandButton cmdLoad
      Caption         =   "حمّل"
      Left            =   3400
      Top             =   1500
      Width           =   1700
      Height          =   500
   End
   Begin VB.CommandButton cmdClear
      Caption         =   "امسح القائمة"
      Left            =   3400
      Top             =   2100
      Width           =   1700
      Height          =   500
   End
End

Option Explicit

Private Function DataFile() As String
    DataFile = App.Path & "\tasks.txt"
End Function

Private Sub Form_Load()
    cmdLoad_Click
End Sub

Private Sub cmdAdd_Click()
    If txtTask.Text <> "" Then lstTasks.AddItem txtTask.Text
    txtTask.Text = ""
End Sub

Private Sub cmdSave_Click()
    Dim f As Integer, i As Integer
    f = FreeFile
    Open DataFile() For Output As #f
    For i = 0 To lstTasks.ListCount - 1
        Print #f, lstTasks.List(i)
    Next i
    Close #f
End Sub

Private Sub cmdLoad_Click()
    Dim f As Integer, lineText As String
    lstTasks.Clear
    If Dir(DataFile()) = "" Then Exit Sub      ' لا يوجد ملف بعد
    f = FreeFile
    Open DataFile() For Input As #f
    Do While Not EOF(f)
        Line Input #f, lineText
        lstTasks.AddItem lineText
    Loop
    Close #f
End Sub

Private Sub cmdClear_Click()
    lstTasks.Clear
End Sub
```

لاحظ أن `Form_Load` يستدعي `cmdLoad_Click` مباشرة: إجراء الحدث في النهاية إجراء عادي يمكن استدعاؤه.

> 💡 **ملاحظة عن العربية في الملفات:** أوامر الملفات في فيجوال بيسك 6 تكتب النص بترميز ويندوز المحلي (ANSI). النصوص العربية تُحفظ بشكل صحيح فقط إذا كانت لغة "البرامج غير الداعمة لـ Unicode" في إعدادات ويندوز هي العربية؛ وإلا ستظهر علامات `?`. لذلك استخدمنا بيانات إنجليزية في أمثلة هذا الدرس.

## أخطاء شائعة

- **نسيان `Close`:** قد لا تُحفظ البيانات، ولا يمكن فتح الملف مرة أخرى.
- **استخدام `Output` بدل `Append`:** يمسح كل ما كان في الملف!
- **فتح ملف غير موجود للقراءة:** الخطأ 53. تحقق بـ `Dir` أولًا.
- **القراءة بعد نهاية الملف:** استخدم `Do While Not EOF(f)`، وإلا يظهر الخطأ 62 "Input past end of file".
- **أرقام ملفات ثابتة مثل `#1` في كل مكان:** إذا فتحت ملفين بالرقم نفسه يقع خطأ. استخدم `FreeFile`.
- **اختلاف ترتيب `Write #` و`Input #`:** اقرأ الحقول بالترتيب نفسه الذي كتبتها به.

## تمارين

### تمرين 1: جدول الضرب في ملف

اكتب جدول ضرب العدد 5 (من 1 إلى 5) في ملف `table.txt`، ثم اقرأ الملف واطبع عدد أسطره وآخر سطر فيه.

```vb exercise
Sub Main()
    Dim f As Integer, i As Integer, path As String
    path = App.Path & "\table.txt"
End Sub
```

```vb solution
Sub Main()
    Dim f As Integer, i As Integer, path As String
    Dim lineText As String, count As Integer
    path = App.Path & "\table.txt"
    f = FreeFile
    Open path For Output As #f
    For i = 1 To 5
        Print #f, "5 x " & i & " = " & (5 * i)
    Next i
    Close #f

    f = FreeFile
    Open path For Input As #f
    Do While Not EOF(f)
        Line Input #f, lineText
        count = count + 1
    Loop
    Close #f
    Debug.Print "عدد الأسطر: " & count
    Debug.Print "آخر سطر: " & lineText
End Sub
```

```text output
عدد الأسطر: 5
آخر سطر: 5 x 5 = 25
```

### تمرين 2: مجموع الدرجات من ملف

احفظ بـ `Write #` ثلاثة سجلات (المادة، الدرجة): Math 90، Science 85، English 77، ثم اقرأها بـ `Input #` واطبع المجموع.

```vb exercise
Sub Main()
    Dim f As Integer, path As String
    Dim subject As String, mark As Integer, total As Integer
    path = App.Path & "\marks.txt"
End Sub
```

```vb solution
Sub Main()
    Dim f As Integer, path As String
    Dim subject As String, mark As Integer, total As Integer
    path = App.Path & "\marks.txt"
    f = FreeFile
    Open path For Output As #f
    Write #f, "Math", 90
    Write #f, "Science", 85
    Write #f, "English", 77
    Close #f

    f = FreeFile
    Open path For Input As #f
    Do While Not EOF(f)
        Input #f, subject, mark
        total = total + mark
    Loop
    Close #f
    Debug.Print "المجموع = " & total
End Sub
```

```text output
المجموع = 252
```

## اختبر نفسك

```quiz
{"question": "أي وضع يضيف إلى آخر الملف دون مسح محتواه؟", "choices": ["Output", "Input", "Append", "Binary"], "answer": 2, "explanation": "Append يضيف في النهاية، أما Output فيبدأ الملف من جديد."}
```

```quiz
{"question": "ما وظيفة FreeFile؟", "choices": ["حذف ملف", "إعطاء رقم ملف غير مستخدم", "إغلاق كل الملفات", "معرفة حجم الملف"], "answer": 1, "explanation": "FreeFile تُرجع أول رقم ملف متاح لاستخدامه مع Open."}
```

```quiz
{"question": "ما الذي يجعل حلقة القراءة تتوقف عند نهاية الملف؟", "choices": ["Do While Not EOF(f)", "Do While f > 0", "For i = 1 To EOF", "Loop Until Close"], "answer": 0, "explanation": "EOF(f) تصبح True عند نهاية الملف."}
```

```quiz
{"question": "ماذا تُرجع Dir(path) إذا لم يكن الملف موجودًا؟", "choices": ["0", "False", "نصًّا فارغًا \"\"", "خطأ 53"], "answer": 2, "explanation": "Dir تُرجع اسم الملف إذا وُجد، ونصًّا فارغًا إذا لم يوجد."}
```

## الخلاصة

- `FreeFile` ثم `Open ... For Output/Append/Input As #f` ثم `Close #f`.
- `Print #` و`Line Input #` للأسطر، و`Write #` و`Input #` للسجلات المنظمة.
- `EOF` لنهاية الملف، و`Dir` للتحقق من الوجود، و`Kill` للحذف، و`App.Path` لمجلد البرنامج.
