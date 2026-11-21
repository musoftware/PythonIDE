# الدرس 6: الدوال والقيم المتعددة والأخطاء

> **تشبيه:** الدالة **ماكينة**: تضع فيها مدخلات (المعاملات) وتأخذ منها نتيجة. وماكينات Go مميزة: يمكن أن تُخرج **أكثر من نتيجة** في نفس الوقت، مثل ماكينة صرف تعطيك النقود والإيصال معًا.

## تعريف دالة

```go run
package main

import "fmt"

func square(x int) int {
    return x * x
}

func greet(name string) {
    fmt.Println("أهلًا يا", name)
}

func add(a, b float64) float64 {   // a و b من نفس النوع
    return a + b
}

func main() {
    fmt.Println(square(7))
    greet("سلمى")
    fmt.Println(add(2.5, 4))
}
```

```text output
49
أهلًا يا سلمى
6.5
```

- النوع يأتي **بعد** اسم المعامل: `x int`.
- نوع القيمة المرجعة بعد الأقواس: `func square(x int) int`.
- ترتيب الدوال في الملف لا يهم؛ لا نحتاج نماذج أولية كما في C.

## إرجاع أكثر من قيمة

```go run
package main

import "fmt"

func divide(a, b int) (int, int) {
    return a / b, a % b
}

func minMax(nums []int) (min, max int) {   // قيم مرجعة مُسماة
    min, max = nums[0], nums[0]
    for _, n := range nums {
        if n < min {
            min = n
        }
        if n > max {
            max = n
        }
    }
    return
}

func main() {
    q, r := divide(17, 5)
    fmt.Println("الناتج", q, "والباقي", r)
    lo, hi := minMax([]int{7, 2, 9, 4})
    fmt.Println(lo, hi)
    _, onlyRest := divide(10, 3)
    fmt.Println(onlyRest)
}
```

```text output
الناتج 3 والباقي 2
2 9
1
```

## الأخطاء: قيمة عادية وليست استثناء

في Go لا توجد `try/catch`. الدالة التي قد تفشل ترجع **آخر قيمة من نوع `error`**. إذا نجحت تكون `nil`:

```go run
package main

import (
    "errors"
    "fmt"
)

func safeDivide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, errors.New("لا يمكن القسمة على صفر")
    }
    return a / b, nil
}

func main() {
    if r, err := safeDivide(10, 4); err == nil {
        fmt.Println("الناتج:", r)
    }
    r, err := safeDivide(1, 0)
    if err != nil {
        fmt.Println("خطأ:", err)
        return
    }
    fmt.Println(r)
}
```

```text output
الناتج: 2.5
خطأ: لا يمكن القسمة على صفر
```

> **تشبيه:** كأن كل ماكينة لها **لمبة حمراء** (err). بعد كل استخدام تنظر للمبة: إن كانت مطفأة (`nil`) فالنتيجة سليمة، وإن أضاءت فلا تثق في النتيجة.

هذا الأسلوب `if err != nil { ... }` ستراه في كل مكان في Go. قد يبدو كثيرًا، لكنه يجعل الأخطاء **واضحة** ولا تختبئ.

## أخطاء بتفاصيل: `fmt.Errorf`

```go run
package main

import (
    "fmt"
    "strconv"
)

func parseAge(s string) (int, error) {
    n, err := strconv.Atoi(s)
    if err != nil {
        return 0, fmt.Errorf("العمر %q ليس رقمًا", s)
    }
    if n < 0 || n > 150 {
        return 0, fmt.Errorf("العمر %d خارج المدى", n)
    }
    return n, nil
}

func main() {
    for _, s := range []string{"30", "abc", "200"} {
        age, err := parseAge(s)
        if err != nil {
            fmt.Println("خطأ:", err)
            continue
        }
        fmt.Println("عمر صحيح:", age)
    }
}
```

```text output
عمر صحيح: 30
خطأ: العمر "abc" ليس رقمًا
خطأ: العمر 200 خارج المدى
```

## الدوال قيم: الدوال المجهولة والإغلاقات

يمكن تخزين دالة في متغير، أو تمريرها لدالة أخرى:

```go run
package main

import "fmt"

func apply(nums []int, f func(int) int) []int {
    out := []int{}
    for _, n := range nums {
        out = append(out, f(n))
    }
    return out
}

func counter() func() int {
    count := 0
    return func() int {       // دالة تتذكر count (إغلاق closure)
        count++
        return count
    }
}

func main() {
    double := func(x int) int { return x * 2 }
    fmt.Println(apply([]int{1, 2, 3}, double))
    fmt.Println(apply([]int{1, 2, 3}, func(x int) int { return x * x }))

    next := counter()
    fmt.Println(next(), next(), next())
}
```

