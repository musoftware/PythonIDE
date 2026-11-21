# الدرس 1: مرحبًا بك في Java وتجهيز JDK

أهلًا بك في دورة **Java** (تُنطق «جافا»). سنبدأ من الصفر تمامًا، ولا نفترض أنك كتبت سطر كود من قبل. وفي النهاية ستبني برنامجًا حقيقيًا بنافذة وأزرار وقوائم، ترسمه بالفأرة في مصمم النماذج ثم تكتب كود Java الذي يعمل عند الضغط على الأزرار.

## ما هي Java؟

**Java** لغة برمجة ظهرت سنة 1995، وهي من أكثر اللغات انتشارًا في العالم: تطبيقات أندرويد، وأنظمة البنوك والشركات الكبيرة، والخوادم، وحتى لعبة Minecraft الشهيرة مكتوبة بها.

شعار Java المشهور: **«اكتب مرة واحدة، شغّل في أي مكان»** (Write Once, Run Anywhere). كيف؟

> **تشبيه:** تخيّل أنك كتبت كتابًا بلغة عالمية وسيطة، وفي كل بلد يوجد **مترجم فوري** يقرؤه بلغة أهل البلد. كود Java يُترجم إلى لغة وسيطة اسمها **bytecode**، وفي كل جهاز (ويندوز أو لينكس أو ماك) يوجد «المترجم الفوري» **JVM** (آلة جافا الافتراضية) الذي يشغّلها.

```text
Main.java  --(javac)-->  Main.class (bytecode)  --(java / JVM)-->  البرنامج يعمل
```

## ما هو JDK؟

**JDK** (Java Development Kit) هي حزمة التطوير، وفيها:

- **`javac`**: المترجم الذي يحوّل ملفات `.java` إلى ملفات `.class`.
- **`java`**: يشغّل البرنامج على JVM.
- **المكتبة القياسية**: آلاف الأصناف الجاهزة للنصوص والملفات والتواريخ والشبكات...

## تجهيز بيئة العمل

1. ثبّت **JDK 17** أو أحدث. أسهل طريقة من نافذة الأوامر:

```text
winget install EclipseAdoptium.Temurin.17.JDK
```

2. أغلق RAD IDE وافتحها من جديد.
3. للتأكد اكتب في نافذة الأوامر `javac -version`، فيظهر مثل `javac 17.0.12`.

> **ملحوظة:** الـ IDE تبحث عن JDK تلقائيًا في `JAVA_HOME` و`PATH` والمجلدات المعتادة مثل `C:\Program Files\Eclipse Adoptium` و`%LOCALAPPDATA%\Java`. إذا لم تجده ستكتب لك ذلك في نافذة **Output** (المخرجات).

## برنامجك الأول

اضغط زر **▶ جرّبه** فوق المثال:

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

ماذا حدث عندما ضغطت «جرّبه»؟

1. أنشأت الـ IDE **مشروع Eclipse حقيقيًا** في مجلد الدروس: الملفان `.project` و`.classpath`، والكود في `src/Main.java`.
2. فتحت المشروع **في مكانه** (in place)، فظهر في **Solution Explorer** (مستكشف الحلول).
3. ترجمته بـ `javac` ثم شغّلته بـ `java`، وظهر الناتج في نافذة **Output**.

أي أن ما تتعلمه هنا يعمل كما هو في Eclipse وIntelliJ IDEA وأي مكان فيه JDK.

## العربية في الناتج

```java run
public class Main {
    public static void main(String[] args) {
        System.out.println("السلام عليكم");
        System.out.println("أنا أتعلم Java اليوم");
    }
}
```

```text output
السلام عليكم
أنا أتعلم Java اليوم
```

كل `System.out.println` تطبع سطرًا ثم تنزل إلى سطر جديد. والنص يوضع بين علامتي تنصيص `"..."`.

## قاعدة مهمة: اسم الملف = اسم الصنف

