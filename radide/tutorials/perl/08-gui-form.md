# الدرس 8: أول نافذة Perl في مصمم النماذج

Perl لغة نصوص في الأساس، لكن RAD IDE تسمح لك أن تبني بها **برنامجًا بنافذة وأزرار** بطريقة Visual Basic: ترسم النافذة في المصمم، ثم تكتب في Perl ما يحدث عند كل ضغطة.

## البرمجة بالأحداث

في البرنامج الرسومي لا يسير الكود من أعلى لأسفل ثم ينتهي، بل **ينتظر** أفعال المستخدم. لكل فعل (ضغطة زر، كتابة نص، اختيار من قائمة) **حدث** (event)، ونكتب لكل حدث دالة تسمى **معالج الحدث** (event handler).

> **تشبيه:** البرنامج الرسومي مثل **موظف الاستعلامات**: يجلس منتظرًا، فإذا سأله شخص عن «المواعيد» أجاب عن المواعيد، وإذا سأله عن «الأسعار» أجاب عن الأسعار.

## «جسر الواجهة» (GUI Bridge) في Perl

1. الـ IDE **ترسم النافذة**.
2. برنامج Perl يعمل في الخلفية وينتظر.
3. عند الضغط على `btnHello` تستدعي الـ IDE الدالة `btnHello_Click` في برنامجك.
4. داخل الدالة تستخدم دوال الوحدة `RadGUI`:

| الدالة | وظيفتها | مثال |
|---|---|---|
| `rad_get($obj, $prop)` | تقرأ خاصية كنص | `rad_get("txtName", "Text")` |
| `rad_getnum($obj, $prop)` | تقرأ خاصية كرقم | `rad_getnum("txtA", "Text")` |
| `rad_set($obj, $prop, $value)` | تغيّر خاصية | `rad_set("lblOut", "Text", "مرحبا")` |
| `rad_call($obj, $method, @args)` | تستدعي دالة في الأداة | `rad_call("lstLog", "AddItem", "سطر")` |
| `rad_msgbox($text)` | رسالة منبثقة | `rad_msgbox("تم الحفظ")` |
| `rad_input($prompt)` | مربع إدخال | `rad_input("ما اسمك؟")` |
| `rad_end()` | تنهي البرنامج | |

وما تطبعه بـ `print` يظهر في نافذة **Output** للتتبع.

## خطوة بخطوة: برنامج الترحيب

1. **File > New Project...** ثم **Scripting > Perl (GUI Bridge)** باسم `HelloPerl`.
2. من **Toolbox** (صندوق الأدوات) ارسم الأدوات، وغيّر **Name** و**Text** من **Properties** (الخصائص):

| الأداة | Name | Text |
|---|---|---|
| `Label` | `lblOut` | (فارغ) |
| `TextBox` | `txtName` | (فارغ) |
| `Button` | `btnHello` | `رحّب بي` |

3. **انقر مرتين** على الزر، فتضيف الـ IDE الدالة `sub btnHello_Click` إلى `Form1.pl`. اكتب:

<!-- test: {"set": {"txtName.Text": "هدى"}, "events": ["btnHello.Click"], "expect": {"lblOut.Text": "أهلًا يا هدى!"}, "captions": {"btnHello": "رحّب بي"}} -->
```perl form run
# Event handlers for Form1.
use strict;
use warnings;
use RadGUI;

sub Form1_Load {                     # عند ظهور النافذة
    rad_set("lblOut", "Text", "اكتب اسمك ثم اضغط الزر");
}

sub btnHello_Click {                 # عند الضغط على الزر
    my ($e) = @_;
    my $name = rad_get("txtName", "Text");
    $name =~ s/^\s+|\s+$//g;         # احذف المسافات من الطرفين
    if ($name eq "") {
        rad_set("lblOut", "Text", "من فضلك اكتب اسمك أولًا");
    } else {
        rad_set("lblOut", "Text", "أهلًا يا $name!");
    }
}

1;
```

4. اضغط **F5**.

لاحظ:

