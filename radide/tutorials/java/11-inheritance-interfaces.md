# الدرس 11: الوراثة والواجهات (Interfaces)

في الدرس السابق صنعنا أصنافًا مستقلة. اليوم نتعلم كيف **نبني صنفًا على صنف آخر** فنعيد استخدام الكود بدل نسخه، وكيف نكتب **عقدًا** تلتزم به أصناف مختلفة.

> **تشبيه:** **الوراثة** مثل العائلة: الابن يرث من أبيه لون العينين وطريقة الكلام، ثم يضيف صفاته الخاصة. أما **الواجهة** فمثل **رخصة القيادة**: لا يهم من أنت (طبيب أو طالب)، المهم أنك تستطيع القيادة لأنك اجتزت نفس الاختبار.

## الوراثة بـ `extends`

```java run
public class Main {
    public static void main(String[] args) {
        Dog d = new Dog("ريكس");
        d.eat();       // موروثة من Animal
        d.bark();      // خاصة بـ Dog
    }
}

class Animal {
    protected String name;

    Animal(String name) {
        this.name = name;
    }

    void eat() {
        System.out.println(name + " يأكل");
    }
}

class Dog extends Animal {
    Dog(String name) {
        super(name);       // يستدعي مُنشئ الصنف الأب
    }

    void bark() {
        System.out.println(name + " ينبح: هو هو!");
    }
}
```

```text output
ريكس يأكل
ريكس ينبح: هو هو!
```

- `class Dog extends Animal` تعني: `Dog` **صنف مشتق** (subclass) من `Animal` وهو **الصنف الأب** (superclass).
- `super(name)` يستدعي مُنشئ الأب، ويجب أن يكون أول سطر في المُنشئ.
- `protected` تسمح للأصناف المشتقة برؤية الحقل `name`.
- Java تسمح بأب **واحد فقط** لكل صنف.

## إعادة التعريف (Override) وتعدد الأشكال

```java run
import java.util.List;

public class Main {
    public static void main(String[] args) {
        List<Shape> shapes = List.of(new Circle(1), new Square(2), new Circle(2));
        double total = 0;
        for (Shape s : shapes) {
            System.out.println(s.name() + ": " + Math.round(s.area() * 100) / 100.0);
            total += s.area();
        }
        System.out.println("المجموع: " + Math.round(total * 100) / 100.0);
    }
}

class Shape {
    String name() {
        return "شكل";
    }

    double area() {
        return 0;
    }
}

class Circle extends Shape {
    private final double r;

    Circle(double r) {
        this.r = r;
    }

    @Override
    String name() {
        return "دائرة";
    }

    @Override
    double area() {
        return Math.PI * r * r;
    }
}

class Square extends Shape {
    private final double side;

    Square(double side) {
        this.side = side;
    }

    @Override
    String name() {
        return "مربع";
    }

    @Override
    double area() {
        return side * side;
    }
}
```

```text output
دائرة: 3.14
مربع: 4.0
دائرة: 12.57
المجموع: 19.71
```

المتغير `s` نوعه `Shape`، لكن عند استدعاء `s.area()` تعمل دالة **الكائن الحقيقي** (`Circle` أو `Square`). هذه هي **تعددية الأشكال** (polymorphism): كود واحد يتعامل مع أنواع كثيرة.

## الأصناف المجردة `abstract`

الصنف `Shape` السابق لا معنى لإنشاء كائن منه مباشرة. نجعله **مجردًا** (abstract) ونجبر كل صنف مشتق على كتابة دواله:

```java run
public class Main {
    public static void main(String[] args) {
        Employee[] staff = { new Manager("هدى", 9000), new Intern("يوسف") };
        for (Employee e : staff) {
            System.out.println(e.name + " يتقاضى " + e.salary());
        }
    }
}

abstract class Employee {
    final String name;

    Employee(String name) {
        this.name = name;
    }

    abstract double salary();     // بلا جسم: كل صنف مشتق يكتبها
}

class Manager extends Employee {
    private final double base;

    Manager(String name, double base) {
        super(name);
        this.base = base;
    }

    @Override
    double salary() {
        return base * 1.2;
    }
}

class Intern extends Employee {
    Intern(String name) {
        super(name);
    }

    @Override
    double salary() {
        return 2500;
    }
}
```

