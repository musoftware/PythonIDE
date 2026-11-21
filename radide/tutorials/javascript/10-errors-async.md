# الدرس 10: الأخطاء والبرمجة غير المتزامنة (async/await)

**في هذا الدرس ستتعلم:**

- التقاط الأخطاء بـ `try` و`catch` و`finally`.
- رمي أخطائك الخاصة بـ `throw`.
- ما معنى «غير متزامن»، و`setTimeout`.
- **الوعود** (Promises) والكلمتين `async` و`await`.
- تنفيذ عدة مهام معًا بـ `Promise.all`.

## الأخطاء جزء طبيعي من البرمجة

عندما يحدث خطأ أثناء التشغيل (مثل قراءة خاصية من `undefined`) يتوقف البرنامج ويطبع رسالة الخطأ. لكن أحيانًا نتوقع حدوث الخطأ ونريد التعامل معه بهدوء: إن كتب المستخدم بيانات غير صالحة نعرض له رسالة بدل أن ينهار البرنامج.

## `try ... catch ... finally`

```js run
try {
    const data = JSON.parse("{ هذا ليس JSON }");
    console.log(data);
} catch (err) {
    console.log("حدث خطأ:", err.name);
} finally {
    console.log("هذا السطر يُنفَّذ دائمًا");
}
console.log("البرنامج مستمر");
```

```text output
حدث خطأ: SyntaxError
هذا السطر يُنفَّذ دائمًا
البرنامج مستمر
```

- نضع الكود الذي قد يفشل داخل `try`.
- إن حدث خطأ ينتقل التنفيذ فورًا إلى `catch`، والمتغير `err` فيه معلومات الخطأ: `err.name` نوعه، و`err.message` رسالته.
- `finally` اختيارية، وتُنفَّذ في كل الأحوال (مفيدة لإغلاق ملف أو اتصال).

> **تشبيه:** `try` مثل لاعب السيرك على الحبل، و`catch` هي **شبكة الأمان** تحته. إن سقط لا تنتهي العرض، بل يقع على الشبكة ويكمل.

## رمي الأخطاء بـ `throw`

يمكنك أن تُطلق خطأً بنفسك عندما تكتشف مشكلة:

```js run
function withdraw(balance, amount) {
    if (amount <= 0) {
        throw new Error("المبلغ يجب أن يكون أكبر من صفر");
    }
    if (amount > balance) {
        throw new Error("الرصيد غير كافٍ");
    }
    return balance - amount;
}

for (const amount of [200, 5000, -1]) {
    try {
        console.log("الرصيد الجديد:", withdraw(1000, amount));
    } catch (e) {
        console.log("مرفوض:", e.message);
    }
}
```

```text output
الرصيد الجديد: 800
مرفوض: الرصيد غير كافٍ
مرفوض: المبلغ يجب أن يكون أكبر من صفر
```

## ما معنى «غير متزامن»؟

بعض العمليات تأخذ وقتًا: تحميل صفحة من الإنترنت، قراءة ملف كبير، انتظار مؤقت. لو انتظر البرنامج كل عملية حتى تنتهي لتجمّد. لذلك تبدأ JavaScript العملية، **وتكمل بقية الكود**، ثم تعود إلى النتيجة عندما تجهز.

> **تشبيه:** في المطعم يأخذ النادل طلبك ويذهب لخدمة طاولات أخرى، ولا يقف بجانب المطبخ حتى ينضج طعامك. عندما يجهز الطبق يحضره لك. هذا هو العمل **غير المتزامن** (asynchronous).

```js run
console.log("1) طلبت القهوة");
setTimeout(() => {
    console.log("3) القهوة جاهزة!");
}, 500);
console.log("2) أقرأ الجريدة أثناء الانتظار");
```

```text output
1) طلبت القهوة
2) أقرأ الجريدة أثناء الانتظار
3) القهوة جاهزة!
```

`setTimeout(دالة, ملي_ثانية)` تنفّذ الدالة بعد المدة المحددة (500 ملي ثانية = نصف ثانية)، لكن البرنامج لا ينتظر عندها، بل يطبع السطر الثاني أولًا.

## الوعود (Promises)

**الوعد** (Promise) كائن يمثّل نتيجة ستأتي **لاحقًا**: إما أن يُوفى به (resolve) بقيمة، أو يُرفض (reject) بخطأ.

```js run
function orderPizza(size) {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            if (size === "كبيرة" || size === "صغيرة") {
                resolve(`بيتزا ${size} جاهزة`);
            } else {
                reject(new Error(`لا يوجد مقاس ${size}`));
            }
        }, 200);
    });
}

orderPizza("كبيرة")
    .then((msg) => console.log(msg))
    .catch((e) => console.log("خطأ:", e.message));
```

```text output
بيتزا كبيرة جاهزة
```

`then` تستقبل النتيجة عند النجاح، و`catch` تستقبل الخطأ.

## `async` و`await`: الطريقة الأسهل

`await` تعني «انتظر هذا الوعد حتى يكتمل، ثم أعطني نتيجته»، ولا تُستخدم إلا داخل دالة معلّمة بـ `async`. والجميل أن الكود يُقرأ من أعلى إلى أسفل كأنه عادي، ونلتقط الأخطاء بـ `try/catch` المعتادة:

```js run
function wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function orderPizza(size) {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            if (size === "كبيرة" || size === "صغيرة") resolve(`بيتزا ${size} جاهزة`);
            else reject(new Error(`لا يوجد مقاس ${size}`));
        }, 100);
    });
}

async function main() {
    console.log("بدأنا");
    await wait(200);
    console.log("مرّت 200 ملي ثانية");

    const p = await orderPizza("صغيرة");
    console.log(p);

    try {
        await orderPizza("عملاقة");
    } catch (e) {
        console.log("خطأ:", e.message);
    }
    console.log("انتهينا");
}

main();
```

