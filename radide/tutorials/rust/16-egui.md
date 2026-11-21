# الدرس 16: تطبيق سطح مكتب بمكتبة egui (المشروع الختامي)

في الدرس السابق رسمنا النافذة في مصمم النماذج. هناك طريقة ثانية شائعة جدًا في عالم Rust: أن **تصف** الواجهة بالكود نفسه باستخدام مكتبة **egui**. وفي هذا الدرس الختامي نبني بها تطبيقًا صغيرًا لإدارة المهام يجمع أغلب ما تعلمناه في الدورة.

## ما هي egui؟

egui مكتبة واجهات من نوع **الوضع الفوري** (immediate mode): في كل إطار (حوالي 60 مرة في الثانية عند الحاجة) تُستدعى دالتك `update`، فتكتب فيها «اعرض عنوانًا، ثم مربع نص، ثم زرًا». وإن ضُغط الزر ترجع `clicked()` بـ `true` في نفس السطر.

> **تشبيه:** مصمم النماذج مثل **بناء بيت** بالطوب: تبنيه مرة ويبقى. أما egui فمثل **السبورة**: في كل لحظة تمسحها وترسم الحالة الحالية من جديد بسرعة كبيرة، فتبدو للعين ثابتة. لا تحتاج أن «تحدّث» الأدوات؛ ترسم ما في متغيراتك فقط.

| | مصمم النماذج (GUI Bridge) | egui |
|---|---|---|
| تصميم الواجهة | بالسحب والإفلات | بالكود |
| الأحداث | دوال `btnX_Click` | `if ui.button(...).clicked()` |
| الحالة | خصائص الأدوات | حقول هيكل `App` |
| الملف الناتج | برنامج يعمل مع الـ IDE | ملف `exe` مستقل تمامًا |

## إنشاء المشروع

1. **File ← New Project...** ← **Native** ← **Rust (Cargo)**.
2. اختر القالب **egui Desktop App** وسمّه `todo_app`.
3. تنشئ الـ IDE `Cargo.toml` وفيه `eframe = "0.31"`، و`src/main.rs` فيه تطبيق تجريبي.
4. اضغط **Ctrl+F5**. **أول بناء** يحمّل eframe ومكتباتها ويترجمها، وقد يستغرق بضع دقائق (يلزم اتصال بالإنترنت مرة واحدة). البناءات التالية سريعة.

## أصغر تطبيق egui

```rust run
// #file: Cargo.toml
[package]
name = "hello_egui"
version = "0.1.0"
edition = "2021"

[dependencies]
eframe = "0.31"

// #file: src/main.rs
use eframe::egui;

fn main() -> eframe::Result {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default().with_inner_size([320.0, 160.0]),
        ..Default::default()
    };
    eframe::run_native("مرحبا egui", options, Box::new(|_cc| Ok(Box::new(Hello::default()))))
}

#[derive(Default)]
struct Hello {
    clicks: u32,
}

impl eframe::App for Hello {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("Hello, egui!");
            if ui.button("Click me").clicked() {
                self.clicks += 1;
            }
            ui.label(format!("Clicks: {}", self.clicks));
        });
    }
}
```

اقرأ الكود هكذا:

- `main` تفتح نافذة بحجم 320×160 وتعطيها كائنًا من نوع `Hello`.
- `Hello` هيكل يحفظ **الحالة** (عدد الضغطات). `#[derive(Default)]` تعطينا `Hello::default()` بقيمة صفر.
- نطبق السمة `eframe::App` (تذكر الدرس 12!) بكتابة التابع `update`.
- داخل `update` نرسم: عنوان، زر، نص. عند الضغط نزيد العداد، وفي الإطار التالي يظهر الرقم الجديد.

> **ملاحظة عن العربية:** الخط الافتراضي في egui لا يحتوي الحروف العربية، لذلك كتبنا نصوص الأزرار بالإنجليزية. يمكن تحميل خط عربي (مثل Noto Naskh) عبر `ctx.set_fonts(...)`، لكن egui لا تدعم بعدُ تشكيل الحروف العربية واتجاهها بالكامل. إن كانت الواجهة العربية مهمة لك فاستخدم مصمم النماذج من الدرس 15.

## المشروع الختامي: قائمة المهام

التطبيق: مربع لكتابة مهمة، وزر **Add**، وقائمة بالمهام لكل منها مربع اختيار (منجزة أم لا) وزر حذف، وعداد في الأسفل.

