# الدرس 13: أدوات بيئة الويب - المعاينة والطلبات وعرض التصميم

**في هذا الدرس ستتعلم:**

- استخدام **Preview** (المعاينة) لاختبار الموقع على أحجام الهاتف والتابلت والشاشة الكبيرة.
- قراءة تفاصيل أي طلب في نافذة **Requests** (الطلبات).
- تصميم الصفحات بالسحب والإفلات في **Design View** (عرض التصميم) دون أن يضيع كود PHP.
- **IntelliSense** و**Emmet** لكتابة PHP و HTML بسرعة.
- صنع واجهة **JSON API** صغيرة واختبارها بـ **REST Client** (عميل REST).
- **SuperPreview** و**SEO Report** قبل النشر.

هذا الدرس عملي: افتح أي موقع من الدروس السابقة (أو أنشئ **PHP Starter Site** من **File > New Project... > Web > PHP Web Site**) وطبّق الخطوات معه.

## 1) المعاينة على الأجهزة المختلفة

بعد التشغيل (**Ctrl+F5**) انظر إلى شريط أدوات نافذة **Preview**:

| الأداة | وظيفتها |
|---|---|
| شريط العنوان | اكتب أي مسار مثل `/about.php?x=1` ثم Enter |
| **Back** / **Forward** / **Reload** | رجوع، تقدّم، تحديث (أو F5 داخل الصفحة) |
| قائمة الأجهزة | `Responsive (fit)`، `Phone (375 x 667)`، `Tablet (768 x 1024)`، `Laptop`، `Desktop` |
| **Rotate** (تدوير) | يقلب الجهاز بين الوضع الطولي والعرضي |
| **Open in Browser** (فتح في المتصفح) | يفتح نفس العنوان في متصفحك الخارجي |

اختر **Phone (375 x 667)** وتأكد أن النصوص لا تخرج من الشاشة وأن القوائم قابلة للضغط. هذا أسرع بكثير من فتح الموقع على هاتف حقيقي بعد كل تعديل، ومع **التحديث المباشر** ترى النتيجة فور الحفظ.

## 2) نافذة Requests بالتفصيل

كل سطر في **Requests** طلب واحد بأعمدة: **Time** و**Method** و**Path** و**Status** و**ms** (المدة) و**Size** و**Type**. اختر سطرًا لترى تبويباته:

- **General**: العنوان الكامل، والحالة، والمدة.
- **Request Headers**: ما أرسله المتصفح (ومنه `Cookie` الخاصة بالجلسة).
- **Request Body**: حقول النموذج في طلبات `POST`.
- **Response Headers**: ما رد به الخادم (ومنه `Location` في التحويلات و`Set-Cookie`).
- **Response**: الـ HTML أو JSON الذي رجع.

وبالزر الأيمن على أي طلب: **Copy URL** (نسخ الرابط)، و**Copy as curl** (نسخ كأمر curl لإعادته من سطر الأوامر)، و**Open in Preview**، و**Open File** (يفتح ملف PHP الذي خدم الطلب في المحرر). وخانة **Hide images / CSS / JS** تخفي طلبات الصور والتنسيق لتركّز على صفحاتك. والرموز التي يجب أن تلفت نظرك: `302` تحويل، و`404` ملف غير موجود (رابط مكسور أو صورة ناقصة)، و`500` خطأ في كود PHP.

## 3) عرض التصميم (Design View)

افتح صفحة `.php` أو `.html` ثم اضغط زر **Design** في شريط الأدوات (أو **Ctrl+Shift+D**)، أو بالزر الأيمن على الملف في Solution Explorer: **Open in Design View** (فتح في عرض التصميم). تظهر الصفحة كما ستبدو، وعلى الجانب:

- **Toolbox** (صندوق الأدوات): كتل جاهزة تسحبها إلى الصفحة: عناوين، وفقرات، وصور، وأزرار، وجداول، ونماذج، وأعمدة، وكتل Bootstrap (بعد زر **+ Bootstrap**).
- **Layers** (الطبقات): شجرة عناصر الصفحة؛ اختر منها العنصر الصعب الوصول إليه.
- **CSS Properties**: الألوان والخطوط والمسافات والحدود للعنصر المختار.
- **Attributes**: خصائص العنصر مثل `id` و`class` و`href` و`name`.