```text output
هدى يتقاضى 10800.0
يوسف يتقاضى 2500.0
```

`new Employee("x")` الآن خطأ ترجمة: `Employee is abstract; cannot be instantiated`.

## الواجهات `interface`

الواجهة **قائمة دوال** بلا تنفيذ (عقد). أي صنف يكتب `implements` يَعِد بتنفيذها كلها. والصنف يستطيع تنفيذ **أكثر من واجهة**:

```java run
public class Main {
    public static void main(String[] args) {
        Printable[] things = { new Invoice(350), new Report("المبيعات") };
        for (Printable p : things) {
            p.print();
        }
        Invoice inv = new Invoice(100);
        inv.save();
    }
}

interface Printable {
    void print();
}

interface Savable {
    void save();

    default void saveTwice() {      // دالة افتراضية لها تنفيذ داخل الواجهة
        save();
        save();
    }
}

class Invoice implements Printable, Savable {
    private final double amount;

    Invoice(double amount) {
        this.amount = amount;
    }

    @Override
    public void print() {
        System.out.println("فاتورة بمبلغ " + amount);
    }

    @Override
    public void save() {
        System.out.println("تم حفظ الفاتورة");
    }
}

class Report implements Printable {
    private final String title;

    Report(String title) {
        this.title = title;
    }

    @Override
    public void print() {
        System.out.println("تقرير: " + title);
    }
}
```

```text output
فاتورة بمبلغ 350.0
تقرير: المبيعات
تم حفظ الفاتورة
```

لاحظ أن دوال الواجهة `public` دائمًا، فيجب أن تكتب `public` عند تنفيذها في الصنف.

| | صنف مجرد `abstract class` | واجهة `interface` |
|---|---|---|
| عدد ما يرثه الصنف | واحد فقط (`extends`) | أي عدد (`implements`) |
| حقول عادية | نعم | لا (ثوابت فقط) |
| مُنشئ | نعم | لا |
| متى أستخدمه؟ | أنواع من نفس العائلة تشترك في كود | قدرة مشتركة بين أصناف مختلفة |

## واجهات Java الجاهزة: `Comparable`

كثير من مكتبات Java تعمل مع واجهات جاهزة. مثلًا `Collections.sort` ترتب أي كائنات تنفذ `Comparable`:

```java run
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class Main {
    public static void main(String[] args) {
        List<Player> players = new ArrayList<>();
        players.add(new Player("Omar", 120));
        players.add(new Player("Laila", 300));
        players.add(new Player("Sami", 80));
        Collections.sort(players);
        for (Player p : players) {
            System.out.println(p.name + " " + p.score);
        }
    }
}

class Player implements Comparable<Player> {
    final String name;
    final int score;

    Player(String name, int score) {
        this.name = name;
        this.score = score;
    }

    @Override
    public int compareTo(Player other) {
        return other.score - this.score;     // الأعلى أولًا
    }
}
```

```text output
Laila 300
Omar 120
Sami 80
```

## `instanceof` لمعرفة النوع الحقيقي

```java run
public class Main {
    public static void main(String[] args) {
        Object[] items = { "سلام", 42, 3.5, new int[] {1, 2} };
        for (Object o : items) {
            if (o instanceof String s) {
                System.out.println("نص طوله " + s.length());
            } else if (o instanceof Integer n) {
                System.out.println("عدد صحيح ضعفه " + n * 2);
            } else {
                System.out.println("نوع آخر: " + o.getClass().getSimpleName());
            }
        }
    }
}
```

```text output
نص طوله 4
عدد صحيح ضعفه 84
نوع آخر: Double
نوع آخر: int[]
```

`o instanceof String s` يفحص النوع، وإذا صح يضع الكائن في متغير جديد `s` من النوع `String` مباشرة.

## أخطاء شائعة

### نسيان `super(...)`

