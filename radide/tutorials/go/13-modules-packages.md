# الدرس 13: الوحدات `go.mod` والحزم والمكتبات الخارجية

كلما كبر البرنامج احتجنا تقسيمه إلى **حزم** (packages)، واستخدام مكتبات كتبها آخرون. في هذا الدرس نفهم الملف `go.mod`، وننشئ حزمة خاصة بنا، ونضيف مكتبة من الإنترنت.

## الوحدة (module) والملف `go.mod`

**الوحدة** هي المشروع كله: مجموعة حزم لها اسم وإصدار. يعرّفها ملف `go.mod` في جذر المجلد:

```text
module lesson

go 1.22
```

- `module lesson`: اسم الوحدة. الحزم الداخلية تُستورد بأسماء تبدأ به، مثل `lesson/mathx`.
- `go 1.22`: إصدار اللغة الذي يستخدمه المشروع.

> **في الـ IDE:** عند أول تشغيل لمشروع Go تنشئ الـ IDE ملف `go.mod` تلقائيًا باسم `radapp` وبإصدار Go المثبت عندك. ويمكنك تعديله بنفسك.

> **تشبيه:** الوحدة مثل **عمارة** لها عنوان (اسم الوحدة)، والحزم **شقق** داخلها. لكي تزور شقة تكتب العنوان كاملًا: «عمارة lesson، شقة mathx».

## مشروع بعدة ملفات في نفس الحزمة

كل ملفات `.go` في نفس المجلد تنتمي إلى نفس الحزمة، وترى دوال بعضها مباشرة بلا `import`:

```go run
// #file: main.go
package main

import "fmt"

func main() {
    fmt.Println(greeting("عالم"))
    fmt.Println("2 + 3 =", add(2, 3))
}
// #file: helpers.go
package main

func greeting(name string) string {
    return "مرحبًا يا " + name
}

func add(a, b int) int {
    return a + b
}
```

```text output
مرحبًا يا عالم
2 + 3 = 5
```

في الـ IDE أضف الملف من **Project ← Add Module...** (إضافة وحدة برمجية)، فيُنشأ بالسطر `package main` جاهزًا.

## حزمة خاصة بنا في مجلد فرعي

الحزمة الجديدة تعيش في **مجلد خاص بها**، واسم الحزمة عادةً هو اسم المجلد:

```go run
// #file: go.mod
module lesson

go 1.22
// #file: main.go
package main

import (
    "fmt"

    "lesson/mathx"
)

func main() {
    fmt.Println(mathx.Max(4, 9))
    fmt.Println(mathx.IsPrime(97))
    fmt.Println(mathx.Average([]float64{2, 4, 9}))
}
// #file: mathx/mathx.go
// Package mathx فيها دوال رياضية بسيطة.
package mathx

// Max ترجع أكبر العددين.
func Max(a, b int) int {
    if a > b {
        return a
    }
    return b
}

// IsPrime تعرف إن كان العدد أوليًا.
func IsPrime(n int) bool {
    if n < 2 {
        return false
    }
    for d := 2; d*d <= n; d++ {
        if n%d == 0 {
            return false
        }
    }
    return true
}

// Average متوسط شريحة أعداد.
func Average(xs []float64) float64 {
    return sum(xs) / float64(len(xs))
}

func sum(xs []float64) float64 {    // حرف صغير: خاصة بالحزمة
    t := 0.0
    for _, x := range xs {
        t += x
    }
    return t
}
```

```text output
9
true
5
```

لاحظ:

- نستورد الحزمة بالمسار الكامل `"lesson/mathx"`، ونستخدمها باسمها الأخير: `mathx.Max`.
- `Max` و`IsPrime` و`Average` تبدأ بحرف كبير، فهي **عامة**. أما `sum` فخاصة: لو كتبنا `mathx.sum` في `main` لظهر خطأ.
- التعليق فوق الدالة يبدأ باسمها؛ أدوات Go تعرضه كتوثيق، ويظهر عند وقوف الماوس على الاسم في المحرر.

## المكتبات الخارجية

آلاف المكتبات المجانية موجودة على موقع **pkg.go.dev**. لإضافة مكتبة:

**من الـ IDE:** **Project ← Manage Packages...** (إدارة الحزم)، ابحث عن المكتبة واضغط تثبيت. تنفذ الـ IDE في الخلفية الأمر `go get`.

**من الطرفية** (**View ← Terminal** = الطرفية):

```text
go get github.com/fatih/color@latest
```

