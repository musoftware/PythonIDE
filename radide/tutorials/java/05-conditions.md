# الدرس 5: الشروط واتخاذ القرار

البرنامج الذكي يتصرف بحسب الموقف: إذا كانت كلمة المرور صحيحة يدخل المستخدم، وإلا تظهر رسالة خطأ. هذا ما تفعله **الشروط**.

> **تشبيه:** الشرط مثل **إشارة المرور**: إذا كانت خضراء تمر، وإذا كانت حمراء تقف.

## عوامل المقارنة

| العامل | المعنى | مثال | الناتج |
|---|---|---|---|
| `==` | يساوي | `5 == 5` | `true` |
| `!=` | لا يساوي | `5 != 3` | `true` |
| `>` | أكبر من | `5 > 8` | `false` |
| `<` | أصغر من | `5 < 8` | `true` |
| `>=` | أكبر من أو يساوي | `5 >= 5` | `true` |
| `<=` | أصغر من أو يساوي | `4 <= 3` | `false` |

## `if` و`else`

```java run
public class Main {
    public static void main(String[] args) {
        int temperature = 38;
        if (temperature > 35) {
            System.out.println("الجو حار جدًا، اشرب ماءً كثيرًا");
        } else {
            System.out.println("الجو معتدل");
        }
        System.out.println("انتهى البرنامج");
    }
}
```

```text output
الجو حار جدًا، اشرب ماءً كثيرًا
انتهى البرنامج
```

## سلسلة `else if`

```java run
public class Main {
    public static void main(String[] args) {
        int grade = 78;
        if (grade >= 90) {
            System.out.println("ممتاز");
        } else if (grade >= 80) {
            System.out.println("جيد جدًا");
        } else if (grade >= 65) {
            System.out.println("جيد");
        } else if (grade >= 50) {
            System.out.println("مقبول");
        } else {
            System.out.println("راسب");
        }
    }
}
```

```text output
جيد
```

تُفحص الشروط بالترتيب، وأول شرط صحيح يُنفذ ثم تُترك بقية السلسلة.

## العوامل المنطقية

| العامل | المعنى | يكون صحيحًا عندما |
|---|---|---|
| `&&` | و (AND) | الطرفان صحيحان |
| `||` | أو (OR) | أحد الطرفين على الأقل صحيح |
| `!` | ليس (NOT) | يقلب القيمة |

```java run
public class Main {
    public static void main(String[] args) {
        int age = 20;
        boolean hasTicket = true;
        if (age >= 18 && hasTicket) {
            System.out.println("مسموح بالدخول");
        }
        String day = "الجمعة";
        if (day.equals("الجمعة") || day.equals("السبت")) {
            System.out.println("عطلة نهاية الأسبوع");
        }
        boolean isRaining = false;
        if (!isRaining) {
            System.out.println("يمكنك الخروج دون مظلة");
        }
    }
}
```

```text output
مسموح بالدخول
عطلة نهاية الأسبوع
يمكنك الخروج دون مظلة
```

## مقارنة النصوص: `equals` وليس `==`

هذه من أهم قواعد Java! النصوص **كائنات**، و`==` تسأل «هل هما **نفس الكائن** في الذاكرة؟» وليس «هل لهما نفس الحروف؟». لمقارنة المحتوى استخدم `equals`:

```java run
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        String answer = in.nextLine();
        System.out.println(answer == "yes");          // خطأ شائع!
        System.out.println(answer.equals("yes"));     // الصحيح
        System.out.println(answer.equalsIgnoreCase("YES"));
    }
}
```

```text input
yes
```

```text output
false
true
true
```

النص الذي قرأناه من المستخدم كائن جديد، فـ `==` تعطي `false` رغم أن الحروف متطابقة.

## `switch`

```java run
public class Main {
    public static void main(String[] args) {
        int day = 3;
        switch (day) {
            case 1:
                System.out.println("الأحد");
                break;
            case 2:
                System.out.println("الإثنين");
                break;
            case 3:
                System.out.println("الثلاثاء");
                break;
            case 6:
            case 7:
                System.out.println("عطلة");
                break;
            default:
                System.out.println("يوم آخر");
        }
    }
}
```

```text output
الثلاثاء
```

> **انتبه:** إذا نسيت `break` في `switch` القديم، **يسقط** التنفيذ إلى الـ `case` التالي ويكمل! هذا مصدر أخطاء كثيرة.

## `switch` الحديث (Java 14+)

السهم `->` لا يسقط إلى التالي، ويمكن أن يرجع قيمة:

```java run
public class Main {
    public static void main(String[] args) {
        int month = 4;
        String season = switch (month) {
            case 12, 1, 2 -> "الشتاء";
            case 3, 4, 5 -> "الربيع";
            case 6, 7, 8 -> "الصيف";
            default -> "الخريف";
        };
        System.out.println(season);

        String op = "*";
        int result = switch (op) {
            case "+" -> 6 + 3;
            case "-" -> 6 - 3;
            case "*" -> 6 * 3;
            default -> 0;
        };
        System.out.println(result);
    }
}
```

