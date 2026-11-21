# الدرس 3: المتغيرات وقابلية التغيير والأنواع

## `let`: تعريف متغير

```rust run
fn main() {
    let age = 25;
    let price = 19.99;
    let name = "علي";
    let is_student = true;
    println!("{name} عمره {age}، والسعر {price}، طالب؟ {is_student}");
}
```

```text output
علي عمره 25، والسعر 19.99، طالب؟ true
```

المترجم **يستنتج** النوع من القيمة: `25` عدد صحيح، و`19.99` عشري، وهكذا.

## المتغيرات ثابتة افتراضيًا!

هنا أول مفاجأة في Rust: المتغير **لا يمكن تغييره** إلا إذا طلبت ذلك صراحة بكلمة `mut` (اختصار mutable، أي قابل للتغيير):

<!-- compile-error -->
```rust
fn main() {
    let score = 10;
    score = 20;          // خطأ!
}
```

```text
error[E0384]: cannot assign twice to immutable variable `score`
help: consider making this binding mutable: `mut score`
```

```rust run
fn main() {
    let mut score = 10;
    println!("البداية: {score}");
    score = 20;
    score += 5;
    println!("الآن: {score}");
}
```

```text output
البداية: 10
الآن: 25
```

> **تشبيه:** المتغير العادي في Rust مثل **رسالة مكتوبة بالحبر**: لا تُمحى. والمتغير `mut` مثل **سبورة**: تكتب وتمسح كما تشاء. لماذا الحبر هو الافتراضي؟ لأن معظم القيم لا تحتاج تغييرًا، وعندما ترى `mut` تعرف فورًا أن هذه القيمة ستتغير، فتنتبه لها.

## الأنواع الأساسية

| النوع | يخزن | مثال |
|---|---|---|
| `i32` | عدد صحيح (الافتراضي) | `let n: i32 = -7;` |
| `i64` / `u64` | صحيح كبير / بلا إشارة | `let big: u64 = 9_000_000_000;` |
| `usize` | فهرس وأحجام | `let i: usize = 0;` |
| `f64` | عشري (الافتراضي) | `let x: f64 = 3.14;` |
| `bool` | `true` / `false` | `let ok = true;` |
| `char` | حرف يونيكود واحد | `let c = 'م';` |
| `&str` | نص ثابت | `let s = "مرحبا";` |

حرف `i` يعني عددًا بإشارة (موجب وسالب)، و`u` بلا إشارة (موجب فقط)، والرقم عدد البتات. والشرطة السفلية `_` في الأرقام للقراءة فقط: `1_000_000` تساوي مليونًا.

```rust run
fn main() {
    let a: i32 = 2_147_483_647;   // أكبر i32
    let b: u8 = 255;              // أكبر u8
    let c: char = 'ج';
    let big: i64 = a as i64 * 2;
    println!("{a} {b} {c} {big}");
    println!("حجم char = {} بايت", std::mem::size_of::<char>());
}
```

```text output
2147483647 255 ج 4294967294
حجم char = 4 بايت
```

## التحويل بين الأنواع: `as`

Rust **لا تحول تلقائيًا** بين الأنواع:

```rust run
fn main() {
    let total = 17;
    let count = 5;
    println!("{}", total / count);                    // قسمة صحيحة
    println!("{}", total as f64 / count as f64);      // قسمة عشرية
    let x = 9.99_f64;
    println!("{}", x as i32);                         // يحذف الكسر
    println!("{}", x.round() as i32);                 // يقرّب
}
```

```text output
3
3.4
9
10
```

## الظل (Shadowing)

يمكن تعريف متغير جديد **بنفس الاسم**، فيغطي القديم. مفيد عند تحويل قيمة من نوع لآخر:

```rust run
fn main() {
    let input = "42";                      // نص
    let input: i32 = input.parse().unwrap();   // نفس الاسم، لكن عدد الآن
    let input = input * 2;
    println!("{input}");
}
```

```text output
84
```

