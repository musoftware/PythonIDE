# الدرس 9: التعدادات و`Option` و`match`

الهيكل يقول: «عندي هذا **و** ذاك **و** ذلك». أما **التعداد** (enum) فيقول: «أنا **واحد فقط** من هذه الاحتمالات». إشارة المرور مثلًا إما حمراء **أو** صفراء **أو** خضراء، ولا يمكن أن تكون اثنين معًا.

> **تشبيه:** التعداد مثل **سؤال اختيار من متعدد**: الإجابة واحدة فقط من الخيارات المكتوبة. و`match` مثل **المصحح** الذي ينظر للإجابة ويقرر ماذا يفعل مع كل خيار.

## تعداد بسيط و`match`

```rust run
enum Light {
    Red,
    Yellow,
    Green,
}

fn action(l: Light) -> &'static str {
    match l {
        Light::Red => "قف",
        Light::Yellow => "استعد",
        Light::Green => "انطلق",
    }
}

fn main() {
    println!("{}", action(Light::Red));
    println!("{}", action(Light::Green));
}
```

```text output
قف
انطلق
```

`match` يجب أن يغطي **كل** الاحتمالات. لو حذفت سطر `Light::Green` سيرفض المترجم:

```text
error[E0004]: non-exhaustive patterns: `Light::Green` not covered
```

هذه ميزة عظيمة: إذا أضفت لونًا جديدًا للتعداد لاحقًا، يدلك المترجم على **كل** مكان نسيت أن تعالجه فيه.

> **ملاحظة:** `&'static str` تعني نصًا ثابتًا مكتوبًا داخل البرنامج يعيش طوال تشغيله. لا تقلق من `'static` الآن.

## تعدادات تحمل بيانات

كل خيار في التعداد يمكن أن يحمل بيانات مختلفة:

```rust run
enum Shape {
    Circle(f64),                 // نصف القطر
    Rect { w: f64, h: f64 },     // عرض وارتفاع
    Dot,                         // بلا بيانات
}

impl Shape {
    fn area(&self) -> f64 {
        match self {
            Shape::Circle(r) => 3.14 * r * r,
            Shape::Rect { w, h } => w * h,
            Shape::Dot => 0.0,
        }
    }
}

fn main() {
    let shapes = vec![Shape::Circle(1.0), Shape::Rect { w: 2.0, h: 5.0 }, Shape::Dot];
    for s in &shapes {
        println!("{:.2}", s.area());
    }
}
```

```text output
3.14
10.00
0.00
```

داخل `match` **نفك** البيانات: `Shape::Circle(r)` تضع نصف القطر في المتغير `r`.

## `Option`: قيمة قد تكون موجودة أو لا

في Rust **لا يوجد** `null`. بدلًا منه تعداد جاهز في المكتبة القياسية:

```rust
enum Option<T> {
    Some(T),   // توجد قيمة
    None,      // لا توجد قيمة
}
```

مثلًا البحث عن عنصر قد ينجح أو يفشل:

```rust run
fn find_index(names: &[&str], target: &str) -> Option<usize> {
    for (i, n) in names.iter().enumerate() {
        if *n == target {
            return Some(i);
        }
    }
    None
}

fn main() {
    let names = ["علي", "منى", "يوسف"];
    match find_index(&names, "منى") {
        Some(i) => println!("وجدتها في المكان {i}"),
        None => println!("غير موجودة"),
    }
    match find_index(&names, "هند") {
        Some(i) => println!("وجدتها في المكان {i}"),
        None => println!("غير موجودة"),
    }
}
```

```text output
وجدتها في المكان 1
غير موجودة
```

> **لماذا هذا أفضل من null؟** في لغات كثيرة تنسى أن القيمة قد تكون `null` فينهار البرنامج. في Rust لا يمكنك استخدام ما بداخل `Option` قبل أن **تفتحه** وتتعامل مع حالة `None`. المترجم يجبرك على التفكير فيها.

## طرق مختصرة مع `Option`

```rust run
fn main() {
    let a: Option<i32> = Some(5);
    let b: Option<i32> = None;

    println!("{}", a.unwrap_or(0));      // القيمة أو بديل
    println!("{}", b.unwrap_or(0));

    if let Some(x) = a {                 // نهتم بحالة واحدة فقط
        println!("a فيها {x}");
    }

    let doubled = a.map(|x| x * 2);      // نحول القيمة إن وجدت
    println!("{:?} {:?}", doubled, b.map(|x| x * 2));

    let v = vec![10, 20, 30];
    println!("{:?} {:?}", v.get(1), v.get(9));   // get ترجع Option
}
```

```text output
5
0
a فيها 5
Some(10) None
Some(20) None
```

- `unwrap_or(بديل)`: القيمة، أو البديل إن كانت `None`.
- `if let Some(x) = ...`: مثل `match` بفرع واحد.
- `unwrap()`: تأخذ القيمة **وتوقف البرنامج** إن كانت `None`. استخدمها فقط عندما تكون متأكدًا تمامًا.

