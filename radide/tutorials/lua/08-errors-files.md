# الدرس 8: معالجة الأخطاء والملفات

ماذا يحدث إذا قسم برنامجك على `nil`، أو حاول فتح ملف غير موجود؟ بدون معالجة سيتوقف البرنامج برسالة خطأ. في هذا الدرس نتعلم كيف **نلتقط** الأخطاء، وكيف نقرأ الملفات ونكتبها.

> **تشبيه:** `pcall` مثل **قفاز الفرن**: تمسك به الصينية الساخنة (الكود الخطر)، فإذا كانت ساخنة جدًا لا تحترق يدك، بل تعرف فقط أنها ساخنة.

## `error` و`pcall`

```lua run
local function divide(a, b)
  if b == 0 then
    error("لا يمكن القسمة على صفر")
  end
  return a / b
end

local ok, result = pcall(divide, 10, 2)
print(ok, result)

ok, result = pcall(divide, 10, 0)
print(ok)
print(result)
print("البرنامج مستمر")
```

```text output
true	5.0
false
main.lua:3: لا يمكن القسمة على صفر
البرنامج مستمر
```

- `error("رسالة")` تثير خطأ وتوقف الدالة.
- `pcall(f, args...)` («استدعاء محمي») تنفذ الدالة؛ إذا نجحت تُرجع `true` والنتيجة، وإذا فشلت تُرجع `false` ورسالة الخطأ، **دون أن يتوقف البرنامج**.
- Lua تضيف اسم الملف ورقم السطر إلى الرسالة (`main.lua:3:`). لتمنع ذلك اكتب `error("رسالة", 0)`.

## التقاط أخطاء Lua نفسها

```lua run
local ok, err = pcall(function()
  local t = nil
  return t.name
end)
print(ok)
print(err)

local ok2, err2 = pcall(function()
  return 1 + {}
end)
print(err2)
```

```text output
false
main.lua:3: attempt to index a nil value (local 't')
main.lua:9: attempt to perform arithmetic on a table value
```

## `assert`: تأكد وإلا أوقف

```lua run
local function set_age(age)
  assert(type(age) == "number", "العمر يجب أن يكون رقمًا")
  assert(age >= 0 and age <= 150, "العمر خارج المدى")
  return "تم حفظ العمر " .. age
end

print(set_age(30))
print(select(2, pcall(set_age, "ثلاثون")))
print(select(2, pcall(set_age, 200)))
```

```text output
تم حفظ العمر 30
main.lua:2: العمر يجب أن يكون رقمًا
main.lua:3: العمر خارج المدى
```

`assert(شرط, رسالة)` تثير خطأ بالرسالة إذا كان الشرط خاطئًا. و`select(2, ...)` تأخذ القيمة الثانية مما تُرجعه `pcall`.

## كتابة ملف وقراءته

```lua run
local f = assert(io.open("notes.txt", "w"))
f:write("السطر الأول\n")
f:write("السطر الثاني\n")
f:close()

f = assert(io.open("notes.txt", "a"))     -- إضافة في الآخر
f:write("السطر الثالث\n")
f:close()

f = assert(io.open("notes.txt", "r"))
local all = f:read("a")
f:close()
io.write(all)

local n = 0
for line in io.lines("notes.txt") do
  n = n + 1
  print(n .. ": " .. line)
end
os.remove("notes.txt")
print(io.open("notes.txt") == nil)
```

```text output
السطر الأول
السطر الثاني
السطر الثالث
1: السطر الأول
2: السطر الثاني
3: السطر الثالث
true
```

| الكتابة | وظيفتها |
|---|---|
| `io.open(path, "w")` | يفتح للكتابة (ويمسح القديم) |
| `io.open(path, "a")` | يفتح للإضافة في الآخر |
| `io.open(path, "r")` | يفتح للقراءة (الافتراضي) |
| `f:write(...)` | يكتب |
| `f:read("a")` / `f:read("l")` | يقرأ كل الملف / سطرًا |
| `io.lines(path)` | يمر على أسطر الملف |
| `f:close()` | يغلق الملف (مهم!) |
| `os.remove(path)` | يحذف الملف |

## `io.open` لا يثير خطأ بل يُرجع `nil`

```lua run
local f, err = io.open("missing.txt", "r")
if not f then
  print("تعذر فتح الملف:")
  print(err)
else
  f:close()
end
```

