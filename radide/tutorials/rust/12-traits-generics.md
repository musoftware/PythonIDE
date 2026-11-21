# الدرس 12: السمات (traits) والأنواع العامة

لنفترض أن عندنا قطة وكلبًا وبقرة، وكلها «تُصدر صوتًا». نريد دالة واحدة تتعامل مع أي حيوان يُصدر صوتًا. في Rust نعبر عن هذه «القدرة المشتركة» بـ **سمة** (trait).

> **تشبيه:** السمة مثل **رخصة القيادة**: لا يهم إن كنت طبيبًا أو مهندسًا، المهم أنك تحمل الرخصة، فيُسمح لك بقيادة السيارة. والدالة التي تطلب `impl Speak` تقول: «أي نوع يحمل رخصة `Speak` مرحب به».

## تعريف سمة وتطبيقها

```rust run
trait Speak {
    fn name(&self) -> String;
    fn sound(&self) -> String;

    // تابع له تنفيذ افتراضي: تحصل عليه الأنواع مجانًا
    fn introduce(&self) -> String {
        format!("أنا {} وأقول {}", self.name(), self.sound())
    }
}

struct Cat;
struct Dog {
    name: String,
}

impl Speak for Cat {
    fn name(&self) -> String {
        String::from("قطة")
    }
    fn sound(&self) -> String {
        String::from("مياو")
    }
}

impl Speak for Dog {
    fn name(&self) -> String {
        self.name.clone()
    }
    fn sound(&self) -> String {
        String::from("هاو")
    }
    fn introduce(&self) -> String {            // نعيد تعريف التابع الافتراضي
        format!("الكلب {} ينبح: {}!", self.name, self.sound())
    }
}

fn main() {
    let c = Cat;
    let d = Dog { name: String::from("ريكس") };
    println!("{}", c.introduce());
    println!("{}", d.introduce());
}
```

```text output
أنا قطة وأقول مياو
الكلب ريكس ينبح: هاو!
```

## دوال تقبل أي نوع يطبق السمة

```rust run
trait Shape {
    fn area(&self) -> f64;
}

struct Square(f64);
struct Circle(f64);

impl Shape for Square {
    fn area(&self) -> f64 {
        self.0 * self.0
    }
}

impl Shape for Circle {
    fn area(&self) -> f64 {
        3.14 * self.0 * self.0
    }
}

// تقبل أي نوع يطبق Shape (يُحدد النوع وقت الترجمة)
fn describe(s: &impl Shape) -> String {
    format!("المساحة {:.1}", s.area())
}

fn main() {
    println!("{}", describe(&Square(3.0)));
    println!("{}", describe(&Circle(1.0)));

    // قائمة فيها أنواع مختلفة: نستخدم Box<dyn Shape>
    let shapes: Vec<Box<dyn Shape>> = vec![Box::new(Square(2.0)), Box::new(Circle(2.0))];
    let total: f64 = shapes.iter().map(|s| s.area()).sum();
    println!("المجموع {:.2}", total);
}
```

```text output
المساحة 9.0
المساحة 3.1
المجموع 16.56
```

- `&impl Shape`: «أي نوع يطبق `Shape`».
- `Box<dyn Shape>`: صندوق يحمل **أي** شكل، لنضع أشكالًا مختلفة في نفس القائمة.

## الأنواع العامة (Generics)

دالة واحدة تعمل مع أنواع كثيرة. نكتب النوع كمتغير بين `<>`:

```rust run
fn largest<T: PartialOrd + Copy>(items: &[T]) -> T {
    let mut big = items[0];
    for &x in items {
        if x > big {
            big = x;
        }
    }
    big
}

#[derive(Debug)]
struct Pair<T> {
    a: T,
    b: T,
}

impl<T: std::fmt::Display> Pair<T> {
    fn show(&self) -> String {
        format!("({}, {})", self.a, self.b)
    }
}

fn main() {
    println!("{}", largest(&[3, 9, 2]));
    println!("{}", largest(&[1.5, 0.2, 7.25]));
    println!("{}", largest(&['ب', 'ي', 'ا']));
    let p = Pair { a: "سين", b: "صاد" };
    println!("{}", p.show());
}
```

```text output
9
7.25
ي
(سين, صاد)
```

`T: PartialOrd + Copy` اسمها **قيد**: «`T` أي نوع **يمكن مقارنته** و**يمكن نسخه**». بدون `PartialOrd` لا يسمح المترجم بـ `x > big`.

## سمات جاهزة مهمة

