# الدرس 4: MySQL و PostgreSQL والخوادم المحلية

**في هذا الدرس ستتعلم:**

- الفرق بين **قاعدة بيانات في ملف** (SQLite) و**خادم قواعد بيانات** (MySQL / MariaDB و PostgreSQL).
- تشغيل خادم محلي من داخل البيئة بضغطة زر، بدون تثبيت خدمة ويندوز.
- الاتصال بخادم موجود (على جهازك أو على الإنترنت) وحفظ كلمة المرور بأمان.
- ما يحتاجه برنامجك ليتصل بهذه الخوادم.

## مطبخ البيت ومطبخ المطعم

- **SQLite** مثل **مطبخ البيت**: صغير، في متناول يدك، يكفي أسرتك (برنامج واحد على جهاز واحد).
- **MySQL / MariaDB** و **PostgreSQL** مثل **مطبخ مطعم**: خادم يعمل طوال الوقت، يخدم مئات الزبائن (البرامج والمستخدمين) في وقت واحد، وعليه موظف أمن (اسم مستخدم وكلمة مرور).

| | SQLite | MySQL / MariaDB | PostgreSQL |
|---|---|---|---|
| أين البيانات؟ | ملف `.db` | داخل الخادم | داخل الخادم |
| يحتاج تشغيل خادم؟ | لا | نعم | نعم |
| مستخدمون كثيرون معًا | محدود | ممتاز | ممتاز |
| مناسب لـ | برامج سطح المكتب، والتجارب | مواقع الويب، والأنظمة المشتركة | الأنظمة الكبيرة والتقارير المعقدة |
| مكتبة Python | مدمجة (`sqlite3`) | `pymysql` | `psycopg` |

والجميل: لغة **SQL** نفسها تقريبًا في الثلاثة، فاستعلامات الدرس السابق تعمل عليها.

## خادم محلي بضغطة زر

لا تحتاج تثبيت MySQL كخدمة ويندوز تعمل دائمًا. البيئة تشغّل الخادم **عندما تطلب**، وتوقفه عندما تطلب أو عند إغلاق البيئة.

### الخطوات

1. افتح **Tools > Databases > Start local MariaDB/MySQL** (تشغيل MariaDB/MySQL المحلي)، أو **Start local PostgreSQL** (تشغيل PostgreSQL المحلي).
   - أو من نافذة **Databases**: زر **Local Servers** (الخوادم المحلية) في شريطها.
2. **أول مرة** تنشئ البيئة مجلد البيانات وتجهّز الخادم (قد تستغرق دقيقة).
3. يظهر اتصال جديد في الشجرة باسم المستخدم **`radide`** وقاعدة بيانات اسمها **`radide`**. ابدأ العمل فورًا.

### تفاصيل تهمك

| الشيء | أين؟ |
|---|---|
| برامج الخادم | `%LOCALAPPDATA%\RADIDE\toolchains\mariadb` و `...\pgsql`، أو خادم مثبت عندك |
| البيانات | `%LOCALAPPDATA%\RADIDE\db\<المحرك>\data` |
| من يستطيع الاتصال؟ | جهازك فقط (`127.0.0.1`)، لا أحد من الشبكة |
| كلمة المرور | عشوائية تُنشأ أول مرة، محفوظة **مشفّرة** بجانب مجلد البيانات |

في قائمة **Local Servers** أيضًا: **Stop local ...** للإيقاف، و **Copy ... Password** لنسخ كلمة المرور (لتضعها في برنامج آخر مثلًا)، و **Server Status...** لحالة الخوادم.

### إذا لم يكن الخادم موجودًا

يظهر الأمر بهذا الشكل: **Start local MariaDB/MySQL (not installed)...**. اضغطه فتعرض البيئة رسالة بالخطوات:

