# الدرس 6: الدوال والكتل (Blocks)

عندما يتكرر جزء من الكود في أماكن كثيرة، نعطيه اسمًا ونستدعيه بالاسم. هذا هو **الدالة** (method، وتسمى أيضًا function). وفي Ruby أداة خاصة جميلة اسمها **الكتلة** (block): قطعة كود تمررها لدالة لتنفذها.

> **تشبيه:** الدالة مثل **وصفة طبخ** مكتوبة مرة واحدة: «اصنع كعكة» وتعطيها المقادير (المعاملات) فتُرجع لك كعكة (القيمة المرجعة). والكتلة مثل **ملاحظة تضعها مع الطلب**: «وزيّنها بالفراولة».

## تعريف دالة واستدعاؤها

```ruby run
def greet(name)
  puts "أهلًا يا #{name}!"
end

greet("سارة")
greet "خالد"
```

```text output
أهلًا يا سارة!
أهلًا يا خالد!
```

- `def` تبدأ التعريف، ثم اسم الدالة، ثم **المعاملات** (parameters) بين قوسين، وفي النهاية `end`.
- عند الاستدعاء يمكن حذف الأقواس: `greet "خالد"`، وهذا شائع في Ruby.

## القيمة المرجعة

الدالة في Ruby تُرجع **قيمة آخر سطر فيها** تلقائيًا، ويمكنك استخدام `return` للخروج المبكر:

```ruby run
def square(x)
  x * x
end

def grade(score)
  return "غير صالح" if score < 0 || score > 100
  score >= 50 ? "ناجح" : "راسب"
end

puts square(7)
puts square(square(2))
puts grade(75)
puts grade(30)
puts grade(120)
```

```text output
49
16
ناجح
راسب
غير صالح
```

`شرط ? قيمة1 : قيمة2` اسمه **العامل الثلاثي** (ternary): إذا كان الشرط صحيحًا فالنتيجة القيمة الأولى، وإلا الثانية.

## القيم الافتراضية والمعاملات المسماة

```ruby run
def power(base, exp = 2)
  base ** exp
end

def order(item, quantity: 1, size: "وسط")
  "#{quantity} × #{item} (#{size})"
end

puts power(5)
puts power(2, 10)
puts order("قهوة")
puts order("شاي", size: "كبير", quantity: 3)
```

```text output
25
1024
1 × قهوة (وسط)
3 × شاي (كبير)
```

المعاملات المسماة (keyword arguments) مثل `quantity:` تُكتب باسمها عند الاستدعاء، فلا يهم ترتيبها، ويصبح الكود أوضح.

## نطاق المتغيرات

المتغيرات التي تُنشأ داخل الدالة **محلية**: لا تُرى خارجها، والدالة لا ترى متغيرات البرنامج الخارجية:

```ruby run
total = 100

def add_tax(price)
  tax = price * 0.14
  price + tax
end

puts add_tax(200)
puts total
puts defined?(tax).inspect
```

```text output
228.0
100
nil
```

إذا أردت أن تستخدم الدالة قيمة من الخارج، فمررها لها كمعامل.

## الكتل (Blocks) و`yield`

استخدمنا الكتل من قبل مع `each` و`times`. يمكنك أن تكتب دالة تقبل كتلة وتنفذها بالكلمة `yield`:

```ruby run
def twice
  yield
  yield
end

twice { puts "Ruby!" }

def with_border
  puts "-" * 12
  yield
  puts "-" * 12
end

with_border { puts "داخل الإطار" }

def each_even(limit)
  0.step(limit, 2) { |n| yield n }
end

each_even(6) { |n| print n, " " }
puts
```

```text output
Ruby!
Ruby!
------------
داخل الإطار
------------
0 2 4 6 
```

## `map` و`select` و`reduce`: الكتل مع المصفوفات

هذه الدوال من أقوى ما في Ruby، وكلها تأخذ كتلة:

```ruby run
nums = [1, 2, 3, 4, 5, 6]
p nums.map { |n| n * n }
p nums.select { |n| n.even? }
p nums.reject { |n| n.even? }
puts nums.reduce(0) { |sum, n| sum + n }
puts nums.find { |n| n > 3 }
puts nums.any? { |n| n > 5 }
puts nums.all? { |n| n > 0 }
p nums.map(&:to_s)
```

```text output
[1, 4, 9, 16, 25, 36]
[2, 4, 6]
[1, 3, 5]
21
4
true
true
["1", "2", "3", "4", "5", "6"]
```