| السمة | تعطيك | كيف تحصل عليها |
|---|---|---|
| `Debug` | الطباعة بـ `{:?}` | `#[derive(Debug)]` |
| `Display` | الطباعة بـ `{}` | تكتبها بنفسك |
| `Clone` / `Copy` | النسخ | `#[derive(Clone, Copy)]` |
| `PartialEq` / `PartialOrd` | `==` و`<` | `#[derive(PartialEq, PartialOrd)]` |
| `Default` | قيمة افتراضية `T::default()` | `#[derive(Default)]` |

### تطبيق `Display` بنفسك

```rust run
use std::fmt;

struct Money {
    pounds: u32,
    piasters: u32,
}

impl fmt::Display for Money {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{} جنيه و{} قرش", self.pounds, self.piasters)
    }
}

fn main() {
    let m = Money { pounds: 12, piasters: 50 };
    println!("السعر: {m}");
    let text = m.to_string();          // Display تعطيك to_string مجانًا
    println!("{}", text.len() > 0);
}
```

```text output
السعر: 12 جنيه و50 قرش
true
```

## أخطاء شائعة

| الرسالة | السبب | الحل |
|---|---|---|
| `the trait bound Foo: Shape is not satisfied` | النوع لا يطبق السمة | اكتب `impl Shape for Foo` |
| `binary operation > cannot be applied to type T` | نوع عام بلا قيد مقارنة | أضف `T: PartialOrd` |
| `not all trait items implemented, missing: area` | نسيت دالة مطلوبة | اكتب الدالة (أو اضغط **Ctrl+.** > «Implement missing members») |
| `doesn't implement std::fmt::Display` | طباعة بـ `{}` لنوعك | طبّق `Display` أو استخدم `{:?}` مع `Debug` |

## تمارين

### التمرين 1

طبّق السمة `Describe` على الهيكل `Book` لترجع «كتاب: العنوان»:

```rust exercise
trait Describe {
    fn describe(&self) -> String;
}

struct Book {
    title: String,
}

// اكتب impl Describe for Book هنا

fn main() {
    let b = Book { title: String::from("الأيام") };
    println!("{}", b.describe());
}
```

```rust solution
trait Describe {
    fn describe(&self) -> String;
}

struct Book {
    title: String,
}

impl Describe for Book {
    fn describe(&self) -> String {
        format!("كتاب: {}", self.title)
    }
}

fn main() {
    let b = Book { title: String::from("الأيام") };
    println!("{}", b.describe());
}
```

```text output
كتاب: الأيام
```

### التمرين 2

اكتب دالة عامة `count_equal` تعد كم مرة يظهر عنصر في شريحة، لأي نوع يمكن مقارنته بـ `==`:

```rust exercise
fn count_equal<T>(items: &[T], target: T) -> usize {
    // أكمل (ستحتاج قيدًا على T)
    0
}

fn main() {
    println!("{}", count_equal(&[1, 2, 1, 3, 1], 1));
    println!("{}", count_equal(&["أ", "ب", "أ"], "أ"));
}
```

```rust solution
fn count_equal<T: PartialEq>(items: &[T], target: T) -> usize {
    items.iter().filter(|x| **x == target).count()
}

fn main() {
    println!("{}", count_equal(&[1, 2, 1, 3, 1], 1));
    println!("{}", count_equal(&["أ", "ب", "أ"], "أ"));
}
```

```text output
3
2
```

## اختبر نفسك

```quiz
{"question": "ما السمة (trait) في Rust؟", "choices": ["نوع من المتغيرات", "مجموعة دوال تصف قدرة مشتركة تطبقها الأنواع", "حلقة تكرار", "مكتبة خارجية"], "answer": 1, "explanation": "السمة تعرّف سلوكًا مشتركًا، وأي نوع يطبقها يمكن استخدامه حيث تُطلب."}
```

```quiz
{"question": "ماذا يعني T: PartialOrd في fn largest<T: PartialOrd>؟", "choices": ["T يجب أن يكون رقمًا", "T أي نوع يمكن مقارنته بـ < و>", "T نص", "لا شيء"], "answer": 1, "explanation": "هذا قيد يسمح باستخدام عمليات المقارنة على T."}
```

```quiz
{"question": "كيف تضع أشكالًا من أنواع مختلفة في قائمة واحدة؟", "choices": ["Vec<Shape>", "Vec<Box<dyn Shape>>", "Vec<impl Shape>", "مستحيل"], "answer": 1, "explanation": "Box<dyn Shape> يحمل أي نوع يطبق Shape."}
```

## الخلاصة

- `trait` يصف قدرة، و`impl Trait for Type` يطبقها.
- الدوال الافتراضية في السمة تُعطى مجانًا ويمكن إعادة تعريفها.
- `&impl Trait` و`<T: Trait>` لدوال تقبل أنواعًا كثيرة، و`Box<dyn Trait>` لقوائم مختلطة.
- `Display` و`Debug` و`Clone` و`PartialEq` سمات جاهزة تستخدمها كل يوم.
