# الدرس 10: الأصناف والكائنات (Classes)

Java لغة **كائنية التوجه** (Object-Oriented) في أساسها: كل شيء فيها يدور حول الأصناف والكائنات. الصنف يجمع **البيانات** (الحقول) و**السلوك** (الدوال) في وحدة واحدة.

> **تشبيه:** **الصنف** مثل **المخطط الهندسي** لبيت، و**الكائن** هو البيت الحقيقي المبني منه. من مخطط واحد نبني بيوتًا كثيرة، لكل بيت لونه وسكانه.

## أول صنف

في Java يمكن وضع أكثر من صنف في ملف واحد، بشرط أن يكون صنف **واحد فقط** `public` ويحمل اسم الملف:

```java run
public class Main {
    public static void main(String[] args) {
        Car car1 = new Car();
        car1.brand = "تويوتا";
        car1.year = 2020;

        Car car2 = new Car();
        car2.brand = "كيا";
        car2.year = 2024;

        car1.describe();
        car2.describe();
    }
}

class Car {
    String brand;      // حقل (field)
    int year;

    void describe() {  // دالة (method) - ليست static: تعمل على كائن معين
        System.out.println("سيارة " + brand + " موديل " + year);
    }
}
```

```text output
سيارة تويوتا موديل 2020
سيارة كيا موديل 2024
```

- `new Car()` ينشئ **كائنًا** (object) جديدًا.
- `car1.brand` يصل إلى حقل الكائن بالنقطة.
- الدالة `describe()` بلا `static`، فهي **دالة كائن** (instance method) تستخدم حقول الكائن الذي استُدعيت عليه.

## المُنشئ (Constructor) و`this`

```java run
public class Main {
    public static void main(String[] args) {
        Student s = new Student("نور", 3);
        s.print();
        Student t = new Student("عمر");
        t.print();
    }
}

class Student {
    String name;
    int level;

    Student(String name, int level) {
        this.name = name;      // this.name = حقل الكائن، name = المعامل
        this.level = level;
    }

    Student(String name) {
        this(name, 1);         // يستدعي المُنشئ الآخر
    }

    void print() {
        System.out.println(name + " في المستوى " + level);
    }
}
```

```text output
نور في المستوى 3
عمر في المستوى 1
```

المُنشئ اسمه اسم الصنف وبلا نوع إرجاع، ويعمل تلقائيًا عند `new`. و`this` تعني «هذا الكائن».

## التغليف: `private` مع getters وsetters

```java run
public class Main {
    public static void main(String[] args) {
        BankAccount acc = new BankAccount("هالة");
        acc.deposit(500);
        acc.withdraw(200);
        acc.withdraw(1000);
        System.out.println("رصيد " + acc.getOwner() + ": " + acc.getBalance());
    }
}

class BankAccount {
    private final String owner;
    private double balance;

    BankAccount(String owner) {
        this.owner = owner;
    }

    public String getOwner() {
        return owner;
    }

    public double getBalance() {
        return balance;
    }

    public void deposit(double amount) {
        if (amount > 0) {
            balance += amount;
        }
    }

    public void withdraw(double amount) {
        if (amount > balance) {
            System.out.println("الرصيد لا يكفي");
        } else {
            balance -= amount;
        }
    }
}
```

```text output
الرصيد لا يكفي
رصيد هالة: 300.0
```

- `private` تمنع الوصول من خارج الصنف، فلا يستطيع أحد كتابة `acc.balance = -5`.
- **getter** (`getBalance`) للقراءة، و**setter** (`setX`) للكتابة مع الفحص. هذا هو العُرف في Java.

| معدّل الوصول | من يراه؟ |
|---|---|
| `public` | الجميع |
| `private` | الصنف نفسه فقط |
| `protected` | الصنف والأصناف المشتقة والحزمة |
| (بدون كلمة) | أصناف نفس الحزمة (package) |

## `toString()`

```java run
public class Main {
    public static void main(String[] args) {
        Point p = new Point(3, 4);
        System.out.println(p);
        System.out.println("النقطة هي " + p);
    }
}

class Point {
    private final int x, y;

    Point(int x, int y) {
        this.x = x;
        this.y = y;
    }

    @Override
    public String toString() {
        return "(" + x + ", " + y + ")";
    }
}
```

```text output
(3, 4)
النقطة هي (3, 4)
```

`@Override` **علامة توضيحية** (annotation) تقول للمترجم: «أنا أعيد تعريف دالة موروثة». إذا أخطأت في اسمها ينبهك المترجم.

## الأعضاء الثابتة: `static`

```java run
public class Main {
    public static void main(String[] args) {
        new Visitor("أ");
        new Visitor("ب");
        new Visitor("ج");
        System.out.println("عدد الزوار: " + Visitor.count);
        System.out.println(MathUtil.square(7));
    }
}

class Visitor {
    static int count = 0;    // مشترك بين كل الكائنات
    String name;

    Visitor(String name) {
        this.name = name;
        count++;
    }
}

class MathUtil {
    static int square(int x) {
        return x * x;
    }
}
```

```text output
عدد الزوار: 3
49
```

## السجلات: `record` (Java 16+)

```java run
public class Main {
    record Person(String name, int age) { }

    public static void main(String[] args) {
        Person a = new Person("Ali", 30);
        Person b = new Person("Ali", 30);
        System.out.println(a);
        System.out.println(a.name() + " " + a.age());
        System.out.println(a.equals(b));
    }
}
```

```text output
Person[name=Ali, age=30]
Ali 30
true
```

`record` يعطيك المُنشئ والحقول الثابتة ودوال القراءة (`name()`) و`toString` و`equals` في سطر واحد.

