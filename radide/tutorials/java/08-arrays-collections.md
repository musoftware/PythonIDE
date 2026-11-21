# الدرس 8: المصفوفات وArrayList وHashMap

لتخزين درجات 30 طالبًا لا نعرّف 30 متغيرًا، بل نستخدم **مصفوفة** أو **مجموعة** (collection) تحمل قيمًا كثيرة تحت اسم واحد.

> **تشبيه:** المصفوفة مثل **خزانة أدراج مرقّمة** تبدأ من **صفر**، وعدد أدراجها ثابت. و`ArrayList` خزانة **تتمدد** وحدها كلما أضفت درجًا. و`HashMap` مثل **دليل الهاتف**: تبحث بالاسم فتجد الرقم.

## المصفوفات (Arrays)

```java run
public class Main {
    public static void main(String[] args) {
        int[] grades = {85, 92, 78, 64, 99};
        System.out.println(grades[0]);
        System.out.println(grades[4]);
        System.out.println(grades.length);
        grades[2] = 80;
        System.out.println(grades[2]);
    }
}
```

```text output
85
99
5
80
```

- `int[]` مصفوفة أعداد صحيحة، والفهرس يبدأ من `0`، وآخر فهرس `length - 1`.
- لاحظ: `length` بلا أقواس للمصفوفات.

### الإنشاء بحجم محدد والمرور عليها

```java run
public class Main {
    public static void main(String[] args) {
        String[] names = new String[3];
        names[0] = "علي";
        names[1] = "هدى";
        names[2] = "مريم";
        for (int i = 0; i < names.length; i++) {
            System.out.println((i + 1) + ". " + names[i]);
        }

        double[] prices = {12.5, 30, 7.25, 50};
        double total = 0, max = prices[0];
        for (double p : prices) {
            total += p;
            if (p > max) {
                max = p;
            }
        }
        System.out.println("المجموع = " + total);
        System.out.println("الأغلى = " + max);
    }
}
```

```text output
1. علي
2. هدى
3. مريم
المجموع = 99.75
الأغلى = 50.0
```

### الصنف `Arrays`

```java run
import java.util.Arrays;

public class Main {
    public static void main(String[] args) {
        int[] nums = {42, 7, 19, 3, 25};
        System.out.println(Arrays.toString(nums));
        Arrays.sort(nums);
        System.out.println(Arrays.toString(nums));
        System.out.println(Arrays.binarySearch(nums, 19));
        int[] copy = Arrays.copyOf(nums, 3);
        System.out.println(Arrays.toString(copy));
    }
}
```

```text output
[42, 7, 19, 3, 25]
[3, 7, 19, 25, 42]
2
[3, 7, 19]
```

> **انتبه:** `System.out.println(nums)` تطبع شيئًا غريبًا مثل `[I@1b6d3586` (عنوان المصفوفة في الذاكرة). استخدم `Arrays.toString(nums)`.

## القوائم: `ArrayList`

```java run
import java.util.ArrayList;
import java.util.Collections;

public class Main {
    public static void main(String[] args) {
        ArrayList<String> fruits = new ArrayList<>();
        fruits.add("تفاح");
        fruits.add("موز");
        fruits.add("برتقال");
        System.out.println("عدد الفواكه: " + fruits.size());

        fruits.add(1, "مانجو");
        fruits.remove("موز");
        System.out.println(fruits);
        System.out.println(fruits.contains("تفاح"));
        System.out.println(fruits.get(0));

        ArrayList<Integer> nums = new ArrayList<>();
        nums.add(30);
        nums.add(10);
        nums.add(20);
        Collections.sort(nums);
        System.out.println(nums);
    }
}
```

```text output
عدد الفواكه: 3
[تفاح, مانجو, برتقال]
true
تفاح
[10, 20, 30]
```

| الدالة | وظيفتها |
|---|---|
| `add(x)` / `add(i, x)` | إضافة في النهاية / في الموضع `i` |
| `get(i)` | العنصر رقم `i` |
| `set(i, x)` | تغيير العنصر رقم `i` |
| `remove(i)` / `remove(x)` | حذف بالموضع / بالقيمة |
| `size()` | عدد العناصر |
| `contains(x)` | هل العنصر موجود؟ |
| `clear()` | حذف الكل |

> **مهم:** `ArrayList` لا تقبل الأنواع البدائية مباشرة: نكتب `ArrayList<Integer>` وليس `ArrayList<int>`، و`Double` بدل `double`. وJava تحول بينهما تلقائيًا (autoboxing).

