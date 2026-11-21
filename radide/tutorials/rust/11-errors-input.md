# الدرس 11: الأخطاء بـ `Result` وقراءة المدخلات

ماذا يحدث إذا كتب المستخدم «abc» بدل رقم؟ أو حاولنا فتح ملف غير موجود؟ هذه **أخطاء متوقعة**، وRust تعاملها بطريقة واضحة جدًا: الدالة التي قد تفشل ترجع **`Result`**.

## `Result`: نجاح أو فشل

```rust
enum Result<T, E> {
    Ok(T),    // نجحت، ومعها النتيجة
    Err(E),   // فشلت، ومعها سبب الفشل
}
```

> **تشبيه:** `Result` مثل **ظرف** يصلك من مكتب البريد: إما فيه **الطرد** الذي طلبته (`Ok`)، أو فيه **ورقة اعتذار** تشرح لماذا لم يصل (`Err`). لا يمكنك أخذ الطرد دون أن تفتح الظرف وتنظر.

```rust run
fn main() {
    let inputs = ["42", "abc", "-7"];
    for s in inputs {
        match s.parse::<i32>() {
            Ok(n) => println!("{s} -> رقم صحيح {n}"),
            Err(e) => println!("{s} -> خطأ: {e}"),
        }
    }
}
```

```text output
42 -> رقم صحيح 42
abc -> خطأ: invalid digit found in string
-7 -> رقم صحيح -7
```

`parse::<i32>()` ترجع `Result<i32, ParseIntError>`. كتبنا النوع بين `::<>` لنخبرها إلى أي نوع تحول.

## دوال ترجع `Result` والعامل `?`

نكتب دوالنا التي قد تفشل لترجع `Result`. والعامل **`?`** اختصار رائع: «إن كان `Err` فارجع به فورًا من الدالة، وإن كان `Ok` فأعطني ما بداخله».

```rust run
fn divide(a: f64, b: f64) -> Result<f64, String> {
    if b == 0.0 {
        return Err(String::from("لا يمكن القسمة على صفر"));
    }
    Ok(a / b)
}

fn average_of(text: &str) -> Result<f64, String> {
    let mut sum = 0.0;
    let mut count = 0.0;
    for part in text.split(',') {
        let n: f64 = part.trim().parse().map_err(|_| format!("«{}» ليس رقمًا", part.trim()))?;
        sum += n;
        count += 1.0;
    }
    divide(sum, count)
}

fn main() {
    println!("{:?}", divide(10.0, 4.0));
    println!("{:?}", divide(1.0, 0.0));
    match average_of("10, 20, 30") {
        Ok(v) => println!("المتوسط {v}"),
        Err(e) => println!("خطأ: {e}"),
    }
    match average_of("10, س, 30") {
        Ok(v) => println!("المتوسط {v}"),
        Err(e) => println!("خطأ: {e}"),
    }
}
```

```text output
Ok(2.5)
Err("لا يمكن القسمة على صفر")
المتوسط 20
خطأ: «س» ليس رقمًا
```

- `map_err` تحول نوع الخطأ (هنا من `ParseFloatError` إلى `String` برسالة عربية).
- `?` يعمل فقط داخل دالة ترجع `Result` (أو `Option`).

## `panic!`: الأخطاء غير المتوقعة

`panic!` يوقف البرنامج فورًا. نستخدمه للأخطاء التي **لا يجب أن تحدث أبدًا** (خطأ برمجي)، وليس لأخطاء المستخدم.

| الموقف | استخدم |
|---|---|
| المستخدم كتب رقمًا خطأ | `Result` واطلب منه الإعادة |
| ملف قد لا يكون موجودًا | `Result` |
| حالة مستحيلة منطقيًا (خطأ في كودك) | `panic!` أو `unwrap()` أو `expect("سبب")` |

## قراءة المدخلات من لوحة المفاتيح

نقرأ سطرًا بـ `std::io::stdin().read_line`:

```rust run
use std::io;

fn main() {
    println!("ما اسمك؟");
    let mut name = String::new();
    io::stdin().read_line(&mut name).expect("تعذرت القراءة");
    let name = name.trim();                 // نحذف سطر Enter في آخر النص

    println!("كم عمرك؟");
    let mut line = String::new();
    io::stdin().read_line(&mut line).expect("تعذرت القراءة");
    match line.trim().parse::<u32>() {
        Ok(age) => println!("أهلًا {name}، بعد 10 سنوات سيكون عمرك {}", age + 10),
        Err(_) => println!("العمر يجب أن يكون رقمًا"),
    }
}
```

```text input
نور
25
```

```text output
ما اسمك؟
كم عمرك؟
أهلًا نور، بعد 10 سنوات سيكون عمرك 35
```

> **في الـ IDE:** عند التشغيل بـ **Ctrl+F5** تظهر نافذة طرفية تكتب فيها المدخلات. وفي صفحة الدرس يأخذ زر «تحقق» المدخلات من مربع `text input` تلقائيًا.

