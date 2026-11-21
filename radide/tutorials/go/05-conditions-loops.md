# الدرس 5: الشروط وحلقة `for`

في هذا الدرس نتعلم كيف يتخذ البرنامج القرارات (`if` و`switch`)، وكيف يكرر العمل. ومفاجأة Go اللطيفة: **حلقة التكرار واحدة فقط** اسمها `for`، لكنها تقوم بكل الأدوار.

## `if` و`else`

```go run
package main

import "fmt"

func main() {
    score := 83
    if score >= 90 {
        fmt.Println("ممتاز")
    } else if score >= 80 {
        fmt.Println("جيد جدًا")
    } else if score >= 50 {
        fmt.Println("ناجح")
    } else {
        fmt.Println("راسب")
    }
}
```

```text output
جيد جدًا
```

- لا أقواس حول الشرط في Go.
- الأقواس المعقوصة `{ }` **إجبارية** حتى لو كان سطرًا واحدًا.
- `else` يجب أن تكون في نفس سطر `}`.

## `if` مع تعريف قصير

ميزة جميلة: يمكن تعريف متغير داخل `if` نفسها، ويعيش فقط داخلها:

```go run
package main

import (
    "fmt"
    "strconv"
)

func main() {
    if n, err := strconv.Atoi("42"); err == nil {
        fmt.Println("الرقم:", n)
    } else {
        fmt.Println("خطأ:", err)
    }
}
```

```text output
الرقم: 42
```

## العوامل المنطقية

| العامل | معناه |
|---|---|
| `==` و`!=` | يساوي، لا يساوي |
| `<` `>` `<=` `>=` | مقارنات |
| `&&` | و |
| <code>&#124;&#124;</code> | أو |
| `!` | ليس |

وفي Go الشرط يجب أن يكون من نوع `bool` فعلًا: `if n { }` مع `n` عدد صحيح خطأ ترجمة (على عكس C).

## `switch`

`switch` في Go أذكى من C: **لا تحتاج `break`**، وكل حالة يمكن أن تحتوي عدة قيم، بل وشروطًا:

```go run
package main

import "fmt"

func main() {
    day := "الجمعة"
    switch day {
    case "الجمعة", "السبت":
        fmt.Println("عطلة نهاية الأسبوع")
    case "الأحد":
        fmt.Println("بداية الأسبوع")
    default:
        fmt.Println("يوم عمل")
    }

    temp := 36
    switch {                       // بلا متغير: كل case شرط
    case temp >= 35:
        fmt.Println("حار جدًا")
    case temp >= 25:
        fmt.Println("دافئ")
    default:
        fmt.Println("معتدل")
    }
}
```

```text output
عطلة نهاية الأسبوع
حار جدًا
```

## حلقة `for` بأشكالها الثلاثة

> **تشبيه:** `for` في Go مثل **سكين الجيب السويسري**: أداة واحدة تقوم بعمل `for` و`while` والحلقة اللانهائية في اللغات الأخرى.

```go run
package main

import "fmt"

func main() {
    // 1) الشكل الكلاسيكي
    for i := 1; i <= 3; i++ {
        fmt.Println("الدورة", i)
    }

    // 2) مثل while
    n := 1
    for n < 100 {
        n *= 2
    }
    fmt.Println("أول قوة لـ 2 أكبر من 100:", n)

    // 3) حلقة لا نهائية مع break
    count := 0
    for {
        count++
        if count == 5 {
            break
        }
    }
    fmt.Println("count =", count)
}
```

```text output
الدورة 1
الدورة 2
الدورة 3
أول قوة لـ 2 أكبر من 100: 128
count = 5
```

## `range`: المرور على المجموعات

`range` تمر على عناصر نص أو شريحة أو خريطة، وتعطيك **الفهرس والقيمة**:

```go run
package main

import "fmt"

func main() {
    fruits := []string{"تفاح", "موز", "عنب"}
    for i, f := range fruits {
        fmt.Println(i, f)
    }
    total := 0
    for _, x := range []int{5, 10, 15} {   // _ لتجاهل الفهرس
        total += x
    }
    fmt.Println("المجموع:", total)
    for i := range 3 {                      // Go 1.22+: من 0 إلى 2
        fmt.Print(i, " ")
    }
    fmt.Println()
}
```