إذا كان للأب مُنشئ بمعاملات فقط، فيجب أن يستدعيه الابن: وإلا يظهر الخطأ `constructor Animal in class Animal cannot be applied to given types`.

### نسيان `public` عند تنفيذ دالة واجهة

`void print() { ... }` داخل `Invoice` يعطي `attempting to assign weaker access privileges; was public`. اكتب `public void print()`.

### عدم تنفيذ كل دوال الواجهة

`Report is not abstract and does not override abstract method save() in Savable`: نفّذ كل الدوال أو اجعل الصنف `abstract`.

## تمارين

### التمرين 1

أكمل الصنف `Cat` المشتق من `Animal` بحيث تعيد الدالة `sound()` النص `مياو`.

```java exercise
public class Main {
    public static void main(String[] args) {
        Animal[] pets = { new Cow(), new Cat() };
        for (Animal a : pets) {
            System.out.println(a.getClass().getSimpleName() + ": " + a.sound());
        }
    }
}

abstract class Animal {
    abstract String sound();
}

class Cow extends Animal {
    @Override
    String sound() {
        return "مووو";
    }
}

class Cat {
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        Animal[] pets = { new Cow(), new Cat() };
        for (Animal a : pets) {
            System.out.println(a.getClass().getSimpleName() + ": " + a.sound());
        }
    }
}

abstract class Animal {
    abstract String sound();
}

class Cow extends Animal {
    @Override
    String sound() {
        return "مووو";
    }
}

class Cat extends Animal {
    @Override
    String sound() {
        return "مياو";
    }
}
```

```text output
Cow: مووو
Cat: مياو
```

### التمرين 2

عرّف واجهة `Discount` فيها الدالة `double apply(double price)`، ونفّذها في صنفين: `HalfPrice` (نصف السعر) و`MinusTen` (ينقص 10). ثم طبّق الاثنين على السعر 100.

```java exercise
public class Main {
    public static void main(String[] args) {
        // Discount[] offers = { new HalfPrice(), new MinusTen() };
        // اطبع ناتج كل عرض على السعر 100
    }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        Discount[] offers = { new HalfPrice(), new MinusTen() };
        for (Discount d : offers) {
            System.out.println(d.apply(100));
        }
    }
}

interface Discount {
    double apply(double price);
}

class HalfPrice implements Discount {
    @Override
    public double apply(double price) {
        return price / 2;
    }
}

class MinusTen implements Discount {
    @Override
    public double apply(double price) {
        return price - 10;
    }
}
```

```text output
50.0
90.0
```

## اختبر نفسك

```quiz
{"question": "كم صنفًا أبًا يمكن أن يرث منه صنف في Java؟", "choices": ["واحد فقط", "اثنان", "أي عدد", "لا يمكن الوراثة"], "answer": 0, "explanation": "Java تسمح بـ extends لصنف واحد، لكن implements لأي عدد من الواجهات."}
```

```quiz
{"question": "ماذا يفعل super(name) داخل مُنشئ الصنف المشتق؟", "choices": ["ينشئ كائنًا جديدًا من الأب", "يستدعي مُنشئ الصنف الأب", "يطبع الاسم", "يحذف الحقل"], "answer": 1, "explanation": "super(...) يستدعي مُنشئ الأب ليجهز الجزء الموروث من الكائن."}
```

```quiz
{"question": "متغير نوعه Shape يشير إلى كائن Circle. أي دالة area() تعمل؟", "choices": ["دالة Shape دائمًا", "دالة Circle", "خطأ ترجمة", "لا تعمل أي دالة"], "answer": 1, "explanation": "هذه تعددية الأشكال: تعمل دالة الكائن الحقيقي."}
```

## الخلاصة

- `extends` للوراثة من صنف واحد، و`super(...)` لمُنشئ الأب، و`@Override` لإعادة التعريف.
- `abstract` لصنف لا يُنشأ منه كائن مباشرة، ودوال بلا جسم تكتبها الأصناف المشتقة.
- `interface` عقد، والصنف ينفذ أي عدد من الواجهات بـ `implements`.
- `instanceof` يفحص النوع الحقيقي للكائن.
