# الدرس 11: `defer` و`panic` والملفات

في هذا الدرس نتعلم كلمة سحرية في Go اسمها `defer` تضمن تنفيذ «التنظيف» دائمًا، ثم نستخدمها في التعامل مع الملفات.

## `defer`: أجّل حتى نهاية الدالة

```go run
package main

import "fmt"

func main() {
    fmt.Println("بداية")
    defer fmt.Println("هذا يُطبع في النهاية")
    defer fmt.Println("وهذا قبله")
    fmt.Println("منتصف")
}
```

```text output
بداية
منتصف
وهذا قبله
هذا يُطبع في النهاية
```

- `defer` تؤجل تنفيذ الاستدعاء حتى **قبل خروج الدالة مباشرة**، مهما كانت طريقة الخروج.
- إذا كان هناك أكثر من `defer` تُنفذ بالعكس: الأخير أولًا، مثل كومة أطباق.

> **تشبيه:** `defer` مثل ورقة تلصقها على باب الغرفة: «أطفئ النور عند الخروج». مهما خرجت من الغرفة، من الباب أو مسرعًا، ستراها وتنفذها.

## الكتابة في ملف

```go run
package main

import (
    "fmt"
    "os"
)

func main() {
    f, err := os.Create("notes.txt")      // ينشئ الملف أو يفرغه
    if err != nil {
        fmt.Println("خطأ:", err)
        return
    }
    defer f.Close()                       // سيُغلق مهما حدث

    fmt.Fprintln(f, "Ali,90")
    fmt.Fprintln(f, "Mona,85")
    fmt.Fprintf(f, "%s,%d\n", "Omar", 77)
    fmt.Println("تم الحفظ")
}
```

```text output
تم الحفظ
```

`fmt.Fprintln` و`fmt.Fprintf` مثل `Println` و`Printf`، لكنها تكتب في الملف. والملف يُحفظ في **مجلد التشغيل**، وهو مجلد المشروع عند التشغيل من الـ IDE.

## الطريقة السريعة: قراءة وكتابة ملف كامل

```go run
package main

import (
    "fmt"
    "os"
    "strings"
)

func main() {
    data := "first line\nsecond line\nthird line\n"
    if err := os.WriteFile("log.txt", []byte(data), 0644); err != nil {
        fmt.Println(err)
        return
    }
    content, err := os.ReadFile("log.txt")
    if err != nil {
        fmt.Println(err)
        return
    }
    lines := strings.Split(strings.TrimSpace(string(content)), "\n")
    for i, line := range lines {
        fmt.Printf("%d: %s\n", i+1, line)
    }
}
```

```text output
1: first line
2: second line
3: third line
```

الرقم `0644` صلاحيات الملف بأسلوب Unix (قراءة وكتابة للمالك وقراءة للباقين)، وويندوز يتجاهل معظمها.

## القراءة سطرًا سطرًا (للملفات الكبيرة)

```go run
package main

import (
    "bufio"
    "fmt"
    "os"
    "strconv"
    "strings"
)

func main() {
    os.WriteFile("scores.txt", []byte("Ali 90\nMona 85\nOmar 77\n"), 0644)

    f, err := os.Open("scores.txt")
    if err != nil {
        fmt.Println(err)
        return
    }
    defer f.Close()

    total, count := 0, 0
    sc := bufio.NewScanner(f)
    for sc.Scan() {
        fields := strings.Fields(sc.Text())
        score, _ := strconv.Atoi(fields[1])
        fmt.Println(fields[0], "=>", score)
        total += score
        count++
    }
    fmt.Printf("المتوسط: %.2f\n", float64(total)/float64(count))
}
```

```text output
Ali => 90
Mona => 85
Omar => 77
المتوسط: 84.00
```

لاحظ: نفس `bufio.Scanner` الذي قرأنا به من لوحة المفاتيح، لكن مع ملف هذه المرة. هذه قوة الواجهات: `Scanner` يقبل أي `io.Reader`.

## ملف غير موجود

```go run
package main

import (
    "errors"
    "fmt"
    "io/fs"
    "os"
)

func main() {
    _, err := os.ReadFile("no-such-file.txt")
    if errors.Is(err, fs.ErrNotExist) {
        fmt.Println("الملف غير موجود")
    }
}
```

```text output
الملف غير موجود
```

## `panic` و`recover`