```text output
تعذر فتح الملف:
missing.txt: No such file or directory
```

لذلك كتبنا `assert(io.open(...))` في المثال السابق: إذا فشل الفتح يتوقف البرنامج برسالة واضحة.

## مثال: حفظ الدرجات واسترجاعها

```lua run
local scores = {{"علي", 80}, {"منى", 95}, {"خالد", 67}}

local f = assert(io.open("scores.csv", "w"))
for _, s in ipairs(scores) do
  f:write(s[1], ",", s[2], "\n")
end
f:close()

local total, count = 0, 0
for line in io.lines("scores.csv") do
  local name, score = line:match("^(.-),(%d+)$")
  total, count = total + tonumber(score), count + 1
  print(name .. " => " .. score)
end
print(string.format("المتوسط: %.1f", total / count))
os.remove("scores.csv")
```

```text output
علي => 80
منى => 95
خالد => 67
المتوسط: 80.7
```

الملفات تُنشأ في **مجلد المشروع**، لأن الـ IDE تشغّل البرنامج من هناك.

## أخطاء شائعة

### نسيان `close`

الكتابة قد تبقى في ذاكرة مؤقتة ولا تصل إلى الملف إلا عند `close`. أغلق الملف دائمًا بعد الكتابة.

### استخدام الملف بعد فشل فتحه

`local f = io.open("x.txt"); f:read("a")` تعطي `attempt to index a nil value (local 'f')` إذا لم يوجد الملف. افحص `f` أو استخدم `assert`.

## تمارين

### التمرين 1

اكتب دالة `safe_number(s)` تستخدم `tonumber` وتثير خطأ `"ليس رقمًا: " .. s` إذا فشل التحويل. ثم استدعها بـ `pcall` مع `"42"` ومع `"abc"`، واطبع النتيجة أو الرسالة (استخدم `error(msg, 0)` لتمنع إضافة رقم السطر).

```lua exercise
local function safe_number(s)
end

for _, s in ipairs({"42", "abc"}) do
  -- pcall ...
end
```

```lua solution
local function safe_number(s)
  local n = tonumber(s)
  if not n then error("ليس رقمًا: " .. s, 0) end
  return n
end

for _, s in ipairs({"42", "abc"}) do
  local ok, res = pcall(safe_number, s)
  if ok then
    print("الرقم: " .. res)
  else
    print("خطأ: " .. res)
  end
end
```

```text output
الرقم: 42
خطأ: ليس رقمًا: abc
```

### التمرين 2

اكتب 5 أعداد في الملف `nums.txt` (كل عدد في سطر)، ثم اقرأها بـ `io.lines` واطبع مجموعها، ثم احذف الملف.

```lua exercise
local nums = {4, 8, 15, 16, 23}
```

```lua solution
local nums = {4, 8, 15, 16, 23}
local f = assert(io.open("nums.txt", "w"))
for _, n in ipairs(nums) do f:write(n, "\n") end
f:close()

local sum = 0
for line in io.lines("nums.txt") do
  sum = sum + tonumber(line)
end
print("المجموع: " .. sum)
os.remove("nums.txt")
```

```text output
المجموع: 66
```

## اختبر نفسك

```quiz
{"question": "ماذا تُرجع pcall إذا حدث خطأ؟", "choices": ["nil فقط", "false ورسالة الخطأ", "true", "توقف البرنامج"], "answer": 1, "explanation": "pcall تُرجع false ثم رسالة الخطأ، ويستمر البرنامج."}
```

```quiz
{"question": "ماذا يُرجع io.open لملف غير موجود في وضع القراءة؟", "choices": ["يثير خطأ", "nil ورسالة الخطأ", "ملفًا فارغًا", "true"], "answer": 1, "explanation": "io.open لا تثير خطأ، بل تُرجع nil والرسالة، ولذلك نفحص النتيجة أو نستخدم assert."}
```

## الخلاصة

- `error(msg)` تثير خطأ، و`pcall(f, ...)` تلتقطه وتُرجع `ok, result`.
- `assert(شرط, رسالة)` للتأكد من الافتراضات.
- `io.open(path, mode)` و`f:write` و`f:read` و`io.lines` و`f:close` للملفات.
- `io.open` تُرجع `nil` عند الفشل؛ افحص النتيجة دائمًا.
