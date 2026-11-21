# الدرس 7: النصوص `String` و`&str` والعربية

في Rust نوعان رئيسيان للنصوص، ومعرفة الفرق بينهما تجعل حياتك أسهل كثيرًا:

| | `String` | `&str` |
|---|---|---|
| ما هو؟ | نص **مملوك** يمكن أن يكبر ويتغير | **نظرة** (استعارة) على نص موجود |
| أين يعيش؟ | في الكومة (heap) | في أي مكان (داخل String أو داخل البرنامج نفسه) |
| مثال | `String::from("سلام")` | `"سلام"` |

> **تشبيه:** `String` مثل **دفتر تملكه**: تكتب فيه وتضيف صفحات. و`&str` مثل **صورة لصفحة** من دفتر أو كتاب: تقرؤها لكنك لا تملك الأصل.

## إنشاء النصوص وتعديلها

```rust run
fn main() {
    let fixed: &str = "مرحبا";                   // نص ثابت داخل البرنامج
    let mut s = String::from("Hello");            // نص مملوك
    s.push_str(", World");                        // إلحاق نص
    s.push('!');                                  // إلحاق حرف
    println!("{fixed} | {s}");

    let a = String::from("Rust");
    let b = String::from(" لغة");
    let c = a + &b;                              // a تنتقل إلى c
    println!("{c}");

    let name = "منى";
    let age = 20;
    let msg = format!("{name} عمرها {age}");     // الطريقة الأوضح للدمج
    println!("{msg}");

    let owned: String = fixed.to_string();        // من &str إلى String
    let view: &str = &owned;                      // من String إلى &str
    println!("{view}");
}
```

```text output
مرحبا | Hello, World!
Rust لغة
منى عمرها 20
مرحبا
```

## اجعل دوالك تأخذ `&str`

الدالة التي تقرأ نصًا فقط تأخذ `&str`، فتقبل الاثنين:

```rust run
fn greet(name: &str) -> String {
    format!("أهلًا يا {name}")
}

fn main() {
    let s = String::from("عمر");
    println!("{}", greet(&s));       // String تتحول تلقائيًا لـ &str
    println!("{}", greet("ليلى"));   // &str مباشرة
}
```

```text output
أهلًا يا عمر
أهلًا يا ليلى
```

## العربية: البايتات والحروف

النصوص في Rust دائمًا **UTF-8**، والحرف العربي فيها بايتان:

```rust run
fn main() {
    let ar = "سلام";
    println!("بايتات: {}", ar.len());
    println!("حروف: {}", ar.chars().count());
    for ch in ar.chars() {
        print!("[{ch}]");
    }
    println!();
    let first = ar.chars().next().unwrap();
    println!("الحرف الأول: {first}");
    let reversed: String = ar.chars().rev().collect();
    println!("معكوس: {reversed}");
}
```

```text output
بايتات: 8
حروف: 4
[س][ل][ا][م]
الحرف الأول: س
معكوس: مالس
```

- `len()` تعد **البايتات**، و`chars().count()` تعد **الحروف**.
- لا يمكن كتابة `ar[0]` في Rust! المترجم يرفض لأن الفهرس بالبايت قد يقطع حرفًا عربيًا في منتصفه. Rust تحميك من هذا الخطأ الشائع في اللغات الأخرى.

### الشرائح النصية

يمكن أخذ جزء من النص بالبايتات، بشرط أن تكون الحدود عند بداية حرف:

```rust run
fn main() {
    let s = "Hello سلام";
    println!("{}", &s[0..5]);        // أول 5 بايتات
    println!("{}", &s[6..]);         // من البايت 6 حتى النهاية
    let first_two: String = "سلام".chars().take(2).collect();
    println!("{first_two}");         // أول حرفين بأمان
}
```

```text output
Hello
سلام
سل
```

لو كتبت `&"سلام"[0..1]` لتوقف البرنامج برسالة `byte index 1 is not a char boundary`. استخدم `chars()` عندما تتعامل مع الحروف.

## دوال مفيدة

```rust run
fn main() {
    let s = "  Rust is fast, Rust is safe  ";
    let t = s.trim();
    println!("[{t}]");
    println!("{}", t.to_uppercase());
    println!("{}", t.contains("safe"));
    println!("{}", t.starts_with("Rust"));
    println!("{}", t.replace("Rust", "C"));
    println!("{:?}", t.find("fast"));
    let words: Vec<&str> = t.split(", ").collect();
    println!("{:?}", words);
    println!("{}", t.split_whitespace().count());
    let csv = "أحمد,منى,علي";
    for name in csv.split(',') {
        println!("- {name}");
    }
    println!("{}", "=".repeat(10));
}
```

