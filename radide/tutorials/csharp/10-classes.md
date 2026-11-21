# الدرس 10: الأصناف والكائنات (Classes)

حتى الآن كانت بياناتنا متفرقة: متغير للاسم، ومتغير للعمر، ومتغير للرصيد. **البرمجة كائنية التوجه** (Object-Oriented Programming) تجمع البيانات والدوال التي تعمل عليها في وحدة واحدة اسمها **الكائن** (object).

> **تشبيه:** **الصنف** (class) مثل **المخطط الهندسي** لبيت: يحدد عدد الغرف ومكان الأبواب. و**الكائن** هو البيت الحقيقي المبني من المخطط. من مخطط واحد نبني بيوتًا كثيرة، لكل بيت لونه وسكانه.

## أول صنف

```csharp run
var car1 = new Car();
car1.Brand = "تويوتا";
car1.Year = 2020;

var car2 = new Car();
car2.Brand = "كيا";
car2.Year = 2024;

car1.Describe();
car2.Describe();

class Car
{
    public string Brand;     // حقل (field)
    public int Year;

    public void Describe()   // دالة (method)
    {
        Console.WriteLine($"سيارة {Brand} موديل {Year}");
    }
}
```

```text output
سيارة تويوتا موديل 2020
سيارة كيا موديل 2024
```

- `class Car { ... }` يعرّف الصنف. في البرامج المختصرة يُكتب الصنف **بعد** التعليمات.
- `new Car()` ينشئ كائنًا جديدًا (نسخة) من الصنف.
- `car1.Brand` يصل إلى **حقل** في الكائن بالنقطة `.`.
- `public` تعني أن الحقل أو الدالة متاحة من خارج الصنف.

## المُنشئ (Constructor)

المُنشئ دالة خاصة **اسمها اسم الصنف**، تعمل تلقائيًا عند `new`، ومكانها المناسب لتجهيز القيم الابتدائية:

```csharp run
var s = new Student("نور", 3);
s.Print();
var t = new Student("عمر");
t.Print();

class Student
{
    public string Name;
    public int Level;

    public Student(string name, int level = 1)
    {
        Name = name;
        Level = level;
    }

    public void Print() => Console.WriteLine($"{Name} في المستوى {Level}");
}
```

```text output
نور في المستوى 3
عمر في المستوى 1
```

## التغليف والخصائص (Encapsulation and Properties)

لا نريد أن يضع أي أحد رصيدًا سالبًا في حساب البنك! لذلك نجعل الحقل **خاصًا** `private`، ونتحكم في الوصول إليه:

```csharp run
var acc = new BankAccount("هالة");
acc.Deposit(500);
acc.Withdraw(200);
acc.Withdraw(1000);
Console.WriteLine($"رصيد {acc.Owner}: {acc.Balance}");

class BankAccount
{
    private decimal balance;              // لا يُرى من الخارج

    public string Owner { get; }          // خاصية للقراءة فقط
    public decimal Balance => balance;    // خاصية محسوبة للقراءة

    public BankAccount(string owner)
    {
        Owner = owner;
    }

    public void Deposit(decimal amount)
    {
        if (amount > 0)
            balance += amount;
    }

    public void Withdraw(decimal amount)
    {
        if (amount > balance)
            Console.WriteLine("الرصيد لا يكفي");
        else
            balance -= amount;
    }
}
```

```text output
الرصيد لا يكفي
رصيد هالة: 300
```

**الخاصية** (property) تبدو من الخارج مثل الحقل، لكن خلفها كود يتحكم في القراءة (`get`) والكتابة (`set`).

### الخصائص التلقائية

```csharp run
var p = new Product { Name = "قلم", Price = 7.5m };
p.Price = 8;
Console.WriteLine($"{p.Name}: {p.Price}");

class Product
{
    public string Name { get; set; }
    public decimal Price { get; set; }
}
```

```text output
قلم: 8
```

`{ get; set; }` خاصية تلقائية: المترجم ينشئ الحقل الخفي بنفسه. و`new Product { Name = ..., Price = ... }` يسمى **مُهيئ الكائن** (object initializer).

### خاصية بشرط في `set`

