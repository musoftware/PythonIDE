# الدرس 7: الأصناف والكائنات والوحدات

قلنا إن كل شيء في Ruby **كائن** (object): الرقم والنص والمصفوفة. اليوم نصنع كائناتنا الخاصة. الصنف (class) هو **القالب**، والكائن هو **نسخة** مصنوعة من القالب.

> **تشبيه:** الصنف مثل **مخطط المنزل** عند المهندس: فيه عدد الغرف ومكان الأبواب. والكائنات هي **المنازل الحقيقية** المبنية من المخطط، ولكل منزل لونه وأصحابه.

## أول صنف

```ruby run
class Student
  def initialize(name, grade)
    @name = name
    @grade = grade
  end

  def info
    "#{@name}: #{@grade}"
  end

  def passed?
    @grade >= 50
  end
end

s1 = Student.new("سارة", 92)
s2 = Student.new("خالد", 41)
puts s1.info
puts s2.info
puts s1.passed?
puts s2.passed?
```

```text output
سارة: 92
خالد: 41
true
false
```

- اسم الصنف يبدأ بحرف كبير: `Student`.
- `Student.new(...)` تنشئ كائنًا جديدًا، وتستدعي تلقائيًا الدالة الخاصة `initialize` (**المُنشئ**، constructor).
- المتغيرات التي تبدأ بـ `@` مثل `@name` هي **متغيرات الكائن** (instance variables): كل كائن له نسخته منها، وتبقى طوال عمر الكائن.

## الخصائص: `attr_reader` و`attr_accessor`

متغيرات `@` مخفية عن الخارج. لكي نقرأها أو نغيرها من خارج الصنف نضيف **خصائص**:

```ruby run
class Product
  attr_reader :name          # قراءة فقط
  attr_accessor :price       # قراءة وكتابة

  def initialize(name, price)
    @name = name
    @price = price
  end

  def to_s
    "#{@name} - #{@price} جنيه"
  end
end

item = Product.new("قلم", 5)
puts item.name
item.price = 7
puts item.price
puts item
```

```text output
قلم
7
قلم - 7 جنيه
```

| الكلمة | تنشئ |
|---|---|
| `attr_reader :x` | دالة قراءة `obj.x` |
| `attr_writer :x` | دالة كتابة `obj.x = v` |
| `attr_accessor :x` | الاثنتين معًا |

والدالة `to_s` يستدعيها `puts` والاستيفاء تلقائيًا لتحويل الكائن إلى نص.

## الوراثة (Inheritance)

صنف جديد يأخذ كل ما في صنف آخر ويضيف عليه أو يغيّر فيه:

```ruby run
class Animal
  attr_reader :name

  def initialize(name)
    @name = name
  end

  def speak
    "..."
  end

  def introduce
    "أنا #{@name} وأقول: #{speak}"
  end
end

class Cat < Animal
  def speak
    "مياو"
  end
end

class Dog < Animal
  def initialize(name, breed)
    super(name)
    @breed = breed
  end

  def speak
    "هاو"
  end
end

[Cat.new("مشمش"), Dog.new("روكي", "جيرمن")].each { |a| puts a.introduce }
puts Cat.ancestors.first(2).inspect
```

```text output
أنا مشمش وأقول: مياو
أنا روكي وأقول: هاو
[Cat, Animal]
```

- `class Cat < Animal` تعني «Cat يرث من Animal».
- `super(name)` تستدعي نفس الدالة في الصنف الأب.
- `introduce` معرّفة في `Animal` لكنها تستدعي `speak` الخاصة بكل حيوان. هذا هو **تعدد الأشكال** (polymorphism).

## دوال الصنف والمتغيرات المشتركة

```ruby run
class Counter
  @@count = 0                 # متغير مشترك بين كل الكائنات

  def initialize
    @@count += 1
  end

  def self.count              # دالة على الصنف نفسه
    @@count
  end
end

3.times { Counter.new }
puts Counter.count
```

```text output
3
```

## الوحدات (Modules)

**الوحدة** (module) مجموعة دوال وثوابت لا يُنشأ منها كائنات. نستخدمها لشيئين:

1. **تجميع** دوال مترابطة تحت اسم واحد (مثل `Math`).
2. **الخلط** (mixin): إضافة دوال جاهزة لأي صنف بالكلمة `include`.