وفي أعلى التبويب ثلاثة أوضاع: **Design** (تصميم فقط)، و**Split** (مقسوم: التصميم فوق والكود تحت، ويتزامنان في الاتجاهين)، و**Code** (الكود فقط). وقائمة لحجم الجهاز، و**Undo** / **Redo**، و**Borders** لإظهار حدود العناصر، و**Preview** لرؤية الصفحة بدون أدوات التحرير.

> **ماذا عن كود PHP؟** عرض التصميم **يحمي** كود PHP: كل `<?php ... ?>` و`<?= ... ?>` داخل الصفحة يظهر كـ «شريحة كود» صغيرة لا تُعدّل بالخطأ، ويُعاد كما هو حرفيًا عند الحفظ. وما قبل `<body>` (مثل كتلة PHP في أعلى الملف) يبقى كما هو. لذلك تستطيع تصميم صفحة مثل `index.php` في المشروع النهائي بأمان.

جرّب: افتح `about.php`، واسحب من **Toolbox** كتلة صورة وفقرة، وغيّر لون العنوان من **CSS Properties**، ثم احفظ (**Ctrl+S**) وانتقل إلى **Split** لترى الـ HTML الذي كُتب.

## 4) IntelliSense و Emmet

- **IntelliSense** لـ PHP و HTML و CSS: اكتب `str_` فتظهر دوال النصوص مع شرحها ومعاملاتها، أو `$_` فتظهر `$_GET` و`$_POST` و`$_SESSION`. ويعمل معها **Go to Definition** (الانتقال إلى التعريف) بـ **F12** على اسم دالة كتبتها في ملف آخر. إن لم تظهر الاقتراحات ثبّت خوادم اللغات مرة واحدة من **Tools > Install Web Language Servers (HTML/CSS/JSON/PHP/JS/TS)**.
- **Emmet**: اكتب اختصارًا ثم **Tab** فيتوسع إلى HTML كامل. مثلًا `ul>li*3` تصبح قائمة فيها ثلاثة عناصر، و`form>input[name=email]+button` تصبح نموذجًا. (من القائمة: **Edit > Emmet: Expand Abbreviation**.)
- **Edit > Language Mode...** (وضع اللغة...) لتغيير لغة ملف تفتحه الـ IDE بلغة خاطئة.

## 5) واجهة JSON API و REST Client

المواقع الحديثة لا ترسل HTML فقط؛ تطبيقات الجوال وكود JavaScript يطلبون **بيانات** بصيغة **JSON**. صفحة PHP تستطيع أن ترد بـ JSON بدل HTML:

<!-- test: {"requests": [{"path": "/api.php?q=php"}]} -->
```php web run
// #file: api.php
<?php
header('Content-Type: application/json; charset=utf-8');

$books = [
    ["id" => 1, "title" => "تعلم PHP", "price" => 120],
    ["id" => 2, "title" => "قواعد البيانات", "price" => 95],
    ["id" => 3, "title" => "PHP المتقدمة", "price" => 180],
];
$q = mb_strtolower(trim($_GET['q'] ?? ''));
if ($q !== '') {
    $books = array_values(array_filter($books,
        fn($b) => str_contains(mb_strtolower($b['title']), $q)));
}
echo json_encode(["count" => count($books), "items" => $books], JSON_UNESCAPED_UNICODE);
```

```text output
{"count":2,"items":[{"id":1,"title":"تعلم PHP","price":120},{"id":3,"title":"PHP المتقدمة","price":180}]}
```

- `header('Content-Type: application/json')` يخبر الطالب أن الرد JSON.
- `json_encode` يحوّل المصفوفة إلى نص JSON، و`JSON_UNESCAPED_UNICODE` يترك العربية مقروءة بدل `ا...`.
- `array_values` يعيد ترقيم العناصر من 0 حتى تخرج قائمة JSON لا كائنًا.

لاختبار الواجهة افتح **Tools > REST Client** (أدوات > عميل REST) أو **Ctrl+Alt+K**: نافذة مثل Postman تختار فيها الطريقة (`GET`، `POST`...)، وتكتب العنوان، وتضيف المعاملات والترويسات وجسم الطلب، ثم **Send**؛ فيظهر الرد منسقًا مع الحالة والمدة والحجم. وتستطيع حفظ الطلبات في ملف `.http` داخل المشروع، وفوق كل طلب فيه رابط **Send Request**:

```text
@host = http://127.0.0.1:8123

### كل الكتب
GET {{host}}/api.php

### البحث
GET {{host}}/api.php?q=php
Accept: application/json
```

