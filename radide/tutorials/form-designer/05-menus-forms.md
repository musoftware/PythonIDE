# الدرس 5: القوائم ومحرر القوائم والنماذج المتعددة

**في هذا الدرس ستتعلم:**

- إضافة شريط قوائم لبرنامجك بـ `MenuStrip` وتحريره في **Menu Editor** (محرر القوائم).
- كتابة معالجات أوامر القوائم، والفواصل، والعلامات (Checked)، والتعطيل.
- إضافة نموذج ثانٍ: **Project > Add Windows Form...**، وفتحه من النموذج الأول.
- أي نموذج يبدأ به البرنامج، وكيف تمرر البيانات بين النماذج.

## القائمة: فهرس الأوامر

شريط القوائم في برنامجك مثل **قائمة الطعام في مطعم**: أقسام رئيسية (مقبلات، أطباق رئيسية، حلويات)، وتحت كل قسم أصناف.
في البرنامج: **File** وتحتها جديد وفتح وخروج، و **Edit** وتحتها نسخ ولصق...

## `MenuStrip` ومحرر القوائم خطوة بخطوة

1. من صندوق الأدوات ضع `MenuStrip` على النموذج. يذهب إلى **الصينية** تحت النموذج، ويظهر شريط قوائم في أعلى النموذج.
2. انقر `MenuStrip1` بالزر الأيمن > **Edit Menu...** (تحرير القائمة...). يفتح **Menu Editor** (محرر القوائم).
3. في المحرر شجرة بعمودين: النص (Text) والاسم (Name)، وأزرار:

| الزر | وظيفته |
|---|---|
| **Add Menu** | قائمة رئيسية جديدة (مثل "ملف") |
| **Add Item** | أمر داخل القائمة المحددة (مثل "جديد") |
| **Add Separator** | خط فاصل بين مجموعات الأوامر |
| **Delete** | حذف العنصر المحدد |
| **Move Up** / **Move Down** | تغيير الترتيب |

4. انقر الخلية **مرتين** لتعديل النص أو الاسم. النص `-` وحده يعني فاصلًا.
5. اضغط **OK**. القوائم تظهر في المصمم.

> 💡 **أسماء الأوامر:** المحرر يقترح أسماء تبدأ بـ `mnu`. اجعلها واضحة مثل `mnuFileNew` و `mnuEditCopy`، لأن المعالج سيحمل الاسم: `mnuFileNew_Click`.

### معالجات الأوامر

بعد تحرير القائمة، حدد `MenuStrip1` وافتح لسان **Events** في نافذة الخصائص: ستجد **كل أمر** في القائمة كحدث. انقره مرتين لإنشاء معالجه.
وتستطيع أيضًا نقر الأمر نفسه في القائمة الظاهرة على النموذج.

## مثال: محرر نصوص صغير

لاحظ في ملف `.frm` أن القوائم أدوات `VB.Menu` متداخلة. هذا ما ينتجه محرر القوائم عند الحفظ بصيغة VB6:

