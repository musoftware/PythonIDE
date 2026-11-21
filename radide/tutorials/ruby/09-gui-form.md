# الدرس 9: أول نافذة Ruby في مصمم النماذج

كل برامجنا حتى الآن تعمل في الكونسول: نص يُطبع ونص يُقرأ. اليوم نبني برنامجًا **بنافذة وأزرار ومربعات نص**، بطريقة Visual Basic الشهيرة: ترسم النافذة بالسحب والإفلات، ثم تكتب كود Ruby الذي يعمل عند الضغط على الأزرار.

## البرمجة بالأحداث (Event-Driven Programming)

في برنامج الكونسول، البرنامج هو الذي يقود: يسأل ثم ينتظر الإجابة. أما في البرنامج الرسومي فـ **المستخدم** هو الذي يقود: قد يضغط أي زر في أي وقت. لذلك نكتب الكود على شكل **معالجات أحداث** (event handlers): دالة لكل **حدث** (event) تقول «عندما يحدث كذا، افعل كذا».

> **تشبيه:** برنامج الكونسول مثل موظف يملأ معك استمارة سؤالًا بعد سؤال. والبرنامج الرسومي مثل **النادل في المطعم**: لا يفعل شيئًا حتى تناديه، فإذا طلبت «عصير» أحضر العصير، وإذا طلبت «الحساب» أحضر الحساب.

## كيف يعمل «جسر الواجهة» (GUI Bridge)؟

1. **الـ IDE ترسم النافذة** التي صممتها في مصمم النماذج (Form Designer).
2. **برنامج Ruby** يعمل في الخلفية وينتظر الأحداث.
3. عندما يضغط المستخدم زرًا اسمه `btnHello`، ترسل الـ IDE الحدث إلى برنامجك فتُستدعى دالتك `btnHello_Click`.
4. داخل الدالة تقرأ الأدوات وتغيّرها بطريقة سهلة: `ui.txtName.Text` للقراءة، و`ui.lblOut.Text = "..."` للكتابة.

## أهم أدوات الجسر في Ruby

| الكتابة | وظيفتها |
|---|---|
| `ui.txtName.Text` | تقرأ النص المكتوب في الأداة `txtName` |
| `ui.lblOut.Text = "مرحبا"` | تغيّر خاصية في أداة |
| `ui.lstLog.AddItem("سطر")` | تستدعي دالة في أداة (هنا: إضافة عنصر لقائمة) |
| `Rad.get("txtA", "Text")` | مثل `ui.txtA.Text` بكتابة أخرى |
| `Rad.get_num("txtA", "Text")` | تقرأ الخاصية كرقم |
| `Rad.set("lblOut", "Text", "x")` | مثل `ui.lblOut.Text = "x"` |
| `msgbox "تم الحفظ"` | رسالة منبثقة |
| `Rad.input("ما اسمك؟")` | مربع إدخال يُرجع ما كتبه المستخدم |
| `Rad.quit` | تنهي البرنامج |

وأي شيء تطبعه بـ `puts` يظهر في نافذة **Output**، وهذا مفيد لتتبع ما يحدث.

## مشروعك الأول خطوة بخطوة: برنامج الترحيب

### 1) إنشاء المشروع

1. **File > New Project...** (ملف > مشروع جديد...).
2. من مجموعة **Scripting** اختر **Ruby (GUI Bridge)**، وسمّ المشروع `HelloRuby`.
3. تفتح الـ IDE النموذج **Form1** في وضع التصميم، ومعه ملف الكود `Form1.rb`.

### 2) رسم النافذة

من **Toolbox** (صندوق الأدوات) اسحب إلى النموذج الأدوات التالية، ثم غيّر خاصية **Name** لكل أداة من نافذة **Properties** (الخصائص):

| الأداة | Name | Text |
|---|---|---|
| `Label` | `lblOut` | (فارغ) |
| `TextBox` | `txtName` | (فارغ) |
| `Button` | `btnHello` | `رحّب بي` |

