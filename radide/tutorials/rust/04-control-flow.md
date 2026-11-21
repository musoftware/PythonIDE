# الدرس 4: الشروط والحلقات

## `if` و`else`

```rust run
fn main() {
    let score = 83;
    if score >= 90 {
        println!("ممتاز");
    } else if score >= 80 {
        println!("جيد جدًا");
    } else if score >= 50 {
        println!("ناجح");
    } else {
        println!("راسب");
    }
}
```

```text output
جيد جدًا
```

- لا أقواس حول الشرط، و`{ }` إجبارية.
- الشرط يجب أن يكون `bool` فعلًا: `if score { }` خطأ ترجمة.

## `if` تعبير يرجع قيمة

في Rust، `if` ليست مجرد جملة، بل **تعبير** (expression) يعطي قيمة، فيمكن وضعها في متغير:

```rust run
fn main() {
    let n = 7;
    let kind = if n % 2 == 0 { "زوجي" } else { "فردي" };
    println!("{n} {kind}");

    let temp = 36;
    let advice = if temp > 30 {
        "اشرب ماءً كثيرًا"
    } else {
        "الجو لطيف"
    };
    println!("{advice}");
}
```

```text output
7 فردي
اشرب ماءً كثيرًا
```

لاحظ أنه لا توجد `;` بعد `"زوجي"` و`"فردي"`: السطر الأخير في الكتلة بلا فاصلة منقوطة هو **قيمة** الكتلة. هذه فكرة مهمة سنراها كثيرًا.

## الحلقة اللانهائية `loop`

```rust run
fn main() {
    let mut count = 0;
    let result = loop {
        count += 1;
        if count == 5 {
            break count * 10;     // اخرج وأرجع قيمة
        }
    };
    println!("result = {result}");
}
```

```text output
result = 50
```

## `while`

```rust run
fn main() {
    let mut n = 12345;
    let mut digits = 0;
    while n > 0 {
        n /= 10;
        digits += 1;
    }
    println!("عدد الأرقام: {digits}");
}
```

```text output
عدد الأرقام: 5
```

## `for` والمدى (range)

أكثر حلقة استخدامًا في Rust: تمر على **مدى** من الأرقام أو على عناصر مجموعة:

```rust run
fn main() {
    for i in 1..4 {               // 1 و2 و3 (بدون 4)
        print!("{i} ");
    }
    println!();
    for i in 1..=4 {              // 1 إلى 4 (شامل)
        print!("{i} ");
    }
    println!();
    for i in (1..=3).rev() {      // بالعكس
        print!("{i} ");
    }
    println!("انطلق!");
    for i in (0..10).step_by(3) { // بخطوة 3
        print!("{i} ");
    }
    println!();

    let fruits = ["تفاح", "موز", "عنب"];
    for f in fruits {
        println!("{f}");
    }
    for (i, f) in fruits.iter().enumerate() {
        println!("{i}: {f}");
    }
}
```

```text output
1 2 3 
1 2 3 4 
3 2 1 انطلق!
0 3 6 9 
تفاح
موز
عنب
0: تفاح
1: موز
2: عنب
```

> **تشبيه:** `1..4` مثل **تذكرة دخول من البوابة 1 حتى قبل البوابة 4**، و`1..=4` تذكرة **تشمل** البوابة 4.

## `break` و`continue`، وتسمية الحلقات

```rust run
fn main() {
    let mut sum = 0;
    for i in 1..=10 {
        if i % 2 == 0 {
            continue;
        }
        sum += i;
    }
    println!("مجموع الفردي: {sum}");

    'outer: for a in 1..10 {
        for b in 1..10 {
            if a * b == 42 {
                println!("وجدت: {a} × {b}");
                break 'outer;       // اخرج من الحلقتين
            }
        }
    }
}
```

```text output
مجموع الفردي: 25
وجدت: 6 × 7
```

## `match`: الاختيار الذكي

`match` مثل `switch` في اللغات الأخرى لكنها أقوى بكثير، وسنتعمق فيها في الدرس 9:

```rust run
fn main() {
    for day in [1, 6, 9] {
        let name = match day {
            1 => "السبت",
            2 => "الأحد",
            3..=5 => "وسط الأسبوع",
            6 | 7 => "نهاية الأسبوع",
            _ => "رقم غير صحيح",
        };
        println!("{day}: {name}");
    }
}
```

```text output
1: السبت
6: نهاية الأسبوع
9: رقم غير صحيح
```

- `3..=5` مدى، و`6 | 7` «أو».
- `_` تطابق أي شيء آخر. و`match` **يجب** أن تغطي كل الاحتمالات، وإلا يرفض المترجم البرنامج. هذا يمنعك من نسيان حالة!

## أخطاء شائعة

- **الشرط ليس `bool`:** `if x { }` مع `x` عدد: `expected bool, found integer`.
- **فرعا `if` بنوعين مختلفين** في تعبير: `if c { 5 } else { "five" }` خطأ.
- **`match` لا تغطي كل الحالات:** `non-exhaustive patterns`؛ أضف `_ =>`.
- **الخطأ بواحد في المدى:** `0..n` لا تشمل `n`.

## تمارين

### التمرين 1

FizzBuzz من 1 إلى 15 باستخدام `match` على صف `(i % 3, i % 5)`:

```rust exercise
fn main() {
    for i in 1..=15 {
        // match (i % 3, i % 5) { ... }
        println!("{i}");
    }
}
```

```rust solution
fn main() {
    for i in 1..=15 {
        match (i % 3, i % 5) {
            (0, 0) => println!("FizzBuzz"),
            (0, _) => println!("Fizz"),
            (_, 0) => println!("Buzz"),
            _ => println!("{i}"),
        }
    }
}
```

```text output
1
2
Fizz
4
Buzz
Fizz
7
8
Fizz
Buzz
11
Fizz
13
14
FizzBuzz
```

### التمرين 2

اطبع مثلثًا من النجوم بارتفاع 4 بحلقتي `for`:

```rust exercise
fn main() {
    let height = 4;
    // *
    // **
    // ***
    // ****
    let _ = height;
}
```

```rust solution
fn main() {
    let height = 4;
    for i in 1..=height {
        for _ in 0..i {
            print!("*");
        }
        println!();
    }
}
```

```text output
*
**
***
****
```

## اختبر نفسك

```quiz
{"question": "ما الأرقام التي تمر عليها `for i in 2..5`؟", "choices": ["2 3 4 5", "2 3 4", "3 4 5", "2 5"], "answer": 1, "explanation": "المدى .. لا يشمل الطرف الأخير."}
```

```quiz
{"question": "ما قيمة x في `let x = if true { 1 } else { 2 };`؟", "choices": ["true", "1", "2", "خطأ"], "answer": 1, "explanation": "if تعبير يرجع قيمة الفرع المنفذ."}
```

```quiz
{"question": "لماذا نضع `_ =>` في آخر match؟", "choices": ["للزينة", "لتغطية كل القيم الأخرى لأن match يجب أن تكون شاملة", "لإنهاء البرنامج", "لتجاهل الأخطاء"], "answer": 1, "explanation": "match يجب أن تغطي كل الاحتمالات، و_ تطابق الباقي."}
```

## الخلاصة

- `if` تعبير يرجع قيمة، وشرطه `bool`.
- الحلقات: `loop` (مع `break قيمة`)، و`while`، و`for` على مدى أو مجموعة.
- `a..b` بدون b، و`a..=b` معها.
- `match` اختيار شامل مع أنماط ومدى و`_`.
