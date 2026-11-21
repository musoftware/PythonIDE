# الدرس 3: الشروط واتخاذ القرار

حتى الآن كانت برامجنا تنفذ كل الأسطر بالترتيب. لكن البرامج الحقيقية **تختار**: إذا كانت كلمة المرور صحيحة ادخل، وإلا اعرض رسالة خطأ. هذا هو **الشرط** (condition).

> **تشبيه:** الشرط مثل مفترق طرق عليه لافتة: «إذا كنت ذاهبًا إلى الإسكندرية فاتجه يمينًا، وإلا فاتجه يسارًا». السيارة تسلك طريقًا واحدًا فقط.

## عوامل المقارنة

نتيجة المقارنة دائمًا `true` أو `false`:

```ruby run
puts 5 > 3
puts 5 < 3
puts 5 == 5
puts 5 != 5
puts 4 >= 4
puts "ali" == "Ali"
```

```text output
true
false
true
false
true
false
```

| العامل | معناه |
|---|---|
| `==` | يساوي (لاحظ: علامتان) |
| `!=` | لا يساوي |
| `>` و`<` | أكبر من، أصغر من |
| `>=` و`<=` | أكبر من أو يساوي، أصغر من أو يساوي |

## `if` و`elsif` و`else`

```ruby run
score = 78

if score >= 90
  puts "ممتاز"
elsif score >= 75
  puts "جيد جدًا"
elsif score >= 50
  puts "مقبول"
else
  puts "راسب"
end
puts "انتهى التقييم"
```

```text output
جيد جدًا
انتهى التقييم
```

- كل `if` تنتهي بالكلمة `end`.
- تُكتب `elsif` هكذا (وليس `elseif` ولا `else if`).
- Ruby تفحص الشروط من أعلى لأسفل وتنفذ **أول** فرع شرطه صحيح فقط، ثم تقفز إلى ما بعد `end`.
- المسافة البادئة (سطران) ليست إجبارية لكنها تجعل الكود مقروءًا، والـ IDE تضيفها لك.

## العوامل المنطقية: `&&` و`||` و`!`

```ruby run
age = 20
has_ticket = true

if age >= 18 && has_ticket
  puts "تفضل بالدخول"
end

day = "الجمعة"
if day == "الجمعة" || day == "السبت"
  puts "عطلة نهاية الأسبوع"
end

puts !true
```

```text output
تفضل بالدخول
عطلة نهاية الأسبوع
false
```

| العامل | معناه | يكون صحيحًا عندما |
|---|---|---|
| `&&` | و (and) | الطرفان صحيحان |
| `\|\|` | أو (or) | أحد الطرفين على الأقل صحيح |
| `!` | ليس (not) | يعكس القيمة |

## `unless` والشرط في آخر السطر

Ruby تحب أن يُقرأ الكود كالجمل. `unless` تعني «إلا إذا»، أي عكس `if`. ويمكن كتابة شرط قصير في **آخر السطر**:

```ruby run
balance = 50
price = 80

puts "الرصيد لا يكفي" if balance < price
puts "تمت عملية الشراء" unless balance < price

logged_in = false
unless logged_in
  puts "من فضلك سجّل الدخول"
end
```

```text output
الرصيد لا يكفي
من فضلك سجّل الدخول
```

> **نصيحة:** استخدم `unless` مع شرط بسيط فقط. `unless` مع `else` أو مع شروط مركبة تربك القارئ؛ استخدم `if` حينها.

## `case` و`when`

عندما تقارن متغيرًا واحدًا بقيم كثيرة، فإن `case` أوضح من سلسلة `elsif`:

```ruby run
day = 3
name = case day
       when 1 then "السبت"
       when 2 then "الأحد"
       when 3 then "الاثنين"
       else "يوم آخر"
       end
puts name

grade = 85
case grade
when 90..100 then puts "A"
when 80...90 then puts "B"
when 70...80 then puts "C"
else puts "F"
end
```

```text output
الاثنين
B
```

- `90..100` **مدى** (Range) يشمل 90 و100، و`80...90` (ثلاث نقاط) يشمل 80 ولا يشمل 90.
- `case` في Ruby **تُرجع قيمة**، لذلك خزّنا نتيجتها في `name`. وكذلك `if`!

## ما هو «الصحيح» في Ruby؟

قاعدة بسيطة ومهمة: **كل القيم صحيحة (truthy) ما عدا `false` و`nil`**. حتى `0` والنص الفارغ `""` صحيحان، وهذا يختلف عن لغات أخرى:

