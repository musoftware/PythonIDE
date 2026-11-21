# الدرس 15: مشاريع Maven وGradle والمكتبات وتصحيح الأخطاء

حتى الآن كانت مشاريعنا صغيرة: ملف أو اثنان يترجمهما `javac`. لكن مشاريع Java الحقيقية فيها مئات الملفات وتعتمد على **مكتبات** كتبها آخرون. اليوم نتعلم ثلاث مهارات يستخدمها كل مبرمج Java يوميًا:

1. تقسيم البرنامج على **أكثر من ملف**.
2. فتح مشاريع **Maven** و**Gradle** في RAD IDE وإضافة المكتبات من **Maven Central**.
3. **تصحيح الأخطاء** (debugging): إيقاف البرنامج عند سطر معين ومراقبة المتغيرات.

## الجزء الأول: برنامج من أكثر من ملف

القاعدة في Java: كل صنف `public` في ملف يحمل اسمه. في الدروس، السطر `// #file: اسم.java` يفصل بين الملفات، و«جرّبه» تنشئ كل ملف في المجلد `src` للمشروع:

```java run
public class Main {
    public static void main(String[] args) {
        System.out.println("مساحة الدائرة: " + Geometry.circleArea(2));
        System.out.println("أكبر رقم: " + Stats.max(new int[] {4, 19, 7}));
        System.out.println("المتوسط: " + Stats.average(new int[] {4, 19, 7}));
    }
}
// #file: Geometry.java
public class Geometry {
    public static double circleArea(double r) {
        return Math.round(Math.PI * r * r * 100) / 100.0;
    }
}
// #file: Stats.java
public class Stats {
    public static int max(int[] values) {
        int best = values[0];
        for (int v : values) {
            if (v > best) {
                best = v;
            }
        }
        return best;
    }

    public static double average(int[] values) {
        int sum = 0;
        for (int v : values) {
            sum += v;
        }
        return (double) sum / values.length;
    }
}
```

```text output
مساحة الدائرة: 12.57
أكبر رقم: 19
المتوسط: 10.0
```

`javac` يترجم الملفات الثلاثة معًا، و`Main` يستخدم الصنفين الآخرين باسميهما مباشرة لأنها كلها في نفس **الحزمة** (package).

### الحزم (Packages)

في المشاريع الكبيرة تُجمع الأصناف في **حزم** مثل المجلدات: أول سطر في الملف `package com.myshop.model;`، ويوضع الملف في المجلد المطابق `com/myshop/model/`. ولاستخدام صنف من حزمة أخرى نكتب `import`:

```java
package com.myshop.app;

import com.myshop.model.Product;     // صنف من حزمتنا
import java.util.List;               // صنف من مكتبة Java
```

> **تشبيه:** الحزمة مثل **العنوان البريدي**: قد يوجد شخصان اسمهما «أحمد»، لكن «أحمد - شارع النيل - القاهرة» واحد فقط. وكذلك `java.util.List` و`java.awt.List` صنفان مختلفان بنفس الاسم.

## الجزء الثاني: Maven وGradle

**Maven** و**Gradle** أداتا **بناء** (build tools). كل منهما تقرأ ملف وصف للمشروع، ثم:

- تنزّل **المكتبات** التي يحتاجها المشروع (ومكتبات تلك المكتبات) من مستودع **Maven Central** تلقائيًا.
- تترجم الكود، وتشغل الاختبارات، وتصنع ملف `.jar` جاهزًا للتوزيع.

> **تشبيه:** ملف `pom.xml` مثل **قائمة مشتريات** تعطيها لمساعد: «أحتاج مكتبة Gson الإصدار 2.11». المساعد (Maven) يذهب إلى السوق (Maven Central)، ويشتري ما في القائمة وكل ما يلزمه، ويرتبه في مطبخك.

### شكل مشروع Maven

```text
MyApp/
├── pom.xml                       ← وصف المشروع والمكتبات
└── src/
    ├── main/java/com/example/App.java
    └── test/java/com/example/AppTest.java
```

وملف `pom.xml` المبسط:

```xml
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>myapp</artifactId>
  <version>1.0</version>

  <properties>
    <maven.compiler.release>17</maven.compiler.release>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>

  <dependencies>
    <dependency>
      <groupId>com.google.code.gson</groupId>
      <artifactId>gson</artifactId>
      <version>2.11.0</version>
    </dependency>
  </dependencies>
</project>
```

