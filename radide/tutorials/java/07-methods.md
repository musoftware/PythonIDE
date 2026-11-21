# الدرس 7: الدوال (Methods)

**الدالة** (method) تجمع مجموعة تعليمات تحت اسم واحد، فنستدعيها كلما احتجنا إليها بدل تكرار الكود. وقد استخدمنا دوالًا كثيرة جاهزة مثل `println` و`Math.sqrt`، واليوم نكتب دوالنا.

> **تشبيه:** الدالة مثل **ماكينة العصير**: تضع فيها فاكهة (**المعاملات**)، فتعطيك عصيرًا (**القيمة المرجعة**)، ولا تحتاج أن تعرف ما يحدث بداخلها.

## دالة بسيطة

في Java تُكتب الدوال **داخل الصنف** بجانب `main`. والآن نكتبها `static` لكي نستدعيها من `main` مباشرة:

```java run
public class Main {
    static void sayHello() {
        System.out.println("مرحبًا بك في برنامجنا!");
        System.out.println("-----------------------");
    }

    public static void main(String[] args) {
        sayHello();
        sayHello();
    }
}
```

```text output
مرحبًا بك في برنامجنا!
-----------------------
مرحبًا بك في برنامجنا!
-----------------------
```

- **التعريف**: `static void sayHello() { ... }`، و`void` تعني أنها لا ترجع قيمة.
- **الاستدعاء**: `sayHello();`.
- العُرف في Java: أسماء الدوال بأسلوب **camelCase** وتبدأ بحرف صغير (`calculateTotal`).

## المعاملات والقيمة المرجعة

```java run
public class Main {
    static void greet(String name, int age) {
        System.out.println("أهلًا " + name + "، عمرك " + age + " سنة");
    }

    static int square(int x) {
        return x * x;
    }

    static double average(double a, double b, double c) {
        return (a + b + c) / 3;
    }

    public static void main(String[] args) {
        greet("سلمى", 14);
        System.out.println(square(6));
        System.out.println(square(3) + square(4));
        System.out.println(average(80, 90, 70));
    }
}
```

```text output
أهلًا سلمى، عمرك 14 سنة
36
25
80.0
```

- `name` و`age` **معاملات** (parameters)، والقيم `"سلمى"` و`14` **وسائط** (arguments).
- النوع قبل اسم الدالة (`int`، `double`) هو نوع القيمة المرجعة، و`return` تنهي الدالة وترجعها.

## التحميل الزائد (Overloading)

عدة دوال بنفس الاسم إذا اختلفت معاملاتها:

```java run
public class Main {
    static int add(int a, int b) {
        return a + b;
    }

    static double add(double a, double b) {
        return a + b;
    }

    static int add(int a, int b, int c) {
        return a + b + c;
    }

    public static void main(String[] args) {
        System.out.println(add(2, 3));
        System.out.println(add(2.5, 3.1));
        System.out.println(add(1, 2, 3));
    }
}
```

```text output
5
5.6
6
```

> **ملحوظة:** Java لا تدعم القيم الافتراضية للمعاملات (مثل `int qty = 1`). البديل هو التحميل الزائد: دالة بمعامل أقل تستدعي الأخرى بالقيمة الافتراضية.

## عدد متغير من الوسائط: `...`

```java run
public class Main {
    static int sum(int... numbers) {
        int total = 0;
        for (int n : numbers) {
            total += n;
        }
        return total;
    }

    public static void main(String[] args) {
        System.out.println(sum());
        System.out.println(sum(5));
        System.out.println(sum(1, 2, 3, 4));
    }
}
```

```text output
0
5
10
```

`int... numbers` تجعل `numbers` مصفوفة فيها كل ما أُرسل.

## التمرير بالقيمة (Pass by Value)

Java ترسل **نسخة** من قيمة المتغير البدائي، فتعديلها داخل الدالة لا يغير الأصل:

```java run
public class Main {
    static void doubleIt(int n) {
        n = n * 2;
        System.out.println("داخل الدالة: " + n);
    }

    public static void main(String[] args) {
        int x = 5;
        doubleIt(x);
        System.out.println("خارج الدالة: " + x);
    }
}
```

```text output
داخل الدالة: 10
خارج الدالة: 5
```

إذا أردت قيمة جديدة فأرجعها بـ `return`: `x = doubleIt(x);`.

## نطاق المتغيرات

```java run
public class Main {
    static int calls = 0;          // حقل في الصنف: يبقى بين الاستدعاءات

    static void counter() {
        int local = 0;             // محلي: يُنشأ من جديد كل مرة
        local++;
        calls++;
        System.out.println("local = " + local + ", calls = " + calls);
    }

    public static void main(String[] args) {
        counter();
        counter();
    }
}
```

```text output
local = 1, calls = 1
local = 1, calls = 2
```

## الاستدعاء الذاتي (Recursion)

```java run
public class Main {
    static long factorial(int n) {
        if (n <= 1) {
            return 1;                  // حالة التوقف
        }
        return n * factorial(n - 1);
    }

    static int fib(int n) {
        return n < 2 ? n : fib(n - 1) + fib(n - 2);
    }

    public static void main(String[] args) {
        System.out.println(factorial(5));
        System.out.println(factorial(15));
        for (int i = 0; i < 10; i++) {
            System.out.print(fib(i) + " ");
        }
        System.out.println();
    }
}
```

