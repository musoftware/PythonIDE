# الدرس 3: مصمم الهاتف وصندوق أدوات الموبايل

**في هذا الدرس ستتعلم:**

- اختيار **الجهاز** واتجاه الشاشة في المصمم.
- أدوات المجموعة **Mobile** في صندوق الأدوات، ومتى تستخدم كل واحدة.
- الخاصيتين `Anchor` و `Dock` لكي تتمدد الأدوات مع عرض الهاتف.
- الحاويات `Column` و `Row` و `Card` لترتيب الأدوات تلقائيًا.

## المصمم داخل إطار هاتف

افتح `MainScreen.form` بنقرة مزدوجة في **Solution Explorer**. سترى الشاشة مرسومة داخل **إطار هاتف** حقيقي: شريط الحالة في الأعلى، وشريط الإيماءات في الأسفل. المنطقة البيضاء بينهما اسمها **المنطقة الآمنة** (safe area)، وفيها تضع أدواتك.

انقر على مكان فارغ في الشاشة لتختار **الشاشة نفسها**، ثم انظر في نافذة **Properties** (الخصائص):

| الخاصية | معناها |
|---|---|
| `Device` | نوع الجهاز الذي يُرسم إطاره |
| `Orientation` | `Portrait` (طولي) أو `Landscape` (أفقي) |
| `Text` | عنوان الشاشة |
| `Route` | اسم مسار الشاشة داخل التطبيق (اتركه فارغًا ليكون `/MainScreen`) |
| `Width` و `Height` | مقاس المنطقة الآمنة بوحدة **dp**، ويُحسب من الجهاز والاتجاه |

الأجهزة المتاحة:

| `Device` | المقاس (dp) |
|---|---|
| `pixel` | Pixel / Medium phone ‏(412 x 915)، وهو الافتراضي |
| `small_phone` | Small phone ‏(360 x 640) |
| `tablet` | Tablet ‏(800 x 1280) |
| `iphone_15` | iPhone 15 ‏(393 x 852) |
| `iphone_se` | iPhone SE ‏(375 x 667) |

> **ما هي dp؟** وحدة قياس مستقلة عن دقة الشاشة. زر عرضه 100dp يظهر بالحجم نفسه تقريبًا على هاتف رخيص وهاتف غالٍ، مهما اختلف عدد نقاط الشاشة.

جرّب تغيير `Device` إلى `small_phone` ثم `tablet`: يتغير الإطار، وتتحرك الأدوات المربوطة بالحواف معه.

## صندوق الأدوات: المجموعة Mobile

في **Toolbox** (صندوق الأدوات) تظهر مع مشاريع الموبايل مجموعة اسمها **Mobile**:

| الأداة | البادئة المقترحة للاسم | ماذا تفعل؟ | أشهر حدث |
|---|---|---|---|
| `AppBar` | `AppBar1` | الشريط العلوي: عنوان وأزرار أيقونات | `Click` (مع `e.Action`) |
| `MTextField` | `txt` | حقل كتابة بتصميم Material وفيه تلميح `Hint` | `Changed` و `Submitted` |
| `MListView` | `lst` | قائمة صفوف قابلة للتمرير | `Tap` (مع `e.Index`) |
| `Switch` | `sw` | مفتاح تشغيل وإيقاف | `Changed` |
| `MSlider` | `sld` | منزلق لاختيار رقم | `Changed` |
| `Fab` | `fab` | الزر العائم الدائري لأهم أمر في الشاشة | `Click` |
| `Card` | - | بطاقة بزوايا مستديرة تجمع أدوات | `Tap` |
| `MImage` و `MIcon` | `img` | صورة أو أيقونة | `Tap` |
| `BottomNav` و `MTabBar` و `Drawer` | - | التنقل بين الصفحات | `Changed` أو `Tap` |
| `MWebView` | - | صفحة ويب داخل التطبيق | `Load` |
| `Column` و `Row` و `Stack` | - | حاويات ترتّب ما بداخلها | - |

والأدوات الكلاسيكية تعمل أيضًا: `Button` و `Label` و `TextBox` و `CheckBox` و `RadioButton` و `ComboBox` و `ProgressBar` و `Timer`. الأدوات الخاصة بويندوز فقط تظهر **رمادية** في مشاريع الموبايل.

> **نصيحة:** سمِّ كل أداة باسم يبدأ ببادئة نوعها (`btnSave` و `txtEmail` و `lblTotal`). هكذا تعرف نوع الأداة من اسمها في الكود، كما في دورة BASIC.

## الأدوات تتمدد مع الهاتف: Anchor و Dock

الهواتف مختلفة العرض. لكي يملأ حقل الكتابة عرض الشاشة على كل هاتف:

- اجعل `Anchor` يساوي `Top, Left, Right`: تبقى المسافة ثابتة بين الأداة والحافتين اليسرى واليمنى، فيتمدد عرضها.
- `Dock` = `Top` يلصق الأداة بأعلى الشاشة بعرضها كله (هكذا يعمل `AppBar`)، و`Bottom` لأسفلها (مثل `BottomNav`).

القوالب تضع `Anchor` بهذا الشكل لكل أداة بعرض الشاشة.

