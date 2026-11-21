# الدرس 11: من Dart إلى Flutter: الودجات وأول تطبيق موبايل

وصلت إلى الهدف الذي بدأنا من أجله! **Flutter** إطار من Google تكتب به بلغة Dart تطبيقًا واحدًا يعمل على Android وiPhone وويندوز والويب. في هذا الدرس نرى كيف تتحول كل فكرة تعلمتها في Dart إلى جزء من تطبيق موبايل.

> **تشبيه:** تطبيق Flutter مثل **مكعبات الليغو**: كل شيء على الشاشة مكعب صغير اسمه **ودجة** (widget): نص، زر، صورة، صف، عمود. تركّب المكعبات داخل بعضها فتبني شاشة كاملة.

## كل شيء ودجة

هذا تطبيق Flutter كامل مكتوب بالطريقة العادية (بدون مصمم). اقرأه فقط وحاول أن تتعرف على ما تعلمته:

```dart
import 'package:flutter/material.dart';

void main() => runApp(const MyApp());

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        appBar: AppBar(title: const Text('تطبيقي الأول')),
        body: const Center(
          child: Text('مرحبًا يا Flutter', style: TextStyle(fontSize: 24)),
        ),
      ),
    );
  }
}
```

| ما تراه في الكود | تعلمته في الدرس |
|---|---|
| `void main() => runApp(...)` | الدالة الرئيسية والدالة السهمية (1 و4) |
| `class MyApp extends StatelessWidget` | الأصناف والوراثة (7) |
| `@override Widget build(...)` | إعادة تعريف دالة موروثة (7) |
| `const MyApp({super.key})` | باني بمعاملات مسماة و`const` (7) |
| `appBar: ...` و`body: ...` و`child: ...` | المعاملات المسماة (4) |
| `const Text(...)` | كائن ثابت (2 و7) |

الودجات تتداخل كالشجرة: `MaterialApp` فيه `Scaffold` (هيكل الشاشة)، وفيه `AppBar` (الشريط العلوي) و`Center` (يوسّط ما بداخله)، وفي `Center` نص `Text`.

## الحالة (State) و `setState`

الشاشة التي تتغير (عداد، قائمة تكبر) تحتاج **حالة**. في Flutter العادي:

```dart
class Counter extends StatefulWidget {
  const Counter({super.key});
  @override
  State<Counter> createState() => _CounterState();
}

class _CounterState extends State<Counter> {
  int count = 0;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text('العدد: $count'),
        ElevatedButton(
          onPressed: () => setState(() => count++),
          child: const Text('زِد'),
        ),
      ],
    );
  }
}
```

- `count` متغير داخل الصنف يبقى بين الضغطات، مثل المتغير على مستوى الملف في الدرس 9.
- `onPressed: () => ...` دالة مجهولة تُمرر للزر: تعمل عند الضغط (الدرس 4).
- `setState` تقول لـ Flutter: «تغيرت البيانات، أعد رسم الشاشة». تذكّر `refresh()` في الدرس 10!
- `children: [...]` قائمة ودجات (الدرس 5)، ويمكن أن يكون فيها `if` و`for`.

## الطريقة الأسهل: مصمم الشاشات في RAD IDE

كتابة شجرة الودجات بيدك قوية، لكنها طويلة للمبتدئ. RAD IDE تعطيك طريقة Visual Basic: **ترسم الشاشة** في مصمم على شكل هاتف، وتكتب **الأحداث** فقط، والـ IDE تولّد كود Flutter الذي يرسم الشاشة.

1. **File > New Project...** ثم من مجموعة **Mobile** (موبايل) اختر **Flutter App**، وسمّه `HelloFlutter`.
2. يفتح المصمم على شكل هاتف. من **Toolbox** (صندوق الأدوات) اسحب `Label` و`MTextField` و`Button`، وسمّها من **Properties** (الخصائص): `lblHello` و`txtName` و`btnHello`.
3. انقر مرتين على الزر، فيفتح الملف `lib/main_screen.dart` على الدالة `btnHello_Click`.
4. اختر الجهاز من قائمة **Device:** في شريط **Mobile** (اختر `Windows` لأسرع تجربة)، ثم اضغط **F5**.

الملف الذي تكتب فيه:

<!-- test: {"controls": {"lblHello": {"Text": ""}, "txtName": {"Text": ""}, "btnHello": {"Text": "رحّب"}}, "do": ["btnHello_Click()", "txtName.text = 'سلمى'", "btnHello_Click()"], "expect": {"lblHello.text": "أهلًا يا سلمى!"}, "toast": ["اكتب اسمك أولًا"]} -->
```flutter run
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  int greetings = 0;

  void MainScreen_Load() {
    lblHello.text = 'اكتب اسمك واضغط الزر';
  }

  void btnHello_Click() {
    final name = txtName.text.trim();
    if (name.isEmpty) {
      Toast('اكتب اسمك أولًا');
      return;
    }
    greetings++;
    lblHello.text = 'أهلًا يا $name!';
    print('عدد التحيات: $greetings');
  }
}
```

