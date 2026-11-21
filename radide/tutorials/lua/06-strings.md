# الدرس 6: النصوص والأنماط

النصوص في كل مكان: أسماء، ورسائل، وملفات، وأوامر. Lua تعطيك مكتبة `string` فيها دوال كثيرة، ونظام **أنماط** (patterns) صغير وقوي للبحث في النصوص.

> **تشبيه:** الأنماط مثل **مصفاة الذهب**: تهز الرمل فيها فيبقى ما يطابق الشكل الذي تريده فقط (أرقام، أو كلمات، أو بريد إلكتروني).

## دوال النص الأساسية

```lua run
local s = "Hello Lua"
print(s:upper())
print(s:lower())
print(s:len())
print(s:sub(1, 5))
print(s:sub(-3))
print(s:rep(2, " | "))
print(s:reverse())
```

```text output
HELLO LUA
hello lua
9
Hello
Lua
Hello Lua | Hello Lua
auL olleH
```

- الكتابة `s:upper()` تساوي `string.upper(s)`. النقطتان `:` تمرران النص نفسه كأول معامل.
- `sub(i, j)` تقطع من الحرف `i` إلى `j` (البداية 1، والأرقام السالبة من النهاية).

> **العربية:** دوال `string` تعمل على **البايتات**، والحرف العربي بايتان أو أكثر. لذلك `("سلام"):sub(1, 2)` تعطي الحرف الأول فقط، و`upper` لا تغيّر الحروف العربية. لعدّ الحروف استخدم `utf8.len`، وللمرور عليها `utf8.codes`.

## البحث والاستبدال

```lua run
local text = "أحب لغة Lua وأحب الألعاب"
print(text:find("Lua"))
print(text:find("Python"))
local new, count = text:gsub("أحب", "أعشق")
print(new)
print("عدد الاستبدالات: " .. count)
print(("a,b,,c"):gsub(",", ";"))
```

```text output
15	17
nil
أعشق لغة Lua وأعشق الألعاب
عدد الاستبدالات: 2
a;b;;c	3
```

- `find` تُرجع موضع البداية والنهاية **بالبايت** (لهذا كان موضع `Lua` هو 15 وليس 10: كل حرف عربي قبلها بايتان)، أو `nil` إذا لم تجد.
- `gsub(pattern, replacement)` تستبدل كل التطابقات، وتُرجع النص الجديد وعدد الاستبدالات.

## التنسيق: `string.format`

```lua run
local name, score, avg = "منى", 95, 87.456
print(string.format("الطالبة %s حصلت على %d", name, score))
print(string.format("المتوسط: %.1f", avg))
print(string.format("[%5d]", 42))
print(string.format("[%-5d]", 42))
print(string.format("%03d", 7))
print(string.format("%x", 255))
print(string.format("%5.1f%%", 12.345))
```

```text output
الطالبة منى حصلت على 95
المتوسط: 87.5
[   42]
[42   ]
007
ff
 12.3%
```

| الرمز | معناه |
|---|---|
| `%s` | نص |
| `%d` | عدد صحيح |
| `%.2f` | عدد عشري بمنزلتين |
| `%5d` / `%-5d` | عرض 5 خانات، يمين / يسار |
| `%03d` | أصفار في البداية |
| `%%` | علامة النسبة نفسها |

## الأنماط (Patterns)

| النمط | يطابق |
|---|---|
| `%d` | رقم |
| `%a` | حرف إنجليزي |
| `%s` | مسافة بيضاء |
| `%w` | حرف أو رقم |
| `.` | أي حرف |
| `%S` و`%D`... | العكس (أي شيء ليس مسافة، ليس رقمًا...) |
| `+` | مرة أو أكثر |
| `*` | صفر مرة أو أكثر |
| `?` | اختياري |
| `^` و`$` | بداية النص ونهايته |
| `( )` | التقاط جزء |

```lua run
local msg = "طلبت 3 أقلام و 12 دفترًا بسعر 250 جنيه"
for n in msg:gmatch("%d+") do
  io.write(n, " ")
end
print()

local date = "2026-11-21"
local y, m, d = date:match("(%d+)-(%d+)-(%d+)")
print(d .. "/" .. m .. "/" .. y)

print(("  مسافات زائدة  "):match("^%s*(.-)%s*$") .. "|")
print(("user@mail.com"):match("^[%w%.]+@[%w%.]+%.%a+$") ~= nil)
print(("not-an-email"):match("^[%w%.]+@[%w%.]+%.%a+$") ~= nil)
```

