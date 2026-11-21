# الدرس 10: الواجهات (interfaces)

**الواجهة** (interface) في Go تصف **سلوكًا**: مجموعة دوال يجب أن يملكها النوع. وأي نوع يملك هذه الدوال **يحقق الواجهة تلقائيًا**، بلا كلمة `implements`.

> **تشبيه:** الواجهة مثل **مقبس الكهرباء** في الحائط. المقبس لا يهتم إن كان الجهاز ثلاجة أو مروحة أو شاحنًا؛ يكفي أن يكون للجهاز **قابس** بالشكل الصحيح. كذلك الدالة التي تأخذ واجهة لا تهتم بنوع القيمة، بل بأنها تملك الدوال المطلوبة.

## أول واجهة

```go run
package main

import (
    "fmt"
    "math"
)

type Shape interface {
    Area() float64
    Name() string
}

type Circle struct{ R float64 }
type Square struct{ Side float64 }

func (c Circle) Area() float64 { return math.Pi * c.R * c.R }
func (c Circle) Name() string  { return "دائرة" }

func (s Square) Area() float64 { return s.Side * s.Side }
func (s Square) Name() string  { return "مربع" }

func describe(s Shape) {
    fmt.Printf("%s مساحتها %.2f\n", s.Name(), s.Area())
}

func main() {
    shapes := []Shape{Circle{1}, Square{3}, Circle{2}}
    total := 0.0
    for _, s := range shapes {
        describe(s)
        total += s.Area()
    }
    fmt.Printf("المجموع %.2f\n", total)
}
```

```text output
دائرة مساحتها 3.14
مربع مساحتها 9.00
دائرة مساحتها 12.57
المجموع 24.71
```

- `Circle` و`Square` لم يذكرا `Shape` أبدًا، لكن كلاهما يملك `Area()` و`Name()`، فيحققان الواجهة.
- الشريحة `[]Shape` تحمل أنواعًا مختلفة معًا، وكل عنصر يستدعي دالته هو. هذا اسمه **تعدد الأشكال** (polymorphism).

## واجهات مشهورة في المكتبة القياسية

### `fmt.Stringer`

```go
type Stringer interface {
    String() string
}
```

أي نوع له `String() string` يطبعه `fmt` بطريقته، كما رأينا في الدرس السابق.

### `error`

```go
type error interface {
    Error() string
}
```

نعم! الخطأ في Go مجرد واجهة. يمكنك إنشاء نوع خطأ خاص بك:

```go run
package main

import (
    "errors"
    "fmt"
)

type NotFoundError struct {
    Key string
}

func (e *NotFoundError) Error() string {
    return "غير موجود: " + e.Key
}

func find(db map[string]int, key string) (int, error) {
    v, ok := db[key]
    if !ok {
        return 0, &NotFoundError{Key: key}
    }
    return v, nil
}

func main() {
    db := map[string]int{"pen": 5}
    if _, err := find(db, "book"); err != nil {
        fmt.Println(err)
        var nf *NotFoundError
        if errors.As(err, &nf) {
            fmt.Println("المفتاح الناقص هو", nf.Key)
        }
    }
}
```

```text output
غير موجود: book
المفتاح الناقص هو book
```

`errors.As` تفحص إن كان الخطأ من نوع معين وتعطيك تفاصيله.

## الواجهة الفارغة `any`

`any` (واسمها القديم `interface{}`) واجهة بلا دوال، فكل الأنواع تحققها. نستخدمها لقيم من أي نوع، ثم نعرف نوعها بـ **type switch**:

```go run
package main

import "fmt"

func kind(v any) string {
    switch x := v.(type) {
    case int:
        return fmt.Sprintf("عدد صحيح: %d", x)
    case string:
        return fmt.Sprintf("نص بطول %d بايت", len(x))
    case bool:
        return "منطقي"
    case []int:
        return fmt.Sprintf("شريحة من %d أعداد", len(x))
    default:
        return fmt.Sprintf("نوع آخر: %T", x)
    }
}

func main() {
    for _, v := range []any{42, "Go", true, []int{1, 2}, 3.5} {
        fmt.Println(kind(v))
    }
}
```

```text output
عدد صحيح: 42
نص بطول 2 بايت
منطقي
شريحة من 2 أعداد
نوع آخر: float64
```

## تأكيد النوع