```text output
الربيع
18
```

## العامل الثلاثي `? :`

```java run
public class Main {
    public static void main(String[] args) {
        int n = 7;
        String kind = n % 2 == 0 ? "زوجي" : "فردي";
        System.out.println(n + " عدد " + kind);
    }
}
```

```text output
7 عدد فردي
```

## مثال: آلة حاسبة

```java run
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        double a = Double.parseDouble(in.nextLine());
        String op = in.nextLine().trim();
        double b = Double.parseDouble(in.nextLine());
        switch (op) {
            case "+" -> System.out.println(a + b);
            case "-" -> System.out.println(a - b);
            case "*" -> System.out.println(a * b);
            case "/" -> {
                if (b == 0) {
                    System.out.println("لا يمكن القسمة على صفر");
                } else {
                    System.out.println(a / b);
                }
            }
            default -> System.out.println("عملية غير معروفة");
        }
    }
}
```

```text input
9
/
2
```

```text output
4.5
```

## أخطاء شائعة

### `=` بدل `==`

<!-- compile-error -->
```java
public class Main {
    public static void main(String[] args) {
        int x = 5;
        if (x = 5) {
            System.out.println("خمسة");
        }
    }
}
```

```text
Main.java:4: error: incompatible types: int cannot be converted to boolean
```

### `==` مع النصوص

لا يظهر خطأ ترجمة، لكن النتيجة خاطئة كما رأيت. **دائمًا** `equals` للنصوص.

### فاصلة منقوطة بعد `if`

`if (x > 10);` تنهي الشرط بتعليمة فارغة، فتُنفذ الكتلة التالية دائمًا.

## تمارين

### التمرين 1

اقرأ عددًا صحيحًا واطبع: موجب أو سالب أو صفر.

```java exercise
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        int n = in.nextInt();
        // اطبع: موجب / سالب / صفر
    }
}
```

```java solution
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        int n = in.nextInt();
        if (n > 0) {
            System.out.println("موجب");
        } else if (n < 0) {
            System.out.println("سالب");
        } else {
            System.out.println("صفر");
        }
    }
}
```

```text input
-4
```

```text output
سالب
```

### التمرين 2

اقرأ سنة واطبع هل هي كبيسة (تقبل القسمة على 4 ولا تقبل القسمة على 100، أو تقبل القسمة على 400).

```java exercise
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        int year = in.nextInt();
        // 2024 سنة كبيسة   أو   2023 سنة عادية
    }
}
```

```java solution
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        int year = in.nextInt();
        boolean leap = (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;
        System.out.println(year + (leap ? " سنة كبيسة" : " سنة عادية"));
    }
}
```

```text input
2024
```

```text output
2024 سنة كبيسة
```

### التمرين 3

اقرأ كلمة المرور، واطبع `مرحبًا` إذا كانت `java123`، وإلا `كلمة مرور خاطئة`.

```java exercise
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        String pass = in.nextLine();
        // قارن بـ equals
    }
}
```

```java solution
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        String pass = in.nextLine();
        if (pass.equals("java123")) {
            System.out.println("مرحبًا");
        } else {
            System.out.println("كلمة مرور خاطئة");
        }
    }
}
```

```text input
java123
```

```text output
مرحبًا
```

## اختبر نفسك

```quiz
{"question": "كيف تقارن محتوى نصين في Java؟", "choices": ["s1 == s2", "s1.equals(s2)", "s1 = s2", "compare(s1, s2)"], "answer": 1, "explanation": "== تقارن هل هما نفس الكائن، وequals تقارن الحروف."}
```

```quiz
{"question": "ماذا يحدث إذا نسيت break في switch القديم؟", "choices": ["خطأ ترجمة", "يكمل التنفيذ في الـ case التالي", "يتوقف البرنامج", "لا شيء"], "answer": 1, "explanation": "هذا يسمى السقوط (fall-through)، والسهم -> في switch الحديث يمنعه."}
```

```quiz
{"question": "متى يكون (a > 0 || b > 0) صحيحًا؟", "choices": ["إذا كان الاثنان موجبين فقط", "إذا كان أحدهما على الأقل موجبًا", "إذا كانا سالبين", "دائمًا"], "answer": 1, "explanation": "|| يكفيه أن يكون طرف واحد صحيحًا."}
```

## الخلاصة

- `if` / `else if` / `else`، والعوامل `&&` و`||` و`!`.
- النصوص تُقارن بـ `equals` و`equalsIgnoreCase`، وليس بـ `==`.
- `switch` القديم يحتاج `break`، و`switch` الحديث بالسهم `->` يرجع قيمة ولا يسقط.
- `? :` لاختيار قيمة بسرعة.