```text output
3 12 250 
21/11/2026
مسافات زائدة|
true
false
```

- `gmatch` تعطي كل التطابقات واحدًا تلو الآخر في حلقة `for`.
- `match` تُرجع الأجزاء الملتقطة بالأقواس، أو `nil`.
- `[%w%.]` **مجموعة**: حرف أو رقم أو نقطة. و`.-` تعني «أي شيء، أقل عدد ممكن».

> **ملحوظة:** أنماط Lua أبسط من «التعابير النمطية» (Regular Expressions) في اللغات الأخرى، لكنها تكفي لمعظم الحاجات. والرمز الخاص فيها هو `%` وليس `\`.

## تقسيم نص

لا توجد دالة `split` جاهزة في Lua، لكنها سطران بـ `gmatch`:

```lua run
local function split(s, sep)
  local parts = {}
  for piece in (s .. sep):gmatch("(.-)" .. sep) do
    parts[#parts + 1] = piece
  end
  return parts
end

local row = split("علي,80,القاهرة", ",")
print(#row, row[1], row[3])
```

```text output
3	علي	القاهرة
```

## المرور على الحروف العربية

```lua run
local word = "قمر"
for _, code in utf8.codes(word) do
  io.write(utf8.char(code), "-")
end
print()
print(utf8.len(word))
```

```text output
ق-م-ر-
3
```

## أخطاء شائعة

### الرموز الخاصة في `gsub` و`find`

`("1+1"):find("+")` خطأ أو نتيجة غريبة، لأن `+` رمز خاص في الأنماط. اكتب `%+`، أو مرر `true` كمعامل رابع لتبحث بحثًا حرفيًا: `s:find("+", 1, true)`.

### النصوص لا تتغير

`s:upper()` لا تغيّر `s`، بل تُرجع نصًا جديدًا. النصوص في Lua **ثابتة** (immutable). اكتب `s = s:upper()`.

## تمارين

### التمرين 1

اقرأ جملة إنجليزية واطبع عدد كلماتها، وأطول كلمة فيها.

```lua exercise
local sentence = io.read("l")
```

```lua solution
local sentence = io.read("l")
local count, longest = 0, ""
for word in sentence:gmatch("%a+") do
  count = count + 1
  if #word > #longest then longest = word end
end
print("عدد الكلمات: " .. count)
print("أطول كلمة: " .. longest)
```

```text input
Lua is a powerful and fast language
```

```text output
عدد الكلمات: 7
أطول كلمة: powerful
```

### التمرين 2

اقرأ رقم هاتف مثل `010-1234-5678` واحذف منه كل ما ليس رقمًا، ثم اطبع الرقم وعدد أرقامه.

```lua exercise
local phone = io.read("l")
```

```lua solution
local phone = io.read("l")
local digits = phone:gsub("%D", "")
print(digits)
print("عدد الأرقام: " .. #digits)
```

```text input
010-1234-5678
```

```text output
01012345678
عدد الأرقام: 11
```

لاحظ أن `gsub` تُرجع قيمتين، و`local digits = ...` تأخذ الأولى فقط.

## اختبر نفسك

```quiz
{"question": "ماذا تُرجع (\"abcdef\"):sub(2, 4)؟", "choices": ["abc", "bcd", "cde", "bc"], "answer": 1, "explanation": "sub(2, 4) من الحرف الثاني إلى الرابع: bcd."}
```

```quiz
{"question": "أي نمط يطابق رقمًا واحدًا أو أكثر؟", "choices": ["%d", "%d+", "\\d+", "[0-9]?"], "answer": 1, "explanation": "%d رقم واحد، و+ تعني مرة أو أكثر."}
```

```quiz
{"question": "بعد s:upper() هل يتغير s؟", "choices": ["نعم", "لا، تُرجع نصًا جديدًا"], "answer": 1, "explanation": "النصوص ثابتة في Lua، والدوال تُرجع نصوصًا جديدة."}
```

## الخلاصة

- `s:upper()` و`s:sub(i, j)` و`s:rep(n)` و`s:find()` و`s:gsub()`.
- `string.format` لتنسيق الأرقام والنصوص.
- الأنماط: `%d` و`%a` و`%s` و`+` و`*` والأقواس للالتقاط، و`gmatch` و`match`.
- دوال `string` تعمل على البايتات؛ استخدم `utf8.len` و`utf8.codes` للعربية.