<!-- test: {"steps": [["menu", "mnuEditUpper"], ["menu", "mnuViewWrap"]], "expect": {"txtNote.Text": "HELLO MENUS", "mnuViewWrap.Checked": "True", "mnuEditUndo.Enabled": "False"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "محرر صغير"
   ClientWidth     =   5400
   ClientHeight    =   3000
   Begin VB.TextBox txtNote
      Text            =   "hello menus"
      MultiLine       =   -1  'True
      Left            =   120
      Top             =   120
      Width           =   5100
      Height          =   2700
   End
   Begin VB.Menu mnuFile
      Caption         =   "ملف"
      Begin VB.Menu mnuFileNew
         Caption         =   "جديد"
      End
      Begin VB.Menu mnuFileSep
         Caption         =   "-"
      End
      Begin VB.Menu mnuFileExit
         Caption         =   "خروج"
      End
   End
   Begin VB.Menu mnuEdit
      Caption         =   "تحرير"
      Begin VB.Menu mnuEditUpper
         Caption         =   "حروف كبيرة"
      End
      Begin VB.Menu mnuEditUndo
         Caption         =   "تراجع"
      End
   End
   Begin VB.Menu mnuView
      Caption         =   "عرض"
      Begin VB.Menu mnuViewWrap
         Caption         =   "التفاف النص"
      End
   End
End

Private Sub Form_Load()
    mnuEditUndo.Enabled = False
End Sub

Private Sub mnuFileNew_Click()
    txtNote.Text = ""
End Sub

Private Sub mnuFileExit_Click()
    Unload Me
End Sub

Private Sub mnuEditUpper_Click()
    txtNote.Text = UCase(txtNote.Text)
End Sub

Private Sub mnuViewWrap_Click()
    mnuViewWrap.Checked = Not mnuViewWrap.Checked
End Sub
```

- `Checked` يضع علامة ✓ بجانب الأمر، مفيد للخيارات التي تُشغَّل وتُطفأ.
- `Enabled = False` يجعل الأمر رماديًا، مثل "تراجع" عندما لا يوجد ما يُتراجع عنه. هنا عطّلناه في `Form_Load`، ويمكنك أيضًا ضبطه من نافذة الخصائص.

## نموذج ثانٍ

### إضافته

1. **Project > Add Windows Form...** (مشروع > إضافة نموذج Windows...)، أو انقر المشروع بالزر الأيمن في مستكشف الحلول > **Add > Windows Form...**.
2. اكتب اسمًا مثل `frmAbout` واضغط **OK**. في مشروع متعدد اللغات يمكنك اختيار لغة مختلفة لهذا النموذج وحده.
3. صممه كأي نموذج.

### فتحه من النموذج الأول

| ما تريد | BASIC | Python |
|---|---|---|
| إظهار النموذج | `Form2.Show` | `from Form2 import Form2` ثم `Form2(self.root)` |
| إظهاره وانتظار إغلاقه (حوار) | `Form2.Show vbModal` | — |
| إغلاق النموذج الحالي | `Unload Me` | `self.root.destroy()` |

### أي نموذج يبدأ به البرنامج؟

النموذج الأول في المشروع هو **نموذج البداية**. لتغييره: **Project > Project Properties...** > **Startup form**.

## مثال: نموذجان يتبادلان البيانات

الزر في `Form1` يكتب في عنوان داخل `Form2` ثم يُظهره. لاحظ علامتي `'#file:` اللتين تقسمان المثال إلى ملفين:

<!-- test: {"steps": [["set", "txtName", "Text", "كريم"], ["click", "cmdOpen"], ["form", "Form2"]], "expect": {"lblWelcome.Caption": "أهلًا يا كريم، هذا هو النموذج الثاني"}} -->
```vb form run
'#file: Form1.frm
Begin VB.Form Form1
   Caption         =   "النموذج الأول"
   ClientWidth     =   4800
   ClientHeight    =   1800
   Begin VB.TextBox txtName
      Left            =   240
      Top             =   240
      Width           =   2400
      Height          =   400
   End
   Begin VB.CommandButton cmdOpen
      Caption         =   "افتح النموذج الثاني"
      Left            =   240
      Top             =   840
      Width           =   2400
      Height          =   500
   End
End

Private Sub cmdOpen_Click()
    Form2.lblWelcome.Caption = "أهلًا يا " & txtName.Text & "، هذا هو النموذج الثاني"
    Form2.Show
End Sub
'#file: Form2.frm
Begin VB.Form Form2
   Caption         =   "النموذج الثاني"
   ClientWidth     =   5400
   ClientHeight    =   1400
   Begin VB.Label lblWelcome
      Left            =   240
      Top             =   240
      Width           =   4800
      Height          =   400
   End
End
```

## أخطاء شائعة

- **وضع `MenuStrip` ثم البحث عنه على النموذج:** هو في الصينية. القائمة نفسها تظهر في أعلى النموذج.
- **أمر قائمة بلا معالج:** يظهر ولا يفعل شيئًا. افتح لسان **Events** لـ `MenuStrip1` وأنشئ معالجه.
- **نسيان `Show`:** كتابة قيم في `Form2` لا تُظهره. اكتب `Form2.Show`.
- **البرنامج يبدأ بالنموذج الخطأ:** غيّر **Startup form** في خصائص المشروع.

## تمرين

### تمرين 1: أمر "حروف صغيرة"

أضف إلى قائمة "تحرير" أمرًا اسمه `mnuEditLower` نصه "حروف صغيرة"، يحوّل النص إلى حروف صغيرة بـ `LCase`.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "محرر صغير"
   ClientWidth     =   5400
   ClientHeight    =   3000
   Begin VB.TextBox txtNote
      Text            =   "HELLO"
      Left            =   120
      Top             =   120
      Width           =   5100
      Height          =   2700
   End
   Begin VB.Menu mnuEdit
      Caption         =   "تحرير"
      Begin VB.Menu mnuEditUpper
         Caption         =   "حروف كبيرة"
      End
   End
End

Private Sub mnuEditUpper_Click()
    txtNote.Text = UCase(txtNote.Text)
End Sub
```

<!-- test: {"steps": [["menu", "mnuEditLower"]], "expect": {"txtNote.Text": "hello"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "محرر صغير"
   ClientWidth     =   5400
   ClientHeight    =   3000
   Begin VB.TextBox txtNote
      Text            =   "HELLO"
      Left            =   120
      Top             =   120
      Width           =   5100
      Height          =   2700
   End
   Begin VB.Menu mnuEdit
      Caption         =   "تحرير"
      Begin VB.Menu mnuEditUpper
         Caption         =   "حروف كبيرة"
      End
      Begin VB.Menu mnuEditLower
         Caption         =   "حروف صغيرة"
      End
   End
End

Private Sub mnuEditUpper_Click()
    txtNote.Text = UCase(txtNote.Text)
End Sub

Private Sub mnuEditLower_Click()
    txtNote.Text = LCase(txtNote.Text)
End Sub
```

### مهمة عملية: نافذة "حول"

1. في مشروع BASIC ضع `MenuStrip`، وأنشئ بمحرر القوائم قائمة "مساعدة" فيها أمر "حول البرنامج" باسم `mnuHelpAbout`.
2. **Project > Add Windows Form...** وسمِّه `frmAbout`، وضع فيه عنوانًا وزر "إغلاق" يكتب `Unload Me`.
3. في معالج `mnuHelpAbout_Click` اكتب `frmAbout.Show vbModal`.
4. شغّل البرنامج وجرّب.

## اختبر نفسك

```quiz
{"question": "أين تجد أوامر القائمة لإنشاء معالجاتها؟", "choices": ["في لسان Events بعد تحديد MenuStrip1", "في نافذة Output", "في Tools > Options", "لا تحتاج معالجات"], "answer": 0, "explanation": "كل أمر في القائمة يظهر كحدث في لسان Events للـ MenuStrip."}
```

```quiz
{"question": "ما النص الذي يجعل عنصر القائمة فاصلًا؟", "choices": ["`|`", "`-`", "`*`", "`sep`"], "answer": 1, "explanation": "النص `-` وحده يعني خطًا فاصلًا."}
```

```quiz
{"question": "كيف تُظهر النموذج `Form2` من كود BASIC؟", "choices": ["`Form2.Open`", "`Form2.Show`", "`Show Form2()`", "`Load Form2.Visible`"], "answer": 1, "explanation": "`Form2.Show` تُظهره، و `Form2.Show vbModal` تُظهره كحوار ينتظر إغلاقه."}
```

## الخلاصة

- `MenuStrip` + **Edit Menu...** = محرر القوائم: **Add Menu** و **Add Item** و **Add Separator** و `-` للفاصل.
- معالجات الأوامر من لسان **Events**، واسمها `mnuX_Click`. `Checked` للعلامة و `Enabled` للتعطيل.
- **Project > Add Windows Form...** لنموذج جديد، و `Form2.Show` لفتحه، و **Startup form** في خصائص المشروع.