`panic` توقف البرنامج فورًا عند خطأ **لا يمكن الاستمرار بعده** (خطأ برمجي). وGo نفسها تستدعيها عند الخروج عن حدود شريحة مثلًا. أما `recover` داخل `defer` فتلتقطها:

```go run
package main

import "fmt"

func safeIndex(s []int, i int) (v int, err error) {
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("فهرس غير صالح: %d", i)
        }
    }()
    return s[i], nil
}

func main() {
    s := []int{10, 20, 30}
    fmt.Println(safeIndex(s, 1))
    fmt.Println(safeIndex(s, 9))
}
```

```text output
20 <nil>
0 فهرس غير صالح: 9
```

> **قاعدة Go:** الأخطاء المتوقعة (ملف غير موجود، مدخل خاطئ) تُرجع كقيمة `error`. و`panic` فقط للأخطاء البرمجية النادرة. لا تستخدم `panic/recover` بدل `if err != nil`.

## أخطاء شائعة

- **نسيان `Close`:** استخدم `defer f.Close()` مباشرة بعد نجاح الفتح.
- **`defer` قبل فحص الخطأ:** إن فشل `os.Open` يكون `f` فارغًا. افحص `err` أولًا ثم `defer`.
- **`os.Create` على ملف مهم:** يمسح محتواه! للإلحاق استخدم `os.OpenFile(name, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)`.

## تمارين

### التمرين 1

اكتب الأعداد من 1 إلى 5 في ملف `nums.txt` بـ `os.WriteFile`، ثم اقرأه واطبع مجموع الأعداد:

```go exercise
package main

import (
    "fmt"
    "os"
)

func main() {
    // اكتب ثم اقرأ واجمع
    // اطبع: المجموع = 15
    _ = os.WriteFile
    fmt.Print("")
}
```

```go solution
package main

import (
    "fmt"
    "os"
    "strconv"
    "strings"
)

func main() {
    var b strings.Builder
    for i := 1; i <= 5; i++ {
        fmt.Fprintln(&b, i)
    }
    os.WriteFile("nums.txt", []byte(b.String()), 0644)

    data, err := os.ReadFile("nums.txt")
    if err != nil {
        fmt.Println(err)
        return
    }
    sum := 0
    for _, f := range strings.Fields(string(data)) {
        n, _ := strconv.Atoi(f)
        sum += n
    }
    fmt.Println("المجموع =", sum)
}
```

```text output
المجموع = 15
```

### التمرين 2

ما ترتيب الطباعة؟ اكتب دالة `steps` فيها `defer` بحيث يكون الناتج كما في الأسفل:

```go exercise
package main

import "fmt"

func steps() {
    // استخدم defer لتظهر "3" في النهاية
    fmt.Println("1")
    fmt.Println("2")
}

func main() {
    steps()
    fmt.Println("4")
}
```

```go solution
package main

import "fmt"

func steps() {
    defer fmt.Println("3")
    fmt.Println("1")
    fmt.Println("2")
}

func main() {
    steps()
    fmt.Println("4")
}
```

```text output
1
2
3
4
```

## اختبر نفسك

```quiz
{"question": "متى يُنفذ استدعاء مؤجل بـ defer؟", "choices": ["فورًا", "قبل خروج الدالة مباشرة", "عند نهاية البرنامج فقط", "بعد ثانية"], "answer": 1, "explanation": "defer ينفذ عند خروج الدالة المحيطة، بأي طريقة كان الخروج."}
```

```quiz
{"question": "إذا كتبنا defer A ثم defer B، أيهما يُنفذ أولًا؟", "choices": ["A", "B", "معًا", "لا شيء"], "answer": 1, "explanation": "المؤجلات تنفذ بالعكس (آخر داخل أول خارج)."}
```

```quiz
{"question": "ما الطريقة المعتادة في Go للإبلاغ عن ملف غير موجود؟", "choices": ["panic", "إرجاع قيمة error", "طباعة رسالة وإكمال", "os.Exit"], "answer": 1, "explanation": "الأخطاء المتوقعة تُرجع كقيم error، وpanic للأخطاء البرمجية."}
```

## الخلاصة

- `defer` يؤجل التنظيف إلى نهاية الدالة، وبترتيب عكسي.
- `os.Create` و`os.Open` و`defer f.Close()` للملفات، و`os.ReadFile`/`os.WriteFile` للطريقة السريعة.
- `bufio.Scanner` يقرأ الملف سطرًا سطرًا.
- `panic` للأخطاء البرمجية فقط، و`recover` يلتقطها داخل `defer`.
