# الدرس 10: المجموعات: `Vec` و`HashMap` والمكرِّرات

البرامج الحقيقية تتعامل مع **قوائم** من البيانات: درجات الفصل، أسماء المنتجات، أسعارها. في هذا الدرس نتعلم أهم مجموعتين في Rust، ثم **المكرِّرات** (iterators) التي تجعل معالجة القوائم قصيرة وواضحة.

## المتجه `Vec<T>`: قائمة قابلة للنمو

> **تشبيه:** `Vec` مثل **قطار** يمكنك أن تضيف له عربات في آخره أو تفصلها، وكل العربات من نفس النوع.

```rust run
fn main() {
    let mut marks: Vec<i32> = Vec::new();   // متجه فارغ
    marks.push(70);
    marks.push(85);
    marks.push(92);

    let names = vec!["أحمد", "منى", "سامي"];   // متجه بقيم أولية

    println!("عدد الدرجات: {}", marks.len());
    println!("أول درجة: {}", marks[0]);
    println!("آخر اسم: {}", names[names.len() - 1]);

    marks[1] = 88;                          // تعديل عنصر
    let last = marks.pop();                 // إزالة الأخير (Option)
    println!("{:?} أُزيل {:?}", marks, last);

    for n in &names {                       // المرور بدون أخذ الملكية
        print!("{n} ");
    }
    println!();
    println!("فيها منى؟ {}", names.contains(&"منى"));
}
```

```text output
عدد الدرجات: 3
أول درجة: 70
آخر اسم: سامي
[70, 88] أُزيل Some(92)
أحمد منى سامي 
فيها منى؟ true
```

> **تحذير:** `marks[10]` على متجه فيه 3 عناصر **يوقف البرنامج** (panic) برسالة `index out of bounds`. إن لم تكن متأكدًا استخدم `marks.get(10)` التي ترجع `Option`.

## المكرِّرات: معالجة القائمة في سطر

بدل حلقة طويلة نبني **سلسلة** من العمليات:

```rust run
fn main() {
    let nums = vec![3, 8, 1, 10, 5, 6];

    let total: i32 = nums.iter().sum();
    let max = nums.iter().max().unwrap();
    let evens: Vec<i32> = nums.iter().filter(|&&n| n % 2 == 0).cloned().collect();
    let squares: Vec<i32> = nums.iter().map(|n| n * n).collect();
    let big = nums.iter().filter(|&&n| n > 4).count();

    println!("المجموع {total}، الأكبر {max}");
    println!("الزوجية {:?}", evens);
    println!("المربعات {:?}", squares);
    println!("أكبر من 4: {big}");

    let mut sorted = nums.clone();
    sorted.sort();
    println!("مرتبة {:?}", sorted);
}
```

```text output
المجموع 33، الأكبر 10
الزوجية [8, 10, 6]
المربعات [9, 64, 1, 100, 25, 36]
أكبر من 4: 4
مرتبة [1, 3, 5, 6, 8, 10]
```

| العملية | ماذا تفعل |
|---|---|
| `iter()` | تبدأ المرور على العناصر (بالاستعارة) |
| `map(دالة)` | تحول كل عنصر |
| `filter(شرط)` | تبقي العناصر التي تحقق الشرط |
| `sum()` / `count()` / `max()` | تجمع النتيجة في قيمة واحدة |
| `collect()` | تجمع الناتج في مجموعة جديدة (`Vec` مثلًا) |
| `enumerate()` | تعطي `(رقم, عنصر)` |

`|n| n * n` اسمها **دالة مغلقة** (closure): دالة صغيرة بلا اسم نكتبها في مكانها. ما بين الخطين العموديين هو المعاملات.

> **ملاحظة عن `&&n`:** `iter()` تعطي مراجع `&i32`، و`filter` تعطي مرجعًا لذلك المرجع، لذلك نكتب `|&&n|` لنفك المرجعين ونحصل على الرقم نفسه. إن بدا لك هذا معقدًا فاكتب `|n| **n % 2 == 0` أو اترك rust-analyzer يقترح عليك.

## `HashMap`: قاموس مفتاح وقيمة

> **تشبيه:** `HashMap` مثل **دليل الهاتف**: تبحث بالاسم (المفتاح) فتجد الرقم (القيمة) فورًا دون المرور على كل الصفحات.

```rust run
use std::collections::HashMap;

fn main() {
    let mut prices: HashMap<String, f64> = HashMap::new();
    prices.insert(String::from("شاي"), 15.0);
    prices.insert(String::from("قهوة"), 25.0);
    prices.insert(String::from("عصير"), 20.0);

    match prices.get("قهوة") {
        Some(p) => println!("سعر القهوة {p}"),
        None => println!("غير موجودة"),
    }

    prices.insert(String::from("شاي"), 17.0);       // نفس المفتاح: تحديث
    prices.remove("عصير");

    let mut keys: Vec<&String> = prices.keys().collect();
    keys.sort();                                      // HashMap بلا ترتيب، فنرتب للطباعة
    for k in keys {
        println!("{k} = {}", prices[k]);
    }
}
```

