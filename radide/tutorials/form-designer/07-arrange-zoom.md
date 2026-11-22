# الدرس 7: قائمة Format وترتيب Tab والتكبير

**في هذا الدرس ستتعلم:**

- محاذاة الأدوات وتوحيد أحجامها وتوسيطها من قائمة **Format** (تنسيق).
- ترتيب الطبقات: **Bring to Front** و **Send to Back**.
- قفل الأدوات بعد انتهاء التصميم.
- ترتيب التنقل بمفتاح `Tab`: **View > Tab Order**.
- تكبير المصمم وتصغيره من 25% إلى 400%.

## مسطرة النجار

النافذة المرتبة تبدو احترافية: الأزرار بنفس الحجم، والعناوين على خط واحد. لا تحتاج أن تحرك كل أداة بالنقطة يدويًا؛ قائمة **Format** هي مسطرة النجار وزاويته.

## المحاذاة والأحجام

حدد **أداتين أو أكثر** (`Ctrl` + نقر). **الأداة المرجعية** هي التي حددتها **أخيرًا**، وهي نفسها التي تعرض نافذة الخصائص بياناتها؛ البقية تُحاذى عليها.

| الأمر | الاسم العربي | المعنى |
|---|---|---|
| **Format > Align > Lefts** | محاذاة > الحواف اليسرى | نفس `Left` |
| **Format > Align > Centers** | المراكز | نفس المركز الأفقي |
| **Format > Align > Rights** | الحواف اليمنى | نفس الحافة اليمنى |
| **Format > Align > Tops** | الحواف العلوية | نفس `Top`، أي على سطر واحد |
| **Format > Align > Middles** | المنتصفات | نفس المركز الرأسي |
| **Format > Align > Bottoms** | الحواف السفلية | نفس الحافة السفلية |
| **Format > Make Same Size > Width / Height / Both** | توحيد الحجم > العرض / الارتفاع / كلاهما | نفس العرض أو الارتفاع أو الاثنين |
| **Format > Align > to Grid** / **Make Same Size > Size to Grid** | إلى الشبكة / الحجم حسب الشبكة | المكان أو الحجم على أقرب نقاط الشبكة (يكفي أداة واحدة) |
| **Format > Horizontal Spacing / Vertical Spacing** | التباعد الأفقي / الرأسي | **Make Equal** مسافات متساوية (3 أدوات على الأقل، الطرفان لا يتحركان)، **Increase / Decrease** بخطوة شبكة، **Remove** الأدوات متلاصقة؛ الأداة المرجعية لا تتحرك |
| **Format > Center in Form > Horizontally / Vertically** | توسيط في النموذج > أفقيًا / رأسيًا | وسط النموذج (أو وسط الحاوية)؛ الأدوات المحددة تتحرك معًا كمجموعة واحدة |
| **Format > Order > Bring to Front** | إحضار إلى الأمام | الأداة فوق غيرها |
| **Format > Order > Send to Back** | إرسال إلى الخلف | الأداة خلف غيرها |
| **Format > Lock Controls** | قفل عناصر التحكم | لا تتحرك الأدوات ولا يتغير حجمها بالخطأ |

> 💡 **Bring to Front و Send to Back** يغيّران أيضًا ترتيب الالتصاق في `Dock` كما رأيت في الدرس السابق.

> 💡 الأوامر التي لا تناسب التحديد تظهر رمادية، مثل Visual Studio: المحاذاة وتوحيد الحجم تحتاج أداتين، و Make Equal ثلاث أدوات، ولا شيء يتحرك والأدوات مقفلة.

### لوحة المفاتيح والفأرة كما في Visual Studio

- الأسهم تحرّك الأدوات المحددة بكسلًا واحدًا، و `Ctrl` + الأسهم إلى خط الشبكة التالي (أو حافة أداة أخرى)، و `Shift` + الأسهم تغيّر الحجم، و `Ctrl+Shift` + الأسهم تغيّره حتى خط الشبكة.
- أثناء السحب تلتصق حافة الأداة بحواف الأدوات المجاورة ويظهر خط أزرق (Snapline)؛ اضغط `Alt` أثناء السحب لتحريك حر بدون شبكة، و `Esc` لإلغاء السحب.
- `Tab` و `Shift+Tab` يحددان الأداة التالية / السابقة، و `Esc` يحدد الحاوية ثم النموذج.
- اسحب بالفأرة على مكان فارغ لتحديد عدة أدوات (`Shift` يضيف، و `Ctrl` يبدّل)، ومع أداة من Toolbox اسحب لترسم الأداة بالحجم الذي تريده، أو انقر الأداة في Toolbox مرتين لتُضاف فورًا.
- اللصق (`Ctrl+V`) يضع الأدوات داخل الحاوية المحددة، ويزيحها قليلًا إذا كان مكانها مشغولًا.

