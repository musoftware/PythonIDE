# الدرس 4: قوالب Blade

**في هذا الدرس ستتعلم:**

- إنشاء قالب بأمر **New Blade View...** وتمرير البيانات إليه من المتحكم.
- طباعة القيم بـ `{{ }}` (مع الحماية التلقائية من XSS)، والتوجيهات `@if` و`@foreach` و`@forelse`.
- **التخطيط المشترك** بـ `@extends` و`@section` و`@yield`.
- **المكونات** `<x-...>`، والنماذج مع `@csrf` و`@method`.
- أوامر الـ IDE: لغة Blade في المحرر، و**Open the Controller That Renders It**.

## لماذا Blade؟

في دورة PHP كتبنا HTML مع `<?= htmlspecialchars($x) ?>` و`<?php foreach (...): ?>`. Blade يقدم نفس الفكرة بصيغة **أقصر وأأمن**، ويحوّل القالب في الخلفية إلى PHP عادي (ويحفظه مؤقتًا في `storage/framework/views` ليكون سريعًا).

| PHP عادي | Blade |
|---|---|
| `<?= htmlspecialchars($title) ?>` | `{{ $title }}` |
| `<?php if ($x): ?> ... <?php endif; ?>` | `@if ($x) ... @endif` |
| `<?php foreach ($books as $b): ?>` | `@foreach ($books as $b)` |
| `<?php require 'header.php'; ?>` | `@extends('layouts.app')` أو `@include('partials.header')` |

## أول قالب

1. انقر بالزر الأيمن على `resources/views` ثم **New Blade View...** (قالب Blade جديد...).
2. الاسم بصيغة النقاط: `books.index` (يعني الملف `resources/views/books/index.blade.php`). اترك **Layout** فارغًا الآن.

ملفات `.blade.php` تفتح في المحرر بلغة **Blade**: تلوين للتوجيهات `@...` وللـ `{{ }}` مع HTML. اكتب:

```blade
<h1>الكتب ({{ count($books) }})</h1>

@if (count($books) === 0)
    <p>لا توجد كتب بعد.</p>
@else
    <ul>
        @foreach ($books as $book)
            <li>{{ $loop->iteration }}. {{ $book }}</li>
        @endforeach
    </ul>
@endif
```

والمتحكم من الدرس السابق يمرر البيانات:

```php
return view('books.index', ['books' => $books]);
// أو بصيغة مختصرة إذا كان اسم المتغير مطابقًا:
return view('books.index', compact('books'));
```

افتح `/books` في المعاينة. و`$loop` متغير جاهز داخل `@foreach` فيه `iteration` (رقم الدورة من 1) و`first` و`last` و`count`.

> **من القالب إلى المتحكم:** انقر بالزر الأيمن على `index.blade.php` في Solution Explorer واختر **Open the Controller That Renders It** (فتح المتحكم الذي يعرض هذا القالب): تنقلك الـ IDE إلى سطر `view('books.index')` في المتحكم. والعكس: **F12** على `'books.index'` داخل `view(...)` يفتح القالب.

## {{ }} تحميك تلقائيًا

`{{ $x }}` تمرر القيمة على `htmlspecialchars` **دائمًا**، فلا تنسى الحماية من XSS أبدًا. أما `{!! $x !!}` فتطبع HTML **كما هو** دون حماية؛ لا تستخدمها مع بيانات الزائر. لتفهم الفرق، هذه محاكاة صغيرة لمحرك قوالب يفعل ما يفعله Blade مع هاتين الصيغتين:

