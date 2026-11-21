# الدرس 5: المصفوفات (Array) والقواميس (Hash)

المتغير الواحد يحمل قيمة واحدة. لكن ماذا لو أردنا حفظ أسماء ثلاثين طالبًا؟ نحتاج **مجموعة** من القيم في متغير واحد. في Ruby أداتان أساسيتان: **المصفوفة** (Array) و**القاموس** (Hash).

> **تشبيه:** المصفوفة مثل **قطار** عرباته مرقمة 0 و1 و2...، تصل لأي عربة برقمها. والقاموس مثل **دفتر الهاتف**: تبحث بالاسم (المفتاح) فتجد الرقم (القيمة).

## المصفوفة: إنشاؤها والوصول لعناصرها

```ruby run
fruits = ["تفاح", "موز", "برتقال"]
puts fruits[0]
puts fruits[2]
puts fruits[-1]
puts fruits.length
p fruits.first(2)
```

```text output
تفاح
برتقال
برتقال
3
["تفاح", "موز"]
```

- العناصر بين قوسين مربعين `[...]` ومفصولة بفواصل.
- الترقيم (الفهرس index) يبدأ من **0**، و`-1` تعني العنصر الأخير.
- `length` (أو `size`) عدد العناصر.

## التعديل والإضافة والحذف

```ruby run
nums = [5, 3, 8]
nums << 10          # أضف في الآخر
nums.push(1)        # مثلها
nums.unshift(0)     # أضف في الأول
nums[1] = 50        # غيّر عنصرًا
p nums
nums.delete(8)      # احذف القيمة 8
last = nums.pop     # احذف الأخير وأرجعه
p nums
puts "حُذف: #{last}"
puts nums.include?(50)
```

```text output
[0, 50, 3, 8, 10, 1]
[0, 50, 3, 10]
حُذف: 1
true
```

## المرور على المصفوفة

```ruby run
names = ["علي", "منى", "خالد"]
names.each do |name|
  puts "أهلًا #{name}"
end
names.each_with_index do |name, i|
  puts "#{i + 1}. #{name}"
end
```

```text output
أهلًا علي
أهلًا منى
أهلًا خالد
1. علي
2. منى
3. خالد
```

## دوال جاهزة رائعة

```ruby run
scores = [70, 95, 88, 60, 95]
puts scores.sum
puts scores.max
puts scores.min
p scores.sort
p scores.sort.reverse
p scores.uniq
puts scores.count(95)
puts (scores.sum.to_f / scores.size).round(1)
puts scores.join(" - ")
```

```text output
408
95
60
[60, 70, 88, 95, 95]
[95, 95, 88, 70, 60]
[70, 95, 88, 60]
2
81.6
70 - 95 - 88 - 60 - 95
```

`join` تحوّل المصفوفة إلى نص، و`split` تفعل العكس: `"a,b,c".split(",")` تعطي `["a", "b", "c"]`.

## القاموس (Hash): مفتاح وقيمة

```ruby run
ages = { "علي" => 20, "منى" => 22 }
ages["خالد"] = 19           # أضف زوجًا جديدًا
puts ages["منى"]
p ages["سعيد"]               # مفتاح غير موجود
puts ages.length
ages.each do |name, age|
  puts "#{name}: #{age}"
end
```

```text output
22
nil
3
علي: 20
منى: 22
خالد: 19
```

- القاموس بين أقواس معقوصة `{ ... }`، وكل زوج `مفتاح => قيمة`.
- البحث عن مفتاح غير موجود يعطي `nil` (وليس خطأ).
- القاموس يحفظ ترتيب الإضافة.

## الرموز (Symbols) كمفاتيح

في Ruby نستخدم غالبًا **الرموز** مثل `:name` كمفاتيح، وهناك كتابة مختصرة لها:

```ruby run
book = { title: "Ruby للمبتدئين", pages: 250, available: true }
puts book[:title]
puts book[:pages]
book[:pages] += 10
p book.keys
puts book.key?(:price)
puts book.fetch(:price, "غير محدد")
```

```text output
Ruby للمبتدئين
250
[:title, :pages, :available]
false
غير محدد
```

