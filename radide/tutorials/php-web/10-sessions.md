# الدرس 10: الجلسات والكوكيز وتسجيل الدخول

**في هذا الدرس ستتعلم:**

- لماذا «ينسى» الخادم الزائر بين طلب وآخر، وكيف تحل **الجلسات** ذلك.
- `session_start` والمصفوفة `$_SESSION`.
- **الكوكيز** بـ `setcookie` و`$_COOKIE`.
- التحويل بين الصفحات بـ `header('Location: ...')` ونمط **POST ثم Redirect ثم GET**.
- صفحة تسجيل دخول آمنة بـ `password_hash` و`password_verify`.

## الخادم ذاكرته قصيرة

بروتوكول HTTP **بلا ذاكرة**: كل طلب مستقل تمامًا، والخادم لا يتذكر أنك نفس الشخص الذي طلب الصفحة قبل ثانية. فكيف يعرف الموقع أنك سجّلت دخولك، أو ماذا في سلة مشترياتك؟

**الجلسة** (session) مثل **غرفة الأمانات** في متحف: تسلّم حقيبتك فيعطونك **رقمًا**. الحقيبة تبقى عندهم (على الخادم)، والرقم معك. وفي كل زيارة تُظهر الرقم فيعيدون إليك حقيبتك.

- الحقيبة = المصفوفة `$_SESSION` المحفوظة على الخادم.
- الرقم = **كوكي** صغيرة اسمها `PHPSESSID` يحفظها المتصفح ويرسلها مع كل طلب.

## عدّاد الزيارات

<!-- test: {"requests": [{"path": "/"}, {"path": "/"}, {"path": "/"}], "all": true} -->
```php web run
<?php
session_start();
$_SESSION['visits'] = ($_SESSION['visits'] ?? 0) + 1;
?>
<p>هذه زيارتك رقم <?= $_SESSION['visits'] ?></p>
```

عند فتح الصفحة ثلاث مرات (المتصفح يرسل نفس الكوكي كل مرة):

```text output
<p>هذه زيارتك رقم 1</p>

<p>هذه زيارتك رقم 2</p>

<p>هذه زيارتك رقم 3</p>
```

اضغط «جرّبه» ثم زر التحديث في المعاينة عدة مرات. وفي نافذة **Requests** اختر أي طلب وافتح تبويب **Request Headers**: ستجد الترويسة `Cookie: PHPSESSID=...`؛ هذا هو «رقم الأمانات».

> **مهم:** `session_start()` يجب أن تُستدعى **قبل أي مخرجات** (حتى قبل مسافة أو سطر فارغ)، لأنها ترسل كوكي في ترويسات الرد، والترويسات تُرسل قبل محتوى الصفحة. وإلا يظهر التحذير `headers already sent`.

## التحويل: header('Location')

`header('Location: page.php')` يقول للمتصفح «اذهب إلى هذه الصفحة»، فيطلبها المتصفح وحده. وبعدها نكتب `exit;` لإيقاف بقية الكود:

<!-- test: {"requests": [{"path": "/old.php"}]} -->
```php web run
// #file: old.php
<?php
header('Location: new.php');
exit;
// #file: new.php
<p>هذه هي الصفحة الجديدة</p>
```

```text output
<p>هذه هي الصفحة الجديدة</p>
```

في Requests سترى طلبين: `GET /old.php` بالرمز `302` (تحويل)، ثم `GET /new.php` بالرمز `200`.

### نمط POST - Redirect - GET

بعد معالجة نموذج POST نحوّل إلى صفحة عادية بدل عرض النتيجة مباشرة. بهذا إذا ضغط الزائر «تحديث» لا يُعاد إرسال النموذج مرة ثانية (ولا تُضاف نفس الطلبية مرتين!). ولعرض رسالة بعد التحويل نستخدم **رسالة فلاش** (flash): تُحفظ في الجلسة وتُعرض مرة واحدة ثم تُحذف:

