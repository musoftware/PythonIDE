# الدرس 2: نافذة الخصائص

**في هذا الدرس ستتعلم:**

- أجزاء نافذة **Properties** (الخصائص): قائمة الاختيار، والعرض المصنّف والأبجدي، ووصف الخاصية.
- أهم الخصائص المشتركة: `Name` و `Text` و `Enabled` و `Visible` و `Font` و `BackColor` وأماكن الأداة.
- قواعد تسمية الأدوات (`btn` و `txt` و `lbl` ...).
- الفرق بين تغيير خاصية **وقت التصميم** وتغييرها **وقت التشغيل** بالكود.

## بطاقة هوية لكل أداة

كل أداة على النموذج لها **بطاقة هوية**: اسمها، ونصها، ولونها، ومكانها، وحجمها... هذه البطاقة هي **نافذة الخصائص**.
تحدد أداة في المصمم فتعرض النافذة بطاقتها، وتغيّر أي قيمة فيتغير شكل الأداة فورًا.

افتحها من **View > Properties** (عرض > الخصائص).

## أجزاء النافذة

| الجزء | ما هو؟ |
|---|---|
| **قائمة الاختيار** في الأعلى | اسم الأداة المحددة ونوعها. افتحها لتختار أداة أخرى، أو النموذج نفسه |
| **Categorized** (مصنّفة) / **A-Z** | ترتيب الخصائص في مجموعات (المظهر، والسلوك، والتخطيط، والبيانات ...) أو أبجديًا |
| لسان **Properties** (الخصائص) | جدول من عمودين: **Property** (الخاصية) و **Value** (القيمة) |
| لسان **Events** (الأحداث) | أحداث الأداة ومعالجاتها (الدرس التالي) |
| **منطقة الوصف** في الأسفل | شرح قصير للخاصية المحددة |

### تعديل القيم

- **نص أو رقم**: انقر القيمة واكتب، ثم `Enter`.
- **قائمة اختيارات** (مثل `TextAlign` أو `Dock`): اختر من القائمة المنسدلة.
- **صح / خطأ** (مثل `Enabled` و `Visible`): `True` أو `False`.
- **لون**: يفتح منتقي الألوان.
- **Anchor**: نافذة صغيرة فيها أربعة أشرطة (أعلى وأسفل ويسار ويمين) تفعّلها بالنقر. سنشرحها في درس Anchor و Dock.

## أهم الخصائص

| الخاصية | المعنى | مثال |
|---|---|---|
| `Name` | اسم الأداة في الكود. **أهم خاصية** | `btnSave` |
| `Text` | النص الظاهر: عنوان النافذة، ونص الزر، ومحتوى مربع النص | `حفظ` |
| `Left` و `Top` | مكان الأداة داخل حاويتها | `16` و `60` |
| `Width` و `Height` | العرض والارتفاع | `120` و `32` |
| `Enabled` | هل تستجيب للمستخدم؟ `False` تجعلها رمادية | `True` |
| `Visible` | هل تظهر؟ | `True` |
| `BackColor` و `ForeColor` | لون الخلفية ولون النص | |
| `FontName` و `FontSize` و `FontBold` | الخط | `Segoe UI`، `9` |
| `ToolTip` | تلميح يظهر عند وقوف الفأرة | `احفظ التغييرات` |
| `TabIndex` | ترتيب التنقل بـ `Tab` | `0`، `1`، `2` ... |

خصائص **النموذج** نفسه (حدده بالنقر على مكان فارغ منه): `Text` (العنوان)، و `StartPosition` (`CenterScreen` يجعله في وسط الشاشة)، و `FormBorderStyle` (`Sizable` قابل لتغيير الحجم، أو ثابت)، و `WindowState`، و `Icon`.

> 💡 **في كود BASIC:** خاصية `Text` في نافذة الخصائص هي ما يسميه Visual Basic 6 **`Caption`** للنموذج والعناوين والأزرار، و **`Text`** لمربعات النص. لذلك تكتب في الكود `lblOut.Caption` و `txtName.Text`.

## سمِّ أدواتك جيدًا

الاسم الافتراضي `Button1` لا يخبرك بشيء. بعد أسبوع لن تتذكر ماذا يفعل `Button7`!
اكتب **بادئة من ثلاثة حروف** لنوع الأداة، ثم وصفها:

| البادئة | النوع | مثال |
|---|---|---|
| `btn` أو `cmd` | زر | `btnSave` |
| `txt` | مربع نص | `txtName` |
| `lbl` | عنوان | `lblTotal` |
| `chk` | مربع اختيار | `chkAgree` |
| `opt` أو `rdo` | زر اختيار | `optMale` |
| `lst` | قائمة | `lstItems` |
| `cbo` | قائمة منسدلة | `cboCity` |
| `tmr` | مؤقت | `tmrClock` |

> ⚠️ **غيّر الاسم قبل كتابة الكود.** إذا كتبت معالج `Button1_Click` ثم غيّرت الاسم إلى `btnSave`، فالمعالج القديم لن يرتبط بالزر الجديد تلقائيًا في كل اللغات.

## وقت التصميم ووقت التشغيل

- **وقت التصميم** (Design time): ما تكتبه في نافذة الخصائص. هو حالة النافذة عند فتحها.
- **وقت التشغيل** (Run time): ما يغيّره الكود أثناء عمل البرنامج.

في المثال التالي: الزر `cmdSave` يبدأ معطّلًا (`Enabled = False` من التصميم)، ويتفعّل بالكود عندما يكتب المستخدم شيئًا. وزر "إخفاء" يخفي العنوان ويغيّر لونه:

