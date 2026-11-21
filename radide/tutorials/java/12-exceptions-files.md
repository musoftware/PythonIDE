# الدرس 12: الاستثناءات والملفات

البرامج الحقيقية تواجه مفاجآت: المستخدم يكتب حروفًا بدل رقم، أو الملف غير موجود، أو القسمة على صفر. اليوم نتعلم كيف **نتعامل مع الأخطاء** بأدب بدل أن ينهار البرنامج، وكيف **نحفظ البيانات في ملفات** ونقرؤها.

> **تشبيه:** الاستثناء مثل **جرس الإنذار** في المبنى: عندما يحدث شيء غير طبيعي يرن الجرس، فيتوقف العمل العادي ويذهب الجميع إلى خطة الطوارئ (`catch`). وإذا لم توجد خطة طوارئ، يُخلى المبنى كله (ينهار البرنامج).

## ماذا يحدث بدون معالجة؟

```java
int[] nums = {1, 2, 3};
System.out.println(nums[5]);
```

يتوقف البرنامج برسالة طويلة:

```text
Exception in thread "main" java.lang.ArrayIndexOutOfBoundsException: Index 5 out of bounds for length 3
	at Main.main(Main.java:4)
```

اقرأها هكذا: **نوع الاستثناء** (`ArrayIndexOutOfBoundsException`)، ثم **السبب** (الفهرس 5 والطول 3)، ثم **مكان الخطأ** (`Main.java` السطر 4).

## `try` و`catch`

```java run
public class Main {
    public static void main(String[] args) {
        String[] inputs = { "25", "abc", "0" };
        for (String text : inputs) {
            try {
                int n = Integer.parseInt(text);
                int result = 100 / n;
                System.out.println("100 / " + n + " = " + result);
            } catch (NumberFormatException e) {
                System.out.println("'" + text + "' ليس رقمًا");
            } catch (ArithmeticException e) {
                System.out.println("لا يمكن القسمة على صفر");
            }
        }
        System.out.println("البرنامج مستمر بأمان");
    }
}
```

```text output
100 / 25 = 4
'abc' ليس رقمًا
لا يمكن القسمة على صفر
البرنامج مستمر بأمان
```

- الكود الذي قد يفشل يوضع داخل `try`.
- عند حدوث استثناء يقفز التنفيذ مباشرة إلى `catch` المناسب لنوعه، ويُترك باقي `try`.
- يمكن كتابة أكثر من `catch`، أو جمعها: `catch (NumberFormatException | ArithmeticException e)`.

## `finally`: يعمل دائمًا

```java run
public class Main {
    public static void main(String[] args) {
        System.out.println(divide(10, 2));
        System.out.println(divide(10, 0));
    }

    static String divide(int a, int b) {
        try {
            return "الناتج " + (a / b);
        } catch (ArithmeticException e) {
            return "خطأ: " + e.getMessage();
        } finally {
            System.out.println("(انتهت محاولة قسمة " + a + " على " + b + ")");
        }
    }
}
```

```text output
(انتهت محاولة قسمة 10 على 2)
الناتج 5
(انتهت محاولة قسمة 10 على 0)
خطأ: / by zero
```

`finally` تعمل سواء نجح `try` أو فشل، حتى مع `return`. مكانها المناسب لإغلاق الملفات والاتصالات.

## رمي استثناء بنفسك: `throw`

```java run
public class Main {
    public static void main(String[] args) {
        int[] ages = { 20, -3, 150 };
        for (int age : ages) {
            try {
                setAge(age);
                System.out.println("تم حفظ العمر " + age);
            } catch (IllegalArgumentException e) {
                System.out.println("مرفوض: " + e.getMessage());
            }
        }
    }

    static void setAge(int age) {
        if (age < 0 || age > 120) {
            throw new IllegalArgumentException("العمر يجب أن يكون بين 0 و120");
        }
    }
}
```

```text output
تم حفظ العمر 20
مرفوض: العمر يجب أن يكون بين 0 و120
مرفوض: العمر يجب أن يكون بين 0 و120
```