- اسم الدالة = **اسم الأداة + `_` + اسم الحدث**.
- المعامل `$e` قاموس (مرجع) بمعلومات الحدث مثل `$e->{X}` و`$e->{Y}`، ويمكن تجاهله.
- السطر `1;` في آخر الملف عُرف في Perl: الملف المحمّل يجب أن يُرجع قيمة صحيحة.
- الـ IDE تولّد `_radmain.pl` الذي يحمّل ملفك وينتظر الأحداث.

## مثال: محوّل درجات الحرارة

ارسم `txtValue` و`btnToF` و`btnToC` و`lblResult`:

<!-- test: {"set": {"txtValue.Text": "100"}, "events": ["btnToF.Click"], "expect": {"lblResult.Text": "100 مئوية = 212.0 فهرنهايت"}, "captions": {"btnToF": "إلى فهرنهايت", "btnToC": "إلى مئوية"}} -->
```perl form run
use strict;
use warnings;
use RadGUI;

sub read_value {
    my $text = rad_get("txtValue", "Text");
    unless ($text =~ /^-?\d+(\.\d+)?$/) {
        rad_msgbox("اكتب رقمًا صحيحًا");
        return undef;
    }
    return $text;
}

sub btnToF_Click {
    my $c = read_value() // return;
    rad_set("lblResult", "Text", sprintf("%s مئوية = %.1f فهرنهايت", $c, $c * 9 / 5 + 32));
    print "تحويل $c إلى فهرنهايت\n";          # في Output
}

sub btnToC_Click {
    my $f = read_value() // return;
    rad_set("lblResult", "Text", sprintf("%s فهرنهايت = %.1f مئوية", $f, ($f - 32) * 5 / 9));
}

1;
```

```text output
تحويل 100 إلى فهرنهايت
```

- `read_value` دالة مساعدة عادية (ليست حدثًا)، تفحص المدخل بتعبير نمطي.
- `my $c = read_value() // return;` تعني: إذا كانت النتيجة `undef` فاخرج من الدالة.

## القوائم والمتغيرات التي تبقى

ارسم `txtItem` و`btnAdd` و`btnClear` و`lstItems` و`lblCount`:

<!-- test: {"events": [{"set": {"txtItem.Text": "قهوة"}}, "btnAdd.Click", {"set": {"txtItem.Text": "شاي"}}, "btnAdd.Click", {"set": {"txtItem.Text": "قهوة"}}, "btnAdd.Click"], "expect": {"lstItems.items": "قهوة|شاي", "lblCount.Text": "العناصر: 2"}, "msgbox": ["«قهوة» موجود من قبل"], "captions": {"btnAdd": "أضف", "btnClear": "امسح"}} -->
```perl form run
use strict;
use warnings;
use RadGUI;

my %seen;          # يبقى بين الأحداث لأن البرنامج يظل يعمل

sub btnAdd_Click {
    my $item = rad_get("txtItem", "Text");
    return if $item eq "";
    if ($seen{$item}++) {
        rad_msgbox("«$item» موجود من قبل");
        return;
    }
    rad_call("lstItems", "AddItem", $item);
    rad_set("txtItem", "Text", "");
    rad_set("lblCount", "Text", "العناصر: " . rad_getnum("lstItems", "ListCount"));
}

sub btnClear_Click {
    rad_call("lstItems", "Clear");
    %seen = ();
    rad_set("lblCount", "Text", "العناصر: 0");
}

1;
```

المتغير `%seen` المعرّف بـ `my` في أعلى الملف تراه كل الدوال في الملف، ويحتفظ بقيمته طوال تشغيل البرنامج.

## أخطاء شائعة

- **اسم الدالة لا يطابق الأداة:** `sub btnhello_click` قد يعمل (الجسر يتسامح في حالة الأحرف)، لكن `sub Button1_Click` لن يعمل إذا كان اسم الزر `btnHello`. انقر مرتين على الأداة لتكتب الـ IDE الاسم الصحيح.
- **نسيان `1;` في آخر الملف:** قد تظهر رسالة `did not return a true value`.
- **`use utf8` في ملف النموذج:** لا تحتاجه هنا؛ النصوص العربية تصل للنافذة صحيحة كما هي. وإذا أضفته فستحتاج إلى تحويل الترميز بنفسك.

