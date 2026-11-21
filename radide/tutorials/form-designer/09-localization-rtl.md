# الدرس 9: ترجمة النماذج والاتجاه من اليمين إلى اليسار

**في هذا الدرس ستتعلم:**

- جعل النموذج **قابلًا للترجمة** (`Localizable = True`) وتصميم نسخة لكل لغة.
- خاصيتي **`RightToLeft`** و **`RightToLeftLayout`** لنافذة عربية حقيقية.
- نافذة **Format > Localization Strings...** لترجمة كل النصوص في جدول واحد.
- كيف يختار البرنامج لغته عند التشغيل، وكيف يبدّلها أثناء العمل.

## نافذة واحدة بأكثر من لسان

تخيّل لافتة محل فيها وجهان: وجه بالعربية ووجه بالإنجليزية. اللافتة واحدة، لكن الوجه الظاهر يتبع الزبون.
النموذج القابل للترجمة كذلك: **تصميم واحد** (الأدوات وأماكنها)، و**جدول نصوص لكل لغة**. البرنامج يعرض الجدول المناسب للمستخدم.

> 💡 الترجمة ومرآة الاتجاه تُولَّدان لمشروعات **Python (Tkinter)** و **Python (PySide6 / Qt)**، على طريقة Visual Basic 2005.

## الخطوة 1: اجعل النموذج قابلًا للترجمة

1. افتح النموذج في المصمم، وانقر مكانًا فارغًا منه لتحديد **النموذج نفسه**.
2. في نافذة الخصائص اجعل **`Localizable`** = `True`.
3. ظهرت خاصية **`Language`**، وقيمتها `(Default)` أي "النصوص الأساسية".

## الخطوة 2: صمّم النسخة العربية

1. غيّر **`Language`** إلى `Arabic (ar)`.
2. الآن كل نص تكتبه يذهب إلى **الجدول العربي**، والنصوص الأساسية تبقى كما هي:
   - `Text` لكل أداة وللنموذج، و `ToolTip`، و `Items` للقوائم، و `TabPages` و `Columns`.
3. اكتب: عنوان النموذج `بيانات العميل`، والزر `حفظ`، والعنوان `الاسم:` ...
4. ارجع إلى `(Default)`: ترى النصوص الإنجليزية الأصلية. ارجع إلى `Arabic (ar)`: ترى العربية.

## الخطوة 3: الاتجاه من اليمين إلى اليسار

وأنت على `Language = Arabic (ar)`:

| الخاصية | القيمة | النتيجة |
|---|---|---|
| **`RightToLeft`** | `True` | النص يُقرأ من اليمين، ومحاذاته يمين، وشريط التمرير على اليسار |
| **`RightToLeftLayout`** | `True` | **النموذج كله ينعكس كالمرآة**: ما كان على اليسار يصبح على اليمين |

الخاصيتان تُحفظان **لكل لغة**: النسخة العربية معكوسة، والإنجليزية من اليسار إلى اليمين. استخدم `RightToLeftLayout` مع `RightToLeft` معًا.

> ⚠️ **لا ترسم نموذجًا ثانيًا للعربية.** نموذج واحد معكوس أسهل في الصيانة: إذا أضفت زرًّا يظهر في اللغتين.

## الخطوة 4: جدول الترجمة

**Format > Localization Strings...** (تنسيق > نصوص الترجمة...) يفتح جدولًا فيه **كل نص قابل للترجمة** في النموذج: صف لكل نص، وعمود لكل لغة.

| الزر | الاسم العربي | وظيفته |
|---|---|---|
| **Add Language** | إضافة لغة | عمود جديد للغة أخرى، مثل الفرنسية |
| **Remove Language** | إزالة لغة | حذف عمود لغة |
| **Import .resx.json...** | استيراد ‎.resx.json... | استيراد ترجمة أرسلها لك مترجم |
| **Mirror** | عكس الاتجاه | تفعيل الاتجاه من اليمين إلى اليسار للغة المحددة |

