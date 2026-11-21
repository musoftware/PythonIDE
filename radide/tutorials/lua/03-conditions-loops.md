# الدرس 3: الشروط وحلقات التكرار

البرنامج الذكي **يختار** (الشروط) و**يكرر** (الحلقات). هاتان الأداتان معًا تصنعان معظم منطق أي برنامج.

> **تشبيه:** الشرط مثل **إشارة المرور**: إذا كانت خضراء تمر، وإلا تقف. والحلقة مثل **الدوران في مضمار**: تلف حتى تكمل عدد اللفات المطلوب.

## المقارنة

```lua run
print(5 > 3)
print(5 == 5)
print(5 ~= 5)
print("a" < "b")
print(10 >= 11)
```

```text output
true
true
false
true
false
```

| العامل | معناه |
|---|---|
| `==` | يساوي |
| `~=` | لا يساوي (لاحظ: `~=` وليس `!=`) |
| `<` `>` `<=` `>=` | أصغر، أكبر، أصغر أو يساوي، أكبر أو يساوي |

## `if` و`elseif` و`else`

```lua run
local score = 82

if score >= 90 then
  print("ممتاز")
elseif score >= 75 then
  print("جيد جدًا")
elseif score >= 50 then
  print("مقبول")
else
  print("راسب")
end
```

```text output
جيد جدًا
```

- بعد الشرط تأتي الكلمة `then`، وفي النهاية `end`.
- `elseif` كلمة واحدة.

## `and` و`or` و`not`

```lua run
local age, has_ticket = 20, true
if age >= 18 and has_ticket then
  print("تفضل بالدخول")
end

local day = "الجمعة"
if day == "الجمعة" or day == "السبت" then
  print("عطلة")
end

print(not true)
local name = nil
print(name or "زائر")      -- قيمة افتراضية
```

```text output
تفضل بالدخول
عطلة
false
زائر
```

`name or "زائر"` حيلة شائعة في Lua: إذا كان `name` يساوي `nil` فالنتيجة `"زائر"`.

### ما هو «الصحيح» في Lua؟

**كل شيء صحيح ما عدا `false` و`nil`**. حتى الرقم `0` والنص الفارغ `""` صحيحان:

```lua run
if 0 then print("0 صحيح في Lua") end
if "" then print("النص الفارغ صحيح") end
```

```text output
0 صحيح في Lua
النص الفارغ صحيح
```

## حلقة `for` العددية

```lua run
for i = 1, 5 do
  io.write(i, " ")
end
print()

for i = 10, 1, -3 do
  io.write(i, " ")
end
print()

for i = 1, 3 do
  print(i .. " × 7 = " .. i * 7)
end
```

```text output
1 2 3 4 5 
10 7 4 1 
1 × 7 = 7
2 × 7 = 14
3 × 7 = 21
```

الصيغة: `for متغير = بداية, نهاية, خطوة do ... end`. الخطوة اختيارية وافتراضيها 1، والنهاية **مشمولة**.

## `while` و`repeat ... until`

```lua run
local balance, years = 1000, 0
while balance < 2000 do
  balance = balance * 1.1
  years = years + 1
end
print("يتضاعف المبلغ بعد " .. years .. " سنوات")

local n = 3
repeat
  print("العد: " .. n)
  n = n - 1
until n == 0
print("انطلق!")
```

```text output
يتضاعف المبلغ بعد 8 سنوات
العد: 3
العد: 2
العد: 1
انطلق!
```

- `while شرط do ... end` تكرر **ما دام** الشرط صحيحًا (وقد لا تنفذ أبدًا).
- `repeat ... until شرط` تنفذ **مرة على الأقل** ثم تكرر **حتى يصبح** الشرط صحيحًا.

## `break` و`goto continue`

```lua run
for i = 1, 10 do
  if i % 2 == 0 then goto continue end   -- تخطَّ الزوجي
  if i > 7 then break end                -- توقف بعد 7
  io.write(i, " ")
  ::continue::
end
print()
```