```text output
عدد التحيات: 1
```

قارن هذا بالدرس 9: نفس الفكرة تمامًا! اسم الدالة `اسمالأداة_الحدث`، والمتغير `greetings` داخل الصنف يبقى بين الضغطات. الفرق أن الأدوات هنا **كائنات** لها خصائص (`txtName.text`)، وأن الكود داخل **صنف** `MainScreenCode` يرث من `MainScreenDesigner` (الجزء المولَّد الذي فيه الأدوات).

- `part 'main_screen_designer.dart';` تجعل الملف المولَّد جزءًا من ملفك، فترى الأدوات دون أن تعرّفها.
- `Toast('...')` رسالة قصيرة تظهر أسفل الشاشة ثم تختفي، و`MsgBox('...')` رسالة بزر موافق.
- تغيير خاصية مثل `lblHello.text = ...` يعيد رسم الشاشة وحده: مكتبة RAD IDE تستدعي `setState` بدلًا منك.

> **لا تعدّل** `lib/main_screen_designer.dart`: الـ IDE تعيد كتابته كلما حفظت التصميم. اكتب دائمًا في `lib/main_screen.dart`.

## أخطاء شائعة

- **نسيان الفاصلة بعد معامل مسمى** في شجرة الودجات: `child: Text('a') style: ...`. ضع فاصلة بعد كل معامل، والعادة في Flutter فاصلة حتى بعد الأخير لكي ينسق المحرر الكود جيدًا.
- **تعريف المتغير داخل الحدث** بدل الصنف: يرجع صفرًا مع كل ضغطة.
- **`setState` في كود المصمم:** لا تحتاجها في RAD IDE، لكنها ضرورية في كود Flutter العادي.

## تمارين

### التمرين 1

في شاشة فيها `txtAge` و`btnCheck` و`lblResult`: إذا كان العمر 18 أو أكثر اكتب `يمكنك التصويت`، وإلا اكتب `باقي لك N سنوات`. وإذا لم يكن المدخل رقمًا اعرض `MsgBox('اكتب رقمًا')`.

```flutter exercise
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void btnCheck_Click() {
    // int.tryParse(txtAge.text)
  }
}
```

<!-- test: {"controls": {"txtAge": {"Text": ""}, "btnCheck": {"Text": "تحقق"}, "lblResult": {"Text": ""}}, "do": ["txtAge.text = 'abc'", "btnCheck_Click()", "txtAge.text = '15'", "btnCheck_Click()"], "expect": {"lblResult.text": "باقي لك 3 سنوات"}, "msgbox": ["اكتب رقمًا"]} -->
```flutter solution
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void btnCheck_Click() {
    final age = int.tryParse(txtAge.text.trim());
    if (age == null) {
      MsgBox('اكتب رقمًا');
      return;
    }
    lblResult.text = age >= 18 ? 'يمكنك التصويت' : 'باقي لك ${18 - age} سنوات';
  }
}
```

## اختبر نفسك

```quiz
{"question": "ما هي الودجة (widget) في Flutter؟", "choices": ["ملف إعدادات", "أي جزء من الواجهة: نص أو زر أو صف أو شاشة كاملة", "نوع من المتغيرات", "أداة لتثبيت Flutter"], "answer": 1, "explanation": "في Flutter كل شيء ودجة، والودجات تتداخل كشجرة."}
```

```quiz
{"question": "ما وظيفة setState في Flutter العادي؟", "choices": ["تحذف الشاشة", "تخبر Flutter أن البيانات تغيرت فتعيد رسم الشاشة", "تحفظ البيانات في ملف", "تغلق التطبيق"], "answer": 1, "explanation": "بعد تغيير الحالة نستدعي setState لكي تُبنى الواجهة من جديد. في مصمم RAD IDE يحدث هذا تلقائيًا."}
```

```quiz
{"question": "في أي ملف تكتب أحداث شاشة Flutter في RAD IDE؟", "choices": ["lib/main_screen_designer.dart", "lib/main_screen.dart", "pubspec.yaml", "lib/main.dart"], "answer": 1, "explanation": "ملف designer يُولَّد من التصميم، وكودك في lib/main_screen.dart."}
```

## الخلاصة

- Flutter تبني الواجهة من **ودجات** متداخلة، وكل ما تعلمته في Dart (الأصناف، المعاملات المسماة، الدوال المجهولة، القوائم) هو لغة هذه الشجرة.
- `StatelessWidget` لشاشة ثابتة، و`StatefulWidget` مع `setState` لشاشة تتغير.
- في RAD IDE: **File > New Project... > Mobile > Flutter App**، ترسم الشاشة وتكتب الأحداث في `lib/main_screen.dart`.
- للتفاصيل الكاملة (القوائم، الشاشات المتعددة، المؤقتات، البناء للهاتف) تابع **«دليل تطبيقات الموبايل بـ Flutter في RAD IDE»** في قائمة الدروس (**Help > Tutorials (Arabic lessons)**).
