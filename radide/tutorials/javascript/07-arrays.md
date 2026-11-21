# الدرس 7: المصفوفات (Arrays)

**في هذا الدرس ستتعلم:**

- إنشاء **مصفوفة** والوصول إلى عناصرها بالفهرس.
- الإضافة والحذف: `push` و`pop` و`shift` و`unshift` و`splice`.
- البحث: `includes` و`indexOf` و`find`.
- الأدوات القوية: `forEach` و`map` و`filter` و`reduce`.
- الترتيب بـ `sort`، والدمج بـ `join`.

## ما هي المصفوفة؟

**المصفوفة** (array) قائمة مرتبة من القيم داخل متغير واحد.

> **تشبيه:** المصفوفة مثل **قطار** فيه عربات مرقّمة. كل عربة فيها قيمة، وترقيم العربات يبدأ من **صفر**.

```js run
const colors = ["أحمر", "أخضر", "أزرق"];
console.log(colors[0]);
console.log(colors[2]);
console.log("عدد العناصر:", colors.length);
console.log("الأخير:", colors[colors.length - 1]);
colors[1] = "أصفر";
console.log(colors);
```

```text output
أحمر
أزرق
عدد العناصر: 3
الأخير: أزرق
[ 'أحمر', 'أصفر', 'أزرق' ]
```

- الرقم بين `[ ]` اسمه **الفهرس** (index)، ويبدأ من `0`.
- `colors.length` عدد العناصر، فآخر فهرس هو `length - 1`.
- المصفوفة المنشأة بـ `const` يمكن تغيير **محتواها**، لكن لا يمكن إسناد مصفوفة أخرى للمتغير نفسه.
- `console.log` تعرض المصفوفة بين `[ ]` والنصوص بين علامتي `' '`.

## الإضافة والحذف

```js run
const queue = ["علي", "منى"];
queue.push("سامي");          // إضافة في النهاية
queue.unshift("هدى");        // إضافة في البداية
console.log(queue);

const last = queue.pop();    // حذف الأخير وإرجاعه
const first = queue.shift(); // حذف الأول وإرجاعه
console.log(last, first);
console.log(queue);

const nums = [10, 20, 30, 40, 50];
nums.splice(1, 2);           // من الفهرس 1 احذف عنصرين
console.log(nums);
```

```text output
[ 'هدى', 'علي', 'منى', 'سامي' ]
سامي هدى
[ 'علي', 'منى' ]
[ 10, 40, 50 ]
```

## المرور على المصفوفة

```js run
const prices = [15, 40, 25];

for (let i = 0; i < prices.length; i++) {
    console.log(`العنصر ${i}: ${prices[i]}`);
}

for (const p of prices) {
    console.log("السعر", p);
}

prices.forEach((p, i) => console.log(i, "->", p));
```

```text output
العنصر 0: 15
العنصر 1: 40
العنصر 2: 25
السعر 15
السعر 40
السعر 25
0 -> 15
1 -> 40
2 -> 25
```

## البحث

```js run
const names = ["سارة", "أحمد", "ليلى", "أحمد"];
console.log(names.includes("ليلى"));
console.log(names.indexOf("أحمد"));
console.log(names.indexOf("كريم"));

const scores = [45, 82, 67, 91];
console.log(scores.find((s) => s > 80));
console.log(scores.findIndex((s) => s > 80));
```

```text output
true
1
-1
82
1
```

- `indexOf` ترجع `-1` إن لم تجد العنصر.
- `find` ترجع **أول** عنصر يحقق الشرط، و`findIndex` ترجع فهرسه.

## `map` و`filter` و`reduce`: الثلاثي الذهبي

هذه الدوال تأخذ **دالة رد نداء** وتطبقها على كل عنصر، ولا تغيّر المصفوفة الأصلية بل ترجع نتيجة جديدة:

```js run
const prices = [100, 250, 40, 75];

// map: حوّل كل عنصر إلى شيء آخر
const withTax = prices.map((p) => p * 1.14);
console.log(withTax.map((p) => p.toFixed(1)));

// filter: احتفظ بالعناصر التي تحقق الشرط فقط
const cheap = prices.filter((p) => p < 100);
console.log(cheap);

// reduce: اجمع العناصر في قيمة واحدة
const total = prices.reduce((sum, p) => sum + p, 0);
console.log("الإجمالي:", total);

// يمكن ربطها في سلسلة
const result = prices.filter((p) => p >= 75).map((p) => p / 5);
console.log(result);
```

```text output
[ '114.0', '285.0', '45.6', '85.5' ]
[ 40, 75 ]
الإجمالي: 465
[ 20, 50, 15 ]
```

> **تشبيه:** `map` مصنع يحوّل كل قطعة تدخله، و`filter` مصفاة لا يمر منها إلا ما يحقق الشرط، و`reduce` حصّالة تجمع كل شيء في نتيجة واحدة.

## الترتيب والدمج

```js run
const nums = [10, 2, 33, 4];
nums.sort();
console.log(nums);
nums.sort((a, b) => a - b);
console.log(nums);
nums.sort((a, b) => b - a);
console.log(nums);

const words = ["موز", "تفاح", "عنب"];
console.log(words.join(" - "));
console.log("أ,ب,ج".split(","));
console.log([1, 2, 3].reverse());
console.log([1, 2, 3, 4, 5].slice(1, 3));
```