## ترتيب Tab

المستخدم الذي يملأ استمارة يضغط `Tab` لينتقل من خانة إلى التالية. الترتيب الطبيعي: الاسم، ثم البريد، ثم الهاتف، ثم زر الحفظ.
هذا الترتيب تحدده خاصية `TabIndex` لكل أداة (0 أولًا، ثم 1، ثم 2 ...).

### ضبطه بالنقر

1. افتح النموذج في المصمم واختر **View > Tab Order** (عرض > ترتيب Tab).
2. يظهر رقم صغير على كل أداة.
3. **انقر الأدوات بالترتيب** الذي تريده: الأولى تأخذ 0، والثانية 1، وهكذا.
4. اضغط `Esc` أو اختر **View > Tab Order** مرة أخرى للانتهاء.

### ماذا يحدث في الملف؟

في ملف `.frm` يُكتب `TabIndex` لكل أداة، كما ترى في المثال التالي. ولاحظ أيضًا أن مربعات النص الثلاثة مصطفة بنفس `Left` وبنفس `Width`، كأنها رُتبت بـ **Align > Lefts** و **Make Same Size > Width**. البرنامج يتحقق من ذلك عند التحميل:

```vb form run
Begin VB.Form Form1
   Caption         =   "استمارة"
   ClientWidth     =   4800
   ClientHeight    =   2800
   Begin VB.TextBox txtName
      TabIndex        =   0
      Left            =   1200
      Top             =   240
      Width           =   3000
      Height          =   400
   End
   Begin VB.TextBox txtEmail
      TabIndex        =   1
      Left            =   1200
      Top             =   780
      Width           =   3000
      Height          =   400
   End
   Begin VB.TextBox txtPhone
      TabIndex        =   2
      Left            =   1200
      Top             =   1320
      Width           =   3000
      Height          =   400
   End
   Begin VB.CommandButton cmdSave
      Caption         =   "حفظ"
      TabIndex        =   3
      Left            =   1200
      Top             =   1980
      Width           =   1200
      Height          =   500
   End
End

Private Sub Form_Load()
    Debug.Print "حافة يسرى واحدة: " & (txtName.Left = txtEmail.Left And txtEmail.Left = txtPhone.Left)
    Debug.Print "عرض واحد: " & (txtName.Width = txtEmail.Width And txtEmail.Width = txtPhone.Width)
    Debug.Print "الزر تحت المربعات: " & (cmdSave.Left = txtName.Left)
End Sub
```

```text output
حافة يسرى واحدة: True
عرض واحد: True
الزر تحت المربعات: True
```

بعد «افتح في المحرر» اختر **View > Tab Order** في المصمم: سترى الأرقام 0 و 1 و 2 و 3 على الأدوات بالترتيب نفسه المكتوب في الملف.

## تكبير المصمم

عند تصميم نافذة صغيرة بتفاصيل دقيقة، أو نافذة كبيرة على شاشة صغيرة، كبّر أو صغّر **المصمم** (البرنامج نفسه لا يتأثر):

| الطريقة | الخطوات |
|---|---|
| الفأرة | `Ctrl` + عجلة الفأرة فوق المصمم |
| القائمة | **View > Zoom** (عرض > التكبير): **Zoom In** و **Zoom Out** ونسب جاهزة: 50% و 75% و 100% و 150% و 200% و 300% و 400% |
| شريط الحالة | مربع النسبة في شريط الحالة: اختر أو اكتب نسبة |

كل شيء يعمل أثناء التكبير: التحديد، والسحب من صندوق الأدوات، وتغيير الحجم. المقاسات في نافذة الخصائص تبقى بالنقاط الحقيقية.

## أخطاء شائعة

- **المحاذاة على الأداة الخطأ:** الأداة المرجعية هي المحددة **أخيرًا**. اجعل الأداة التي في المكان الصحيح آخر ما تنقره.
- **"الأدوات لا تتحرك!"**: ربما فعّلت **Format > Lock Controls**. اختره مرة أخرى لإلغاء القفل.
- **ترك وضع Tab Order مفتوحًا:** النقر على الأدوات يغيّر أرقامها بدل تحديدها. اضغط `Esc`.
- **ظن أن التكبير يغيّر حجم البرنامج:** التكبير للمصمم فقط.

