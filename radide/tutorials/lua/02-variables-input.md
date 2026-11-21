# الدرس 2: المتغيرات والأنواع والإدخال

**المتغير** (variable) اسم نحفظ فيه قيمة لنستخدمها لاحقًا.

> **تشبيه:** المتغير مثل درج في خزانة عليه ملصق باسمه. تضع فيه شيئًا، وتفتحه لاحقًا بالاسم لتجده.

## `local`: المتغير المحلي

```lua run
local name = "سارة"
local age = 20
local height = 1.65
local student = true

print(name, age)
print(name .. " عمرها " .. age .. " سنة")
age = age + 1
print("بعد سنة: " .. age)
```

```text output
سارة	20
سارة عمرها 20 سنة
بعد سنة: 21
```

- في Lua إذا كتبت `x = 5` بدون `local` يصبح المتغير **عامًا** (global) يراه البرنامج كله. هذا مصدر أخطاء كثيرة في البرامج الكبيرة.
- العادة الجيدة: **اكتب `local` دائمًا** عند إنشاء متغير جديد، إلا إذا كنت تقصد متغيرًا عامًا.
- لا تكتب نوع المتغير؛ Lua تعرفه من القيمة.

## الأنواع الأساسية

```lua run
print(type(42))
print(type(3.14))
print(type("نص"))
print(type(true))
print(type(nil))
print(type({}))
print(type(print))
print(math.type(42), math.type(3.14))
```

```text output
number
number
string
boolean
nil
table
function
integer	float
```

| النوع | معناه | مثال |
|---|---|---|
| `number` | رقم (صحيح `integer` أو عشري `float`) | `42`، `3.14` |
| `string` | نص | `"مرحبا"` |
| `boolean` | قيمة منطقية | `true`، `false` |
| `nil` | «لا شيء»، القيمة الافتراضية لأي متغير لم يُعطَ قيمة | `nil` |
| `table` | جدول (القائمة والقاموس والكائن، كلها جداول!) | `{1, 2, 3}` |
| `function` | دالة (الدوال قيم مثل الأرقام) | `print` |

## `nil`: القيمة الغائبة

```lua run
local x
print(x)
print(undefined_variable)
x = 10
print(x)
x = nil
print(x)
```

```text output
nil
nil
10
nil
```

قراءة متغير لم يُعرَّف **لا تعطي خطأ** في Lua، بل تعطي `nil`. هذا مريح، لكنه يعني أن خطأ كتابة اسم متغير قد يمر بصمت! انتبه للأسماء.

## التحويل بين الأنواع

```lua run
print(tonumber("42") + 8)
print(tonumber("3.5") * 2)
print(tonumber("abc"))
print(tostring(100) .. " نقطة")
print("10" + 5)
print(math.floor(3.7), math.ceil(3.2))
print(string.format("%.2f", 3.14159))
```

```text output
50
7.0
nil
100 نقطة
15
3	4
3.14
```

- `tonumber` تحوّل النص إلى رقم، وتُرجع `nil` إذا لم يكن رقمًا.
- `"10" + 5` تعمل (Lua تحوّل النص تلقائيًا في العمليات الحسابية)، لكن الأوضح أن تستخدم `tonumber`.
- `string.format("%.2f", x)` تقرّب لمنزلتين عشريتين.

## الإسناد المتعدد

```lua run
local a, b = 1, 2
print(a, b)
a, b = b, a        -- تبديل القيمتين في سطر واحد!
print(a, b)
local x, y, z = 10, 20
print(x, y, z)
```

```text output
1	2
2	1
10	20	nil
```

## قراءة الإدخال: `io.read`

```lua run
io.write("ما اسمك؟ ")
local name = io.read("l")
io.write("كم عمرك؟ ")
local age = io.read("n")
print()
print("أهلًا يا " .. name .. "!")
print("بعد عشر سنوات سيكون عمرك " .. age + 10)
```

```text input
منى
22
```

```text output
ما اسمك؟ كم عمرك؟ 
أهلًا يا منى!
بعد عشر سنوات سيكون عمرك 32
```