- **MariaDB**: نزّل "Windows x86_64 ZIP" من `mariadb.org/download` وفك ضغطه في `%LOCALAPPDATA%\RADIDE\toolchains\mariadb`.
- **PostgreSQL**: نزّل "zip archive" للويندوز من موقع EnterpriseDB، وضع مجلد `pgsql` في `%LOCALAPPDATA%\RADIDE\toolchains\pgsql`.

## الاتصال بخادم موجود

1. **Tools > Databases > Add Connection...** (إضافة اتصال...).
2. **Type:** MySQL أو PostgreSQL.
3. **Server:** (مثل `localhost` أو عنوان الخادم)، و **Port:** (`3306` لـ MySQL و `5432` لـ PostgreSQL).
4. **User:** و **Password:**، ثم **List Databases** لاختيار القاعدة في **Database:**.
5. **Test Connection**، ثم **OK**.

> ⚠️ **كلمات المرور:** الاتصال يُحفظ في `project.radproj` **بدون** كلمة المرور. إذا فعّلت **Remember the password** تُحفظ مشفّرة في إعدادات البيئة على جهازك فقط. لذلك يمكنك رفع المشروع إلى GitHub بأمان.

## ماذا يحتاج برنامجك؟

- **برامج Python** تحتاج مكتبة الاتصال: `pymysql` لـ MySQL، و `psycopg[binary]` لـ PostgreSQL. ثبّتها من **Project > Manage Packages...** (مشروع > إدارة الحزم...). وإذا كانت ناقصة، تكتب البيئة بجانب اسم الاتصال في معالج مصادر البيانات `driver missing`.
- **كلمة المرور في البرنامج المولَّد** لا تُكتب في الكود أبدًا: يأخذها من متغير بيئة، أو من ملف `connections.json` بجانب البرنامج، أو يسأل المستخدم.

## SQL واحد لكل المحركات

أغلب ما كتبناه يعمل في الثلاثة كما هو. هذا المثال يعمل على SQLite، ويمكنك نسخ استعلاماته كما هي إلى لسان استعلام على خادم MariaDB أو PostgreSQL المحلي:

```vb run
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=portable.db"
    cn.Execute "DROP TABLE IF EXISTS Books"
    cn.Execute "CREATE TABLE Books (Id INTEGER PRIMARY KEY, Title VARCHAR(100) NOT NULL, Pages INTEGER)"
    cn.Execute "INSERT INTO Books (Title, Pages) VALUES ('Kalila wa Dimna', 320)"
    cn.Execute "INSERT INTO Books (Title, Pages) VALUES ('Al-Ayyam', 210)"
    cn.Execute "UPDATE Books SET Pages = Pages + 10 WHERE Title = 'Al-Ayyam'"
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT Title, Pages FROM Books ORDER BY Pages DESC", cn
    Do While Not rs.EOF
        Debug.Print rs("Title") & ": " & rs("Pages") & " صفحة"
        rs.MoveNext
    Loop
    rs.Close
    cn.Close
End Sub
```

```text output
Kalila wa Dimna: 320 صفحة
Al-Ayyam: 220 صفحة
```

الفروق الصغيرة بين المحركات تظهر في أشياء مثل الترقيم التلقائي: `INTEGER PRIMARY KEY` في SQLite، و `AUTO_INCREMENT` في MySQL، و `SERIAL` أو `GENERATED ... AS IDENTITY` في PostgreSQL.

## أخطاء شائعة

- **"Connection refused":** الخادم متوقف. شغّله من **Local Servers**.
- **المنفذ مشغول:** برنامج آخر (خادم MySQL مثبت مثلًا) يستخدم 3306. أوقفه أو استخدم المثبت نفسه في **Add Connection...**.
- **رفع كلمة المرور إلى GitHub:** لا تكتبها في الكود ولا في ملفات المشروع.
- **نسيان مكتبة الاتصال في برنامج Python:** ثبّت `pymysql` أو `psycopg` من **Manage Packages...**.

## تمرين

### تمرين 1: أطول كتاب

