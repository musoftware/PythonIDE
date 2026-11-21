# الدرس 8: الهياكل والدوال المرتبطة

حتى الآن خزّنا كل معلومة في متغير منفصل. لكن الطالب مثلًا له **اسم** و**عمر** و**درجة**. بدل ثلاثة متغيرات متفرقة نجمعها في **هيكل** (struct) واحد.

> **تشبيه:** الهيكل مثل **استمارة** فيها خانات بأسماء: «الاسم»، «العمر»، «الدرجة». تعريف الهيكل هو **تصميم الاستمارة**، وكل متغير من نوعه هو **استمارة معبأة**.

## تعريف هيكل واستخدامه

```rust run
struct Student {
    name: String,
    age: u32,
    mark: f64,
}

fn main() {
    let s = Student {
        name: String::from("سارة"),
        age: 19,
        mark: 91.5,
    };
    println!("{} عمرها {} ودرجتها {}", s.name, s.age, s.mark);

    let mut t = Student { name: String::from("خالد"), age: 20, mark: 70.0 };
    t.mark += 5.0;                       // نغير حقلًا (لأن t معرّف بـ mut)
    println!("{}: {}", t.name, t.mark);
}
```

```text output
سارة عمرها 19 ودرجتها 91.5
خالد: 75
```

- كل **حقل** له اسم ونوع.
- نصل للحقل بالنقطة: `s.name`.
- لتغيير أي حقل يجب أن يكون المتغير كله `mut`.

## الدوال المرتبطة ودوال الكائن بـ `impl`

نضع الدوال الخاصة بالهيكل داخل كتلة `impl`:

- **دالة مرتبطة** لا تأخذ `self`، مثل المُنشئ `new`، وتُستدعى بـ `Student::new(...)`.
- **دالة كائن** (method، وتُسمّى أيضًا «تابعًا») تأخذ `&self` (للقراءة) أو `&mut self` (للتعديل)، وتُستدعى بالنقطة `s.passed()`.

```rust run
struct Rect {
    w: f64,
    h: f64,
}

impl Rect {
    fn new(w: f64, h: f64) -> Rect {          // دالة مرتبطة (مُنشئ)
        Rect { w, h }                          // اختصار: w: w, h: h
    }

    fn square(side: f64) -> Self {             // Self = Rect
        Self { w: side, h: side }
    }

    fn area(&self) -> f64 {                    // تابع للقراءة
        self.w * self.h
    }

    fn scale(&mut self, k: f64) {              // تابع للتعديل
        self.w *= k;
        self.h *= k;
    }
}

fn main() {
    let mut r = Rect::new(3.0, 4.0);
    println!("المساحة = {}", r.area());
    r.scale(2.0);
    println!("بعد التكبير = {}", r.area());
    let q = Rect::square(5.0);
    println!("مربع = {}", q.area());
}
```

```text output
المساحة = 12
بعد التكبير = 48
مربع = 25
```

> **ملاحظة:** `&self` هي نفس فكرة الاستعارة من الدرس 6: دالة الكائن **تستعير** الكائن ولا يأخذ ملكيته.

## طباعة الهيكل بـ `#[derive(Debug)]`

لا يعرف `println!` كيف يطبع هيكلك. نطلب من المترجم أن يكتب كود الطباعة بنفسه:

```rust run
#[derive(Debug, Clone, PartialEq)]
struct Point {
    x: i32,
    y: i32,
}

fn main() {
    let p = Point { x: 3, y: -2 };
    println!("{:?}", p);                 // طباعة مختصرة
    println!("{:#?}", p);                // طباعة منسقة على عدة أسطر
    let q = p.clone();
    println!("متساويان؟ {}", p == q);
}
```

```text output
Point { x: 3, y: -2 }
Point {
    x: 3,
    y: -2,
}
متساويان؟ true
```

- `Debug` للطباعة بـ `{:?}`.
- `Clone` لكي تعمل `.clone()`.
- `PartialEq` لكي تعمل المقارنة `==`.

## هياكل الصفوف (tuple structs)

هيكل بلا أسماء للحقول، مفيد لإعطاء معنى لقيمة بسيطة:

```rust run
struct Meters(f64);
struct Color(u8, u8, u8);

fn main() {
    let d = Meters(12.5);
    let red = Color(255, 0, 0);
    println!("المسافة {} متر", d.0);
    println!("الأحمر = ({}, {}, {})", red.0, red.1, red.2);
}
```

```text output
المسافة 12.5 متر
الأحمر = (255, 0, 0)
```

## مثال متكامل: حساب بنكي