الفرق عن `mut`: الظل ينشئ متغيرًا **جديدًا** (وقد يكون نوعه مختلفًا)، بينما `mut` يغير قيمة نفس المتغير. و`.parse().unwrap()` تحول النص لعدد؛ سنفهمها في درس الأخطاء.

## الثوابت `const`

```rust run
const PI: f64 = 3.14159;
const MAX_USERS: u32 = 100;

fn main() {
    let r = 2.0;
    println!("المساحة: {:.2}", PI * r * r);
    println!("الحد الأقصى: {MAX_USERS}");
}
```

```text output
المساحة: 12.57
الحد الأقصى: 100
```

الثابت يجب أن يُكتب نوعه دائمًا، وأسماؤه بحروف كبيرة.

## الصفوف (Tuples)

قيمة واحدة تجمع عدة قيم بأنواع مختلفة:

```rust run
fn main() {
    let person = ("منى", 28, 1.65);
    println!("{} {} {}", person.0, person.1, person.2);
    let (name, age, height) = person;      // تفكيك
    println!("{name} - {age} - {height}");
}
```

```text output
منى 28 1.65
منى - 28 - 1.65
```

## المتغير غير المستخدم

إذا عرّفت متغيرًا ولم تستخدمه يعطيك المترجم **تحذيرًا** (ليس خطأ): `unused variable`. إذا كان مقصودًا ابدأ اسمه بـ `_`، مثل `_temp`.

## أخطاء شائعة

- **نسيان `mut`:** `cannot assign twice to immutable variable`.
- **خلط الأنواع:** `i32 + f64` خطأ ترجمة؛ حوّل بـ `as`.
- **تجاوز الحد:** `let x: u8 = 300;` خطأ ترجمة لأن `u8` لا يتجاوز 255. وأثناء التشغيل في وضع التصحيح يتوقف البرنامج بـ `attempt to add with overflow`.

## تمارين

### التمرين 1

اجعل الكود يعمل: المتغير `count` يجب أن يزيد:

```rust exercise
fn main() {
    let count = 0;
    count += 1;
    count += 1;
    println!("count = {count}");
}
```

```rust solution
fn main() {
    let mut count = 0;
    count += 1;
    count += 1;
    println!("count = {count}");
}
```

```text output
count = 2
```

### التمرين 2

احسب متوسط ثلاث درجات صحيحة واطبعه بخانتين، مستخدمًا `as f64`:

```rust exercise
fn main() {
    let a = 85;
    let b = 90;
    let c = 78;
    // المتوسط = 84.33
}
```

```rust solution
fn main() {
    let a = 85;
    let b = 90;
    let c = 78;
    let avg = (a + b + c) as f64 / 3.0;
    println!("المتوسط = {:.2}", avg);
}
```

```text output
المتوسط = 84.33
```

## اختبر نفسك

```quiz
{"question": "ماذا يحدث عند تغيير متغير عُرّف بـ `let x = 5;` بدون mut؟", "choices": ["يتغير عاديًا", "خطأ ترجمة", "تحذير فقط", "يُتجاهل التغيير"], "answer": 1, "explanation": "المتغيرات ثابتة افتراضيًا، والتغيير يحتاج mut."}
```

```quiz
{"question": "ما النوع الافتراضي للعدد الصحيح في Rust؟", "choices": ["i64", "i32", "u32", "usize"], "answer": 1, "explanation": "الأعداد الصحيحة بلا نوع محدد تكون i32."}
```

```quiz
{"question": "ما الفرق بين الظل (shadowing) وmut؟", "choices": ["لا فرق", "الظل ينشئ متغيرًا جديدًا قد يختلف نوعه، وmut يغير نفس المتغير", "mut أسرع", "الظل للثوابت فقط"], "answer": 1, "explanation": "let بنفس الاسم تنشئ متغيرًا جديدًا يغطي القديم."}
```

## الخلاصة

- `let` للتعريف، والمتغيرات ثابتة إلا مع `mut`.
- أنواع أساسية: `i32` و`f64` و`bool` و`char` و`&str`.
- لا تحويل تلقائي: استخدم `as`.
- الظل يعيد استخدام الاسم، و`const` للثوابت، والصفوف تجمع قيمًا مختلفة.
