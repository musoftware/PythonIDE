# الدرس 9: أول نافذة Dart في مصمم النماذج

قبل أن ننتقل إلى تطبيقات الموبايل، نبني **برنامجًا بنافذة وأزرار على سطح المكتب** بطريقة Visual Basic: نرسم النافذة في المصمم، ونكتب بلغة Dart ما يحدث عند كل ضغطة. هكذا تتعلم **البرمجة بالأحداث** بأبسط شكل، ثم تجدها نفسها في Flutter.

## البرمجة بالأحداث

في البرنامج الرسومي لا يسير الكود من أعلى لأسفل ثم ينتهي، بل **ينتظر** أفعال المستخدم. لكل فعل (ضغطة زر، كتابة نص، اختيار من قائمة) **حدث** (event)، ونكتب لكل حدث دالة تسمى **معالج الحدث** (event handler).

> **تشبيه:** البرنامج الرسومي مثل **جرس الباب**: لا يرن وحده. عندما يضغط أحد الزر يحدث «حدث»، فيرن الجرس (يعمل المعالج).

## كيف يعمل «جسر الواجهة» (GUI Bridge)؟

1. الـ IDE **ترسم النافذة** التي صممتها.
2. برنامج Dart يعمل في الخلفية وينتظر.
3. عند الضغط على زر اسمه `btnHello` تستدعي الـ IDE الدالة `btnHello_Click` في برنامجك.
4. داخل الدالة تتعامل مع الأدوات بالصنف `Rad`:

| الكتابة | وظيفتها |
|---|---|
| `Rad.get('txtName', 'Text')` | تقرأ خاصية كنص |
| `Rad.getNum('txtA', 'Text')` | تقرأ خاصية كرقم (والنص غير الرقمي يصبح 0) |
| `Rad.set('lblOut', 'Text', 'مرحبا')` | تغيّر خاصية |
| `Rad.call('lstLog', 'AddItem', ['سطر'])` | تستدعي دالة في الأداة (المعاملات في قائمة) |
| `msgbox('تم')` | رسالة منبثقة |
| `Rad.input('ما اسمك؟')` | مربع إدخال يُرجع ما كتبه المستخدم |
| `Rad.end()` | تنهي البرنامج |

وما تطبعه بـ `print` يظهر في نافذة **Output** (المخرجات) للتتبع.

## خطوة بخطوة: برنامج الترحيب

1. **File > New Project...** ثم من مجموعة **Scripting** اختر **Dart (GUI Bridge)** وسمّه `HelloDart`.
2. من **Toolbox** (صندوق الأدوات) ارسم الأدوات التالية، وغيّر **Name** و**Text** من نافذة **Properties** (الخصائص):

| الأداة | Name | Text |
|---|---|---|
| `Label` | `lblOut` | (فارغ) |
| `TextBox` | `txtName` | (فارغ) |
| `Button` | `btnHello` | `رحّب بي` |

3. **انقر مرتين** على الزر في المصمم، فتنشئ الـ IDE الدالة `btnHello_Click` في الملف `Form1.dart` وتضع المؤشر داخلها. اكتب:

<!-- test: {"set": {"txtName.Text": "يوسف"}, "events": ["btnHello.Click"], "expect": {"lblOut.Text": "أهلًا يا يوسف!"}, "captions": {"btnHello": "رحّب بي"}} -->
```dart form run
import 'radgui.dart';

void Form1_Load(RadEvent e) {           // عند ظهور النافذة
  Rad.set('lblOut', 'Text', 'اكتب اسمك ثم اضغط الزر');
}

void btnHello_Click(RadEvent e) {       // عند الضغط على الزر
  final name = Rad.get('txtName', 'Text').trim();
  if (name.isEmpty) {
    Rad.set('lblOut', 'Text', 'من فضلك اكتب اسمك أولًا');
  } else {
    Rad.set('lblOut', 'Text', 'أهلًا يا $name!');
  }
}
```

4. اضغط **F5** (أو **Debug > Start**)، اكتب اسمك واضغط الزر.

- اسم الدالة = **اسم الأداة + `_` + اسم الحدث**: `btnHello_Click`، `Form1_Load`، `tmrTick_Tick`.
- معالجات الأحداث دوال **على مستوى الملف** (خارج أي صنف) تأخذ `RadEvent e`، وفيه تفاصيل الحدث مثل `e.x` و`e.y`.
- `import 'radgui.dart';` تجلب الصنف `Rad`، والـ IDE تنسخ هذا الملف إلى المشروع عند التشغيل.
- الـ IDE تولّد `_radmain.dart` الذي يستقبل الأحداث ويستدعي دوالك، فلا تكتب أنت حلقة الانتظار.

