# الدرس 3: المتغيرات والأنواع والثوابت

> **تشبيه:** المتغير **علبة** لها اسم ونوع. في Go يجب أن يعرف المترجم نوع كل علبة، لكنه ذكي: كثيرًا ما **يستنتج** النوع بنفسه من القيمة.

## ثلاث طرق لتعريف متغير

```go run
package main

import "fmt"

func main() {
    var age int = 25        // الطريقة الكاملة
    var city = "القاهرة"     // النوع يُستنتج (string)
    price := 19.99          // الأقصر والأكثر استخدامًا داخل الدوال (float64)

    fmt.Println(age, city, price)

    age = 26                // تغيير القيمة: = فقط
    fmt.Println("العمر الجديد:", age)
}
```

```text output
25 القاهرة 19.99
العمر الجديد: 26
```

- `:=` تعني «عرّف متغيرًا جديدًا وأعطه قيمة». تُستخدم داخل الدوال فقط.
- `=` تغيّر قيمة متغير موجود.

## القيم الصفرية (Zero Values)

على عكس C، المتغير في Go **لا يحتوي أبدًا قيمة عشوائية**. إن لم تعطه قيمة يأخذ «القيمة الصفرية» لنوعه:

```go run
package main

import "fmt"

func main() {
    var n int
    var f float64
    var s string
    var ok bool
    fmt.Printf("%d %v %q %v\n", n, f, s, ok)
}
```

```text output
0 0 "" false
```

## الأنواع الأساسية

| النوع | يخزن | مثال |
|---|---|---|
| `int` | عدد صحيح | `n := 42` |
| `float64` | عدد عشري | `x := 3.14` |
| `string` | نص | `s := "مرحبا"` |
| `bool` | `true` أو `false` | `ok := true` |
| `rune` | حرف واحد (يونيكود) | `r := 'م'` |
| `byte` | بايت واحد | `b := byte(65)` |

وهناك أحجام محددة مثل `int8` و`int64` و`uint` و`float32` عند الحاجة.

## التحويل بين الأنواع

Go **لا تحوّل تلقائيًا** بين الأنواع أبدًا. يجب أن تكتب التحويل بنفسك:

```go run
package main

import "fmt"

func main() {
    total := 17
    count := 5
    fmt.Println(total / count)                    // قسمة صحيحة
    fmt.Println(float64(total) / float64(count))  // تحويل صريح
    x := 9.99
    fmt.Println(int(x))                           // يحذف الكسر
}
```

```text output
3
3.4
9
```

الكتابة `total / 2.5` مع `total` من نوع `int` خطأ ترجمة: `mismatched types`. هذه الصرامة تمنع أخطاء خفية كثيرة.

## تعريف عدة متغيرات

```go run
package main

import "fmt"

func main() {
    a, b := 3, 7
    a, b = b, a            // تبديل في سطر واحد!
    fmt.Println(a, b)

    var (
        name  = "Go"
        year  = 2009
        fast  = true
    )
    fmt.Println(name, year, fast)
}
```

```text output
7 3
Go 2009 true
```

## الثوابت `const`

```go run
package main

import "fmt"

const Pi = 3.14159
const TaxRate = 0.14

const (
    Small = iota   // 0
    Medium         // 1
    Large          // 2
)

func main() {
    r := 2.0
    fmt.Printf("المساحة: %.2f\n", Pi*r*r)
    fmt.Printf("الضريبة على 200: %.2f\n", 200*TaxRate)
    fmt.Println(Small, Medium, Large)
}
```

```text output
المساحة: 12.57
الضريبة على 200: 28.00
0 1 2
```

`iota` عدّاد يبدأ من 0 ويزيد مع كل سطر داخل `const ( ... )`، مفيد لترقيم الخيارات.

## المتغير الفارغ `_`

إذا أعطتك دالة قيمتين وتريد واحدة فقط، ضع `_` مكان التي لا تريدها. (سنستخدمه كثيرًا مع الدوال لاحقًا.)

## أخطاء شائعة

- **`:=` لمتغير موجود في نفس النطاق:** `no new variables on left side of :=`. استخدم `=`.
- **متغير لا تستخدمه:** `declared and not used`. احذفه أو استخدمه.
- **خلط الأنواع:** `int + float64` غير مسموح؛ حوّل أحدهما.
- **`:=` خارج الدوال:** على مستوى الحزمة استخدم `var`.

## تمارين

### التمرين 1

احسب مساحة ومحيط مستطيل طوله `8` وعرضه `5`:

```go exercise
package main

import "fmt"

func main() {
    // المساحة = 40
    // المحيط = 26
}
```

```go solution
package main

import "fmt"

func main() {
    length, width := 8, 5
    fmt.Println("المساحة =", length*width)
    fmt.Println("المحيط =", 2*(length+width))
}
```

```text output
المساحة = 40
المحيط = 26
```

### التمرين 2

لديك `ints := 7` و`half := 0.5`. اطبع حاصل ضربهما بعد التحويل المناسب:

```go exercise
package main

import "fmt"

func main() {
    ints := 7
    half := 0.5
    // اطبع: 3.5
    _, _ = ints, half
}
```

```go solution
package main

import "fmt"

func main() {
    ints := 7
    half := 0.5
    fmt.Println(float64(ints) * half)
}
```

```text output
3.5
```

## اختبر نفسك

```quiz
{"question": "ما قيمة `var s string` إذا لم نعطه قيمة؟", "choices": ["nil", "نص فارغ \"\"", "قيمة عشوائية", "خطأ ترجمة"], "answer": 1, "explanation": "القيمة الصفرية للنص هي النص الفارغ."}
```

```quiz
{"question": "ما الفرق بين := و =؟", "choices": ["لا فرق", ":= تعرّف متغيرًا جديدًا، و= تغيّر قيمة موجود", "= للأرقام فقط", ":= للثوابت"], "answer": 1, "explanation": ":= تعريف مع إسناد، و= إسناد فقط."}
```

```quiz
{"question": "هل تسمح Go بجمع int مع float64 مباشرة؟", "choices": ["نعم دائمًا", "لا، يجب التحويل الصريح", "فقط مع الثوابت المتغيرة", "فقط في الطباعة"], "answer": 1, "explanation": "Go لا تحول الأنواع تلقائيًا؛ استخدم float64(x)."}
```

## الخلاصة

- `var` و`:=` لتعريف المتغيرات، و`=` لتغييرها.
- كل متغير له قيمة صفرية، لا قيم عشوائية.
- لا تحويل تلقائي بين الأنواع: `float64(x)` و`int(y)`.
- `const` للثوابت، و`iota` للترقيم.
