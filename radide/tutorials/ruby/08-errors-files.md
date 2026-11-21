# الدرس 8: معالجة الأخطاء والملفات

البرامج الحقيقية تواجه مفاجآت: المستخدم يكتب حروفًا بدل رقم، أو ملف غير موجود، أو قسمة على صفر. البرنامج الجيد **لا ينهار**، بل يتعامل مع الخطأ بهدوء. في Ruby يسمى الخطأ **استثناء** (exception).

> **تشبيه:** معالجة الأخطاء مثل **شبكة الأمان** تحت لاعب السيرك: إذا سقط اللاعب لا ينتهي العرض، بل تلتقطه الشبكة ويكمل.

## `begin` و`rescue`

```ruby run
begin
  result = 10 / 0
  puts "لن يُطبع هذا السطر"
rescue ZeroDivisionError => e
  puts "خطأ: لا يمكن القسمة على صفر"
  puts "رسالة Ruby: #{e.message}"
end
puts "البرنامج مستمر"
```

```text output
خطأ: لا يمكن القسمة على صفر
رسالة Ruby: divided by 0
البرنامج مستمر
```

- الكود الذي قد يفشل يوضع بين `begin` و`rescue`.
- عند حدوث الخطأ تقفز Ruby فورًا إلى `rescue` وتترك بقية الأسطر.
- `=> e` تحفظ كائن الخطأ في `e`، و`e.message` نص الرسالة.

## أنواع متعددة و`else` و`ensure`

```ruby run
def safe_divide(a, b)
  result = Integer(a) / Integer(b)
rescue ZeroDivisionError
  "لا قسمة على صفر"
rescue ArgumentError
  "أدخل أرقامًا صحيحة"
else
  "الناتج = #{result}"
ensure
  puts "(انتهت محاولة #{a} / #{b})"
end

puts safe_divide("10", "2")
puts safe_divide("10", "0")
puts safe_divide("عشرة", "2")
```

```text output
(انتهت محاولة 10 / 2)
الناتج = 5
(انتهت محاولة 10 / 0)
لا قسمة على صفر
(انتهت محاولة عشرة / 2)
أدخل أرقامًا صحيحة
```

- داخل `def` يمكن كتابة `rescue` مباشرة بدون `begin`.
- `else` تُنفذ إذا **لم** يحدث خطأ، و`ensure` تُنفذ **دائمًا** (مكان مناسب لإغلاق الملفات مثلًا).
- `Integer("عشرة")` تثير `ArgumentError`، بعكس `"عشرة".to_i` التي تعطي `0` بصمت. استخدم `Integer()` عندما تريد اكتشاف الإدخال الخاطئ.

## إثارة خطأ بنفسك: `raise`

```ruby run
def set_age(age)
  raise ArgumentError, "العمر يجب أن يكون بين 0 و 150" unless (0..150).include?(age)
  "تم حفظ العمر #{age}"
end

puts set_age(30)
begin
  puts set_age(200)
rescue ArgumentError => e
  puts "مرفوض: #{e.message}"
end
```

```text output
تم حفظ العمر 30
مرفوض: العمر يجب أن يكون بين 0 و 150
```

## `retry`: أعد المحاولة

```ruby run
attempts = 0
begin
  attempts += 1
  n = Integer(gets.chomp)
  puts "شكرًا، أدخلت #{n}"
rescue ArgumentError
  puts "ليس رقمًا، حاول مرة أخرى"
  retry if attempts < 3
end
```

```text input
abc
12x
42
```

```text output
ليس رقمًا، حاول مرة أخرى
ليس رقمًا، حاول مرة أخرى
شكرًا، أدخلت 42
```

## الكتابة في ملف والقراءة منه

```ruby run
File.write("notes.txt", "السطر الأول\nالسطر الثاني\n")
File.open("notes.txt", "a") do |f|      # "a" = إضافة في آخر الملف
  f.puts "السطر الثالث"
end

puts File.read("notes.txt")
puts "عدد الأسطر: #{File.readlines("notes.txt").size}"
File.foreach("notes.txt").with_index(1) do |line, i|
  puts "#{i}: #{line.chomp}"
end
puts File.exist?("notes.txt")
File.delete("notes.txt")
puts File.exist?("notes.txt")
```

```text output
السطر الأول
السطر الثاني
السطر الثالث
عدد الأسطر: 3
1: السطر الأول
2: السطر الثاني
3: السطر الثالث
true
false
```

| الطريقة | وظيفتها |
|---|---|
| `File.write(path, text)` | تكتب الملف (وتمسح القديم) |
| `File.read(path)` | تقرأ الملف كله كنص |
| `File.readlines(path)` | مصفوفة من الأسطر |
| `File.foreach(path) { \|line\| }` | تمر على الأسطر واحدًا واحدًا |
| `File.open(path, "a") { \|f\| }` | تفتح الملف للإضافة وتغلقه تلقائيًا بعد الكتلة |
| `File.exist?(path)` | هل الملف موجود؟ |

