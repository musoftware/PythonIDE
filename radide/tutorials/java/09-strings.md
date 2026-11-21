# الدرس 9: التعامل مع النصوص

النص في Java من الصنف `String`، ومعه عشرات الدوال الجاهزة للبحث والتقطيع والتحويل.

> **تشبيه:** النص مثل **قطار** من العربات، في كل عربة حرف (`char`) والعربات مرقمة من 0. ولا يمكنك تغيير عربة في مكانها: النصوص في Java **غير قابلة للتعديل** (immutable)، وكل دالة ترجع نصًا **جديدًا**.

## الطول والحروف

```java run
public class Main {
    public static void main(String[] args) {
        String word = "Programming";
        System.out.println(word.length());
        System.out.println(word.charAt(0));
        System.out.println(word.charAt(word.length() - 1));
        System.out.println(word.isEmpty());
    }
}
```

```text output
11
P
g
false
```

## أهم الدوال

```java run
public class Main {
    public static void main(String[] args) {
        String s = "  Hello, Java World  ";
        System.out.println("[" + s.trim() + "]");
        System.out.println(s.trim().toUpperCase());
        System.out.println(s.trim().toLowerCase());
        System.out.println(s.contains("Java"));
        System.out.println(s.trim().startsWith("Hello"));
        System.out.println(s.trim().endsWith("World"));
        System.out.println(s.indexOf("World"));
        System.out.println(s.replace("World", "Egypt").trim());
    }
}
```

```text output
[Hello, Java World]
HELLO, JAVA WORLD
hello, java world
true
true
true
14
Hello, Java Egypt
```

| الدالة | وظيفتها |
|---|---|
| `length()` | الطول |
| `charAt(i)` | الحرف رقم `i` |
| `trim()` / `strip()` | حذف المسافات من الطرفين |
| `toUpperCase()` / `toLowerCase()` | أحرف كبيرة / صغيرة |
| `contains(x)` | هل يحتوي على `x`؟ |
| `indexOf(x)` | موضع أول ظهور (أو `-1`) |
| `replace(a, b)` | استبدال |
| `substring(i, j)` | من `i` حتى قبل `j` |
| `split(regex)` | تقسيم إلى مصفوفة |
| `equals` / `equalsIgnoreCase` | المقارنة |

## اقتطاع جزء: `substring`

```java run
public class Main {
    public static void main(String[] args) {
        String date = "2026-11-21";
        String year = date.substring(0, 4);     // من 0 حتى قبل 4
        String month = date.substring(5, 7);
        String day = date.substring(8);         // من 8 حتى النهاية
        System.out.println("اليوم " + day + " الشهر " + month + " السنة " + year);
    }
}
```

```text output
اليوم 21 الشهر 11 السنة 2026
```

> **انتبه:** `substring(i, j)` في Java تأخذ **موضع النهاية** (غير مشمول)، وليس الطول كما في C#.

## التقسيم والدمج

```java run
public class Main {
    public static void main(String[] args) {
        String line = "أحمد,25,القاهرة,مهندس";
        String[] parts = line.split(",");
        System.out.println("الاسم: " + parts[0]);
        System.out.println("العمر: " + parts[1]);
        System.out.println("عدد الحقول: " + parts.length);
        System.out.println(String.join(" | ", parts));
    }
}
```

```text output
الاسم: أحمد
العمر: 25
عدد الحقول: 4
أحمد | 25 | القاهرة | مهندس
```

> **ملحوظة:** `split` تأخذ **تعبيرًا نمطيًا** (regex). للتقسيم على النقطة اكتب `split("\\.")`، وعلى `|` اكتب `split("\\|")`، وعلى مسافة أو أكثر `split("\\s+")`.

## المقارنة والفحص

```java run
public class Main {
    public static void main(String[] args) {
        String a = "java";
        String b = "Java";
        System.out.println(a.equals(b));
        System.out.println(a.equalsIgnoreCase(b));
        System.out.println("apple".compareTo("banana") < 0);
        System.out.println("   ".isBlank());
    }
}
```

```text output
false
true
true
true
```

## المرور على الحروف وعكس النص

```java run
public class Main {
    public static void main(String[] args) {
        String text = "Hello World 2026";
        int letters = 0, digits = 0, spaces = 0;
        for (char c : text.toCharArray()) {
            if (Character.isLetter(c)) letters++;
            else if (Character.isDigit(c)) digits++;
            else if (Character.isWhitespace(c)) spaces++;
        }
        System.out.println("حروف " + letters + "، أرقام " + digits + "، مسافات " + spaces);

        String word = "level";
        String reversed = new StringBuilder(word).reverse().toString();
        System.out.println(reversed);
        System.out.println(word.equals(reversed) ? "متناظر (palindrome)" : "غير متناظر");
    }
}
```

```text output
حروف 10، أرقام 4، مسافات 2
level
متناظر (palindrome)
```

## `StringBuilder`

لبناء نص كبير بإضافات كثيرة في حلقة، `StringBuilder` أسرع بكثير من `+=`:

```java run
public class Main {
    public static void main(String[] args) {
        StringBuilder sb = new StringBuilder();
        for (int i = 1; i <= 5; i++) {
            sb.append(i);
            if (i < 5) {
                sb.append(" - ");
            }
        }
        sb.append("\nانتهى");
        System.out.println(sb.toString());
        sb.insert(0, ">> ");
        System.out.println(sb.length());
    }
}
```

