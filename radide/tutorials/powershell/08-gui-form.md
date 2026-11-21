# الدرس 8: أول نافذة PowerShell في مصمم النماذج

حتى الآن كتبنا سكربتات تعمل في الكونسول ثم تنتهي. في هذا الدرس نبني **برنامجًا بنافذة وأزرار** بطريقة Visual Basic: نرسم النافذة في المصمم، ثم نكتب بلغة PowerShell ما يحدث عند كل ضغطة.

## البرمجة بالأحداث

في البرنامج الرسومي لا يسير الكود من أعلى لأسفل ثم ينتهي، بل **ينتظر** أفعال المستخدم. لكل فعل (ضغطة زر، كتابة نص، اختيار من قائمة) **حدث** (event)، ونكتب لكل حدث دالة تسمى **معالج الحدث** (event handler).

> **تشبيه:** البرنامج الرسومي مثل **لوحة المصعد**: لا يتحرك المصعد وحده، بل ينتظر. تضغط زر «3» فيذهب للطابق الثالث، وتضغط زر «فتح الباب» فيفتح. كل زر مربوط بعمل محدد.

## كيف يعمل «جسر الواجهة» (GUI Bridge)؟

1. الـ IDE **ترسم النافذة** التي صممتها.
2. سكربت PowerShell يعمل في الخلفية وينتظر.
3. عند الضغط على زر اسمه `btnHello` تستدعي الـ IDE الدالة `btnHello_Click` في سكربتك.
4. داخل الدالة تتعامل مع الأدوات كأنها **كائنات** PowerShell عادية:

| الكتابة | وظيفتها |
|---|---|
| `$txtName.Text` | تقرأ النص المكتوب في `txtName` |
| `$lblOut.Text = "مرحبا"` | تغيّر خاصية |
| `$lstLog.AddItem("سطر")` | تستدعي دالة في الأداة |
| `$lstLog.ListCount` / `$lstLog.ListIndex` | عدد العناصر / رقم العنصر المختار |
| `$btnGo.Enabled = $false` | تعطّل الزر |
| `RadToNumber $txtA.Text` | تحوّل نص الأداة إلى رقم |
| `MsgBox "تم"` | رسالة منبثقة |
| `InputBox "ما اسمك؟"` | مربع إدخال يُرجع ما كتبه المستخدم |
| `RadEnd` | تنهي البرنامج |

من أين جاءت المتغيرات `$txtName` و`$lblOut`؟ الـ IDE تولّد ملفًا اسمه `Form1_designer.ps1` فيه كائن لكل أداة رسمتها، باسمها نفسه. لا تعدّل هذا الملف بيدك، فالـ IDE تعيد كتابته كلما حفظت التصميم.

> **مهم:** كل قيمة «تسقط» من الدالة دون أن تُخزن في متغير تظهر في نافذة **Output** (المخرجات). هذا مفيد للتتبع: اكتب `"وصلنا هنا"` وحده في سطر فتراه في Output.

## خطوة بخطوة: برنامج الترحيب

1. **File > New Project...** ثم من مجموعة **.NET** اختر **PowerShell (GUI Bridge)** وسمّه `HelloPS`.
2. من **Toolbox** (صندوق الأدوات) ارسم الأدوات التالية، وغيّر **Name** و**Text** من نافذة **Properties** (الخصائص):

| الأداة | Name | Text |
|---|---|---|
| `Label` | `lblOut` | (فارغ) |
| `TextBox` | `txtName` | (فارغ) |
| `Button` | `btnHello` | `رحّب بي` |

3. **انقر مرتين** على الزر في المصمم، فتنشئ الـ IDE الدالة `btnHello_Click($e)` في الملف `Form1.ps1` وتضع المؤشر داخلها. اكتب:

<!-- test: {"set": {"txtName.Text": "يوسف"}, "events": ["btnHello.Click"], "expect": {"lblOut.Text": "أهلًا يا يوسف!"}, "captions": {"btnHello": "رحّب بي"}} -->
```powershell form run
# Event handlers for Form1.
function Form1_Load($e) {                 # عند ظهور النافذة
    $lblOut.Text = "اكتب اسمك ثم اضغط الزر"
}

function btnHello_Click($e) {             # عند الضغط على الزر
    $name = $txtName.Text.Trim()
    if ($name -eq "") {
        $lblOut.Text = "من فضلك اكتب اسمك أولًا"
    }
    else {
        $lblOut.Text = "أهلًا يا $name!"
    }
}
```

4. اضغط **F5** (أو **Debug > Start**)، اكتب اسمك واضغط الزر.

