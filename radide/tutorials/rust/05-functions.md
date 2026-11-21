# الدرس 5: الدوال والتعبيرات

> **تشبيه:** الدالة **ماكينة عصير**: تضع الفاكهة (المعاملات) فتخرج العصير (القيمة المرجعة). وفي Rust يجب أن تكتب على الماكينة نوع ما يدخل ونوع ما يخرج بوضوح.

## تعريف دالة

```rust run
fn square(x: i32) -> i32 {
    x * x                      // بلا ; : هذه قيمة الدالة
}

fn greet(name: &str) {
    println!("أهلًا يا {name}");
}

fn add(a: f64, b: f64) -> f64 {
    return a + b;              // return صريحة (مسموحة أيضًا)
}

fn main() {
    println!("{}", square(7));
    greet("سلمى");
    println!("{}", add(2.5, 4.0));
}
```

```text output
49
أهلًا يا سلمى
6.5
```

- نوع كل معامل **إجباري**: `x: i32`.
- نوع القيمة المرجعة بعد السهم: `-> i32`. والدالة بلا سهم لا ترجع شيئًا.
- أسماء الدوال والمتغيرات في Rust بحروف صغيرة وشرطة سفلية: `calculate_total` (أسلوب snake_case).
- ترتيب الدوال في الملف لا يهم.

## التعبير والجملة: سر الفاصلة المنقوطة

- **التعبير** (expression) يعطي قيمة: `5` و`x + 1` و`if ... else ...` وكتلة `{ ... }`.
- **الجملة** (statement) تنفذ عملًا ولا تعطي قيمة، وتنتهي بـ `;`.

السطر الأخير في الدالة **بلا** `;` هو القيمة المرجعة. فإن أضفت `;` بالخطأ يصبح جملة، والدالة لا ترجع شيئًا:

<!-- compile-error -->
```rust
fn square(x: i32) -> i32 {
    x * x;
}
```

```text
error[E0308]: mismatched types
  |
1 | fn square(x: i32) -> i32 {
  |    ------            ^^^ expected `i32`, found `()`
2 |     x * x;
  |          - help: remove this semicolon to return this value
```

مرة أخرى، المترجم يخبرك بالحل: «احذف الفاصلة المنقوطة». و`()` اسمها «الوحدة» (unit)، وتعني «لا قيمة».

## الكتل تعبيرات أيضًا

```rust run
fn main() {
    let x = 3;
    let y = {
        let doubled = x * 2;
        doubled + 1            // قيمة الكتلة
    };
    println!("y = {y}");
}
```

```text output
y = 7
```

## إرجاع أكثر من قيمة بصف

```rust run
fn divide(a: i32, b: i32) -> (i32, i32) {
    (a / b, a % b)
}

fn min_max(nums: &[i32]) -> (i32, i32) {
    let mut lo = nums[0];
    let mut hi = nums[0];
    for &n in nums {
        if n < lo { lo = n; }
        if n > hi { hi = n; }
    }
    (lo, hi)
}

fn main() {
    let (q, r) = divide(17, 5);
    println!("الناتج {q} والباقي {r}");
    let (lo, hi) = min_max(&[7, 2, 9, 4]);
    println!("{lo} {hi}");
}
```

```text output
الناتج 3 والباقي 2
2 9
```

`&[i32]` تعني «نظرة على قائمة أعداد» (شريحة)، وسنفهم `&` جيدًا في الدرس القادم.

## الاستدعاء الذاتي

```rust run
fn factorial(n: u64) -> u64 {
    if n <= 1 { 1 } else { n * factorial(n - 1) }
}

fn fib(n: u32) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => fib(n - 1) + fib(n - 2),
    }
}

fn main() {
    println!("10! = {}", factorial(10));
    let first: Vec<u64> = (0..10).map(fib).collect();
    println!("{:?}", first);
}
```

```text output
10! = 3628800
[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
```

## الإغلاقات (Closures): دوال صغيرة بلا اسم

```rust run
fn main() {
    let double = |x: i32| x * 2;
    let add = |a: i32, b: i32| a + b;
    println!("{} {}", double(5), add(2, 3));

    let rate = 0.14;
    let tax = |price: f64| price * rate;     // تتذكر rate من حولها
    println!("{:.2}", tax(200.0));

    let nums = [1, 2, 3, 4, 5];
    let squares: Vec<i32> = nums.iter().map(|n| n * n).collect();
    println!("{:?}", squares);
}
```

```text output
10 5
28.00
[1, 4, 9, 16, 25]
```

الإغلاق يُكتب بين خطين عموديين `|معاملات| تعبير`، ويستطيع استخدام المتغيرات المحيطة به (مثل `rate`).

## أخطاء شائعة

- **`;` بعد القيمة المرجعة:** `expected i32, found ()`.
- **نسيان نوع المعامل:** `fn f(x)` خطأ؛ اكتب `fn f(x: i32)`.
- **اسم دالة بحروف كبيرة:** تحذير `should have a snake case name`.

## تمارين

### التمرين 1

اكتب دالة `is_even` ترجع `bool`:

```rust exercise
// اكتب is_even هنا

fn main() {
    // println!("{} {}", is_even(4), is_even(7));
}
```

```rust solution
fn is_even(n: i32) -> bool {
    n % 2 == 0
}

fn main() {
    println!("{} {}", is_even(4), is_even(7));
}
```

```text output
true false
```

### التمرين 2

اكتب دالة `max3` ترجع أكبر ثلاثة أعداد، بدون `return`:

```rust exercise
fn max3(a: i32, b: i32, c: i32) -> i32 {
    0 // أكمل
}

fn main() {
    println!("{}", max3(4, 19, 7));
    println!("{}", max3(-1, -5, -3));
}
```

```rust solution
fn max3(a: i32, b: i32, c: i32) -> i32 {
    let m = if a > b { a } else { b };
    if m > c { m } else { c }
}

fn main() {
    println!("{}", max3(4, 19, 7));
    println!("{}", max3(-1, -5, -3));
}
```

```text output
19
-1
```

## اختبر نفسك

```quiz
{"question": "ماذا ترجع الدالة إذا كان آخر سطر فيها `x + 1` بلا فاصلة منقوطة؟", "choices": ["لا شيء", "قيمة x + 1", "خطأ دائمًا", "صفر"], "answer": 1, "explanation": "التعبير الأخير بلا ; هو القيمة المرجعة."}
```

```quiz
{"question": "ما معنى `-> f64` في تعريف الدالة؟", "choices": ["المعامل من نوع f64", "الدالة ترجع قيمة من نوع f64", "الدالة سريعة", "تعليق"], "answer": 1, "explanation": "السهم يحدد نوع القيمة المرجعة."}
```

```quiz
{"question": "كيف يُكتب الإغلاق (closure) الذي يضاعف عددًا؟", "choices": ["fn(x) x*2", "|x| x * 2", "lambda x: x*2", "(x) => x*2"], "answer": 1, "explanation": "الإغلاق في Rust: |معاملات| تعبير."}
```

## الخلاصة

- `fn name(p: Type) -> Ret { ... }`، والأنواع إجبارية.
- آخر تعبير بلا `;` هو القيمة المرجعة.
- الكتل و`if` و`match` تعبيرات تعطي قيمًا.
- الصفوف لإرجاع عدة قيم، والإغلاقات `|x| ...` دوال صغيرة.
