# الدرس 14: الأدوات والأحداث: القوائم والاختيارات والمؤقت

في الدرس السابق استخدمنا مربع النص والزر والعنوان. اليوم نتعرف على أدوات أكثر: **القائمة** `ListBox`، و**القائمة المنسدلة** `ComboBox`، و**مربع الاختيار** `CheckBox`، و**زر الخيار** `RadioButton`، و**المؤقت** `Timer`، مع الرسائل ومربعات الإدخال.

## القائمة `ListBox`

| الكود | معناه |
|---|---|
| `lstNames.AddItem("علي")` | يضيف عنصرًا في النهاية |
| `lstNames.RemoveItem(2)` | يحذف العنصر رقم 2 (الترقيم من 0) |
| `lstNames.Clear()` | يحذف كل العناصر |
| `lstNames.ListCount` | عدد العناصر |
| `lstNames.ListIndex` | رقم العنصر المختار (`-1` إذا لا يوجد اختيار) |
| `lstNames.Text` | نص العنصر المختار |
| `lstNames.List(i)` | نص العنصر رقم `i` |

ارسم: `TextBox` باسم `txtItem`، و`Button` باسم `btnAdd`، و`Button` باسم `btnRemove`، و`ListBox` باسم `lstItems`، و`Label` باسم `lblCount`.

<!-- test: {"items": {"lstItems": ["خبز"]}, "set": {"txtItem.Text": "حليب"}, "events": ["btnAdd Click", "btnAdd Click"], "msgbox": ["اكتب اسم العنصر أولًا"], "expect": {"lstItems.ListCount": "2", "lblCount.Text": "عدد العناصر: 2", "txtItem.Text": ""}} -->
```csharp form run
public static partial class Form1
{
    static void UpdateCount()
    {
        lblCount.Text = $"عدد العناصر: {lstItems.ListCount}";
    }

    static void btnAdd_Click(RadEvent e)
    {
        string item = txtItem.Text.Trim();
        if (item == "")
        {
            MsgBox("اكتب اسم العنصر أولًا");
            return;
        }
        lstItems.AddItem(item);
        txtItem.Text = "";
        txtItem.SetFocus();
        UpdateCount();
    }

    static void btnRemove_Click(RadEvent e)
    {
        int i = lstItems.ListIndex;
        if (i < 0)
        {
            MsgBox("اختر عنصرًا من القائمة أولًا");
            return;
        }
        lstItems.RemoveItem(i);
        UpdateCount();
    }
}
```

### حدث تغيير الاختيار

الحدث الافتراضي للقائمة هو `SelectedIndexChanged`: يعمل كلما اختار المستخدم عنصرًا آخر.

<!-- test: {"items": {"lstCities": ["Cairo", "Giza", "Aswan"]}, "set": {"lstCities.ListIndex": "2"}, "events": ["lstCities SelectedIndexChanged"], "expect": {"lblChoice.Text": "اخترت: Aswan (رقم 2)"}} -->
```csharp form run
public static partial class Form1
{
    static void Form1_Load(RadEvent e)
    {
        lstCities.AddItem("Cairo");
        lstCities.AddItem("Giza");
        lstCities.AddItem("Aswan");
    }

    static void lstCities_SelectedIndexChanged(RadEvent e)
    {
        lblChoice.Text = $"اخترت: {lstCities.Text} (رقم {lstCities.ListIndex})";
    }
}
```

## القائمة المنسدلة `ComboBox`

تعمل مثل `ListBox` (نفس `AddItem` و`ListIndex` و`Text`)، لكنها تأخذ مساحة سطر واحد وتنسدل عند الضغط. ويمكن ملء عناصرها من المصمم: خاصية **Items** في نافذة الخصائص، عنصر في كل سطر.

<!-- test: {"set": {"cboSize.Text": "كبير", "txtQty.Text": "3"}, "events": ["btnPrice Click"], "expect": {"lblPrice.Text": "السعر: 135 جنيه"}} -->
```csharp form run
public static partial class Form1
{
    static void Form1_Load(RadEvent e)
    {
        cboSize.AddItem("صغير");
        cboSize.AddItem("وسط");
        cboSize.AddItem("كبير");
    }

    static void btnPrice_Click(RadEvent e)
    {
        int unit = cboSize.Text switch
        {
            "صغير" => 25,
            "وسط" => 35,
            "كبير" => 45,
            _ => 0
        };
        if (unit == 0)
        {
            lblPrice.Text = "اختر الحجم";
            return;
        }
        int qty = ToInt(txtQty.Text);
        lblPrice.Text = $"السعر: {unit * qty} جنيه";
    }
}
```

## مربع الاختيار وزر الخيار