```text output
[ 10, 2, 33, 4 ]
[ 2, 4, 10, 33 ]
[ 33, 10, 4, 2 ]
موز - تفاح - عنب
[ 'أ', 'ب', 'ج' ]
[ 3, 2, 1 ]
[ 2, 3 ]
```

> **فخ مشهور:** `sort()` بدون دالة ترتّب العناصر **كنصوص**، فيأتي `10` قبل `2`! للأعداد اكتب دائمًا `sort((a, b) => a - b)`.

- `join(فاصل)` تحوّل المصفوفة إلى نص، و`split(فاصل)` العكس.
- `slice(من, إلى)` تنسخ جزءًا (لا يشمل «إلى») دون تغيير الأصل.

## نشر المصفوفة `...`

ثلاث نقاط `...` تفرد عناصر المصفوفة، وهي طريقة سهلة للنسخ والدمج:

```js run
const a = [1, 2];
const b = [3, 4];
const all = [...a, ...b, 5];
console.log(all);
console.log(Math.max(...all));
```

```text output
[ 1, 2, 3, 4, 5 ]
5
```

## أخطاء شائعة

- **الفهرس يبدأ من صفر:** العنصر الأول هو `arr[0]` وليس `arr[1]`.
- **فهرس خارج المصفوفة:** `arr[10]` في مصفوفة من 3 عناصر تعطي `undefined` ولا تعطي خطأ.
- **ترتيب الأعداد بـ `sort()` وحدها:** يرتبها كنصوص.
- **نسيان أن `map` و`filter` ترجعان مصفوفة جديدة:** `prices.map(...)` وحدها لا تغيّر `prices`.

## تمارين

### التمرين 1

لديك درجات طالب. اطبع المتوسط بخانة عشرية واحدة، وأعلى درجة، وعدد الدرجات التي تزيد على 70.

```js exercise
const grades = [85, 62, 90, 71, 55];
// المتوسط: 72.6
// الأعلى: 90
// فوق 70: 3
```

```js solution
const grades = [85, 62, 90, 71, 55];
const avg = grades.reduce((s, g) => s + g, 0) / grades.length;
console.log("المتوسط:", avg.toFixed(1));
console.log("الأعلى:", Math.max(...grades));
console.log("فوق 70:", grades.filter((g) => g > 70).length);
```

```text output
المتوسط: 72.6
الأعلى: 90
فوق 70: 3
```

### التمرين 2

حوّل مصفوفة الأسماء إلى أسماء مرقّمة باستخدام `map` (الدالة تستقبل العنصر والفهرس)، ثم اطبعها كل اسم في سطر بـ `join("\n")`.

```js exercise
const names = ["هدى", "كريم", "نور"];
// 1. هدى
// 2. كريم
// 3. نور
```

```js solution
const names = ["هدى", "كريم", "نور"];
const numbered = names.map((n, i) => `${i + 1}. ${n}`);
console.log(numbered.join("\n"));
```

```text output
1. هدى
2. كريم
3. نور
```

### التمرين 3

احذف الأعداد المكررة من المصفوفة ورتّبها تصاعديًا. (تلميح: احتفظ بالعنصر إن كان `indexOf` له يساوي فهرسه الحالي.)

```js exercise
const nums = [5, 3, 5, 1, 3, 9];
// [ 1, 3, 5, 9 ]
```

```js solution
const nums = [5, 3, 5, 1, 3, 9];
const unique = nums.filter((n, i) => nums.indexOf(n) === i);
unique.sort((a, b) => a - b);
console.log(unique);
```

```text output
[ 1, 3, 5, 9 ]
```

## اختبر نفسك

```quiz
{"question": "ما فهرس العنصر الأول في المصفوفة؟", "choices": ["1", "0", "-1", "حسب المصفوفة"], "answer": 1, "explanation": "الفهرسة في JavaScript تبدأ من صفر."}
```

```quiz
{"question": "ما ناتج `[1, 2, 3].map((x) => x * 10)`؟", "choices": ["[ 10, 20, 30 ]", "60", "[ 1, 2, 3 ]", "30"], "answer": 0, "explanation": "`map` تطبق الدالة على كل عنصر وترجع مصفوفة جديدة."}
```

```quiz
{"question": "لماذا نكتب `sort((a, b) => a - b)` للأعداد؟", "choices": ["لأنها أسرع", "لأن `sort()` وحدها ترتب العناصر كنصوص", "لترتيب تنازلي", "لا داعي لذلك"], "answer": 1, "explanation": "بدون دالة مقارنة يأتي `10` قبل `2` لأن المقارنة تكون حرفًا حرفًا."}
```

```quiz
{"question": "أي دالة تجمع عناصر المصفوفة في قيمة واحدة؟", "choices": ["`filter`", "`map`", "`reduce`", "`find`"], "answer": 2, "explanation": "`reduce` تمر على العناصر وتجمعها في نتيجة واحدة مثل المجموع."}
```

## الخلاصة

- `[a, b, c]` مصفوفة، والفهرس يبدأ من 0، و`length` عدد العناصر.
- `push` و`pop` و`shift` و`unshift` و`splice` للتعديل.
- `map` للتحويل، و`filter` للتصفية، و`reduce` للتجميع، و`find` للبحث.
- رتّب الأعداد بـ `sort((a, b) => a - b)`، وادمج بـ `join`.