> **نصيحة:** اعتد على البادئات في الأسماء: `txt` لمربع النص، و`btn` للزر، و`lbl` للعنوان، و`lst` للقائمة، و`chk` لمربع الاختيار، و`tmr` للمؤقت. ستعرف نوع الأداة من اسمها فورًا.

### 3) كتابة الكود

**انقر مرتين** على الزر في المصمم، فتنشئ الـ IDE دالة الحدث `def btnHello_Click(e)` وتنقلك إليها. اكتب:

<!-- test: {"set": {"txtName.Text": "ريم"}, "events": ["btnHello.Click"], "expect": {"lblOut.Text": "أهلًا يا ريم!"}, "captions": {"btnHello": "رحّب بي"}} -->
```ruby form run
# Event handlers for Form1.
def Form1_Load(e)                  # تعمل مرة واحدة عند ظهور النافذة
  ui.lblOut.Text = "اكتب اسمك ثم اضغط الزر"
end

def btnHello_Click(e)              # تعمل عند الضغط على الزر
  name = ui.txtName.Text.strip
  if name.empty?
    ui.lblOut.Text = "من فضلك اكتب اسمك أولًا"
  else
    ui.lblOut.Text = "أهلًا يا #{name}!"
  end
end
```

### 4) التشغيل

اضغط **F5**. تظهر نافذتك؛ اكتب اسمك (مثلًا «ريم») واضغط الزر، فيظهر: **أهلًا يا ريم!**

لاحظ أن:

- اسم الدالة يجب أن يكون بالضبط **`اسمالأداة_اسمالحدث`**، مثل `btnHello_Click`. هكذا تربطها الـ IDE بالحدث.
- `Form1_Load` حدث خاص بالنموذج يعمل عند ظهوره، ومكانه المناسب لضبط القيم الابتدائية.
- المعامل `e` يحمل معلومات الحدث (مثل `e.X` و`e.Y` لموضع الفأرة)، ويمكنك تجاهله.
- لا تكتب أنت حلقة الانتظار: الـ IDE تولّد ملف `_radmain.rb` يحمّل كودك وينتظر الأحداث.

## مثال ثانٍ: آلة حاسبة

ارسم: `txtA` و`txtB` (مربعا نص)، وأربعة أزرار `btnAdd` و`btnSub` و`btnMul` و`btnDiv`، و`lblResult`. ولاحظ الدالة المساعدة `calculate` التي تمنع تكرار الكود في الأزرار الأربعة:

<!-- test: {"set": {"txtA.Text": "7", "txtB.Text": "2"}, "events": ["btnDiv.Click"], "expect": {"lblResult.Text": "الناتج = 3.5"}, "captions": {"btnAdd": "+", "btnSub": "-", "btnMul": "×", "btnDiv": "÷"}} -->
```ruby form run
# دالة مساعدة عادية (ليست حدثًا): تقرأ الرقمين وتحسب وتعرض الناتج
def calculate(op)
  a = Rad.get_num("txtA", "Text")
  b = Rad.get_num("txtB", "Text")
  if op == :/ && b == 0
    ui.lblResult.Text = "لا يمكن القسمة على صفر"
    return
  end
  result = a.to_f.public_send(op, b)
  result = result.to_i if result == result.to_i      # 4.0 تظهر 4
  ui.lblResult.Text = "الناتج = #{result}"
  puts "#{a} #{op} #{b} = #{result}"                  # يظهر في Output
end

def btnAdd_Click(e) = calculate(:+)
def btnSub_Click(e) = calculate(:-)
def btnMul_Click(e) = calculate(:*)
def btnDiv_Click(e) = calculate(:/)
```

```text output
7 / 2 = 3.5
```

