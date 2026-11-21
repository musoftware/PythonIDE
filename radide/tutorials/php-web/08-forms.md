# الدرس 8: النماذج - استقبال بيانات الزائر

**في هذا الدرس ستتعلم:**

- كيف يرسل نموذج HTML بياناته إلى PHP بطريقتي `GET` و`POST`.
- قراءة البيانات من `$_GET` و`$_POST`.
- **الأمان أولًا:** لماذا نمرر كل ما نطبعه على `htmlspecialchars`.
- التحقق من المدخلات وعرض رسائل الأخطاء، وإبقاء ما كتبه الزائر في الحقول.
- مراقبة ما يُرسل فعلًا في نافذة **Requests**.

## النموذج: استمارة يملؤها الزائر

**النموذج** (form) في HTML مثل استمارة ورقية: حقول يملؤها الزائر، وزر إرسال. عند الضغط يرسل المتصفح طلبًا جديدًا إلى الصفحة المذكورة في `action`، ومعه أسماء الحقول (`name`) وقيمها:

```html
<form method="get" action="hello.php">
    <input name="name">
    <button>أرسل</button>
</form>
```

## GET: البيانات في العنوان

مع `method="get"` تُلصق البيانات في **عنوان الصفحة**: `hello.php?name=سارة`. وتقرأها PHP من المصفوفة `$_GET`:

<!-- test: {"requests": [{"path": "/hello.php?name=Sara"}]} -->
```php web run
// #file: index.php
<form method="get" action="hello.php">
    <label>اسمك: <input name="name"></label>
    <button>أرسل</button>
</form>
// #file: hello.php
<?php
$name = $_GET['name'] ?? 'زائر';
?>
<h1>أهلًا يا <?= htmlspecialchars($name) ?>!</h1>
<a href="index.php">رجوع</a>
```

عند إرسال الاسم `Sara` تفتح الصفحة `/hello.php?name=Sara` ويصل:

```text output
<h1>أهلًا يا Sara!</h1>
<a href="index.php">رجوع</a>
```

اضغط «جرّبه»، واكتب اسمك في المعاينة، وراقب شريط العنوان ونافذة **Requests**: سترى طلب `GET /hello.php?name=...`. وإذا اخترت الطلب في Requests ترى تفاصيله في تبويبات: **General** (العنوان والحالة والمدة)، و**Request Headers** (ترويسات الطلب)، و**Request Body**، و**Response Headers**، و**Response** (الـ HTML الذي رجع).

**متى نستخدم GET؟** للبحث والتصفية والروابط التي يمكن حفظها أو مشاركتها (`search.php?q=php`). ولا نستخدمه أبدًا لكلمات المرور أو لتغيير البيانات.

## الأمان: `htmlspecialchars`

ماذا لو كتب زائر خبيث في حقل الاسم كود JavaScript مثل `<script>...</script>`؟ إذا طبعناه كما هو سينفّذه متصفح كل من يفتح الصفحة! هذا هجوم شهير اسمه **XSS**. الحل: `htmlspecialchars` تحوّل الرموز الخاصة إلى رموز آمنة تُعرض ولا تُنفّذ:

```php run
<?php
$evil = '<script>alert("hacked")</script>';
echo htmlspecialchars($evil), "\n";
echo htmlspecialchars("Tom & Jerry's"), "\n";
```

```text output
&lt;script&gt;alert(&quot;hacked&quot;)&lt;/script&gt;
Tom &amp; Jerry&#039;s
```

> **القاعدة الذهبية للويب:** كل قيمة جاءت من الزائر (أو من قاعدة البيانات) تمر على `htmlspecialchars` **قبل طباعتها** في HTML. لا استثناءات. كثير من المبرمجين يعرّفون دالة قصيرة لها: `function e($s) { return htmlspecialchars((string) $s); }`.

## POST: البيانات في جسم الطلب

مع `method="post"` لا تظهر البيانات في العنوان، بل تُرسل في **جسم الطلب**، وتقرأها PHP من `$_POST`. نستخدمها لإرسال البيانات التي **تغيّر** شيئًا: تسجيل، أو إضافة، أو تسجيل دخول.

الأسلوب الشائع: **نفس الصفحة** تعرض النموذج وتعالجه. نعرف أن الزائر أرسل النموذج من `$_SERVER['REQUEST_METHOD']`:

