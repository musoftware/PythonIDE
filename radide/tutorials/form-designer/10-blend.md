# الدرس 10: Blend: الحالات المرئية والخط الزمني وربط البيانات

**في هذا الدرس ستتعلم:**

- **الحالات المرئية** (Visual States): زر يتغير لونه عند وقوف الفأرة أو الضغط، بدون كود.
- **الخط الزمني** (Storyboards): حركة الأدوات بإطارات رئيسية (Keyframes) تسجّلها بالفأرة.
- **ربط البيانات التجريبية** (Data panel): أدوات تعرض حقول ملف JSON أو CSV.
- كيف تتحكم في ذلك كله من الكود: `GoToState` و `Begin` و `MoveNext`.

## ما هو Blend؟

**Expression Blend** أداة من Microsoft للمصممين: يصنعون فيها الحركة والتفاعل بالفأرة، والمبرمج يكتب المنطق.
في RAD IDE ثلاث نوافذ على طريقة Blend، تعمل في المصمم العادي لمشروعات **Python (Tkinter)** و **Python (PySide6 / Qt)**:

| النافذة | القائمة | الاسم العربي |
|---|---|---|
| **States** | **View > States** | الحالات |
| **Objects and Timeline** | **View > Objects and Timeline** | الكائنات والخط الزمني |
| **Data** | **View > Data** | البيانات |

## 1) الحالات المرئية: وجوه الأداة

الزر له "مزاج": عادي، والفأرة فوقه، ومضغوط، ومعطّل. كل مزاج **حالة** (State) لها ألوانها وخصائصها.

### الحالات الجاهزة

| الحالة | متى تظهر؟ |
|---|---|
| `MouseOver` | الفأرة فوق الأداة |
| `Pressed` | زر الفأرة مضغوط عليها |
| `Focused` | الأداة عليها التركيز (المؤشر فيها) |
| `Disabled` | `Enabled = False` |

### خطوة بخطوة: زر يتوهج

1. افتح **View > States**. حدد زرًّا في المصمم.
2. في نافذة States اختر الحالة `MouseOver`. المصمم يعرض الزر **كما سيبدو** في تلك الحالة.
3. فعّل **Record** (تسجيل). الآن أي تعديل في نافذة الخصائص يُحفظ **لهذه الحالة فقط**.
4. غيّر `BackColor` إلى أزرق فاتح. أو استخدم: اختر الخاصية من القائمة ثم **Override** (تجاوز)، و **Colour...** (اللون...) للألوان.
5. أطفئ **Record**. التصميم الأساسي لم يتغير.
6. شغّل البرنامج ومرّر الفأرة على الزر: يتغير لونه وحده، ويرجع عند خروج الفأرة.

**Remove** يحذف تجاوز الخاصية المحددة من الحالة.

### حالات من تصميمك

**Add State** (إضافة حالة) ينشئ حالة للنموذج كله، مثل `Expanded` (لوحة مفتوحة) أو `ReadOnly`. سجّل فيها خصائص أدوات كثيرة، ثم انتقل إليها بالكود:

```python
    def btnMore_Click(self):
        self.GoToState("Expanded")
```

## 2) الخط الزمني: الحركة بإطارات رئيسية

**الإطار الرئيسي** (Keyframe) لقطة: "عند الثانية 0 الزر عند `Left = 10`، وعند الثانية 1 عند `Left = 200`". البرنامج يرسم ما بينهما بنعومة.
مثل كتاب الرسوم المتحركة الذي تقلّب صفحاته بسرعة، لكنك ترسم صفحتين فقط والحاسوب يرسم الباقي.

### خطوة بخطوة: زر ينزلق

1. افتح **View > Objects and Timeline**.
2. اضغط **New** (جديد) لإنشاء `Storyboard1`. خيارات القصة:
   - **Begin on Load** (البدء عند التحميل): تبدأ وحدها عند فتح النافذة.
   - **Repeat** (تكرار): تعيد من البداية إلى الأبد.
   - **AutoReverse** (عكس تلقائي): تمشي للأمام ثم ترجع.
3. فعّل **● Record keyframes** (● تسجيل الإطارات الرئيسية). يظهر إطار أحمر حول المصمم مكتوب عليه "Recording".
4. اسحب **مؤشر الوقت** الأحمر على المسطرة إلى `1000` ميلي ثانية (أو اكتب الوقت في خانته).
5. حرّك الزر في المصمم إلى مكانه الجديد. يُسجَّل **إطار واحد** عند الثانية 1 للخاصية التي تغيرت (`Left`)، ومعه إطار عند 0 بالقيمة الأصلية.
6. أطفئ التسجيل. اضغط **▶ Play** (تشغيل) لترى الحركة في المصمم، و **■ Stop** (إيقاف) لإرجاع كل شيء.

