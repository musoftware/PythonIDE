# الدرس 13: الوحدات والـ crates والاختبارات

عندما يكبر البرنامج لا يصح أن يبقى كله في ملف واحد. Rust تنظم الكود في **وحدات** (modules)، وتسمح لك باستخدام آلاف المكتبات الجاهزة (**crates**) من موقع **crates.io**، وفيها نظام **اختبارات** مدمج.

> **تشبيه:** المشروع مثل **مكتبة عامة**: الوحدات هي **الرفوف** (رف للرياضيات، رف للنصوص)، والـ crates الخارجية **كتب استعرتها من مكتبة أخرى**، والاختبارات **أمين المكتبة** الذي يتأكد كل يوم أن كل كتاب في مكانه.

## وحدة داخل نفس الملف

```rust run
mod geometry {
    pub const PI: f64 = 3.14159;

    pub fn circle_area(r: f64) -> f64 {
        PI * r * r
    }

    fn secret() -> i32 {          // خاصة: لا تُرى خارج الوحدة
        42
    }

    pub fn answer() -> i32 {
        secret()                  // داخل الوحدة يمكن استخدامها
    }
}

use geometry::circle_area;        // نختصر الاسم

fn main() {
    println!("{:.2}", geometry::circle_area(1.0));
    println!("{:.2}", circle_area(2.0));
    println!("{}", geometry::answer());
}
```

```text output
3.14
12.57
42
```

- كل شيء داخل الوحدة **خاص** افتراضيًا. نكتب `pub` لما نريد إظهاره.
- نصل للعناصر بـ `::` مثل `geometry::circle_area`، أو نستوردها بـ `use`.

## وحدة في ملف مستقل

في مشروع cargo نضع الوحدة في ملف بجوار `main.rs`، ونعلن عنها بـ `mod اسم;`:

```rust run
// #file: src/main.rs
mod textutil;                     // يبحث المترجم عن src/textutil.rs

fn main() {
    let s = "  مرحبا بكم في Rust  ";
    println!("[{}]", textutil::clean(s));
    println!("{}", textutil::word_count(s));
}

// #file: src/textutil.rs
pub fn clean(s: &str) -> String {
    s.trim().to_string()
}

pub fn word_count(s: &str) -> usize {
    s.split_whitespace().count()
}
```

```text output
[مرحبا بكم في Rust]
4
```

**في الـ IDE:** اضغط بالزر الأيمن على المشروع في **Solution Explorer** (مستكشف الحلول) ← **Add** > **Module...** واكتب `src/textutil.rs` (أو أنشئ الملف في مجلد `src` بأي طريقة؛ الـ IDE تعرض ملفات المشروع كما هي على القرص). ثم أضف السطر `mod textutil;` في `main.rs`. إن نسيته يذكرك rust-analyzer بتحذير «file not included in module tree».

## استخدام crate من crates.io

لنستخدم المكتبة الشهيرة **serde_json** لقراءة وكتابة بيانات JSON.

**الطريقة في الـ IDE:**

1. **Project > Manage Packages...** (مشروع ← إدارة الحزم...).
2. ابحث عن `serde_json` واضغط **Install**. تنفذ الـ IDE الأمر `cargo add serde_json`، فيُضاف السطر إلى `[dependencies]` في `Cargo.toml`.
3. أول بناء يحمّل المكتبة ويترجمها (قد يأخذ دقيقة)، وبعدها يصبح سريعًا.

وهذا هو المشروع كاملًا (ملفان):

```rust run
// #file: Cargo.toml
[package]
name = "lesson"
version = "0.1.0"
edition = "2021"

[dependencies]
serde_json = "1"

// #file: src/main.rs
use serde_json::{json, Value};

fn main() {
    // إنشاء JSON بالماكرو json!
    let student = json!({
        "name": "مريم",
        "marks": [90, 85, 77]
    });
    println!("{}", student["name"]);
    println!("{}", student.to_string());

    // قراءة JSON من نص
    let text = r#"{"city": "القاهرة", "temp": 31.5}"#;
    let v: Value = serde_json::from_str(text).expect("JSON غير صالح");
    println!("{} = {}", v["city"].as_str().unwrap(), v["temp"].as_f64().unwrap());

    let total: i64 = student["marks"].as_array().unwrap().iter().map(|m| m.as_i64().unwrap()).sum();
    println!("مجموع الدرجات = {total}");
}
```

```text output
"مريم"
{"marks":[90,85,77],"name":"مريم"}
القاهرة = 31.5
مجموع الدرجات = 252
```

