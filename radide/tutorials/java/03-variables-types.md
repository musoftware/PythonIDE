# الدرس 3: المتغيرات وأنواع البيانات

البرامج تتعامل مع **بيانات**: اسم المستخدم، وعمره، وسعر المنتج، وهل الطلب مدفوع أم لا. وحتى يتذكر البرنامج هذه البيانات نضعها في **متغيرات**.

> **تشبيه:** المتغير مثل **علبة عليها ملصق**: الملصق هو **الاسم**، وما بداخلها هو **القيمة**، ونوع العلبة يحدد ما يمكن وضعه فيها. علبة الأرقام لا تقبل نصًا.

## تعريف المتغير

**النوع** ثم **الاسم** ثم `=` و**القيمة**:

```java run
public class Main {
    public static void main(String[] args) {
        int age = 25;
        String name = "خالد";
        double height = 1.75;
        boolean isStudent = true;
        char grade = 'A';

        System.out.println(name);
        System.out.println(age);
        System.out.println(height);
        System.out.println(isStudent);
        System.out.println(grade);
    }
}
```

```text output
خالد
25
1.75
true
A
```

## الأنواع البدائية والنصوص

| النوع | يخزّن | مثال |
|---|---|---|
| `int` | عدد صحيح (حتى نحو 2 مليار) | `int count = 10;` |
| `long` | عدد صحيح كبير جدًا (ينتهي بـ `L`) | `long stars = 8000000000L;` |
| `double` | عدد عشري | `double price = 19.99;` |
| `float` | عدد عشري أقل دقة (ينتهي بـ `f`) | `float t = 36.6f;` |
| `boolean` | صح أو خطأ | `boolean done = false;` |
| `char` | حرف واحد بين `' '` | `char c = 'ب';` |
| `String` | نص بين `" "` (لاحظ S كبيرة) | `String city = "طنطا";` |

الأنواع بحروف صغيرة (`int`، `double`، `boolean`، `char`...) تسمى **الأنواع البدائية** (primitive types). أما `String` فهو **صنف**، ولذلك يبدأ بحرف كبير.

## تغيير القيمة

```java run
public class Main {
    public static void main(String[] args) {
        int score = 10;
        System.out.println("النقاط: " + score);
        score = 25;
        System.out.println("النقاط: " + score);
        score = score + 5;
        System.out.println("النقاط: " + score);
    }
}
```

```text output
النقاط: 10
النقاط: 25
النقاط: 30
```

## `var`: دع المترجم يستنتج النوع

منذ Java 10 يمكن كتابة `var` للمتغيرات المحلية إذا كانت القيمة الابتدائية واضحة:

```java run
public class Main {
    public static void main(String[] args) {
        var city = "أسوان";     // String
        var year = 2026;         // int
        var pi = 3.14;           // double
        System.out.println(city + " " + year + " " + pi);
    }
}
```

```text output
أسوان 2026 3.14
```

النوع يُحدد مرة واحدة ولا يتغير بعدها: `year = "نص";` خطأ ترجمة.

## الثوابت: `final`

```java run
public class Main {
    public static void main(String[] args) {
        final double PI = 3.14159;
        final int DAYS_IN_WEEK = 7;
        double r = 2;
        System.out.println("مساحة الدائرة = " + PI * r * r);
        System.out.println("أيام 3 أسابيع = " + DAYS_IN_WEEK * 3);
    }
}
```

```text output
مساحة الدائرة = 12.56636
أيام 3 أسابيع = 21
```

العُرف في Java: الثوابت بحروف كبيرة وشرطة سفلية `MAX_SCORE`.

## التحويل بين الأنواع

### من نص إلى رقم

```java run
public class Main {
    public static void main(String[] args) {
        int n = Integer.parseInt("42");
        double d = Double.parseDouble("12.5");
        System.out.println(n + 8);
        System.out.println(d * 2);
    }
}
```

```text output
50
25.0
```

لاحظ أن Java تطبع العدد العشري `25` بالشكل `25.0` دائمًا.

### من رقم إلى نص

```java run
public class Main {
    public static void main(String[] args) {
        int n = 7;
        String s = String.valueOf(n);
        System.out.println(s + s);
        System.out.println(n + n);
        System.out.println("" + n + n);
    }
}
```

```text output
77
14
77
```

### التحويل الصريح (Casting)

```java run
public class Main {
    public static void main(String[] args) {
        double d = 9.8;
        int i = (int) d;           // يقطع الكسر
        System.out.println(i);

        int a = 7, b = 2;
        double avg = (double) a / b;
        System.out.println(avg);
        System.out.println(Math.round(9.8));
    }
}
```

```text output
9
3.5
10
```

