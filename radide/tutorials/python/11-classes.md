# الدرس 11: الأصناف والكائنات (Classes)

حتى الآن كنا نخزن البيانات في متغيرات وقوائم وقواميس، ونكتب الدوال منفصلة عنها. **البرمجة كائنية التوجه** (Object-Oriented Programming) تجمع البيانات والدوال التي تعمل عليها في وحدة واحدة اسمها **الكائن** (object).

> **تشبيه:** **الصنف** (class) مثل **التصميم الهندسي** لسيارة، و**الكائن** (object) هو السيارة الحقيقية المصنوعة من هذا التصميم. من تصميم واحد تصنع سيارات كثيرة، لكل واحدة لونها وعدد كيلومتراتها، وكلها تستطيع أن «تسير» و«تتوقف».

## أول صنف

```python run
class Dog:
    def __init__(self, name, age):
        self.name = name        # خاصية (attribute)
        self.age = age

    def bark(self):             # دالة تابعة (method)
        print(f"{self.name} يقول: هو هو!")

rex = Dog("Rex", 3)
max_dog = Dog("Max", 5)
rex.bark()
max_dog.bark()
print(rex.age, max_dog.age)
```

```text output
Rex يقول: هو هو!
Max يقول: هو هو!
3 5
```

لنفهم كل جزء:

- `class Dog:` تعرّف صنفًا اسمه `Dog`. العادة أن يبدأ اسم الصنف بحرف كبير.
- `__init__` دالة خاصة اسمها **المُنشئ** (constructor)، تُستدعى تلقائيًا عند إنشاء كائن جديد بـ `Dog("Rex", 3)`.
- `self` تعني «هذا الكائن نفسه». بها يحفظ كل كائن بياناته الخاصة: `self.name = name`.
- `bark` **دالة تابعة** (method): دالة داخل الصنف، وأول معامل فيها دائمًا `self`.
- نصل للخصائص والدوال بالنقطة: `rex.age` و`rex.bark()`.

## مثال: حساب بنكي

```python run
class BankAccount:
    def __init__(self, owner, balance=0):
        self.owner = owner
        self.balance = balance

    def deposit(self, amount):
        self.balance += amount
        print(f"إيداع {amount}، الرصيد الآن {self.balance}")

    def withdraw(self, amount):
        if amount > self.balance:
            print("الرصيد غير كافٍ")
            return False
        self.balance -= amount
        print(f"سحب {amount}، الرصيد الآن {self.balance}")
        return True

acc = BankAccount("Amira", 500)
acc.deposit(200)
acc.withdraw(1000)
acc.withdraw(300)
print(acc.owner, acc.balance)
```

```text output
إيداع 200، الرصيد الآن 700
الرصيد غير كافٍ
سحب 300، الرصيد الآن 400
Amira 400
```

لاحظ كيف أصبحت **البيانات** (`balance`) و**العمليات** عليها (`deposit` و`withdraw`) في مكان واحد. هذا يسمى **التغليف** (encapsulation).

## طباعة الكائن بشكل جميل: `__str__`

```python run
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return f"({self.x}, {self.y})"

    def distance_to_origin(self):
        return (self.x ** 2 + self.y ** 2) ** 0.5

p = Point(3, 4)
print(p)
print(p.distance_to_origin())
```

```text output
(3, 4)
5.0
```

بدون `__str__` كانت `print(p)` ستطبع شيئًا مثل `<__main__.Point object at 0x...>`.

## خصائص الصنف وخصائص الكائن

```python run
class Student:
    school = "RAD School"        # خاصية مشتركة بين كل الكائنات
    count = 0

    def __init__(self, name):
        self.name = name         # خاصية خاصة بكل كائن
        Student.count += 1

a = Student("Ali")
b = Student("Laila")
print(a.school, b.school)
print("عدد الطلاب:", Student.count)
```

```text output
RAD School RAD School
عدد الطلاب: 2
```

## الوراثة (Inheritance)

يمكن لصنف أن **يرث** كل خصائص ودوال صنف آخر، ثم يضيف أو يغيّر ما يريد:

```python run
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return "..."

    def introduce(self):
        print(f"أنا {self.name} وأقول {self.speak()}")

class Cat(Animal):
    def speak(self):
        return "مياو"

class Cow(Animal):
    def speak(self):
        return "موووو"

for animal in [Cat("Mishmish"), Cow("Bakra"), Animal("Unknown")]:
    animal.introduce()
```

```text output
أنا Mishmish وأقول مياو
أنا Bakra وأقول موووو
أنا Unknown وأقول ...
```

- `class Cat(Animal):` تعني أن `Cat` يرث من `Animal`.
- `Cat` أعاد تعريف `speak` فقط، وورث `__init__` و`introduce` كما هي.
- نفس الاستدعاء `animal.introduce()` أعطى نتائج مختلفة حسب نوع الكائن. هذا اسمه **تعدد الأشكال** (polymorphism).

### `super()`: استدعاء دالة الأب

```python run
class Employee:
    def __init__(self, name, salary):
        self.name = name
        self.salary = salary

    def info(self):
        return f"{self.name}: {self.salary}"

class Manager(Employee):
    def __init__(self, name, salary, team):
        super().__init__(name, salary)    # المُنشئ الأصلي يتولى الاسم والراتب
        self.team = team

    def info(self):
        return super().info() + f" (يدير {len(self.team)} موظفين)"

m = Manager("Hala", 20000, ["Ali", "Omar", "Sara"])
print(m.info())
print(isinstance(m, Employee))
```

