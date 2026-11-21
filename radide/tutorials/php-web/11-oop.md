# الدرس 11: الأصناف والكائنات والاستثناءات

**في هذا الدرس ستتعلم:**

- ما هو **الصنف** (class) وما هو **الكائن** (object).
- الخصائص والدوال (methods) والمُنشئ `__construct` بصيغته المختصرة.
- الخصائص الخاصة `private` والتغليف، والكلمة `readonly`.
- الوراثة باختصار، والدوال الثابتة `static`.
- **الاستثناءات**: `throw` و`try` و`catch`.

لماذا الآن؟ لأن كل الأدوات الحديثة في PHP تُستخدم بالكائنات: `PDO` لقواعد البيانات في الدرس القادم كائن، وأطر العمل Laravel وCodeIgniter مبنية بالكامل على الأصناف.

## الصنف قالب، والكائن نسخة منه

**الصنف** مثل **قالب الكعك**: يحدد الشكل. و**الكائن** كعكة حقيقية صُنعت بالقالب؛ تستطيع أن تصنع كعكات كثيرة، لكل منها حشوتها الخاصة.

```php run
<?php
class Book
{
    public string $title;
    public float $price;

    public function priceWithTax(): float
    {
        return $this->price * 1.14;
    }
}

$b = new Book();
$b->title = "مقدمة ابن خلدون";
$b->price = 200;
echo $b->title, ": ", $b->priceWithTax(), "\n";
```

```text output
مقدمة ابن خلدون: 228
```

- `class Book { ... }` يعرّف الصنف.
- `public string $title;` **خاصية** (property): بيان يحمله كل كائن.
- `public function ...` **دالة الصنف** (method): سلوك يقوم به الكائن.
- `new Book()` يصنع كائنًا جديدًا.
- `->` للوصول إلى خصائص الكائن ودواله، و`$this` تعني «الكائن الحالي».

## المُنشئ: تجهيز الكائن عند إنشائه

`__construct` دالة تُستدعى تلقائيًا مع `new`. وفي PHP 8 نستطيع تعريف الخصائص **مباشرة** في معاملات المُنشئ (ترقية المعاملات):

```php run
<?php
class Product
{
    public function __construct(
        public string $name,
        public float $price,
        public int $qty = 0,
    ) {
    }

    public function total(): float
    {
        return $this->price * $this->qty;
    }

    public function label(): string
    {
        return "{$this->name} × {$this->qty} = {$this->total()}";
    }
}

$p1 = new Product("قلم", 5, 12);
$p2 = new Product("دفتر", 20);
$p2->qty = 3;
echo $p1->label(), "\n";
echo $p2->label(), "\n";
```

```text output
قلم × 12 = 60
دفتر × 3 = 60
```

## التغليف: private

ماذا لو كتب أحدهم `$account->balance = -5000;`؟ نحمي البيانات بجعلها `private` (لا تُرى إلا داخل الصنف)، ونسمح بتغييرها عبر دوال تتحقق من صحتها. وهذا **التغليف** (encapsulation):

```php run
<?php
class BankAccount
{
    private float $balance = 0;

    public function __construct(public readonly string $owner)
    {
    }

    public function deposit(float $amount): void
    {
        if ($amount <= 0) {
            throw new InvalidArgumentException("المبلغ يجب أن يكون موجبًا");
        }
        $this->balance += $amount;
    }

    public function withdraw(float $amount): void
    {
        if ($amount > $this->balance) {
            throw new RuntimeException("الرصيد لا يكفي");
        }
        $this->balance -= $amount;
    }

    public function balance(): float
    {
        return $this->balance;
    }
}

$acc = new BankAccount("هالة");
$acc->deposit(1000);
$acc->withdraw(300);
echo "{$acc->owner}: {$acc->balance()}\n";

try {
    $acc->withdraw(5000);
} catch (RuntimeException $e) {
    echo "تعذّر السحب: ", $e->getMessage(), "\n";
}

try {
    $acc->owner = "شخص آخر";
} catch (Error $e) {
    echo "لا يمكن تغيير المالك (readonly)\n";
}
```

```text output
هالة: 700
تعذّر السحب: الرصيد لا يكفي
لا يمكن تغيير المالك (readonly)
```

- `readonly` خاصية تُعطى قيمتها مرة واحدة ولا تتغير بعدها.
- `throw new ...Exception("...")` **يرمي استثناءً**: يوقف التنفيذ العادي ويعلن عن مشكلة.

## الاستثناءات: try و catch

**الاستثناء** (exception) مثل **إنذار الحريق**: عند حدوث مشكلة يدق الإنذار، فيتوقف العمل العادي، وينتقل التنفيذ إلى أقرب `catch` مستعد للتعامل معه:

```php run
<?php
function divide(float $a, float $b): float
{
    if ($b == 0) {
        throw new DivisionByZeroError("لا يمكن القسمة على صفر");
    }
    return $a / $b;
}

foreach ([[10, 2], [5, 0], [9, 3]] as [$a, $b]) {
    try {
        $r = divide($a, $b);       // إن رُمي استثناء لا يُنفّذ السطر التالي
        echo "$a / $b = $r\n";
    } catch (DivisionByZeroError $e) {
        echo "خطأ: ", $e->getMessage(), "\n";
    } finally {
        echo "---\n";
    }
}
```

```text output
10 / 2 = 5
---
خطأ: لا يمكن القسمة على صفر
---
9 / 3 = 3
---
```