| الكتابة | تقرأ |
|---|---|
| `io.read("l")` | سطرًا كاملًا (بدون رمز السطر الجديد) |
| `io.read("n")` | رقمًا |
| `io.read("a")` | كل الإدخال الباقي |

عند الضغط على «جرّبه» ترسل الـ IDE المدخلات المكتوبة في الدرس (`منى` ثم `22`) كأن المستخدم كتبها.

> **تنبيه:** بعد `io.read("n")` يبقى رمز السطر الجديد في الإدخال. إذا قرأت بعدها سطرًا بـ `io.read("l")` فستحصل على نص فارغ. الحل: اقرأ الأرقام كسطور ثم حوّلها: `tonumber(io.read("l"))`.

## طول النص والعربية

```lua run
local word = "Lua"
print(#word)
local arabic = "قمر"
print(#arabic)
print(utf8.len(arabic))
```

```text output
3
6
3
```

العامل `#` يعطي عدد **البايتات** وليس عدد الحروف. الحرف العربي يأخذ بايتين في ترميز UTF-8، لذلك `#"قمر"` تساوي 6. استخدم `utf8.len` لعدّ الحروف.

## أخطاء شائعة

### نسيان `local`

إذا كتبت `count = 0` داخل دالة بدل `local count = 0`، فأنت تنشئ (أو تغيّر) متغيرًا عامًا قد يستخدمه جزء آخر من البرنامج.

### جمع `nil` مع رقم

<!-- compile-error -->
```lua
local total
print(total + 1)
```

الخطأ: `attempt to perform arithmetic on a nil value (local 'total')`. أعطِ المتغير قيمة ابتدائية: `local total = 0`.

## تمارين

### التمرين 1

اقرأ عددين (كل عدد في سطر) واطبع مجموعهما ومتوسطهما.

```lua exercise
local a = tonumber(io.read("l"))
local b = tonumber(io.read("l"))
```

```lua solution
local a = tonumber(io.read("l"))
local b = tonumber(io.read("l"))
print("المجموع = " .. a + b)
print("المتوسط = " .. (a + b) / 2)
```

```text input
8
5
```

```text output
المجموع = 13
المتوسط = 6.5
```

### التمرين 2

اقرأ عدد الثواني (مثلًا `3725`) واطبعه بالشكل `1 ساعة 2 دقيقة 5 ثانية`. استخدم `//` و`%`.

```lua exercise
local s = tonumber(io.read("l"))
```

```lua solution
local s = tonumber(io.read("l"))
local h = s // 3600
local m = (s % 3600) // 60
local sec = s % 60
print(h .. " ساعة " .. m .. " دقيقة " .. sec .. " ثانية")
```

```text input
3725
```

```text output
1 ساعة 2 دقيقة 5 ثانية
```

## اختبر نفسك

```quiz
{"question": "ما قيمة متغير أنشأته بـ local x دون أن تعطيه قيمة؟", "choices": ["0", "\"\"", "nil", "خطأ"], "answer": 2, "explanation": "أي متغير بلا قيمة يساوي nil."}
```

```quiz
{"question": "ماذا يُرجع tonumber(\"12a\")؟", "choices": ["12", "0", "nil", "خطأ"], "answer": 2, "explanation": "tonumber تُرجع nil إذا لم يكن النص رقمًا صالحًا بالكامل."}
```

```quiz
{"question": "لماذا #\"سلام\" تساوي 8 وليس 4؟", "choices": ["خطأ في Lua", "لأن # تعد البايتات، والحرف العربي بايتان في UTF-8", "لأن النص فيه مسافات", "لأن # تضرب في 2"], "answer": 1, "explanation": "استخدم utf8.len لعدّ الحروف الحقيقية."}
```

## الخلاصة

- `local name = value` لإنشاء متغير محلي، واكتب `local` دائمًا.
- الأنواع: `number` و`string` و`boolean` و`nil` و`table` و`function`.
- `tonumber` و`tostring` و`string.format` للتحويل والتنسيق.
- `io.read("l")` لسطر، و`io.read("n")` لرقم.
- `#` تعد البايتات، و`utf8.len` تعد الحروف.