```text output
[2 4 6]
[1 4 9]
1 2 3
```

## دوال بعدد متغير من المعاملات

```go run
package main

import "fmt"

func sum(nums ...int) int {
    total := 0
    for _, n := range nums {
        total += n
    }
    return total
}

func main() {
    fmt.Println(sum())
    fmt.Println(sum(1, 2, 3))
    values := []int{10, 20, 30}
    fmt.Println(sum(values...))
}
```

```text output
0
6
60
```

## أخطاء شائعة

- **تجاهل الخطأ:** `n, _ := strconv.Atoi(s)` مقبول فقط إن كنت متأكدًا. غالبًا افحص `err`.
- **استخدام القيمة رغم وجود خطأ:** عند `err != nil` اعتبر القيمة الأخرى بلا معنى.
- **رسائل الأخطاء:** العادة في Go أن تبدأ بحرف صغير ولا تنتهي بنقطة، لأنها تُدمج في رسائل أخرى.

## تمارين

### التمرين 1

اكتب دالة `rectangle` ترجع المساحة والمحيط معًا:

```go exercise
package main

import "fmt"

func rectangle(w, h int) (int, int) {
    // أكمل
    return 0, 0
}

func main() {
    a, p := rectangle(6, 4)
    fmt.Println("المساحة", a, "المحيط", p)
}
```

```go solution
package main

import "fmt"

func rectangle(w, h int) (int, int) {
    return w * h, 2 * (w + h)
}

func main() {
    a, p := rectangle(6, 4)
    fmt.Println("المساحة", a, "المحيط", p)
}
```

```text output
المساحة 24 المحيط 20
```

### التمرين 2

اكتب دالة `sqrtInt` ترجع خطأ إن كان العدد سالبًا، وإلا ترجع أكبر عدد صحيح مربعه لا يتجاوز العدد:

```go exercise
package main

import (
    "errors"
    "fmt"
)

func sqrtInt(n int) (int, error) {
    // أكمل
    return 0, errors.New("لم يُكتب بعد")
}

func main() {
    for _, n := range []int{17, -4, 49} {
        r, err := sqrtInt(n)
        if err != nil {
            fmt.Println(n, "خطأ:", err)
        } else {
            fmt.Println(n, "=>", r)
        }
    }
}
```

```go solution
package main

import (
    "errors"
    "fmt"
)

func sqrtInt(n int) (int, error) {
    if n < 0 {
        return 0, errors.New("عدد سالب")
    }
    r := 0
    for (r+1)*(r+1) <= n {
        r++
    }
    return r, nil
}

func main() {
    for _, n := range []int{17, -4, 49} {
        r, err := sqrtInt(n)
        if err != nil {
            fmt.Println(n, "خطأ:", err)
        } else {
            fmt.Println(n, "=>", r)
        }
    }
}
```

```text output
17 => 4
-4 خطأ: عدد سالب
49 => 7
```

## اختبر نفسك

```quiz
{"question": "كيف تُبلّغ دالة في Go عن فشلها عادةً؟", "choices": ["throw exception", "ترجع قيمة error أخيرة لا تساوي nil", "تطبع رسالة فقط", "تنهي البرنامج"], "answer": 1, "explanation": "الأسلوب المعتاد: آخر قيمة مرجعة من نوع error."}
```

```quiz
{"question": "ما معنى `_` في `_, r := divide(10, 3)`؟", "choices": ["خطأ", "تجاهل القيمة الأولى", "صفر", "متغير اسمه underscore يُستخدم لاحقًا"], "answer": 1, "explanation": "المتغير الفارغ _ يتجاهل القيمة."}
```

```quiz
{"question": "ماذا تعني `func sum(nums ...int)`؟", "choices": ["تأخذ int واحدًا", "تأخذ أي عدد من قيم int", "ترجع شريحة", "خطأ ترجمة"], "answer": 1, "explanation": "... تعني عددًا متغيرًا من المعاملات، تصل كشريحة."}
```

## الخلاصة

- `func name(p type) result { ... }`، والنوع بعد الاسم.
- الدوال ترجع عدة قيم، وآخرها غالبًا `error`.
- `errors.New` و`fmt.Errorf` لإنشاء الأخطاء، و`if err != nil` لفحصها.
- الدوال قيم: تُخزن وتُمرر، والإغلاق يتذكر متغيراته.
