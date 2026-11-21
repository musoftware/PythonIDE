# الدرس 4: الإدخال بـ Scanner والعمليات الحسابية

اليوم نجعل برامجنا **تسأل** المستخدم وتقرأ إجابته، ثم **تحسب** بها.

## قراءة الإدخال: `Scanner`

الصنف `Scanner` يقرأ من لوحة المفاتيح (`System.in`). وهو موجود في الحزمة `java.util`، فنستورده بـ `import`:

```java run
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        System.out.print("ما اسمك؟ ");
        String name = in.nextLine();
        System.out.println("أهلًا يا " + name + "!");
    }
}
```

```text input
منى
```

```text output
ما اسمك؟ أهلًا يا منى!
```

- `import java.util.Scanner;` يقول للمترجم أين يجد الصنف `Scanner`.
- `new Scanner(System.in)` ينشئ قارئًا من لوحة المفاتيح.
- `in.nextLine()` تنتظر سطرًا كاملًا وترجعه نصًا.

> **ملحوظة:** عند الضغط على «جرّبه» ترسل الـ IDE المدخلات المكتوبة في الدرس، أو تسألك أنت أن تكتبها. وما تكتبه لا يظهر في الناتج، لذلك يأتي الرد في نفس سطر السؤال.

## قراءة الأرقام

| الدالة | تقرأ |
|---|---|
| `nextInt()` | عددًا صحيحًا |
| `nextDouble()` | عددًا عشريًا |
| `nextLine()` | سطرًا كاملًا (نصًا) |
| `next()` | كلمة واحدة |
| `nextBoolean()` | `true` أو `false` |

> **ملحوظة:** `nextDouble()` تتبع إعدادات اللغة في ويندوز، فقد تتوقع فاصلة عشرية غير النقطة إذا كانت لغة النظام عربية. لكي تقبل دائمًا `25.5` اكتب بعد إنشاء القارئ: `in.useLocale(java.util.Locale.US);`، أو اقرأ سطرًا وحوّله بـ `Double.parseDouble(in.nextLine())`.

```java run
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        System.out.print("العدد الأول: ");
        int a = in.nextInt();
        System.out.print("العدد الثاني: ");
        int b = in.nextInt();
        System.out.println();
        System.out.println("المجموع = " + (a + b));
    }
}
```

```text input
12
30
```

```text output
العدد الأول: العدد الثاني: 
المجموع = 42
```

### فخ `nextInt` ثم `nextLine`

`nextInt()` تقرأ الرقم فقط وتترك ضغطة Enter في الطابور، فتقرؤها `nextLine()` التالية كسطر فارغ! الحل: استدعِ `in.nextLine()` مرة إضافية بعد `nextInt()`، أو اقرأ كل شيء بـ `nextLine()` وحوّله بـ `Integer.parseInt`:

```java run
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        int age = Integer.parseInt(in.nextLine().trim());
        String city = in.nextLine();
        System.out.println(age + " سنة من " + city);
    }
}
```

```text input
30
الأقصر
```

```text output
30 سنة من الأقصر
```

## الحماية من الإدخال الخاطئ

إذا كتب المستخدم «عشرة» بدل رقم، يتوقف `parseInt` بخطأ `NumberFormatException`. سنتعلم معالجة الأخطاء في الدرس 12، والآن نستخدم `hasNextInt()` التي تفحص قبل القراءة:

```java run
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        System.out.print("كم عمرك؟ ");
        if (in.hasNextInt()) {
            int age = in.nextInt();
            System.out.println("بعد 10 سنوات سيصبح عمرك " + (age + 10));
        } else {
            System.out.println("«" + in.next() + "» ليس رقمًا صحيحًا");
        }
    }
}
```

```text input
عشرون
```

```text output
كم عمرك؟ «عشرون» ليس رقمًا صحيحًا
```

## العمليات الحسابية

| العامل | المعنى | مثال | الناتج |
|---|---|---|---|
| `+` | جمع | `7 + 2` | `9` |
| `-` | طرح | `7 - 2` | `5` |
| `*` | ضرب | `7 * 2` | `14` |
| `/` | قسمة | `7 / 2` | `3` (أعداد صحيحة!) |
| `%` | باقي القسمة | `7 % 2` | `1` |

```java run
public class Main {
    public static void main(String[] args) {
        int a = 17, b = 5;
        System.out.println(a + b);
        System.out.println(a - b);
        System.out.println(a * b);
        System.out.println(a / b);
        System.out.println(a % b);
        System.out.println(17.0 / 5);
    }
}
```

```text output
22
12
85
3
2
3.4
```

> **مهم جدًا:** قسمة عددين صحيحين في Java تعطي عددًا صحيحًا ويُحذف الكسر: `17 / 5 = 3`. اجعل أحد الطرفين عشريًا لتحصل على `3.4`.

### الأولوية والاختصارات

```java run
public class Main {
    public static void main(String[] args) {
        System.out.println(2 + 3 * 4);
        System.out.println((2 + 3) * 4);

        int points = 10;
        points += 5;
        points -= 3;
        points *= 2;
        System.out.println(points);

        int count = 0;
        count++;
        count++;
        count--;
        System.out.println(count);
    }
}
```