كل مكتبة تُعرَّف بثلاثة أجزاء تسمى **الإحداثيات** (coordinates): `groupId:artifactId:version`، مثل `com.google.code.gson:gson:2.11.0`.

### نفس المشروع بـ Gradle

Gradle يستخدم ملف `build.gradle` (بلغة Groovy) أو `build.gradle.kts` (بلغة Kotlin) بدل XML:

```groovy
plugins {
    id 'application'
}

repositories {
    mavenCentral()
}

dependencies {
    implementation 'com.google.code.gson:gson:2.11.0'
}

application {
    mainClass = 'com.example.App'
}
```

### فتح المشروع في RAD IDE (في مكانه)

1. **File > Open Project...** (ملف > فتح مشروع...) واختر `pom.xml` أو `build.gradle`، أو **File > Open Folder...** (ملف > فتح مجلد...) واختر مجلد المشروع فتتعرف الـ IDE على نوعه تلقائيًا.
2. تفتح الـ IDE المشروع **في مكانه**: لا تنسخه ولا تضيف إليه ملفات خاصة بها، فيبقى صالحًا للفتح في IntelliJ IDEA وEclipse وNetBeans.
3. في **Solution Explorer** (مستكشف الحلول) ترى ملفات `src` و`pom.xml`.
4. اضغط **F5** للتشغيل: تبني الـ IDE بأداة المشروع نفسها (`mvn compile` أو `gradle classes`)، ثم تشغّل الصنف الذي فيه `main`. وإذا كان في المشروع أكثر من `main` فاختر واحدًا من **Native > Startup target**.
5. القائمة **Native** تعرض أوامر الأداة: `mvn compile` و`mvn test` و`mvn package` و`mvn clean`، أو `gradle build` و`gradle test` و`gradle run` و`gradle clean`.

| الملف في المجلد | كيف تبني الـ IDE |
|---|---|
| `mvnw.cmd` (Maven Wrapper) | تستخدمه أولًا |
| `pom.xml` فقط | `mvn` من `PATH` |
| `gradlew.bat` (Gradle Wrapper) | تستخدمه أولًا |
| `build.gradle` فقط | `gradle` من `PATH` أو توزيعة Gradle نزّلها Wrapper سابقًا |
| لا Maven ولا Gradle | تترجم بنفسها بـ `javac` |

> **نصيحة:** المشاريع الحديثة تأتي غالبًا مع **Wrapper** (`mvnw` أو `gradlew`)، وهو سكربت صغير ينزّل الإصدار الصحيح من الأداة تلقائيًا، فلا تحتاج إلى تثبيت Maven أو Gradle بنفسك.

### إضافة مكتبة إلى مشروع رسومي (GUI Bridge)

مشاريع **Java (GUI Bridge, JDK)** من الدرسين 13 و14 لا تحتاج إلى Maven: الـ IDE تنزّل المكتبات بنفسها من Maven Central إلى المجلد `libs/` في مشروعك.

1. **Project > Manage Packages...** (مشروع > إدارة الحزم...).
2. ابحث عن المكتبة، مثل `gson`.
3. اختر `com.google.code.gson:gson` والإصدار واضغط **Install**.

تنزل ملفات `.jar` (مع المكتبات التي تعتمد عليها) إلى `libs/`، وتُسجَّل في `libs/maven.json`، وتُضاف إلى `classpath` تلقائيًا عند الترجمة والتشغيل. بعدها تستخدمها في `Form1.java` بـ `import com.google.gson.Gson;` كأي صنف.

## الجزء الثالث: تصحيح الأخطاء (Debugging)

نوعان من الأخطاء:

- **أخطاء الترجمة** (compile errors): `javac` يرفض الكود ويخبرك بالسطر في **Error List** (قائمة الأخطاء). سهلة نسبيًا.
- **الأخطاء المنطقية** (logic errors): البرنامج يعمل لكن الناتج خطأ. هنا نحتاج إلى **المصحح** (debugger).

> **تشبيه:** المصحح مثل **زر الإيقاف المؤقت وإعادة اللقطة** في مباراة كرة القدم: توقف اللعب عند لحظة معينة، وتنظر أين كان كل لاعب، ثم تتقدم لقطة لقطة لترى أين حدث الخطأ بالضبط.