## الاستثناءات المفحوصة (checked) و`throws`

Java تقسم الاستثناءات إلى نوعين:

| النوع | أمثلة | هل يجبرك المترجم على معالجته؟ |
|---|---|---|
| **غير مفحوص** (unchecked) | `NullPointerException`، `ArithmeticException`، `NumberFormatException` | لا |
| **مفحوص** (checked) | `IOException`، `FileNotFoundException` | نعم: `try/catch` أو `throws` |

الدالة التي قد ترمي استثناءً مفحوصًا تعلن ذلك في توقيعها بـ `throws`:

```java
static String readFirstLine(String file) throws IOException {
    return Files.readAllLines(Path.of(file)).get(0);
}
```

إذا نسيت يظهر خطأ الترجمة: `unreported exception IOException; must be caught or declared to be thrown`.

## الكتابة في ملف والقراءة منه

الحزمة `java.nio.file` فيها الصنف `Files` بدوال بسيطة جدًا:

```java run
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public class Main {
    public static void main(String[] args) {
        Path file = Path.of("notes.txt");
        try {
            Files.writeString(file, "السطر الأول\n");
            Files.writeString(file, "السطر الثاني\n", java.nio.file.StandardOpenOption.APPEND);
            Files.write(file, List.of("ثالث", "رابع"), java.nio.file.StandardOpenOption.APPEND);

            List<String> lines = Files.readAllLines(file);
            System.out.println("عدد الأسطر: " + lines.size());
            for (int i = 0; i < lines.size(); i++) {
                System.out.println((i + 1) + ": " + lines.get(i));
            }
            Files.delete(file);
            System.out.println("هل الملف موجود؟ " + Files.exists(file));
        } catch (IOException e) {
            System.out.println("خطأ في الملف: " + e.getMessage());
        }
    }
}
```

```text output
عدد الأسطر: 4
1: السطر الأول
2: السطر الثاني
3: ثالث
4: رابع
هل الملف موجود؟ false
```

| الدالة | وظيفتها |
|---|---|
| `Files.writeString(path, text)` | تكتب النص (وتمسح القديم) |
| `Files.writeString(path, text, StandardOpenOption.APPEND)` | تضيف في النهاية |
| `Files.write(path, list)` | تكتب قائمة أسطر |
| `Files.readString(path)` | تقرأ الملف كله نصًا واحدًا |
| `Files.readAllLines(path)` | تقرأ الأسطر في `List<String>` |
| `Files.exists(path)` / `Files.delete(path)` | الفحص / الحذف |

الملف يُنشأ في **مجلد التشغيل الحالي**، وهو مجلد المشروع عند التشغيل من RAD IDE.

## ملف غير موجود

```java run
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;

public class Main {
    public static void main(String[] args) {
        try {
            String text = Files.readString(Path.of("missing.txt"));
            System.out.println(text);
        } catch (NoSuchFileException e) {
            System.out.println("الملف غير موجود: " + e.getMessage());
        } catch (IOException e) {
            System.out.println("خطأ آخر: " + e);
        }
    }
}
```

```text output
الملف غير موجود: missing.txt
```

## `try`-with-resources: إغلاق تلقائي

القارئات والكاتبات (`BufferedReader` و`BufferedWriter`) يجب إغلاقها. اكتبها بين قوسين بعد `try` فتُغلق تلقائيًا:

```java run
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

public class Main {
    public static void main(String[] args) throws IOException {
        Path file = Path.of("scores.csv");
        try (BufferedWriter w = Files.newBufferedWriter(file)) {
            w.write("Ali,80\n");
            w.write("Mona,95\n");
            w.write("Hany,70\n");
        }
        int total = 0, count = 0;
        try (BufferedReader r = Files.newBufferedReader(file)) {
            String line;
            while ((line = r.readLine()) != null) {
                String[] parts = line.split(",");
                total += Integer.parseInt(parts[1]);
                count++;
            }
        }
        System.out.println("المتوسط: " + (double) total / count);
        Files.delete(file);
    }
}
```

