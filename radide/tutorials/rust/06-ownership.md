# الدرس 6: الملكية والاستعارة: قلب Rust

هذا أهم درس في الدورة. **الملكية** (ownership) هي الفكرة التي تجعل Rust آمنة بلا جامع قمامة. قد تبدو غريبة في البداية، لكنها مبنية على ثلاث قواعد بسيطة، وبعد أن تفهمها ستكتب كودًا أكثر أمانًا في أي لغة.

## المشكلة التي تحلها Rust

في C رأينا مشاكل الذاكرة: نسيان `free` (تسرب)، أو `free` مرتين، أو استخدام ذاكرة بعد تحريرها. لغات مثل Java وPython تحلها بـ **جامع القمامة** الذي يعمل في الخلفية ويبطئ البرنامج قليلًا. أما Rust فتحلها **وقت الترجمة** بقواعد الملكية.

## قواعد الملكية الثلاث

1. كل قيمة لها **مالك** واحد (متغير).
2. لا يوجد إلا **مالك واحد** في نفس الوقت.
3. عندما يخرج المالك من نطاقه (scope) **تُحرر القيمة تلقائيًا**.

> **تشبيه:** القيمة مثل **كتاب**. له مالك واحد. يمكنك أن **تهديه** لصديق (نقل الملكية)، فيصبح ملكه ولا تستطيع قراءته بعدها. أو أن **تعيره** إياه (استعارة)، فيقرؤه ثم يرجعه وما زال كتابك. وعندما ينتقل صاحب الكتاب من المدينة (يخرج من النطاق) يأخذ كتابه معه تلقائيًا.

## النطاق والتحرير التلقائي

```rust run
fn main() {
    {
        let s = String::from("مرحبا");   // s تملك النص
        println!("{s}");
    }                                    // هنا تخرج s من نطاقها ويُحرر النص تلقائيًا
    println!("انتهى النطاق");
}
```

```text output
مرحبا
انتهى النطاق
```

`String` نص يعيش في الكومة (heap) ويمكن أن يكبر. لا يوجد `free`: Rust تحرره بنفسها في المكان الصحيح.

## النقل (Move)

```rust run
fn main() {
    let a = String::from("كتاب");
    let b = a;                 // انتقلت الملكية من a إلى b
    println!("{b}");
    // println!("{a}");        // خطأ لو أزلنا التعليق: a لم تعد تملك شيئًا
}
```

```text output
كتاب
```

لو أزلت التعليق عن السطر الأخير:

```text
error[E0382]: borrow of moved value: `a`
  |
2 |     let a = String::from("كتاب");
  |         - move occurs because `a` has type `String`, which does not implement the `Copy` trait
3 |     let b = a;
  |             - value moved here
```

لماذا؟ لو بقي `a` و`b` يملكان نفس النص، فعند نهاية الدالة سيُحرر مرتين! Rust تمنع ذلك بنقل الملكية.

### الأنواع البسيطة تُنسخ

الأعداد و`bool` و`char` صغيرة وتُنسخ نسخًا (نوع `Copy`)، فلا مشكلة:

```rust run
fn main() {
    let x = 5;
    let y = x;                 // نسخة
    println!("{x} {y}");
    let s1 = String::from("نص");
    let s2 = s1.clone();       // نسخة عميقة صريحة
    println!("{s1} {s2}");
}
```

```text output
5 5
نص نص
```

`clone()` تنسخ البيانات فعلًا، وهي صريحة لكي ترى أين تحدث النسخ المكلفة.

## الملكية والدوال

تمرير قيمة لدالة **ينقل** ملكيتها:

```rust run
fn take(s: String) {
    println!("أخذت: {s}");
}                               // هنا يُحرر s

fn make() -> String {
    String::from("جديد")        // ترجع الملكية للمستدعي
}

fn main() {
    let s = String::from("هدية");
    take(s);
    // println!("{s}");         // خطأ: s انتقلت إلى take
    let t = make();
    println!("{t}");
}
```

```text output
أخذت: هدية
جديد
```

## الاستعارة (Borrowing) بالمراجع `&`

نقل الملكية في كل استدعاء مزعج. الحل: **نعير** القيمة بمرجع `&`، فتقرؤها الدالة ولا تملكها:

```rust run
fn length(s: &String) -> usize {   // تستعير ولا تملك
    s.chars().count()
}

fn main() {
    let name = String::from("فاطمة");
    let n = length(&name);         // نعيرها
    println!("{name} فيها {n} حروف");   // name ما زالت لنا
}
```

```text output
فاطمة فيها 5 حروف
```

## الاستعارة القابلة للتغيير `&mut`

لكي تعدل الدالة القيمة المستعارة نعطيها `&mut`:

```rust run
fn add_title(s: &mut String) {
    s.push_str(" المحترم");
}

fn double_all(v: &mut Vec<i32>) {
    for x in v.iter_mut() {
        *x *= 2;
    }
}

fn main() {
    let mut name = String::from("الأستاذ أحمد");
    add_title(&mut name);
    println!("{name}");

    let mut nums = vec![1, 2, 3];
    double_all(&mut nums);
    println!("{:?}", nums);
}
```

```text output
الأستاذ أحمد المحترم
[2, 4, 6]
```