```php run
<?php
function render(string $template, array $vars): string
{
    // {!! $name !!} => القيمة كما هي (خطر مع بيانات الزائر)
    $out = preg_replace_callback('/\{!!\s*\$(\w+)\s*!!\}/u',
        fn($m) => (string) ($vars[$m[1]] ?? ''), $template);
    // {{ $name }} => القيمة بعد htmlspecialchars (آمن)
    return preg_replace_callback('/\{\{\s*\$(\w+)\s*\}\}/u',
        fn($m) => htmlspecialchars((string) ($vars[$m[1]] ?? '')), $out);
}

$comment = '<script>alert(1)</script> كتاب رائع';
echo render('<p>{{ $comment }}</p>', ['comment' => $comment]), "\n";
echo render('<p>{!! $comment !!}</p>', ['comment' => $comment]), "\n";
echo render('<b>{{ $count }}</b> كتب', ['count' => 3]), "\n";
```

```text output
<p>&lt;script&gt;alert(1)&lt;/script&gt; كتاب رائع</p>
<p><script>alert(1)</script> كتاب رائع</p>
<b>3</b> كتب
```

## التخطيط المشترك (Layout)

بدل `header.php` و`footer.php` نصنع **تخطيطًا** واحدًا فيه «أماكن فارغة» (`@yield`) تملؤها كل صفحة (`@section`). أنشئ بـ **New Blade View...** القالب `layouts.app`:

```blade
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="utf-8">
    <title>@yield('title', 'مكتبتي')</title>
    @vite(['resources/css/app.css', 'resources/js/app.js'])
</head>
<body>
    <nav>
        <a href="{{ route('books.index') }}">الكتب</a>
        <a href="{{ route('books.create') }}">+ كتاب جديد</a>
    </nav>

    @if (session('status'))
        <p class="flash">{{ session('status') }}</p>
    @endif

    <main>@yield('content')</main>
</body>
</html>
```

ثم أي صفحة تمتد منه. وعند إنشاء قالب جديد بـ **New Blade View...** اكتب في حقل **Layout (@extends, optional)** القيمة `layouts.app` فيُكتب لك هذا الهيكل تلقائيًا:

```blade
@extends('layouts.app')

@section('title', 'الكتب')

@section('content')
    <h1>الكتب</h1>
    ...
@endsection
```

لاحظ `session('status')`: رسالة الفلاش في Laravel جاهزة، تضعها في المتحكم بـ `->with('status', '...')` (الدرس 7).

> **ملاحظة عن @vite:** يربط ملفات CSS و JS التي يبنيها Vite. إن لم تكن قد شغّلت `npm install` و`npm run build` (أو **Laravel > npm > ...**) فاحذف هذا السطر مؤقتًا أو ضع `<link>` عاديًا.

## المكونات <x-...>

**المكوّن** (component) قطعة واجهة قابلة لإعادة الاستخدام بخصائص، مثل تنبيه ملوّن. أنشئه بالزر الأيمن على `resources/views/components` ثم **New Component...** باسم `alert` مع خيار **Anonymous component** (قالب فقط):

```blade
{{-- resources/views/components/alert.blade.php --}}
@props(['type' => 'info'])

<div class="alert alert-{{ $type }}">
    {{ $slot }}
</div>
```

واستخدامه في أي قالب:

```blade
<x-alert type="success">تم حفظ الكتاب بنجاح</x-alert>
<x-alert>معلومة عادية</x-alert>
```

`$slot` هو المحتوى بين وسمي البداية والنهاية. و**IntelliSense** يقترح أسماء المكونات بعد `<x-` وخصائصها بعد المسافة.

## النماذج في Blade

```blade
<form method="POST" action="{{ route('books.store') }}">
    @csrf
    <input name="title" value="{{ old('title') }}">
    @error('title')
        <span class="error">{{ $message }}</span>
    @enderror
    <button>حفظ</button>
</form>

<form method="POST" action="{{ route('books.destroy', $book) }}">
    @csrf
    @method('DELETE')
    <button>حذف</button>
</form>
```

- `@csrf` يضع الحقل المخفي لرمز CSRF (الذي كتبناه بأيدينا في المشروع النهائي لدورة PHP). بدونه يرد Laravel بـ `419 Page Expired`.
- `@method('DELETE')` لأن نماذج HTML لا تعرف إلا GET و POST، فيرسل Laravel الطريقة الحقيقية في حقل مخفي.
- `old('title')` القيمة التي كتبها الزائر قبل فشل التحقق (النموذج اللاصق)، و`@error` يعرض رسالة خطأ الحقل.