الـ IDE تصحح برامج Java عبر **JDWP** (Java Debug Wire Protocol)، البروتوكول المدمج في كل JDK، فلا تحتاج إلى تثبيت أي شيء إضافي. ويعمل ذلك في مشاريع الكونسول ومشاريع Maven وGradle والمشاريع الرسومية.

### برنامج فيه خطأ منطقي

هذا البرنامج يُفترض أن يحسب متوسط الدرجات، لكن الناتج غريب:

```java run
public class Main {
    public static void main(String[] args) {
        int[] grades = { 90, 80, 75 };
        int sum = 0;
        for (int i = 0; i < grades.length; i++) {
            sum += grades[i];
        }
        double average = sum / grades.length;   // الخطأ هنا!
        System.out.println("المتوسط = " + average);
    }
}
```

```text output
المتوسط = 81.0
```

المتوسط الحقيقي `245 ÷ 3 = 81.67`، فلماذا ظهر `81.0`؟ لنستخدم المصحح لنكتشف ذلك.

### الخطوة 1: نقطة توقف (Breakpoint)

1. اضغط «افتح في المحرر» فوق المثال.
2. ضع المؤشر على السطر `double average = ...` واضغط **F9**: **Debug > Toggle Breakpoint** (تصحيح الأخطاء > تبديل نقطة التوقف). تظهر دائرة حمراء في الهامش.

### الخطوة 2: التشغيل مع التصحيح

اضغط **F5**: **Debug > Start Debugging / Continue** (تصحيح الأخطاء > بدء تصحيح الأخطاء / متابعة). تترجم الـ IDE المشروع مع معلومات التصحيح، وتشغله مع JDWP، ويتوقف البرنامج **قبل** تنفيذ السطر المعلّم، ويظهر السطر بلون مميز.

### الخطوة 3: راقب المتغيرات

- نافذة **Locals** (المتغيرات المحلية): تعرض كل المتغيرات وقيمها الآن: `sum = 245`، و`grades` مصفوفة من 3 عناصر.
- نافذة **Call Stack** (مكدس الاستدعاءات): تعرض سلسلة الدوال التي أوصلتنا إلى هذا السطر.
- نافذة **Watch** (المراقبة): أضف تعبيرًا مثل `sum / grades.length` فترى `81`، ثم `sum / 3.0` فترى `81.666...`. وجدنا السبب: **قسمة عددين صحيحين** تعطي عددًا صحيحًا، ثم يُحوَّل إلى `double` بعد ضياع الكسر!

### الخطوة 4: التنقل خطوة بخطوة

| المفتاح | الأمر | الاسم العربي | ماذا يفعل |
|---|---|---|---|
| `F10` | Step Over | خطوة فوق | ينفذ السطر الحالي وينتقل إلى التالي |
| `F11` | Step Into | خطوة إلى الداخل | يدخل داخل الدالة المستدعاة في السطر |
| `Shift+F11` | Step Out | خطوة إلى الخارج | يكمل الدالة الحالية ويعود إلى من استدعاها |
| `F5` | Continue | متابعة | يكمل حتى نقطة التوقف التالية |
| `Shift+F5` | Stop Debugging | إيقاف تصحيح الأخطاء | ينهي البرنامج |

### الإصلاح

```java run
public class Main {
    public static void main(String[] args) {
        int[] grades = { 90, 80, 75 };
        int sum = 0;
        for (int i = 0; i < grades.length; i++) {
            sum += grades[i];
        }
        double average = (double) sum / grades.length;
        System.out.printf("المتوسط = %.2f%n", average);
    }
}
```

```text output
المتوسط = 81.67
```

### تصحيح البرامج الرسومية

نفس الخطوات تعمل في مشاريع **Java (GUI Bridge)**: ضع نقطة توقف داخل `btnHello_Click` في `Form1.java` واضغط F5، ثم اضغط الزر في نافذة برنامجك، فيتوقف التنفيذ عند السطر وترى القيم في Locals.

## نصائح للتصحيح

- **اقرأ رسالة الاستثناء كاملة:** نوعه (`NullPointerException`...) والسطر الأول من **stack trace** الذي يذكر ملفك يدلانك على المكان مباشرة.
- **اطبع القيم** بـ `System.out.println` في المواضع المشكوك فيها، فهي أبسط طرق التصحيح.
- **قسّم المشكلة:** علّق نصف الكود واختبر، ثم ضيّق الدائرة.

