# الدرس 6: الدوال (Functions)

**في هذا الدرس ستتعلم:**

- كيف تكتب **دالة** وتستدعيها.
- المعاملات (parameters) والقيم الافتراضية.
- إرجاع النتيجة بـ `return`.
- **الدوال السهمية** (arrow functions).
- **النطاق** (scope): أين يعيش المتغير.
- تمرير دالة إلى دالة أخرى.

## ما هي الدالة؟

**الدالة** (function) مجموعة تعليمات لها اسم، نكتبها مرة واحدة ونستدعيها كلما احتجنا إليها.

> **تشبيه:** الدالة مثل **وصفة** في كتاب الطبخ: تكتب الوصفة مرة واحدة باسم «كيكة الشوكولاتة»، وكلما أردت كيكة تقول «نفّذ الوصفة» بدل أن تعيد كتابة الخطوات كلها. والمكونات التي تعطيها للوصفة هي **المعاملات**، والكيكة التي تخرج هي **القيمة المرجعة**.

## تعريف دالة واستدعاؤها

```js run
function greet() {
    console.log("السلام عليكم!");
    console.log("أهلًا بك في الدورة");
}

greet();
greet();
```

```text output
السلام عليكم!
أهلًا بك في الدورة
السلام عليكم!
أهلًا بك في الدورة
```

- `function greet() { ... }` **تعريف** الدالة: لا يُنفَّذ شيء عند هذا السطر.
- `greet();` **استدعاء** الدالة: الآن تُنفَّذ تعليماتها. لا تنسَ القوسين `()`.

## المعاملات

المعاملات متغيرات تستقبل قيمًا عند الاستدعاء:

```js run
function greet(name, city) {
    console.log(`أهلًا يا ${name} من ${city}`);
}

greet("سارة", "الإسكندرية");
greet("خالد", "أسوان");
greet("منى");
```

```text output
أهلًا يا سارة من الإسكندرية
أهلًا يا خالد من أسوان
أهلًا يا منى من undefined
```

في الاستدعاء الأخير لم نعطِ قيمة لـ `city` فأصبحت `undefined`. الحل: **قيمة افتراضية**:

```js run
function greet(name, city = "مصر") {
    console.log(`أهلًا يا ${name} من ${city}`);
}
greet("منى");
greet("علي", "بنها");
```

```text output
أهلًا يا منى من مصر
أهلًا يا علي من بنها
```

## إرجاع قيمة بـ `return`

أغلب الدوال تحسب شيئًا و**ترجعه** لمن استدعاها:

```js run
function area(width, height) {
    return width * height;
}

const a = area(4, 5);
console.log("المساحة:", a);
console.log("مساحتان:", area(2, 3) + area(1, 1));
```

```text output
المساحة: 20
مساحتان: 7
```

`return` تنهي الدالة فورًا. أي سطر بعدها داخل الدالة لا يُنفَّذ. ويمكن استخدامها للخروج المبكر:

```js run
function divide(a, b) {
    if (b === 0) {
        return "لا يمكن القسمة على صفر";
    }
    return a / b;
}
console.log(divide(10, 4));
console.log(divide(5, 0));
```

```text output
2.5
لا يمكن القسمة على صفر
```

> **ملحوظة:** دالة بلا `return` ترجع `undefined`.

## الدوال السهمية (Arrow Functions)

طريقة مختصرة وحديثة لكتابة الدوال، منتشرة جدًا في الكود الحديث:

```js run
const square = (x) => x * x;
const add = (a, b) => a + b;
const hello = () => "مرحبًا!";
const describe = (name, age) => {
    const kind = age >= 18 ? "بالغ" : "قاصر";
    return `${name}: ${kind}`;
};

console.log(square(9));
console.log(add(2, 3));
console.log(hello());
console.log(describe("ياسر", 16));
```

```text output
81
5
مرحبًا!
ياسر: قاصر
```

- إن كان جسم الدالة **تعبيرًا واحدًا** نكتبه بعد `=>` مباشرة فيُرجَع تلقائيًا دون `return`.
- إن كان أكثر من سطر نضع `{ }` ونكتب `return` بأنفسنا.

## النطاق (Scope)

المتغير الذي يُنشأ داخل كتلة `{ }` (دالة أو `if` أو حلقة) لا يُرى خارجها:

```js run
const appName = "حاسبتي";     // نطاق عام: يُرى في كل مكان

function show() {
    const version = 2;         // نطاق محلي: داخل الدالة فقط
    console.log(appName, version);
}
show();
console.log(typeof version);
```

```text output
حاسبتي 2
undefined
```