## أخطاء شائعة

- **`View [books.index] not found`:** اسم الملف أو المجلد خطأ؛ يجب أن يكون `resources/views/books/index.blade.php` (والامتداد `.blade.php` كاملًا).
- **`Undefined variable $books`:** لم تمرر المتغير من المتحكم في `view(...)`.
- **التغييرات لا تظهر:** نادرًا بسبب الذاكرة المؤقتة للقوالب؛ **Laravel > Cache > view:clear**.
- **`{!! !!}` مع مدخلات الزائر:** ثغرة XSS. استخدم `{{ }}`.

## تمرين

### تمرين: أكمل محرك القوالب

أضف إلى دالة المحاكاة دعم **قيمة افتراضية** بالصيغة `{{ $name ?? 'زائر' }}`: إذا لم يوجد المتغير تُطبع القيمة الافتراضية (بعد `htmlspecialchars` أيضًا).

```php exercise
<?php
function render(string $template, array $vars): string
{
    return preg_replace_callback('/\{\{\s*\$(\w+)\s*\}\}/u',
        fn($m) => htmlspecialchars((string) ($vars[$m[1]] ?? '')), $template);
}
echo render("أهلًا {{ \$name ?? 'زائر' }}", []), "\n";
echo render("أهلًا {{ \$name ?? 'زائر' }}", ['name' => '<b>منى</b>']), "\n";
```

```php solution
<?php
function render(string $template, array $vars): string
{
    return preg_replace_callback("/\{\{\s*\\$(\w+)\s*(?:\?\?\s*'([^']*)'\s*)?\}\}/u",
        fn($m) => htmlspecialchars((string) ($vars[$m[1]] ?? ($m[2] ?? ''))), $template);
}
echo render("أهلًا {{ \$name ?? 'زائر' }}", []), "\n";
echo render("أهلًا {{ \$name ?? 'زائر' }}", ['name' => '<b>منى</b>']), "\n";
```

```text output
أهلًا زائر
أهلًا &lt;b&gt;منى&lt;/b&gt;
```

## اختبر نفسك

```quiz
{"question": "ما الفرق بين {{ $x }} و {!! $x !!} في Blade؟", "choices": ["لا فرق", "الأولى تحمي من XSS بـ htmlspecialchars والثانية تطبع HTML كما هو", "الثانية أسرع وأأمن", "الأولى للأرقام فقط"], "answer": 1, "explanation": "{{ }} آمنة دائمًا؛ {!! !!} للـ HTML الموثوق فقط."}
```

```quiz
{"question": "ماذا يحدث إذا نسيت @csrf في نموذج POST؟", "choices": ["يعمل عاديًا", "يرد Laravel بالخطأ 419 Page Expired", "يُحذف النموذج", "خطأ 404"], "answer": 1, "explanation": "Laravel يرفض طلبات POST بدون رمز CSRF صحيح."}
```

```quiz
{"question": "القالب books.index موجود في أي ملف؟", "choices": ["resources/views/books.index.php", "resources/views/books/index.blade.php", "app/Views/books/index.php", "public/books/index.html"], "answer": 1, "explanation": "النقطة في اسم القالب تعني مجلدًا، والامتداد .blade.php."}
```

## الخلاصة

- القوالب في `resources/views` بامتداد `.blade.php`، تُنشأ بـ **New Blade View...** وتُستدعى بـ `view('folder.name', [...])`.
- `{{ }}` للطباعة الآمنة، و`@if` و`@foreach` و`@forelse` للمنطق، و`$loop` داخل الحلقات.
- `@extends` و`@section` و`@yield` للتخطيط المشترك، و`<x-name>` للمكونات.
- في النماذج: `@csrf` دائمًا، و`@method('PUT'/'DELETE')`، و`old()` و`@error`.