```csharp run
var c = new Circle();
c.Radius = 3;
Console.WriteLine($"{c.Area:F2}");
c.Radius = -5;
Console.WriteLine(c.Radius);

class Circle
{
    private double radius;
    public double Radius
    {
        get => radius;
        set => radius = value < 0 ? 0 : value;   // value = القيمة الجديدة
    }
    public double Area => Math.PI * radius * radius;
}
```

```text output
28.27
0
```

## `ToString()`: كيف يُطبع الكائن؟

```csharp run
var pt = new Point(3, 4);
Console.WriteLine(pt);
Console.WriteLine($"النقطة هي {pt}");

class Point
{
    public int X { get; }
    public int Y { get; }
    public Point(int x, int y) { X = x; Y = y; }
    public override string ToString() => $"({X}, {Y})";
}
```

```text output
(3, 4)
النقطة هي (3, 4)
```

## الأعضاء الثابتة: `static`

العضو `static` يخص **الصنف نفسه** وليس كائنًا معينًا، مثل عدّاد مشترك بين كل الكائنات:

```csharp run
new Visitor("أ");
new Visitor("ب");
new Visitor("ج");
Console.WriteLine($"عدد الزوار: {Visitor.Count}");

class Visitor
{
    public static int Count = 0;
    public string Name;
    public Visitor(string name)
    {
        Name = name;
        Count++;
    }
}
```

```text output
عدد الزوار: 3
```

## السجلات: `record`

للبيانات البسيطة توفر C# الحديثة `record`: سطر واحد يعطيك المُنشئ والخصائص و`ToString` والمقارنة بالقيمة:

```csharp run
var a = new Person("Ali", 30);
var b = new Person("Ali", 30);
Console.WriteLine(a);
Console.WriteLine(a == b);

record Person(string Name, int Age);
```

```text output
Person { Name = Ali, Age = 30 }
True
```

## قائمة من الكائنات

```csharp run
var books = new List<Book>
{
    new Book("البخلاء", "الجاحظ", 1),
    new Book("كليلة ودمنة", "ابن المقفع", 2),
    new Book("الأيام", "طه حسين", 5)
};
foreach (var b in books.OrderBy(b => b.Title))
    Console.WriteLine(b);
Console.WriteLine($"مجموع النسخ: {books.Sum(b => b.Copies)}");

record Book(string Title, string Author, int Copies)
{
    public override string ToString() => $"{Title} - {Author} ({Copies} نسخة)";
}
```

```text output
الأيام - طه حسين (5 نسخة)
البخلاء - الجاحظ (1 نسخة)
كليلة ودمنة - ابن المقفع (2 نسخة)
مجموع النسخ: 8
```

## أخطاء شائعة

### استخدام كائن قبل إنشائه بـ `new`

```csharp
Car c = null;
c.Describe();   // NullReferenceException
```

المتغير موجود لكنه لا يشير إلى كائن. الرسالة `Object reference not set to an instance of an object` من أشهر أخطاء C#: ابحث عن متغير نسيت أن تكتب له `new`.

### الوصول إلى عضو `private` من الخارج

`acc.balance = 1000000;` يعطي الخطأ `CS0122: 'BankAccount.balance' is inaccessible due to its protection level`، وهذا هو المطلوب: التغليف يحمي البيانات.

### كتابة نوع إرجاع للمُنشئ

`public void Student(...)` ليست مُنشئًا بل دالة عادية! المُنشئ بلا نوع إرجاع إطلاقًا.

## تمارين

### التمرين 1

أكمل الصنف `Rectangle` بخاصيتين `Width` و`Height`، ومُنشئ، وخاصيتين محسوبتين `Area` و`Perimeter`.

```csharp exercise
var r = new Rectangle(5, 3);
Console.WriteLine($"المساحة {r.Area} والمحيط {r.Perimeter}");

class Rectangle
{
    // أكمل هنا
    public double Area => 0;
    public double Perimeter => 0;
    public Rectangle(double w, double h) { }
}
```

