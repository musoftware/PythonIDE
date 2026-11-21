# الدرس 2: برنامجك الأول سطرًا سطرًا

في الدرس السابق شغّلنا برنامجًا يطبع رسالة. اليوم نفهم كل كلمة فيه، ونتعلم التعليقات ورموز الهروب وطرق الطباعة المختلفة.

## البرنامج كاملًا

```java run
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
```

```text output
Hello, World!
```

## الشرح سطرًا سطرًا

### `public class Main`

في Java **كل** الكود يعيش داخل **صنف** (class). الصنف مثل **غرفة** في بيت البرنامج، وسنتعلمه بالتفصيل في الدرس العاشر.

- `public` تعني أن الصنف متاح للجميع.
- `Main` اسم الصنف، ويجب أن يكون الملف اسمه `Main.java`.

### `public static void main(String[] args)`

هذه هي **نقطة البداية**: أول دالة تُنفذ عندما يبدأ البرنامج. يجب أن تُكتب بهذا الشكل تمامًا:

- `public`: متاحة لـ JVM لكي تستدعيها.
- `static`: تخص الصنف نفسه ولا تحتاج إلى إنشاء كائن.
- `void`: لا ترجع قيمة.
- `main`: الاسم بحروف صغيرة.
- `String[] args`: مصفوفة نصوص فيها وسائط سطر الأوامر (لن نحتاجها الآن).

### الأقواس المعقوصة `{ }`

كل زوج `{ }` يحدد **كتلة** (block): جسم الصنف، وجسم الدالة.

### `System.out.println("Hello, World!");`

- `System.out` هو **مخرج الكونسول** (الشاشة النصية).
- `.println` تكتب ثم تنزل سطرًا جديدًا (print line).
- `"Hello, World!"` نص (String) بين علامتي تنصيص.
- `;` تنهي التعليمة.

> **نصيحة:** في محرر الـ IDE اكتب `sout` أو `System.` ثم انتظر قائمة الإكمال التلقائي، فهي توفر عليك الكتابة وتمنع الأخطاء الإملائية.

## `print` و`println` و`printf`

```java run
public class Main {
    public static void main(String[] args) {
        System.out.print("واحد ");
        System.out.print("اثنان ");
        System.out.println("ثلاثة");
        System.out.println("سطر جديد");
        System.out.printf("العمر: %d سنة، الطول: %.2f متر%n", 20, 1.756);
    }
}
```

```text output
واحد اثنان ثلاثة
سطر جديد
العمر: 20 سنة، الطول: 1.76 متر
```

- `print` تكتب **دون** النزول إلى سطر جديد، و`println` تكتب ثم تنزل.
- `printf` تطبع **بتنسيق**: `%d` لعدد صحيح، و`%.2f` لعدد عشري برقمين بعد الفاصلة، و`%s` لنص، و`%n` لسطر جديد.

## رموز الهروب (Escape Sequences)

```java run
public class Main {
    public static void main(String[] args) {
        System.out.println("السطر الأول\nالسطر الثاني");
        System.out.println("الاسم:\tسارة");
        System.out.println("قال: \"مرحبًا\"");
        System.out.println("C:\\Projects\\app");
    }
}
```

```text output
السطر الأول
السطر الثاني
الاسم:	سارة
قال: "مرحبًا"
C:\Projects\app
```

| الرمز | معناه |
|---|---|
| `\n` | سطر جديد |
| `\t` | مسافة جدولة (Tab) |
| `\"` | علامة تنصيص داخل النص |
| `\\` | شرطة مائلة عكسية واحدة |

## دمج النصوص والأرقام

علامة `+` بين نص وأي قيمة **تدمجهما** في نص واحد:

```java run
public class Main {
    public static void main(String[] args) {
        String name = "ليلى";
        int age = 12;
        System.out.println("اسمي " + name + " وعمري " + age + " سنة");
        System.out.println("بعد 5 سنوات: " + (age + 5));
        System.out.println("بدون أقواس: " + age + 5);
    }
}
```

```text output
اسمي ليلى وعمري 12 سنة
بعد 5 سنوات: 17
بدون أقواس: 125
```

انتبه للسطر الأخير! `"..." + age + 5` تُقرأ من اليسار: النص + 12 = نص، ثم النص + 5 = نص، فتظهر `125`. الأقواس `(age + 5)` تجعل الجمع يحدث أولًا. وسنشرح `String` و`int` في الدرس القادم.