<!-- test: {"steps": [["set", "txtNote", "Text", "مرحبا"], ["click", "cmdHide"]], "expect": {"cmdSave.Enabled": "True", "lblTip.Visible": "False", "Form1.BackColor": "65535"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "الخصائص"
   ClientWidth     =   4800
   ClientHeight    =   2400
   Begin VB.TextBox txtNote
      Left            =   240
      Top             =   240
      Width           =   3000
      Height          =   400
   End
   Begin VB.CommandButton cmdSave
      Caption         =   "حفظ"
      Enabled         =   0   'False
      Left            =   3360
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.Label lblTip
      Caption         =   "اكتب ملاحظة لتفعيل زر الحفظ"
      Left            =   240
      Top             =   840
      Width           =   4200
      Height          =   400
   End
   Begin VB.CommandButton cmdHide
      Caption         =   "إخفاء"
      Left            =   240
      Top             =   1500
      Width           =   1200
      Height          =   400
   End
End

Private Sub txtNote_Change()
    cmdSave.Enabled = (Len(txtNote.Text) > 0)
End Sub

Private Sub cmdHide_Click()
    lblTip.Visible = False
    Me.BackColor = vbYellow
End Sub
```

بعد «افتح في المحرر» حدد `cmdSave` في المصمم وانظر إلى `Enabled` في نافذة الخصائص: قيمته `False`.

## أخطاء شائعة

- **تغيير `Text` بدل `Name`:** النص يتغير على الشاشة، لكن الاسم في الكود يبقى `Button1`.
- **أسماء بالعربية أو بمسافات:** الاسم يجب أن يبدأ بحرف إنجليزي، بلا مسافات ولا رموز: `btnSave` وليس `زر حفظ`.
- **البحث عن خاصية في العرض المصنّف:** إذا لم تجدها، اضغط **A-Z** لترتيبها أبجديًا.
- **تعديل خاصية الأداة الخطأ:** انظر إلى قائمة الاختيار في أعلى النافذة: هي تخبرك أي أداة محددة.

## تمرين

### تمرين 1: زر يتفعّل بالموافقة

عند الضغط على `cmdAgree` اجعل `cmdNext` مفعّلًا، وغيّر نص `lblState` إلى "شكرًا لموافقتك"، وأخفِ الزر `cmdAgree` نفسه.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "الشروط"
   ClientWidth     =   4800
   ClientHeight    =   2000
   Begin VB.CommandButton cmdAgree
      Caption         =   "أوافق"
      Left            =   240
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.CommandButton cmdNext
      Caption         =   "التالي"
      Enabled         =   0   'False
      Left            =   1680
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.Label lblState
      Caption         =   "اقرأ الشروط أولًا"
      Left            =   240
      Top             =   900
      Width           =   4200
      Height          =   400
   End
End

Private Sub cmdAgree_Click()
    ' اكتب هنا
End Sub
```

<!-- test: {"steps": [["click", "cmdAgree"]], "expect": {"cmdNext.Enabled": "True", "lblState.Caption": "شكرًا لموافقتك", "cmdAgree.Visible": "False"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "الشروط"
   ClientWidth     =   4800
   ClientHeight    =   2000
   Begin VB.CommandButton cmdAgree
      Caption         =   "أوافق"
      Left            =   240
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.CommandButton cmdNext
      Caption         =   "التالي"
      Enabled         =   0   'False
      Left            =   1680
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.Label lblState
      Caption         =   "اقرأ الشروط أولًا"
      Left            =   240
      Top             =   900
      Width           =   4200
      Height          =   400
   End
End

Private Sub cmdAgree_Click()
    cmdNext.Enabled = True
    lblState.Caption = "شكرًا لموافقتك"
    cmdAgree.Visible = False
End Sub
```

### مهمة عملية: بطاقة الأداة

1. ضع زرًّا على نموذج جديد. غيّر `Name` إلى `btnOK` و `Text` إلى `موافق`.
2. اجعل `FontSize` يساوي 12 و `FontBold` يساوي `True`.
3. اكتب في `ToolTip`: `اضغط للمتابعة`، ثم شغّل البرنامج وقف بالفأرة على الزر.
4. حدد النموذج نفسه واجعل `StartPosition` يساوي `CenterScreen`.

## اختبر نفسك

```quiz
{"question": "أي خاصية تحدد اسم الأداة في الكود؟", "choices": ["`Text`", "`Name`", "`ToolTip`", "`TabIndex`"], "answer": 1, "explanation": "`Name` هو الاسم الذي تكتبه في الكود، و `Text` هو النص الظاهر."}
```

```quiz
{"question": "زر خاصيته `Enabled = False`. كيف يبدو؟", "choices": ["مختفٍ تمامًا", "ظاهر لكنه رمادي ولا يستجيب", "أحمر", "يعمل عاديًا"], "answer": 1, "explanation": "Enabled = False يعطّل الأداة مع بقائها ظاهرة. أما Visible = False فيخفيها."}
```

```quiz
{"question": "أي اسم هو الأفضل لمربع نص يُكتب فيه البريد الإلكتروني؟", "choices": ["`TextBox3`", "`txtEmail`", "`مربع البريد`", "`email box`"], "answer": 1, "explanation": "بادئة النوع ثم الوصف، بحروف إنجليزية وبلا مسافات."}
```

## الخلاصة

- نافذة الخصائص "بطاقة هوية" الأداة المحددة: **Categorized** أو **A-Z**، والوصف في الأسفل.
- `Name` للكود، و `Text` للشاشة، و `Enabled` و `Visible` للحالة.
- سمِّ الأدوات ببادئة النوع: `btnSave` و `txtName` و `lblTotal`، وقبل كتابة الكود.
- قيم التصميم هي البداية، والكود يغيّرها وقت التشغيل.
