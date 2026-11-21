# الدرس 11: الوراثة والواجهات (Interfaces)

في الدرس السابق صنعنا أصنافًا مستقلة. لكن في الواقع كثير من الأشياء **تتشابه**: القطة والكلب كلاهما حيوان، والموظف والمدير كلاهما شخص. **الوراثة** تسمح لصنف أن يأخذ كل ما في صنف آخر ثم يضيف إليه أو يغيّر فيه.

> **تشبيه:** الوراثة مثل **العائلة**: الابن يرث من أبيه لون العينين وطول القامة، لكن له أيضًا صفاته الخاصة. وفي البرمجة: الصنف **المشتق** (derived) يرث من الصنف **الأساسي** (base) حقوله ودواله.

## أول مثال على الوراثة

```csharp run
var d = new Dog { Name = "ريكس" };
d.Eat();
d.Bark();

var c = new Cat { Name = "مشمش" };
c.Eat();
c.Meow();

class Animal
{
    public string Name { get; set; }
    public void Eat() => Console.WriteLine($"{Name} يأكل");
}

class Dog : Animal          // Dog يرث من Animal
{
    public void Bark() => Console.WriteLine($"{Name}: هاو هاو!");
}

class Cat : Animal
{
    public void Meow() => Console.WriteLine($"{Name}: مياو!");
}
```

```text output
ريكس يأكل
ريكس: هاو هاو!
مشمش يأكل
مشمش: مياو!
```

النقطتان `:` في `class Dog : Animal` تعني «يرث من». فالكلب عنده `Name` و`Eat()` دون أن نكتبهما من جديد.

## المُنشئ في الوراثة: `base`

```csharp run
var m = new Manager("سعاد", 12000, 4);
m.Print();

class Employee
{
    public string Name { get; }
    public decimal Salary { get; }
    public Employee(string name, decimal salary)
    {
        Name = name;
        Salary = salary;
    }
}

class Manager : Employee
{
    public int TeamSize { get; }
    public Manager(string name, decimal salary, int team) : base(name, salary)
    {
        TeamSize = team;
    }
    public void Print() => Console.WriteLine($"{Name} تدير فريقًا من {TeamSize} براتب {Salary}");
}
```

```text output
سعاد تدير فريقًا من 4 براتب 12000
```

`: base(name, salary)` يستدعي مُنشئ الصنف الأساسي أولًا.

## إعادة التعريف: `virtual` و`override`

أحيانًا يريد الصنف المشتق أن **يغير** سلوك دالة موروثة:

```csharp run
Shape[] shapes = { new Circle(2), new Square(3), new Shape() };
foreach (Shape s in shapes)
    Console.WriteLine($"{s.Name}: {s.Area():F2}");

class Shape
{
    public virtual string Name => "شكل";
    public virtual double Area() => 0;
}

class Circle : Shape
{
    private double r;
    public Circle(double r) { this.r = r; }
    public override string Name => "دائرة";
    public override double Area() => Math.PI * r * r;
}

class Square : Shape
{
    private double side;
    public Square(double side) { this.side = side; }
    public override string Name => "مربع";
    public override double Area() => side * side;
}
```

```text output
دائرة: 12.57
مربع: 9.00
شكل: 0.00
```

هذا هو **تعدد الأشكال** (polymorphism): المتغير من نوع `Shape`، لكن كل كائن ينفذ **نسخته** من `Area()`. الحلقة لا تعرف ولا تهتم إن كان الشكل دائرة أم مربعًا.

- `virtual` في الأساسي تعني «مسموح للمشتقين إعادة تعريفي».
- `override` في المشتق تعني «هذه نسختي الجديدة».
- `this.r` تعني «حقل `r` في هذا الكائن»، لتمييزه عن المعامل الذي يحمل نفس الاسم.

## الأصناف المجردة: `abstract`

إذا لم يكن لـ «شكل عام» معنى، نجعل الصنف **مجردًا**: لا يمكن إنشاء كائن منه، وعلى كل مشتق أن يكتب الدوال المجردة:

```csharp run
Vehicle[] list = { new Bike(), new Truck() };
foreach (var v in list)
    Console.WriteLine($"{v.GetType().Name}: {v.Wheels()} عجلات");

abstract class Vehicle
{
    public abstract int Wheels();
}

class Bike : Vehicle
{
    public override int Wheels() => 2;
}

class Truck : Vehicle
{
    public override int Wheels() => 6;
}
```

```text output
Bike: 2 عجلات
Truck: 6 عجلات
```

## الواجهات (Interfaces)

الواجهة **عقد**: قائمة دوال وخصائص يَعِد الصنف بتنفيذها، دون أي كود. والصنف يرث من صنف واحد فقط، لكنه يستطيع تنفيذ **عدة واجهات**.

> **تشبيه:** الواجهة مثل **مقبس الكهرباء**: أي جهاز له القابس المناسب يعمل فيه، سواء كان مكواة أو حاسوبًا أو شاحن هاتف. المقبس لا يهتم بما داخل الجهاز.

```csharp run
IPayable[] items = { new Invoice(1500), new Salary("هاني", 8000) };
decimal total = 0;
foreach (IPayable p in items)
{
    Console.WriteLine(p.Describe());
    total += p.Amount;
}
Console.WriteLine($"الإجمالي: {total}");

interface IPayable
{
    decimal Amount { get; }
    string Describe();
}

class Invoice : IPayable
{
    public decimal Amount { get; }
    public Invoice(decimal amount) { Amount = amount; }
    public string Describe() => $"فاتورة بقيمة {Amount}";
}

class Salary : IPayable
{
    public string Who { get; }
    public decimal Amount { get; }
    public Salary(string who, decimal amount) { Who = who; Amount = amount; }
    public string Describe() => $"راتب {Who}: {Amount}";
}
```