> **تنبيه:** قد يضع محلل Dart خطًا خفيفًا تحت الاسم `btnHello_Click` لأن Dart تفضّل الأسماء بلا شرطة سفلية. هذا تنبيه أسلوب فقط، والاسم بهذا الشكل مطلوب لكي يجد الجسر الدالة.

## آلة حاسبة صغيرة

ارسم `txtA` و`txtB` والأزرار `btnAdd` و`btnMul` و`btnDiv` والعنوان `lblResult`:

<!-- test: {"set": {"txtA.Text": "9", "txtB.Text": "4"}, "events": ["btnDiv.Click"], "expect": {"lblResult.Text": "الناتج = 2.25"}, "captions": {"btnAdd": "+", "btnMul": "×", "btnDiv": "÷"}} -->
```dart form run
import 'radgui.dart';

num a() => Rad.getNum('txtA', 'Text');
num b() => Rad.getNum('txtB', 'Text');

void showResult(num value) {
  final text = value == value.roundToDouble() ? value.toInt().toString() : value.toString();
  Rad.set('lblResult', 'Text', 'الناتج = $text');
  print('الناتج: $text');                 // في Output
}

void btnAdd_Click(RadEvent e) => showResult(a() + b());

void btnMul_Click(RadEvent e) => showResult(a() * b());

void btnDiv_Click(RadEvent e) {
  if (b() == 0) {
    msgbox('لا يمكن القسمة على صفر');
    return;
  }
  showResult(a() / b());
}
```

```text output
الناتج: 2.25
```

- `a()` و`b()` و`showResult` دوال مساعدة عادية (أسماؤها لا تطابق أداة وحدثًا).
- `Rad.getNum` تحوّل النص إلى رقم، والنص الفارغ يصبح 0 فلا يتوقف البرنامج.
- المعالج القصير يمكن كتابته بالسهم `=>` كما تعلمنا في الدرس 4.

## القوائم (`ListBox`)

ارسم `txtItem` و`btnAdd` و`btnRemove` و`lstItems` و`lblCount`:

<!-- test: {"events": [{"set": {"txtItem.Text": "حليب"}}, "btnAdd.Click", {"set": {"txtItem.Text": "خبز"}}, "btnAdd.Click", {"set": {"txtItem.Text": "جبن"}}, "btnAdd.Click", {"set": {"lstItems.ListIndex": "1"}}, "btnRemove.Click"], "expect": {"lstItems.items": "حليب|جبن", "lblCount.Text": "العناصر: 2"}, "captions": {"btnAdd": "أضف", "btnRemove": "احذف المختار"}} -->
```dart form run
import 'radgui.dart';

void updateCount() {
  final n = Rad.getNum('lstItems', 'ListCount');
  Rad.set('lblCount', 'Text', 'العناصر: $n');
}

void btnAdd_Click(RadEvent e) {
  final item = Rad.get('txtItem', 'Text').trim();
  if (item.isNotEmpty) {
    Rad.call('lstItems', 'AddItem', [item]);
    Rad.set('txtItem', 'Text', '');
    updateCount();
  }
}

void btnRemove_Click(RadEvent e) {
  final index = Rad.getNum('lstItems', 'ListIndex').toInt();
  if (index >= 0) {
    Rad.call('lstItems', 'RemoveItem', [index]);
    updateCount();
  } else {
    msgbox('اختر عنصرًا أولًا');
  }
}
```

> **انتبه:** ترقيم عناصر القائمة يبدأ من **0** كقوائم Dart، و`ListIndex` = `-1` تعني أن المستخدم لم يختر شيئًا.

## المؤقت (Timer) والمتغيرات التي تبقى بين الأحداث

ارسم أداة `Timer` باسم `tmrTick` وعنوانًا `lblTime`:

<!-- test: {"events": ["tmrTick.Tick", "tmrTick.Tick"], "expect": {"lblTime.Text": "الثواني: 2", "tmrTick.enabled": "True"}} -->
```dart form run
import 'radgui.dart';

var seconds = 0;          // متغير على مستوى الملف: يحتفظ بقيمته بين الأحداث

void Form1_Load(RadEvent e) {
  Rad.set('tmrTick', 'Interval', 1000);   // كل 1000 ملّي ثانية
  Rad.set('tmrTick', 'Enabled', 'True');
}

void tmrTick_Tick(RadEvent e) {
  seconds++;
  Rad.set('lblTime', 'Text', 'الثواني: $seconds');
}
```

المتغير `seconds` معرّف **خارج** الدوال، فيبقى طوال تشغيل البرنامج. لو عرّفناه داخل `tmrTick_Tick` لبدأ من صفر مع كل حدث.

