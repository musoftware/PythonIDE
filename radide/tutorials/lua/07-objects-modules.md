# الدرس 7: الكائنات بالجداول الوصفية والوحدات

Lua لا تحتوي كلمة `class`، لكنها تسمح لك ببناء **كائنات** و**أصناف** بالجداول نفسها، مع أداة خاصة اسمها **الجدول الوصفي** (metatable). وفي نفس الدرس نتعلم تقسيم البرنامج إلى **وحدات** (modules) في ملفات منفصلة.

> **تشبيه:** الجدول الوصفي مثل **دليل التعليمات المرفق** بجهاز: إذا لم تجد زرًا على الجهاز نفسه، تبحث في الدليل لتعرف ماذا تفعل.

## كائن بسيط: جدول فيه بيانات ودوال

```lua run
local account = {owner = "سارة", balance = 100}

function account.deposit(self, amount)
  self.balance = self.balance + amount
end

function account:withdraw(amount)      -- نفس الشيء بكتابة أقصر
  self.balance = self.balance - amount
end

account.deposit(account, 50)
account:withdraw(30)                   -- تساوي account.withdraw(account, 30)
print(account.owner, account.balance)
```

```text output
سارة	120
```

- `self` تعني «الكائن نفسه».
- النقطتان `:` في التعريف تضيفان `self` تلقائيًا، وفي الاستدعاء تمرران الكائن تلقائيًا. **استخدم `:` دائمًا مع دوال الكائنات.**

## الصنف: قالب لكائنات كثيرة

```lua run
local Account = {}
Account.__index = Account          -- ابحث عن الدوال الناقصة في Account

function Account.new(owner, balance)
  local self = setmetatable({}, Account)
  self.owner = owner
  self.balance = balance or 0
  return self
end

function Account:deposit(amount)
  self.balance = self.balance + amount
end

function Account:info()
  return self.owner .. ": " .. self.balance
end

local a = Account.new("علي", 50)
local b = Account.new("منى")
a:deposit(25)
b:deposit(200)
print(a:info())
print(b:info())
```

```text output
علي: 75
منى: 200
```

كيف يعمل؟

1. كل كائن جدول صغير فيه **بياناته فقط** (`owner` و`balance`).
2. `setmetatable({}, Account)` تجعل `Account` الجدول الوصفي للكائن.
3. عندما تكتب `a:deposit(25)` لا تجد Lua المفتاح `deposit` في `a`، فتنظر في `__index` الخاص بجدوله الوصفي (وهو `Account`)، فتجد الدالة هناك.

## الوراثة

```lua run
local Animal = {}
Animal.__index = Animal

function Animal.new(name)
  return setmetatable({name = name}, Animal)
end

function Animal:speak() return "..." end

function Animal:introduce()
  return "أنا " .. self.name .. " وأقول: " .. self:speak()
end

local Cat = setmetatable({}, {__index = Animal})   -- Cat يرث من Animal
Cat.__index = Cat

function Cat.new(name)
  return setmetatable(Animal.new(name), Cat)
end

function Cat:speak() return "مياو" end

print(Animal.new("حيوان"):introduce())
print(Cat.new("مشمش"):introduce())
```

```text output
أنا حيوان وأقول: ...
أنا مشمش وأقول: مياو
```

سلسلة البحث: الكائن ← `Cat` ← `Animal`. الدالة `introduce` موجودة في `Animal` فقط، لكنها تستدعي `speak` الخاصة بالقط.

## دوال وصفية أخرى (Metamethods)

```lua run
local Vector = {}
Vector.__index = Vector

function Vector.new(x, y) return setmetatable({x = x, y = y}, Vector) end
Vector.__add = function(a, b) return Vector.new(a.x + b.x, a.y + b.y) end
Vector.__eq = function(a, b) return a.x == b.x and a.y == b.y end
Vector.__tostring = function(v) return "(" .. v.x .. ", " .. v.y .. ")" end

local v = Vector.new(1, 2) + Vector.new(3, 4)
print(tostring(v))
print(v == Vector.new(4, 6))
```

```text output
(4, 6)
true
```

`__add` تجعل `+` تعمل على كائناتك، و`__tostring` تحدد كيف يُطبع الكائن، و`__eq` تحدد معنى `==`.

## الوحدات (Modules): تقسيم البرنامج إلى ملفات

الوحدة ملف Lua **يُرجع جدولًا** فيه دواله. ونستخدمها من ملف آخر بالدالة `require`. في المثال التالي ملفان في مشروع واحد:

```lua run
-- #file: main.lua
local geometry = require("geometry")
print(geometry.circle_area(2))
print(geometry.rect_area(3, 4))
print(geometry.PI)

-- #file: geometry.lua
local M = {}

M.PI = 3.14159

function M.circle_area(r)
  return string.format("%.2f", M.PI * r * r)
end

function M.rect_area(w, h)
  return w * h
end

local function secret()     -- محلية: لا يراها من يستخدم الوحدة
  return 42
end

return M
```

