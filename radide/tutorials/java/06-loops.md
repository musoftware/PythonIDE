# الدرس 6: حلقات التكرار

**حلقة التكرار** (loop) تكرر مجموعة من التعليمات ما دام شرط معين صحيحًا، فتوفر عليك كتابة نفس السطر مئات المرات.

> **تشبيه:** حلقة التكرار مثل **عدّاد اللفّات** في سباق الجري: العدّاء يجري لفّة، والعدّاد يزيد واحدًا، حتى يصل العدد المطلوب.

## حلقة `for`

```java run
public class Main {
    public static void main(String[] args) {
        for (int i = 1; i <= 5; i++) {
            System.out.println("اللفّة رقم " + i);
        }
    }
}
```

```text output
اللفّة رقم 1
اللفّة رقم 2
اللفّة رقم 3
اللفّة رقم 4
اللفّة رقم 5
```

الأجزاء الثلاثة: **البداية** `int i = 1`، و**الشرط** `i <= 5` (يُفحص قبل كل لفّة)، و**الخطوة** `i++` (بعد كل لفّة).

### العد التنازلي والجمع

```java run
public class Main {
    public static void main(String[] args) {
        for (int i = 10; i >= 0; i -= 2) {
            System.out.print(i + " ");
        }
        System.out.println();

        int sum = 0;
        for (int i = 1; i <= 100; i++) {
            sum += i;
        }
        System.out.println("مجموع الأرقام من 1 إلى 100 = " + sum);
    }
}
```

```text output
10 8 6 4 2 0
مجموع الأرقام من 1 إلى 100 = 5050
```

## حلقة `while`

عندما لا نعرف عدد المرات بل شرط الاستمرار:

```java run
public class Main {
    public static void main(String[] args) {
        int money = 100;
        int months = 0;
        while (money < 200) {
            money += money / 10;
            months++;
        }
        System.out.println("بعد " + months + " شهرًا صار المبلغ " + money);
    }
}
```

```text output
بعد 8 شهرًا صار المبلغ 212
```

## حلقة `do ... while`

تُنفذ **مرة واحدة على الأقل**، لأن الشرط في النهاية:

```java run
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        int number;
        do {
            System.out.print("أدخل رقمًا من 1 إلى 10: ");
            number = in.nextInt();
        } while (number < 1 || number > 10);
        System.out.println();
        System.out.println("شكرًا، اخترت " + number);
    }
}
```

```text input
15
0
7
```

```text output
أدخل رقمًا من 1 إلى 10: أدخل رقمًا من 1 إلى 10: أدخل رقمًا من 1 إلى 10: 
شكرًا، اخترت 7
```

## `break` و`continue`

```java run
public class Main {
    public static void main(String[] args) {
        for (int i = 1; i <= 10; i++) {
            if (i % 3 == 0) {
                continue;      // تخطَّ مضاعفات 3
            }
            if (i > 8) {
                break;         // توقف بعد 8
            }
            System.out.print(i + " ");
        }
        System.out.println();
    }
}
```

```text output
1 2 4 5 7 8
```

## الحلقات المتداخلة

```java run
public class Main {
    public static void main(String[] args) {
        for (int row = 1; row <= 4; row++) {
            for (int col = 1; col <= row; col++) {
                System.out.print("*");
            }
            System.out.println();
        }
        for (int i = 1; i <= 3; i++) {
            for (int j = 1; j <= 5; j++) {
                System.out.printf("%4d", i * j);
            }
            System.out.println();
        }
    }
}
```

```text output
*
**
***
****
   1   2   3   4   5
   2   4   6   8  10
   3   6   9  12  15
```

`%4d` تطبع العدد في 4 خانات فتصطف الأعمدة.

## حلقة `for` المحسّنة (`for-each`)

تمر على كل عنصر في مصفوفة أو مجموعة. سنستخدمها كثيرًا في الدرس الثامن:

```java run
public class Main {
    public static void main(String[] args) {
        String word = "Java17!";
        int letters = 0;
        for (char c : word.toCharArray()) {
            if (Character.isLetter(c)) {
                letters++;
            }
        }
        System.out.println("عدد الحروف: " + letters);
    }
}
```