## أخطاء شائعة

- **تعريف العداد داخل المعالج:** يرجع إلى صفر مع كل ضغطة. ضعه على مستوى الملف.
- **نسيان القائمة في `Rad.call`:** `Rad.call('lst', 'AddItem', 'x')` خطأ في النوع، والصحيح `['x']`.
- **جمع نصوص الأدوات:** `Rad.get('txtA', 'Text') + Rad.get('txtB', 'Text')` يلصق النصين. استخدم `Rad.getNum`.
- **تغيير اسم الأداة بعد كتابة الكود:** غيّر اسم الدالة أيضًا (`btnGreet_Click`)، وإلا لن يحدث شيء.

## تمارين

### التمرين 1

برنامج «مربع العدد»: يكتب المستخدم عددًا في `txtNum` ويضغط `btnSquare`، فيظهر في `lblResult`: `مربع 7 هو 49`.

<!-- test: {"set": {"txtNum.Text": "7"}, "events": ["btnSquare.Click"], "expect": {"lblResult.Text": "مربع 7 هو 49"}} -->
```dart form exercise
import 'radgui.dart';

void btnSquare_Click(RadEvent e) {
}
```

<!-- test: {"set": {"txtNum.Text": "7"}, "events": ["btnSquare.Click"], "expect": {"lblResult.Text": "مربع 7 هو 49"}, "captions": {"btnSquare": "احسب المربع"}} -->
```dart form solution
import 'radgui.dart';

void btnSquare_Click(RadEvent e) {
  final n = Rad.getNum('txtNum', 'Text');
  Rad.set('lblResult', 'Text', 'مربع $n هو ${n * n}');
}
```

### التمرين 2

زر `btnAsk` يسأل المستخدم عن مدينته بـ `Rad.input`، ثم يضيفها إلى القائمة `lstCities` ويعرض في `lblCount` عدد المدن مثل `المدن: 2`. وإذا كتب مدينة موجودة من قبل تظهر رسالة `موجودة بالفعل` ولا تُضاف.

<!-- test: {"events": ["btnAsk.Click", "btnAsk.Click", "btnAsk.Click"], "inputs": ["طنطا", "المنصورة", "طنطا"], "expect": {"lstCities.items": "طنطا|المنصورة", "lblCount.Text": "المدن: 2"}, "msgbox": ["موجودة بالفعل"]} -->
```dart form exercise
import 'radgui.dart';

final cities = <String>[];

void btnAsk_Click(RadEvent e) {
}
```

<!-- test: {"events": ["btnAsk.Click", "btnAsk.Click", "btnAsk.Click"], "inputs": ["طنطا", "المنصورة", "طنطا"], "expect": {"lstCities.items": "طنطا|المنصورة", "lblCount.Text": "المدن: 2"}, "msgbox": ["موجودة بالفعل"], "captions": {"btnAsk": "أضف مدينة"}} -->
```dart form solution
import 'radgui.dart';

final cities = <String>[];

void btnAsk_Click(RadEvent e) {
  final city = Rad.input('ما مدينتك؟').trim();
  if (city.isEmpty) return;
  if (cities.contains(city)) {
    msgbox('موجودة بالفعل');
    return;
  }
  cities.add(city);
  Rad.call('lstCities', 'AddItem', [city]);
  Rad.set('lblCount', 'Text', 'المدن: ${cities.length}');
}
```

## اختبر نفسك

```quiz
{"question": "ما اسم الدالة التي تعمل عند الضغط على زر اسمه btnSave؟", "choices": ["onSave", "btnSave_Click", "Click_btnSave", "btnSave.click"], "answer": 1, "explanation": "اسم المعالج = اسم الأداة + _ + اسم الحدث."}
```

```quiz
{"question": "أين تعرّف متغيرًا يجب أن يحتفظ بقيمته بين الأحداث؟", "choices": ["داخل المعالج", "على مستوى الملف خارج الدوال", "في Properties", "لا يمكن ذلك"], "answer": 1, "explanation": "المتغير خارج الدوال يبقى طوال تشغيل البرنامج."}
```

## الخلاصة

- معالج الحدث دالة على مستوى الملف باسم `اسمالأداة_الحدث(RadEvent e)`، وتنشئها بالنقر المزدوج.
- `Rad.get` و`Rad.getNum` و`Rad.set` و`Rad.call` للتعامل مع الأدوات، و`msgbox` و`Rad.input` للحوار.
- المتغيرات على مستوى الملف تبقى بين الأحداث.
- في الدرسين 11 و12 سنرى أن Flutter تستخدم الفكرة نفسها: أحداث ومعالجات، لكن على شاشة الموبايل.