أوضاع الفتح: `"r"` قراءة (الافتراضي)، و`"w"` كتابة جديدة، و`"a"` إضافة. والملف يُنشأ في **مجلد المشروع**، لأن الـ IDE تشغل البرنامج من هناك.

## مثال: ملف CSV صغير

```ruby run
File.write("scores.csv", "علي,80\nمنى,95\nخالد,67\n")
total = 0
File.readlines("scores.csv", chomp: true).each do |line|
  name, score = line.split(",")
  total += score.to_i
  puts "#{name.ljust(6)}#{score}"
end
puts "المجموع: #{total}"
File.delete("scores.csv")
```

```text output
علي   80
منى   95
خالد  67
المجموع: 242
```

`name, score = line.split(",")` اسمها **الإسناد المتعدد**: أول عنصر في `name` والثاني في `score`.

## أخطاء شائعة

### قراءة ملف غير موجود

`File.read("x.txt")` لملف غير موجود تثير `Errno::ENOENT` (No such file or directory). افحص أولًا بـ `File.exist?` أو ضعها داخل `begin/rescue`.

### `rescue` بدون نوع يبتلع كل شيء

`rescue => e` وحدها تلتقط معظم الأخطاء، وقد تخفي خطأً برمجيًا حقيقيًا مثل اسم متغير مكتوب خطأ. حدد نوع الخطأ الذي تتوقعه كلما أمكن.

### نسيان إغلاق الملف

`f = File.open("x.txt", "w")` بدون `f.close` قد لا يحفظ البيانات. استخدم الصيغة مع الكتلة `File.open(...) do |f| ... end` فتغلقه Ruby تلقائيًا.

## تمارين

### التمرين 1

اقرأ سطرين، وحاول تحويل كل منهما إلى عدد صحيح بـ `Integer()`. إذا نجح اطبع مجموعهما، وإلا اطبع `إدخال غير صالح`.

```ruby exercise
a = gets.chomp
b = gets.chomp
```

```ruby solution
a = gets.chomp
b = gets.chomp
begin
  puts "المجموع = #{Integer(a) + Integer(b)}"
rescue ArgumentError
  puts "إدخال غير صالح"
end
```

```text input
15
x7
```

```text output
إدخال غير صالح
```

### التمرين 2

اكتب في ملف `list.txt` ثلاث مهام (كل مهمة في سطر)، ثم اقرأه واطبع كل مهمة مسبوقة برقمها، ثم احذف الملف.

```ruby exercise
tasks = ["شراء الخبز", "مذاكرة Ruby", "الاتصال بأمي"]
```

```ruby solution
tasks = ["شراء الخبز", "مذاكرة Ruby", "الاتصال بأمي"]
File.write("list.txt", tasks.join("\n") + "\n")
File.readlines("list.txt", chomp: true).each_with_index do |t, i|
  puts "#{i + 1}) #{t}"
end
File.delete("list.txt")
```

```text output
1) شراء الخبز
2) مذاكرة Ruby
3) الاتصال بأمي
```

## اختبر نفسك

```quiz
{"question": "متى يُنفذ الجزء ensure؟", "choices": ["عند حدوث خطأ فقط", "عند عدم حدوث خطأ فقط", "دائمًا", "أبدًا"], "answer": 2, "explanation": "ensure يُنفذ دائمًا سواء حدث خطأ أم لا."}
```

```quiz
{"question": "ما الفرق بين \"abc\".to_i وInteger(\"abc\")؟", "choices": ["لا فرق", "to_i تعطي 0 وInteger تثير ArgumentError", "Integer تعطي 0 وto_i تثير خطأ", "كلاهما يثير خطأ"], "answer": 1, "explanation": "to_i متسامحة وترجع 0، أما Integer() فصارمة وتثير خطأ يمكن التقاطه."}
```

```quiz
{"question": "أي وضع يضيف إلى آخر الملف دون مسح محتواه؟", "choices": ["\"r\"", "\"w\"", "\"a\"", "\"x\""], "answer": 2, "explanation": "الوضع \"a\" (append) يضيف في آخر الملف."}
```

## الخلاصة

- `begin ... rescue Type => e ... else ... ensure ... end` لمعالجة الأخطاء.
- `raise Type, "رسالة"` لإثارة خطأ، و`retry` لإعادة المحاولة.
- `File.write` و`File.read` و`File.readlines` و`File.open(path, "a") { }` للتعامل مع الملفات.
- استخدم `Integer()` و`Float()` لاكتشاف الإدخال غير الصالح.