## الحاويات: Column و Row و Card

بدل أن تحدد مكان كل أداة بالبكسل، ضع الأدوات داخل **حاوية**:

- `Column` ترتّب ما بداخلها **من أعلى لأسفل**.
- `Row` ترتّب ما بداخلها **من اليسار لليمين**.
- `Spacing` المسافة بين العناصر، و`Padding` الحشو الداخلي، و`Align` المحاذاة (`Start` و `Center` و `End` و `Stretch` ...).

اسحب أداة إلى داخل الحاوية من **Toolbox**، واسحبها لأعلى أو لأسفل لتغيير ترتيبها. هذه هي طريقة Flutter الأصلية في التخطيط، والكود المولَّد يستخدم `Column` و `Row` الحقيقيتين.

## الخصائص في الكود

كل أداة في كودك **كائن** له خصائص تشبه فيجوال بيسك:

| الخاصية | النوع | مثال |
|---|---|---|
| `text` | نص | `lblTitle.text = 'مرحبًا';` |
| `visible` | `bool` | `btnDelete.visible = false;` |
| `enabled` | `bool` | `btnSave.enabled = txtName.text.isNotEmpty;` |
| `fontSize` | رقم عشري | `lblTitle.fontSize = 24;` ثم `lblTitle.refresh();` |
| `backColor` و `foreColor` | `Color` | `lblTitle.foreColor = Colors.red;` ثم `lblTitle.refresh();` |

المثال التالي شاشة "بطاقة تعريف": يملأ الحدث `MainScreen_Load` العناوين، ويخفي زرًّا، ويعطّل آخر:

<!-- test: {"form": {"Text": "Profile"}, "controls": {"lblName": {"FontSize": 16}}, "expect": {"lblName.text": "سارة أحمد", "lblCity.text": "المدينة: الإسكندرية", "btnEdit.visible": "false", "btnFollow.enabled": "true", "lblName.fontSize": "24.0"}} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void MainScreen_Load() {
    lblName.text = 'سارة أحمد';
    lblName.fontSize = 24;
    lblName.foreColor = Colors.indigo;
    lblName.refresh();
    lblCity.text = 'المدينة: الإسكندرية';
    btnEdit.visible = false;       // ليس حسابي: لا أعدّل
    btnFollow.enabled = true;
    print('الأدوات: ${radControls.length}');
  }
}
```

```text output
الأدوات: 4
```

`radControls` قائمة بكل أدوات الشاشة، يكتبها الملف المولَّد. هنا 4 أدوات: `lblName` و `lblCity` و `btnEdit` و `btnFollow`.

## أخطاء شائعة

- **تغيير اللون أو حجم الخط دون `refresh()`**: لا تتغير الشاشة. الخصائص `text` و `visible` و `enabled` تعيد الرسم وحدها، أما الألوان والخط فتحتاج `refresh()`.
- **أداة لا تتمدد على التابلت**: نسيت `Anchor = Top, Left, Right`.
- **حقل كتابة تحت لوحة المفاتيح**: ضع الحقول في أعلى الشاشة أو داخل `Column`، فالقائمة تتمرر.

## تمرين

عند تحميل الشاشة: اكتب في `lblTitle` النص `الإعدادات`، واجعل `btnSave` معطّلًا (`enabled = false`)، واطبع `جاهز`.

```flutter exercise
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void MainScreen_Load() {
    // lblTitle و btnSave
  }
}
```

<!-- test: {"expect": {"lblTitle.text": "الإعدادات", "btnSave.enabled": "false"}} -->
```flutter solution
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void MainScreen_Load() {
    lblTitle.text = 'الإعدادات';
    btnSave.enabled = false;
    print('جاهز');
  }
}
```

```text output
جاهز
```

## اختبر نفسك

```quiz
{"question": "أي قيمة لـ Anchor تجعل حقل الكتابة يتمدد مع عرض الهاتف؟", "choices": ["Top, Left", "Top, Left, Right", "Bottom", "None"], "answer": 1, "explanation": "ربط الأداة بالحافتين اليسرى واليمنى يجعل عرضها يتغير مع عرض الشاشة."}
```

```quiz
{"question": "أي حاوية ترتّب ما بداخلها من أعلى لأسفل؟", "choices": ["Row", "Column", "Stack", "Card"], "answer": 1, "explanation": "Column عمودية، و Row أفقية."}
```

```quiz
{"question": "غيّرت `lblTitle.foreColor = Colors.red;` ولم يتغير اللون. ما الناقص؟", "choices": ["setState", "lblTitle.refresh();", "إعادة تشغيل التطبيق", "لا شيء، هذا خطأ في Flutter"], "answer": 1, "explanation": "الألوان والخط تحتاج refresh() لإعادة الرسم."}
```

## الخلاصة

- الخاصيتان `Device` و `Orientation` تحددان إطار الهاتف ومقاس المنطقة الآمنة بوحدة dp.
- مجموعة **Mobile** في صندوق الأدوات فيها أدوات Material: `AppBar` و `MTextField` و `MListView` و `Switch` و `MSlider` و `Fab` ...
- `Anchor` و `Dock` و `Column` و `Row` تجعل التصميم يناسب كل المقاسات.