```text output
120
1307674368000
0 1 1 2 3 5 8 13 21 34
```

## أخطاء شائعة

### نسيان `return`

<!-- compile-error -->
```java
public class Main {
    static int twice(int x) {
        int y = x * 2;
    }
}
```

```text
Main.java:4: error: missing return statement
```

### استدعاء دالة غير `static` من `main`

<!-- compile-error -->
```java
public class Main {
    void hello() {
        System.out.println("مرحبا");
    }

    public static void main(String[] args) {
        hello();
    }
}
```

```text
Main.java:7: error: non-static method hello() cannot be referenced from a static context
```

`main` دالة `static`، فلا تستطيع استدعاء دالة غير ثابتة إلا عبر كائن. الحل الآن: أضف `static` للدالة. وسنفهم الفرق في درس الأصناف.

### عدد الوسائط أو نوعها خطأ

`greet("سلمى")` تعطي `method greet in class Main cannot be applied to given types`.

## تمارين

### التمرين 1

اكتب دالة `max3` ترجع أكبر عدد من ثلاثة.

```java exercise
public class Main {
    static int max3(int a, int b, int c) {
        return 0;
    }

    public static void main(String[] args) {
        System.out.println(max3(4, 9, 2));
        System.out.println(max3(-1, -5, -3));
    }
}
```

```java solution
public class Main {
    static int max3(int a, int b, int c) {
        return Math.max(a, Math.max(b, c));
    }

    public static void main(String[] args) {
        System.out.println(max3(4, 9, 2));
        System.out.println(max3(-1, -5, -3));
    }
}
```

```text output
9
-1
```

### التمرين 2

اكتب دالة `isPrime` واطبع بها الأعداد الأولية من 2 إلى 30.

```java exercise
public class Main {
    static boolean isPrime(int n) {
        return false;
    }

    public static void main(String[] args) {
        for (int i = 2; i <= 30; i++) {
            if (isPrime(i)) {
                System.out.print(i + " ");
            }
        }
        System.out.println();
    }
}
```

```java solution
public class Main {
    static boolean isPrime(int n) {
        if (n < 2) {
            return false;
        }
        for (int d = 2; d * d <= n; d++) {
            if (n % d == 0) {
                return false;
            }
        }
        return true;
    }

    public static void main(String[] args) {
        for (int i = 2; i <= 30; i++) {
            if (isPrime(i)) {
                System.out.print(i + " ");
            }
        }
        System.out.println();
    }
}
```

```text output
2 3 5 7 11 13 17 19 23 29
```

### التمرين 3

اكتب دالتين بالاسم `power`: الأولى `power(double b)` ترجع المربع، والثانية `power(double b, int e)` تحسب الأس بحلقة. اجعل الأولى تستدعي الثانية.

```java exercise
public class Main {
    // power(double b) و power(double b, int e)

    public static void main(String[] args) {
        System.out.println(power(5));
        System.out.println(power(2, 10));
        System.out.println(power(1.5, 3));
    }
}
```

```java solution
public class Main {
    static double power(double b) {
        return power(b, 2);
    }

    static double power(double b, int e) {
        double result = 1;
        for (int i = 0; i < e; i++) {
            result *= b;
        }
        return result;
    }

    public static void main(String[] args) {
        System.out.println(power(5));
        System.out.println(power(2, 10));
        System.out.println(power(1.5, 3));
    }
}
```

```text output
25.0
1024.0
3.375
```

## اختبر نفسك

```quiz
{"question": "لماذا نكتب static قبل الدوال التي نستدعيها من main الآن؟", "choices": ["لتسريعها", "لأن main نفسها static ولا تستطيع استدعاء دالة غير ثابتة دون كائن", "لأنها إلزامية في كل دالة", "لجعلها خاصة"], "answer": 1, "explanation": "الدوال الثابتة تخص الصنف ولا تحتاج إلى كائن."}
```

```quiz
{"question": "ما البديل في Java عن القيم الافتراضية للمعاملات؟", "choices": ["لا يوجد بديل", "التحميل الزائد: دالة بمعاملات أقل تستدعي الأخرى", "var", "final"], "answer": 1, "explanation": "Java لا تدعم المعاملات الاختيارية، فنكتب عدة نسخ من الدالة."}
```

```quiz
{"question": "بعد int x = 5; doubleIt(x); حيث doubleIt تضاعف معاملها فقط، كم قيمة x؟", "choices": ["10", "5", "0", "خطأ"], "answer": 1, "explanation": "Java تمرر نسخة من قيمة المتغير البدائي، فالأصل لا يتغير."}
```

## الخلاصة

- الدوال داخل الصنف: نوع القيمة المرجعة والاسم والمعاملات، و`return`.
- التحميل الزائد بدل القيم الافتراضية، و`int...` لعدد متغير من الوسائط.
- المتغيرات البدائية تُمرر بالقيمة، والمحلية تُنشأ من جديد كل استدعاء.
- الاستدعاء الذاتي يحتاج إلى حالة توقف.