- `def btnAdd_Click(e) = calculate(:+)` صيغة مختصرة لدالة من سطر واحد.
- `a.to_f.public_send(op, b)` تستدعي العملية المحفوظة في `op` (مثل `:+`) على الرقم. كل عملية حسابية في Ruby هي في الحقيقة دالة!

## القوائم والرسائل

ارسم `txtItem` و`btnAdd` و`btnCount` وقائمة `lstItems` (ListBox):

<!-- test: {"events": [{"set": {"txtItem.Text": "تفاح"}}, "btnAdd.Click", {"set": {"txtItem.Text": "موز"}}, "btnAdd.Click", {"set": {"txtItem.Text": " "}}, "btnAdd.Click", "btnCount.Click"], "expect": {"lstItems.items": "تفاح|موز", "lstItems.listcount": "2"}, "msgbox": ["اكتب شيئًا أولًا", "في القائمة 2 عنصر"], "captions": {"btnAdd": "أضف", "btnCount": "كم عنصرًا؟"}} -->
```ruby form run
def btnAdd_Click(e)
  item = ui.txtItem.Text.strip
  if item.empty?
    msgbox "اكتب شيئًا أولًا"
    return
  end
  ui.lstItems.AddItem(item)
  ui.txtItem.Text = ""          # امسح المربع للعنصر التالي
end

def btnCount_Click(e)
  count = Rad.get_num("lstItems", "ListCount")
  msgbox "في القائمة #{count} عنصر"
end
```

دوال القائمة `ListBox` المهمة: `AddItem(نص)` و`RemoveItem(رقم)` و`Clear` و`List(رقم)`، وخصائصها `ListCount` (عدد العناصر) و`ListIndex` (رقم العنصر المختار، و`-1` إذا لم يُختر شيء).

## المؤقت (Timer)

أداة `Timer` لا تظهر للمستخدم، لكنها تطلق الحدث `Tick` كل فترة (`Interval` بالملي ثانية). ارسم `Timer` باسم `tmrClock` و`lblTime`:

<!-- test: {"events": ["tmrClock.Tick", "tmrClock.Tick", "tmrClock.Tick"], "expect": {"lblTime.Text": "مرّت 3 ثانية", "tmrClock.interval": "1000", "tmrClock.enabled": "True"}} -->
```ruby form run
$seconds = 0                     # متغير عام: يحتفظ بقيمته بين الأحداث

def Form1_Load(e)
  Rad.set("tmrClock", "Interval", 1000)   # كل ثانية
  Rad.set("tmrClock", "Enabled", "True")  # شغّل المؤقت
end

def tmrClock_Tick(e)
  $seconds += 1
  ui.lblTime.Text = "مرّت #{$seconds} ثانية"
end
```

> **مهم:** برنامجك يظل يعمل طوال ظهور النافذة، لذلك المتغيرات العامة (التي تبدأ بـ `$`) تحتفظ بقيمتها بين حدث وآخر. أما المتغيرات المحلية داخل الدالة فتُنشأ من جديد مع كل حدث.

## أخطاء شائعة

### اسم الدالة لا يطابق اسم الأداة

إذا سمّيت الزر `btnHello` وكتبت `def btnhello_Click(e)` أو `def Button1_Click(e)` فلن يحدث شيء عند الضغط ولن يظهر خطأ! Ruby حساسة لحالة الأحرف. الحل الأسهل: انقر مرتين على الأداة في المصمم ودع الـ IDE تكتب اسم الدالة.

### نسيان أن `Text` نص دائمًا

`ui.txtA.Text + ui.txtB.Text` تعطي `"52"` إذا كتبت 5 و2، لأنها تلصق نصين. استخدم `Rad.get_num` أو `.to_f`.

### الخطأ داخل حدث

إذا حدث خطأ داخل دالة حدث، لا ينهار البرنامج: تظهر رسالة مثل `[Ruby] error in btnAdd_Click: ...` في نافذة Output ويستمر البرنامج. اقرأ الرسالة ورقم السطر.

## تمارين

### التمرين 1

