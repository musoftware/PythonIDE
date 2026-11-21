# الدرس 13: قواعد البيانات SQLite والإنترنت بـ RingLibCurl

**في هذا الدرس ستتعلم:**

- ما هي **قاعدة البيانات** ولماذا نستخدم **SQLite**.
- إنشاء جدول وإضافة سجلات والبحث فيها من Ring بلغة **SQL**.
- حماية الاستعلام من علامات التنصيص في نص المستخدم.
- تحميل صفحة أو بيانات من الإنترنت بمكتبة **RingLibCurl**.

## ما هي قاعدة البيانات؟

في الدرس 10 حفظنا البيانات في ملف نصي. هذا جيد للبيانات القليلة، لكن عندما تكثر البيانات ونريد البحث والترتيب والتعديل بسرعة، نستخدم **قاعدة بيانات** (database).

> **تشبيه:** الملف النصي مثل كراسة تكتب فيها كل شيء بالترتيب. قاعدة البيانات مثل **دولاب أرشيف** فيه أدراج (جداول)، وكل درج فيه بطاقات منظمة (سجلات)، ولكل بطاقة خانات ثابتة (أعمدة)، ومعه موظف ذكي يجيبك فورًا عن أي سؤال.

**SQLite** قاعدة بيانات صغيرة جدًا: كلها ملف واحد على جهازك (مثل `school.db`)، ولا تحتاج إلى خادم أو تثبيت. وهي تأتي مع Ring جاهزة.

نخاطب قاعدة البيانات بلغة اسمها **SQL**. أهم أوامرها:

| الأمر | العمل |
|---|---|
| `CREATE TABLE` | إنشاء جدول |
| `INSERT INTO` | إضافة سجل |
| `SELECT` | قراءة سجلات (مع `WHERE` للشرط و`ORDER BY` للترتيب) |
| `UPDATE` | تعديل سجلات |
| `DELETE` | حذف سجلات |

## أول قاعدة بيانات

```ring run
load "sqlitelib.ring"

oDB = sqlite_init()
sqlite_open(oDB, "school.db")      # يُنشأ الملف إذا لم يكن موجودًا

sqlite_execute(oDB, "DROP TABLE IF EXISTS students")
sqlite_execute(oDB, "CREATE TABLE students (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT,
    grade INTEGER)")

sqlite_execute(oDB, "INSERT INTO students (name, grade) VALUES ('علي', 90)")
sqlite_execute(oDB, "INSERT INTO students (name, grade) VALUES ('سارة', 95)")
sqlite_execute(oDB, "INSERT INTO students (name, grade) VALUES ('يوسف', 78)")

aRows = sqlite_execute(oDB, "SELECT * FROM students ORDER BY grade DESC")
see "عدد الطلاب: " + len(aRows) + nl
for aRow in aRows
    see "" + aRow[:id] + ". " + aRow[:name] + ": " + aRow[:grade] + nl
next

sqlite_close(oDB)
remove("school.db")
```

```text output
عدد الطلاب: 3
2. سارة: 95
1. علي: 90
3. يوسف: 78
```

### ماذا تُرجع `sqlite_execute`؟

- مع `SELECT`: **قائمة صفوف**، وكل صف **قاموس** مفاتيحه أسماء الأعمدة، فنكتب `aRow[:name]`.
- مع الأوامر الأخرى: قائمة فارغة.
- القيم ترجع دائمًا **نصوصًا**؛ حوّل الأرقام بـ `number()` إذا أردت الحساب بها.

| الدالة | العمل |
|---|---|
| `sqlite_init()` | ينشئ كائن الاتصال |
| `sqlite_open(oDB, cFile)` | يفتح ملف القاعدة (و`":memory:"` قاعدة مؤقتة في الذاكرة) |
| `sqlite_execute(oDB, cSQL)` | ينفّذ أمر SQL |
| `sqlite_errmsg(oDB)` | رسالة آخر خطأ |
| `sqlite_close(oDB)` | يغلق القاعدة |

## البحث والتعديل والحذف والإحصاء

```ring run
load "sqlitelib.ring"

oDB = sqlite_init()
sqlite_open(oDB, ":memory:")       # قاعدة في الذاكرة: تختفي عند الإغلاق
sqlite_execute(oDB, "CREATE TABLE products (name TEXT, price INTEGER, qty INTEGER)")
sqlite_execute(oDB, "INSERT INTO products VALUES ('قلم', 5, 100), ('كراسة', 20, 40), ('حقيبة', 250, 5)")

# بحث بشرط
aRows = sqlite_execute(oDB, "SELECT name FROM products WHERE price < 50")
see "منتجات أقل من 50: "
for aRow in aRows see aRow[:name] + " " next
see nl

# تعديل
sqlite_execute(oDB, "UPDATE products SET price = 200 WHERE name = 'حقيبة'")
# حذف
sqlite_execute(oDB, "DELETE FROM products WHERE qty < 10 AND price > 1000")

# إحصاء
aRows = sqlite_execute(oDB, "SELECT COUNT(*) AS n, SUM(price * qty) AS total FROM products")
see "عدد المنتجات: " + aRows[1][:n] + nl
see "قيمة المخزون: " + aRows[1][:total] + nl

sqlite_close(oDB)
```