في Java يجب أن يكون اسم الملف مطابقًا لاسم الصنف العام (`public class`). فالصنف `public class Main` يجب أن يكون في ملف اسمه `Main.java` بالضبط، بنفس حالة الأحرف. الـ IDE تسمي الملف تلقائيًا في أمثلة الدروس.

## جولة سريعة في الـ IDE

| النافذة | الاسم العربي في الـ IDE | وظيفتها |
|---|---|---|
| **Solution Explorer** | مستكشف الحلول | ملفات المشروع |
| **Output** | المخرجات | ناتج البرنامج ورسائل الترجمة والأخطاء |
| **Toolbox** | صندوق الأدوات | الأزرار ومربعات النص (للبرامج الرسومية) |
| **Properties** | الخصائص | خصائص الأداة المختارة في المصمم |

| الاختصار | الأمر |
|---|---|
| `F5` | تشغيل مع التصحيح: **Debug > Start Debugging / Continue** (تصحيح الأخطاء > بدء تصحيح الأخطاء / متابعة) |
| `Ctrl+F5` | تشغيل دون تصحيح |
| `Shift+F5` | إيقاف البرنامج |
| `Ctrl+S` | حفظ الكل |
| `Ctrl+Shift+F1` | فتح الدروس |

## أخطاء شائعة

- **نسيان الفاصلة المنقوطة `;`** في آخر التعليمة.
- **كتابة `system.out.println`:** Java **حساسة لحالة الأحرف**، والصحيح `System` بحرف S كبير.
- **اسم الملف لا يطابق اسم الصنف:** الصنف `public class Hello` في ملف `Main.java` يعطي الخطأ `class Hello is public, should be declared in a file named Hello.java`.

## تمارين

### التمرين 1

اطبع اسمك في سطر، ثم اسم مدينتك في السطر التالي.

```java exercise
public class Main {
    public static void main(String[] args) {
        // اطبع سطرين: اسمك ثم مدينتك
    }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        System.out.println("أحمد");
        System.out.println("القاهرة");
    }
}
```

```text output
أحمد
القاهرة
```

### التمرين 2

اطبع مربعًا من النجوم بثلاثة أسطر، في كل سطر `***`.

```java exercise
public class Main {
    public static void main(String[] args) {
        // ***
        // ***
        // ***
    }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        System.out.println("***");
        System.out.println("***");
        System.out.println("***");
    }
}
```

```text output
***
***
***
```

## اختبر نفسك

```quiz
{"question": "ما وظيفة javac؟", "choices": ["تشغيل البرنامج", "ترجمة ملفات .java إلى bytecode في ملفات .class", "تحرير الكود", "تنزيل المكتبات"], "answer": 1, "explanation": "javac هو المترجم، وjava هو الذي يشغّل الـ bytecode على JVM."}
```

```quiz
{"question": "لماذا تعمل برامج Java على أنظمة تشغيل مختلفة دون تعديل؟", "choices": ["لأنها مكتوبة بالعربية", "لأنها تُترجم إلى bytecode تشغّله JVM الموجودة لكل نظام", "لأنها لا تحتاج إلى ترجمة", "لا تعمل إلا على ويندوز"], "answer": 1, "explanation": "الـ bytecode واحد، وكل نظام له JVM خاصة به."}
```

```quiz
{"question": "في أي ملف يجب أن يكون الصنف public class Calculator؟", "choices": ["Main.java", "calculator.java", "Calculator.java", "أي ملف"], "answer": 2, "explanation": "اسم الملف يطابق اسم الصنف العام بنفس حالة الأحرف."}
```

## الخلاصة

- Java تُترجم بـ `javac` إلى bytecode، وتعمل على JVM بالأمر `java`.
- تحتاج إلى **JDK 17** أو أحدث بجانب الـ IDE.
- `System.out.println("...")` تطبع سطرًا، واسم الملف يطابق اسم الصنف العام.
- أمثلة الدروس تُفتح كمشاريع Eclipse حقيقية.