`title: "..."` هي نفسها `:title => "..."`. والدالة `fetch(key, default)` ترجع قيمة افتراضية إذا لم يوجد المفتاح.

## مثال: عدّ تكرار الكلمات

```ruby run
text = "قط كلب قط عصفور كلب قط"
counts = Hash.new(0)        # القيمة الافتراضية لأي مفتاح جديد = 0
text.split.each { |word| counts[word] += 1 }
counts.each { |word, n| puts "#{word}: #{n}" }
```

```text output
قط: 3
كلب: 2
عصفور: 1
```

## أخطاء شائعة

### الفهرس خارج المصفوفة

`[1, 2, 3][10]` تعطي `nil` وليس خطأ. فإذا كتبت `[1, 2, 3][10] + 1` ستحصل على `undefined method '+' for nil`. تأكد من الفهرس أو استخدم `fetch`.

### الخلط بين `"name"` و`:name`

`{ name: "علي" }["name"]` تعطي `nil`! لأن المفتاح هو الرمز `:name` وليس النص `"name"`. اكتب `h[:name]`.

### نسيان أن الترقيم يبدأ من الصفر

العنصر الأول هو `a[0]` وليس `a[1]`، والأخير هو `a[a.length - 1]` أو ببساطة `a[-1]`.

## تمارين

### التمرين 1

اقرأ 5 أعداد (كل عدد في سطر) في مصفوفة، ثم اطبع المصفوفة مرتبة، وأكبر عدد، والمتوسط مقربًا لمنزلة واحدة.

```ruby exercise
nums = []
5.times { nums << gets.to_i }
```

```ruby solution
nums = []
5.times { nums << gets.to_i }
puts "مرتبة: #{nums.sort.join(", ")}"
puts "الأكبر: #{nums.max}"
puts "المتوسط: #{(nums.sum.to_f / nums.size).round(1)}"
```

```text input
12
7
30
18
3
```

```text output
مرتبة: 3, 7, 12, 18, 30
الأكبر: 30
المتوسط: 14.0
```

### التمرين 2

لديك قاموس أسعار. اقرأ اسم منتج واطبع سعره، أو `غير موجود` إذا لم يكن في القاموس.

```ruby exercise
prices = { "قلم" => 5, "دفتر" => 20, "حقيبة" => 150 }
item = gets.chomp
```

```ruby solution
prices = { "قلم" => 5, "دفتر" => 20, "حقيبة" => 150 }
item = gets.chomp
if prices.key?(item)
  puts "سعر #{item}: #{prices[item]} جنيه"
else
  puts "غير موجود"
end
```

```text input
دفتر
```

```text output
سعر دفتر: 20 جنيه
```

## اختبر نفسك

```quiz
{"question": "ما قيمة [10, 20, 30][-1]؟", "choices": ["10", "30", "nil", "خطأ"], "answer": 1, "explanation": "الفهرس -1 يعني العنصر الأخير."}
```

```quiz
{"question": "ماذا تُرجع h[\"x\"] إذا لم يكن المفتاح \"x\" موجودًا؟", "choices": ["0", "خطأ", "nil", "\"\""], "answer": 2, "explanation": "البحث عن مفتاح غير موجود يعطي nil، إلا إذا أنشأت القاموس بقيمة افتراضية مثل Hash.new(0)."}
```

```quiz
{"question": "{ name: \"علي\" } تساوي أيًا مما يلي؟", "choices": ["{ \"name\" => \"علي\" }", "{ :name => \"علي\" }", "[:name, \"علي\"]", "لا شيء مما سبق"], "answer": 1, "explanation": "الكتابة name: هي اختصار للرمز :name كمفتاح."}
```

## الخلاصة

- المصفوفة `[...]` قائمة مرتبة تصل لعناصرها بالفهرس من 0، و`-1` للأخير.
- `<<` و`push` و`pop` و`delete` و`include?` و`sort` و`sum` و`max` و`join` من أهم دوالها.
- القاموس `{ مفتاح => قيمة }`، والرموز `title:` هي المفاتيح المعتادة.
- `each` و`each_with_index` للمرور على المصفوفة، و`each { |k, v| }` على القاموس.