<!-- test: {"requests": [{"path": "/"}, {"method": "POST", "path": "/", "data": {"a": "12", "b": "30"}}], "all": true} -->
```php web run
<?php
$result = null;
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $a = (float) ($_POST['a'] ?? 0);
    $b = (float) ($_POST['b'] ?? 0);
    $result = $a + $b;
}
?>
<form method="post">
    <input name="a" size="4"> + <input name="b" size="4">
    <button>احسب</button>
</form>
<?php if ($result !== null): ?>
<p>الناتج: <?= $result ?></p>
<?php endif; ?>
```

الطلب الأول (`GET`) يعرض النموذج فقط، والثاني (`POST` بالقيمتين 12 و30) يعرض الناتج أيضًا:

```text output
<form method="post">
    <input name="a" size="4"> + <input name="b" size="4">
    <button>احسب</button>
</form>

<form method="post">
    <input name="a" size="4"> + <input name="b" size="4">
    <button>احسب</button>
</form>
<p>الناتج: 42</p>
```

بدون `action` يُرسل النموذج إلى نفس الصفحة. وفي **Requests** سترى الطلب `POST /` بالرمز `200`، وفي تبويب **Request Body** تجد الحقلين `a` و`b` وقيمتيهما كما أرسلهما المتصفح.

## التحقق من المدخلات

لا تثق أبدًا بما يرسله الزائر: قد يترك الحقل فارغًا، أو يكتب نصًا مكان الرقم، أو بريدًا خاطئًا. نجمع الأخطاء في مصفوفة، ونعرض النموذج مرة أخرى **مع القيم التي كتبها** حتى لا يعيد الكتابة من البداية:

<!-- test: {"requests": [{"method": "POST", "path": "/", "data": {"name": "", "email": "not-an-email", "age": "15"}}]} -->
```php web run
<?php
function e($s): string { return htmlspecialchars((string) $s); }

$name = trim($_POST['name'] ?? '');
$email = trim($_POST['email'] ?? '');
$age = $_POST['age'] ?? '';
$errors = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if ($name === '') {
        $errors[] = 'الاسم مطلوب';
    }
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $errors[] = 'البريد الإلكتروني غير صحيح';
    }
    if (!ctype_digit($age) || (int) $age < 18) {
        $errors[] = 'العمر يجب أن يكون 18 أو أكثر';
    }
}
?>
<?php if ($errors): ?>
<ul class="errors">
<?php foreach ($errors as $err): ?>
    <li><?= e($err) ?></li>
<?php endforeach; ?>
</ul>
<?php elseif ($_SERVER['REQUEST_METHOD'] === 'POST'): ?>
<p>تم التسجيل، مرحبًا <?= e($name) ?>!</p>
<?php endif; ?>
<form method="post">
    <input name="name" value="<?= e($name) ?>">
    <input name="email" value="<?= e($email) ?>">
    <input name="age" value="<?= e($age) ?>">
    <button>سجّل</button>
</form>
```

أرسلنا اسمًا فارغًا وبريدًا خاطئًا وعمر 15، فيصل:

```text output
<ul class="errors">
    <li>الاسم مطلوب</li>
    <li>البريد الإلكتروني غير صحيح</li>
    <li>العمر يجب أن يكون 18 أو أكثر</li>
</ul>
<form method="post">
    <input name="name" value="">
    <input name="email" value="not-an-email">
    <input name="age" value="15">
    <button>سجّل</button>
</form>
```

أدوات التحقق المستخدمة:

| الأداة | وظيفتها |
|---|---|
| `trim` | تحذف المسافات من الطرفين (حتى لا يُقبل اسم من مسافات فقط) |
| `filter_var($x, FILTER_VALIDATE_EMAIL)` | تتحقق من شكل البريد الإلكتروني |
| `ctype_digit` | هل النص أرقام فقط؟ |
| `value="<?= e($name) ?>"` | يبقي ما كتبه الزائر في الحقل (نموذج «لاصق») |

> **مهم:** التحقق في المتصفح (مثل الخاصية `required` في HTML) مريح للزائر، لكنه **ليس أمانًا**: أي شخص يستطيع تجاوزه وإرسال طلب مباشر. التحقق الحقيقي يكون دائمًا في PHP على الخادم.

## القوائم ومربعات الاختيار

حقل يحمل اسمه أقواسًا مثل `name="topics[]"` يصل إلى PHP **مصفوفة**:

<!-- test: {"requests": [{"method": "POST", "path": "/", "data": {"level": "mid", "topics[]": ["php", "sql"]}}]} -->
```php web run
<?php
$levels = ['new' => 'مبتدئ', 'mid' => 'متوسط', 'pro' => 'محترف'];
$level = $_POST['level'] ?? 'new';
$topics = $_POST['topics'] ?? [];
if (!array_key_exists($level, $levels)) {
    $level = 'new';                       // قيمة غير مسموحة: نتجاهلها
}
?>
<p>المستوى: <?= $levels[$level] ?></p>
<p>المواضيع: <?= htmlspecialchars(implode('، ', $topics)) ?></p>
```

