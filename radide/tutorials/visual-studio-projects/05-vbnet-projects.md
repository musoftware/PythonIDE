# الدرس 5: مشاريع VB.NET (.vbproj)

إذا كنت تعرف **Visual Basic 6** أو **VB.NET**، فأنت في بيتك: RAD IDE تفتح مشاريع `.vbproj` في مكانها، وتصمم نماذجها، وتبنيها وتشغّلها وتصحح أخطاءها، تمامًا مثل مشاريع C#.

> **تشبيه:** C# وVB.NET مثل **لهجتين للغة واحدة**: الكلمات مختلفة (`{ }` في C# و`End Sub` في VB)، لكن المعاني والقواعد واحدة، لأن الاثنتين تُترجمان إلى نفس الكود الوسيط وتعملان على نفس منصة .NET، وتستخدمان نفس المكتبات.

## فتح مشروع VB.NET

نفس الخطوات تمامًا:

1. **File > Open Project...** (ملف > فتح مشروع...) واختر `.vbproj` أو `.sln` الذي يحتويه.
2. في **Solution Explorer** ترى `Form1.vb` وتحته `Form1.Designer.vb` و`Form1.resx`، ووحدات `Module1.vb`.
3. `F5` يبني بـ `dotnet build` (أو MSBuild للمشاريع القديمة) ويشغّل.

## ملفات نموذج VB.NET

`Form1.Designer.vb` يكتبه المصمم بلهجة VB:

```vbnet
<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()>
Partial Class Form1
    Inherits System.Windows.Forms.Form

    Private Sub InitializeComponent()
        Me.btnHello = New System.Windows.Forms.Button()
        Me.SuspendLayout()
        '
        'btnHello
        '
        Me.btnHello.Location = New System.Drawing.Point(12, 41)
        Me.btnHello.Name = "btnHello"
        Me.btnHello.Size = New System.Drawing.Size(120, 30)
        Me.btnHello.Text = "رحّب"
        Me.Controls.Add(Me.btnHello)
        Me.ResumeLayout(False)
    End Sub

    Friend WithEvents btnHello As System.Windows.Forms.Button
End Class
```

لاحظ الفرق المهم عن C#: الأداة معرّفة بـ `Friend WithEvents`، ولا يوجد سطر `+=` لربط الحدث. بدلًا منه، يُربط الحدث في `Form1.vb` بالكلمة **`Handles`**:

```vbnet
Public Class Form1
    Private Sub btnHello_Click(sender As Object, e As EventArgs) Handles btnHello.Click
        MessageBox.Show("أهلًا يا " & txtName.Text)
    End Sub
End Class
```

## المصمم يتكلم VB

كل ما تعلمته في الدرس 4 يعمل هنا، والمصمم يكتب بلهجة VB:

| الفعل في المصمم | ما يُكتب |
|---|---|
| أداة جديدة | `Me.CheckBox1 = New System.Windows.Forms.CheckBox()` و`Friend WithEvents CheckBox1 As ...` |
| نقر مزدوج على أداة | `Private Sub CheckBox1_CheckedChanged(sender As Object, e As EventArgs) Handles CheckBox1.CheckedChanged` في `Form1.vb` |
| حذف أداة | تُحذف تعليماتها، **وتُصلح عبارات `Handles`** التي تذكرها في `Form1.vb` |
| إعادة تسمية أداة | يتغير الاسم في `InitializeComponent` و`Friend WithEvents` **وفي عبارات `Handles`** |

والمصمم يفهم خصائص VB مثل تكملة السطر بـ ` _`، والأرقام بصيغة `&HFF`، و`Nothing` و`True` و`False`.

## من VB6 إلى VB.NET: جدول سريع

إذا كنت قادمًا من VB6 (أو من دورة BASIC في RAD IDE):

| VB6 / RAD BASIC | VB.NET |
|---|---|
| `Private Sub Command1_Click()` | `Private Sub Button1_Click(sender As Object, e As EventArgs) Handles Button1.Click` |
| `MsgBox "مرحبا"` | `MsgBox("مرحبا")` أو `MessageBox.Show("مرحبا")` |
| `Text1.Text` | `TextBox1.Text` |
| `Label1.Caption` | `Label1.Text` |
| `Dim x As Integer` (16 بت) | `Dim x As Integer` (32 بت) أو `Short` لـ 16 بت |
| `Form2.Show vbModal` | `Form2.ShowDialog()` |
| `Unload Me` | `Me.Close()` |

## إنشاء مشروع VB.NET جديد في الحل

1. انقر بالزر الأيمن على الحل: **Add > New Project...**.
2. اختر اللغة **VB** والقالب (**Windows Forms App** أو **Console App** أو **Class Library**).
3. تنشئه الـ IDE بالأمر `dotnet new winforms -lang VB` وتضيفه إلى الحل.

ويمكن أن يجمع حل واحد مشروع C# ومشروع VB.NET، ويستخدم أحدهما الآخر عبر **Add Project Reference...**: مكتبة مكتوبة بـ VB.NET يستخدمها برنامج C# والعكس.

## أخطاء شائعة

- **حذف `Handles btnHello.Click` بالخطأ:** تبقى الدالة لكن لا تعمل عند الضغط، ولا يظهر أي خطأ. أعد كتابة `Handles` أو انقر مرتين على الأداة في المصمم.
- **نسخ كود VB6 كما هو:** `Text1.Caption` و`Set x = ...` و`Variant` لا تعمل في VB.NET. لترحيل مشروع VB6 كامل استخدم معالج الترحيل (الدرس 8).

## اختبر نفسك

```quiz
{"question": "كيف يُربط حدث الضغط بالدالة في VB.NET عادة؟", "choices": ["بسطر += في Form1.Designer.vb", "بالكلمة Handles بعد توقيع الدالة في Form1.vb", "باسم الدالة فقط", "لا يمكن"], "answer": 1, "explanation": "Friend WithEvents في Designer مع Handles btnHello.Click في توقيع الدالة."}
```

```quiz
{"question": "حذفت أداة في المصمم، وكانت لها دالة فيها Handles. ماذا يفعل المصمم؟", "choices": ["يترك Handles فيفشل البناء", "يُصلح عبارة Handles في Form1.vb", "يحذف ملف Form1.vb", "يمنع الحذف"], "answer": 1, "explanation": "المصمم يحذف تعليمات الأداة ويصلح عبارات Handles التي تذكرها، على القرص وفي المحرر المفتوح."}
```

```quiz
{"question": "هل يمكن أن يستخدم مشروع C# مكتبة مكتوبة بـ VB.NET في نفس الحل؟", "choices": ["لا", "نعم، عبر Add Project Reference", "فقط بعد تحويلها إلى C#", "فقط في .NET Framework"], "answer": 1, "explanation": "اللغتان تترجمان إلى نفس الكود الوسيط على منصة .NET."}
```

## الخلاصة

- مشاريع `.vbproj` تُفتح وتُبنى وتُشغّل مثل `.csproj` تمامًا.
- النماذج: `Form1.vb` لكودك، و`Form1.Designer.vb` بلهجة VB (`Me.` و`Friend WithEvents`)، والأحداث بـ `Handles`.
- المصمم يكتب VB، ويصلح عبارات `Handles` عند حذف الأدوات أو إعادة تسميتها.