## القواميس: `HashMap`

```java run
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

public class Main {
    public static void main(String[] args) {
        Map<String, Integer> stock = new TreeMap<>();   // TreeMap: مرتبة حسب المفتاح
        stock.put("pens", 120);
        stock.put("notebooks", 45);
        stock.put("rulers", 30);

        stock.put("notebooks", stock.get("notebooks") + 5);
        System.out.println(stock.get("notebooks"));
        System.out.println(stock.containsKey("eraser"));
        System.out.println(stock.getOrDefault("eraser", 0));

        for (Map.Entry<String, Integer> e : stock.entrySet()) {
            System.out.println(e.getKey() + ": " + e.getValue());
        }

        Map<String, String> phones = new HashMap<>();
        phones.put("Ali", "0100");
        System.out.println(phones.get("Ali"));
        System.out.println(phones.get("Omar"));
    }
}
```

```text output
50
false
0
notebooks: 50
pens: 120
rulers: 30
0100
null
```

- `put(k, v)` يضيف أو يغير، و`get(k)` يرجع القيمة أو `null` إذا لم يوجد المفتاح.
- `HashMap` لا تضمن ترتيب العناصر عند المرور عليها، و`TreeMap` ترتبها حسب المفتاح، و`LinkedHashMap` تحفظ ترتيب الإضافة.

### مثال: عدّ تكرار الكلمات

```java run
import java.util.LinkedHashMap;
import java.util.Map;

public class Main {
    public static void main(String[] args) {
        String text = "قط كلب قط عصفور كلب قط";
        Map<String, Integer> counts = new LinkedHashMap<>();
        for (String w : text.split(" ")) {
            counts.put(w, counts.getOrDefault(w, 0) + 1);
        }
        for (var e : counts.entrySet()) {
            System.out.println(e.getKey() + " = " + e.getValue());
        }
    }
}
```

```text output
قط = 3
كلب = 2
عصفور = 1
```

## لمحة عن Streams

مثل LINQ في C#: أسئلة على المجموعات في سطر واحد:

```java run
import java.util.List;
import java.util.stream.Collectors;

public class Main {
    public static void main(String[] args) {
        List<Integer> nums = List.of(5, 12, 8, 3, 20, 15);
        System.out.println(nums.stream().mapToInt(n -> n).sum());
        System.out.println(nums.stream().mapToInt(n -> n).max().getAsInt());
        List<Integer> big = nums.stream().filter(n -> n > 10).collect(Collectors.toList());
        System.out.println(big);
        System.out.println(nums.stream().map(n -> n * 2).collect(Collectors.toList()));
        System.out.println(nums.stream().sorted().collect(Collectors.toList()));
    }
}
```

```text output
63
20
[12, 20, 15]
[10, 24, 16, 6, 40, 30]
[3, 5, 8, 12, 15, 20]
```

`n -> n > 10` **تعبير لامدا** (lambda): دالة صغيرة بلا اسم. و`List.of(...)` تنشئ قائمة ثابتة لا تقبل الإضافة.

## المصفوفات ثنائية الأبعاد

```java run
public class Main {
    public static void main(String[] args) {
        int[][] table = {
            {1, 2, 3},
            {4, 5, 6}
        };
        for (int[] row : table) {
            for (int v : row) {
                System.out.print(v + " ");
            }
            System.out.println();
        }
    }
}
```

```text output
1 2 3
4 5 6
```

## أخطاء شائعة

- **تجاوز الحدود:** `grades[5]` في مصفوفة طولها 5 توقف البرنامج بـ `ArrayIndexOutOfBoundsException`.
- **`length` و`length()` و`size()`:** المصفوفة `arr.length`، والنص `s.length()`، والقائمة `list.size()`.
- **`ArrayList<int>`:** خطأ ترجمة `unexpected type`. استخدم `Integer`.
- **حذف عناصر داخل for-each على نفس القائمة:** يعطي `ConcurrentModificationException`. استخدم `list.removeIf(x -> ...)`.

## تمارين

### التمرين 1

اطبع أكبر وأصغر عنصر في المصفوفة دون `Arrays.sort`.

```java exercise
public class Main {
    public static void main(String[] args) {
        int[] values = {14, -3, 27, 8, 0, 19};
        // الأكبر = 27
        // الأصغر = -3
    }
}
```