- اسم الدالة = **اسم الأداة + `_` + اسم الحدث**: `btnHello_Click`، `Form1_Load`، `tmrTick_Tick`.
- `Form1_Load` تعمل مرة واحدة عند ظهور النافذة.
- المعامل `$e` يحمل تفاصيل الحدث (مثل `$e.X` و`$e.Y` لموضع الفأرة)، وغالبًا لا نحتاجه.
- الـ IDE تولّد ملف `RadMain.ps1` الذي يحمّل ملفاتك وينتظر الأحداث، فلا تكتب أنت حلقة الانتظار.

## آلة حاسبة صغيرة

ارسم `txtA` و`txtB` والأزرار `btnAdd` و`btnMul` و`btnDiv` والعنوان `lblResult`:

<!-- test: {"set": {"txtA.Text": "9", "txtB.Text": "4"}, "events": ["btnDiv.Click"], "expect": {"lblResult.Text": "الناتج = 2.25"}, "captions": {"btnAdd": "+", "btnMul": "×", "btnDiv": "÷"}} -->
```powershell form run
function Show-Result($value) {
    $lblResult.Text = "الناتج = $value"
    "الناتج: $value"                  # يظهر في Output
}

function btnAdd_Click($e) {
    Show-Result ((RadToNumber $txtA.Text) + (RadToNumber $txtB.Text))
}

function btnMul_Click($e) {
    Show-Result ((RadToNumber $txtA.Text) * (RadToNumber $txtB.Text))
}

function btnDiv_Click($e) {
    $b = RadToNumber $txtB.Text
    if ($b -eq 0) {
        MsgBox "لا يمكن القسمة على صفر" | Out-Null
        return
    }
    Show-Result ((RadToNumber $txtA.Text) / $b)
}
```

```text output
الناتج: 2.25
```

- `Show-Result` دالة مساعدة عادية (ليست حدثًا لأن اسمها لا يطابق أداة)، تستدعيها الأحداث الثلاثة.
- لماذا `RadToNumber`؟ لأن `$txtA.Text` **نص**، و`"9" + "4"` في PowerShell تعطي `"94"`! والتحويل يجعل النص الفارغ صفرًا بدل أن يتوقف البرنامج.
- `MsgBox` تُرجع رقم الزر الذي ضُغط، لذلك نرسله إلى `Out-Null` لكي لا يظهر الرقم في Output.

## القوائم (ListBox)

ارسم `txtItem` و`btnAdd` و`btnRemove` و`lstItems` و`lblCount`:

<!-- test: {"events": [{"set": {"txtItem.Text": "حليب"}}, "btnAdd.Click", {"set": {"txtItem.Text": "خبز"}}, "btnAdd.Click", {"set": {"txtItem.Text": "جبن"}}, "btnAdd.Click", {"set": {"lstItems.ListIndex": "1"}}, "btnRemove.Click"], "expect": {"lstItems.items": "حليب|جبن", "lblCount.Text": "العناصر: 2"}, "captions": {"btnAdd": "أضف", "btnRemove": "احذف المختار"}} -->
```powershell form run
function Update-Count {
    $lblCount.Text = "العناصر: $($lstItems.ListCount)"
}

function btnAdd_Click($e) {
    $item = $txtItem.Text.Trim()
    if ($item) {
        $lstItems.AddItem($item)
        $txtItem.Text = ""
        Update-Count
    }
}

function btnRemove_Click($e) {
    $index = $lstItems.ListIndex
    if ($index -ge 0) {
        $lstItems.RemoveItem($index)
        Update-Count
    }
    else {
        MsgBox "اختر عنصرًا أولًا" | Out-Null
    }
}
```

> **انتبه:** ترقيم عناصر القائمة يبدأ من **0**، و`ListIndex` = `-1` تعني أن المستخدم لم يختر شيئًا.

## المؤقت (Timer) والمتغيرات التي تبقى بين الأحداث

ارسم أداة `Timer` باسم `tmrTick` وعنوانًا `lblTime`:

<!-- test: {"events": ["tmrTick.Tick", "tmrTick.Tick"], "expect": {"lblTime.Text": "الثواني: 2", "tmrTick.enabled": "True"}} -->
```powershell form run
$script:seconds = 0          # يحتفظ بقيمته بين الأحداث

function Form1_Load($e) {
    $tmrTick.Interval = 1000      # كل 1000 ملّي ثانية = ثانية
    $tmrTick.Enabled = $true
}

function tmrTick_Tick($e) {
    $script:seconds++
    $lblTime.Text = "الثواني: $script:seconds"
}
```

لماذا `$script:seconds` وليس `$seconds`؟ داخل الدالة، الكتابة `$seconds++` تنشئ متغيرًا **محليًا** جديدًا يختفي عند انتهاء الدالة، فيبقى العداد 1 إلى الأبد! البادئة `$script:` تعني «متغير السكربت كله»، فيحتفظ بقيمته طوال تشغيل البرنامج.

## أخطاء شائعة