```rust run
// #file: Cargo.toml
[package]
name = "todo_app"
version = "0.1.0"
edition = "2021"

[dependencies]
eframe = "0.31"

// #file: src/main.rs
use eframe::egui;

mod tasks;
use tasks::TaskList;

fn main() -> eframe::Result {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default().with_inner_size([420.0, 380.0]).with_title("Todo"),
        ..Default::default()
    };
    eframe::run_native("Todo", options, Box::new(|_cc| Ok(Box::new(App::default()))))
}

#[derive(Default)]
struct App {
    list: TaskList,
    new_title: String,
    message: String,
}

impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("My tasks");

            ui.horizontal(|ui| {
                let edit = ui.text_edit_singleline(&mut self.new_title);
                let enter = edit.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter));
                if ui.button("Add").clicked() || enter {
                    match self.list.add(&self.new_title) {
                        Ok(()) => {
                            self.new_title.clear();
                            self.message.clear();
                        }
                        Err(e) => self.message = e,
                    }
                }
            });
            if !self.message.is_empty() {
                ui.colored_label(egui::Color32::RED, &self.message);
            }
            ui.separator();

            let mut remove: Option<usize> = None;
            egui::ScrollArea::vertical().max_height(220.0).show(ui, |ui| {
                for (i, task) in self.list.items.iter_mut().enumerate() {
                    ui.horizontal(|ui| {
                        ui.checkbox(&mut task.done, &task.title);
                        if ui.small_button("x").clicked() {
                            remove = Some(i);
                        }
                    });
                }
            });
            if let Some(i) = remove {
                self.list.items.remove(i);
            }

            ui.separator();
            ui.label(format!("{} done of {}", self.list.done_count(), self.list.items.len()));
            if ui.button("Clear done").clicked() {
                self.list.clear_done();
            }
        });
    }
}

// #file: src/tasks.rs
//! منطق المهام بعيدًا عن الواجهة: يمكن اختباره بـ cargo test.

#[derive(Debug, Clone)]
pub struct Task {
    pub title: String,
    pub done: bool,
}

#[derive(Default)]
pub struct TaskList {
    pub items: Vec<Task>,
}

impl TaskList {
    pub fn add(&mut self, title: &str) -> Result<(), String> {
        let title = title.trim();
        if title.is_empty() {
            return Err(String::from("Write a task first"));
        }
        if self.items.iter().any(|t| t.title == title) {
            return Err(format!("'{title}' already exists"));
        }
        self.items.push(Task { title: title.to_string(), done: false });
        Ok(())
    }

    pub fn done_count(&self) -> usize {
        self.items.iter().filter(|t| t.done).count()
    }

    pub fn clear_done(&mut self) {
        self.items.retain(|t| !t.done);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn add_and_clear() {
        let mut l = TaskList::default();
        assert!(l.add("  ").is_err());
        l.add("read").unwrap();
        l.add("code").unwrap();
        assert!(l.add("read").is_err());
        l.items[0].done = true;
        assert_eq!(l.done_count(), 1);
        l.clear_done();
        assert_eq!(l.items.len(), 1);
    }
}
```

### ماذا استخدمنا من الدورة؟

| الفكرة | أين في المشروع |
|---|---|
| الهياكل و`impl` (الدرس 8) | `Task` و`TaskList` و`App` |
| `Option` و`if let` (الدرس 9) | المتغير `remove` |
| `Vec` والمكرِّرات (الدرس 10) | `iter_mut` و`filter` و`retain` و`any` |
| `Result` (الدرس 11) | `add` ترجع `Err` برسالة |
| السمات (الدرس 12) | `impl eframe::App for App` |
| الوحدات والاختبارات (الدرس 13) | `mod tasks;` و`#[test]` |
| الاستعارة (الدرس 6) | `&mut self.new_title` و`&mut task.done` |

لاحظ الفكرة المهمة: **فصلنا المنطق عن الواجهة**. كل قواعد المهام في `tasks.rs`، ويمكن اختبارها بـ **Test Explorer** دون فتح أي نافذة. وملف `main.rs` يهتم بالرسم فقط.

### المتغير `remove`: لماذا لا نحذف داخل الحلقة؟