```text output
فاتورة بقيمة 1500
راتب هاني: 8000
الإجمالي: 9500
```

العُرف أن يبدأ اسم الواجهة بالحرف `I` مثل `IPayable` و`IComparable` و`IDisposable`.

## واجهة جاهزة من .NET: `IComparable`

```csharp run
var players = new List<Player> { new("سيف", 70), new("دينا", 95), new("مازن", 82) };
players.Sort();                        // يستخدم CompareTo
foreach (var p in players)
    Console.WriteLine($"{p.Name} {p.Score}");

class Player : IComparable<Player>
{
    public string Name { get; }
    public int Score { get; }
    public Player(string name, int score) { Name = name; Score = score; }
    public int CompareTo(Player other) => other.Score.CompareTo(Score);   // تنازليًا
}
```

```text output
دينا 95
مازن 82
سيف 70
```

## فحص النوع: `is` و`as`

```csharp run
object[] things = { 42, "مرحبا", 3.5, new List<int> { 1, 2 } };
foreach (object o in things)
{
    if (o is int n)
        Console.WriteLine($"عدد صحيح: {n * 2}");
    else if (o is string s)
        Console.WriteLine($"نص طوله {s.Length}");
    else
        Console.WriteLine($"نوع آخر: {o.GetType().Name}");
}
```

```text output
عدد صحيح: 84
نص طوله 5
نوع آخر: Double
نوع آخر: List`1
```

## أخطاء شائعة

- **نسيان `override`:** إذا كتبت في المشتق `public double Area()` بدون `override` فلن يحدث تعدد الأشكال، والمترجم يحذرك بـ `CS0114`.
- **محاولة إنشاء كائن من صنف مجرد:** `new Vehicle()` تعطي `CS0144: Cannot create an instance of the abstract type`.
- **عدم تنفيذ كل أعضاء الواجهة:** تعطي `CS0535: 'Invoice' does not implement interface member 'IPayable.Describe()'`.

## تمارين

### التمرين 1

أضف صنفًا `Triangle` يرث من `Shape` (قاعدة × ارتفاع ÷ 2)، ثم اطبع مساحة مثلث قاعدته 6 وارتفاعه 4.

```csharp exercise
Shape t = new Triangle(6, 4);
Console.WriteLine($"{t.Name}: {t.Area()}");

class Shape
{
    public virtual string Name => "شكل";
    public virtual double Area() => 0;
}

// class Triangle : Shape { ... }
```

```csharp solution
Shape t = new Triangle(6, 4);
Console.WriteLine($"{t.Name}: {t.Area()}");

class Shape
{
    public virtual string Name => "شكل";
    public virtual double Area() => 0;
}

class Triangle : Shape
{
    private double b, h;
    public Triangle(double b, double h) { this.b = b; this.h = h; }
    public override string Name => "مثلث";
    public override double Area() => b * h / 2;
}
```

```text output
مثلث: 12
```

### التمرين 2

عرّف واجهة `ISpeaker` فيها `string Speak()`، ونفّذها في صنفين `Duck` (`كاك`) و`Cow` (`موو`)، ثم اطبع صوت كل منهما من مصفوفة `ISpeaker[]`.

```csharp exercise
// interface ISpeaker { string Speak(); }
// كاك
// موو
```

```csharp solution
ISpeaker[] farm = { new Duck(), new Cow() };
foreach (var a in farm)
    Console.WriteLine(a.Speak());

interface ISpeaker
{
    string Speak();
}

class Duck : ISpeaker
{
    public string Speak() => "كاك";
}

class Cow : ISpeaker
{
    public string Speak() => "موو";
}
```

```text output
كاك
موو
```

## اختبر نفسك

```quiz
{"question": "ماذا تعني class Dog : Animal؟", "choices": ["Dog جزء من Animal", "Dog يرث من Animal كل أعضائه العامة", "Animal يرث من Dog", "Dog واجهة"], "answer": 1, "explanation": "النقطتان تعنيان الوراثة: Dog صنف مشتق من الصنف الأساسي Animal."}
```

```quiz
{"question": "ما الكلمتان اللازمتان لإعادة تعريف دالة في صنف مشتق؟", "choices": ["static و new", "virtual في الأساسي وoverride في المشتق", "public و private", "abstract و sealed"], "answer": 1, "explanation": "virtual تسمح بإعادة التعريف، وoverride تقدم النسخة الجديدة."}
```

```quiz
{"question": "ما الفرق الأهم بين الصنف الأساسي والواجهة في C#؟", "choices": ["لا فرق", "الصنف يرث من صنف واحد فقط لكنه ينفذ عدة واجهات", "الواجهة فيها كود والصنف لا", "الواجهة أسرع"], "answer": 1, "explanation": "الوراثة من صنف واحد فقط، أما الواجهات فيمكن تنفيذ أكثر من واحدة."}
```

## الخلاصة

- الوراثة `class B : A` تعيد استخدام الكود، و`base(...)` يستدعي مُنشئ الأساسي.
- `virtual` و`override` يحققان تعدد الأشكال، و`abstract` يجبر المشتقين على التنفيذ.
- الواجهة `interface` عقد ينفذه الصنف، ويمكن تنفيذ عدة واجهات.
- `is` يفحص النوع ويحوّل في نفس الوقت.
