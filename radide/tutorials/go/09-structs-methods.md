# الدرس 9: الهياكل والدوال المرتبطة (methods)

Go لا تحتوي `class` كما في C++ وJava، لكنها تعطيك نفس القوة بطريقة أبسط: **هيكل** (struct) يجمع البيانات، و**دوال مرتبطة** (methods) تعمل عليه.

> **تشبيه:** الـ struct **استمارة** بخانات (الاسم، الرصيد...). والـ method **إجراء مكتوب على ظهر الاستمارة** يخصها هي، مثل «إيداع مبلغ» أو «طباعة الكشف».

## تعريف هيكل

```go run
package main

import "fmt"

type Student struct {
    Name  string
    Age   int
    Marks []int
}

func main() {
    s1 := Student{Name: "منى", Age: 20, Marks: []int{90, 85}}
    s2 := Student{"عمر", 22, nil}       // بالترتيب (أقل وضوحًا)
    var s3 Student                      // قيم صفرية
    s3.Name = "سارة"

    fmt.Println(s1.Name, s1.Age, s1.Marks)
    fmt.Println(s2.Name, len(s2.Marks))
    fmt.Printf("%+v\n", s3)
}
```

```text output
منى 20 [90 85]
عمر 0
{Name:سارة Age:0 Marks:[]}
```

`%+v` يطبع الهيكل مع أسماء الحقول، وهو مفيد جدًا لتتبع الأخطاء.

## الدوال المرتبطة (Methods)

```go run
package main

import "fmt"

type Rect struct {
    W, H float64
}

func (r Rect) Area() float64 {          // r هو «المستقبِل» (receiver)
    return r.W * r.H
}

func (r Rect) Perimeter() float64 {
    return 2 * (r.W + r.H)
}

func main() {
    r := Rect{W: 6, H: 4}
    fmt.Println("المساحة:", r.Area())
    fmt.Println("المحيط:", r.Perimeter())
}
```

```text output
المساحة: 24
المحيط: 20
```

`(r Rect)` قبل اسم الدالة تربطها بالنوع `Rect`، فنستدعيها بالنقطة: `r.Area()`.

## المستقبِل المؤشر: لتعديل الهيكل

إذا أردت أن تغير الدالة حقول الهيكل، اجعل المستقبِل **مؤشرًا** `*T`:

```go run
package main

import (
    "errors"
    "fmt"
)

type Account struct {
    Owner   string
    Balance float64
}

func (a *Account) Deposit(amount float64) {
    a.Balance += amount
}

func (a *Account) Withdraw(amount float64) error {
    if amount > a.Balance {
        return errors.New("الرصيد لا يكفي")
    }
    a.Balance -= amount
    return nil
}

func (a Account) String() string {
    return fmt.Sprintf("%s: %.2f", a.Owner, a.Balance)
}

func main() {
    acc := Account{Owner: "ليلى", Balance: 1000}
    acc.Deposit(500)
    if err := acc.Withdraw(5000); err != nil {
        fmt.Println("خطأ:", err)
    }
    acc.Withdraw(300)
    fmt.Println(acc)
}
```

```text output
خطأ: الرصيد لا يكفي
ليلى: 1200.00
```

- `Deposit` و`Withdraw` تعدلان الرصيد، لذلك مستقبلهما `*Account`.
- `String()` دالة خاصة: إذا كانت موجودة يستخدمها `fmt.Println` لطباعة الهيكل.
- Go تأخذ العنوان تلقائيًا: `acc.Deposit(500)` تعمل رغم أن `acc` ليس مؤشرًا.

> **قاعدة بسيطة:** إن كانت أي دالة تعدل الهيكل، اجعل كل دوال النوع بمستقبل مؤشر للتناسق.

## دالة إنشاء: `NewXxx`

لا توجد «مُنشئات» في Go، والعادة أن نكتب دالة اسمها `New...`:

```go run
package main

import "fmt"

type Counter struct {
    name  string
    value int
}

func NewCounter(name string) *Counter {
    return &Counter{name: name}
}

func (c *Counter) Inc() { c.value++ }

func main() {
    c := NewCounter("الزوار")
    c.Inc()
    c.Inc()
    fmt.Println(c.name, c.value)
}
```

```text output
الزوار 2
```

## الحروف الكبيرة = عام