`*x` تعني «القيمة التي يشير إليها المرجع x»، مثل المؤشرات في C لكن بأمان كامل.

## قاعدة الاستعارة الذهبية

في أي لحظة يمكنك أن تملك **أحد** الأمرين:

- **عدد غير محدود من المراجع للقراءة** `&T`، أو
- **مرجع واحد فقط للكتابة** `&mut T`.

> **تشبيه:** وثيقة على الطاولة: يمكن لعشرة أشخاص **قراءتها** معًا. لكن إن أراد أحدهم **الكتابة** فيها، يجب أن يأخذها وحده، حتى لا يقرأ أحد نصًا نصف مكتوب.

```rust run
fn main() {
    let mut s = String::from("abc");
    let r1 = &s;
    let r2 = &s;
    println!("{r1} {r2}");     // قراءتان معًا: مسموح
    // آخر استخدام لـ r1 و r2 كان في السطر السابق، فيمكننا الآن الكتابة
    let w = &mut s;
    w.push('d');
    println!("{w}");
}
```

```text output
abc abc
abcd
```

هذه القاعدة تمنع وقت الترجمة نوعًا كاملًا من الأخطاء اسمه **سباق البيانات** (data race)، وهو من أصعب أخطاء البرامج المتزامنة.

## لا مراجع معلقة

Rust لا تسمح أبدًا بمرجع لقيمة حُررت:

<!-- compile-error -->
```rust
fn dangle() -> &String {
    let s = String::from("hi");
    &s
}
```

```text
error[E0106]: missing lifetime specifier
help: ... consider returning an owned value: `String`
```

الحل: أرجع `String` نفسه (انقل الملكية) بدل مرجع إليه.

## أخطاء شائعة وحلولها

| الرسالة | السبب | الحل |
|---|---|---|
| `borrow of moved value` | استخدام متغير بعد نقل ملكيته | مرر `&x` بدل `x`، أو استخدم `.clone()` |
| `cannot borrow as mutable because it is also borrowed as immutable` | قراءة وكتابة في نفس الوقت | أنهِ استخدام مراجع القراءة قبل الكتابة |
| `cannot borrow as mutable, as it is not declared as mutable` | نسيان `mut` | `let mut x` و`&mut x` |

> **نصيحة:** لا تحارب المترجم! عندما يرفض كودك، اقرأ الرسالة، وفكر: «من يملك هذه القيمة الآن؟». ومع الوقت ستكتب الكود الصحيح من أول مرة.

## تمارين

### التمرين 1

صحح الكود لكي يعمل بدون `clone`، بجعل الدالة تستعير النص:

```rust exercise
fn shout(s: String) -> String {
    s.to_uppercase()
}

fn main() {
    let word = String::from("rust");
    let loud = shout(word);
    println!("{word} -> {loud}");
}
```

```rust solution
fn shout(s: &String) -> String {
    s.to_uppercase()
}

fn main() {
    let word = String::from("rust");
    let loud = shout(&word);
    println!("{word} -> {loud}");
}
```

```text output
rust -> RUST
```

### التمرين 2

اكتب دالة `add_bonus` تزيد كل درجة في المتجه بمقدار 5 عبر `&mut`:

```rust exercise
fn add_bonus(marks: &mut Vec<i32>) {
    // أكمل
}

fn main() {
    let mut marks = vec![70, 85, 90];
    add_bonus(&mut marks);
    println!("{:?}", marks);
}
```

```rust solution
fn add_bonus(marks: &mut Vec<i32>) {
    for m in marks.iter_mut() {
        *m += 5;
    }
}

fn main() {
    let mut marks = vec![70, 85, 90];
    add_bonus(&mut marks);
    println!("{:?}", marks);
}
```

```text output
[75, 90, 95]
```

## اختبر نفسك

```quiz
{"question": "بعد `let b = a;` حيث a من نوع String، ماذا يحدث لـ a؟", "choices": ["تبقى صالحة", "تنتقل ملكيتها إلى b ولا يمكن استخدامها", "تصبح نصًا فارغًا", "تُنسخ"], "answer": 1, "explanation": "String تنتقل ملكيتها (move)، وa لم تعد صالحة."}
```

```quiz
{"question": "ما القاعدة الذهبية للاستعارة؟", "choices": ["مراجع كتابة كثيرة", "مراجع قراءة كثيرة أو مرجع كتابة واحد فقط في نفس الوقت", "مرجع واحد دائمًا", "لا قيود"], "answer": 1, "explanation": "إما عدة &T أو &mut T واحد."}
```

```quiz
{"question": "متى تُحرر القيمة في Rust؟", "choices": ["عند استدعاء free", "عندما يخرج مالكها من النطاق", "عندما يعمل جامع القمامة", "لا تُحرر أبدًا"], "answer": 1, "explanation": "Rust تحرر القيمة تلقائيًا عند نهاية نطاق مالكها."}
```

## الخلاصة

- لكل قيمة مالك واحد، وتُحرر عند خروجه من النطاق.
- الإسناد والتمرير **ينقلان** الملكية (إلا للأنواع البسيطة التي تُنسخ).
- `&x` استعارة للقراءة، و`&mut x` استعارة للكتابة.
- عدة قراءات **أو** كتابة واحدة، ولا مراجع معلقة أبدًا.