```ruby run
module Geometry
  PI = 3.14159

  def self.circle_area(r)
    (PI * r * r).round(2)
  end
end

module Greeter
  def hello
    "مرحبًا، أنا #{name}"
  end
end

class Teacher
  include Greeter
  attr_reader :name

  def initialize(name)
    @name = name
  end
end

puts Geometry.circle_area(3)
puts Geometry::PI
puts Teacher.new("أ. منى").hello
puts Math.sqrt(16)
```

```text output
28.27
3.14159
مرحبًا، أنا أ. منى
4.0
```

## أخطاء شائعة

### نسيان `@`

إذا كتبت `name = name` داخل `initialize` بدل `@name = name`، فلن يُحفظ شيء في الكائن، لأن `name` بدون `@` متغير محلي يختفي بعد انتهاء الدالة.

### قراءة متغير بدون خاصية

<!-- compile-error -->
```ruby
class Box
  def initialize(size)
    @size = size
  end
end
puts Box.new(3).size
```

الخطأ: `undefined method 'size'`. أضف `attr_reader :size` إلى الصنف.

### اسم الصنف بحرف صغير

`class student` خطأ: `class/module name must be CONSTANT` أي «اسم الصنف يجب أن يكون ثابتًا (يبدأ بحرف كبير)».

## تمارين

### التمرين 1

اكتب صنف `Rectangle` له `width` و`height`، ودالتان `area` و`perimeter`. ثم أنشئ مستطيلًا 4 × 6 واطبع مساحته ومحيطه.

```ruby exercise
class Rectangle
  # ...
end

r = Rectangle.new(4, 6)
puts "المساحة: #{r.area}"
puts "المحيط: #{r.perimeter}"
```

```ruby solution
class Rectangle
  attr_reader :width, :height

  def initialize(width, height)
    @width = width
    @height = height
  end

  def area
    width * height
  end

  def perimeter
    2 * (width + height)
  end
end

r = Rectangle.new(4, 6)
puts "المساحة: #{r.area}"
puts "المحيط: #{r.perimeter}"
```

```text output
المساحة: 24
المحيط: 20
```

### التمرين 2

اكتب صنف `BankAccount` فيه `balance` (قراءة فقط) ودالتان `deposit(amount)` و`withdraw(amount)`. السحب يرفض إذا كان المبلغ أكبر من الرصيد ويطبع `الرصيد لا يكفي`.

```ruby exercise
class BankAccount
  attr_reader :balance
  # ...
end

acc = BankAccount.new(100)
acc.deposit(50)
acc.withdraw(500)
acc.withdraw(30)
puts "الرصيد: #{acc.balance}"
```

```ruby solution
class BankAccount
  attr_reader :balance

  def initialize(balance = 0)
    @balance = balance
  end

  def deposit(amount)
    @balance += amount
  end

  def withdraw(amount)
    if amount > @balance
      puts "الرصيد لا يكفي"
    else
      @balance -= amount
    end
  end
end

acc = BankAccount.new(100)
acc.deposit(50)
acc.withdraw(500)
acc.withdraw(30)
puts "الرصيد: #{acc.balance}"
```

```text output
الرصيد لا يكفي
الرصيد: 120
```

## اختبر نفسك

```quiz
{"question": "ما اسم الدالة التي تُستدعى تلقائيًا عند Student.new؟", "choices": ["new", "create", "initialize", "constructor"], "answer": 2, "explanation": "new تستدعي initialize، وهي المُنشئ في Ruby."}
```

```quiz
{"question": "ماذا تعني @name داخل الصنف؟", "choices": ["متغير محلي", "ثابت", "متغير خاص بالكائن يبقى طوال عمره", "متغير عام للبرنامج كله"], "answer": 2, "explanation": "المتغيرات التي تبدأ بـ @ متغيرات كائن (instance variables)."}
```

```quiz
{"question": "ما الذي تفعله include Greeter داخل صنف؟", "choices": ["تحذف الصنف", "تضيف دوال الوحدة Greeter إلى كائنات الصنف", "تنشئ كائنًا", "تستدعي Greeter.new"], "answer": 1, "explanation": "include تخلط دوال الوحدة في الصنف (mixin)."}
```

## الخلاصة

- `class Name ... end` قالب، و`Name.new` تنشئ كائنًا وتستدعي `initialize`.
- `@var` متغير كائن، و`attr_reader` / `attr_accessor` تجعله خاصية.
- `class B < A` وراثة، و`super` تستدعي دالة الأب.
- `module` لتجميع الدوال (`Math.sqrt`) أو لخلطها في الأصناف بـ `include`.