<!-- test: {"requests": [{"method": "POST", "path": "/", "data": {"item": "قهوة"}}, {"path": "/"}], "all": true} -->
```php web run
<?php
session_start();
$_SESSION['cart'] ??= [];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $item = trim($_POST['item'] ?? '');
    if ($item !== '') {
        $_SESSION['cart'][] = $item;
        $_SESSION['flash'] = "تمت إضافة $item إلى السلة";
    }
    header('Location: index.php');
    exit;
}
$flash = $_SESSION['flash'] ?? '';
unset($_SESSION['flash']);
?>
<?php if ($flash): ?>
<p class="flash"><?= htmlspecialchars($flash) ?></p>
<?php endif; ?>
<p>في السلة: <?= count($_SESSION['cart']) ?></p>
<form method="post"><input name="item"><button>أضف</button></form>
```

أرسلنا «قهوة» (يتبعه التحويل وعرض الرسالة)، ثم فتحنا الصفحة مرة أخرى (الرسالة اختفت والسلة بقيت):

```text output
<p class="flash">تمت إضافة قهوة إلى السلة</p>
<p>في السلة: 1</p>
<form method="post"><input name="item"><button>أضف</button></form>

<p>في السلة: 1</p>
<form method="post"><input name="item"><button>أضف</button></form>
```

`$_SESSION['cart'] ??= [];` معناها: «إن لم تكن موجودة فاجعلها مصفوفة فارغة».

## كلمات المرور: لا تحفظها أبدًا كما هي

إذا سُرقت قاعدة بيانات فيها كلمات مرور مكشوفة فقد خسر كل مستخدم حسابه (وربما حساباته في مواقع أخرى). لذلك نحفظ **بصمة** (hash) لا يمكن عكسها:

```php run
<?php
$hash = password_hash("secret123", PASSWORD_DEFAULT);
echo str_starts_with($hash, '$2y$') ? "بصمة bcrypt بطول " . strlen($hash) . "\n" : "؟\n";
var_dump(password_verify("secret123", $hash));
var_dump(password_verify("wrong", $hash));
var_dump(password_hash("secret123", PASSWORD_DEFAULT) === $hash);
```

```text output
بصمة bcrypt بطول 60
bool(true)
bool(false)
bool(false)
```

- `password_hash` تصنع بصمة مختلفة في كل مرة (فيها «ملح» عشوائي)، لذلك السطر الأخير `false`.
- `password_verify` هي الطريقة **الوحيدة** الصحيحة للمقارنة.

## صفحة تسجيل دخول كاملة

ثلاث صفحات: `login.php` (النموذج والتحقق)، و`account.php` (محمية)، و`logout.php`. المستخدمون هنا في مصفوفة، وفي الدرس 12 سننقلهم إلى قاعدة بيانات:

<!-- test: {"requests": [{"path": "/account.php"}, {"method": "POST", "path": "/login.php", "data": {"user": "mona", "pass": "wrong"}}, {"method": "POST", "path": "/login.php", "data": {"user": "mona", "pass": "secret123"}}, {"path": "/logout.php"}], "all": true} -->
```php web run
// #file: users.php
<?php
// في الواقع: صف في جدول users. البصمة صُنعت مرة واحدة بـ password_hash
return ['mona' => password_hash('secret123', PASSWORD_DEFAULT)];
// #file: login.php
<?php
session_start();
$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $users = require __DIR__ . '/users.php';
    $user = $_POST['user'] ?? '';
    $pass = $_POST['pass'] ?? '';
    if (isset($users[$user]) && password_verify($pass, $users[$user])) {
        session_regenerate_id(true);       // رقم جلسة جديد بعد الدخول
        $_SESSION['user'] = $user;
        header('Location: account.php');
        exit;
    }
    $error = 'اسم المستخدم أو كلمة المرور غير صحيحة';
}
?>
<?php if ($error): ?><p class="error"><?= $error ?></p><?php endif; ?>
<form method="post">
    <input name="user"> <input name="pass" type="password"> <button>دخول</button>
</form>
// #file: account.php
<?php
session_start();
if (!isset($_SESSION['user'])) {
    header('Location: login.php');
    exit;
}
?>
<h1>حسابي</h1>
<p>مرحبًا <?= htmlspecialchars($_SESSION['user']) ?></p>
<a href="logout.php">خروج</a>
// #file: logout.php
<?php
session_start();
$_SESSION = [];
session_destroy();
header('Location: login.php');
exit;
```

