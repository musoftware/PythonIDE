# الدرس 5: الجداول (Tables): القوائم والقواميس

في Lua بنية بيانات واحدة فقط تفعل كل شيء: **الجدول** (table). يكون قائمة مرتبة، أو قاموسًا (مفتاح وقيمة)، أو كائنًا، أو وحدة برمجية. إذا فهمت الجداول فهمت نصف Lua.

> **تشبيه:** الجدول مثل **خزانة أدراج** متعددة الاستخدام: يمكنك ترقيم الأدراج 1 و2 و3 (قائمة)، أو كتابة أسماء عليها «جوارب» و«قمصان» (قاموس)، أو الاثنين معًا.

## الجدول كقائمة

```lua run
local fruits = {"تفاح", "موز", "برتقال"}
print(fruits[1])
print(fruits[3])
print(#fruits)
print(fruits[10])
```

```text output
تفاح
برتقال
3
nil
```

> **مهم جدًا:** الترقيم في Lua يبدأ من **1** وليس من 0 كمعظم اللغات. و`#fruits` تعطي عدد العناصر.

## الإضافة والحذف والترتيب

```lua run
local nums = {5, 3, 8}
table.insert(nums, 10)          -- في الآخر
table.insert(nums, 1, 0)        -- في الموضع 1
nums[#nums + 1] = 7             -- طريقة أخرى للإضافة في الآخر
print(table.concat(nums, ", "))
local removed = table.remove(nums)       -- احذف الأخير
table.remove(nums, 1)                    -- احذف الأول
print(table.concat(nums, ", "), "حُذف:", removed)
table.sort(nums)
print(table.concat(nums, " < "))
table.sort(nums, function(a, b) return a > b end)
print(table.concat(nums, " > "))
```

```text output
0, 5, 3, 8, 10, 7
5, 3, 8, 10	حُذف:	7
3 < 5 < 8 < 10
10 > 8 > 5 > 3
```

| الدالة | وظيفتها |
|---|---|
| `table.insert(t, v)` | أضف `v` في آخر الجدول |
| `table.insert(t, i, v)` | أضف `v` في الموضع `i` |
| `table.remove(t)` / `table.remove(t, i)` | احذف الأخير / العنصر `i` وأرجعه |
| `table.concat(t, sep)` | ألصق العناصر في نص واحد |
| `table.sort(t, cmp)` | رتب الجدول (مع دالة مقارنة اختيارية) |

## المرور على القائمة: `ipairs`

```lua run
local names = {"علي", "منى", "خالد"}
for i, name in ipairs(names) do
  print(i .. ". " .. name)
end

local total = 0
for _, n in ipairs({10, 20, 30}) do
  total = total + n
end
print("المجموع: " .. total)
```

```text output
1. علي
2. منى
3. خالد
المجموع: 60
```

`ipairs` تعطي في كل دورة **الرقم والقيمة**. والاسم `_` عُرف لمتغير لا نحتاجه.

## الجدول كقاموس

```lua run
local student = {name = "سارة", age = 20, city = "القاهرة"}
print(student.name)
print(student["age"])
student.grade = 95            -- أضف مفتاحًا
student.city = nil            -- احذف مفتاحًا
print(student.city)
print(student.grade)
```

```text output
سارة
20
nil
95
```

- `{name = "سارة"}` تعني المفتاح `"name"` والقيمة `"سارة"`.
- `student.name` و`student["name"]` نفس الشيء. استخدم الأقواس إذا كان المفتاح فيه مسافات أو متغيرًا.
- لحذف مفتاح أعطه القيمة `nil`.

## المرور على القاموس: `pairs`

`pairs` تمر على كل المفاتيح، لكن **بترتيب غير مضمون**. إذا أردت ترتيبًا ثابتًا فاجمع المفاتيح ورتبها:

```lua run
local prices = {tea = 10, coffee = 25, juice = 15}

local keys = {}
for k in pairs(prices) do
  keys[#keys + 1] = k
end
table.sort(keys)

for _, k in ipairs(keys) do
  print(k .. " = " .. prices[k])
end
```

```text output
coffee = 25
juice = 15
tea = 10
```

## جداول داخل جداول

```lua run
local classroom = {
  {name = "علي", scores = {80, 90}},
  {name = "منى", scores = {95, 85}},
}

for _, s in ipairs(classroom) do
  local sum = 0
  for _, sc in ipairs(s.scores) do sum = sum + sc end
  print(s.name .. ": المتوسط " .. sum / #s.scores)
end
print(classroom[2].scores[1])
```

```text output
علي: المتوسط 85.0
منى: المتوسط 90.0
95
```

## الجدول يُمرر بالمرجع

