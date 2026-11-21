# الدرس 7: الشرائح (slices) والخرائط (maps)

أهم مجموعتين في Go: **الشريحة** (slice) لقائمة مرتبة من العناصر، و**الخريطة** (map) لربط مفتاح بقيمة، مثل القاموس.

## المصفوفة ثابتة الحجم

```go run
package main

import "fmt"

func main() {
    var a [3]int            // مصفوفة من 3 أعداد (أصفار)
    a[0] = 10
    b := [4]string{"أ", "ب", "ج", "د"}
    fmt.Println(a, len(a))
    fmt.Println(b[2])
}
```

```text output
[10 0 0] 3
ج
```

المصفوفة في Go حجمها جزء من نوعها ولا يتغير، لذلك نادرًا ما نستخدمها مباشرة. نستخدم بدلًا منها **الشرائح**.

## الشرائح: قوائم مرنة

```go run
package main

import "fmt"

func main() {
    nums := []int{5, 3, 8}          // بلا رقم بين [] = شريحة
    nums = append(nums, 1, 9)       // أضف في الآخر
    fmt.Println(nums, "الطول:", len(nums))

    nums[0] = 50
    fmt.Println("الأول:", nums[0], "الأخير:", nums[len(nums)-1])

    part := nums[1:3]               // من الفهرس 1 حتى قبل 3
    fmt.Println(part)
    fmt.Println(nums[:2], nums[3:])
}
```

```text output
[5 3 8 1 9] الطول: 5
الأول: 50 الأخير: 9
[3 8]
[50 3] [1 9]
```

> **تشبيه:** الشريحة مثل **نافذة** تنظر منها إلى صف من الخزائن (مصفوفة مخفية). `nums[1:3]` نافذة أصغر على نفس الخزائن، فإن غيرت عنصرًا من خلالها يتغير في الأصل أيضًا!

```go run
package main

import "fmt"

func main() {
    a := []int{1, 2, 3, 4}
    b := a[1:3]
    b[0] = 99                 // يغير a أيضًا!
    fmt.Println(a)

    c := make([]int, len(a))  // نسخة مستقلة
    copy(c, a)
    c[0] = -1
    fmt.Println(a, c)
}
```

```text output
[1 99 3 4]
[1 99 3 4] [-1 99 3 4]
```

`make([]int, n)` تنشئ شريحة بطول `n` (أصفار)، و`copy` تنسخ العناصر.

## عمليات شائعة على الشرائح

```go run
package main

import (
    "fmt"
    "slices"
    "sort"
)

func main() {
    marks := []int{70, 95, 60, 88}
    sum := 0
    for _, m := range marks {
        sum += m
    }
    fmt.Printf("المتوسط %.2f\n", float64(sum)/float64(len(marks)))

    sort.Ints(marks)                       // ترتيب تصاعدي
    fmt.Println(marks)
    fmt.Println(slices.Contains(marks, 88), slices.Index(marks, 95))
    fmt.Println(slices.Max(marks))

    i := 1                                 // حذف العنصر رقم 1
    marks = append(marks[:i], marks[i+1:]...)
    fmt.Println(marks)

    names := []string{"Zaid", "Amal", "Laila"}
    sort.Strings(names)
    fmt.Println(names)
}
```

```text output
المتوسط 78.25
[60 70 88 95]
true 3
95
[60 88 95]
[Amal Laila Zaid]
```

الحزمة `slices` (منذ Go 1.21) فيها دوال جاهزة مثل `Contains` و`Index` و`Max` و`Sort`.

## الخرائط: مفتاح وقيمة

> **تشبيه:** الخريطة مثل **دليل الهاتف**: تبحث بالاسم (المفتاح) فتجد الرقم (القيمة) فورًا، بدون المرور على كل الصفحات.

```go run
package main

import "fmt"

func main() {
    ages := map[string]int{
        "علي":  30,
        "منى":  25,
    }
    ages["يوسف"] = 19            // إضافة
    ages["علي"] = 31             // تعديل
    fmt.Println(ages["منى"])
    fmt.Println("العدد:", len(ages))

    age, ok := ages["كريم"]      // هل المفتاح موجود؟
    fmt.Println(age, ok)

    delete(ages, "يوسف")
    _, ok = ages["يوسف"]
    fmt.Println("يوسف موجود؟", ok)
}
```

```text output
25
العدد: 3
0 false
يوسف موجود؟ false
```

- قراءة مفتاح غير موجود ترجع القيمة الصفرية (`0`)، لذلك نستخدم الصيغة `v, ok := m[key]` لنعرف إن كان موجودًا فعلًا.