```text output
[Rust is fast, Rust is safe]
RUST IS FAST, RUST IS SAFE
true
true
C is fast, C is safe
Some(8)
["Rust is fast", "Rust is safe"]
6
- أحمد
- منى
- علي
==========
```

`find` ترجع `Some(8)` إن وجدت النص، أو `None` إن لم تجده. هذا هو النوع `Option` الذي سنشرحه في الدرس 9.

## تحويل النص إلى رقم والعكس

```rust run
fn main() {
    let n: i32 = "42".parse().unwrap();
    let x: f64 = "3.5".parse().unwrap();
    println!("{}", n + 1);
    println!("{}", x * 2.0);
    let text = 123.to_string();
    println!("{} حروف", text.len());
    let bad: Result<i32, _> = "abc".parse::<i32>();
    println!("{}", bad.is_err());
}
```

```text output
43
7
3 حروف
true
```

`unwrap()` تعني «أنا متأكد أن التحويل سينجح». إن فشل يتوقف البرنامج. في الدرس 11 نتعلم التعامل مع الفشل بلطف.

## أخطاء شائعة

- **`s[0]`:** غير مسموح؛ استخدم `s.chars().nth(0)`.
- **`len()` لعدد الحروف العربية:** استخدم `chars().count()`.
- **دالة تأخذ `String` وهي تحتاج القراءة فقط:** اجعلها `&str`.
- **`a + b` مع اثنين من نوع String:** الطرف الثاني يجب أن يكون `&b`. والأسهل `format!`.

## تمارين

### التمرين 1

اكتب دالة `initials` ترجع الحرف الأول من كل كلمة (تعمل مع العربية):

```rust exercise
fn initials(name: &str) -> String {
    // استخدم split_whitespace و chars().next()
    String::new()
}

fn main() {
    println!("{}", initials("Grace Brewster Hopper"));
    println!("{}", initials("محمد علي كلاي"));
}
```

```rust solution
fn initials(name: &str) -> String {
    let mut out = String::new();
    for word in name.split_whitespace() {
        if let Some(c) = word.chars().next() {
            out.push(c);
        }
    }
    out
}

fn main() {
    println!("{}", initials("Grace Brewster Hopper"));
    println!("{}", initials("محمد علي كلاي"));
}
```

```text output
GBH
معك
```

### التمرين 2

اكتب دالة `count_char` تعد مرات ظهور حرف معين:

```rust exercise
fn count_char(s: &str, target: char) -> usize {
    0 // أكمل
}

fn main() {
    println!("{}", count_char("banana", 'a'));
    println!("{}", count_char("مدرسة ممتازة", 'م'));
}
```

```rust solution
fn count_char(s: &str, target: char) -> usize {
    s.chars().filter(|&c| c == target).count()
}

fn main() {
    println!("{}", count_char("banana", 'a'));
    println!("{}", count_char("مدرسة ممتازة", 'م'));
}
```

```text output
3
3
```

## اختبر نفسك

```quiz
{"question": "ما الفرق الأساسي بين String و&str؟", "choices": ["لا فرق", "String نص مملوك قابل للتغيير، و&str نظرة مستعارة على نص", "&str أسرع دائمًا", "String للعربية فقط"], "answer": 1, "explanation": "String تملك بياناتها، و&str تستعير."}
```

```quiz
{"question": "ماذا ترجع `\"قلم\".len()`؟", "choices": ["3", "6", "4", "خطأ"], "answer": 1, "explanation": "len تعد البايتات، والحرف العربي بايتان."}
```

```quiz
{"question": "لماذا لا تسمح Rust بـ `s[0]` على النصوص؟", "choices": ["لأنها بطيئة", "لأن الفهرس بالبايت قد يقطع حرفًا متعدد البايتات", "لأن النصوص فارغة", "خطأ في اللغة"], "answer": 1, "explanation": "UTF-8 يجعل الحرف عدة بايتات، فالفهرسة المباشرة غير آمنة."}
```

## الخلاصة

- `String` مملوك ومتغير، و`&str` استعارة؛ اجعل دوالك تأخذ `&str`.
- `format!` أوضح طريقة لدمج النصوص.
- `len()` للبايتات و`chars()` للحروف؛ لا فهرسة مباشرة.
- `parse()` للتحويل لأرقام، و`to_string()` للعكس.