```ruby run
zero = 0
empty = ""
nothing = nil
puts "0 صحيح" if zero
puts "النص الفارغ صحيح" if empty
puts "nil خطأ" unless nothing
```

```text output
0 صحيح
النص الفارغ صحيح
nil خطأ
```

## مثال كامل: الرقم زوجي أم فردي؟

```ruby run
n = gets.to_i
if n.even?
  puts "#{n} زوجي"
else
  puts "#{n} فردي"
end
puts "موجب" if n.positive?
```

```text input
14
```

```text output
14 زوجي
موجب
```

الدوال التي تنتهي بعلامة استفهام مثل `even?` و`positive?` و`zero?` تُرجع `true` أو `false`، وهذا عُرف جميل في Ruby.

## أخطاء شائعة

### `=` بدل `==`

`if x = 5` لا تقارن، بل **تخزّن** 5 في `x` فيصبح الشرط صحيحًا دائمًا! Ruby تعطي تحذيرًا `found '= literal' in conditional`. استخدم `==` للمقارنة.

### نسيان `end`

<!-- compile-error -->
```ruby
if 5 > 3
  puts "نعم"
```

الخطأ: `syntax error ... unexpected end-of-input` أي «انتهى الملف بشكل غير متوقع». كل `if` و`case` تحتاج `end`.

### كتابة `else if`

`else if` تفتح `if` جديدة داخل `else` وتحتاج `end` إضافية. اكتب `elsif`.

## تمارين

### التمرين 1

اقرأ درجة طالب (0 إلى 100) واطبع `ناجح` إذا كانت 50 فأكثر، وإلا `راسب`.

```ruby exercise
grade = gets.to_i
```

```ruby solution
grade = gets.to_i
if grade >= 50
  puts "ناجح"
else
  puts "راسب"
end
```

```text input
64
```

```text output
ناجح
```

### التمرين 2

اقرأ ثلاثة أعداد (كل عدد في سطر) واطبع أكبرها باستخدام `if` و`elsif` (دون استخدام `max`).

```ruby exercise
a = gets.to_i
b = gets.to_i
c = gets.to_i
```

```ruby solution
a = gets.to_i
b = gets.to_i
c = gets.to_i
if a >= b && a >= c
  biggest = a
elsif b >= c
  biggest = b
else
  biggest = c
end
puts "الأكبر هو #{biggest}"
```

```text input
12
45
7
```

```text output
الأكبر هو 45
```

### التمرين 3

اقرأ رقم شهر (1 إلى 12) واستخدم `case` لتطبع فصل السنة: الشتاء (12، 1، 2)، الربيع (3 إلى 5)، الصيف (6 إلى 8)، الخريف (9 إلى 11)، وإلا `رقم غير صحيح`.

```ruby exercise
month = gets.to_i
```

```ruby solution
month = gets.to_i
season = case month
         when 12, 1, 2 then "الشتاء"
         when 3..5 then "الربيع"
         when 6..8 then "الصيف"
         when 9..11 then "الخريف"
         else "رقم غير صحيح"
         end
puts season
```

```text input
7
```

```text output
الصيف
```

لاحظ أن `when 12, 1, 2` تقبل عدة قيم مفصولة بفواصل.

## اختبر نفسك

```quiz
{"question": "أي من القيم التالية تُعتبر false في شرط Ruby؟", "choices": ["0", "\"\" (نص فارغ)", "nil", "[] (مصفوفة فارغة)"], "answer": 2, "explanation": "في Ruby القيمتان الوحيدتان الخاطئتان هما false وnil. الصفر والنص الفارغ صحيحان."}
```

```quiz
{"question": "كيف تُكتب «وإلا إذا» في Ruby؟", "choices": ["else if", "elseif", "elsif", "elif"], "answer": 2, "explanation": "الكلمة في Ruby هي elsif."}
```

```quiz
{"question": "هل المدى 1...5 يشمل الرقم 5؟", "choices": ["نعم", "لا"], "answer": 1, "explanation": "ثلاث نقاط تعني أن النهاية غير مشمولة، أما 1..5 بنقطتين فتشمل 5."}
```

## الخلاصة

- `if` / `elsif` / `else` / `end` لاختيار طريق واحد من عدة طرق.
- `&&` و`||` و`!` لربط الشروط وعكسها.
- `unless` عكس `if`، ويمكن كتابة الشرط القصير في آخر السطر.
- `case` و`when` لمقارنة قيمة واحدة بقيم كثيرة أو بمديات مثل `80...90`.
- كل شيء صحيح في Ruby ما عدا `false` و`nil`.