أضف إلى المثال كتابًا ثالثًا (`Rijal fi al-Shams`، 150 صفحة)، ثم اطبع عنوان الكتاب الأكبر عدد صفحات فقط بهذا الشكل: `الأطول: Kalila wa Dimna`.
استخدم `ORDER BY Pages DESC LIMIT 1`.

```vb exercise
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=portable.db"
    cn.Execute "DROP TABLE IF EXISTS Books"
    cn.Execute "CREATE TABLE Books (Id INTEGER PRIMARY KEY, Title VARCHAR(100) NOT NULL, Pages INTEGER)"
    cn.Execute "INSERT INTO Books (Title, Pages) VALUES ('Kalila wa Dimna', 320)"
    cn.Execute "INSERT INTO Books (Title, Pages) VALUES ('Al-Ayyam', 210)"
    ' أكمل
    cn.Close
End Sub
```

```vb solution
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=portable.db"
    cn.Execute "DROP TABLE IF EXISTS Books"
    cn.Execute "CREATE TABLE Books (Id INTEGER PRIMARY KEY, Title VARCHAR(100) NOT NULL, Pages INTEGER)"
    cn.Execute "INSERT INTO Books (Title, Pages) VALUES ('Kalila wa Dimna', 320)"
    cn.Execute "INSERT INTO Books (Title, Pages) VALUES ('Al-Ayyam', 210)"
    cn.Execute "INSERT INTO Books (Title, Pages) VALUES ('Rijal fi al-Shams', 150)"
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT Title FROM Books ORDER BY Pages DESC LIMIT 1", cn
    Debug.Print "الأطول: " & rs("Title")
    rs.Close
    cn.Close
End Sub
```

```text output
الأطول: Kalila wa Dimna
```

### مهمة عملية: خادم PostgreSQL محلي

1. **Tools > Databases > Start local PostgreSQL** (أو اتبع رسالة التثبيت إن ظهرت).
2. افتح **New Query** على الاتصال الجديد، والصق جمل `CREATE TABLE` و `INSERT` من المثال، وغيّر `INTEGER PRIMARY KEY` إلى `SERIAL PRIMARY KEY`.
3. شغّل `SELECT * FROM Books` وقارن النتيجة.
4. من **Local Servers** اختر **Stop local PostgreSQL**.

## اختبر نفسك

```quiz
{"question": "ما المستخدم وقاعدة البيانات اللذان ينشئهما الخادم المحلي؟", "choices": ["`root` و `mysql`", "`radide` و `radide`", "`admin` و `test`", "لا ينشئ شيئًا"], "answer": 1, "explanation": "الخادم المحلي ينشئ المستخدم radide وقاعدة radide بكلمة مرور عشوائية مشفّرة."}
```

```quiz
{"question": "من يستطيع الاتصال بالخادم المحلي الذي تشغّله البيئة؟", "choices": ["أي جهاز على الإنترنت", "جهازك فقط (127.0.0.1)", "أجهزة الشبكة المحلية كلها", "لا أحد"], "answer": 1, "explanation": "الخادم يستمع على 127.0.0.1 فقط."}
```

```quiz
{"question": "برنامج Python متصل بـ MySQL لا يعمل وتظهر \"driver missing\". ما الحل؟", "choices": ["إعادة تثبيت ويندوز", "تثبيت `pymysql` من Project > Manage Packages...", "حذف الجدول", "استخدام Excel"], "answer": 1, "explanation": "كل محرك يحتاج مكتبة اتصال: pymysql لـ MySQL و psycopg لـ PostgreSQL."}
```

## الخلاصة

- SQLite ملف، و MySQL / PostgreSQL خوادم لمستخدمين كثيرين، و SQL واحد تقريبًا.
- **Start local MariaDB/MySQL** و **Start local PostgreSQL**: خادم عند الطلب، على `127.0.0.1`، بالمستخدم `radide`.
- **Add Connection...** لخادم موجود، وكلمة المرور مشفّرة خارج المشروع.
- برامج Python تحتاج `pymysql` أو `psycopg`، وكلمات المرور لا تُكتب في الكود.