## قائمة من الكائنات

```java run
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

public class Main {
    record Book(String title, String author, int copies) { }

    public static void main(String[] args) {
        List<Book> books = new ArrayList<>();
        books.add(new Book("Dune", "Herbert", 1));
        books.add(new Book("Emma", "Austen", 2));
        books.add(new Book("Bambi", "Salten", 5));
        books.sort(Comparator.comparing(Book::title));
        int total = 0;
        for (Book b : books) {
            System.out.println(b.title() + " - " + b.author() + " (" + b.copies() + ")");
            total += b.copies();
        }
        System.out.println("مجموع النسخ: " + total);
    }
}
```

```text output
Bambi - Salten (5)
Dune - Herbert (1)
Emma - Austen (2)
مجموع النسخ: 8
```

`Book::title` **مرجع دالة** (method reference): اختصار للامدا `b -> b.title()`.

## أخطاء شائعة

### `NullPointerException`

```java
Car c = null;
c.describe();    // NullPointerException
```

المتغير لا يشير إلى كائن. ابحث عن متغير نسيت أن تنشئه بـ `new`.

### الوصول إلى عضو `private`

`acc.balance = 1000000;` يعطي `balance has private access in BankAccount`. وهذا هو المطلوب.

### كتابة نوع إرجاع للمُنشئ

`void Student(String name)` دالة عادية وليست مُنشئًا، فلن تعمل عند `new`.

## تمارين

### التمرين 1

أكمل الصنف `Rectangle` بحقلين خاصين ومُنشئ ودالتين `area()` و`perimeter()`.

```java exercise
public class Main {
    public static void main(String[] args) {
        Rectangle r = new Rectangle(5, 3);
        System.out.println("المساحة " + r.area() + " والمحيط " + r.perimeter());
    }
}

class Rectangle {
    Rectangle(double w, double h) { }
    double area() { return 0; }
    double perimeter() { return 0; }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        Rectangle r = new Rectangle(5, 3);
        System.out.println("المساحة " + r.area() + " والمحيط " + r.perimeter());
    }
}

class Rectangle {
    private final double width, height;

    Rectangle(double w, double h) {
        width = w;
        height = h;
    }

    double area() {
        return width * height;
    }

    double perimeter() {
        return 2 * (width + height);
    }
}
```

```text output
المساحة 15.0 والمحيط 16.0
```

### التمرين 2

صنف `Counter` فيه `increment()` و`reset()` و`getValue()`.

```java exercise
public class Main {
    public static void main(String[] args) {
        Counter c = new Counter();
        c.increment();
        c.increment();
        c.increment();
        System.out.println(c.getValue());
        c.reset();
        System.out.println(c.getValue());
    }
}

class Counter {
    // أكمل هنا
    int getValue() { return 0; }
    void increment() { }
    void reset() { }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        Counter c = new Counter();
        c.increment();
        c.increment();
        c.increment();
        System.out.println(c.getValue());
        c.reset();
        System.out.println(c.getValue());
    }
}

class Counter {
    private int value;

    int getValue() {
        return value;
    }

    void increment() {
        value++;
    }

    void reset() {
        value = 0;
    }
}
```

```text output
3
0
```

### التمرين 3

عرّف `record Employee(String name, double salary)`، واطبع اسم صاحب أعلى راتب من قائمة من ثلاثة.

```java exercise
import java.util.List;

public class Main {
    // record Employee(...)

    public static void main(String[] args) {
        // الأعلى راتبًا: رنا
    }
}
```

```java solution
import java.util.List;

public class Main {
    record Employee(String name, double salary) { }

    public static void main(String[] args) {
        List<Employee> staff = List.of(new Employee("سامي", 7000), new Employee("رنا", 9500),
                new Employee("فادي", 6200));
        Employee top = staff.get(0);
        for (Employee e : staff) {
            if (e.salary() > top.salary()) {
                top = e;
            }
        }
        System.out.println("الأعلى راتبًا: " + top.name());
    }
}
```

```text output
الأعلى راتبًا: رنا
```

## اختبر نفسك

```quiz
{"question": "ما الفرق بين دالة static ودالة كائن (بدون static)؟", "choices": ["لا فرق", "static تخص الصنف وتُستدعى باسمه، ودالة الكائن تعمل على كائن معين وحقوله", "دالة الكائن أسرع", "static لا ترجع قيمة"], "answer": 1, "explanation": "MathUtil.square(7) دالة صنف، أما car1.describe() فتستخدم حقول car1."}
```

```quiz
{"question": "ماذا تعني this.name = name في المُنشئ؟", "choices": ["خطأ", "ضع قيمة المعامل name في حقل الكائن name", "اطبع الاسم", "قارن الاسمين"], "answer": 1, "explanation": "this.name هو الحقل، وname وحدها المعامل."}
```

```quiz
{"question": "ما فائدة @Override؟", "choices": ["تسريع الدالة", "تجعل المترجم يتأكد أنك تعيد تعريف دالة موروثة فعلًا", "تجعل الدالة خاصة", "إلزامية في كل دالة"], "answer": 1, "explanation": "إذا أخطأت في الاسم أو المعاملات ينبهك المترجم بدل أن تُنشأ دالة جديدة بالخطأ."}
```

## الخلاصة

- الصنف مخطط، والكائن نسخة بـ `new`، والمُنشئ يجهزه، و`this` هو الكائن الحالي.
- التغليف: حقول `private` مع getters وsetters.
- `@Override public String toString()` لطباعة الكائن، و`static` للأعضاء المشتركة.
- `record` للبيانات البسيطة، و`Comparator.comparing` للترتيب.
