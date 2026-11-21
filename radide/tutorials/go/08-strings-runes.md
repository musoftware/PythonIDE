# الدرس 8: النصوص والعربية والـ runes

هذا الدرس مهم جدًا لنا كعرب! Go تحفظ النصوص بترميز **UTF-8**، وفيه الحرف الإنجليزي بايت واحد، بينما الحرف العربي **بايتان**. فإذا لم ننتبه، ستعطينا بعض العمليات نتائج غريبة مع العربية.

## البايت والـ rune

- **البايت** (`byte`): وحدة تخزين صغيرة.
- **الـ rune**: حرف يونيكود كامل، مثل `'A'` أو `'م'` أو حتى رمز تعبيري.

> **تشبيه:** النص مثل **قطار بضائع**. الحرف الإنجليزي صندوق صغير يأخذ عربة واحدة، والحرف العربي صندوق كبير يأخذ عربتين. `len` تعدّ **العربات** (البايتات)، أما إن أردت عدد **الصناديق** (الحروف) فاعدّ الـ runes.

```go run
package main

import (
    "fmt"
    "unicode/utf8"
)

func main() {
    en := "Salam"
    ar := "سلام"
    fmt.Println(len(en), len(ar))                                   // بايتات
    fmt.Println(utf8.RuneCountInString(en), utf8.RuneCountInString(ar)) // حروف
    fmt.Println(len([]rune(ar)))                                      // طريقة أخرى
}
```

```text output
5 8
5 4
4
```

## المرور على حروف نص عربي

`for ... range` على النص تمر على **الحروف** (runes) لا البايتات، وهذا ما نريده غالبًا:

```go run
package main

import "fmt"

func main() {
    word := "مصر"
    for i, ch := range word {
        fmt.Printf("البايت %d: %c\n", i, ch)
    }
    fmt.Println(word[0:2])   // أول بايتين = أول حرف عربي
}
```

```text output
البايت 0: م
البايت 2: ص
البايت 4: ر
م
```

لاحظ أن الفهرس يقفز 2 في كل مرة، لأن كل حرف عربي بايتان. و`%c` يطبع الـ rune كحرف.

> **تحذير:** `word[0]` تعطيك **بايتًا** واحدًا، وليس الحرف `م`! لأخذ حرف بفهرسه حوّل النص أولًا: `[]rune(word)[0]`.

## عكس نص عربي بشكل صحيح

```go run
package main

import "fmt"

func reverse(s string) string {
    r := []rune(s)
    for i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {
        r[i], r[j] = r[j], r[i]
    }
    return string(r)
}

func main() {
    fmt.Println(reverse("Hello"))
    fmt.Println(reverse("قمر"))
}
```

```text output
olleH
رمق
```

لو عكسنا **البايتات** بدل الـ runes لتحطمت الحروف العربية وظهرت رموزًا غريبة.

## الحزمة `strings`

```go run
package main

import (
    "fmt"
    "strings"
)

func main() {
    s := "  Go is fun, Go is fast  "
    t := strings.TrimSpace(s)
    fmt.Printf("[%s]\n", t)
    fmt.Println(strings.ToUpper(t))
    fmt.Println(strings.Contains(t, "fun"))
    fmt.Println(strings.Count(t, "Go"))
    fmt.Println(strings.Index(t, "fast"))
    fmt.Println(strings.Replace(t, "Go", "Rust", 1))
    fmt.Println(strings.ReplaceAll(t, "Go", "C"))
    parts := strings.Split("أحمد,منى,علي", ",")
    fmt.Println(len(parts), parts[1])
    fmt.Println(strings.Join(parts, " - "))
    fmt.Println(strings.HasPrefix(t, "Go"), strings.HasSuffix(t, "slow"))
    fmt.Println(strings.Repeat("=", 10))
}
```

```text output
[Go is fun, Go is fast]
GO IS FUN, GO IS FAST
true
2
17
Rust is fun, Go is fast
C is fun, C is fast
3 منى
أحمد - منى - علي
true false
==========
```

## بناء النصوص بكفاءة: `strings.Builder`

جمع النصوص بـ `+` داخل حلقة كبيرة بطيء، لأن كل `+` ينشئ نصًا جديدًا. `strings.Builder` أسرع:

```go run
package main

import (
    "fmt"
    "strings"
)

func main() {
    var b strings.Builder
    for i := 1; i <= 5; i++ {
        fmt.Fprintf(&b, "%d", i)
        if i < 5 {
            b.WriteString(", ")
        }
    }
    fmt.Println(b.String())
}
```