## تمارين

### التمرين 1

هذا البرنامج يجب أن يطبع الأعداد الزوجية من 2 إلى 10، لكنه يطبع شيئًا آخر. استخدم المصحح (أو فكّر) لتجد الخطأ وتصلحه.

```java exercise
public class Main {
    public static void main(String[] args) {
        for (int i = 1; i <= 10; i++) {
            if (i % 2 == 1) {
                System.out.print(i + " ");
            }
        }
        System.out.println();
    }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        for (int i = 1; i <= 10; i++) {
            if (i % 2 == 0) {
                System.out.print(i + " ");
            }
        }
        System.out.println();
    }
}
```

```text output
2 4 6 8 10
```

### التمرين 2

قسّم البرنامج على ملفين: انقل الدالة `countVowels` إلى صنف جديد اسمه `TextTools` في ملف `TextTools.java`، وأصلح الخطأ فيها: يجب أن تعد الحروف المتحركة الإنجليزية الكبيرة أيضًا.

```java exercise
public class Main {
    public static void main(String[] args) {
        System.out.println(countVowels("Hello World"));
        System.out.println(countVowels("AEIOU"));
    }

    static int countVowels(String s) {
        int count = 0;
        for (char c : s.toCharArray()) {
            if ("aeiou".indexOf(c) >= 0) {
                count++;
            }
        }
        return count;
    }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        System.out.println(TextTools.countVowels("Hello World"));
        System.out.println(TextTools.countVowels("AEIOU"));
    }
}
// #file: TextTools.java
public class TextTools {
    public static int countVowels(String s) {
        int count = 0;
        for (char c : s.toLowerCase().toCharArray()) {
            if ("aeiou".indexOf(c) >= 0) {
                count++;
            }
        }
        return count;
    }
}
```

```text output
3
5
```

## اختبر نفسك

```quiz
{"question": "ما الملف الذي يصف مشروع Maven ومكتباته؟", "choices": ["build.gradle", "pom.xml", ".classpath", "maven.json"], "answer": 1, "explanation": "Maven يقرأ pom.xml، وGradle يقرأ build.gradle أو build.gradle.kts."}
```

```quiz
{"question": "ماذا تعني com.google.code.gson:gson:2.11.0؟", "choices": ["مسار ملف على جهازك", "إحداثيات مكتبة: groupId ثم artifactId ثم الإصدار", "أمر ترجمة", "اسم حزمة Java داخل الكود"], "answer": 1, "explanation": "كل مكتبة في Maven Central تُعرّف بـ groupId:artifactId:version."}
```

```quiz
{"question": "عند فتح pom.xml في RAD IDE، ماذا يحدث لملفات المشروع؟", "choices": ["تُنسخ إلى مشروع RAD IDE جديد", "يُفتح المشروع في مكانه دون إضافة ملفات خاصة بالـ IDE", "تُحذف ملفات Maven", "يُحوَّل إلى Gradle"], "answer": 1, "explanation": "الفتح في المكان يترك المشروع كما هو، فيبقى صالحًا لـ IntelliJ وEclipse وNetBeans."}
```

```quiz
{"question": "لماذا طبع البرنامج 81.0 بدل 81.67؟", "choices": ["خطأ في المصفوفة", "قسمة عددين صحيحين تحذف الكسر قبل التحويل إلى double", "الحلقة لم تكتمل", "printf غير موجودة"], "answer": 1, "explanation": "sum / grades.length قسمة int على int، والحل (double) sum / grades.length."}
```

## الخلاصة

- كل صنف `public` في ملف باسمه، والحزم (`package` و`import`) تنظم المشاريع الكبيرة.
- **Maven** (`pom.xml`) و**Gradle** (`build.gradle`) ينزّلان المكتبات من Maven Central ويبنيان المشروع، وRAD IDE تفتحهما **في مكانهما** وتعرض أوامرهما في القائمة **Native**.
- في المشاريع الرسومية: **Project > Manage Packages...** ينزّل المكتبات إلى `libs/`.
- المصحح عبر JDWP: `F9` نقطة توقف، و`F5` تشغيل ومتابعة، و`F10` / `F11` / `Shift+F11` للتنقل، مع **Locals** و**Watch** و**Call Stack**.