هذا شيء جيد: كل دالة لها «غرفتها» الخاصة، فلا تتصادم أسماء المتغيرات بين الدوال.

## الدوال قيم أيضًا

في JavaScript يمكنك تخزين دالة في متغير، أو تمريرها إلى دالة أخرى. الدالة التي نمررها تُسمى **دالة رد النداء** (callback):

```js run
function repeat(times, action) {
    for (let i = 1; i <= times; i++) {
        action(i);
    }
}

repeat(3, (n) => console.log("الدورة", n));
```

```text output
الدورة 1
الدورة 2
الدورة 3
```

ستستخدم هذه الفكرة كثيرًا مع المصفوفات (`map` و`filter`) في الدرس القادم، ومع الأحداث في النوافذ.

## الاستدعاء الذاتي (Recursion)

يمكن للدالة أن تستدعي نفسها، بشرط وجود حالة توقف:

```js run
function factorial(n) {
    if (n <= 1) return 1;          // حالة التوقف
    return n * factorial(n - 1);
}
console.log(factorial(5));
```

```text output
120
```

## أخطاء شائعة

- **نسيان القوسين عند الاستدعاء:** `greet;` لا تستدعي الدالة. اكتب `greet();`.
- **نسيان `return`:** `function sum(a, b) { a + b; }` ترجع `undefined`.
- **الأقواس المعقوصة في الدالة السهمية:** `(x) => { x * 2 }` ترجع `undefined` لأن وجود `{ }` يحتاج `return`. اكتب `(x) => x * 2`.
- **استدعاء ذاتي بلا حالة توقف:** يعطي `RangeError: Maximum call stack size exceeded`.

## تمارين

### التمرين 1

اكتب دالة `isEven(n)` ترجع `true` إذا كان العدد زوجيًا، ثم اطبع نتيجتها للأعداد 4 و7.

```js exercise
// function isEven(n) { ... }
// الناتج المطلوب:
// true
// false
```

```js solution
function isEven(n) {
    return n % 2 === 0;
}
console.log(isEven(4));
console.log(isEven(7));
```

```text output
true
false
```

### التمرين 2

اكتب دالة سهمية `toFahrenheit` تحوّل الدرجة المئوية إلى فهرنهايت بالقانون `c * 9 / 5 + 32`، واطبع تحويل `0` و`37` و`100`.

```js exercise
// const toFahrenheit = ...
// 32
// 98.6
// 212
```

```js solution
const toFahrenheit = (c) => c * 9 / 5 + 32;
console.log(toFahrenheit(0));
console.log(toFahrenheit(37));
console.log(toFahrenheit(100));
```

```text output
32
98.6
212
```

### التمرين 3

اكتب دالة `maxOf3(a, b, c)` ترجع أكبر الأعداد الثلاثة **دون** استخدام `Math.max`.

```js exercise
// console.log(maxOf3(3, 11, 7));   // 11
// console.log(maxOf3(-1, -5, -3)); // -1
```

```js solution
function maxOf3(a, b, c) {
    let max = a;
    if (b > max) max = b;
    if (c > max) max = c;
    return max;
}
console.log(maxOf3(3, 11, 7));
console.log(maxOf3(-1, -5, -3));
```

```text output
11
-1
```

## اختبر نفسك

```quiz
{"question": "ماذا ترجع دالة لا تحتوي على `return`؟", "choices": ["0", "null", "undefined", "خطأ"], "answer": 2, "explanation": "الدالة التي لا ترجع شيئًا صراحة ترجع `undefined`."}
```

```quiz
{"question": "ما الذي تطبعه `const f = (x) => x + 1; console.log(f(4));`؟", "choices": ["4", "5", "x + 1", "undefined"], "answer": 1, "explanation": "الدالة السهمية ذات التعبير الواحد ترجع قيمته تلقائيًا: 4 + 1."}
```

```quiz
{"question": "متغير أُنشئ بـ `const` داخل دالة، أين يمكن استخدامه؟", "choices": ["في أي مكان في البرنامج", "داخل تلك الدالة فقط", "في الدوال الأخرى فقط", "بعد انتهاء الدالة فقط"], "answer": 1, "explanation": "المتغير المحلي يعيش داخل كتلته فقط."}
```

## الخلاصة

- `function name(params) { ... return value; }` ثم `name(args)` للاستدعاء.
- القيم الافتراضية: `function f(x = 10)`.
- الدوال السهمية: `(a, b) => a + b`.
- المتغيرات داخل الدالة محلية، والدوال قيم يمكن تمريرها (callbacks).
