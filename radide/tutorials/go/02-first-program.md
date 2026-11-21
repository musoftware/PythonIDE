# الدرس 2: برنامجك الأول والحزمة `fmt`

## البرنامج كاملًا

```go run
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
```

```text output
Hello, World!
```

## الشرح سطرًا سطرًا

### `package main`

كل ملف Go ينتمي إلى **حزمة** (package). الحزمة `main` خاصة: هي التي تصنع برنامجًا تنفيذيًا. أي حزمة باسم آخر تكون **مكتبة** يستخدمها غيرها.

### `import "fmt"`

نستورد الحزمة `fmt` (اختصار format) من المكتبة القياسية، وفيها دوال الطباعة والتنسيق.

> **تشبيه:** `import` مثل استعارة كتاب من **مكتبة المدرسة**. المكتبة القياسية لـ Go غنية جدًا: نصوص، ورياضيات، وملفات، وشبكات، وغيرها.

### `func main() { ... }`

`func` تعني دالة. و`main` نقطة بداية البرنامج. ولاحظ أن القوس `{` **يجب** أن يكون في نفس سطر `func`؛ هذه قاعدة في Go وليست اختيارًا.

### `fmt.Println(...)`

`Println` تطبع ما بين القوسين ثم تنزل سطرًا. ولاحظ: **لا توجد فاصلة منقوطة** في آخر السطر! المترجم يضعها بنفسه.

## ثلاث دوال للطباعة

```go run
package main

import "fmt"

func main() {
    fmt.Println("العمر:", 20, "سنة")   // يضع مسافة بين القيم ويختم بسطر جديد
    fmt.Print("بدون ", "سطر جديد")     // لا يضيف سطرًا جديدًا
    fmt.Print("\n")
    fmt.Printf("الاسم: %s، العمر: %d\n", "سارة", 20)
    fmt.Printf("السعر: %.2f\n", 12.5)
    fmt.Printf("قيمة أي شيء: %v و %v\n", true, []int{1, 2, 3})
}
```

```text output
العمر: 20 سنة
بدون سطر جديد
الاسم: سارة، العمر: 20
السعر: 12.50
قيمة أي شيء: true و [1 2 3]
```

| المحدد | يطبع |
|---|---|
| `%d` | عدد صحيح |
| `%f` / `%.2f` | عدد عشري / بخانتين |
| `%s` | نص |
| `%v` | **أي قيمة** بشكلها الافتراضي (مريح جدًا) |
| `%T` | نوع القيمة |
| `%q` | نص بين علامتي تنصيص |
| `%%` | علامة `%` |

## `Sprintf`: بناء نص بدل طباعته

```go run
package main

import "fmt"

func main() {
    msg := fmt.Sprintf("%d + %d = %d", 3, 4, 3+4)
    fmt.Println(msg)
    fmt.Printf("%T %T %T\n", 5, 2.5, "hi")
}
```

```text output
3 + 4 = 7
int float64 string
```

## التعليقات

```go run
package main

import "fmt"

// main نقطة بداية البرنامج (تعليق من سطر واحد)
func main() {
    /* تعليق
       من عدة أسطر */
    fmt.Println("التعليقات لا تظهر")
}
```

```text output
التعليقات لا تظهر
```

> **عادة في Go:** التعليق فوق الدالة يبدأ باسمها، مثل `// main نقطة بداية البرنامج`. أدوات التوثيق تستخدمه تلقائيًا.

## Go صارمة (وهذا جيد!)

- **استيراد حزمة لا تستخدمها خطأ ترجمة:** `"os" imported and not used`.
- **متغير معرّف ولا تستخدمه خطأ ترجمة:** `declared and not used`.
- **القوس `{` في سطر جديد خطأ:** `syntax error: unexpected semicolon or newline before {`.

هذه الصرامة تُبقي الكود نظيفًا. والـ IDE تنسق الكود بأسلوب Go الرسمي من **Format Document** (تنسيق المستند).

## تمارين

### التمرين 1

اطبع بطاقة منتج باستخدام `Printf`:

```go exercise
package main

import "fmt"

func main() {
    name := "قلم"
    price := 7.5
    qty := 4
    // المنتج: قلم
    // السعر: 7.50
    // الكمية: 4
    // الإجمالي: 30.00
    _, _, _ = name, price, qty
}
```

```go solution
package main

import "fmt"

func main() {
    name := "قلم"
    price := 7.5
    qty := 4
    fmt.Printf("المنتج: %s\n", name)
    fmt.Printf("السعر: %.2f\n", price)
    fmt.Printf("الكمية: %d\n", qty)
    fmt.Printf("الإجمالي: %.2f\n", price*float64(qty))
}
```

```text output
المنتج: قلم
السعر: 7.50
الكمية: 4
الإجمالي: 30.00
```

(السطر `_, _, _ = name, price, qty` في كود البداية موجود فقط لكي لا يشتكي المترجم من متغيرات غير مستخدمة؛ احذفه عندما تكتب حلك.)

### التمرين 2

استخدم `Sprintf` لبناء النص `Go 1.0 صدرت سنة 2012` ثم اطبعه:

```go exercise
package main

import "fmt"

func main() {
    version := 1.0
    year := 2012
    text := "" // استخدم fmt.Sprintf
    fmt.Println(text)
    _, _ = version, year
}
```

```go solution
package main

import "fmt"

func main() {
    version := 1.0
    year := 2012
    text := fmt.Sprintf("Go %.1f صدرت سنة %d", version, year)
    fmt.Println(text)
}
```

```text output
Go 1.0 صدرت سنة 2012
```

## اختبر نفسك

```quiz
{"question": "ما المحدد الذي يطبع أي قيمة بشكلها الافتراضي؟", "choices": ["%d", "%s", "%v", "%q"], "answer": 2, "explanation": "%v (value) يطبع أي نوع."}
```

```quiz
{"question": "ماذا يحدث إذا استوردت حزمة ولم تستخدمها؟", "choices": ["تحذير فقط", "خطأ ترجمة", "لا شيء", "يبطؤ البرنامج"], "answer": 1, "explanation": "Go تعتبر الاستيراد غير المستخدم خطأ ترجمة."}
```

```quiz
{"question": "ما الفرق بين Println وPrint؟", "choices": ["لا فرق", "Println تضيف سطرًا جديدًا ومسافات بين القيم", "Print أسرع", "Print للأرقام فقط"], "answer": 1, "explanation": "Println تفصل القيم بمسافات وتختم بسطر جديد."}
```

## الخلاصة

- `package main` و`func main()` نقطة البداية، و`import` لاستيراد الحزم.
- `Println` و`Print` و`Printf`، و`Sprintf` لبناء النصوص.
- `%v` يطبع أي شيء، و`%T` يطبع النوع.
- لا فواصل منقوطة، و`{` في نفس السطر، ولا متغيرات أو حزم غير مستخدمة.