```rust run
#[derive(Debug)]
struct Account {
    owner: String,
    balance: f64,
}

impl Account {
    fn new(owner: &str) -> Self {
        Account { owner: owner.to_string(), balance: 0.0 }
    }

    fn deposit(&mut self, amount: f64) {
        self.balance += amount;
    }

    fn withdraw(&mut self, amount: f64) -> bool {
        if amount > self.balance {
            return false;                    // الرصيد لا يكفي
        }
        self.balance -= amount;
        true
    }
}

fn main() {
    let mut acc = Account::new("ليلى");
    acc.deposit(500.0);
    println!("سحب 200: {}", acc.withdraw(200.0));
    println!("سحب 900: {}", acc.withdraw(900.0));
    println!("{:?}", acc);
}
```

```text output
سحب 200: true
سحب 900: false
Account { owner: "ليلى", balance: 300.0 }
```

لاحظ أن `{:?}` يطبع `300.0` بالفاصلة العشرية، بينما `{}` يطبعها `300`.

## أخطاء شائعة

| الرسالة | السبب | الحل |
|---|---|---|
| `` `Point` doesn't implement `Debug` `` | طباعة بـ `{:?}` بدون derive | أضف `#[derive(Debug)]` فوق الهيكل |
| `cannot assign to s.mark, as s is not declared as mutable` | تعديل حقل في متغير غير `mut` | `let mut s = ...` |
| `cannot borrow *self as mutable` | دالة تعدّل الكائن لكنها تأخذ `&self` | غيّرها إلى `&mut self` |
| `missing field age` | نسيان حقل عند الإنشاء | يجب تعبئة كل الحقول |

> **نصيحة من الـ IDE:** اكتب `r.` في المحرر فيعرض لك rust-analyzer كل الحقول ودوال الكائن. وإذا نسيت حقلًا عند الإنشاء ضع المؤشر على الخطأ واضغط **Ctrl+.** واختر «Fill struct fields» فتُكتب الحقول الناقصة لك.

## تمارين

### التمرين 1

أضف إلى الهيكل `Circle` دالة `area` ترجع المساحة (π × r × r) واستخدم `std::f64::consts::PI`:

```rust exercise
use std::f64::consts::PI;

struct Circle {
    r: f64,
}

impl Circle {
    // أضف التابع area هنا
}

fn main() {
    let c = Circle { r: 2.0 };
    println!("{:.2}", c.area());
}
```

```rust solution
use std::f64::consts::PI;

struct Circle {
    r: f64,
}

impl Circle {
    fn area(&self) -> f64 {
        PI * self.r * self.r
    }
}

fn main() {
    let c = Circle { r: 2.0 };
    println!("{:.2}", c.area());
}
```

```text output
12.57
```

### التمرين 2

اكتب هيكل `Counter` فيه حقل `count` ومُنشئ `new` يبدأ من صفر ودالة `tick` تزيده بواحد. ثم استدعِ `tick` ثلاث مرات واطبع العدد:

```rust exercise
struct Counter {
    count: u32,
}

// اكتب impl Counter هنا

fn main() {
    let mut c = Counter::new();
    c.tick();
    c.tick();
    c.tick();
    println!("العدد = {}", c.count);
}
```

```rust solution
struct Counter {
    count: u32,
}

impl Counter {
    fn new() -> Self {
        Counter { count: 0 }
    }

    fn tick(&mut self) {
        self.count += 1;
    }
}

fn main() {
    let mut c = Counter::new();
    c.tick();
    c.tick();
    c.tick();
    println!("العدد = {}", c.count);
}
```

```text output
العدد = 3
```

## اختبر نفسك

```quiz
{"question": "كيف تستدعي الدالة المرتبطة new للهيكل Rect؟", "choices": ["Rect.new()", "Rect::new()", "new Rect()", "Rect->new()"], "answer": 1, "explanation": "الدوال المرتبطة (بلا self) تُستدعى بـ :: مثل Rect::new()."}
```

```quiz
{"question": "دالة كائن تغيّر حقول الكائن يجب أن تأخذ:", "choices": ["self", "&self", "&mut self", "لا شيء"], "answer": 2, "explanation": "&mut self تعطي الدالة استعارة قابلة للتعديل."}
```

```quiz
{"question": "ماذا تضيف لكي تطبع الهيكل بـ {:?}؟", "choices": ["#[derive(Debug)]", "impl Print", "use std::fmt", "#[print]"], "answer": 0, "explanation": "derive(Debug) يجعل المترجم يكتب كود الطباعة."}
```

## الخلاصة

- `struct` يجمع حقولًا مرتبطة في نوع واحد.
- `impl` يضم الدوال المرتبطة (`Type::new`) ودوال الكائن (`obj.method()`).
- `&self` للقراءة و`&mut self` للتعديل.
- `#[derive(Debug, Clone, PartialEq)]` يعطيك الطباعة والنسخ والمقارنة مجانًا.