## المرور على خريطة بترتيب ثابت

ترتيب `range` على الخريطة **عشوائي** في Go عمدًا! إن أردت ترتيبًا ثابتًا فرتّب المفاتيح أولًا:

```go run
package main

import (
    "fmt"
    "sort"
    "strings"
)

func main() {
    text := "the cat and the dog and the bird"
    counts := map[string]int{}
    for _, w := range strings.Fields(text) {
        counts[w]++
    }
    keys := make([]string, 0, len(counts))
    for k := range counts {
        keys = append(keys, k)
    }
    sort.Strings(keys)
    for _, k := range keys {
        fmt.Println(k, counts[k])
    }
}
```

```text output
and 2
bird 1
cat 1
dog 1
the 3
```

`make([]string, 0, n)` تنشئ شريحة فارغة بسعة مبدئية `n`، لتسريع `append`.

## أخطاء شائعة

- **الخروج عن الحدود:** `nums[10]` في شريحة طولها 5 يوقف البرنامج برسالة `index out of range`.
- **نسيان إسناد نتيجة `append`:** `append(nums, 4)` وحدها لا تغير `nums`؛ اكتب `nums = append(nums, 4)`.
- **الكتابة في خريطة `nil`:** `var m map[string]int` ثم `m["a"] = 1` ينهار. أنشئها بـ `map[string]int{}` أو `make`.
- **الاعتماد على ترتيب الخريطة.**

## تمارين

### التمرين 1

اكتب دالة `evens` ترجع شريحة بالأعداد الزوجية فقط:

```go exercise
package main

import "fmt"

func evens(nums []int) []int {
    result := []int{}
    // أكمل
    return result
}

func main() {
    fmt.Println(evens([]int{1, 2, 3, 4, 5, 6, 10}))
}
```

```go solution
package main

import "fmt"

func evens(nums []int) []int {
    result := []int{}
    for _, n := range nums {
        if n%2 == 0 {
            result = append(result, n)
        }
    }
    return result
}

func main() {
    fmt.Println(evens([]int{1, 2, 3, 4, 5, 6, 10}))
}
```

```text output
[2 4 6 10]
```

### التمرين 2

عُدّ تكرار كل حرف في الكلمة `banana` باستخدام خريطة، واطبع النتائج مرتبة حسب الحرف:

```go exercise
package main

import (
    "fmt"
    "sort"
)

func main() {
    word := "banana"
    counts := map[rune]int{}
    // أكمل: املأ counts ثم اطبع a 3 / b 1 / n 2
    _ = word
    _ = sort.Ints
    fmt.Print("")
    _ = counts
}
```

```go solution
package main

import (
    "fmt"
    "sort"
)

func main() {
    word := "banana"
    counts := map[rune]int{}
    for _, ch := range word {
        counts[ch]++
    }
    keys := []rune{}
    for k := range counts {
        keys = append(keys, k)
    }
    sort.Slice(keys, func(i, j int) bool { return keys[i] < keys[j] })
    for _, k := range keys {
        fmt.Println(string(k), counts[k])
    }
}
```

```text output
a 3
b 1
n 2
```

## اختبر نفسك

```quiz
{"question": "ما الفرق بين `[3]int` و`[]int`؟", "choices": ["لا فرق", "الأول مصفوفة ثابتة الحجم، والثاني شريحة مرنة", "الأول شريحة", "الثاني للنصوص"], "answer": 1, "explanation": "وجود الرقم يعني مصفوفة ثابتة، وبدونه شريحة."}
```

```quiz
{"question": "كيف نعرف إن كان مفتاح موجودًا في خريطة؟", "choices": ["m[k] != 0", "v, ok := m[k] ثم نفحص ok", "len(m[k])", "m.has(k)"], "answer": 1, "explanation": "ok تكون true فقط إن كان المفتاح موجودًا."}
```

```quiz
{"question": "ماذا يحدث لـ `a` إذا عدلنا `b := a[1:3]`؟", "choices": ["لا شيء", "يتغير a لأن b نافذة على نفس العناصر", "خطأ ترجمة", "يُحذف a"], "answer": 1, "explanation": "الشريحة الجزئية تشارك المصفوفة نفسها."}
```

## الخلاصة

- الشريحة `[]T` قائمة مرنة: `append` و`len` و`s[a:b]` و`copy`.
- الحزمتان `sort` و`slices` فيهما الترتيب والبحث.
- الخريطة `map[K]V`: إضافة، و`delete`، و`v, ok := m[k]`.
- ترتيب الخريطة عشوائي؛ رتب المفاتيح عند الحاجة.
