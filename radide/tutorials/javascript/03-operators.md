# الدرس 3: العمليات الحسابية والمقارنة والمنطق

**في هذا الدرس ستتعلم:**

- العوامل الحسابية: `+` و`-` و`*` و`/` و`%` و`**`.
- اختصارات مثل `+=` و`++`.
- المقارنة بـ `===` و`!==` ولماذا نتجنب `==`.
- العوامل المنطقية `&&` و`||` و`!`.
- الكائن `Math` للعمليات الرياضية الجاهزة.

## العوامل الحسابية

```js run
const a = 17;
const b = 5;
console.log("الجمع:", a + b);
console.log("الطرح:", a - b);
console.log("الضرب:", a * b);
console.log("القسمة:", a / b);
console.log("باقي القسمة:", a % b);
console.log("الأس:", 2 ** 10);
```

```text output
الجمع: 22
الطرح: 12
الضرب: 85
القسمة: 3.4
باقي القسمة: 2
الأس: 1024
```

- القسمة في JavaScript تعطي الناتج العشري دائمًا: `17 / 5` تعطي `3.4` وليس `3`.
- `%` تعطي **باقي القسمة**: `17 % 5` هو `2` لأن `17 = 5 × 3 + 2`. مفيدة جدًا لمعرفة هل العدد زوجي: `n % 2 === 0`.
- `**` للأس: `2 ** 10` تعني 2 مرفوعة للقوة 10.

> **تشبيه:** باقي القسمة مثل توزيع 17 قطعة حلوى على 5 أطفال بالتساوي: كل طفل يأخذ 3، ويتبقى معك قطعتان.

## ترتيب العمليات

مثل الرياضيات تمامًا: الأقواس أولًا، ثم الأس، ثم الضرب والقسمة، ثم الجمع والطرح:

```js run
console.log(2 + 3 * 4);
console.log((2 + 3) * 4);
console.log(10 - 4 - 3);
```

```text output
14
20
3
```

عندما تشك، ضع أقواسًا. الأقواس الزائدة لا تضر وتجعل الكود أوضح.

## اختصارات الإسناد

```js run
let score = 10;
score += 5;     // نفس score = score + 5
console.log(score);
score -= 3;     // score = score - 3
console.log(score);
score *= 2;     // score = score * 2
console.log(score);
score++;        // زيادة 1
console.log(score);
score--;        // نقصان 1
console.log(score);

let msg = "مرحبًا";
msg += " يا صديقي";
console.log(msg);
```

```text output
15
12
24
25
24
مرحبًا يا صديقي
```

## الأعداد العشرية: مفاجأة صغيرة

```js run
console.log(0.1 + 0.2);
console.log((0.1 + 0.2).toFixed(2));
console.log(Math.round(2.567 * 100) / 100);
```

```text output
0.30000000000000004
0.30
2.57
```

الحاسوب يخزّن الأعداد العشرية بالنظام الثنائي، وبعضها لا يُمثَّل بدقة تامة، فيظهر هذا الفرق الصغير جدًا. هذا ليس خطأ في JavaScript وحدها، بل يحدث في أغلب اللغات. للعرض استخدم `toFixed(2)` التي تعطي **نصًا** بعدد الخانات العشرية الذي تريده.

## المقارنة

نتيجة المقارنة دائمًا `true` أو `false`:

```js run
console.log(5 > 3);
console.log(5 < 3);
console.log(5 >= 5);
console.log(4 <= 3);
console.log(5 === 5);
console.log(5 !== 3);
```

```text output
true
false
true
false
true
true
```

### `===` وليس `==`

في JavaScript نوعان من «يساوي»:

- `===` **المساواة الصارمة**: تقارن القيمة **والنوع** معًا.
- `==` المساواة المتساهلة: تحوّل الأنواع قبل المقارنة، فتعطي نتائج غريبة.

```js run
console.log(5 === "5");
console.log(5 == "5");
console.log(0 == "");
console.log(0 === "");
```

```text output
false
true
true
false
```

> **قاعدة:** استخدم دائمًا `===` و`!==`. انسَ أن `==` موجودة.

## العوامل المنطقية

| العامل | معناه | مثال |
|---|---|---|
| `&&` | «و»: صحيح إذا كان الطرفان صحيحين | `age >= 18 && hasId` |
| `\|\|` | «أو»: صحيح إذا كان أحدهما صحيحًا على الأقل | `isAdmin \|\| isOwner` |
| `!` | «ليس»: يعكس القيمة | `!isEmpty` |

```js run
const age = 20;
const hasTicket = true;
console.log(age >= 18 && hasTicket);
console.log(age < 12 || age > 60);
console.log(!hasTicket);
```

```text output
true
false
false
```

## القيم «الصادقة» و«الكاذبة»

عندما تضع قيمة غير منطقية في مكان ينتظر `true` أو `false`، تعتبر JavaScript هذه القيم **كاذبة** (falsy): `false` و`0` و`""` (النص الفارغ) و`null` و`undefined` و`NaN`. وكل ما عداها **صادق** (truthy).