- `CheckBox`: اختيار مستقل (نعم / لا). قيمته في الخاصية `Value`: `"1"` إذا كان مُعلّمًا و`"0"` إذا لم يكن.
- `RadioButton`: مجموعة خيارات لا يُختار منها إلا واحد. قيمته `Value` تكون `"True"` للمختار.
- الدالة `ToBool(text)` تحول `"1"` و`"True"` إلى `true`.

ارسم `TextBox` باسم `txtText`، و`CheckBox` باسم `chkUpper` (Text: أحرف كبيرة)، و`CheckBox` باسم `chkTrim` (Text: حذف المسافات)، و`RadioButton` باسم `optBrackets` (Text: أقواس)، و`Button` باسم `btnApply`، و`Label` باسم `lblOut`.

<!-- test: {"set": {"txtText.Text": "  hello  ", "chkUpper.Value": "1", "chkTrim.Value": "1", "optBrackets.Value": "True"}, "events": ["btnApply Click"], "expect": {"lblOut.Text": "[HELLO]"}} -->
```csharp form run
public static partial class Form1
{
    static void btnApply_Click(RadEvent e)
    {
        string s = txtText.Text;
        if (ToBool(chkTrim.Value))
            s = s.Trim();
        if (ToBool(chkUpper.Value))
            s = s.ToUpper();
        if (ToBool(optBrackets.Value))
            s = "[" + s + "]";
        lblOut.Text = s;
    }
}
```

## المؤقت `Timer`

المؤقت أداة **غير مرئية**: تظهر أسفل المصمم وليس على النافذة. كل فترة (خاصية `Interval` بالمللي ثانية، و1000 = ثانية واحدة) يطلق الحدث `Tick` ما دامت خاصيته `Enabled` صحيحة.

ارسم `Timer` باسم `tmrClock` (Interval = 1000، Enabled = False)، و`Label` باسم `lblTime`، و`Button` باسم `btnStart`، و`Button` باسم `btnStop`.

<!-- test: {"events": ["btnStart Click", "tmrClock Tick", "tmrClock Tick", "tmrClock Tick"], "expect": {"lblTime.Text": "00:03", "tmrClock.Enabled": "True"}} -->
```csharp form run
public static partial class Form1
{
    static int seconds = 0;

    static void btnStart_Click(RadEvent e)
    {
        seconds = 0;
        lblTime.Text = "00:00";
        tmrClock.Enabled = true;
    }

    static void btnStop_Click(RadEvent e)
    {
        tmrClock.Enabled = false;
        MsgBox($"توقفت ساعة الإيقاف عند {lblTime.Text}");
    }

    static void tmrClock_Tick(RadEvent e)
    {
        seconds++;
        lblTime.Text = $"{seconds / 60:D2}:{seconds % 60:D2}";
    }
}
```

`{x:D2}` تطبع العدد الصحيح في خانتين على الأقل مع صفر في البداية (`03`).

## الرسائل ومربعات الإدخال

```csharp
MsgBox("تم الحفظ بنجاح");                 // رسالة
string name = InputBox("ما اسمك؟");        // سؤال يرجع النص (فارغ إذا ضغط إلغاء)
```

<!-- test: {"input": ["Hana"], "events": ["btnAsk Click"], "msgbox": ["مرحبًا Hana، اسمك فيه 4 حروف"], "expect": {"lblName.Text": "Hana"}} -->
```csharp form run
public static partial class Form1
{
    static void btnAsk_Click(RadEvent e)
    {
        string name = InputBox("ما اسمك؟");
        if (string.IsNullOrWhiteSpace(name))
            return;
        lblName.Text = name;
        MsgBox($"مرحبًا {name}، اسمك فيه {name.Length} حروف");
    }
}
```

## أحداث أخرى مفيدة

| الحدث | متى يعمل |
|---|---|
| `Form1_Load` | عند ظهور النموذج |
| `txtX_TextChanged` | كلما تغير النص في مربع النص |
| `chkX_CheckedChanged` | عند تعليم مربع الاختيار أو إلغائه |
| `lstX_DoubleClick` | نقر مزدوج على القائمة |
| `picX_MouseMove` | حركة الفأرة (`e.X` و`e.Y`) |
| `Form1_KeyDown` | ضغط مفتاح (`e.KeyCode`) |

لترى كل أحداث أداة: اخترها في المصمم، ثم انقر أيقونة **الأحداث** (البرق) في نافذة Properties، وانقر مرتين على الحدث لإنشاء دالته.

## أخطاء شائعة

- **قراءة `ListIndex` دون فحص `-1`:** إذا لم يختر المستخدم شيئًا ثم استدعيت `RemoveItem(-1)` فلن يحدث ما تريد. افحص دائمًا `if (i < 0)`.
- **نسيان تفعيل المؤقت:** المؤقت لا يعمل إلا إذا كان `Enabled = true`، والفترة `Interval` أكبر من صفر.
- **مقارنة `chkX.Value == "True"`:** قيمة مربع الاختيار `"1"` أو `"0"`، فاستخدم `ToBool(...)` التي تقبل الصيغتين.

