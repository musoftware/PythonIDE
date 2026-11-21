# الدرس 5: الإرفاق بعملية ومصححات اللغات الأخرى

**في هذا الدرس ستتعلم:**

- أن كل ما تعلمته (`F9` و `F10` و Locals و Watch ...) يعمل مع لغات كثيرة، ولكل لغة **محرك تصحيح** خلفها.
- تثبيت المصححات من **Tools > Language Servers and Debuggers...**.
- **الإرفاق بعملية** (Attach to Process): تصحيح برنامج يعمل بالفعل.
- تصحيح JavaScript في المعاينة، وتطبيقات الموبايل، وإضافات VS Code.

## واجهة واحدة ومحركات كثيرة

لوحة قيادة السيارة واحدة (المقود والدواسات)، لكن تحت الغطاء قد يكون محرك بنزين أو كهرباء.
كذلك المصحح في RAD IDE: **الأزرار والنوافذ واحدة**، والمحرك يختلف حسب اللغة:

| اللغة | محرك التصحيح |
|---|---|
| Visual Basic 6 (BASIC) | المصحح المدمج في البيئة (لا يحتاج تثبيتًا) |
| Python (Tkinter و Qt و Django و Flask ...) | `debugpy` |
| C و C++‎ و Fortran | `gdb` (مع MinGW) |
| Go | Delve (`dlv`) |
| Java | JDWP (مدمج في JDK) |
| C#‎ | `netcoredbg` |
| Lua و Perl | وكلاء تصحيح مرفقون بالبيئة |
| Ruby | `rdbg` (مكتبة debug المرفقة بـ Ruby) |
| PowerShell | PowerShell Editor Services |
| JavaScript في مواقع الويب | أدوات المتصفح عبر المعاينة |
| Flutter / Dart | مصحح Dart |

## تثبيت المصححات وخوادم اللغات

**Tools > Language Servers and Debuggers...** (أدوات > خوادم اللغات والمصححات...): نافذة تعرض لكل لغة خادم اللغة (للإكمال الذكي والانتقال إلى التعريف) والمصحح، وحالة كل منهما، وزر لتثبيت الناقص.
ولـ Go أمر خاص: **Debug > Install Delve (Go Debugger)** يبني `dlv` بأدوات Go نفسها.

## الإرفاق بعملية (Attach to Process)

أحيانًا يكون البرنامج **يعمل بالفعل**: خادم ويب بدأ منذ ساعة، أو برنامج شغّله زميل، ويحدث فيه خطأ لا يتكرر إلا بعد وقت. بدل إعادة تشغيله من البيئة، **ترفق** المصحح به وهو يعمل.
مثل طبيب يفحص عداءً أثناء السباق بدل أن يطلب منه إعادة السباق.

### خطوة بخطوة

1. **Debug > Attach to Process...** (تصحيح الأخطاء > الإرفاق بعملية...) أو `Ctrl+Alt+P`.
2. تظهر قائمة البرامج العاملة. خانة **Only Python and debuggable programs** (Python والبرامج القابلة للتصحيح فقط) تقصّر القائمة، و **Refresh** يحدّثها.
3. اختر البرنامج، ثم من **Attach with:** (الإرفاق باستخدام:) اختر المحرك: `debugpy` لـ Python، و `gdb` للبرامج الأصلية (C و C++‎)، و Delve لـ Go، و `netcoredbg` لـ .NET.
4. اضغط **Attach** (إرفاق). الآن نقاط التوقف في ملفات ذلك البرنامج تعمل.
5. **Stop Debugging** (`Shift+F5`) **يفصل** المصحح فقط، والبرنامج **يستمر في العمل**.

> ⚠️ أنت ترفق بنسخة المصدر التي عندك: إذا كان البرنامج العامل مبنيًا من كود مختلف، لن تطابق نقاط التوقف الأسطر.

## حالات خاصة