```text output
12.57
12
3.14159
```

- السطر `-- #file: geometry.lua` في الدرس يعني «ما بعده ملف اسمه `geometry.lua`». عند «جرّبه» تنشئ الـ IDE الملفين.
- `require("geometry")` تبحث عن `geometry.lua` في مجلد المشروع، وتنفذه **مرة واحدة** فقط حتى لو استدعيتها عدة مرات.
- في RAD IDE: **Project > Add Module...** (إضافة وحدة برمجية...) تنشئ ملف وحدة جاهزًا بهذا الشكل.

## أخطاء شائعة

### `.` بدل `:` عند الاستدعاء

<!-- compile-error -->
```lua
local Account = {}
Account.__index = Account
function Account:deposit(n) self.balance = self.balance + n end
local a = setmetatable({balance = 0}, Account)
a.deposit(10)
```

الخطأ: `attempt to index a number value (local 'self')`، لأن `a.deposit(10)` جعلت `self` تساوي `10`. اكتب `a:deposit(10)`.

### نسيان `return M` في آخر الوحدة

بدون `return M` تُرجع `require` القيمة `true` بدل الجدول، وستحصل على `attempt to index a boolean value`.

## تمارين

### التمرين 1

اكتب صنف `Rectangle` فيه `new(w, h)` ودالتان `area` و`perimeter`، ثم اطبع مساحة ومحيط مستطيل 4 × 6.

```lua exercise
local Rectangle = {}
Rectangle.__index = Rectangle

-- function Rectangle.new(w, h) ...

local r = Rectangle.new(4, 6)
print("المساحة: " .. r:area())
print("المحيط: " .. r:perimeter())
```

```lua solution
local Rectangle = {}
Rectangle.__index = Rectangle

function Rectangle.new(w, h)
  return setmetatable({w = w, h = h}, Rectangle)
end

function Rectangle:area() return self.w * self.h end
function Rectangle:perimeter() return 2 * (self.w + self.h) end

local r = Rectangle.new(4, 6)
print("المساحة: " .. r:area())
print("المحيط: " .. r:perimeter())
```

```text output
المساحة: 24
المحيط: 20
```

### التمرين 2

اكتب وحدة `mathx.lua` فيها الدالتان `is_prime(n)` و`primes_upto(n)` (تُرجع جدولًا)، واستخدمها من `main.lua` لتطبع الأعداد الأولية حتى 30.

```lua exercise
-- #file: main.lua
local mathx = require("mathx")
print(table.concat(mathx.primes_upto(30), " "))

-- #file: mathx.lua
local M = {}
-- ...
return M
```

```lua solution
-- #file: main.lua
local mathx = require("mathx")
print(table.concat(mathx.primes_upto(30), " "))

-- #file: mathx.lua
local M = {}

function M.is_prime(n)
  if n < 2 then return false end
  for d = 2, math.floor(math.sqrt(n)) do
    if n % d == 0 then return false end
  end
  return true
end

function M.primes_upto(n)
  local out = {}
  for i = 2, n do
    if M.is_prime(i) then out[#out + 1] = i end
  end
  return out
end

return M
```

```text output
2 3 5 7 11 13 17 19 23 29
```

## اختبر نفسك

```quiz
{"question": "ماذا تفعل obj:move(5)؟", "choices": ["تستدعي move بدون معاملات", "تستدعي obj.move(obj, 5)", "تنشئ كائنًا جديدًا", "خطأ دائمًا"], "answer": 1, "explanation": "النقطتان تمرران الكائن نفسه كأول معامل (self)."}
```

```quiz
{"question": "ما وظيفة __index في الجدول الوصفي؟", "choices": ["ترقيم الجدول", "المكان الذي تبحث فيه Lua عن المفاتيح غير الموجودة في الكائن", "حذف المفاتيح", "طباعة الجدول"], "answer": 1, "explanation": "__index هو أساس الأصناف والوراثة في Lua."}
```

```quiz
{"question": "ماذا يجب أن يكون في آخر ملف الوحدة؟", "choices": ["end", "return M (الجدول الذي فيه الدوال)", "exit()", "لا شيء"], "answer": 1, "explanation": "require تُرجع ما يُرجعه ملف الوحدة، وهو عادة جدول الدوال."}
```

## الخلاصة

- الكائن جدول فيه بيانات، والدوال تُعرّف وتُستدعى بـ `:` لتأخذ `self`.
- الصنف = جدول + `__index` يشير إليه + `setmetatable({}, Class)`.
- الوراثة بسلسلة `__index`، والعوامل بـ `__add` و`__eq` و`__tostring`.
- الوحدة ملف يُرجع جدولًا، وتُستخدم بـ `require("name")`.