برنامج تحويل العملة: المستخدم يكتب مبلغًا بالدولار في `txtUsd` ويضغط `btnConvert`، فيظهر في `lblEgp` المبلغ بالجنيه (سعر الدولار 50 جنيهًا) بالشكل: `100 دولار = 5000 جنيه`.

<!-- test: {"set": {"txtUsd.Text": "100"}, "events": ["btnConvert.Click"], "expect": {"lblEgp.Text": "100 دولار = 5000 جنيه"}} -->
```ruby form exercise
RATE = 50

def btnConvert_Click(e)
  # اقرأ txtUsd واكتب الناتج في lblEgp
end
```

<!-- test: {"set": {"txtUsd.Text": "100"}, "events": ["btnConvert.Click"], "expect": {"lblEgp.Text": "100 دولار = 5000 جنيه"}, "captions": {"btnConvert": "حوّل"}} -->
```ruby form solution
RATE = 50

def btnConvert_Click(e)
  usd = Rad.get_num("txtUsd", "Text")
  ui.lblEgp.Text = "#{usd} دولار = #{usd * RATE} جنيه"
end
```

### التمرين 2

عدّاد ضغطات: زر `btnClick` كلما ضُغط زاد العداد ويظهر في `lblCount` النص `عدد الضغطات: N`، وزر `btnReset` يعيده للصفر.

<!-- test: {"events": ["btnClick.Click", "btnClick.Click", "btnClick.Click", "btnReset.Click", "btnClick.Click"], "expect": {"lblCount.Text": "عدد الضغطات: 1"}} -->
```ruby form exercise
$count = 0

def btnClick_Click(e)
end

def btnReset_Click(e)
end
```

<!-- test: {"events": ["btnClick.Click", "btnClick.Click", "btnClick.Click", "btnReset.Click", "btnClick.Click"], "expect": {"lblCount.Text": "عدد الضغطات: 1"}, "captions": {"btnClick": "اضغطني", "btnReset": "صفّر"}} -->
```ruby form solution
$count = 0

def show_count
  ui.lblCount.Text = "عدد الضغطات: #{$count}"
end

def btnClick_Click(e)
  $count += 1
  show_count
end

def btnReset_Click(e)
  $count = 0
  show_count
end
```

## اختبر نفسك

```quiz
{"question": "ما اسم الدالة التي تعمل عند الضغط على زر اسمه btnSave؟", "choices": ["save_click", "btnSave_Click", "Click_btnSave", "on_btnSave"], "answer": 1, "explanation": "اسم المعالج = اسم الأداة + _ + اسم الحدث."}
```

```quiz
{"question": "متى يعمل Form1_Load؟", "choices": ["عند كل ضغطة زر", "مرة واحدة عند ظهور النافذة", "عند إغلاق النافذة", "كل ثانية"], "answer": 1, "explanation": "Load حدث النموذج الذي يعمل عند ظهوره، وهو مكان القيم الابتدائية."}
```

```quiz
{"question": "لماذا نستخدم $count بدل count في عدّاد الضغطات؟", "choices": ["لأنه أسرع", "لأن المتغير العام يحتفظ بقيمته بين الأحداث", "لأن Ruby تمنع count", "لا فرق"], "answer": 1, "explanation": "المتغير المحلي داخل الدالة يُنشأ من جديد مع كل حدث، أما العام فيبقى."}
```

## الخلاصة

- البرنامج الرسومي يتكون من معالجات أحداث `اسمالأداة_الحدث`.
- `ui.txtName.Text` للقراءة، و`ui.lblOut.Text = ...` للكتابة، و`Rad.get_num` للأرقام.
- `msgbox` للرسائل، و`Rad.input` للسؤال، و`AddItem` / `ListCount` للقوائم.
- `Timer` يطلق `Tick` كل `Interval` ملي ثانية بعد تفعيله.
- `puts` داخل الأحداث يكتب في نافذة Output للتتبع.