- التحويل من نوع صغير إلى كبير (`int` إلى `double`) يحدث **تلقائيًا**.
- من كبير إلى صغير (`double` إلى `int`) يحتاج إلى **تحويل صريح** `(int)` لأنه قد يفقد معلومات.

## الأصناف المغلِّفة (Wrapper Classes)

لكل نوع بدائي صنف مقابل: `Integer` لـ `int`، و`Double` لـ `double`، و`Boolean` لـ `boolean`، و`Character` لـ `char`. وفيها دوال مفيدة:

```java run
public class Main {
    public static void main(String[] args) {
        System.out.println(Integer.MAX_VALUE);
        System.out.println(Integer.MIN_VALUE);
        System.out.println(Character.isDigit('5'));
        System.out.println(Integer.toBinaryString(10));
    }
}
```

```text output
2147483647
-2147483648
true
1010
```

## أخطاء شائعة

### متغير محلي بلا قيمة

<!-- compile-error -->
```java
public class Main {
    public static void main(String[] args) {
        int total;
        System.out.println(total);
    }
}
```

```text
Main.java:4: error: variable total might not have been initialized
```

### نوع غير متوافق

<!-- compile-error -->
```java
public class Main {
    public static void main(String[] args) {
        int x = 3.7;
    }
}
```

```text
Main.java:3: error: incompatible types: possible lossy conversion from double to int
```

**المعنى:** «تحويل قد يفقد بيانات من `double` إلى `int`». إذا كنت تقصد ذلك فاكتب `(int) 3.7`.

### `string` بحرف صغير

`string name = "Ali";` خطأ: `cannot find symbol ... class string`. الصحيح `String`.

## تمارين

### التمرين 1

عرّف متغيرات لكتاب: العنوان، وعدد الصفحات، والسعر، ومتوفر، ثم اطبعها.

```java exercise
public class Main {
    public static void main(String[] args) {
        // الكتاب: البرمجة للجميع
        // الصفحات: 320
        // السعر: 150.5
        // متوفر: true
    }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        String title = "البرمجة للجميع";
        int pages = 320;
        double price = 150.5;
        boolean available = true;
        System.out.println("الكتاب: " + title);
        System.out.println("الصفحات: " + pages);
        System.out.println("السعر: " + price);
        System.out.println("متوفر: " + available);
    }
}
```

```text output
الكتاب: البرمجة للجميع
الصفحات: 320
السعر: 150.5
متوفر: true
```

### التمرين 2

حوّل النصين `"15"` و`"27"` إلى أرقام واطبع مجموعهما.

```java exercise
public class Main {
    public static void main(String[] args) {
        String a = "15";
        String b = "27";
        // اطبع: 42
    }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        String a = "15";
        String b = "27";
        System.out.println(Integer.parseInt(a) + Integer.parseInt(b));
    }
}
```

```text output
42
```

### التمرين 3

بدّل قيمتي `x` و`y` باستخدام متغير مؤقت.

```java exercise
public class Main {
    public static void main(String[] args) {
        int x = 3;
        int y = 8;
        // بدّل القيمتين
        System.out.println("x = " + x + ", y = " + y);
    }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        int x = 3;
        int y = 8;
        int temp = x;
        x = y;
        y = temp;
        System.out.println("x = " + x + ", y = " + y);
    }
}
```

```text output
x = 8, y = 3
```

## اختبر نفسك

```quiz
{"question": "لماذا يبدأ String بحرف كبير وint بحرف صغير؟", "choices": ["خطأ في Java", "لأن int نوع بدائي أما String فصنف", "لا فرق", "لأن String أقدم"], "answer": 1, "explanation": "الأنواع البدائية بحروف صغيرة، والأصناف تبدأ بحرف كبير."}
```

```quiz
{"question": "ماذا يطبع System.out.println(10 / 4.0);؟", "choices": ["2", "2.5", "2.0", "3"], "answer": 1, "explanation": "أحد الطرفين عشري فتكون القسمة عشرية = 2.5."}
```

```quiz
{"question": "أي كلمة تجعل المتغير ثابتًا لا يتغير في Java؟", "choices": ["const", "static", "final", "var"], "answer": 2, "explanation": "final تمنع تغيير القيمة بعد إسنادها."}
```

```quiz
{"question": "ما ناتج (int) 7.9؟", "choices": ["8", "7", "7.9", "خطأ"], "answer": 1, "explanation": "التحويل الصريح إلى int يقطع الكسر ولا يقرّب."}
```

## الخلاصة

- المتغير: نوع واسم وقيمة، والأنواع البدائية `int` و`long` و`double` و`boolean` و`char`، والنص `String`.
- `var` للاستنتاج، و`final` للثوابت.
- `Integer.parseInt` و`Double.parseDouble` و`String.valueOf` للتحويل، و`(int)` للتحويل الصريح.
- Java تطبع الأعداد العشرية مع `.0` مثل `25.0`.
