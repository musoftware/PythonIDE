# الدرس 8: IntelliSense والانتقال إلى التعريف

**في هذا الدرس ستتعلم:**

- الاقتراحات التي تقرؤها الـ IDE **من مشروعك أنت**: أسماء المسارات والقوالب والإعدادات والترجمات وأعمدة الجداول.
- اقتراحات Blade: التوجيهات والمكونات وخصائصها والمتغيرات.
- **F12** و**Ctrl+نقر** للانتقال من نص مثل `'books.index'` إلى ملفه.
- ملفات **IDE Helper** ولماذا تحسّن الاقتراحات.

## IntelliSense يعرف مشروعك

محرر PHP في RAD IDE يعمل مع خادم اللغة **intelephense** (الدوال والأصناف والمتغيرات). وفوقه طبقة **خاصة بـ Laravel** تقرأ ملفات مشروعك وتتحدث **فور** تعديلها: أضف مسارًا أو قالبًا أو مفتاح إعداد أو عمودًا في ترحيل، فيظهر في الاقتراحات مباشرة.

جرّب في أي متحكم أو قالب، والمؤشر داخل علامات التنصيص:

| تكتب | تقترح الـ IDE |
|---|---|
| `route('` | أسماء المسارات: `books.index` و`books.edit`... |
| `view('` | أسماء القوالب: `books.index` و`layouts.app`... |
| `config('` ثم `config('app.` | ملفات الإعدادات ثم مفاتيحها |
| `__('` أو `trans('` | مفاتيح الترجمة من `lang/` |
| `env('` | مفاتيح ملف `.env` |
| `asset('` | ملفات مجلد `public` |
| `$book->` | أعمدة الجدول (من الترحيلات أو من قاعدة SQLite نفسها) والعلاقات (`category`) والـ accessors |
| `Book::` | دوال الاستعلام والـ scopes الخاصة بك |
| `Book::where('` | أسماء الأعمدة |
| `->with('` | أسماء العلاقات |
| `'title' => 'required` ثم الفاصل العمودي (في قواعد التحقق) | قواعد التحقق: `string` و`max:` و`unique:`... |

## في قوالب Blade

ملفات `.blade.php` تفتح بلغة **Blade**، وفيها:

- اكتب `@fo` فتظهر `@foreach` و`@forelse` و`@for`... بقوالبها الكاملة.
- اكتب `<x-` فتظهر مكوناتك (`<x-alert>` و`<x-book-card>`...)، وبعد اسم المكون ومسافة تظهر **خصائصه** (`type`...).
- اكتب `{{ $` فتظهر **المتغيرات التي يمررها المتحكم** لهذا القالب (`$books` و`$q`)، وداخل `@foreach ($books as $book)` تعمل `$book->` بأعمدة الكتاب.
- و**Emmet** يعمل كما في HTML: `ul>li*3` ثم Tab.

## F12: من النص إلى الملف

ضع المؤشر على أي من هذه النصوص واضغط **F12** (**Go to Definition** - الانتقال إلى التعريف) أو **Ctrl+نقر**:

| على | يفتح |
|---|---|
| `view('books.index')` | `resources/views/books/index.blade.php` |
| `route('books.show')` | السطر الذي عُرّف فيه المسار في `routes/web.php` |
| `config('app.name')` | السطر في `config/app.php` |
| `__('messages.saved')` | السطر في ملف الترجمة |
| `env('APP_KEY')` | السطر في `.env` |
| `<x-alert>` في Blade | ملف المكون |

وباقي الكلمات (أسماء الأصناف والدوال) تذهب إلى تعريفها بالطريقة العادية عبر intelephense. ومع أوامر الزر الأيمن من الدرس 2 (**Open the Controller That Renders It** و**Open Migration**...) لن تبحث عن ملف يدويًا تقريبًا.

## كيف تعرف الـ IDE أسماء المسارات؟

تقرأ ملفات `routes/*.php` وتبحث عن `->name('...')`، وتسأل `artisan route:list` أيضًا. هذه محاكاة مبسطة للقراءة الأولى بتعبير نمطي:

```php run
<?php
$webPhp = <<<'PHP'
Route::get('/', [HomeController::class, 'index'])->name('home');
Route::get('/books', [BookController::class, 'index'])->name('books.index');
Route::post('/books', [BookController::class, 'store'])->name('books.store');
Route::get('/about', fn() => view('about'));
PHP;

preg_match_all("/Route::(\w+)\('([^']+)'.*?->name\('([^']+)'\)/", $webPhp, $m, PREG_SET_ORDER);
foreach ($m as [$all, $method, $uri, $name]) {
    printf("%-12s %-6s %s\n", $name, strtoupper($method), $uri);
}
echo "مسارات بلا اسم: ", substr_count($webPhp, "Route::") - count($m), "\n";
```

```text output
home         GET    /
books.index  GET    /books
books.store  POST   /books
مسارات بلا اسم: 1
```

(المسار بلا اسم لا يظهر في اقتراحات `route('`؛ سبب إضافي لتسمية مساراتك.)

## ملفات IDE Helper

بعض ميزات Laravel «سحرية» يصعب على أي محرر فهمها وحده: الواجهات (Facades) مثل `Cache::` و`Auth::`، والأعمدة كخصائص في النماذج. الحزمة **barryvdh/laravel-ide-helper** تولّد ملفات وصفية (`_ide_helper.php` و`_ide_helper_models.php` و`.phpstorm.meta.php`) يقرؤها intelephense.

- عند إنشاء المشروع من الـ IDE تُثبّت تلقائيًا (خانة **Install laravel-ide-helper**).
- بعد إضافة نماذج أو أعمدة جديدة: **Laravel > Regenerate IDE Helper Files** (إعادة توليد ملفات IDE Helper)، أو زر **IDE Helper** في لوحة Laravel، أو لوحة الأوامر **Laravel: Generate IDE Helper Files**. وإن لم تكن الحزمة مثبتة تعرض الـ IDE تثبيتها كحزمة تطوير (`composer require --dev`).

## إن لم تظهر الاقتراحات

- ثبّت خوادم اللغات مرة واحدة: **Tools > Install Web Language Servers (HTML/CSS/JSON/PHP/JS/TS)**.
- تأكد أن الملف بلغته الصحيحة: القوالب يجب أن تنتهي بـ `.blade.php`. ويمكن التغيير من **Edit > Language Mode...**.
- `vendor/` غير موجود؟ جهّز المشروع (**Laravel > Prepare Project**)؛ بعض الاقتراحات تحتاج تشغيل `artisan`.

## اختبر نفسك

```quiz
{"question": "ماذا تقترح الـ IDE عند كتابة route(' ؟", "choices": ["أسماء الملفات", "أسماء المسارات المعرّفة في مشروعك", "دوال PHP", "لا شيء"], "answer": 1, "explanation": "تقرأ الـ IDE المسارات من routes/*.php و route:list وتقترح أسماءها."}
```

```quiz
{"question": "ما الذي يفعله F12 على النص 'books.index' داخل view(...)؟", "choices": ["يحذف القالب", "يفتح ملف القالب resources/views/books/index.blade.php", "يشغّل الموقع", "ينسخ النص"], "answer": 1, "explanation": "الانتقال إلى التعريف يعمل على نصوص Laravel مثل القوالب والمسارات والإعدادات."}
```

```quiz
{"question": "متى تعيد توليد ملفات IDE Helper؟", "choices": ["كل دقيقة", "بعد إضافة نماذج أو أعمدة أو حزم جديدة", "قبل كل تشغيل", "أبدًا"], "answer": 1, "explanation": "الملفات تصف النماذج والواجهات؛ حدّثها عندما تتغير."}
```

## الخلاصة

- اقتراحات من مشروعك: `route('` و`view('` و`config('` و`__('` و`env('` و`asset('` و`$model->` وقواعد التحقق.
- في Blade: التوجيهات، و`<x-` بالمكونات وخصائصها، ومتغيرات المتحكم.
- **F12 / Ctrl+نقر** من النص إلى الملف والسطر.
- **Regenerate IDE Helper Files** لاقتراحات أدق للواجهات والنماذج.