| ما تريد | كيف |
|---|---|
| تصحيح JavaScript في موقع ويب | فعّل **Debug JavaScript in the Preview** في **Tools > Options... > Web**، ثم `F9` في ملفات `.js` |
| تطبيق Expo على الويب | **Debug > Debug Expo Web Page (js-debug)** |
| تطبيق Flutter | **Debug > Mobile**: **Hot Reload** (`Ctrl+Alt+R`)، و **Hot Restart**، و **Always Use the Dart Debugger for F5** |
| مصحح من إضافة VS Code | **Debug > Debug with Extension Debugger** |
| برنامج بخيوط كثيرة | **Debug > Windows > Threads**: انقر خيطًا مرتين لترى مكدسه ومتغيراته |
| مجلد VS Code فيه `launch.json` | إعدادات التشغيل فيه تصبح أهداف تشغيل وتصحيح في البيئة |

## مثال: ما يراه المصحح

أيًّا كان المحرك، ما يصلك هو نفسه: **أين توقف البرنامج**، و**المكدس**، و**المتغيرات**. هذا برنامج BASIC صغير يطبع "تقرير توقف" كالذي يرسله المحرك للبيئة، لتفهم الفكرة:

```vb run
Sub Report(fileName As String, lineNo As Integer, frames As String, vars As String)
    Debug.Print "توقف في " & fileName & " السطر " & lineNo
    Debug.Print "المكدس: " & frames
    Debug.Print "المتغيرات: " & vars
End Sub

Sub Main()
    Report "Module1.bas", 12, "CalcTax <- ProcessOrder <- Main", "amount=200"
End Sub
```

```text output
توقف في Module1.bas السطر 12
المكدس: CalcTax <- ProcessOrder <- Main
المتغيرات: amount=200
```

## أخطاء شائعة

- **"debugpy is not installed":** ثبّته من **Tools > Language Servers and Debuggers...** أو في بيئة المشروع الافتراضية.
- **نقاط توقف رمادية لا تعمل في C++‎:** البرنامج مبني بدون معلومات تصحيح. ابنه من البيئة بإعداد التصحيح.
- **ظن أن Stop يغلق البرنامج المرفق:** في الإرفاق يفصل المصحح فقط.
- **إرفاق محرك خاطئ:** `debugpy` لا يفهم برنامج Go. اختر المحرك المناسب في **Attach with:**.

## اختبر نفسك

```quiz
{"question": "ماذا يحدث للبرنامج المرفق عند الضغط على Stop Debugging؟", "choices": ["يُغلق", "يُفصل المصحح ويستمر البرنامج في العمل", "يُعاد تشغيله", "يُحذف"], "answer": 1, "explanation": "في الإرفاق، Stop يفصل المصحح فقط."}
```

```quiz
{"question": "أي محرك تختاره للإرفاق ببرنامج Python يعمل؟", "choices": ["gdb", "debugpy", "Delve", "netcoredbg"], "answer": 1, "explanation": "debugpy لـ Python، و gdb للبرامج الأصلية، و Delve لـ Go، و netcoredbg لـ .NET."}
```

```quiz
{"question": "أين تثبّت مصححات اللغات وخوادمها؟", "choices": ["Tools > Language Servers and Debuggers...", "File > New Window", "Help > About", "Format > Lock Controls"], "answer": 0, "explanation": "نافذة خوادم اللغات والمصححات تعرض الحالة وتثبّت الناقص."}
```

## الخلاصة

- الأزرار واحدة لكل اللغات، والمحرك يختلف: المدمج لـ BASIC، و debugpy و gdb و Delve و JDWP و netcoredbg ...
- **Tools > Language Servers and Debuggers...** للتثبيت، و **Install Delve** لـ Go.
- **Debug > Attach to Process...** (`Ctrl+Alt+P`): اختر البرنامج والمحرك، و Stop يفصل فقط.
- JavaScript في المعاينة، و Flutter من **Debug > Mobile**، والخيوط في **Threads**.