```go run
package main

import "fmt"

func main() {
    var v any = "مرحبًا"
    s, ok := v.(string)
    fmt.Println(s, ok)
    n, ok := v.(int)
    fmt.Println(n, ok)
}
```

```text output
مرحبًا true
0 false
```

الصيغة `v.(T)` مع `ok` آمنة؛ أما بدون `ok` فإن كان النوع خاطئًا يتوقف البرنامج (panic).

## واجهات صغيرة = تصميم جيد

مثل Go المشهور: «كلما كبرت الواجهة ضعفت الفكرة». معظم واجهات Go فيها دالة واحدة أو اثنتان، مثل `io.Reader` (دالة `Read`) و`io.Writer` (دالة `Write`). وهذا يجعل الكود مرنًا وسهل الاختبار.

## أخطاء شائعة

- **مستقبل مؤشر ثم تمرير قيمة:** إن عرّفت `func (e *T) Error()` فـ `*T` هو الذي يحقق `error`، لا `T`. لذلك أرجعنا `&NotFoundError{...}`.
- **الإفراط في `any`:** تخسر فحص الأنواع وقت الترجمة. استخدمها عند الحاجة فقط.
- **تأكيد نوع بلا `ok`** على قيمة قد تكون من نوع آخر.

## تمارين

### التمرين 1

أضف نوع `Triangle` (قاعدة `Base` وارتفاع `Height`) يحقق الواجهة `Shape`:

```go exercise
package main

import "fmt"

type Shape interface {
    Area() float64
    Name() string
}

// عرّف Triangle ودالتيه

func main() {
    var s Shape
    // s = Triangle{Base: 10, Height: 4}
    if s != nil {
        fmt.Printf("%s: %.1f\n", s.Name(), s.Area())
    }
}
```

```go solution
package main

import "fmt"

type Shape interface {
    Area() float64
    Name() string
}

type Triangle struct {
    Base, Height float64
}

func (t Triangle) Area() float64 { return t.Base * t.Height / 2 }
func (t Triangle) Name() string  { return "مثلث" }

func main() {
    var s Shape
    s = Triangle{Base: 10, Height: 4}
    if s != nil {
        fmt.Printf("%s: %.1f\n", s.Name(), s.Area())
    }
}
```

```text output
مثلث: 20.0
```

### التمرين 2

اكتب واجهة `Speaker` بدالة `Speak() string`، ونوعين `Cat` و`Dog`، ثم اطبع صوت كل حيوان في الشريحة:

```go exercise
package main

import "fmt"

// Speaker و Cat و Dog

func main() {
    // animals := []Speaker{Cat{}, Dog{}, Cat{}}
    fmt.Print("")
}
```

```go solution
package main

import "fmt"

type Speaker interface {
    Speak() string
}

type Cat struct{}
type Dog struct{}

func (Cat) Speak() string { return "مياو" }
func (Dog) Speak() string { return "هاو" }

func main() {
    animals := []Speaker{Cat{}, Dog{}, Cat{}}
    for _, a := range animals {
        fmt.Println(a.Speak())
    }
}
```

```text output
مياو
هاو
مياو
```

## اختبر نفسك

```quiz
{"question": "متى يحقق نوع ما واجهة في Go؟", "choices": ["عندما نكتب implements", "تلقائيًا عندما يملك كل دوالها", "عندما يرث منها", "لا يمكن"], "answer": 1, "explanation": "التحقيق ضمني: يكفي امتلاك الدوال المطلوبة."}
```

```quiz
{"question": "ما الواجهة التي يحققها أي نوع له `Error() string`؟", "choices": ["Stringer", "error", "any فقط", "Reader"], "answer": 1, "explanation": "error واجهة بدالة واحدة Error() string."}
```

```quiz
{"question": "ماذا يفعل `switch x := v.(type)`؟", "choices": ["يحول v إلى نص", "يختار حالة حسب النوع الفعلي للقيمة", "يقارن القيم", "يطبع النوع"], "answer": 1, "explanation": "type switch يفحص النوع الحقيقي المخزن في الواجهة."}
```

## الخلاصة

- الواجهة مجموعة دوال، وتحقيقها تلقائي.
- `[]Shape` تحمل أنواعًا مختلفة: تعدد الأشكال.
- `error` و`fmt.Stringer` واجهات صغيرة مشهورة.
- `any` لأي نوع، مع type switch وتأكيد النوع `v.(T)`.