```text output
عدد الحروف: 4
```

## الحلقات المسماة (labeled break)

`break` تخرج من الحلقة الداخلية فقط. للخروج من الحلقتين معًا نعطي الخارجية **اسمًا**:

```java run
public class Main {
    public static void main(String[] args) {
        outer:
        for (int i = 1; i <= 5; i++) {
            for (int j = 1; j <= 5; j++) {
                if (i * j == 12) {
                    System.out.println("وجدنا " + i + " × " + j + " = 12");
                    break outer;
                }
            }
        }
    }
}
```

```text output
وجدنا 3 × 4 = 12
```

## أخطاء شائعة

- **الحلقة اللانهائية:** نسيان `i++` في `while`. إذا علق البرنامج اضغط **Shift+F5**.
- **الخطأ بفارق واحد:** `for (int i = 0; i <= 10; i++)` تتكرر 11 مرة.
- **متغير الحلقة خارجها:** `i` المعرّف في `for` لا يوجد بعدها.
- **فاصلة منقوطة بعد `for (...)`:** `for (int i = 0; i < 5; i++);` حلقة فارغة، والكتلة بعدها تُنفذ مرة واحدة.

## تمارين

### التمرين 1

اطبع جدول ضرب العدد 7 من 1 إلى 5 بالشكل `7 x 1 = 7`.

```java exercise
public class Main {
    public static void main(String[] args) {
        // 7 x 1 = 7 ... 7 x 5 = 35
    }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        for (int i = 1; i <= 5; i++) {
            System.out.println("7 x " + i + " = " + 7 * i);
        }
    }
}
```

```text output
7 x 1 = 7
7 x 2 = 14
7 x 3 = 21
7 x 4 = 28
7 x 5 = 35
```

### التمرين 2

اقرأ `n` واحسب مضروبه `n!` بالنوع `long`.

```java exercise
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        int n = new Scanner(System.in).nextInt();
        // 10! = 3628800
    }
}
```

```java solution
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        int n = new Scanner(System.in).nextInt();
        long fact = 1;
        for (int i = 2; i <= n; i++) {
            fact *= i;
        }
        System.out.println(n + "! = " + fact);
    }
}
```

```text input
10
```

```text output
10! = 3628800
```

### التمرين 3

اقرأ أرقامًا حتى يكتب المستخدم `0`، ثم اطبع عددها ومجموعها.

```java exercise
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        // العدد: ...
        // المجموع: ...
    }
}
```

```java solution
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        int count = 0, sum = 0;
        while (true) {
            int x = in.nextInt();
            if (x == 0) {
                break;
            }
            count++;
            sum += x;
        }
        System.out.println("العدد: " + count);
        System.out.println("المجموع: " + sum);
    }
}
```

```text input
5
12
3
0
```

```text output
العدد: 3
المجموع: 20
```

## اختبر نفسك

```quiz
{"question": "كم مرة تتكرر for (int i = 0; i < 5; i++)؟", "choices": ["4", "5", "6", "لا نهائية"], "answer": 1, "explanation": "من 0 إلى 4: خمس مرات."}
```

```quiz
{"question": "ما الحلقة التي تُنفذ مرة واحدة على الأقل؟", "choices": ["for", "while", "do...while", "for-each"], "answer": 2, "explanation": "do...while تفحص الشرط بعد تنفيذ الجسم."}
```

```quiz
{"question": "كيف تخرج من حلقتين متداخلتين مرة واحدة؟", "choices": ["break مرتين في نفس السطر", "break مع اسم الحلقة الخارجية (labeled break)", "continue", "return فقط"], "answer": 1, "explanation": "نسمي الحلقة الخارجية outer: ثم نكتب break outer;."}
```

## الخلاصة

- `for` لعدد معروف، و`while` لشرط استمرار، و`do...while` للتنفيذ مرة على الأقل.
- for-each: `for (char c : word.toCharArray())`.
- `break` و`continue`، و`break label` للخروج من الحلقات المتداخلة.
- `printf("%4d")` لمحاذاة الأعمدة.