هذا الجدول أسرع من تحديد كل أداة على حدة، ويريك النصوص التي لم تُترجم بعد.

## ماذا يُحفظ؟

- داخل `Form1.form` تُحفظ الجداول تحت `resources`.
- وعند الحفظ يُكتب ملف لكل لغة بجانب النموذج: `Form1.ar.resx.json`.

هكذا يبدو الجدول العربي (مختصرًا):

```text
{"ar": {"name": "Arabic", "RightToLeft": true, "RightToLeftLayout": true,
        "strings": {"$this.Text": "بيانات العميل", "lblName.Text": "الاسم:", "btnSave.Text": "حفظ"}}}
```

`$this` تعني النموذج نفسه. وأي مترجم يستطيع تعديل ملف `.resx.json` دون أن يلمس الكود؛ ضعه بجانب البرنامج فيضيف لغة أو يصحح ترجمة.

## كيف يختار البرنامج لغته؟

عند التشغيل يبحث البرنامج بالترتيب:

1. متغير البيئة `RADIDE_LANG` (مثل `ar`).
2. ملف `language.txt` بجانب البرنامج، فيه رمز اللغة.
3. لغة واجهة ويندوز.

وللتبديل **أثناء التشغيل** (زر "English / عربي" مثلًا):

```python
    def btnLang_Click(self):
        new = "en" if self.CurrentLanguage == "ar" else "ar"
        self.ApplyLanguage(new)
```

`ApplyLanguage` يغيّر النصوص والاتجاه فورًا، و `CurrentLanguage` يخبرك باللغة الحالية.

## الفكرة نفسها بكود بسيط

جدول ترجمة هو في الحقيقة "قاموس": مفتاح ← نص لكل لغة. هذا برنامج BASIC صغير يحاكي ما يفعله النموذج المترجم:

```vb run
Function Tr(key As String, lang As String) As String
    If lang = "ar" Then
        Select Case key
            Case "$this.Text": Tr = "بيانات العميل"
            Case "lblName.Text": Tr = "الاسم:"
            Case "btnSave.Text": Tr = "حفظ"
        End Select
    Else
        Select Case key
            Case "$this.Text": Tr = "Customer"
            Case "lblName.Text": Tr = "Name:"
            Case "btnSave.Text": Tr = "Save"
        End Select
    End If
End Function

Sub Main()
    Dim lang As String
    lang = "ar"
    Debug.Print Tr("$this.Text", lang) & " | " & Tr("lblName.Text", lang) & " | " & Tr("btnSave.Text", lang)
    lang = "en"
    Debug.Print Tr("$this.Text", lang) & " | " & Tr("lblName.Text", lang) & " | " & Tr("btnSave.Text", lang)
End Sub
```

```text output
بيانات العميل | الاسم: | حفظ
Customer | Name: | Save
```

## أخطاء شائعة

- **الكتابة والـ Language على (Default) وأنت تظنها عربية:** النص يغيّر الأصل الإنجليزي. انظر إلى قيمة `Language` قبل الكتابة.
- **`RightToLeftLayout` بدون `RightToLeft`:** الأماكن تنعكس لكن النص يبقى محاذى لليسار. فعّل الاثنين.
- **نصوص مكتوبة في الكود:** `MsgBox "Saved"` لا يظهر في جدول الترجمة. اجعل نصوص الكود تتبع `CurrentLanguage`.
- **نسيان الحفظ قبل إرسال الملفات للمترجم:** ملفات `.resx.json` تُكتب عند الحفظ.

## تمرين

### تمرين 1: أضف الفرنسية

أضف إلى الدالة `Tr` لغة ثالثة `fr`: `Client` و `Nom :` و `Enregistrer`، واطبع السطر الفرنسي فقط.

