# الدرس 11: قاموس المصطلحات (إنجليزي - عربي)

أهم المصطلحات التي مرت بك في دورة Lua، مع مثال لكل منها.

## أساسيات

| English | العربية | مثال في Lua |
|---|---|---|
| variable / local variable | متغير / متغير محلي | `local x = 5` |
| global variable | متغير عام | `x = 5` |
| nil | لا شيء (قيمة غائبة) | `nil` |
| number (integer / float) | رقم (صحيح / عشري) | `42` / `3.5` |
| string | نص | `"قمر"` |
| boolean | قيمة منطقية | `true` |
| concatenation | إلصاق النصوص | `"a" .. "b"` |
| comment | تعليق | `-- ...` |
| integer division | قسمة صحيحة | `7 // 2` |

## التحكم

| English | العربية | مثال |
|---|---|---|
| condition | شرط | `if x > 0 then` |
| loop | حلقة تكرار | `for` / `while` / `repeat` |
| numeric for | حلقة for العددية | `for i = 1, 10 do` |
| generic for | حلقة for العامة | `for k, v in pairs(t) do` |
| break | اخرج من الحلقة | |

## الدوال

| English | العربية | مثال |
|---|---|---|
| function | دالة | `local function f(x)` |
| parameter / argument | معامل / وسيط | |
| return value(s) | القيمة (القيم) المرجعة | `return a, b` |
| varargs | عدد غير محدد من المعاملات | `...` |
| anonymous function | دالة مجهولة | `function(x) return x end` |
| closure | إغلاق (دالة تتذكر متغيراتها) | |
| recursion | استدعاء ذاتي | `factorial(n - 1)` |
| scope / block | نطاق / كتلة | `do ... end` |

## الجداول والكائنات

| English | العربية | مثال |
|---|---|---|
| table | جدول | `{}` |
| array / list | قائمة (تبدأ من 1) | `{"أ", "ب"}` |
| dictionary / key-value | قاموس / مفتاح وقيمة | `{name = "علي"}` |
| length operator | عامل الطول | `#t` |
| reference | مرجع | `b = a` (نفس الجدول) |
| metatable | جدول وصفي | `setmetatable(obj, Class)` |
| metamethod | دالة وصفية | `__index` / `__add` |
| method / self | دالة كائن / الكائن نفسه | `obj:move()` |
| inheritance | وراثة | |
| module | وحدة | `require("geometry")` |

## النصوص والأخطاء والملفات

| English | العربية |
|---|---|
| pattern | نمط (للبحث في النصوص) |
| capture | التقاط (جزء بين أقواس في النمط) |
| format | تنسيق (`string.format`) |
| error / protected call | خطأ / استدعاء محمي (`pcall`) |
| assertion | تأكيد (`assert`) |
| file handle | مقبض ملف (`io.open`) |

## الواجهات الرسومية

| English | العربية |
|---|---|
| form | نموذج (نافذة) |
| control | أداة / عنصر تحكم |
| event / event handler | حدث / معالج حدث |
| property | خاصية |
| Toolbox / Properties window | صندوق الأدوات / نافذة الخصائص |
| GUI Bridge | جسر الواجهة |
| breakpoint / step over | نقطة توقف / خطوة فوق |

## اختبر نفسك

```quiz
{"question": "ما الترجمة الأنسب لـ metatable؟", "choices": ["جدول كبير", "جدول وصفي يحدد سلوك جدول آخر", "جدول في قاعدة بيانات", "جدول الضرب"], "answer": 1, "explanation": "الجدول الوصفي يحدد ماذا يحدث عند البحث عن مفتاح غير موجود، أو عند جمع جدولين، وغير ذلك."}
```

## إلى أين بعد ذلك؟

- **ألعاب:** إطار LÖVE (love2d.org) يستخدم Lua لصنع ألعاب ثنائية الأبعاد.
- **Roblox:** لغة Luau مبنية على Lua 5.1، ومعظم ما تعلمته ينطبق عليها.
- **الكتاب الرسمي:** «Programming in Lua» لمصمم اللغة روبرتو إيروزاليمسكي.
- جرّب دورات أخرى في **Help > Tutorials (Arabic lessons)...**.