```text output
المتوسط: 81.66666666666667
```

هنا كتبنا `throws IOException` على `main` نفسها لنختصر، فأي خطأ ملفات سيوقف البرنامج برسالته.

## أخطاء شائعة

- **`catch (Exception e)` الفارغ:** يبتلع كل الأخطاء بصمت فلا تعرف ما حدث. اطبع الرسالة على الأقل.
- **ترتيب `catch` خاطئ:** الأعم (`Exception`) يجب أن يكون بعد الأخص (`IOException`)، وإلا يظهر `exception IOException has already been caught`.
- **نسيان إغلاق الملف:** استخدم `try`-with-resources دائمًا مع القارئات والكاتبات.

## تمارين

### التمرين 1

الدالة `safeParse` يجب أن ترجع الرقم، أو `-1` إذا لم يكن النص رقمًا صحيحًا. أكملها.

```java exercise
public class Main {
    public static void main(String[] args) {
        System.out.println(safeParse("42"));
        System.out.println(safeParse("4x2"));
        System.out.println(safeParse(""));
    }

    static int safeParse(String text) {
        return Integer.parseInt(text);
    }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        System.out.println(safeParse("42"));
        System.out.println(safeParse("4x2"));
        System.out.println(safeParse(""));
    }

    static int safeParse(String text) {
        try {
            return Integer.parseInt(text);
        } catch (NumberFormatException e) {
            return -1;
        }
    }
}
```

```text output
42
-1
-1
```

### التمرين 2

اكتب ثلاثة أسماء في الملف `names.txt` (اسم في كل سطر)، ثم اقرأها واطبعها مرقمة، ثم احذف الملف.

```java exercise
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public class Main {
    public static void main(String[] args) throws IOException {
        Path file = Path.of("names.txt");
        // اكتب ثم اقرأ ثم احذف
    }
}
```

```java solution
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public class Main {
    public static void main(String[] args) throws IOException {
        Path file = Path.of("names.txt");
        Files.write(file, List.of("سلمى", "خالد", "دينا"));
        List<String> names = Files.readAllLines(file);
        for (int i = 0; i < names.size(); i++) {
            System.out.println((i + 1) + ". " + names.get(i));
        }
        Files.delete(file);
    }
}
```

```text output
1. سلمى
2. خالد
3. دينا
```

## اختبر نفسك

```quiz
{"question": "متى يعمل جزء finally؟", "choices": ["عند النجاح فقط", "عند الفشل فقط", "دائمًا، نجح try أو فشل", "لا يعمل أبدًا"], "answer": 2, "explanation": "finally تعمل في كل الحالات، ولذلك تُستخدم لإغلاق الموارد."}
```

```quiz
{"question": "أي استثناء يجبرك المترجم على معالجته أو إعلانه بـ throws؟", "choices": ["NullPointerException", "ArithmeticException", "IOException", "NumberFormatException"], "answer": 2, "explanation": "IOException استثناء مفحوص (checked)، أما الباقي فغير مفحوصة."}
```

```quiz
{"question": "ما فائدة try (BufferedReader r = ...) { }؟", "choices": ["يجعل القراءة أسرع", "يغلق القارئ تلقائيًا عند الخروج", "يمنع كل الاستثناءات", "يقرأ الملف مرتين"], "answer": 1, "explanation": "try-with-resources يستدعي close() تلقائيًا حتى لو حدث استثناء."}
```

## الخلاصة

- `try` / `catch` / `finally` لمعالجة الأخطاء، و`throw new ...Exception("...")` لرميها.
- الاستثناءات المفحوصة (`IOException`) تحتاج `try/catch` أو `throws`.
- `Files.writeString` و`Files.readAllLines` و`Files.exists` و`Files.delete` للملفات.
- `try`-with-resources يغلق القارئات والكاتبات تلقائيًا.