```text output
0 تفاح
1 موز
2 عنب
المجموع: 30
0 1 2 
```

## `continue` والحلقات المتداخلة

```go run
package main

import "fmt"

func main() {
    for i := 1; i <= 10; i++ {
        if i%3 != 0 {
            continue
        }
        fmt.Print(i, " ")
    }
    fmt.Println()

    for r := 1; r <= 3; r++ {
        for c := 1; c <= 3; c++ {
            fmt.Printf("%3d", r*c)
        }
        fmt.Println()
    }
}
```

```text output
3 6 9 
  1  2  3
  2  4  6
  3  6  9
```

## أخطاء شائعة

- **وضع `else` في سطر جديد:** خطأ ترجمة؛ اكتب `} else {`.
- **انتظار `break` في `switch`:** لا داعي له. وإن أردت النزول للحالة التالية عمدًا اكتب `fallthrough`.
- **حلقة لا تنتهي بالخطأ:** نسيان تغيير متغير الشرط في `for n < 100`. أوقف البرنامج بـ **Shift+F5**.

## تمارين

### التمرين 1

برنامج FizzBuzz الشهير: اطبع الأعداد من 1 إلى 15، لكن اكتب `Fizz` لمضاعفات 3، و`Buzz` لمضاعفات 5، و`FizzBuzz` لمضاعفات الاثنين:

```go exercise
package main

import "fmt"

func main() {
    for i := 1; i <= 15; i++ {
        // أكمل
        fmt.Print("")
    }
}
```

```go solution
package main

import "fmt"

func main() {
    for i := 1; i <= 15; i++ {
        switch {
        case i%15 == 0:
            fmt.Println("FizzBuzz")
        case i%3 == 0:
            fmt.Println("Fizz")
        case i%5 == 0:
            fmt.Println("Buzz")
        default:
            fmt.Println(i)
        }
    }
}
```

```text output
1
2
Fizz
4
Buzz
Fizz
7
8
Fizz
Buzz
11
Fizz
13
14
FizzBuzz
```

### التمرين 2

احسب مجموع أرقام العدد `98765` باستخدام `for` بشكل while:

```go exercise
package main

import "fmt"

func main() {
    n := 98765
    sum := 0
    // أكمل
    fmt.Println(sum, n)
}
```

```go solution
package main

import "fmt"

func main() {
    n := 98765
    sum := 0
    for n > 0 {
        sum += n % 10
        n /= 10
    }
    fmt.Println(sum)
}
```

```text output
35
```

## اختبر نفسك

```quiz
{"question": "كم نوعًا من حلقات التكرار في Go؟", "choices": ["ثلاثة: for وwhile وdo", "واحد فقط: for بأشكال متعددة", "اثنان", "لا توجد حلقات"], "answer": 1, "explanation": "Go فيها for فقط، وتعمل كـ while وكحلقة لا نهائية أيضًا."}
```

```quiz
{"question": "هل تحتاج حالات switch في Go إلى break؟", "choices": ["نعم دائمًا", "لا، كل حالة تنتهي تلقائيًا", "فقط مع النصوص", "فقط في default"], "answer": 1, "explanation": "Go تخرج من switch بعد الحالة المطابقة تلقائيًا."}
```

```quiz
{"question": "ماذا يعطي `for i, v := range s`؟", "choices": ["القيمة فقط", "الفهرس والقيمة", "الطول", "آخر عنصر"], "answer": 1, "explanation": "range تعطي الفهرس ثم القيمة لكل عنصر."}
```

## الخلاصة

- `if` بلا أقواس حول الشرط، و`{ }` إجبارية، ويمكن تعريف متغير داخلها.
- `switch` بلا `break`، وتقبل عدة قيم وشروطًا.
- `for` هي الحلقة الوحيدة: كلاسيكية، أو كـ while، أو لا نهائية.
- `range` للمرور على المجموعات.