- `try { ... }` الكود الذي قد يرمي استثناءً.
- `catch (النوع $e)` يلتقط ذلك النوع، و`$e->getMessage()` نص الرسالة.
- `finally` يُنفّذ في كل الأحوال (نجح الكود أو فشل).

> **في الويب:** الاستثناء الذي لا يلتقطه أحد يظهر للزائر كـ `Fatal error: Uncaught ...`. في الدرس القادم سنلتقط استثناءات `PDOException` من قاعدة البيانات.

## الوراثة و static باختصار

**الوراثة** (inheritance): صنف جديد يأخذ كل ما في صنف موجود ويضيف عليه أو يغيّره. و`static` تعني أن الخاصية أو الدالة تخص **الصنف نفسه** لا كل كائن، ونصل إليها بـ `::`:

```php run
<?php
class User
{
    public static int $count = 0;

    public function __construct(public string $name)
    {
        self::$count++;
    }

    public function role(): string
    {
        return "مستخدم";
    }

    public function describe(): string
    {
        return "{$this->name} ({$this->role()})";
    }
}

class Admin extends User
{
    public function role(): string
    {
        return "مدير";
    }
}

$people = [new User("سعيد"), new Admin("نور"), new User("رامي")];
foreach ($people as $p) {
    echo $p->describe(), "\n";
}
echo "عدد المستخدمين: ", User::$count, "\n";
var_dump($people[1] instanceof User);
```

```text output
سعيد (مستخدم)
نور (مدير)
رامي (مستخدم)
عدد المستخدمين: 3
bool(true)
```

`Admin extends User` يرث كل شيء ويعيد تعريف `role` فقط. وهذا ما ستراه كثيرًا في Laravel: `class Post extends Model` وفي CodeIgniter: `class ProductModel extends Model`.

## أخطاء شائعة

- **نسيان `$this->`:** داخل الدالة `$price` متغير محلي جديد، أما خاصية الكائن فهي `$this->price`.
- **استخدام `.` بدل `->`:** `$book.title` خطأ؛ الصحيح `$book->title`.
- **الوصول إلى خاصية `private` من الخارج:** `Error: Cannot access private property`.
- **التقاط كل شيء وإخفاؤه:** `catch (Exception $e) {}` فارغ يخفي الأخطاء فلا تعرف ماذا حدث. اعرض أو سجّل الرسالة.

## تمارين

### تمرين 1: صنف المستطيل

أكمل صنف `Rectangle` بمُنشئ يأخذ `width` و`height`، ودالتي `area()` و`perimeter()`. لمستطيل 4 × 6 اطبع `المساحة 24 والمحيط 20`.

```php exercise
<?php
class Rectangle
{
    // __construct, area, perimeter
}
$r = new Rectangle(4, 6);
echo "المساحة {$r->area()} والمحيط {$r->perimeter()}\n";
```

```php solution
<?php
class Rectangle
{
    public function __construct(public float $width, public float $height)
    {
    }

    public function area(): float
    {
        return $this->width * $this->height;
    }

    public function perimeter(): float
    {
        return 2 * ($this->width + $this->height);
    }
}
$r = new Rectangle(4, 6);
echo "المساحة {$r->area()} والمحيط {$r->perimeter()}\n";
```

```text output
المساحة 24 والمحيط 20
```

### تمرين 2: عمر صحيح

دالة `setAge(int $age)` في صنف `Person` ترمي `InvalidArgumentException` برسالة `عمر غير صحيح` إذا كان العمر أقل من 0 أو أكبر من 150. التقط الاستثناء واطبع رسالته عند `setAge(200)`.

```php exercise
<?php
class Person
{
    private int $age = 0;

    public function setAge(int $age): void
    {
        $this->age = $age;
    }
}
$p = new Person();
$p->setAge(200);
```

```php solution
<?php
class Person
{
    private int $age = 0;

    public function setAge(int $age): void
    {
        if ($age < 0 || $age > 150) {
            throw new InvalidArgumentException("عمر غير صحيح");
        }
        $this->age = $age;
    }
}
$p = new Person();
try {
    $p->setAge(200);
} catch (InvalidArgumentException $e) {
    echo $e->getMessage(), "\n";
}
```

```text output
عمر غير صحيح
```

## اختبر نفسك

```quiz
{"question": "ما العلاقة بين الصنف والكائن؟", "choices": ["لا علاقة", "الصنف قالب والكائن نسخة مصنوعة منه بـ new", "الكائن قالب والصنف نسخة", "هما نفس الشيء"], "answer": 1, "explanation": "الصنف يحدد الشكل والسلوك، و new تصنع كائنًا منه."}
```

```quiz
{"question": "داخل دالة الصنف، كيف تصل إلى الخاصية price؟", "choices": ["$price", "$this->price", "this.price", "self.price"], "answer": 1, "explanation": "$this يشير إلى الكائن الحالي، و -> للوصول إلى خصائصه."}
```

```quiz
{"question": "متى يُنفّذ الجزء finally؟", "choices": ["عند النجاح فقط", "عند الفشل فقط", "في كل الأحوال", "لا يُنفّذ أبدًا"], "answer": 2, "explanation": "finally يعمل سواء رُمي استثناء أم لا."}
```

## الخلاصة

- `class` يعرّف قالبًا، و`new` يصنع كائنًا، و`->` للخصائص والدوال، و`$this` الكائن الحالي.
- المُنشئ المختصر `__construct(public string $name)` يعرّف الخاصية ويعطيها قيمتها.
- `private` و`readonly` يحميان البيانات، و`extends` للوراثة، و`static` للصنف نفسه.
- `throw` يرمي استثناءً، و`try / catch / finally` يتعامل معه.