فيُضاف سطر `require` إلى `go.mod`، ويُنشأ ملف `go.sum` الذي يحفظ «بصمة» كل مكتبة للتأكد من سلامتها. ثم تستوردها في الكود:

```go
import "github.com/fatih/color"

func main() {
    color.Green("نجحت العملية!")
    color.Red("حدث خطأ")
}
```

> **ملحوظة:** المكتبات الخارجية تحتاج اتصالًا بالإنترنت في أول مرة فقط؛ بعدها تُحفظ في ذاكرة Go المحلية.

أوامر مفيدة:

| الأمر | وظيفته |
|---|---|
| `go mod tidy` | يضيف المكتبات الناقصة ويحذف غير المستخدمة |
| `go get pkg@none` | يحذف مكتبة |
| `go list -m all` | يعرض كل المكتبات المستخدمة |
| `go build` | يترجم المشروع |
| `go vet` | يفحص الكود بحثًا عن أخطاء شائعة |

## الاختبارات في Go

ملف ينتهي بـ `_test.go` فيه دوال تبدأ بـ `Test`:

```go
// mathx/mathx_test.go
package mathx

import "testing"

func TestMax(t *testing.T) {
    if Max(3, 7) != 7 {
        t.Error("Max(3, 7) يجب أن تساوي 7")
    }
}
```

وتشغلها بالأمر `go test ./...` من الطرفية. وإذا فتحت مجلد وحدة Go بـ **File ← Open Folder...** (فتح مجلد) تظهر في قائمة **Native** أوامر جاهزة: `go build ./...` و`go vet ./...` و`go test ./...` و`go mod tidy`.

## أخطاء شائعة

- **مسار استيراد خاطئ:** إن كان `go.mod` يقول `module lesson` فاستورد `"lesson/mathx"` لا `"mathx"` ولا `"./mathx"`.
- **استخدام دالة بحرف صغير من حزمة أخرى:** `cannot refer to unexported name`.
- **ملفان في نفس المجلد بحزمتين مختلفتين:** كل ملفات المجلد يجب أن تكون نفس الحزمة.
- **استيراد دائري:** الحزمة A تستورد B وB تستورد A؛ Go ترفض ذلك. أعد تنظيم الكود.

## تمارين

### التمرين 1

أكمل الحزمة `text` بدالة عامة `Shout` تحول النص إلى حروف كبيرة وتضيف `!`:

```go exercise
// #file: go.mod
module lesson

go 1.22
// #file: main.go
package main

import (
    "fmt"

    "lesson/text"
)

func main() {
    fmt.Println(text.Shout("hello go"))
}
// #file: text/text.go
package text

// اكتب Shout هنا (استخدم strings.ToUpper)
```

```go solution
// #file: go.mod
module lesson

go 1.22
// #file: main.go
package main

import (
    "fmt"

    "lesson/text"
)

func main() {
    fmt.Println(text.Shout("hello go"))
}
// #file: text/text.go
package text

import "strings"

// Shout ترجع النص بحروف كبيرة مع علامة تعجب.
func Shout(s string) string {
    return strings.ToUpper(s) + "!"
}
```

```text output
HELLO GO!
```

## اختبر نفسك

```quiz
{"question": "ما وظيفة الملف go.mod؟", "choices": ["تخزين كود البرنامج", "تعريف الوحدة واسمها وإصدار Go والمكتبات المطلوبة", "حفظ الإعدادات الرسومية", "ملف مؤقت"], "answer": 1, "explanation": "go.mod يعرف الوحدة ومتطلباتها."}
```

```quiz
{"question": "إذا كان go.mod يقول module shop، فكيف تستورد الحزمة في المجلد cart؟", "choices": ["import \"cart\"", "import \"shop/cart\"", "import \"./cart\"", "import cart"], "answer": 1, "explanation": "المسار يبدأ باسم الوحدة: shop/cart."}
```

```quiz
{"question": "أي الأوامر ينظف go.mod من المكتبات غير المستخدمة؟", "choices": ["go build", "go mod tidy", "go run", "go fmt"], "answer": 1, "explanation": "go mod tidy يضيف الناقص ويحذف غير المستخدم."}
```

## الخلاصة

- `go.mod` يعرف الوحدة، والحزمة = مجلد.
- الاستيراد بالمسار الكامل: `"اسم_الوحدة/الحزمة"`.
- الحرف الكبير يجعل الاسم عامًا خارج الحزمة.
- المكتبات الخارجية بـ **Manage Packages** أو `go get`، والاختبارات في ملفات `_test.go`.