```text output
منتجات أقل من 50: قلم كراسة 
عدد المنتجات: 3
قيمة المخزون: 2300
```

## انتبه: علامة التنصيص في نص المستخدم

النصوص داخل SQL توضع بين `'...'`. فإذا كتب المستخدم اسمًا فيه علامة `'` مثل `O'Brien` انكسر الأمر! والحل أن نضاعف كل `'` في النص قبل وضعه في الأمر:

```ring run
load "sqlitelib.ring"

oDB = sqlite_init()
sqlite_open(oDB, ":memory:")
sqlite_execute(oDB, "CREATE TABLE people (name TEXT)")

cName = "O'Brien"
sqlite_execute(oDB, "INSERT INTO people VALUES ('" + sqlText(cName) + "')")
aRows = sqlite_execute(oDB, "SELECT name FROM people")
see "تم الحفظ: " + aRows[1][:name] + nl

sqlite_execute(oDB, "INSERT INTO people VALUES ('" + cName + "')")   # بدون حماية
see "الخطأ: " + sqlite_errmsg(oDB) + nl
sqlite_close(oDB)

func sqlText c
    return substr(c, "'", "''")
```

```text output
تم الحفظ: O'Brien
الخطأ: near "Brien": syntax error
```

> **مهم للأمان:** وضع نص المستخدم في أمر SQL دون حماية ثغرة خطيرة اسمها **SQL Injection**: قد يكتب المستخدم الخبيث نصًا يحذف جداولك. استخدم دائمًا دالة مثل `sqlText()`.

## رؤية قاعدة البيانات في الـ IDE

لا تحتاج إلى برنامج خارجي لرؤية ما في ملف `.db`: نافذة **Databases** في RAD IDE تعرض ملفات SQLite الموجودة في مجلد المشروع، وتفتح أي جدول في شبكة قابلة للتعديل، ويمكنك فيها كتابة استعلامات SQL وتجربتها قبل وضعها في الكود.

## الإنترنت: RingLibCurl

**libcurl** مكتبة عالمية شهيرة لنقل البيانات عبر الإنترنت (HTTP وHTTPS وFTP وغيرها)، و**RingLibCurl** تربطها بـ Ring. هذا مثال يحمّل صفحة ويب ويطبع عنوانها:

<!-- test: {"norun": true} -->
```ring run
load "libcurl.ring"

curl = curl_easy_init()
curl_easy_setopt(curl, CURLOPT_URL, "https://example.com")
curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1)     # اتبع التحويلات
cPage = curl_easy_perform_silent(curl)                # يُرجع المحتوى نصًا
curl_easy_cleanup(curl)

nStart = substr(cPage, "<title>")
nEnd = substr(cPage, "</title>")
if nStart > 0 and nEnd > nStart
    see "عنوان الصفحة: " + substr(cPage, nStart + 7, nEnd - nStart - 7) + nl
else
    see "لم أستطع قراءة الصفحة (هل أنت متصل بالإنترنت؟)" + nl
ok
see "حجم الصفحة: " + len(cPage) + " بايت" + nl
```

الناتج عند الاتصال بالإنترنت يكون مثل:

```text
عنوان الصفحة: Example Domain
حجم الصفحة: 528 بايت
```

| الدالة | العمل |
|---|---|
| `curl_easy_init()` | ينشئ طلبًا جديدًا |
| `curl_easy_setopt(curl, الخيار, القيمة)` | يضبط خيارًا: `CURLOPT_URL` للعنوان، و`CURLOPT_FOLLOWLOCATION` لاتباع التحويلات |
| `curl_easy_perform_silent(curl)` | ينفّذ الطلب ويُرجع المحتوى نصًا (بدون طباعته) |
| `curl_easy_perform(curl)` | ينفّذ الطلب ويطبع المحتوى مباشرة |
| `curl_easy_cleanup(curl)` | يحرر الطلب |

### الطريقة الأقصر: `download()`

المكتبة `internetlib.ring` (مبنية على RingLibCurl) فيها دالة واحدة تفعل كل ذلك:

<!-- test: {"norun": true} -->
```ring run
load "internetlib.ring"

cData = download("https://example.com")
see "تم تحميل " + len(cData) + " بايت" + nl
```

### إرسال بيانات (POST)

كثير من الخدمات على الإنترنت (API) تستقبل بيانات بطريقة POST:

<!-- test: {"norun": true} -->
```ring run
load "libcurl.ring"

curl = curl_easy_init()
curl_easy_setopt(curl, CURLOPT_URL, "https://httpbin.org/post")
curl_easy_setopt(curl, CURLOPT_POSTFIELDS, "name=Ring&lang=ar")
cReply = curl_easy_perform_silent(curl)
curl_easy_cleanup(curl)
see cReply
```