```java solution
public class Main {
    public static void main(String[] args) {
        int[] values = {14, -3, 27, 8, 0, 19};
        int max = values[0], min = values[0];
        for (int v : values) {
            if (v > max) {
                max = v;
            }
            if (v < min) {
                min = v;
            }
        }
        System.out.println("الأكبر = " + max);
        System.out.println("الأصغر = " + min);
    }
}
```

```text output
الأكبر = 27
الأصغر = -3
```

### التمرين 2

اقرأ أسماء حتى سطر فارغ في `ArrayList<String>`، ثم اطبعها مرتبة مرقمة.

```java exercise
import java.util.ArrayList;
import java.util.Collections;
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        ArrayList<String> names = new ArrayList<>();
        // اقرأ حتى سطر فارغ، رتّب، اطبع
    }
}
```

```java solution
import java.util.ArrayList;
import java.util.Collections;
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        ArrayList<String> names = new ArrayList<>();
        while (in.hasNextLine()) {
            String line = in.nextLine();
            if (line.isEmpty()) {
                break;
            }
            names.add(line);
        }
        Collections.sort(names);
        for (int i = 0; i < names.size(); i++) {
            System.out.println((i + 1) + ". " + names.get(i));
        }
    }
}
```

```text input
Sara
Adam
Mona

```

```text output
1. Adam
2. Mona
3. Sara
```

### التمرين 3

اطبع من القاموس المنتجات التي سعرها أقل من 20 (بترتيب الإضافة، استخدم `LinkedHashMap`).

```java exercise
import java.util.LinkedHashMap;
import java.util.Map;

public class Main {
    public static void main(String[] args) {
        Map<String, Double> prices = new LinkedHashMap<>();
        prices.put("خبز", 5.0);
        prices.put("جبن", 45.0);
        prices.put("لبن", 18.0);
        prices.put("عسل", 120.0);
        prices.put("بيض", 12.0);
        // خبز ثم لبن ثم بيض
    }
}
```

```java solution
import java.util.LinkedHashMap;
import java.util.Map;

public class Main {
    public static void main(String[] args) {
        Map<String, Double> prices = new LinkedHashMap<>();
        prices.put("خبز", 5.0);
        prices.put("جبن", 45.0);
        prices.put("لبن", 18.0);
        prices.put("عسل", 120.0);
        prices.put("بيض", 12.0);
        for (var e : prices.entrySet()) {
            if (e.getValue() < 20) {
                System.out.println(e.getKey());
            }
        }
    }
}
```

```text output
خبز
لبن
بيض
```

## اختبر نفسك

```quiz
{"question": "كيف تعرف عدد عناصر ArrayList اسمها list؟", "choices": ["list.length", "list.length()", "list.size()", "list.count"], "answer": 2, "explanation": "المصفوفة length، والنص length()، والمجموعات size()."}
```

```quiz
{"question": "لماذا نكتب ArrayList<Integer> وليس ArrayList<int>؟", "choices": ["خطأ إملائي", "المجموعات تقبل الكائنات فقط، وInteger هو الصنف المغلِّف لـ int", "Integer أسرع", "لا فرق"], "answer": 1, "explanation": "الأنواع البدائية ليست كائنات، فنستخدم الأصناف المغلِّفة."}
```

```quiz
{"question": "ماذا ترجع map.get(key) إذا لم يكن المفتاح موجودًا؟", "choices": ["0", "خطأ", "null", "\"\""], "answer": 2, "explanation": "ترجع null، ويمكن استخدام getOrDefault لقيمة بديلة."}
```

```quiz
{"question": "كيف تطبع محتوى مصفوفة int[] nums بشكل مقروء؟", "choices": ["System.out.println(nums)", "System.out.println(Arrays.toString(nums))", "nums.print()", "System.out.println(nums.toString)"], "answer": 1, "explanation": "Arrays.toString تعطي [1, 2, 3]، أما طباعة المصفوفة مباشرة فتعطي عنوانها."}
```

## الخلاصة

- المصفوفة `int[]` حجمها ثابت، و`Arrays.toString` و`Arrays.sort` تساعدان.
- `ArrayList<T>`: `add` و`get` و`remove` و`size`، مع `Integer` بدل `int`.
- `HashMap` / `TreeMap` / `LinkedHashMap`: `put` و`get` و`getOrDefault` و`entrySet`.
- Streams: `filter` و`map` و`sorted` و`sum`.