## تمرين

### تمرين 1: صحّح المحاذاة

مربع البريد `txtEmail` منحرف قليلًا وأقصر من مربع الاسم. صحّح `Left` و `Width` له في ملف `.frm` كما لو استخدمت **Align > Lefts** و **Make Same Size > Width** على `txtName`، فيطبع البرنامج `True True`.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "استمارة"
   ClientWidth     =   4800
   ClientHeight    =   2200
   Begin VB.TextBox txtName
      TabIndex        =   0
      Left            =   1200
      Top             =   240
      Width           =   3000
      Height          =   400
   End
   Begin VB.TextBox txtEmail
      TabIndex        =   1
      Left            =   1500
      Top             =   780
      Width           =   2400
      Height          =   400
   End
   Begin VB.CommandButton cmdSave
      Caption         =   "حفظ"
      TabIndex        =   2
      Left            =   1200
      Top             =   1440
      Width           =   1200
      Height          =   500
   End
End

Private Sub Form_Load()
    Debug.Print (txtName.Left = txtEmail.Left) & " " & (txtName.Width = txtEmail.Width)
End Sub
```

```vb form solution
Begin VB.Form Form1
   Caption         =   "استمارة"
   ClientWidth     =   4800
   ClientHeight    =   2200
   Begin VB.TextBox txtName
      TabIndex        =   0
      Left            =   1200
      Top             =   240
      Width           =   3000
      Height          =   400
   End
   Begin VB.TextBox txtEmail
      TabIndex        =   1
      Left            =   1200
      Top             =   780
      Width           =   3000
      Height          =   400
   End
   Begin VB.CommandButton cmdSave
      Caption         =   "حفظ"
      TabIndex        =   2
      Left            =   1200
      Top             =   1440
      Width           =   1200
      Height          =   500
   End
End

Private Sub Form_Load()
    Debug.Print (txtName.Left = txtEmail.Left) & " " & (txtName.Width = txtEmail.Width)
End Sub
```

```text output
True True
```

### مهمة عملية: رتّب نافذة فوضوية

1. ضع أربعة أزرار في أماكن عشوائية بأحجام مختلفة.
2. حدد الأزرار الأخرى بـ `Ctrl` + نقر، واجعل الزر الذي في المكان الصحيح **آخر** ما تنقره.
3. **Format > Align > Lefts**، ثم **Format > Make Same Size > Both**.
4. **View > Tab Order** وانقرها من الأعلى إلى الأسفل، ثم `Esc`.
5. كبّر المصمم إلى 200% بـ `Ctrl` + العجلة لتتأكد من المحاذاة، ثم ارجع إلى 100%.
6. **Format > Lock Controls**.

## اختبر نفسك

```quiz
{"question": "حددت ثلاثة أزرار ثم اخترت Align > Lefts. على أي زر تُحاذى؟", "choices": ["الأكبر", "المحدد أولًا", "المحدد أخيرًا (الذي تعرضه نافذة الخصائص)", "الأقرب للحافة"], "answer": 2, "explanation": "الأداة المحددة أخيرًا هي المرجع، وهي التي تظهر خصائصها في نافذة الخصائص."}
```

```quiz
{"question": "أي خاصية تحدد ترتيب التنقل بمفتاح Tab؟", "choices": ["`Left`", "`TabIndex`", "`Name`", "`Visible`"], "answer": 1, "explanation": "TabIndex: الأصغر أولًا، وتضبطه بالنقر في View > Tab Order."}
```

```quiz
{"question": "كبّرت المصمم إلى 200%. ماذا يحدث لحجم نافذة البرنامج عند تشغيله؟", "choices": ["تتضاعف", "لا تتغير، التكبير للمصمم فقط", "تصغر", "يتوقف البرنامج"], "answer": 1, "explanation": "التكبير يغيّر العرض في المصمم فقط، والمقاسات الحقيقية كما هي."}
```

## الخلاصة

- **Format > Align / Make Same Size / Center in Form** للترتيب، والمرجع هو المحدد أخيرًا.
- **Bring to Front / Send to Back** للطبقات، و **Lock Controls** لمنع التحريك بالخطأ.
- **View > Tab Order**: انقر الأدوات بالترتيب ثم `Esc`، والنتيجة في `TabIndex`.
- **View > Zoom** أو `Ctrl` + العجلة أو شريط الحالة: من 25% إلى 400%.