```text output
1, 2, 3, 4, 5
```

## النصوص غير قابلة للتعديل

لا يمكنك تغيير حرف داخل نص مباشرة: `s[0] = 'X'` خطأ ترجمة. لتعديله حوّله إلى `[]rune` أو `[]byte`، عدّل، ثم أعده نصًا:

```go run
package main

import "fmt"

func main() {
    s := "كتاب"
    r := []rune(s)
    r[0] = 'ح'
    fmt.Println(string(r))
}
```

```text output
حتاب
```

## الحزمة `unicode`: فحص الحروف

```go run
package main

import (
    "fmt"
    "unicode"
)

func main() {
    text := "Go 1.22 لغة رائعة!"
    letters, digits, arabic := 0, 0, 0
    for _, ch := range text {
        if unicode.IsLetter(ch) {
            letters++
        }
        if unicode.IsDigit(ch) {
            digits++
        }
        if unicode.Is(unicode.Arabic, ch) {
            arabic++
        }
    }
    fmt.Println("حروف:", letters, "أرقام:", digits, "عربية:", arabic)
}
```

```text output
حروف: 10 أرقام: 3 عربية: 8
```

## أخطاء شائعة

- **استخدام `len` لعدد الحروف العربية:** يعطي ضعف العدد. استخدم `utf8.RuneCountInString`.
- **قص نص عربي بفهارس بايت عشوائية:** `s[0:3]` قد يقطع حرفًا في المنتصف.
- **الخلط بين `'a'` و`"a"`:** الأولى rune (رقم)، والثانية نص.

## تمارين

### التمرين 1

اكتب دالة `countVowels` تعد حروف العلة الإنجليزية (`a e i o u`) في نص:

```go exercise
package main

import (
    "fmt"
    "strings"
)

func countVowels(s string) int {
    // استخدم strings.ToLower و strings.ContainsRune
    return 0
}

func main() {
    fmt.Println(countVowels("Programming In Go"))
    _ = strings.ToLower
}
```

```go solution
package main

import (
    "fmt"
    "strings"
)

func countVowels(s string) int {
    count := 0
    for _, ch := range strings.ToLower(s) {
        if strings.ContainsRune("aeiou", ch) {
            count++
        }
    }
    return count
}

func main() {
    fmt.Println(countVowels("Programming In Go"))
}
```

```text output
5
```

### التمرين 2

اكتب دالة `isPalindrome` تعرف إن كانت الكلمة تُقرأ من الجهتين بنفس الشكل، وتعمل مع العربية:

```go exercise
package main

import "fmt"

func isPalindrome(s string) bool {
    // حوّل إلى []rune وقارن الطرفين
    return false
}

func main() {
    fmt.Println(isPalindrome("level"), isPalindrome("باب"), isPalindrome("قلم"))
}
```

```go solution
package main

import "fmt"

func isPalindrome(s string) bool {
    r := []rune(s)
    for i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {
        if r[i] != r[j] {
            return false
        }
    }
    return true
}

func main() {
    fmt.Println(isPalindrome("level"), isPalindrome("باب"), isPalindrome("قلم"))
}
```

```text output
true true false
```

## اختبر نفسك

```quiz
{"question": "ماذا ترجع `len(\"قلم\")`؟", "choices": ["3", "6", "4", "2"], "answer": 1, "explanation": "len تعد البايتات، وكل حرف عربي بايتان: 6."}
```

```quiz
{"question": "على ماذا تمر `for _, ch := range s`؟", "choices": ["البايتات", "الحروف (runes)", "الكلمات", "الأسطر"], "answer": 1, "explanation": "range على النص تفك ترميز UTF-8 وتعطي rune لكل حرف."}
```

```quiz
{"question": "كيف تغير حرفًا داخل نص؟", "choices": ["s[0] = 'x'", "تحوله إلى []rune وتعدل ثم string(...)", "strings.Set", "غير ممكن أبدًا"], "answer": 1, "explanation": "النصوص ثابتة، فنعدل نسخة []rune ثم نعيدها نصًا."}
```

## الخلاصة

- النصوص UTF-8: الحرف العربي بايتان.
- `len` للبايتات، و`utf8.RuneCountInString` للحروف.
- `range` على النص تعطي runes، و`[]rune(s)` للفهرسة بالحرف.
- الحزم `strings` و`unicode` و`strings.Builder` أدواتك اليومية.