```js run
console.log(Boolean(0), Boolean(""), Boolean(null));
console.log(Boolean(7), Boolean("مرحبًا"), Boolean("0"));
const nickname = "";
console.log(nickname || "ضيف");
```

```text output
false false false
true true true
ضيف
```

السطر الأخير حيلة مشهورة: `nickname || "ضيف"` تعطي `nickname` إن كان فيه شيء، وإلا تعطي `"ضيف"`. وهناك عامل أحدث `??` يفعل الشيء نفسه لكن مع `null` و`undefined` فقط: `0 ?? 5` تعطي `0`.

## الكائن `Math`

فيه دوال رياضية جاهزة:

```js run
console.log(Math.round(4.6));
console.log(Math.floor(4.9));
console.log(Math.ceil(4.1));
console.log(Math.max(3, 9, 2));
console.log(Math.min(3, 9, 2));
console.log(Math.sqrt(81));
console.log(Math.abs(-7));
console.log(Math.PI.toFixed(4));
```

```text output
5
4
5
9
2
9
7
3.1416
```

و`Math.random()` تعطي عددًا عشوائيًا بين 0 و1 (لا يصل إلى 1). للحصول على رقم نرد من 1 إلى 6 نكتب `Math.floor(Math.random() * 6) + 1`. لن نضعها في مثال له ناتج متوقع لأن الناتج يتغير كل مرة!

## أخطاء شائعة

- **الخلط بين `=` و`===`:** الأولى إسناد (ضع القيمة)، والثانية مقارنة (هل يتساويان؟).
- **استخدام `==`:** تعطي `true` لمقارنات غير منطقية مثل `0 == ""`.
- **نسيان أن `toFixed` تعطي نصًا:** `(2.5).toFixed(1) + 1` تعطي `"2.51"`.
- **القسمة على صفر:** لا تسبب خطأ، بل تعطي `Infinity`. تحقق من المقام بنفسك.

## تمارين

### التمرين 1

لديك عدد الثواني `3725`. اطبع كم ساعة ودقيقة وثانية فيه، باستخدام `Math.floor` و`%`.

```js exercise
const total = 3725;
// الناتج المطلوب: 1 ساعة، 2 دقيقة، 5 ثانية
```

```js solution
const total = 3725;
const hours = Math.floor(total / 3600);
const minutes = Math.floor((total % 3600) / 60);
const seconds = total % 60;
console.log(`${hours} ساعة، ${minutes} دقيقة، ${seconds} ثانية`);
```

```text output
1 ساعة، 2 دقيقة، 5 ثانية
```

### التمرين 2

احسب سعر منتج بعد خصم `15%` من `240` جنيهًا، واطبعه بخانتين عشريتين.

```js exercise
const price = 240;
const discount = 15;   // نسبة مئوية
// الناتج المطلوب: السعر بعد الخصم: 204.00
```

```js solution
const price = 240;
const discount = 15;
const final = price - price * discount / 100;
console.log("السعر بعد الخصم:", final.toFixed(2));
```

```text output
السعر بعد الخصم: 204.00
```

### التمرين 3

اطبع هل العدد `n` زوجي (`true` أو `false`)، ثم اطبع هل هو بين 10 و20 (شاملًا الطرفين).

```js exercise
const n = 14;
// true
// true
```

```js solution
const n = 14;
console.log(n % 2 === 0);
console.log(n >= 10 && n <= 20);
```

```text output
true
true
```

## اختبر نفسك

```quiz
{"question": "ما ناتج `17 % 4`؟", "choices": ["4", "1", "4.25", "0"], "answer": 1, "explanation": "17 = 4 × 4 + 1، فالباقي 1."}
```

```quiz
{"question": "ما ناتج `5 === \"5\"`؟", "choices": ["true", "false", "خطأ", "\"5\""], "answer": 1, "explanation": "`===` تقارن النوع أيضًا: عدد ونص، فالنتيجة false."}
```

```quiz
{"question": "ما الذي تعطيه `\"\" || \"ضيف\"`؟", "choices": ["\"\"", "\"ضيف\"", "true", "false"], "answer": 1, "explanation": "النص الفارغ قيمة كاذبة، فيعطي `||` القيمة الثانية."}
```

```quiz
{"question": "أي تعبير يعطي true إذا كان العمر 18 أو أكثر **ومعه** تذكرة؟", "choices": ["`age >= 18 || ticket`", "`age >= 18 && ticket`", "`!(age >= 18)`", "`age = 18 && ticket`"], "answer": 1, "explanation": "«و» تُكتب `&&`، وتحتاج إلى أن يكون الطرفان صحيحين."}
```

## الخلاصة

- `+ - * / % **` للحساب، و`+=` و`++` اختصارات مريحة.
- `toFixed(n)` لعرض الأعداد العشرية، و`Math` للدوال الرياضية.
- قارن دائمًا بـ `===` و`!==`.
- `&&` و`||` و`!` لربط الشروط، و`||` أو `??` لإعطاء قيمة افتراضية.
