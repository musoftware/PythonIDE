# الدرس 4: الدوال

**الدالة** (function) مجموعة أوامر لها اسم، نكتبها مرة ونستدعيها كلما احتجنا. وفي Lua الدوال **قيم** مثل الأرقام والنصوص: تُخزن في متغيرات، وتُمرر لدوال أخرى، وتُرجع من دوال.

> **تشبيه:** الدالة مثل **آلة العصير**: تضع فيها فاكهة (المعاملات)، فتخرج لك عصيرًا (القيمة المرجعة). لا يهمك ما يحدث بداخلها في كل مرة.

## تعريف دالة واستدعاؤها

```lua run
local function greet(name)
  print("أهلًا يا " .. name .. "!")
end

local function square(x)
  return x * x
end

greet("سارة")
print(square(7))
print(square(square(2)))
```

```text output
أهلًا يا سارة!
49
16
```

- `local function name(params) ... end` تعرّف دالة محلية (الأفضل دائمًا).
- `return` تُرجع القيمة وتنهي الدالة. الدالة بلا `return` تُرجع `nil`.

## إرجاع عدة قيم

ميزة جميلة في Lua: الدالة تستطيع إرجاع **أكثر من قيمة**:

```lua run
local function min_max(a, b, c)
  local lo = math.min(a, b, c)
  local hi = math.max(a, b, c)
  return lo, hi
end

local small, big = min_max(7, 2, 9)
print(small, big)

local function divide(a, b)
  return a // b, a % b
end
local q, r = divide(17, 5)
print("الناتج " .. q .. " والباقي " .. r)
```

```text output
2	9
الناتج 3 والباقي 2
```

## المعاملات الناقصة والزائدة والقيم الافتراضية

```lua run
local function power(base, exp)
  exp = exp or 2          -- قيمة افتراضية
  return base ^ exp
end

print(power(5))
print(power(2, 10))
print(power(3, 3, 99))    -- المعامل الزائد يُهمل
```

```text output
25.0
1024.0
27.0
```

المعامل الذي لا يُمرَّر يساوي `nil`، والحيلة `exp = exp or 2` تعطيه قيمة افتراضية.

## عدد غير محدد من المعاملات: `...`

```lua run
local function sum(...)
  local total = 0
  for _, v in ipairs({...}) do
    total = total + v
  end
  return total, select("#", ...)
end

print(sum(1, 2, 3))
print(sum(10, 20, 30, 40))
```

```text output
6	3
100	4
```

`...` تعني «كل المعاملات»، و`{...}` تجمعها في جدول، و`select("#", ...)` تعطي عددها.

## الدوال قيم

```lua run
local function apply(f, x)
  return f(x)
end

local double = function(n) return n * 2 end

print(apply(double, 21))
print(apply(function(n) return n + 100 end, 5))
print(apply(math.abs, -8))
```

```text output
42
105
8
```

- `function(n) return n * 2 end` **دالة مجهولة** (بلا اسم)، خزّناها في `double`.
- يمكن تمرير دالة كمعامل لدالة أخرى، وهذا أساس أشياء كثيرة مثل الترتيب المخصص والأحداث.

## الإغلاقات (Closures): دالة تتذكر

```lua run
local function make_counter()
  local count = 0
  return function()
    count = count + 1
    return count
  end
end

local c1 = make_counter()
local c2 = make_counter()
print(c1(), c1(), c1())
print(c2())
```

```text output
1	2	3
1
```

الدالة الداخلية **تتذكر** المتغير `count` حتى بعد انتهاء `make_counter`، ولكل عداد نسخته الخاصة. هذا اسمه **الإغلاق** (closure).

## النطاق: `local` مرة أخرى

```lua run
local x = 10
local function f()
  local x = 99    -- متغير جديد داخل الدالة يحجب الخارجي
  return x
end
print(f(), x)

do
  local y = 5
  print(y)
end
print(y)
```