الطلبات بالترتيب: فتح `account.php` بدون دخول (تحويل إلى نموذج الدخول)، ثم كلمة مرور خاطئة، ثم صحيحة (تحويل إلى الحساب)، ثم الخروج:

```text output
<form method="post">
    <input name="user"> <input name="pass" type="password"> <button>دخول</button>
</form>

<p class="error">اسم المستخدم أو كلمة المرور غير صحيحة</p><form method="post">
    <input name="user"> <input name="pass" type="password"> <button>دخول</button>
</form>

<h1>حسابي</h1>
<p>مرحبًا mona</p>
<a href="logout.php">خروج</a>

<form method="post">
    <input name="user"> <input name="pass" type="password"> <button>دخول</button>
</form>
```

نقاط الأمان في هذا المثال:

- **رسالة خطأ واحدة** للاسم والكلمة معًا، حتى لا يعرف المهاجم أي الأسماء موجود.
- `session_regenerate_id(true)` بعد الدخول يمنع هجوم «تثبيت الجلسة».
- الصفحة المحمية تفحص `$_SESSION['user']` **في أعلاها** قبل أي شيء.
- الخروج يمسح الجلسة ويدمّرها.

## الكوكيز

**الكوكي** (cookie) قيمة صغيرة يحفظها **المتصفح** نفسه ويرسلها مع كل طلب. تناسب التفضيلات غير الحساسة مثل لغة الموقع أو الوضع الليلي. (لا تضع فيها أبدًا بيانات مهمة: الزائر يستطيع قراءتها وتعديلها.)

<!-- test: {"requests": [{"path": "/?theme=dark"}, {"path": "/"}], "all": true} -->
```php web run
<?php
if (isset($_GET['theme']) && in_array($_GET['theme'], ['light', 'dark'], true)) {
    setcookie('theme', $_GET['theme'], time() + 30 * 24 * 3600);   // 30 يومًا
    $theme = $_GET['theme'];
} else {
    $theme = $_COOKIE['theme'] ?? 'light';
}
?>
<body class="<?= $theme ?>">الوضع الحالي: <?= $theme ?></body>
```

بعد اختيار الوضع الليلي مرة واحدة، يتذكره الموقع في الزيارة التالية:

```text output
<body class="dark">الوضع الحالي: dark</body>

<body class="dark">الوضع الحالي: dark</body>
```

## الجلسة أم الكوكي؟

| | الجلسة `$_SESSION` | الكوكي `$_COOKIE` |
|---|---|---|
| مكان البيانات | على الخادم | في متصفح الزائر |
| يستطيع الزائر تعديلها؟ | لا | نعم |
| مدة البقاء | حتى إغلاق المتصفح أو انتهاء المهلة | حتى التاريخ الذي تحدده |
| تستخدم لـ | تسجيل الدخول، السلة، رسائل الفلاش | التفضيلات: اللغة، الوضع الليلي |

## أخطاء شائعة

- **`headers already sent`:** طبعت شيئًا (أو سطرًا فارغًا قبل `<?php`) قبل `session_start` أو `header` أو `setcookie`.
- **نسيان `exit;` بعد `header('Location: ...')`:** يكمل الكود تنفيذه، وقد يعرض محتوى محميًا!
- **نسيان `session_start()` في صفحة:** `$_SESSION` تكون فارغة فيها.
- **مقارنة كلمة المرور بـ `===`:** استخدم `password_verify` دائمًا.