```csharp solution
var r = new Rectangle(5, 3);
Console.WriteLine($"المساحة {r.Area} والمحيط {r.Perimeter}");

class Rectangle
{
    public double Width { get; }
    public double Height { get; }
    public double Area => Width * Height;
    public double Perimeter => 2 * (Width + Height);
    public Rectangle(double w, double h) { Width = w; Height = h; }
}
```

```text output
المساحة 15 والمحيط 16
```

### التمرين 2

اكتب صنف `Counter` فيه دالة `Increment()` ودالة `Reset()` وخاصية للقراءة فقط `Value`.

```csharp exercise
var c = new Counter();
c.Increment();
c.Increment();
c.Increment();
Console.WriteLine(c.Value);
c.Reset();
Console.WriteLine(c.Value);

class Counter
{
    // أكمل هنا
    public int Value => 0;
    public void Increment() { }
    public void Reset() { }
}
```

```csharp solution
var c = new Counter();
c.Increment();
c.Increment();
c.Increment();
Console.WriteLine(c.Value);
c.Reset();
Console.WriteLine(c.Value);

class Counter
{
    public int Value { get; private set; }
    public void Increment() => Value++;
    public void Reset() => Value = 0;
}
```

```text output
3
0
```

### التمرين 3

عرّف `record Employee(string Name, decimal Salary)`، وأنشئ قائمة من ثلاثة موظفين، ثم اطبع اسم صاحب أعلى راتب ومتوسط الرواتب.

```csharp exercise
// record Employee(string Name, decimal Salary);
// الأعلى راتبًا: ...
// متوسط الرواتب: ...
```

```csharp solution
var staff = new List<Employee>
{
    new Employee("سامي", 7000),
    new Employee("رنا", 9500),
    new Employee("فادي", 6200)
};
var top = staff.OrderByDescending(e => e.Salary).First();
Console.WriteLine($"الأعلى راتبًا: {top.Name}");
Console.WriteLine($"متوسط الرواتب: {staff.Average(e => e.Salary):F0}");

record Employee(string Name, decimal Salary);
```

```text output
الأعلى راتبًا: رنا
متوسط الرواتب: 7567
```

## اختبر نفسك

```quiz
{"question": "ما العلاقة بين الصنف والكائن؟", "choices": ["هما نفس الشيء", "الصنف مخطط والكائن نسخة حقيقية منه تُنشأ بـ new", "الكائن مخطط والصنف نسخة منه", "الصنف دالة والكائن متغير"], "answer": 1, "explanation": "من صنف واحد نصنع كائنات كثيرة، لكل منها قيمه الخاصة."}
```

```quiz
{"question": "متى يعمل المُنشئ (constructor)؟", "choices": ["عند انتهاء البرنامج", "تلقائيًا عند إنشاء الكائن بـ new", "عند طباعة الكائن", "عندما نستدعيه باسمه في أي وقت"], "answer": 1, "explanation": "المُنشئ يعمل مرة واحدة لكل كائن لحظة إنشائه."}
```

```quiz
{"question": "لماذا نجعل الحقل private ونستخدم خاصية أو دالة للوصول إليه؟", "choices": ["لتسريع البرنامج", "للتغليف: نتحكم في القيم المسموحة ونحمي البيانات", "لأن public ممنوعة", "لتقليل حجم الملف"], "answer": 1, "explanation": "مثل حساب البنك: لا يمكن وضع رصيد سالب لأن التعديل يمر عبر دوال تفحص القيم."}
```

```quiz
{"question": "ماذا يعني static في public static int Count؟", "choices": ["لا يتغير أبدًا", "يخص الصنف نفسه ويشترك فيه كل الكائنات", "خاص بالكائن الأول فقط", "يُحذف بعد الاستخدام"], "answer": 1, "explanation": "العضو static نسخة واحدة على مستوى الصنف."}
```

## الخلاصة

- الصنف مخطط، والكائن نسخة منه بـ `new`، والأعضاء: حقول وخصائص ودوال.
- المُنشئ يجهز الكائن، و`private` مع الخصائص يحقق التغليف.
- `override ToString()` يحدد كيف يُطبع الكائن، و`static` للأعضاء المشتركة.
- `record` للبيانات البسيطة في سطر واحد.