```text output
Hala: 20000 (يدير 3 موظفين)
True
```

## الخاصية المحسوبة: `@property`

```python run
class Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    @property
    def area(self):
        return self.width * self.height

r = Rectangle(4, 6)
print(r.area)       # بدون أقواس، كأنها خاصية عادية
r.width = 10
print(r.area)
```

```text output
24
60
```

## `dataclass`: أصناف البيانات بسرعة

للأصناف التي تحمل بيانات فقط، توفر Python اختصارًا يكتب `__init__` و`__repr__` عنك:

```python run
from dataclasses import dataclass

@dataclass
class Product:
    name: str
    price: float
    qty: int = 1

    def total(self):
        return self.price * self.qty

p = Product("Pen", 7.5, 4)
print(p)
print(p.total())
```

```text output
Product(name='Pen', price=7.5, qty=4)
30.0
```

## أخطاء شائعة

### نسيان `self`

```python run
class Counter:
    def __init__(self):
        self.value = 0

    def add():                 # نسينا self
        self.value += 1

c = Counter()
c.add()
```

```text output
Traceback (most recent call last):
  File "main.py", line 9, in <module>
    c.add()
TypeError: Counter.add() takes 0 positional arguments but 1 was given
```

Python تمرر الكائن تلقائيًا كأول وسيط، فإذا لم يوجد `self` في التعريف يحدث هذا الخطأ.

### نسيان `self.` قبل الخاصية

كتابة `value += 1` بدل `self.value += 1` داخل الدالة تعني متغيرًا محليًا غير موجود، فيحدث `UnboundLocalError` أو `NameError`.

## تمارين

### التمرين 1

أنشئ صنف `Circle` بمُنشئ يأخذ نصف القطر `radius`، ودالة `area` ترجع المساحة (`3.14 × r × r`). اطبع مساحة دائرة نصف قطرها `5`.

```python exercise
class Circle:
    pass

c = Circle(5)
```

```python solution
class Circle:
    def __init__(self, radius):
        self.radius = radius

    def area(self):
        return 3.14 * self.radius * self.radius

c = Circle(5)
print(c.area())
```

```text output
78.5
```

### التمرين 2

أنشئ صنف `ShoppingCart` فيه قائمة `items`، ودالة `add(name, price)`، ودالة `total()`. أضف منتجين واطبع الإجمالي.

```python exercise
class ShoppingCart:
    pass

cart = ShoppingCart()
cart.add("كتاب", 120)
cart.add("قلم", 15)
```

```python solution
class ShoppingCart:
    def __init__(self):
        self.items = []

    def add(self, name, price):
        self.items.append((name, price))

    def total(self):
        return sum(price for name, price in self.items)

cart = ShoppingCart()
cart.add("كتاب", 120)
cart.add("قلم", 15)
print("الإجمالي:", cart.total())
```

```text output
الإجمالي: 135
```

### التمرين 3

أنشئ صنف `Shape` فيه دالة `area` ترجع `0`، وصنفين يرثان منه: `Square(side)` و`Triangle(base, height)`. اطبع مساحة مربع ضلعه `4` ومثلث قاعدته `6` وارتفاعه `3`.

```python exercise
class Shape:
    def area(self):
        return 0
```

```python solution
class Shape:
    def area(self):
        return 0

class Square(Shape):
    def __init__(self, side):
        self.side = side

    def area(self):
        return self.side * self.side

class Triangle(Shape):
    def __init__(self, base, height):
        self.base = base
        self.height = height

    def area(self):
        return self.base * self.height / 2

for shape in [Square(4), Triangle(6, 3)]:
    print(shape.area())
```

```text output
16
9.0
```

## اختبر نفسك

```quiz
{"question": "متى تُستدعى الدالة __init__؟", "choices": ["عند طباعة الكائن", "عند إنشاء كائن جديد من الصنف", "عند حذف الكائن", "يجب استدعاؤها يدويًا دائمًا"], "answer": 1, "explanation": "__init__ هي المُنشئ، وتُستدعى تلقائيًا عند كتابة Dog(...)."}
```

```quiz
{"question": "ماذا تمثل self داخل الدالة التابعة؟", "choices": ["الصنف نفسه", "الكائن الذي استُدعيت عليه الدالة", "أول خاصية", "البرنامج كله"], "answer": 1, "explanation": "self هي الكائن الحالي، وبها نصل إلى خصائصه."}
```

```quiz
{"question": "في class Cat(Animal):، ما علاقة Cat بـ Animal؟", "choices": ["Animal يرث من Cat", "Cat يرث من Animal", "لا علاقة", "Cat نسخة من Animal"], "answer": 1, "explanation": "الصنف بين القوسين هو الأب، وCat يرث كل خصائصه ودواله."}
```

## الخلاصة

- `class` يعرّف تصميمًا، والكائن نسخة منه، و`__init__` المُنشئ، و`self` الكائن الحالي.
- الدوال التابعة تعمل على بيانات الكائن، و`__str__` تحدد شكل طباعته.
- الوراثة `class B(A):` و`super()` و`@property` و`@dataclass` أدوات تنظيم قوية.