## تمارين

### التمرين 1

حاسبة مؤشر كتلة الجسم: `txtWeight` (كجم) و`txtHeight` (متر) وزر `btnBmi`، ويظهر في `lblBmi` الناتج بمنزلة واحدة: `مؤشر كتلة الجسم: 22.9`. (القانون: الوزن ÷ مربع الطول.)

<!-- test: {"set": {"txtWeight.Text": "70", "txtHeight.Text": "1.75"}, "events": ["btnBmi.Click"], "expect": {"lblBmi.Text": "مؤشر كتلة الجسم: 22.9"}} -->
```perl form exercise
use strict;
use warnings;
use RadGUI;

sub btnBmi_Click {
}

1;
```

<!-- test: {"set": {"txtWeight.Text": "70", "txtHeight.Text": "1.75"}, "events": ["btnBmi.Click"], "expect": {"lblBmi.Text": "مؤشر كتلة الجسم: 22.9"}, "captions": {"btnBmi": "احسب"}} -->
```perl form solution
use strict;
use warnings;
use RadGUI;

sub btnBmi_Click {
    my $w = rad_getnum("txtWeight", "Text");
    my $h = rad_getnum("txtHeight", "Text");
    return rad_msgbox("الطول لا يمكن أن يكون صفرًا") if $h == 0;
    rad_set("lblBmi", "Text", sprintf("مؤشر كتلة الجسم: %.1f", $w / ($h * $h)));
}

1;
```

### التمرين 2

زر `btnCount` يعد كلمات النص المكتوب في `txtText` ويعرض في `lblWords`: `عدد الكلمات: N`. استخدم `split` أو تعبيرًا نمطيًا.

<!-- test: {"set": {"txtText.Text": "Perl is fun and powerful"}, "events": ["btnCount.Click"], "expect": {"lblWords.Text": "عدد الكلمات: 5"}} -->
```perl form exercise
use strict;
use warnings;
use RadGUI;

sub btnCount_Click {
}

1;
```

<!-- test: {"set": {"txtText.Text": "Perl is fun and powerful"}, "events": ["btnCount.Click"], "expect": {"lblWords.Text": "عدد الكلمات: 5"}, "captions": {"btnCount": "عدّ الكلمات"}} -->
```perl form solution
use strict;
use warnings;
use RadGUI;

sub btnCount_Click {
    my $text = rad_get("txtText", "Text");
    my @words = split ' ', $text;
    rad_set("lblWords", "Text", "عدد الكلمات: " . scalar(@words));
}

1;
```

`split ' ', $text` (بمسافة بين علامتين) حالة خاصة في Perl: تقسم على أي مسافات وتتجاهل المسافات في البداية.

## اختبر نفسك

```quiz
{"question": "أي دالة تغيّر نص العنوان lblOut في Perl؟", "choices": ["rad_get(\"lblOut\", \"Text\")", "rad_set(\"lblOut\", \"Text\", \"...\")", "print lblOut", "lblOut.Text = ..."], "answer": 1, "explanation": "rad_set تغيّر خاصية في أداة."}
```

```quiz
{"question": "لماذا ينتهي ملف النموذج بالسطر 1;؟", "choices": ["لترقيم الأسطر", "لأن الملف المحمّل في Perl يجب أن يُرجع قيمة صحيحة", "لتشغيل الحدث الأول", "لا فائدة"], "answer": 1, "explanation": "الملفات المحمّلة بـ do أو require تُرجع آخر قيمة فيها، والعُرف أن تكون 1."}
```

## الخلاصة

- معالج الحدث `sub اسمالأداة_الحدث { ... }` في `Form1.pl`.
- `rad_get` و`rad_getnum` و`rad_set` و`rad_call` و`rad_msgbox` و`rad_input`.
- متغيرات `my` في أعلى الملف تبقى بين الأحداث.
- التعابير النمطية مفيدة جدًا لفحص مدخلات المستخدم.