داخل `for task in self.list.items.iter_mut()` نستعير المتجه للكتابة. لو حاولنا `self.list.items.remove(i)` داخل الحلقة لرفض المترجم: لا يمكن تعديل المتجه وهو مستعار (قاعدة الاستعارة الذهبية!). لذلك نحفظ رقم العنصر في `remove`، ونحذفه **بعد** انتهاء الحلقة.

## نشر التطبيق

1. اختر **Build Release** من قائمة **Native** (أو نفّذ `cargo build --release`).
2. ستجد الملف في `target\release\todo_app.exe`. هذا ملف **مستقل**: انسخه لأي جهاز Windows وشغّله دون تثبيت Rust.
3. السطر `#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]` في قالب الـ IDE يخفي نافذة الطرفية السوداء في نسخة الإصدار.

## أفكار لتطوير المشروع

- احفظ المهام في ملف عند الإغلاق بـ `std::fs::write` واقرأها عند الفتح (يمكنك استخدام `serde_json` من الدرس 13).
- أضف مربع بحث يعرض فقط المهام التي تحتوي النص المكتوب (`filter` و`contains`).
- أضف أولوية للمهمة بتعداد `enum Priority { Low, Normal, High }` واعرضها بألوان مختلفة.

## أخطاء شائعة

- **البناء الأول بطيء جدًا:** طبيعي؛ eframe مكتبة كبيرة تُترجم مرة واحدة. لا توقف البناء.
- **`failed to select a version for eframe`:** لا يوجد إنترنت أو الإصدار مكتوب خطأ في `Cargo.toml`.
- **`cannot borrow self.list.items as mutable more than once`:** حذف أو إضافة داخل حلقة على نفس المتجه. استخدم أسلوب المتغير `remove`.
- **مربعات بدل الحروف العربية:** الخط الافتراضي لا يحتوي العربية (راجع الملاحظة أعلاه).

## تمرين

### التمرين 1

أضف إلى `TaskList` تابعًا `pending` يرجع عدد المهام **غير** المنجزة، واعرضه في الواجهة بدل السطر `"{} done of {}"`. ابدأ من هذا الهيكل:

```rust
pub fn pending(&self) -> usize {
    // أكمل
    0
}
```

وهذا الحل لتقارن به بعد أن تجرّب في مشروعك:

```rust
pub fn pending(&self) -> usize {
    self.items.iter().filter(|t| !t.done).count()
}

// وفي update:
ui.label(format!("{} tasks left", self.list.pending()));
```

## اختبر نفسك

```quiz
{"question": "متى تُستدعى الدالة update في تطبيق egui؟", "choices": ["مرة واحدة عند البداية", "في كل إطار يُعاد فيه رسم الواجهة", "عند إغلاق النافذة فقط", "عند الضغط على زر فقط"], "answer": 1, "explanation": "egui من نوع الوضع الفوري: الواجهة تُرسم من جديد في كل إطار."}
```

```quiz
{"question": "كيف تعرف في egui أن الزر ضُغط؟", "choices": ["دالة btnX_Click", "if ui.button(\"...\").clicked()", "حدث OnClick", "msgbox"], "answer": 1, "explanation": "ui.button ترجع Response، وclicked() تكون true في الإطار الذي ضُغط فيه."}
```

```quiz
{"question": "لماذا وضعنا منطق المهام في tasks.rs منفصلًا عن الواجهة؟", "choices": ["لأن egui تشترط ذلك", "لكي نختبره بـ cargo test دون فتح نافذة ويبقى الكود منظمًا", "لتسريع الرسم", "لا سبب"], "answer": 1, "explanation": "فصل المنطق عن الواجهة يجعل الكود قابلًا للاختبار وأسهل في الصيانة."}
```

## الخلاصة وماذا بعد؟

- egui تصف الواجهة بالكود، والحالة في حقول هيكل يطبق `eframe::App`.
- القالب **egui Desktop App** في الـ IDE يجهز كل شيء، و**Build Release** يعطيك `exe` مستقلًا.
- افصل المنطق عن الواجهة واختبره.

**مبروك! أنهيت دورة Rust.** تعلمت المتغيرات والدوال والملكية والاستعارة والهياكل والتعدادات والمجموعات والأخطاء والسمات والوحدات والاختبارات، وبنيت نافذتين بطريقتين مختلفتين. خطوتك التالية: كتاب **The Rust Programming Language** المجاني (اكتب `rustup doc --book` في الطرفية)، وتصفح crates.io لتكتشف آلاف المكتبات.