في Go، الاسم الذي يبدأ **بحرف كبير** مثل `Name` أو `Deposit` يكون **عامًا** (exported) تراه الحزم الأخرى. والذي يبدأ بحرف صغير مثل `value` **خاص** بالحزمة. لا توجد كلمات `public` و`private`!

## التضمين (Embedding)

بدل الوراثة، تضع Go هيكلًا داخل هيكل، فيرث حقوله ودواله:

```go run
package main

import "fmt"

type Person struct {
    Name string
}

func (p Person) Hello() string {
    return "أنا " + p.Name
}

type Employee struct {
    Person          // تضمين
    Salary int
}

func main() {
    e := Employee{Person{"كريم"}, 9000}
    fmt.Println(e.Name)        // حقل من Person
    fmt.Println(e.Hello())     // دالة من Person
    fmt.Println(e.Salary)
}
```

```text output
كريم
أنا كريم
9000
```

## أخطاء شائعة

- **مستقبل بالقيمة في دالة تعدّل:** `func (a Account) Deposit(...)` تعدل نسخة، والأصل لا يتغير.
- **حقل بحرف صغير لا يظهر خارج الحزمة** (وأيضًا لا يُحفظ في JSON).
- **مقارنة هياكل فيها شرائح بـ `==`:** خطأ ترجمة.

## تمارين

### التمرين 1

أضف إلى `Rect` دالة `Scale(f float64)` تكبّر الطول والعرض بالمعامل `f` (تحتاج مستقبلًا مؤشرًا):

```go exercise
package main

import "fmt"

type Rect struct {
    W, H float64
}

func (r Rect) Area() float64 { return r.W * r.H }

// اكتب Scale هنا

func main() {
    r := Rect{2, 3}
    // r.Scale(2)
    fmt.Println(r.Area())
}
```

```go solution
package main

import "fmt"

type Rect struct {
    W, H float64
}

func (r Rect) Area() float64 { return r.W * r.H }

func (r *Rect) Scale(f float64) {
    r.W *= f
    r.H *= f
}

func main() {
    r := Rect{2, 3}
    r.Scale(2)
    fmt.Println(r.Area())
}
```

```text output
24
```

### التمرين 2

عرّف هيكل `Book` بحقلين `Title` و`Pages`، ودالة `String()` تطبعه بالشكل المطلوب:

```go exercise
package main

import "fmt"

// عرّف Book و String()

func main() {
    // b := Book{"Go Basics", 250}
    // fmt.Println(b)
    fmt.Println("")
}
```

```go solution
package main

import "fmt"

type Book struct {
    Title string
    Pages int
}

func (b Book) String() string {
    return fmt.Sprintf("كتاب %q (%d صفحة)", b.Title, b.Pages)
}

func main() {
    b := Book{"Go Basics", 250}
    fmt.Println(b)
}
```

```text output
كتاب "Go Basics" (250 صفحة)
```

## اختبر نفسك

```quiz
{"question": "متى نستخدم مستقبلًا مؤشرًا `func (a *Account)`؟", "choices": ["دائمًا للطباعة", "عندما تعدل الدالة حقول الهيكل", "عندما لا ترجع الدالة شيئًا", "لا يُستخدم أبدًا"], "answer": 1, "explanation": "المستقبل المؤشر يسمح بتعديل الهيكل الأصلي."}
```

```quiz
{"question": "كيف تجعل حقلًا عامًا تراه الحزم الأخرى؟", "choices": ["بكلمة public", "تبدأ اسمه بحرف كبير", "بكلمة export", "تضعه أولًا"], "answer": 1, "explanation": "الحرف الكبير في بداية الاسم يجعله exported."}
```

```quiz
{"question": "بماذا تستبدل Go الوراثة؟", "choices": ["لا يوجد بديل", "التضمين (embedding) والواجهات", "القوالب", "الماكرو"], "answer": 1, "explanation": "Go تستخدم تضمين الهياكل والواجهات بدل الوراثة."}
```

## الخلاصة

- `type X struct { ... }` لتعريف هيكل، و`X{Field: v}` لإنشائه.
- `func (r X) M()` دالة مرتبطة، و`func (r *X) M()` لتعديل الهيكل.
- `String()` يحدد شكل الطباعة، و`NewX` بدل المُنشئ.
- الحرف الكبير = عام، والتضمين بدل الوراثة.