## التعليقات (Comments)

```java run
public class Main {
    // تعليق من سطر واحد

    /*
       تعليق
       من عدة أسطر
    */

    /** تعليق توثيق (Javadoc): يصف الصنف أو الدالة */
    public static void main(String[] args) {
        System.out.println("التعليقات لا تظهر في الناتج"); // تعليق في آخر السطر
        // System.out.println("هذا السطر معطّل");
    }
}
```

```text output
التعليقات لا تظهر في الناتج
```

## أخطاء شائعة

### نسيان الفاصلة المنقوطة

<!-- compile-error -->
```java
public class Main {
    public static void main(String[] args) {
        System.out.println("مرحبا")
    }
}
```

```text
Main.java:3: error: ';' expected
        System.out.println("مرحبا")
                                   ^
```

**المعنى:** «كان متوقعًا وجود `;`». ورقم `3` هو رقم السطر، والسهم `^` يشير إلى المكان. انقر مرتين على الخطأ في نافذة Output لتنتقل إليه.

### خطأ إملائي في اسم الدالة

<!-- compile-error -->
```java
public class Main {
    public static void main(String[] args) {
        System.out.printn("مرحبا");
    }
}
```

```text
Main.java:3: error: cannot find symbol
        System.out.printn("مرحبا");
                  ^
  symbol:   method printn(String)
```

**المعنى:** «لا أجد الرمز `printn`». تأكد من الإملاء وحالة الأحرف.

### `main` بحرف كبير

`public static void Main(String[] args)` تُترجم بلا أخطاء، لكن عند التشغيل يظهر: `Error: Main method not found in class Main`، لأن JVM تبحث عن `main` بحروف صغيرة.

## تمارين

### التمرين 1

اطبع البطاقة التالية باستخدام `\t` بين العنوان والقيمة:

```java exercise
public class Main {
    public static void main(String[] args) {
        // الاسم:	سارة
        // المادة:	Java
        // الدرجة:	95
    }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        System.out.println("الاسم:\tسارة");
        System.out.println("المادة:\tJava");
        System.out.println("الدرجة:\t95");
    }
}
```

```text output
الاسم:	سارة
المادة:	Java
الدرجة:	95
```

### التمرين 2

استخدم `printf` لطباعة سعر منتج `1250.5` برقمين عشريين بالشكل `السعر: 1250.50 جنيه`.

```java exercise
public class Main {
    public static void main(String[] args) {
        double price = 1250.5;
        // اطبع: السعر: 1250.50 جنيه
    }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        double price = 1250.5;
        System.out.printf("السعر: %.2f جنيه%n", price);
    }
}
```

```text output
السعر: 1250.50 جنيه
```

### التمرين 3

اطبع مثلثًا من النجوم بثلاثة أسطر باستخدام `System.out.print` واحدة فقط ورموز `\n`.

```java exercise
public class Main {
    public static void main(String[] args) {
        // *
        // **
        // ***
    }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        System.out.print("*\n**\n***\n");
    }
}
```

```text output
*
**
***
```

## اختبر نفسك

```quiz
{"question": "ما الشكل الصحيح لدالة البداية في Java؟", "choices": ["static void Main()", "public static void main(String[] args)", "void start()", "public main()"], "answer": 1, "explanation": "JVM تبحث عن public static void main(String[] args) بالضبط."}
```

```quiz
{"question": "ماذا يطبع System.out.println(\"A\" + 1 + 2);؟", "choices": ["A3", "A12", "3A", "خطأ"], "answer": 1, "explanation": "الدمج من اليسار: \"A\" + 1 = \"A1\" ثم \"A1\" + 2 = \"A12\"."}
```

```quiz
{"question": "ماذا يعني %.2f في printf؟", "choices": ["عدد صحيح من خانتين", "عدد عشري برقمين بعد الفاصلة", "نص من حرفين", "النسبة المئوية"], "answer": 1, "explanation": "f للعدد العشري، و.2 لعدد الأرقام بعد الفاصلة."}
```

## الخلاصة

- كل كود Java داخل صنف، والبداية من `public static void main(String[] args)`.
- `print` و`println` و`printf` للطباعة، ورموز الهروب مثل `\n` و`\t`.
- `+` تدمج النصوص، وانتبه لترتيب الدمج والأقواس.
- التعليقات `//` و`/* */` و`/** */`.
