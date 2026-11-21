# الدرس 11: مصمم شجرة الودجات (Flutter Designer) وفتح مشاريع Flutter الجاهزة

**في هذا الدرس ستتعرف على:**

- الفرق بين مصمم الهاتف (النماذج) و**مصمم شجرة الودجات** الجديد.
- ملف الشاشة `.fscreen.json` وكيف يتحول إلى كود Flutter حقيقي.
- الأحداث والحركات (animations) في الشاشات المصممة.
- فتح مشروع Flutter كتبه شخص آخر بالأمر **File > Open Folder...**.

> **ملحوظة:** مصمم شجرة الودجات ميزة **جديدة** في RAD IDE وما زالت تُستكمل. هذا الدرس يشرح فكرتها وشكل ملفاتها، وهي ثابتة، وكل الأمثلة فيه يفحصها الـ IDE ويولّد منها كود Dart فعلًا.

## طريقتان لتصميم الشاشة

| | مصمم الهاتف (الدروس السابقة) | مصمم شجرة الودجات |
|---|---|---|
| الملف | `MainScreen.form` | `screens/Login.fscreen.json` |
| طريقة الترتيب | أماكن بالبكسل (مثل فيجوال بيسك) + حاويات | **شجرة ودجات** Flutter الحقيقية (مثل FlutterFlow) |
| الأدوات | أدوات RAD (`MTextField` و `MListView` ...) | ودجات Flutter نفسها: `Container` و `Column` و `TextField` و `ElevatedButton` ... (حوالي 90 ودجة) |
| مناسب لـ | البداية السريعة والتطبيقات البسيطة | التصاميم الجميلة المعقدة والتدرجات والظلال والحركات |

**الودجة** (widget) في Flutter هي أي جزء من الشاشة: نص، زر، مسافة، صندوق ملوّن، صف، عمود... والشاشة كلها **ودجات داخل ودجات**، مثل صناديق داخل صناديق.

> **تشبيه:** الشجرة مثل شجرة العائلة: `Scaffold` هو الجد، وتحته `Column` (الأب)، وتحته الأبناء: حقل كتابة، ومسافة، وزر. كل ودجة لها أب واحد، وقد يكون لها ابن واحد (`child`) أو أبناء كثيرون (`children`).

## ملف الشاشة `.fscreen.json`

كل شاشة ملف JSON. هذه شاشة دخول صغيرة: شريط علوي، وحقل للبريد، ومسافة، وزر يظهر بحركة صعود ناعمة:

```json fscreen
{
 "version": 1,
 "name": "Login",
 "route": "/login",
 "tree": {"id": "w1", "type": "Scaffold", "slots": {
   "appBar": {"id": "w2", "type": "AppBar", "slots": {"title": {"id": "w3", "type": "Text", "props": {"data": "تسجيل الدخول"}}}},
   "body": {"id": "w4", "type": "Padding", "props": {"padding": {"all": 16}}, "slots": {"child":
     {"id": "w5", "type": "Column", "props": {"crossAxisAlignment": "CrossAxisAlignment.stretch"}, "children": [
       {"id": "w6", "type": "TextField", "name": "txtEmail", "props": {"decoration": {"labelText": "البريد"}}},
       {"id": "w7", "type": "SizedBox", "props": {"height": 12}},
       {"id": "w8", "type": "ElevatedButton", "events": {"onPressed": "onLogin"},
        "anim": {"type": "fadeInUp", "delayMs": 300},
        "slots": {"child": {"id": "w9", "type": "Text", "props": {"data": "دخول"}}}}
     ]}}}}}
}
```

أجزاء كل ودجة (عقدة في الشجرة):

| المفتاح | معناه |
|---|---|
| `id` | رقم ثابت فريد داخل الشاشة (`w1` و `w2` ...) |
| `type` | اسم الودجة في Flutter |
| `name` | اسم مثل أسماء فيجوال بيسك (`txtEmail`) لكي تستخدمه في الكود |
| `props` | الخصائص: نصوص وأرقام وألوان `"#FF2196F3"` ومسافات `{"all": 16}` ... |
| `slots` | ابن واحد له اسم: `child` و `body` و `appBar` و `title` ... |
| `children` | قائمة الأبناء (للودجات مثل `Column` و `Row` و `Stack`) |
| `events` | الأحداث: `"onPressed": "onLogin"` |
| `anim` | حركة ظهور: `fadeIn` و `fadeInUp` و `slideLeft` و `zoomIn` و `bounceIn` ... |

أنت لا تكتب هذا الملف بيدك عادةً: المصمم يكتبه وأنت تسحب الودجات وتغيّر خصائصها. لكن فهمه يساعدك جدًا.

## ماذا يولّد الـ IDE من الشاشة؟

من `screens/Login.fscreen.json` يكتب الـ IDE ملفين، بنفس فكرة المصمم الكلاسيكي:

- `lib/screens/login.dart`: **مولَّد** ويُعاد كتابته عند كل حفظ. فيه الصنف `LoginDesigner` والدالة `build()` التي ترسم الشجرة. مثلًا الزر يصبح:

```dart
RadFx(
  type: RadFxType.fadeInUp,
  delayMs: 300,
  child: ElevatedButton(
    onPressed: onLogin,
    child: const Text('دخول'),
  ),
),
```

- `lib/screens/login_events.dart`: **ملفك**. فيه الصنف `LoginEvents` ودوال الأحداث، ويضيف إليه المصمم دوال جديدة فقط ولا يمسح كودك:

```dart
class LoginEvents extends LoginDesigner {
  @override
  void onLogin() {
    final email = txtEmail.text;          // الودجة المسمّاة متاحة باسمها
    if (email.isEmpty) return;
    Navigator.pushNamed(context, '/home');
  }
}
```

لاحظ الفرق عن أدوات RAD: هنا `txtEmail` من نوع `TextEditingController` (أداة Flutter الأصلية)، وإذا غيّرت قيمة تظهر على الشاشة تكتب `setState(() { ... });` بنفسك كما في Flutter العادي.

## أحداث جاهزة بلا كود

قيمة الحدث يمكن أن تكون **اسم دالة** تكتبها أنت، أو **أمر تنقّل جاهز**:

| القيمة في `events` | ماذا يحدث؟ |
|---|---|
| `"onLogin"` | يستدعي دالتك `onLogin()` |
| `"nav:/home"` | يفتح الشاشة ذات المسار `/home` |
| `"replace:/home"` | يستبدل الشاشة الحالية بها |
| `"push:Home"` | يفتح الشاشة `Home` باسم صنفها |
| `"back"` | يرجع للشاشة السابقة |

مثال: شاشة ترحيب فيها زرّان، الأول يفتح شاشة الدخول والثاني يرجع، بلا سطر كود واحد:

```json fscreen
{
 "version": 1,
 "name": "Welcome",
 "tree": {"id": "w1", "type": "Scaffold", "slots": {"body":
   {"id": "w2", "type": "Center", "slots": {"child":
     {"id": "w3", "type": "Column", "props": {"mainAxisSize": "MainAxisSize.min"}, "children": [
       {"id": "w4", "type": "Text", "props": {"data": "أهلًا بك", "style": {"fontSize": 28, "fontWeight": "FontWeight.bold"}}},
       {"id": "w5", "type": "SizedBox", "props": {"height": 24}},
       {"id": "w6", "type": "FilledButton", "events": {"onPressed": "nav:/login"}, "slots": {"child": {"id": "w7", "type": "Text", "props": {"data": "ابدأ"}}}},
       {"id": "w8", "type": "TextButton", "events": {"onPressed": "back"}, "slots": {"child": {"id": "w9", "type": "Text", "props": {"data": "رجوع"}}}}
     ]}}}}}
}
```

## استيراد كود Flutter موجود

العكس ممكن أيضًا: الـ IDE يقرأ ملف Dart فيه دالة `build()` ويحوّله إلى شاشة قابلة للتصميم. ما يفهمه يصبح ودجات عادية، وما لا يفهمه يبقى كما هو في عقدة من نوع `Code` (صندوق منقّط في المعاينة)، فلا يضيع شيء من كودك.

## فتح مشروع Flutter جاهز: File > Open Folder...

عندك مشروع Flutter من الإنترنت أو من زميل (فيه `pubspec.yaml` و `lib/main.dart`)؟

1. **File > Open Folder...** (ملف > فتح مجلد...) واختر مجلد المشروع.
2. يتعرف الـ IDE على أنه مشروع Flutter، ويفتحه **في مكانه** دون نسخ، ويحتفظ بملفاته `lib/main.dart` و `pubspec.yaml` كما هي ولا يولّد فوقها شيئًا.
3. كل شيء يعمل كالمعتاد: قائمة **Device:** و `F5` و Hot Reload و **Build > Mobile App** والمصحح.

## أخطاء شائعة

- **ودجة في المكان الخطأ**: `Expanded` يجب أن يكون ابنًا مباشرًا لـ `Row` أو `Column`، و`Positioned` ابنًا لـ `Stack`. المصمم يحذرك كما يفعل Flutter وقت التشغيل.
- **تعديل `lib/screens/login.dart` بيدك**: يضيع مع الحفظ التالي. اكتب في `login_events.dart`.
- **تغيير قيمة على الشاشة دون `setState`** في الشاشات المصممة: لا تتغير الشاشة.

## اختبر نفسك

```quiz
{"question": "في ملف .fscreen.json، أين يوضع الابن الوحيد لودجة مثل Padding؟", "choices": ["في children", "في slots باسم child", "في props", "في events"], "answer": 1, "explanation": "الابن الواحد في slots (child أو body أو title ...)، والأبناء المتعددون في children."}
```

```quiz
{"question": "ما معنى الحدث \"back\"؟", "choices": ["يغلق التطبيق", "يرجع إلى الشاشة السابقة", "يستدعي دالة اسمها back يجب أن تكتبها", "يعيد تحميل الشاشة"], "answer": 1, "explanation": "back أمر تنقّل جاهز: Navigator.pop."}
```

```quiz
{"question": "أي ملف تكتب فيه كود الأحداث لشاشة اسمها Login؟", "choices": ["lib/screens/login.dart", "lib/screens/login_events.dart", "Login.fscreen.json", "lib/main.dart"], "answer": 1, "explanation": "login.dart مولَّد، و login_events.dart ملفك."}
```

```quiz
{"question": "كيف تفتح مشروع Flutter جاهزًا دون أن يغيّر الـ IDE ملف main.dart فيه؟", "choices": ["File > New Project", "File > Open Folder...", "Build > Mobile App", "لا يمكن"], "answer": 1, "explanation": "Open Folder يتعرف على مشروع Flutter ويفتحه في مكانه محتفظًا بملفاته."}
```

## الخلاصة

- مصمم شجرة الودجات يحفظ الشاشة في `.fscreen.json`، ويولّد `lib/screens/<name>.dart`، وكودك في `<name>_events.dart`.
- العقدة لها `type` و `props` و `slots` و `children` و `events` و `anim`.
- **File > Open Folder...** يفتح أي مشروع Flutter جاهز في مكانه.
