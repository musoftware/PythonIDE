# الدرس 4: قراءة المدخلات وتحويل النصوص إلى أرقام

البرنامج المفيد يتفاعل مع المستخدم. في Go أفضل طريقة لقراءة ما يكتبه المستخدم هي **قراءة سطر كامل كنص**، ثم تحويله إلى ما نحتاج.

## قراءة سطر: `bufio.Scanner`

```go run
package main

import (
    "bufio"
    "fmt"
    "os"
)

func main() {
    in := bufio.NewScanner(os.Stdin)
    fmt.Print("ما اسمك؟ ")
    in.Scan()                 // اقرأ سطرًا
    name := in.Text()         // النص بدون سطر النهاية
    fmt.Println()
    fmt.Println("أهلًا يا", name)
}
```

```text input
نور الهدى
```

```text output
ما اسمك؟ 
أهلًا يا نور الهدى
```

- `import ( ... )` بين قوسين لاستيراد عدة حزم.
- `os.Stdin` هي لوحة المفاتيح (الإدخال القياسي).
- `in.Scan()` تقرأ السطر التالي، و`in.Text()` تعطيك نصه.

> **كيف تجرب برنامجًا يقرأ مدخلات؟** زر «جرّبه» يرسل إلى البرنامج القيم المكتوبة في مربع «المدخلات» تحت الكود. وفي مشروعك الخاص اكتب المدخلات في نافذة **Output** عندما ينتظرها البرنامج.

## تحويل النص إلى رقم: `strconv`

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
    in := bufio.NewScanner(os.Stdin)
    fmt.Print("كم عمرك؟ ")
    in.Scan()
    age, err := strconv.Atoi(strings.TrimSpace(in.Text()))
    fmt.Println()
    if err != nil {
        fmt.Println("هذا ليس رقمًا صحيحًا!")
        return
    }
    fmt.Println("بعد 10 سنوات سيكون عمرك", age+10)
}
```

```text input
25
```

```text output
كم عمرك؟ 
بعد 10 سنوات سيكون عمرك 35
```

هنا ترى أسلوبًا مهمًا جدًا في Go: الدالة `strconv.Atoi` ترجع **قيمتين**: الرقم، وخطأ `err`. إذا نجح التحويل يكون `err` يساوي `nil` (لا شيء). سنتعمق في هذا في درس الدوال.

| الدالة | تحوّل |
|---|---|
| `strconv.Atoi(s)` | نص إلى `int` |
| `strconv.ParseFloat(s, 64)` | نص إلى `float64` |
| `strconv.Itoa(n)` | `int` إلى نص |
| `strings.TrimSpace(s)` | تحذف المسافات من الطرفين |

## ماذا لو كتب المستخدم كلامًا؟

```go run
package main

import (
    "fmt"
    "strconv"
)

func main() {
    for _, text := range []string{"42", "3.5", "abc"} {
        n, err := strconv.Atoi(text)
        if err != nil {
            fmt.Printf("%q: خطأ\n", text)
        } else {
            fmt.Printf("%q: %d\n", text, n)
        }
    }
}
```

```text output
"42": 42
"3.5": خطأ
"abc": خطأ
```

## قراءة عدة أعداد في سطر واحد

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
    in := bufio.NewScanner(os.Stdin)
    fmt.Print("اكتب أعدادًا مفصولة بمسافات: ")
    in.Scan()
    fmt.Println()
    sum := 0.0
    for _, part := range strings.Fields(in.Text()) {   // تقسيم على المسافات
        x, err := strconv.ParseFloat(part, 64)
        if err == nil {
            sum += x
        }
    }
    fmt.Printf("المجموع = %.2f\n", sum)
}
```

```text input
10 20.5 4.5
```

```text output
اكتب أعدادًا مفصولة بمسافات: 
المجموع = 35.00
```

`strings.Fields` تقسّم النص إلى كلمات، و`for _, part := range ...` تمر على الكلمات واحدة واحدة (سنشرح `range` في الدرس القادم).

## الطريقة السريعة: `fmt.Scan`

للبرامج الصغيرة جدًا يمكن قراءة القيم مباشرة:

```go run
package main

import "fmt"

func main() {
    var a, b int
    fmt.Scan(&a, &b)
    fmt.Println("الحاصل:", a*b)
}
```

```text input
6 7
```

```text output
الحاصل: 42
```

العلامة `&` تعطي `Scan` **عنوان** المتغير لتضع فيه القيمة. لكن `fmt.Scan` تقرأ كلمة كلمة ولا تناسب النصوص التي فيها مسافات، لذلك نفضّل `bufio.Scanner` غالبًا.

## أخطاء شائعة

- **تجاهل `err`:** إن كتب المستخدم حروفًا تصبح القيمة `0` بصمت. افحص `err` دائمًا.
- **نسيان `TrimSpace`:** مسافة زائدة تجعل `Atoi` تفشل.
- **نسيان `&` مع `fmt.Scan`:** لا تتغير قيمة المتغير.

## تمارين

### التمرين 1

اقرأ عددين (كل واحد في سطر) واطبع مجموعهما:

```go exercise
package main

import (
    "bufio"
    "fmt"
    "os"
    "strconv"
)

func main() {
    in := bufio.NewScanner(os.Stdin)
    // اقرأ سطرين وحوّلهما بـ strconv.Atoi ثم اطبع: المجموع = ...
    _ = in
    _ = strconv.Itoa
    fmt.Print("")
}
```

```go solution
package main

import (
    "bufio"
    "fmt"
    "os"
    "strconv"
)

func main() {
    in := bufio.NewScanner(os.Stdin)
    in.Scan()
    a, _ := strconv.Atoi(in.Text())
    in.Scan()
    b, _ := strconv.Atoi(in.Text())
    fmt.Println("المجموع =", a+b)
}
```

```text input
15
27
```

```text output
المجموع = 42
```

### التمرين 2

اقرأ درجة حرارة مئوية (قد تكون عشرية) وحوّلها إلى فهرنهايت `F = C*9/5 + 32`:

```go exercise
package main

import (
    "bufio"
    "fmt"
    "os"
)

func main() {
    in := bufio.NewScanner(os.Stdin)
    in.Scan()
    // استخدم strconv.ParseFloat ثم اطبع بخانة عشرية واحدة: 98.6 F
    fmt.Println(in.Text())
}
```

```go solution
package main

import (
    "bufio"
    "fmt"
    "os"
    "strconv"
    "strings"
)

func main() {
    in := bufio.NewScanner(os.Stdin)
    in.Scan()
    c, err := strconv.ParseFloat(strings.TrimSpace(in.Text()), 64)
    if err != nil {
        fmt.Println("قيمة غير صحيحة")
        return
    }
    fmt.Printf("%.1f F\n", c*9/5+32)
}
```

```text input
37
```

```text output
98.6 F
```

## اختبر نفسك

```quiz
{"question": "ماذا ترجع `strconv.Atoi(\"12x\")`؟", "choices": ["12 بلا خطأ", "0 وخطأ err لا يساوي nil", "تنهي البرنامج", "\"12\""], "answer": 1, "explanation": "النص ليس عددًا صحيحًا، فتعيد 0 مع خطأ."}
```

```quiz
{"question": "أي دالة تقسم النص إلى كلمات على المسافات؟", "choices": ["strings.Split", "strings.Fields", "strconv.Atoi", "fmt.Scan"], "answer": 1, "explanation": "strings.Fields تقسم على أي مسافات وتتجاهل التكرار."}
```

```quiz
{"question": "ما معنى `err == nil`؟", "choices": ["حدث خطأ", "لا يوجد خطأ", "المتغير فارغ", "انتهى البرنامج"], "answer": 1, "explanation": "nil تعني لا شيء: لا يوجد خطأ، والعملية نجحت."}
```

## الخلاصة

- `bufio.NewScanner(os.Stdin)` ثم `Scan()` و`Text()` لقراءة سطر.
- `strconv.Atoi` و`ParseFloat` للتحويل، وكلاهما يرجع خطأ يجب فحصه.
- `strings.TrimSpace` و`strings.Fields` لتنظيف النص وتقسيمه.
- `fmt.Scan(&x)` طريقة سريعة للبرامج الصغيرة.