> **ملحوظة:** أمثلة الإنترنت في هذا الدرس تحتاج اتصالًا، لذلك يفحص زر «تحقق» صحة كتابتها فقط. اضغط «جرّبه» لتشغيلها فعلًا.

## أخطاء شائعة

- **نسيان `load "sqlitelib.ring"`:** يعطي «Calling Function without definition: sqlite_init».
- **نسيان أن القيم ترجع نصوصًا:** `aRow[:grade] + 5` لا تجمع بل تلصق (`"90" + 5` تعطي `905`). اكتب `number(aRow[:grade]) + 5`.
- **وضع نص المستخدم في SQL مباشرة:** استخدم `sqlText()`.
- **نسيان `sqlite_close` أو `curl_easy_cleanup`.**

## تمارين

### التمرين 1: أفضل طالب

أنشئ جدولًا في الذاكرة فيه ثلاثة طلاب ودرجاتهم، ثم اطبع اسم صاحب أعلى درجة باستخدام `ORDER BY grade DESC LIMIT 1`.

```ring exercise
load "sqlitelib.ring"

oDB = sqlite_init()
sqlite_open(oDB, ":memory:")
sqlite_execute(oDB, "CREATE TABLE students (name TEXT, grade INTEGER)")
sqlite_execute(oDB, "INSERT INTO students VALUES ('منى', 88), ('كريم', 97), ('هدى', 91)")
# اكتب الاستعلام واطبع النتيجة
sqlite_close(oDB)
```

```ring solution
load "sqlitelib.ring"

oDB = sqlite_init()
sqlite_open(oDB, ":memory:")
sqlite_execute(oDB, "CREATE TABLE students (name TEXT, grade INTEGER)")
sqlite_execute(oDB, "INSERT INTO students VALUES ('منى', 88), ('كريم', 97), ('هدى', 91)")
aRows = sqlite_execute(oDB, "SELECT name, grade FROM students ORDER BY grade DESC LIMIT 1")
see "الأول: " + aRows[1][:name] + " بدرجة " + aRows[1][:grade] + nl
sqlite_close(oDB)
```

```text output
الأول: كريم بدرجة 97
```

### التمرين 2: متوسط الدرجات

استخدم نفس الجدول لحساب **متوسط** الدرجات بـ `AVG(grade)`، ثم اطبعه كرقم صحيح باستخدام `floor(number(...))`.

```ring exercise
load "sqlitelib.ring"

oDB = sqlite_init()
sqlite_open(oDB, ":memory:")
sqlite_execute(oDB, "CREATE TABLE students (name TEXT, grade INTEGER)")
sqlite_execute(oDB, "INSERT INTO students VALUES ('منى', 88), ('كريم', 97), ('هدى', 91)")
# SELECT AVG(grade) AS avg FROM students
sqlite_close(oDB)
```

```ring solution
load "sqlitelib.ring"

oDB = sqlite_init()
sqlite_open(oDB, ":memory:")
sqlite_execute(oDB, "CREATE TABLE students (name TEXT, grade INTEGER)")
sqlite_execute(oDB, "INSERT INTO students VALUES ('منى', 88), ('كريم', 97), ('هدى', 91)")
aRows = sqlite_execute(oDB, "SELECT AVG(grade) AS avg FROM students")
see "المتوسط: " + floor(number(aRows[1][:avg])) + nl
sqlite_close(oDB)
```

```text output
المتوسط: 92
```

## اختبر نفسك

```quiz
{"question": "ماذا تُرجع `sqlite_execute` مع أمر SELECT؟", "choices": ["رقمًا", "قائمة صفوف، كل صف قاموس بأسماء الأعمدة", "نصًا واحدًا", "لا شيء"], "answer": 1, "explanation": "كل صف قاموس، فنكتب aRow[:name]."}
```

```quiz
{"question": "لماذا نضاعف علامة ' في نص المستخدم قبل وضعه في SQL؟", "choices": ["لتسريع الاستعلام", "حتى لا ينكسر الأمر ولنحمي البرنامج من SQL Injection", "لأن SQLite لا تقبل العربية", "لا داعي لذلك"], "answer": 1, "explanation": "'' داخل نص SQL تعني علامة ' واحدة، فيبقى الأمر سليمًا وآمنًا."}
```

```quiz
{"question": "أي دالة في RingLibCurl تُرجع محتوى الصفحة كنص دون طباعته؟", "choices": ["curl_easy_perform", "curl_easy_perform_silent", "curl_easy_init", "curl_text"], "answer": 1, "explanation": "curl_easy_perform_silent تُرجع المحتوى، وcurl_easy_perform تطبعه."}
```

## الخلاصة

- `load "sqlitelib.ring"` ثم `sqlite_init` و`sqlite_open` و`sqlite_execute` و`sqlite_close`.
- نتائج SELECT قائمة قواميس، والقيم نصوص.
- احمِ نص المستخدم بمضاعفة `'`.
- `load "libcurl.ring"` للإنترنت، أو `download()` من `internetlib.ring`.