(غيّر رقم المنفذ إلى الرقم الظاهر في شريط عنوان المعاينة، أو ثبّته من **Site Settings > Port**.)

## 6) قبل النشر: SuperPreview و SEO

- **Site > SuperPreview...**: يعرض نفس الصفحة **جنبًا إلى جنب** بحجمين أو في محركين مختلفين (المعاينة الحية، أو لقطة من Edge أو Chrome أو Firefox المثبتة على جهازك)، مع وضع «تراكب» يكشف الفروق بالبكسل.
- **Site > SEO Report**: يزحف على صفحات موقعك ويعدّد المشكلات: روابط مكسورة (`404`)، وصفحات بلا عنوان `<title>` أو وصف، وصور بلا نص بديل `alt`... ويمكن تصدير التقرير HTML.
- **Site > Lighthouse Report**: تقرير الأداء وسهولة الوصول من Google Lighthouse.

## أخطاء شائعة

- **تعديل الملف أثناء فتحه في Design View وفي محرر الكود معًا:** اعمل في مكان واحد ثم احفظ؛ أو استخدم وضع **Split** الذي يزامن الاثنين.
- **رد JSON يحتوي تحذيرات PHP:** أي `Warning` تُطبع قبل JSON تفسده. راقب تبويب **Response** في Requests.
- **نسيان `array_values` بعد `array_filter`:** تخرج `{"0":...,"2":...}` بدل قائمة.

## تمارين

### تمرين 1: واجهة الوقت... بدون وقت!

اكتب `status.php` ترد بـ JSON فيه `"ok": true` و`"php": 8` (استخدم الثابت `PHP_MAJOR_VERSION`).

<!-- test: {"requests": [{"path": "/status.php"}]} -->
```php web exercise
// #file: status.php
<?php
header('Content-Type: application/json');
```

<!-- test: {"requests": [{"path": "/status.php"}]} -->
```php web solution
// #file: status.php
<?php
header('Content-Type: application/json');
echo json_encode(["ok" => true, "php" => PHP_MAJOR_VERSION]);
```

```text output
{"ok":true,"php":8}
```

### تمرين 2: قراءة JSON

`json_decode` تفعل العكس: تحوّل نص JSON إلى مصفوفة. حوّل النص المعطى واطبع `علي - 3 طلبات`.

```php exercise
<?php
$json = '{"name": "علي", "orders": [101, 102, 103]}';
// $data = json_decode($json, true);
```

```php solution
<?php
$json = '{"name": "علي", "orders": [101, 102, 103]}';
$data = json_decode($json, true);
echo $data['name'], " - ", count($data['orders']), " طلبات\n";
```

```text output
علي - 3 طلبات
```

## اختبر نفسك

```quiz
{"question": "ماذا يحدث لكود PHP داخل الصفحة عند تحريرها في Design View؟", "choices": ["يُحذف", "يظهر كشريحة كود محمية ويُعاد كما هو عند الحفظ", "يتحول إلى HTML", "يُنفّذ مرة واحدة"], "answer": 1, "explanation": "عرض التصميم يحمي كل وسوم PHP ويعيدها حرفيًا عند الحفظ."}
```

```quiz
{"question": "أين ترى الـ HTML أو JSON الذي رد به الخادم على طلب معيّن؟", "choices": ["Requests > تبويب Response", "Toolbox", "Solution Explorer", "Help"], "answer": 0, "explanation": "اختر الطلب في Requests وافتح تبويب Response."}
```

```quiz
{"question": "ما فائدة JSON_UNESCAPED_UNICODE مع json_encode؟", "choices": ["تشفير البيانات", "ترك الحروف العربية مقروءة بدل رموز \\u", "ضغط الرد", "لا فائدة"], "answer": 1, "explanation": "بدونها تتحول العربية إلى \\u0627 وأمثالها (صحيحة لكن غير مقروءة)."}
```

## الخلاصة

- **Preview** بأحجام الأجهزة و**Rotate** لاختبار التصميم المتجاوب، و**Requests** لكل تفاصيل الطلبات.
- **Design View** (Ctrl+Shift+D) للتصميم بالسحب والإفلات مع حماية كود PHP، ووضع **Split** للتزامن.
- IntelliSense وF12 وEmmet لكتابة أسرع.
- صفحة PHP ترد بـ JSON بـ `json_encode`، وتُختبر بـ **REST Client** وملفات `.http`.