## قوة `match` مع الأرقام

```rust run
fn grade(mark: u32) -> char {
    match mark {
        90..=100 => 'A',
        80..=89 => 'B',
        70..=79 => 'C',
        0..=69 => 'F',
        _ => '?',                        // _ تعني «أي شيء آخر»
    }
}

fn main() {
    for m in [95, 83, 71, 40, 150] {
        print!("{} ", grade(m));
    }
    println!();
    let n = 7;
    let kind = match n % 2 {
        0 => "زوجي",
        _ => "فردي",
    };
    println!("{n} {kind}");
}
```

```text output
A B C F ? 
7 فردي
```

## أخطاء شائعة

- **نسيان حالة في `match`:** خطأ `non-exhaustive patterns`. أضف الحالة أو استخدم `_`.
- **استخدام `Option` كأنه قيمة عادية:** `a + 1` حيث `a: Option<i32>` خطأ `cannot add`. افتحها أولًا بـ `match` أو `unwrap_or`.
- **الإفراط في `unwrap()`:** البرنامج ينهار برسالة `called Option::unwrap() on a None value`. استخدم `match` أو `if let`.

## تمارين

### التمرين 1

أكمل الدالة `day_name` لترجع اسم اليوم (1 = السبت ... 7 = الجمعة) في `Some`، و`None` لأي رقم آخر:

```rust exercise
fn day_name(n: u32) -> Option<&'static str> {
    // أكمل
    None
}

fn main() {
    for n in [1, 7, 9] {
        match day_name(n) {
            Some(d) => println!("{n}: {d}"),
            None => println!("{n}: رقم غير صحيح"),
        }
    }
}
```

```rust solution
fn day_name(n: u32) -> Option<&'static str> {
    match n {
        1 => Some("السبت"),
        2 => Some("الأحد"),
        3 => Some("الاثنين"),
        4 => Some("الثلاثاء"),
        5 => Some("الأربعاء"),
        6 => Some("الخميس"),
        7 => Some("الجمعة"),
        _ => None,
    }
}

fn main() {
    for n in [1, 7, 9] {
        match day_name(n) {
            Some(d) => println!("{n}: {d}"),
            None => println!("{n}: رقم غير صحيح"),
        }
    }
}
```

```text output
1: السبت
7: الجمعة
9: رقم غير صحيح
```

### التمرين 2

عرّف تعدادًا `Op` فيه `Add` و`Sub` و`Mul`، ودالة `apply` تنفذ العملية على رقمين:

```rust exercise
// عرّف enum Op هنا

fn apply(op: Op, a: i32, b: i32) -> i32 {
    // أكمل
    0
}

fn main() {
    println!("{}", apply(Op::Add, 6, 3));
    println!("{}", apply(Op::Sub, 6, 3));
    println!("{}", apply(Op::Mul, 6, 3));
}
```

```rust solution
enum Op {
    Add,
    Sub,
    Mul,
}

fn apply(op: Op, a: i32, b: i32) -> i32 {
    match op {
        Op::Add => a + b,
        Op::Sub => a - b,
        Op::Mul => a * b,
    }
}

fn main() {
    println!("{}", apply(Op::Add, 6, 3));
    println!("{}", apply(Op::Sub, 6, 3));
    println!("{}", apply(Op::Mul, 6, 3));
}
```

```text output
9
3
18
```

## اختبر نفسك

```quiz
{"question": "ما الذي يستخدمه Rust بدل null؟", "choices": ["0", "Option مع Some وNone", "undefined", "Nothing"], "answer": 1, "explanation": "Option<T> إما Some(قيمة) أو None، والمترجم يجبرك على معالجة الحالتين."}
```

```quiz
{"question": "ماذا يحدث إذا لم يغطِّ match كل حالات التعداد؟", "choices": ["يعمل ويتجاهل الباقي", "خطأ ترجمة non-exhaustive patterns", "ينهار وقت التشغيل", "تحذير فقط"], "answer": 1, "explanation": "match يجب أن يكون شاملًا، وإلا يرفض المترجم الكود."}
```

```quiz
{"question": "ماذا يعني النمط _ في match؟", "choices": ["لا شيء", "أي قيمة أخرى", "خطأ", "صفر"], "answer": 1, "explanation": "_ يطابق أي قيمة لم تطابقها الفروع السابقة."}
```

## الخلاصة

- `enum` نوع قيمته **واحد** من عدة خيارات، وكل خيار قد يحمل بيانات.
- `match` يفحص كل الخيارات، والمترجم يتأكد أنك لم تنسَ شيئًا.
- `Option<T>` بديل آمن لـ null: `Some(x)` أو `None`.
- `if let` و`unwrap_or` و`map` اختصارات مفيدة.
