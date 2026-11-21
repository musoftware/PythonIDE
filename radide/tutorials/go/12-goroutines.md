# الدرس 12: التزامن: goroutines والقنوات

هذه هي الميزة التي اشتهرت بها Go: تشغيل **مهام كثيرة في نفس الوقت** بسهولة شديدة. تحميل عشرة ملفات معًا، أو خدمة آلاف المستخدمين على خادم واحد.

## الـ goroutine

يكفي أن تكتب `go` قبل استدعاء دالة لتعمل **في الخلفية** بالتوازي مع باقي البرنامج:

> **تشبيه:** المطبخ فيه **طاهٍ رئيسي** (`main`). عندما يقول «go اسلق البيض» يكلّف مساعدًا (goroutine) بالمهمة، ويكمل هو تقطيع الخضار دون انتظار. والمساعدون في Go رخيصون جدًا: يمكنك توظيف آلاف منهم!

```go run
package main

import (
    "fmt"
    "sync"
)

func work(id int, wg *sync.WaitGroup) {
    defer wg.Done()                    // أخبر المجموعة أنني انتهيت
    fmt.Println("المهمة", id, "انتهت")
}

func main() {
    var wg sync.WaitGroup
    wg.Add(1)                          // سننتظر مهمة واحدة
    go work(1, &wg)
    wg.Wait()                          // انتظر حتى تنتهي كل المهام
    fmt.Println("كل المهام انتهت")
}
```

```text output
المهمة 1 انتهت
كل المهام انتهت
```

- `sync.WaitGroup` عدّاد: `Add` يزيده، و`Done` ينقصه، و`Wait` ينتظر حتى يصل للصفر.
- لو لم ننتظر، قد ينتهي `main` (وينتهي البرنامج كله) قبل أن تعمل الـ goroutine!

## ترتيب التنفيذ غير مضمون

عند تشغيل عدة goroutines معًا لا نعرف أيها ينتهي أولًا. لذلك إن أردنا نتيجة مرتبة، نجعل كل مهمة تكتب في **خانتها الخاصة**:

```go run
package main

import (
    "fmt"
    "sync"
)

func square(n int) int { return n * n }

func main() {
    nums := []int{1, 2, 3, 4, 5}
    results := make([]int, len(nums))
    var wg sync.WaitGroup
    for i, n := range nums {
        wg.Add(1)
        go func() {
            defer wg.Done()
            results[i] = square(n)     // كل goroutine تكتب في خانة مختلفة
        }()
    }
    wg.Wait()
    fmt.Println(results)
}
```

```text output
[1 4 9 16 25]
```

## القنوات (channels): التواصل بين المهام

القناة **أنبوب** ترسل فيه goroutine قيمة، وتستقبلها أخرى:

```go run
package main

import "fmt"

func sum(nums []int, out chan int) {
    total := 0
    for _, n := range nums {
        total += n
    }
    out <- total                        // أرسل في القناة
}

func main() {
    data := []int{1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
    ch := make(chan int)
    go sum(data[:5], ch)                // النصف الأول
    go sum(data[5:], ch)                // النصف الثاني
    a, b := <-ch, <-ch                  // استقبل نتيجتين
    fmt.Println("المجموع الكلي:", a+b)
}
```

```text output
المجموع الكلي: 55
```

- `make(chan int)` تنشئ قناة تحمل أعدادًا صحيحة.
- `ch <- v` ترسل، و`v := <-ch` تستقبل.
- الاستقبال **ينتظر** حتى تصل قيمة، فلا نحتاج WaitGroup هنا.

> **مثل Go الشهير:** «لا تتواصلوا بمشاركة الذاكرة، بل شاركوا الذاكرة بالتواصل». أي: بدل أن تقرأ المهام وتكتب نفس المتغير، دعها ترسل القيم عبر القنوات.

## المنتج والمستهلك مع `range` و`close`

```go run
package main

import "fmt"

func produce(n int, out chan<- int) {
    for i := 1; i <= n; i++ {
        out <- i * 10
    }
    close(out)                          // لا مزيد من القيم
}

func main() {
    ch := make(chan int, 3)             // قناة بذاكرة مؤقتة تسع 3 قيم
    go produce(5, ch)
    for v := range ch {                 // تتوقف عند إغلاق القناة
        fmt.Println("استلمت", v)
    }
}
```

```text output
استلمت 10
استلمت 20
استلمت 30
استلمت 40
استلمت 50
```

`chan<- int` تعني قناة للإرسال فقط داخل الدالة، وهذا يوضح النية ويمنع الأخطاء.

## مجمع العمال (Worker Pool)

نمط مشهور جدًا: عدد ثابت من العمال يسحبون المهام من قناة:

```go run
package main

import (
    "fmt"
    "sort"
    "sync"
)

func worker(jobs <-chan int, results chan<- string, wg *sync.WaitGroup) {
    defer wg.Done()
    for n := range jobs {
        results <- fmt.Sprintf("%d^2 = %d", n, n*n)
    }
}

func main() {
    jobs := make(chan int, 10)
    results := make(chan string, 10)
    var wg sync.WaitGroup
    for w := 0; w < 3; w++ {            // 3 عمال
        wg.Add(1)
        go worker(jobs, results, &wg)
    }
    for n := 1; n <= 6; n++ {
        jobs <- n
    }
    close(jobs)
    wg.Wait()
    close(results)

    var out []string
    for r := range results {
        out = append(out, r)
    }
    sort.Strings(out)                   // الترتيب لا يهمنا أثناء العمل
    for _, r := range out {
        fmt.Println(r)
    }
}
```

```text output
1^2 = 1
2^2 = 4
3^2 = 9
4^2 = 16
5^2 = 25
6^2 = 36
```

## حماية متغير مشترك: `sync.Mutex`

إن احتاجت عدة goroutines تعديل نفس المتغير، فاستخدم **قفلًا** (mutex) حتى لا تتصادم:

```go run
package main

import (
    "fmt"
    "sync"
)

type Counter struct {
    mu sync.Mutex
    n  int
}

func (c *Counter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.n++
}

func main() {
    var c Counter
    var wg sync.WaitGroup
    for i := 0; i < 1000; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            c.Inc()
        }()
    }
    wg.Wait()
    fmt.Println("العدد:", c.n)
}
```

```text output
العدد: 1000
```

بدون القفل قد يطبع رقمًا أقل من 1000، لأن عمليتي `n++` في نفس اللحظة قد تضيع إحداهما. هذا اسمه **سباق البيانات** (data race).

## أخطاء شائعة

- **انتهاء `main` قبل المهام:** استخدم `WaitGroup` أو قناة للانتظار.
- **الطريق المسدود (deadlock):** استقبال من قناة لن يرسل فيها أحد. Go تكتشفه وتطبع `all goroutines are asleep - deadlock!`.
- **الإرسال في قناة مغلقة:** يسبب `panic`.
- **تعديل متغير مشترك بلا قفل.**

## تمارين

### التمرين 1

احسب مربعات الأعداد من 1 إلى 4 في goroutines، وأرسل كل نتيجة في قناة، ثم اجمعها في `main`:

```go exercise
package main

import "fmt"

func main() {
    ch := make(chan int)
    for i := 1; i <= 4; i++ {
        // شغّل goroutine ترسل i*i في ch
    }
    total := 0
    // استقبل 4 قيم واجمعها
    fmt.Println("المجموع =", total)
    _ = ch
}
```

```go solution
package main

import "fmt"

func main() {
    ch := make(chan int)
    for i := 1; i <= 4; i++ {
        go func(n int) {
            ch <- n * n
        }(i)
    }
    total := 0
    for i := 0; i < 4; i++ {
        total += <-ch
    }
    fmt.Println("المجموع =", total)
}
```

```text output
المجموع = 30
```

### التمرين 2

اكتب دالة `countdown` ترسل الأعداد 3 ثم 2 ثم 1 في قناة وتغلقها، واطبعها في `main` بـ `range`:

```go exercise
package main

import "fmt"

func countdown(out chan<- int) {
    // أرسل 3 2 1 ثم close
}

func main() {
    ch := make(chan int)
    go countdown(ch)
    // for v := range ch { ... }
    fmt.Println("انطلق!")
}
```

```go solution
package main

import "fmt"

func countdown(out chan<- int) {
    for i := 3; i >= 1; i-- {
        out <- i
    }
    close(out)
}

func main() {
    ch := make(chan int)
    go countdown(ch)
    for v := range ch {
        fmt.Println(v)
    }
    fmt.Println("انطلق!")
}
```

```text output
3
2
1
انطلق!
```

## اختبر نفسك

```quiz
{"question": "ماذا تفعل الكلمة go قبل استدعاء دالة؟", "choices": ["تترجم الدالة", "تشغل الدالة في goroutine بالتوازي", "تؤجلها لنهاية main", "تكررها"], "answer": 1, "explanation": "go f() تبدأ f في goroutine جديدة ويكمل البرنامج دون انتظار."}
```

```quiz
{"question": "ماذا يحدث عند `v := <-ch` ولا توجد قيمة بعد؟", "choices": ["ترجع 0 فورًا", "تنتظر حتى تُرسل قيمة", "خطأ ترجمة", "تنهي البرنامج"], "answer": 1, "explanation": "الاستقبال ينتظر وصول قيمة (أو إغلاق القناة)."}
```

```quiz
{"question": "لماذا نستخدم sync.Mutex؟", "choices": ["لتسريع البرنامج", "لمنع عدة goroutines من تعديل نفس المتغير في نفس اللحظة", "لإنشاء القنوات", "للطباعة"], "answer": 1, "explanation": "القفل يمنع سباق البيانات على المتغيرات المشتركة."}
```

## الخلاصة

- `go f()` تشغل f بالتوازي، و`sync.WaitGroup` ينتظر انتهاء المهام.
- القنوات `chan T` للتواصل: `ch <- v` و`<-ch`، و`close` مع `range`.
- مجمع العمال نمط شائع لتوزيع المهام.
- `sync.Mutex` لحماية المتغيرات المشتركة.