لتعديل إطار: حدده واكتب وقته أو قيمته، واختر **Easing** (طريقة التسارع): `linear` و `in` و `out` و `inout`. **Add Keyframe** يضيف إطارًا يدويًا، و **Delete Key** يحذفه.

### من الكود

```python
    def btnShow_Click(self):
        self.Storyboard1.Begin()

    def Storyboard1_Completed(self):
        self.lblInfo.config(text="انتهت الحركة")
```

وفيها أيضًا `Stop()` و `Pause()` و `Resume()` و `Seek(500)` و `IsPlaying` و `Duration`.

### الفكرة نفسها بمؤقت

القصة المصورة في النهاية مؤقت يغيّر خاصية خطوة بخطوة. هذا مثال BASIC يحرك عنوانًا بمؤقت، ويطلق حدث "الانتهاء" عند الوصول. (المقاسات في كود VB6 بوحدة Twip، و 150 Twip = 10 نقاط على الشاشة.)

<!-- test: {"steps": [["set", "tmrMove", "Enabled", "False"], ["set", "lblBall", "Left", "0"], ["event", "tmrMove", "Timer"], ["event", "tmrMove", "Timer"], ["event", "tmrMove", "Timer"]], "expect": {"lblBall.Left": "450", "tmrMove.Enabled": "False", "lblState.Caption": "انتهت الحركة"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "حركة"
   ClientWidth     =   4800
   ClientHeight    =   1800
   Begin VB.Label lblBall
      Caption         =   "●"
      Left            =   0
      Top             =   240
      Width           =   400
      Height          =   400
   End
   Begin VB.Label lblState
      Left            =   240
      Top             =   1000
      Width           =   4200
      Height          =   400
   End
   Begin VB.Timer tmrMove
      Interval        =   100
   End
End

Private Sub tmrMove_Timer()
    lblBall.Left = lblBall.Left + 150
    If lblBall.Left >= 450 Then
        tmrMove.Enabled = False
        Storyboard_Completed
    End If
End Sub

Private Sub Storyboard_Completed()
    lblState.Caption = "انتهت الحركة"
End Sub
```

## 3) ربط البيانات التجريبية

أثناء التصميم تريد أن ترى القائمة **ممتلئة** بأسماء حقيقية، لا فارغة. نافذة **Data** تربط الأدوات بملف بيانات.

### خطوة بخطوة

1. افتح **View > Data**.
2. اضغط **New Sample** (عينة جديدة): تنشئ البيئة ملف JSON فيه سجلات تجريبية. أو **Add File...** (إضافة ملف...) لاختيار ملف JSON أو CSV عندك.
3. حدد أداة في المصمم، مثل `ListBox1`.
4. في النصف السفلي من النافذة اختر: **الخاصية** (`Items`)، و**مصدر البيانات** (`People`)، و**الحقل** (`name`)، ثم اضغط **Bind** (ربط).
5. مع **Show sample data in the designer** (عرض بيانات تجريبية في المصمم) تظهر الأسماء في المصمم فورًا.

| الخاصية المربوطة | ماذا تأخذ؟ |
|---|---|
| `Text` (و `Checked` و `Value`) | الحقل من **السجل الحالي** |
| `Items` (ListBox و ComboBox) | الحقل من **كل** السجلات |
| `Rows` (DataGridView و ListView) | الحقول المفصولة بفواصل (فارغ = كلها) |

إذا ربطت `ListBox` بحقل `name` و `TextBox` بحقل `email`، فاختيار اسم من القائمة يُظهر بريده في المربع تلقائيًا. هذا اسمه **رئيسي/تفصيلي** (Master / Detail).

### من الكود

```python
    def btnNext_Click(self):
        self.People.MoveNext()
        self.lblCount.config(text=f"{self.People.Position + 1} / {self.People.Count}")
```

وفيه `MoveFirst()` و `MovePrevious()` و `MoveLast()` و `Current` و `Value("name")` و `Refresh()` لإعادة قراءة الملف.

> 💡 هذا الربط لملفات JSON و CSV. أما الربط بقواعد بيانات حقيقية (SQLite و MySQL و PostgreSQL) فتجده في **دليل البيانات والتقارير**.

## أخطاء شائعة

- **نسيان إطفاء Record:** كل تعديل لاحق يذهب إلى الحالة أو القصة بدل التصميم الأساسي. انتبه للإطار الأحمر.
- **تحريك الأداة ومؤشر الوقت عند 0:** يتغير التصميم الأساسي لا الحركة. حرّك المؤشر أولًا.
- **قصة لا تبدأ:** فعّل **Begin on Load** أو استدعِ `Begin()` من الكود.
- **ربط `Text` بقائمة:** للقوائم استخدم `Items`، و `Text` لمربع النص والعنوان.

## تمرين

### تمرين 1: حركة بخطوات أصغر

عدّل المثال ليتحرك العنوان `75` في كل نبضة بدل `150`، وتنتهي الحركة عند `300`. بعد 4 نبضات يجب أن يكون `Left = 300` والمؤقت متوقفًا.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "حركة"
   ClientWidth     =   4800
   ClientHeight    =   1800
   Begin VB.Label lblBall
      Caption         =   "●"
      Left            =   0
      Top             =   240
      Width           =   400
      Height          =   400
   End
   Begin VB.Label lblState
      Left            =   240
      Top             =   1000
      Width           =   4200
      Height          =   400
   End
   Begin VB.Timer tmrMove
      Interval        =   100
   End
End

Private Sub tmrMove_Timer()
    lblBall.Left = lblBall.Left + 150
    If lblBall.Left >= 450 Then
        tmrMove.Enabled = False
        lblState.Caption = "انتهت الحركة"
    End If
End Sub
```

<!-- test: {"steps": [["set", "tmrMove", "Enabled", "False"], ["set", "lblBall", "Left", "0"], ["event", "tmrMove", "Timer"], ["event", "tmrMove", "Timer"], ["event", "tmrMove", "Timer"], ["event", "tmrMove", "Timer"]], "expect": {"lblBall.Left": "300", "tmrMove.Enabled": "False", "lblState.Caption": "انتهت الحركة"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "حركة"
   ClientWidth     =   4800
   ClientHeight    =   1800
   Begin VB.Label lblBall
      Caption         =   "●"
      Left            =   0
      Top             =   240
      Width           =   400
      Height          =   400
   End
   Begin VB.Label lblState
      Left            =   240
      Top             =   1000
      Width           =   4200
      Height          =   400
   End
   Begin VB.Timer tmrMove
      Interval        =   100
   End
End

Private Sub tmrMove_Timer()
    lblBall.Left = lblBall.Left + 75
    If lblBall.Left >= 300 Then
        tmrMove.Enabled = False
        lblState.Caption = "انتهت الحركة"
    End If
End Sub
```

### مهمة عملية: لوحة تنزلق وزر يتوهج

1. في مشروع **Python (Tkinter)** ضع زرًّا `btnShow` و `Panel` اسمه `pnlInfo` خارج يمين النموذج.
2. **States**: اجعل للزر حالة `MouseOver` بلون مختلف.
3. **Objects and Timeline**: أنشئ `Storyboard1` وسجّل حركة اللوحة إلى داخل النموذج خلال 800 ميلي ثانية بتسارع `out`.
4. اكتب `self.Storyboard1.Begin()` في `btnShow_Click` وشغّل البرنامج.

## اختبر نفسك

```quiz
{"question": "فعّلت Record في نافذة States على الحالة `MouseOver` وغيّرت `BackColor`. متى يظهر اللون الجديد؟", "choices": ["دائمًا", "عندما تكون الفأرة فوق الأداة فقط", "عند الضغط فقط", "لا يظهر أبدًا"], "answer": 1, "explanation": "التعديل أثناء التسجيل يُحفظ للحالة المحددة فقط، والتصميم الأساسي يبقى."}
```

```quiz
{"question": "ما هو الإطار الرئيسي (Keyframe)؟", "choices": ["أول نموذج في المشروع", "قيمة خاصية عند لحظة زمنية، والبرنامج يملأ ما بين الإطارات", "صورة خلفية", "زر في شريط الأدوات"], "answer": 1, "explanation": "ترسم لقطتين أو أكثر، والحركة بينهما تُحسب تلقائيًا."}
```

```quiz
{"question": "تريد أن تعرض ListBox الحقل `name` من كل سجلات مصدر البيانات. أي خاصية تربط؟", "choices": ["`Text`", "`Items`", "`Left`", "`Enabled`"], "answer": 1, "explanation": "Items تأخذ الحقل من كل السجلات، و Text تأخذه من السجل الحالي فقط."}
```

## الخلاصة

- **States**: حالات جاهزة (`MouseOver` و `Pressed` و `Focused` و `Disabled`) وحالات من تصميمك، و **Record** لتسجيل الخصائص، و `GoToState` من الكود.
- **Objects and Timeline**: قصص بإطارات رئيسية تسجّلها بتحريك الأدوات، و **▶ Play** للمعاينة، و `Begin()` و `Storyboard1_Completed` في الكود.
- **Data**: ملفات JSON / CSV تُربط بالأدوات بـ **Bind**، وتظهر عينات في المصمم، و `MoveNext()` للتنقل.
- انتبه دائمًا للإطار الأحمر: التسجيل يعمل.