```text output
1 3 5 7 
```

- `break` تخرج من الحلقة.
- لا توجد `continue` في Lua، ونستخدم بدلها `goto continue` مع العلامة `::continue::` في آخر الحلقة.

## مثال: مجموع حتى الصفر

```lua run
local total = 0
while true do
  local n = tonumber(io.read("l"))
  if n == 0 then break end
  total = total + n
end
print("المجموع = " .. total)
```

```text input
4
6
15
0
```

```text output
المجموع = 25
```

## أخطاء شائعة

### نسيان `then` أو `do`

<!-- compile-error -->
```lua
if 5 > 3
  print("نعم")
end
```

الخطأ: `'then' expected near 'print'`، أي «كان متوقعًا then قبل print». ومثلها `'do' expected` مع `for` و`while`.

### `!=` بدل `~=`

`if x != 5 then` خطأ في Lua. اكتب `if x ~= 5 then`.

### تغيير متغير الحلقة داخلها

في `for i = 1, 10 do` لا تغيّر `i` داخل الحلقة؛ Lua تعيد ضبطه في كل دورة ولن يحدث ما تتوقعه.

## تمارين

### التمرين 1

اقرأ عددًا واطبع `زوجي` أو `فردي`، ثم `موجب` أو `سالب` أو `صفر`.

```lua exercise
local n = tonumber(io.read("l"))
```

```lua solution
local n = tonumber(io.read("l"))
if n % 2 == 0 then print("زوجي") else print("فردي") end
if n > 0 then
  print("موجب")
elseif n < 0 then
  print("سالب")
else
  print("صفر")
end
```

```text input
-7
```

```text output
فردي
سالب
```

### التمرين 2

اطبع جدول الضرب للعدد الذي يقرؤه البرنامج من 1 إلى 5.

```lua exercise
local n = tonumber(io.read("l"))
```

```lua solution
local n = tonumber(io.read("l"))
for i = 1, 5 do
  print(n .. " × " .. i .. " = " .. n * i)
end
```

```text input
6
```

```text output
6 × 1 = 6
6 × 2 = 12
6 × 3 = 18
6 × 4 = 24
6 × 5 = 30
```

### التمرين 3

اطبع الأعداد الأولية الأصغر من 20. العدد أولي إذا لم يقبل القسمة على أي عدد من 2 إلى ما قبله.

```lua exercise
for n = 2, 19 do
  -- افحص هل n أولي
end
print()
```

```lua solution
for n = 2, 19 do
  local prime = true
  for d = 2, n - 1 do
    if n % d == 0 then
      prime = false
      break
    end
  end
  if prime then io.write(n, " ") end
end
print()
```

```text output
2 3 5 7 11 13 17 19 
```

## اختبر نفسك

```quiz
{"question": "كيف تُكتب «لا يساوي» في Lua؟", "choices": ["!=", "<>", "~=", "=/="], "answer": 2, "explanation": "عامل عدم المساواة في Lua هو ~=."}
```

```quiz
{"question": "كم مرة تُنفذ for i = 1, 10, 2 do ... end؟", "choices": ["10", "5", "4", "6"], "answer": 1, "explanation": "قيم i هي 1 و3 و5 و7 و9، أي خمس مرات."}
```

```quiz
{"question": "ما الفرق بين while وrepeat ... until؟", "choices": ["لا فرق", "repeat تنفذ مرة واحدة على الأقل", "while أسرع", "repeat لا تقبل break"], "answer": 1, "explanation": "repeat تفحص الشرط في النهاية فتنفذ الجسم مرة على الأقل."}
```

## الخلاصة

- `if ... then ... elseif ... else ... end`، و`~=` للاختلاف، و`and` و`or` و`not`.
- كل شيء صحيح ما عدا `false` و`nil`، و`x or default` لقيمة افتراضية.
- `for i = a, b, step do`، و`while ... do`، و`repeat ... until`.
- `break` للخروج، و`goto continue` لتخطي دورة.