## تمارين

### تمرين 1: آخر بحث

صفحة تحفظ آخر كلمة بحث `q` في الجلسة، وتطبع `<p>آخر بحث: ...</p>`. افتحها بـ `?q=php` ثم بدون `q`: يجب أن تتذكر `php`.

<!-- test: {"requests": [{"path": "/?q=php"}, {"path": "/"}]} -->
```php web exercise
<?php
session_start();
// إذا وُجد $_GET['q'] احفظه في $_SESSION['last']
?>
<p>آخر بحث: <?= htmlspecialchars($_SESSION['last'] ?? 'لا يوجد') ?></p>
```

<!-- test: {"requests": [{"path": "/?q=php"}, {"path": "/"}]} -->
```php web solution
<?php
session_start();
if (isset($_GET['q'])) {
    $_SESSION['last'] = $_GET['q'];
}
?>
<p>آخر بحث: <?= htmlspecialchars($_SESSION['last'] ?? 'لا يوجد') ?></p>
```

```text output
<p>آخر بحث: php</p>
```

### تمرين 2: صفحة محمية

`secret.php` تحوّل إلى `login.php` إذا لم يكن `$_SESSION['user']` موجودًا. صفحة `login.php` جاهزة وتطبع `<p>سجّل دخولك أولًا</p>`.

<!-- test: {"requests": [{"path": "/secret.php"}]} -->
```php web exercise
// #file: secret.php
<?php
session_start();
// أضف الحماية هنا
?>
<p>معلومات سرية</p>
// #file: login.php
<p>سجّل دخولك أولًا</p>
```

<!-- test: {"requests": [{"path": "/secret.php"}]} -->
```php web solution
// #file: secret.php
<?php
session_start();
if (!isset($_SESSION['user'])) {
    header('Location: login.php');
    exit;
}
?>
<p>معلومات سرية</p>
// #file: login.php
<p>سجّل دخولك أولًا</p>
```

```text output
<p>سجّل دخولك أولًا</p>
```

## اختبر نفسك

```quiz
{"question": "أين تُحفظ بيانات $_SESSION؟", "choices": ["في متصفح الزائر", "على الخادم، والمتصفح يحفظ رقم الجلسة فقط", "في عنوان الصفحة", "في ملف CSS"], "answer": 1, "explanation": "البيانات على الخادم، والكوكي PHPSESSID تحمل رقم الجلسة فقط."}
```

```quiz
{"question": "لماذا نحوّل بعد معالجة نموذج POST (نمط PRG)؟", "choices": ["لتسريع الخادم", "حتى لا يُعاد إرسال النموذج عند التحديث", "لأن POST لا يعمل بدونه", "لحذف الجلسة"], "answer": 1, "explanation": "بعد التحويل تصبح الصفحة الحالية GET، فالتحديث لا يعيد الإرسال."}
```

```quiz
{"question": "كيف نتحقق من كلمة المرور المخزنة كبصمة؟", "choices": ["$hash === $pass", "md5($pass) === $hash", "password_verify($pass, $hash)", "password_hash($pass) === $hash"], "answer": 2, "explanation": "password_verify تقارن بأمان، و password_hash تعطي بصمة مختلفة كل مرة."}
```

## الخلاصة

- HTTP بلا ذاكرة، والجلسة (`session_start` + `$_SESSION`) تتذكر الزائر عبر كوكي `PHPSESSID`.
- `header('Location: ...'); exit;` للتحويل، ونمط PRG مع رسائل الفلاش بعد كل POST.
- كلمات المرور: `password_hash` للحفظ و`password_verify` للتحقق، و`session_regenerate_id` بعد الدخول.
- الكوكيز للتفضيلات غير الحساسة فقط.