## تمارين

### التمرين 1

قائمة أرقام: مربع نص `txtNumber`، وزر `btnAdd` يضيف الرقم إلى `lstNumbers`، وزر `btnSum` يكتب مجموع كل الأرقام في `lblSum` بالشكل `المجموع = 60`. استخدم `lstNumbers.List(i)` و`lstNumbers.ListCount`.

<!-- test: {"items": {"lstNumbers": ["10", "20", "30"]}, "events": ["btnSum Click"], "expect": {"lblSum.Text": "المجموع = 60"}} -->
```csharp form exercise
public static partial class Form1
{
    static void btnAdd_Click(RadEvent e)
    {
    }

    static void btnSum_Click(RadEvent e)
    {
    }
}
```

<!-- test: {"items": {"lstNumbers": ["10", "20", "30"]}, "events": ["btnSum Click"], "expect": {"lblSum.Text": "المجموع = 60"}} -->
```csharp form solution
public static partial class Form1
{
    static void btnAdd_Click(RadEvent e)
    {
        lstNumbers.AddItem(txtNumber.Text);
        txtNumber.Text = "";
    }

    static void btnSum_Click(RadEvent e)
    {
        double sum = 0;
        for (int i = 0; i < lstNumbers.ListCount; i++)
            sum += ToNumber(lstNumbers.List(i));
        lblSum.Text = $"المجموع = {sum}";
    }
}
```

### التمرين 2

عدّ تنازلي: `Timer` باسم `tmrDown`، و`Label` باسم `lblLeft`، و`Button` باسم `btnGo`. عند الضغط يبدأ العد من 5، ومع كل `Tick` ينقص واحدًا، وعند الصفر يتوقف المؤقت ويكتب `انطلق!`.

<!-- test: {"events": ["btnGo Click", "tmrDown Tick", "tmrDown Tick", "tmrDown Tick", "tmrDown Tick", "tmrDown Tick"], "expect": {"lblLeft.Text": "انطلق!", "tmrDown.Enabled": "False"}} -->
```csharp form exercise
public static partial class Form1
{
    static int left;

    static void btnGo_Click(RadEvent e)
    {
    }

    static void tmrDown_Tick(RadEvent e)
    {
    }
}
```

<!-- test: {"events": ["btnGo Click", "tmrDown Tick", "tmrDown Tick", "tmrDown Tick", "tmrDown Tick", "tmrDown Tick"], "expect": {"lblLeft.Text": "انطلق!", "tmrDown.Enabled": "False"}} -->
```csharp form solution
public static partial class Form1
{
    static int left;

    static void btnGo_Click(RadEvent e)
    {
        left = 5;
        lblLeft.Text = left.ToString();
        tmrDown.Enabled = true;
    }

    static void tmrDown_Tick(RadEvent e)
    {
        left--;
        if (left <= 0)
        {
            tmrDown.Enabled = false;
            lblLeft.Text = "انطلق!";
        }
        else
        {
            lblLeft.Text = left.ToString();
        }
    }
}
```

## اختبر نفسك

```quiz
{"question": "ماذا يعني lstNames.ListIndex == -1؟", "choices": ["القائمة فيها عنصر واحد", "لا يوجد عنصر مختار", "آخر عنصر مختار", "القائمة ممتلئة"], "answer": 1, "explanation": "‎-1 تعني أن المستخدم لم يختر أي عنصر."}
```

```quiz
{"question": "أي حدث يطلقه المؤقت Timer كل فترة؟", "choices": ["Click", "Load", "Tick", "Change"], "answer": 2, "explanation": "المؤقت يطلق Tick كل Interval مللي ثانية ما دام Enabled صحيحًا."}
```

```quiz
{"question": "ما الفرق بين CheckBox وRadioButton؟", "choices": ["لا فرق", "مربعات الاختيار مستقلة، أما أزرار الخيار فيُختار منها واحد فقط", "RadioButton للأرقام فقط", "CheckBox لا يملك أحداثًا"], "answer": 1, "explanation": "يمكن تعليم عدة CheckBox معًا، أما RadioButton في نفس المجموعة فخيار واحد فقط."}
```

## الخلاصة

- `ListBox` و`ComboBox`: `AddItem` و`RemoveItem` و`Clear` و`ListCount` و`ListIndex` و`Text` و`List(i)`.
- `CheckBox` و`RadioButton`: الخاصية `Value` مع `ToBool(...)`.
- `Timer`: `Interval` و`Enabled` والحدث `Tick`.
- `MsgBox` و`InputBox` للتواصل مع المستخدم، ونافذة Properties تعرض كل الأحداث.