```text output
سعر القهوة 25
شاي = 17
قهوة = 25
```

> **مهم:** ترتيب العناصر داخل `HashMap` **غير مضمون** ويتغير من تشغيل لآخر. إن احتجت ترتيبًا ثابتًا رتّب المفاتيح كما فعلنا، أو استخدم `BTreeMap` التي تحفظ المفاتيح مرتبة.

## عدّ الكلمات بـ `entry`

أشهر استخدام للقاموس: العدّ.

```rust run
use std::collections::BTreeMap;

fn main() {
    let text = "تفاح موز تفاح برتقال موز تفاح";
    let mut count: BTreeMap<&str, u32> = BTreeMap::new();
    for word in text.split_whitespace() {
        *count.entry(word).or_insert(0) += 1;
    }
    for (w, c) in &count {
        println!("{w}: {c}");
    }
}
```

```text output
برتقال: 1
تفاح: 3
موز: 2
```

`entry(word).or_insert(0)` تعني: «أعطني خانة هذه الكلمة، وإن لم تكن موجودة أنشئها بصفر». ثم نزيدها بواحد.

## أخطاء شائعة

| الرسالة | السبب | الحل |
|---|---|---|
| `index out of bounds: the len is 3 but the index is 5` | فهرس خارج القائمة | تحقق من `len()` أو استخدم `get` |
| `cannot borrow as mutable` | `push` على متجه غير `mut` | `let mut v = ...` |
| `a value of type Vec<i32> cannot be built from an iterator over elements of type &i32` | `collect` على مراجع | أضف `.cloned()` أو `.copied()` قبل `collect` |
| `cannot find type HashMap` | نسيان الاستيراد | `use std::collections::HashMap;` |

> **نصيحة من الـ IDE:** مرر الماوس فوق أي متغير فيعرض rust-analyzer نوعه بالضبط (مثل `Vec<&String>`). وفي المحرر تظهر **تلميحات الأنواع** بلون خافت بعد اسم المتغير، فتعرف ماذا ينتج كل سطر في سلسلة المكرِّرات.

## تمارين

### التمرين 1

احسب متوسط الدرجات وعدد الناجحين (الدرجة 50 فأكثر):

```rust exercise
fn main() {
    let marks = vec![45, 78, 90, 33, 66];
    // احسب avg و passed
    let avg = 0.0;
    let passed = 0;
    println!("المتوسط {:.1}، الناجحون {}", avg, passed);
}
```

```rust solution
fn main() {
    let marks = vec![45, 78, 90, 33, 66];
    let total: i32 = marks.iter().sum();
    let avg = total as f64 / marks.len() as f64;
    let passed = marks.iter().filter(|&&m| m >= 50).count();
    println!("المتوسط {:.1}، الناجحون {}", avg, passed);
}
```

```text output
المتوسط 62.4، الناجحون 3
```

### التمرين 2

احسب عدد مرات ظهور كل حرف في الكلمة `"banana"` باستخدام `BTreeMap` واطبعها مرتبة:

```rust exercise
use std::collections::BTreeMap;

fn main() {
    let word = "banana";
    let mut count: BTreeMap<char, u32> = BTreeMap::new();
    // أكمل
    for (ch, n) in &count {
        println!("{ch} {n}");
    }
}
```

```rust solution
use std::collections::BTreeMap;

fn main() {
    let word = "banana";
    let mut count: BTreeMap<char, u32> = BTreeMap::new();
    for ch in word.chars() {
        *count.entry(ch).or_insert(0) += 1;
    }
    for (ch, n) in &count {
        println!("{ch} {n}");
    }
}
```

```text output
a 3
b 1
n 2
```

## اختبر نفسك

```quiz
{"question": "ما الفرق بين v[5] و v.get(5)؟", "choices": ["لا فرق", "v[5] ينهار إن لم يوجد العنصر، وget ترجع Option", "get أسرع", "v[5] ترجع Option"], "answer": 1, "explanation": "الفهرسة المباشرة توقف البرنامج خارج الحدود، أما get فترجع None."}
```

```quiz
{"question": "ما وظيفة collect()؟", "choices": ["تحذف العناصر", "تجمع ناتج المكرِّر في مجموعة جديدة", "ترتب القائمة", "تطبع القائمة"], "answer": 1, "explanation": "collect تحول المكرِّر إلى Vec أو HashMap أو غيرهما."}
```

```quiz
{"question": "أي مجموعة تحفظ المفاتيح مرتبة؟", "choices": ["HashMap", "BTreeMap", "Vec", "Option"], "answer": 1, "explanation": "BTreeMap تبقي المفاتيح مرتبة، وHashMap بلا ترتيب مضمون."}
```

## الخلاصة

- `Vec<T>` قائمة تنمو: `push` و`pop` و`len` و`get`.
- المكرِّرات (`iter` و`map` و`filter` و`sum` و`collect`) تختصر الحلقات.
- `HashMap` و`BTreeMap` قواميس مفتاح وقيمة، و`entry().or_insert()` للعدّ.