```text output
بدأنا
مرّت 200 ملي ثانية
بيتزا صغيرة جاهزة
خطأ: لا يوجد مقاس عملاقة
انتهينا
```

> **مهم:** الدالة `async` ترجع دائمًا وعدًا. لذلك كتبنا الكود داخل `main()` ثم استدعيناها في الآخر. هذا هو النمط الذي سنستخدمه في الدروس القادمة مع الملفات والإدخال.

## عدة مهام معًا: `Promise.all`

```js run
const wait = (ms, value) => new Promise((r) => setTimeout(() => r(value), ms));

async function main() {
    const start = Date.now();
    const results = await Promise.all([
        wait(300, "الأخبار"),
        wait(300, "الطقس"),
        wait(300, "الأسعار"),
    ]);
    const seconds = (Date.now() - start) / 1000;
    console.log(results.join(" + "));
    console.log(seconds < 0.6 ? "انتهت معًا في وقت واحد تقريبًا" : "انتهت واحدة بعد الأخرى");
}
main();
```

```text output
الأخبار + الطقس + الأسعار
انتهت معًا في وقت واحد تقريبًا
```

المهام الثلاث تعمل **في الوقت نفسه**، فالمجموع حوالي 0.3 ثانية لا 0.9.

## مثال حقيقي: `fetch`

في Node.js 18 وما بعده توجد الدالة `fetch` لطلب البيانات من الإنترنت. هذا المثال يحتاج اتصالًا بالإنترنت، لذلك هو للقراءة فقط:

```js
async function showUser() {
    try {
        const res = await fetch("https://jsonplaceholder.typicode.com/users/1");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const user = await res.json();
        console.log(user.name, "-", user.email);
    } catch (e) {
        console.log("تعذّر التحميل:", e.message);
    }
}
showUser();
```

## أخطاء شائعة

- **نسيان `await`:** `const p = orderPizza("صغيرة"); console.log(p);` تطبع `Promise { <pending> }` لا النتيجة.
- **`await` خارج دالة `async`:** في ملفات البرنامج في RAD IDE يعطي `SyntaxError: await is only valid in async functions`. ضع الكود داخل `async function main()`.
- **ابتلاع الخطأ:** `catch (e) {}` الفارغة تخفي المشاكل. اطبع الخطأ على الأقل.
- **وعد مرفوض بلا `catch`:** يطبع Node.js رسالة `UnhandledPromiseRejection` ويوقف البرنامج.

## تمارين

### التمرين 1

اكتب دالة `parseAge(text)` تحوّل النص إلى عدد، وترمي خطأ برسالة `"العمر غير صالح"` إن لم يكن عددًا صحيحًا بين 0 و120. جرّبها على القيم الثلاث.

```js exercise
// for (const t of ["25", "abc", "200"]) { ... }
// 25
// خطأ: العمر غير صالح
// خطأ: العمر غير صالح
```

```js solution
function parseAge(text) {
    const n = Number(text);
    if (!Number.isInteger(n) || n < 0 || n > 120) {
        throw new Error("العمر غير صالح");
    }
    return n;
}
for (const t of ["25", "abc", "200"]) {
    try {
        console.log(parseAge(t));
    } catch (e) {
        console.log("خطأ:", e.message);
    }
}
```

```text output
25
خطأ: العمر غير صالح
خطأ: العمر غير صالح
```

### التمرين 2

اكتب دالة `async` اسمها `countdown(n)` تطبع الأعداد من `n` إلى 1، بانتظار 100 ملي ثانية بين كل عدد والذي يليه، ثم تطبع «انطلق!».

```js exercise
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
// countdown(3) تطبع:
// 3
// 2
// 1
// انطلق!
```

```js solution
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function countdown(n) {
    for (let i = n; i >= 1; i--) {
        console.log(i);
        await wait(100);
    }
    console.log("انطلق!");
}
countdown(3);
```

```text output
3
2
1
انطلق!
```

## اختبر نفسك

```quiz
{"question": "متى يُنفَّذ الجزء `finally`؟", "choices": ["عند حدوث خطأ فقط", "عند عدم حدوث خطأ فقط", "في كل الأحوال", "لا يُنفَّذ أبدًا"], "answer": 2, "explanation": "`finally` تُنفَّذ سواء حدث خطأ أم لا."}
```

```quiz
{"question": "ما ترتيب الطباعة؟ `console.log(\"A\"); setTimeout(() => console.log(\"B\"), 0); console.log(\"C\");`", "choices": ["A B C", "A C B", "B A C", "C A B"], "answer": 1, "explanation": "حتى مع مهلة 0 تُنفَّذ دالة `setTimeout` بعد انتهاء الكود الحالي، فتأتي B أخيرًا."}
```

```quiz
{"question": "أين يمكن استخدام `await` في ملفات برنامجك؟", "choices": ["في أي مكان", "داخل دالة معلّمة بـ `async`", "داخل الحلقات فقط", "داخل `catch` فقط"], "answer": 1, "explanation": "`await` تعمل داخل الدوال المعلّمة بـ `async`."}
```

## الخلاصة

- `try/catch/finally` لالتقاط الأخطاء، و`throw new Error("...")` لرميها.
- العمليات البطيئة غير متزامنة: البرنامج لا يتجمد أثناء انتظارها.
- الوعد نتيجة مستقبلية، و`async/await` أسهل طريقة للتعامل معه.
- `Promise.all` لتنفيذ عدة مهام معًا.