```vb exercise
Function Tr(key As String, lang As String) As String
    If lang = "ar" Then
        Select Case key
            Case "$this.Text": Tr = "بيانات العميل"
            Case "lblName.Text": Tr = "الاسم:"
            Case "btnSave.Text": Tr = "حفظ"
        End Select
    Else
        Select Case key
            Case "$this.Text": Tr = "Customer"
            Case "lblName.Text": Tr = "Name:"
            Case "btnSave.Text": Tr = "Save"
        End Select
    End If
End Function

Sub Main()
    Dim lang As String
    lang = "fr"
    Debug.Print Tr("$this.Text", lang) & " | " & Tr("lblName.Text", lang) & " | " & Tr("btnSave.Text", lang)
End Sub
```

```vb solution
Function Tr(key As String, lang As String) As String
    If lang = "ar" Then
        Select Case key
            Case "$this.Text": Tr = "بيانات العميل"
            Case "lblName.Text": Tr = "الاسم:"
            Case "btnSave.Text": Tr = "حفظ"
        End Select
    ElseIf lang = "fr" Then
        Select Case key
            Case "$this.Text": Tr = "Client"
            Case "lblName.Text": Tr = "Nom :"
            Case "btnSave.Text": Tr = "Enregistrer"
        End Select
    Else
        Select Case key
            Case "$this.Text": Tr = "Customer"
            Case "lblName.Text": Tr = "Name:"
            Case "btnSave.Text": Tr = "Save"
        End Select
    End If
End Function

Sub Main()
    Dim lang As String
    lang = "fr"
    Debug.Print Tr("$this.Text", lang) & " | " & Tr("lblName.Text", lang) & " | " & Tr("btnSave.Text", lang)
End Sub
```

```text output
Client | Nom : | Enregistrer
```

### مهمة عملية: نموذج بلغتين

1. في مشروع **Python (Tkinter)** صمّم نموذجًا فيه `lblName` و `txtName` و `btnSave` و `btnLang` بنصوص إنجليزية.
2. اجعل `Localizable = True`، ثم `Language = Arabic (ar)`، واكتب النصوص العربية، واجعل `RightToLeft` و `RightToLeftLayout` = `True`.
3. افتح **Format > Localization Strings...** وتأكد أن كل الصفوف مترجمة.
4. اكتب معالج `btnLang_Click` كما في الدرس، وشغّل البرنامج وبدّل اللغة.

## اختبر نفسك

```quiz
{"question": "ما الفرق بين `RightToLeft` و `RightToLeftLayout`؟", "choices": ["لا فرق", "الأولى لاتجاه النص ومحاذاته، والثانية تعكس أماكن الأدوات كالمرآة", "الأولى للأزرار والثانية للعناوين", "الثانية تترجم النصوص تلقائيًا"], "answer": 1, "explanation": "RightToLeft للنص، و RightToLeftLayout يعكس النموذج كله. استخدمهما معًا للعربية."}
```

```quiz
{"question": "ماذا يعني `Language = (Default)` في خصائص نموذج قابل للترجمة؟", "choices": ["اللغة العربية", "النصوص الأساسية للنموذج", "لغة ويندوز", "لا توجد نصوص"], "answer": 1, "explanation": "(Default) هي النصوص الأصلية، وكل لغة أخرى لها جدولها."}
```

```quiz
{"question": "كيف يبدّل البرنامج المولَّد لغته أثناء التشغيل؟", "choices": ["بإعادة تثبيته", "`self.ApplyLanguage(\"ar\")`", "بحذف ملف .form", "لا يمكن"], "answer": 1, "explanation": "ApplyLanguage يغيّر النصوص والاتجاه فورًا."}
```

## الخلاصة

- `Localizable = True` ثم `Language` لاختيار اللغة التي تصممها، والتصميم واحد لكل اللغات.
- `RightToLeft` + `RightToLeftLayout` = نافذة عربية معكوسة، وتُحفظان لكل لغة.
- **Format > Localization Strings...** جدول كل النصوص، وملف `Form1.ar.resx.json` لكل لغة.
- البرنامج يختار لغته من `RADIDE_LANG` ثم `language.txt` ثم ويندوز، و `ApplyLanguage` يبدّلها حيًا.