```lua run
local a = {1, 2, 3}
local b = a          -- b و a نفس الجدول!
b[1] = 100
print(a[1])

local function add_item(t, v) t[#t + 1] = v end
add_item(a, 4)
print(#a)
```

```text output
100
4
```

الإسناد `b = a` لا ينسخ الجدول؛ بل يجعل الاسمين يشيران إلى **نفس** الجدول. والدالة التي تستقبل جدولًا تستطيع تعديله.

## مثال: عدّ تكرار الكلمات

```lua run
local text = "قط كلب قط عصفور كلب قط"
local counts, order = {}, {}
for word in text:gmatch("%S+") do
  if not counts[word] then
    counts[word] = 0
    order[#order + 1] = word
  end
  counts[word] = counts[word] + 1
end
for _, w in ipairs(order) do
  print(w .. ": " .. counts[w])
end
```

```text output
قط: 3
كلب: 2
عصفور: 1
```

`text:gmatch("%S+")` تعطي الكلمات واحدة تلو الأخرى (سنشرح الأنماط في الدرس القادم).

## أخطاء شائعة

### البدء من الصفر

`t[0]` في قائمة كُتبت `{"أ", "ب"}` تعطي `nil`. العنصر الأول `t[1]`.

### الثقوب في القائمة

إذا كتبت `t[2] = nil` في وسط قائمة، يصبح `#t` غير موثوق. للحذف من قائمة استخدم `table.remove(t, 2)`.

### الاعتماد على ترتيب `pairs`

لا تفترض أن `pairs` تعطي المفاتيح بترتيب الكتابة. رتب المفاتيح أو استخدم قائمة.

## تمارين

### التمرين 1

اقرأ 5 أعداد (كل عدد في سطر) في جدول، ثم اطبع أكبرها وأصغرها والمتوسط.

```lua exercise
local nums = {}
for i = 1, 5 do
  nums[i] = tonumber(io.read("l"))
end
```

```lua solution
local nums = {}
for i = 1, 5 do
  nums[i] = tonumber(io.read("l"))
end
local sum = 0
for _, n in ipairs(nums) do sum = sum + n end
print("الأكبر: " .. math.max(table.unpack(nums)))
print("الأصغر: " .. math.min(table.unpack(nums)))
print("المتوسط: " .. sum / #nums)
```

```text input
4
9
1
7
4
```

```text output
الأكبر: 9
الأصغر: 1
المتوسط: 5.0
```

`table.unpack(t)` تفك عناصر الجدول إلى معاملات منفصلة، فتصبح `math.max(4, 9, 1, 7, 4)`.

### التمرين 2

قاموس دليل هاتف. اقرأ اسمًا واطبع رقمه أو `غير موجود`.

```lua exercise
local phones = {["علي"] = "0100", ["منى"] = "0122", ["خالد"] = "0111"}
local name = io.read("l")
```

```lua solution
local phones = {["علي"] = "0100", ["منى"] = "0122", ["خالد"] = "0111"}
local name = io.read("l")
print(phones[name] or "غير موجود")
```

```text input
منى
```

```text output
0122
```

لاحظ `["علي"] = ...`: المفاتيح العربية تُكتب بين أقواس مربعة، لأن الصيغة المختصرة `name = ...` تقبل أسماء إنجليزية فقط.

## اختبر نفسك

```quiz
{"question": "ما رقم العنصر الأول في جدول Lua؟", "choices": ["0", "1", "-1", "حسب الجدول"], "answer": 1, "explanation": "القوائم في Lua تبدأ من 1."}
```

```quiz
{"question": "ما الفرق بين ipairs وpairs؟", "choices": ["لا فرق", "ipairs للقوائم بالترتيب 1، 2، 3، وpairs لكل المفاتيح بترتيب غير مضمون", "pairs أسرع دائمًا", "ipairs للقواميس فقط"], "answer": 1, "explanation": "ipairs تمر على الأرقام المتتالية من 1، وpairs تمر على كل المفاتيح."}
```

```quiz
{"question": "بعد local b = a ثم b[1] = 5، ما قيمة a[1]؟", "choices": ["القيمة القديمة", "5", "nil", "خطأ"], "answer": 1, "explanation": "الجداول تُنسخ بالمرجع: a وb اسمان لنفس الجدول."}
```

## الخلاصة

- الجدول `{}` هو البنية الوحيدة في Lua: قائمة تبدأ من 1، أو قاموس، أو الاثنين.
- `table.insert` و`table.remove` و`table.concat` و`table.sort`، و`#t` للطول.
- `ipairs` للقوائم بالترتيب، و`pairs` لكل المفاتيح (رتبها إذا احتجت ترتيبًا).
- الجداول تُمرر بالمرجع.