| الدالة | تُرجع |
|---|---|
| `map` | مصفوفة جديدة بعد تطبيق الكتلة على كل عنصر |
| `select` | العناصر التي تجعل الكتلة صحيحة |
| `reject` | عكس `select` |
| `reduce` | قيمة واحدة تجمع العناصر |
| `find` | أول عنصر يحقق الشرط |
| `any?` / `all?` | هل يوجد عنصر / هل كل العناصر تحقق الشرط |

`map(&:to_s)` اختصار لـ `map { |n| n.to_s }`.

## الدوال المجهولة: `lambda`

يمكنك حفظ كتلة في متغير باستخدام `lambda` (أو السهم `->`)، واستدعاؤها لاحقًا بـ `.call` أو `.()`:

```ruby run
double = ->(x) { x * 2 }
add = lambda { |a, b| a + b }
puts double.call(21)
puts add.(3, 4)
p [1, 2, 3].map(&double)
```

```text output
42
7
[2, 4, 6]
```

## أخطاء شائعة

### عدد المعاملات خطأ

`square(1, 2)` تعطي `wrong number of arguments (given 2, expected 1)` أي «عدد معاملات خطأ: أعطيت 2 والمتوقع 1».

### استخدام الدالة قبل تعريفها

Ruby تنفذ الملف من أعلى لأسفل، فإذا استدعيت دالة في سطر قبل `def` الخاصة بها ستحصل على `undefined method`. ضع التعريفات في الأعلى.

### `yield` بدون كتلة

إذا استدعيت `twice` دون كتلة ستظهر `no block given (yield)`. يمكنك أن تفحص بـ `block_given?` قبل `yield`.

## تمارين

### التمرين 1

اكتب دالة `max_of(a, b, c)` تُرجع أكبر الأعداد الثلاثة (دون `max`)، ثم اطبع `max_of(4, 19, 7)`.

```ruby exercise
def max_of(a, b, c)
  # ...
end

puts max_of(4, 19, 7)
```

```ruby solution
def max_of(a, b, c)
  biggest = a
  biggest = b if b > biggest
  biggest = c if c > biggest
  biggest
end

puts max_of(4, 19, 7)
```

```text output
19
```

### التمرين 2

لديك مصفوفة أسعار. استخدم `map` لزيادة كل سعر 10%، و`select` لإبقاء الأسعار الأكبر من 100 فقط، ثم اطبع النتيجة.

```ruby exercise
prices = [50, 95, 120, 200, 80]
```

```ruby solution
prices = [50, 95, 120, 200, 80]
raised = prices.map { |p| (p * 1.1).round }
expensive = raised.select { |p| p > 100 }
p raised
p expensive
```

```text output
[55, 105, 132, 220, 88]
[105, 132, 220]
```

### التمرين 3

اكتب دالة `repeat(n)` تنفذ الكتلة المعطاة `n` مرات وتمرر لها رقم المرة بدءًا من 1.

```ruby exercise
def repeat(n)
  # استخدم yield
end

repeat(3) { |i| puts "المرة #{i}" }
```

```ruby solution
def repeat(n)
  1.upto(n) { |i| yield i }
end

repeat(3) { |i| puts "المرة #{i}" }
```

```text output
المرة 1
المرة 2
المرة 3
```

## اختبر نفسك

```quiz
{"question": "ماذا تُرجع الدالة def f; 5; 10; end عند استدعائها؟", "choices": ["5", "10", "nil", "[5, 10]"], "answer": 1, "explanation": "الدالة تُرجع قيمة آخر تعبير فيها، وهو 10."}
```

```quiz
{"question": "ما ناتج [1, 2, 3].map { |x| x + 1 }؟", "choices": ["[1, 2, 3]", "[2, 3, 4]", "6", "9"], "answer": 1, "explanation": "map تطبق الكتلة على كل عنصر وتُرجع مصفوفة جديدة."}
```

```quiz
{"question": "ما وظيفة yield داخل الدالة؟", "choices": ["إنهاء البرنامج", "تنفيذ الكتلة التي مُررت للدالة", "إرجاع قيمة", "طباعة نص"], "answer": 1, "explanation": "yield تنفذ الكتلة الممررة للدالة، ويمكن أن تمرر لها قيمًا."}
```

## الخلاصة

- `def name(params) ... end` لتعريف دالة، والقيمة المرجعة هي آخر تعبير أو ما بعد `return`.
- القيم الافتراضية `exp = 2` والمعاملات المسماة `size: "وسط"` تجعل الاستدعاء مرنًا.
- متغيرات الدالة محلية.
- الكتلة `{ |x| ... }` أو `do |x| ... end` تُمرر لدالة وتنفذها `yield`.
- `map` و`select` و`reduce` و`find` تجعل العمل مع المصفوفات قصيرًا وواضحًا.