```text output
1 - 2 - 3 - 4 - 5
انتهى
26
```

## التنسيق: `String.format`

```java run
public class Main {
    public static void main(String[] args) {
        String name = "Laptop";
        double price = 15499.5;
        int qty = 3;
        System.out.println(String.format("|%-10s|%5d|%12.2f|", name, qty, price));
        System.out.println(String.format("%,.2f", 1234567.891));
        System.out.println(String.format("%03d", 7));
        String report = "%s x %d = %.1f".formatted("قلم", 4, 4 * 2.5);
        System.out.println(report);
    }
}
```

```text output
|Laptop    |    3|    15499.50|
1,234,567.89
007
قلم x 4 = 10.0
```

- `%-10s` نص محاذاته يسار في 10 خانات، و`%5d` عدد صحيح في 5 خانات.
- `%,.2f` فواصل الآلاف، و`%03d` أصفار في البداية.
- `"...".formatted(...)` (منذ Java 15) اختصار لـ `String.format`.

## النصوص متعددة الأسطر (Text Blocks)

منذ Java 15 يمكن كتابة نص من عدة أسطر بين `"""`:

```java run
public class Main {
    public static void main(String[] args) {
        String menu = """
            1. إضافة
            2. حذف
            3. خروج""";
        System.out.println(menu);
    }
}
```

```text output
1. إضافة
2. حذف
3. خروج
```

## أخطاء شائعة

- **`s.toUpperCase();` وحدها لا تغير `s`:** اكتب `s = s.toUpperCase();`.
- **`==` للنصوص:** استخدم `equals`.
- **`substring` خارج الحدود:** يعطي `StringIndexOutOfBoundsException`.
- **`split(".")` لا تعمل كما تتوقع:** النقطة في regex تعني «أي حرف»، فاكتب `split("\\.")`.

## تمارين

### التمرين 1

اقرأ جملة واطبع عدد كلماتها (قد تفصل بينها مسافات متعددة).

```java exercise
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        String sentence = new Scanner(System.in).nextLine();
        // عدد الكلمات: 5
    }
}
```

```java solution
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        String sentence = new Scanner(System.in).nextLine();
        String[] words = sentence.trim().split("\\s+");
        System.out.println("عدد الكلمات: " + words.length);
    }
}
```

```text input
أنا   أحب تعلم لغة Java
```

```text output
عدد الكلمات: 5
```

### التمرين 2

اكتب دالة `capitalize` تجعل أول حرف من كل كلمة إنجليزية كبيرًا.

```java exercise
public class Main {
    static String capitalize(String s) {
        return s;
    }

    public static void main(String[] args) {
        System.out.println(capitalize("hello world from java"));
    }
}
```

```java solution
public class Main {
    static String capitalize(String s) {
        String[] words = s.split(" ");
        StringBuilder sb = new StringBuilder();
        for (String w : words) {
            if (sb.length() > 0) {
                sb.append(" ");
            }
            if (!w.isEmpty()) {
                sb.append(Character.toUpperCase(w.charAt(0))).append(w.substring(1));
            }
        }
        return sb.toString();
    }

    public static void main(String[] args) {
        System.out.println(capitalize("hello world from java"));
    }
}
```

```text output
Hello World From Java
```

### التمرين 3

اقرأ بريدًا إلكترونيًا واطبع اسم المستخدم والنطاق، أو `بريد غير صحيح` إذا لم يحتوِ على `@`.

```java exercise
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        String email = new Scanner(System.in).nextLine();
        // المستخدم: sara
        // النطاق: example.com
    }
}
```

```java solution
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        String email = new Scanner(System.in).nextLine();
        int at = email.indexOf('@');
        if (at <= 0) {
            System.out.println("بريد غير صحيح");
        } else {
            System.out.println("المستخدم: " + email.substring(0, at));
            System.out.println("النطاق: " + email.substring(at + 1));
        }
    }
}
```

```text input
sara@example.com
```

```text output
المستخدم: sara
النطاق: example.com
```

## اختبر نفسك

```quiz
{"question": "ما ناتج \"Hello\".substring(1, 3)؟", "choices": ["Hel", "el", "ell", "ello"], "answer": 1, "explanation": "من الموضع 1 حتى قبل 3: الحرفان e وl."}
```

```quiz
{"question": "كيف تقسم نصًا على النقطة؟", "choices": ["split(\".\")", "split(\"\\\\.\")", "split('.')", "divide(\".\")"], "answer": 1, "explanation": "split تأخذ regex والنقطة فيه تعني أي حرف، فنكتب \\\\. للنقطة نفسها."}
```

```quiz
{"question": "متى نستخدم StringBuilder؟", "choices": ["للمقارنة", "لبناء نص كبير بإضافات كثيرة", "لقراءة الملفات", "للتحويل إلى رقم"], "answer": 1, "explanation": "StringBuilder يعدّل في نفس الذاكرة فيكون أسرع من += في الحلقات."}
```

## الخلاصة

- `length()` و`charAt` و`trim` و`toUpperCase` و`contains` و`indexOf` و`replace` و`substring(i, j)` و`split`.
- النصوص غير قابلة للتعديل، والمقارنة بـ `equals`.
- `StringBuilder` للبناء السريع، و`String.format` و`formatted` للتنسيق، و`"""` للنصوص متعددة الأسطر.