> **ملاحظة:** `r#"..."#` نص **خام**: علامات التنصيص داخله لا تحتاج هروبًا بـ `\"`. مفيد جدًا مع JSON.

## الاختبارات المدمجة

نكتب الاختبارات في وحدة عليها `#[cfg(test)]`، وكل اختبار دالة عليها `#[test]`:

```rust run
fn is_even(n: i32) -> bool {
    n % 2 == 0
}

fn factorial(n: u64) -> u64 {
    (1..=n).product()
}

fn main() {
    println!("{} {}", is_even(4), factorial(5));
}

#[cfg(test)]
mod tests {
    use super::*;                 // نستورد دوال الملف الأب

    #[test]
    fn even_numbers() {
        assert!(is_even(10));
        assert!(!is_even(7));
    }

    #[test]
    fn factorial_works() {
        assert_eq!(factorial(0), 1);
        assert_eq!(factorial(5), 120);
    }
}
```

```text output
true 120
```

`#[cfg(test)]` تعني أن هذه الوحدة **لا تدخل** في البرنامج العادي؛ تُترجم فقط عند تشغيل الاختبارات، فلا تزيد حجم برنامجك.

### تشغيل الاختبارات في الـ IDE

- افتح **Test Explorer** (مستكشف الاختبارات) من قائمة **Test**؛ تظهر فيه الاختبارات `even_numbers` و`factorial_works`، فاضغط **Run All**.
- أو اختر من مربع الأهداف أعلى النافذة الهدف `test: all` واضغط **Ctrl+F5** فيُنفذ `cargo test`.
- فوق كل دالة `#[test]` يظهر رابط صغير **Run Test** من rust-analyzer لتشغيل اختبار واحد.

ستظهر نتيجة مثل:

```text
running 2 tests
test tests::even_numbers ... ok
test tests::factorial_works ... ok

test result: ok. 2 passed; 0 failed
```

لو فشل `assert_eq!` تعرض الرسالة القيمتين `left` و`right` لترى الفرق.

## أخطاء شائعة

| الرسالة | السبب | الحل |
|---|---|---|
| `function circle_area is private` | نسيت `pub` | أضف `pub` قبل `fn` |
| `file not found for module textutil` | الملف ليس في `src/` أو اسمه مختلف | تأكد من `src/textutil.rs` |
| `unresolved import serde_json` | المكتبة ليست في `Cargo.toml` | **Manage Packages** أو `cargo add serde_json` |
| `failed to download` | لا يوجد إنترنت عند أول بناء | اتصل بالإنترنت مرة واحدة؛ بعدها تُحفظ المكتبة محليًا |

## تمرين

### التمرين 1

انقل الدالة `square` إلى وحدة `math` واجعلها عامة، ثم استدعها من `main`:

```rust exercise
fn square(x: i32) -> i32 {
    x * x
}

fn main() {
    println!("{}", math::square(9));
}
```

```rust solution
mod math {
    pub fn square(x: i32) -> i32 {
        x * x
    }
}

fn main() {
    println!("{}", math::square(9));
}
```

```text output
81
```

## اختبر نفسك

```quiz
{"question": "ما حالة الدالة داخل mod إذا لم تكتب قبلها pub؟", "choices": ["عامة", "خاصة بالوحدة", "محذوفة", "ثابتة"], "answer": 1, "explanation": "كل شيء خاص افتراضيًا، وpub تجعله مرئيًا خارج الوحدة."}
```

```quiz
{"question": "أين تُكتب المكتبات الخارجية التي يستخدمها المشروع؟", "choices": ["main.rs", "قسم [dependencies] في Cargo.toml", "ملف README", "Cargo.lock يدويًا"], "answer": 1, "explanation": "cargo add يضيفها إلى [dependencies] في Cargo.toml."}
```

```quiz
{"question": "ماذا تعني #[cfg(test)] فوق وحدة الاختبارات؟", "choices": ["تُشغل دائمًا", "تُترجم فقط عند تشغيل الاختبارات", "تمنع الاختبارات", "تجعلها عامة"], "answer": 1, "explanation": "لا تدخل في البرنامج العادي، فقط في cargo test."}
```

## الخلاصة

- `mod` ينظم الكود، و`pub` يظهر ما تريده، و`use` يختصر الأسماء.
- الوحدة في ملف: `mod name;` + `src/name.rs`.
- الـ crates من crates.io عبر **Manage Packages** أو `cargo add`.
- `#[test]` و`assert_eq!` للاختبارات، وتشغيلها من **Test Explorer**.