```text output
14
20
24
1
```

## الصنف `Math`

```java run
public class Main {
    public static void main(String[] args) {
        System.out.println(Math.sqrt(16));
        System.out.println(Math.pow(2, 10));
        System.out.println(Math.abs(-7));
        System.out.println(Math.max(4, 9));
        System.out.println(Math.round(3.6));
        System.out.printf("%.2f%n", Math.PI);
    }
}
```

```text output
4.0
1024.0
7
9
4
3.14
```

لاحظ أن `Math.sqrt` و`Math.pow` ترجعان `double`، فتظهر `4.0` و`1024.0`.

## مثال كامل: حساب الفاتورة

```java run
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        System.out.print("سعر القطعة: ");
        double price = in.nextDouble();
        System.out.print("الكمية: ");
        int qty = in.nextInt();

        double total = price * qty;
        double tax = total * 0.14;
        System.out.println();
        System.out.printf("الإجمالي قبل الضريبة: %.2f%n", total);
        System.out.printf("الضريبة 14%%: %.2f%n", tax);
        System.out.printf("المطلوب: %.2f%n", total + tax);
    }
}
```

```text input
25.5
4
```

```text output
سعر القطعة: الكمية: 
الإجمالي قبل الضريبة: 102.00
الضريبة 14%: 14.28
المطلوب: 116.28
```

في `printf` نكتب `%%` لنطبع علامة `%` نفسها.

## أخطاء شائعة

- **نسيان `import java.util.Scanner;`:** يعطي `cannot find symbol ... class Scanner`.
- **القسمة الصحيحة دون قصد:** `double avg = (a + b) / 2;` تحذف الكسر إذا كان `a` و`b` من نوع `int`. اكتب `/ 2.0`.
- **`nextInt()` ثم `nextLine()`:** السطر يصبح فارغًا. اقرأ بـ `nextLine()` وحوّل.

## تمارين

### التمرين 1

اقرأ طول المستطيل وعرضه (عددين صحيحين) واطبع المساحة والمحيط.

```java exercise
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        // المساحة = ...
        // المحيط = ...
    }
}
```

```java solution
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        int length = in.nextInt();
        int width = in.nextInt();
        System.out.println("المساحة = " + length * width);
        System.out.println("المحيط = " + 2 * (length + width));
    }
}
```

```text input
6
4
```

```text output
المساحة = 24
المحيط = 20
```

### التمرين 2

اقرأ عددًا من الثواني واطبعه بالساعات والدقائق والثواني.

```java exercise
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        int total = in.nextInt();
        // 1 ساعة و 2 دقيقة و 5 ثانية
    }
}
```

```java solution
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        int total = in.nextInt();
        int hours = total / 3600;
        int minutes = total % 3600 / 60;
        int seconds = total % 60;
        System.out.println(hours + " ساعة و " + minutes + " دقيقة و " + seconds + " ثانية");
    }
}
```

```text input
3725
```

```text output
1 ساعة و 2 دقيقة و 5 ثانية
```

### التمرين 3

اقرأ ثلاث درجات عشرية واطبع متوسطها برقمين عشريين.

```java exercise
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        // المتوسط = ...
    }
}
```

```java solution
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        double a = in.nextDouble();
        double b = in.nextDouble();
        double c = in.nextDouble();
        System.out.printf("المتوسط = %.2f%n", (a + b + c) / 3);
    }
}
```

```text input
85
90.5
77
```

```text output
المتوسط = 84.17
```

## اختبر نفسك

```quiz
{"question": "ما السطر اللازم قبل استخدام Scanner؟", "choices": ["#include <Scanner>", "import java.util.Scanner;", "using Scanner;", "لا شيء"], "answer": 1, "explanation": "Scanner في الحزمة java.util فنستورده بـ import."}
```

```quiz
{"question": "ما ناتج 9 / 2 في Java إذا كان العددان int؟", "choices": ["4.5", "4", "5", "خطأ"], "answer": 1, "explanation": "قسمة عددين صحيحين تعطي عددًا صحيحًا."}
```

```quiz
{"question": "ماذا يطبع System.out.println(Math.sqrt(25));؟", "choices": ["5", "5.0", "25", "خطأ"], "answer": 1, "explanation": "Math.sqrt ترجع double، وJava تطبعه 5.0."}
```

```quiz
{"question": "كيف نطبع علامة % داخل printf؟", "choices": ["\\%", "%%", "%p", "لا يمكن"], "answer": 1, "explanation": "في نص التنسيق نكتب %% لتظهر % واحدة."}
```

## الخلاصة

- `Scanner in = new Scanner(System.in);` ثم `nextLine` و`nextInt` و`nextDouble`.
- انتبه لفخ `nextInt` ثم `nextLine`، واستخدم `hasNextInt` للفحص.
- العوامل `+ - * / %`، والقسمة الصحيحة، و`+=` و`++`.
- `Math.sqrt` و`Math.pow` و`Math.max` و`Math.round`، و`printf` للتنسيق.