`trim()` مهمة جدًا: `read_line` تحفظ زر Enter (`\n`) في آخر النص، و`"25\n".parse()` تفشل!

## قراءة عدة أرقام حتى نهاية الإدخال

```rust run
use std::io::{self, BufRead};

fn main() {
    let mut total = 0;
    let mut bad = 0;
    for line in io::stdin().lock().lines() {
        let line = line.unwrap();
        match line.trim().parse::<i32>() {
            Ok(n) => total += n,
            Err(_) => bad += 1,
        }
    }
    println!("المجموع = {total}، أسطر خاطئة = {bad}");
}
```

```text input
5
10
خمسة
20
```

```text output
المجموع = 35، أسطر خاطئة = 1
```

## أخطاء شائعة

- **نسيان `trim()`:** التحويل يفشل بخطأ `invalid digit found in string` حتى لو كتبت رقمًا صحيحًا.
- **استخدام `?` في `main` العادية:** خطأ `the ? operator can only be used in a function that returns Result`. إما أن تستخدم `match`، أو تجعل `main` ترجع `Result<(), Box<dyn std::error::Error>>`.
- **`unwrap()` على مدخلات المستخدم:** البرنامج ينهار عند أول خطأ كتابة. عالج `Err` بلطف.

## تمارين

### التمرين 1

اكتب دالة `safe_sqrt` ترجع `Err` برسالة «رقم سالب» إن كان الرقم سالبًا، وإلا `Ok` بالجذر:

```rust exercise
fn safe_sqrt(x: f64) -> Result<f64, String> {
    // أكمل
    Ok(0.0)
}

fn main() {
    for x in [16.0, -4.0] {
        match safe_sqrt(x) {
            Ok(r) => println!("جذر {x} = {r}"),
            Err(e) => println!("{x}: {e}"),
        }
    }
}
```

```rust solution
fn safe_sqrt(x: f64) -> Result<f64, String> {
    if x < 0.0 {
        return Err(String::from("رقم سالب"));
    }
    Ok(x.sqrt())
}

fn main() {
    for x in [16.0, -4.0] {
        match safe_sqrt(x) {
            Ok(r) => println!("جذر {x} = {r}"),
            Err(e) => println!("{x}: {e}"),
        }
    }
}
```

```text output
جذر 16 = 4
-4: رقم سالب
```

### التمرين 2

اقرأ رقمين من سطرين واطبع حاصل ضربهما. إن لم يكن أحدهما رقمًا اطبع «إدخال غير صحيح»:

```rust exercise
use std::io;

fn read_num() -> Result<i64, String> {
    let mut s = String::new();
    io::stdin().read_line(&mut s).map_err(|e| e.to_string())?;
    // حوّل s إلى رقم وارجع النتيجة
    Ok(0)
}

fn main() {
    // اقرأ رقمين واطبع حاصل الضرب
}
```

```rust solution
use std::io;

fn read_num() -> Result<i64, String> {
    let mut s = String::new();
    io::stdin().read_line(&mut s).map_err(|e| e.to_string())?;
    s.trim().parse::<i64>().map_err(|e| e.to_string())
}

fn main() {
    match (read_num(), read_num()) {
        (Ok(a), Ok(b)) => println!("{a} × {b} = {}", a * b),
        _ => println!("إدخال غير صحيح"),
    }
}
```

```text input
6
7
```

```text output
6 × 7 = 42
```

## اختبر نفسك

```quiz
{"question": "ماذا يفعل العامل ? بعد قيمة Result؟", "choices": ["يطبع الخطأ", "يرجع Err من الدالة فورًا أو يعطي قيمة Ok", "يتجاهل الخطأ", "يوقف البرنامج"], "answer": 1, "explanation": "? ينشر الخطأ للمستدعي، أو يفك قيمة Ok."}
```

```quiz
{"question": "لماذا نكتب trim() بعد read_line؟", "choices": ["لتسريع القراءة", "لحذف \\n ومسافات الطرفين قبل التحويل", "لتحويل النص لرقم", "لا داعي لها"], "answer": 1, "explanation": "read_line تحفظ سطر Enter في آخر النص، والتحويل يفشل بسببه."}
```

```quiz
{"question": "متى تستخدم panic!؟", "choices": ["عندما يكتب المستخدم إدخالًا خطأ", "عند خطأ برمجي لا يجب أن يحدث أبدًا", "في كل دالة", "بدل Result دائمًا"], "answer": 1, "explanation": "الأخطاء المتوقعة تُعالج بـ Result، وpanic! للحالات المستحيلة."}
```

## الخلاصة

- الدوال التي قد تفشل ترجع `Result<T, E>`: `Ok(قيمة)` أو `Err(سبب)`.
- `?` ينشر الخطأ للمستدعي بسطر واحد، و`map_err` تغير شكل الخطأ.
- `stdin().read_line(&mut s)` ثم `s.trim().parse()` لقراءة الأرقام.
- `panic!` و`unwrap` للأخطاء البرمجية فقط.