```text output
99	10
5
nil
```

المتغير `local` يعيش داخل **الكتلة** التي عُرّف فيها فقط (الدالة، أو `do ... end`، أو جسم الحلقة).

## الدالة التي تستدعي نفسها (Recursion)

```lua run
local function factorial(n)
  if n <= 1 then return 1 end
  return n * factorial(n - 1)
end

print(factorial(5))
print(factorial(10))
```

```text output
120
3628800
```

لكي تستدعي الدالة المحلية نفسها يجب أن تُعرّف بالصيغة `local function name` (وليس `local name = function`).

## أخطاء شائعة

### استدعاء دالة قبل تعريفها

<!-- compile-error -->
```lua
print(twice(4))
local function twice(n) return n * 2 end
```

الخطأ: `attempt to call a nil value (global 'twice')`. Lua تنفذ من أعلى لأسفل؛ عرّف الدالة قبل استخدامها.

### نسيان `return`

دالة تحسب ولا تُرجع شيئًا: `local function add(a, b) local s = a + b end` ثم `print(add(1, 2))` تطبع `nil`.

## تمارين

### التمرين 1

اكتب دالة `is_even(n)` تُرجع `true` أو `false`، ودالة `count_even(...)` تُرجع عدد المعاملات الزوجية.

```lua exercise
local function is_even(n)
end

local function count_even(...)
end

print(is_even(4), is_even(7))
print(count_even(1, 2, 3, 4, 6))
```

```lua solution
local function is_even(n)
  return n % 2 == 0
end

local function count_even(...)
  local c = 0
  for _, v in ipairs({...}) do
    if is_even(v) then c = c + 1 end
  end
  return c
end

print(is_even(4), is_even(7))
print(count_even(1, 2, 3, 4, 6))
```

```text output
true	false
3
```

### التمرين 2

اكتب دالة `circle(r)` تُرجع المساحة والمحيط مقربين لمنزلتين (استخدم `math.pi` و`string.format`).

```lua exercise
local function circle(r)
end

local area, perimeter = circle(3)
print("المساحة: " .. area)
print("المحيط: " .. perimeter)
```

```lua solution
local function circle(r)
  local area = string.format("%.2f", math.pi * r * r)
  local perimeter = string.format("%.2f", 2 * math.pi * r)
  return area, perimeter
end

local area, perimeter = circle(3)
print("المساحة: " .. area)
print("المحيط: " .. perimeter)
```

```text output
المساحة: 28.27
المحيط: 18.85
```

## اختبر نفسك

```quiz
{"question": "ماذا تطبع print((function() return 1, 2 end)())؟", "choices": ["1", "2", "1\t2", "خطأ"], "answer": 2, "explanation": "الدالة تُرجع قيمتين، وprint تطبعهما مفصولتين بمسافة جدولة."}
```

```quiz
{"question": "ما قيمة المعامل الذي لم يُمرر عند الاستدعاء؟", "choices": ["0", "nil", "\"\"", "خطأ"], "answer": 1, "explanation": "المعاملات الناقصة تساوي nil، ولذلك نستخدم x = x or قيمة لنعطيها قيمة افتراضية."}
```

```quiz
{"question": "ما الإغلاق (closure)؟", "choices": ["دالة تغلق البرنامج", "دالة داخلية تتذكر متغيرات الدالة التي أنشأتها", "حلقة لا تنتهي", "جدول مغلق"], "answer": 1, "explanation": "الإغلاق دالة تحتفظ بالمتغيرات المحلية للدالة الخارجية حتى بعد انتهائها."}
```

## الخلاصة

- `local function name(params) ... return ... end`.
- الدالة تستطيع إرجاع عدة قيم: `local a, b = f()`.
- `x = x or default` للقيم الافتراضية، و`...` لعدد غير محدد من المعاملات.
- الدوال قيم: تُخزن وتُمرر، والإغلاق دالة تتذكر متغيراتها.