```text output
<p>المستوى: متوسط</p>
<p>المواضيع: php، sql</p>
```

لاحظ كيف قارنّا القيمة بقائمة **مسموحة** (`array_key_exists`) بدل أن نثق بها: الزائر يستطيع إرسال أي قيمة حتى لو لم تكن في القائمة المنسدلة.

## أخطاء شائعة

- **`Undefined array key "name"`:** قرأت `$_POST['name']` قبل الإرسال. استخدم `$_POST['name'] ?? ''`.
- **نسيان الخاصية `name` في الحقل:** الحقل بدون `name` لا يُرسل أبدًا.
- **طباعة المدخلات بدون `htmlspecialchars`:** ثغرة XSS.
- **استخدام GET لكلمات المرور:** تظهر في العنوان وفي سجل المتصفح.

## تمارين

### تمرين 1: محوّل درجات الحرارة

صفحة تقرأ `c` من العنوان (`?c=25`) وتطبع `<p>25 درجة مئوية = 77 فهرنهايت</p>` (الفهرنهايت = c × 9 / 5 + 32).

<!-- test: {"requests": [{"path": "/?c=25"}]} -->
```php web exercise
<?php
$c = (float) ($_GET['c'] ?? 0);
?>
```

<!-- test: {"requests": [{"path": "/?c=25"}]} -->
```php web solution
<?php
$c = (float) ($_GET['c'] ?? 0);
$f = $c * 9 / 5 + 32;
?>
<p><?= $c ?> درجة مئوية = <?= $f ?> فهرنهايت</p>
```

```text output
<p>25 درجة مئوية = 77 فهرنهايت</p>
```

### تمرين 2: نموذج تعليق آمن

عند إرسال `comment` بطريقة POST اطبعه داخل `<blockquote>` بعد تمريره على `htmlspecialchars`. جرّب إرسال `<b>رائع</b>`.

<!-- test: {"requests": [{"method": "POST", "path": "/", "data": {"comment": "<b>رائع</b>"}}]} -->
```php web exercise
<?php
$comment = $_POST['comment'] ?? '';
?>
<blockquote><?= $comment ?></blockquote>
```

<!-- test: {"requests": [{"method": "POST", "path": "/", "data": {"comment": "<b>رائع</b>"}}]} -->
```php web solution
<?php
$comment = $_POST['comment'] ?? '';
?>
<blockquote><?= htmlspecialchars($comment) ?></blockquote>
```

```text output
<blockquote>&lt;b&gt;رائع&lt;/b&gt;</blockquote>
```

## اختبر نفسك

```quiz
{"question": "أين تجد بيانات نموذج أُرسل بـ method=\"post\"؟", "choices": ["$_GET", "$_POST", "$_SERVER فقط", "في عنوان الصفحة"], "answer": 1, "explanation": "بيانات POST في المصفوفة $_POST، وبيانات العنوان في $_GET."}
```

```quiz
{"question": "لماذا نستخدم htmlspecialchars عند طباعة مدخلات الزائر؟", "choices": ["لتسريع الصفحة", "لمنع تنفيذ كود HTML/JavaScript خبيث (XSS)", "لتحويل النص إلى رقم", "لحفظ البيانات"], "answer": 1, "explanation": "تحوّل < و > و & والعلامات إلى رموز آمنة تُعرض ولا تُنفّذ."}
```

```quiz
{"question": "التحقق بالخاصية required في HTML وحده...", "choices": ["يكفي تمامًا", "لا يكفي؛ يجب التحقق في PHP أيضًا", "يمنع XSS", "يشفّر البيانات"], "answer": 1, "explanation": "أي شخص يستطيع تجاوز المتصفح وإرسال طلب مباشر، فالتحقق الحقيقي على الخادم."}
```

## الخلاصة

- `GET` للبحث والروابط (`$_GET`)، و`POST` لإرسال بيانات تغيّر شيئًا (`$_POST`).
- `$_SERVER['REQUEST_METHOD']` يخبرك هل أُرسل النموذج.
- تحقق من كل مدخل على الخادم، واجمع الأخطاء، وأبقِ القيم في الحقول.
- كل ما تطبعه من بيانات الزائر يمر على `htmlspecialchars`.