- **`$count++` بدل `$script:count++`** داخل الحدث: العداد لا يزيد أبدًا. استخدم `$script:` لكل متغير يجب أن يبقى بين الأحداث.
- **جمع نصوص الأدوات مباشرة**: `$txtA.Text + $txtB.Text` يلصق النصين (`"94"`). حوّل بـ `RadToNumber` أولًا.
- **أرقام غريبة في Output**: سطر مثل `MsgBox "تم"` وحده يكتب `1` في Output لأن الدالة تُرجع قيمة. أضف `| Out-Null`.
- **تغيير اسم الأداة بعد كتابة الكود**: إذا غيّرت `Name` من `btnHello` إلى `btnGreet` يجب أن تغيّر اسم الدالة إلى `btnGreet_Click`، وإلا لن يحدث شيء عند الضغط.
- **تعديل `Form1_designer.ps1` بيدك**: تضيع تعديلاتك عند الحفظ التالي. عدّل التصميم من المصمم.

## تمارين

### التمرين 1

برنامج «مربع العدد»: يكتب المستخدم عددًا في `txtNum` ويضغط `btnSquare`، فيظهر في `lblResult`: `مربع 7 هو 49`.

<!-- test: {"set": {"txtNum.Text": "7"}, "events": ["btnSquare.Click"], "expect": {"lblResult.Text": "مربع 7 هو 49"}} -->
```powershell form exercise
function btnSquare_Click($e) {
}
```

<!-- test: {"set": {"txtNum.Text": "7"}, "events": ["btnSquare.Click"], "expect": {"lblResult.Text": "مربع 7 هو 49"}, "captions": {"btnSquare": "احسب المربع"}} -->
```powershell form solution
function btnSquare_Click($e) {
    $n = RadToNumber $txtNum.Text
    $lblResult.Text = "مربع $n هو $($n * $n)"
}
```

### التمرين 2

عدّاد ضغطات: كل ضغطة على `btnClick` تزيد العدد وتعرضه في `lblClicks` مثل `عدد الضغطات: 3`، وزر `btnReset` يعيده إلى صفر. وعند الضغطة العاشرة تظهر رسالة `وصلت إلى 10!`.

<!-- test: {"events": ["btnClick.Click", "btnClick.Click", "btnClick.Click", "btnReset.Click", "btnClick.Click"], "expect": {"lblClicks.Text": "عدد الضغطات: 1"}} -->
```powershell form exercise
$script:clicks = 0

function btnClick_Click($e) {
}

function btnReset_Click($e) {
}
```

<!-- test: {"events": ["btnClick.Click", "btnClick.Click", "btnClick.Click", "btnReset.Click", "btnClick.Click"], "expect": {"lblClicks.Text": "عدد الضغطات: 1"}, "captions": {"btnClick": "اضغطني", "btnReset": "صفّر"}} -->
```powershell form solution
$script:clicks = 0

function Show-Clicks {
    $lblClicks.Text = "عدد الضغطات: $script:clicks"
}

function btnClick_Click($e) {
    $script:clicks++
    Show-Clicks
    if ($script:clicks -eq 10) { MsgBox "وصلت إلى 10!" | Out-Null }
}

function btnReset_Click($e) {
    $script:clicks = 0
    Show-Clicks
}
```

## اختبر نفسك

```quiz
{"question": "ما اسم الدالة التي تعمل عند الضغط على زر اسمه btnSave؟", "choices": ["Click_btnSave", "btnSave_Click", "btnSave.Click", "OnSave"], "answer": 1, "explanation": "اسم المعالج = اسم الأداة + _ + اسم الحدث."}
```

```quiz
{"question": "عداد داخل حدث لا يزيد عن 1 مهما ضغطت. ما السبب الأرجح؟", "choices": ["الزر معطل", "استخدام $count بدل $script:count فيُنشأ متغير محلي جديد كل مرة", "PowerShell لا يدعم الجمع", "يجب استخدام Write-Host"], "answer": 1, "explanation": "المتغير الذي يبقى بين الأحداث يجب أن يكون في نطاق السكربت: $script:count."}
```

```quiz
{"question": "ما ناتج \"9\" + \"4\" إذا كانت القيمتان نصين من مربعي نص؟", "choices": ["13", "94", "خطأ", "0"], "answer": 1, "explanation": "الجمع على النصوص يلصقها. حوّل بـ RadToNumber أولًا."}
```

## الخلاصة

- معالج الحدث دالة باسم `اسمالأداة_الحدث($e)`، وتنشئها بالنقر المزدوج على الأداة.
- الأدوات كائنات جاهزة: `$txtName.Text` للقراءة، و`$lblOut.Text = ...` للكتابة، و`$lst.AddItem(...)` للدوال.
- `RadToNumber` للأرقام، و`MsgBox` و`InputBox` للحوار، و`| Out-Null` لإخفاء القيم المرجعة.
- `$script:name` للمتغيرات التي تبقى بين الأحداث.
