# الدرس 6: تصحيح جافاسكربت المتصفح داخل المعاينة

**في هذا الدرس ستتعلم:**

- الفرق بين كود **الخادم** وكود **المتصفح** في الموقع نفسه.
- تفعيل تصحيح JavaScript داخل **Preview** (المعاينة).
- وضع نقاط توقف في ملفات `.js` التي تعمل في الصفحة، والتوقف عند ضغط زر.
- تصحيح الخادم والمتصفح معًا في جلسة واحدة.

## كودان في موقع واحد

في موقع Node.js يوجد نوعان من JavaScript:

| | كود الخادم | كود المتصفح |
|---|---|---|
| أين يعمل؟ | في Node.js على جهازك (الخادم) | داخل الصفحة في المتصفح (المعاينة) |
| أمثلة | `server.js` و`app.js` والمسارات | `public/js/app.js` والكود داخل `<script>` في HTML |
| يستطيع | قراءة الملفات وقواعد البيانات | تغيير الصفحة (`document`) والاستجابة للنقرات |
| يُصحَّح بـ | مصحح Node.js (الدرس 5) | مصحح المتصفح (هذا الدرس) |

> **تشبيه:** الخادم هو المطبخ والصفحة هي الصالة. الدرس السابق علّمك أن تراقب الطاهي، وهذا الدرس يعلمك أن تراقب النادل وهو يتعامل مع الزبائن.

## كيف يعمل؟

المعاينة في RAD IDE متصفح حقيقي مبني على **Chromium** (المحرك نفسه في Google Chrome). عندما يعمل RAD IDE يفتح هذا المحرك منفذ أدوات المطور (DevTools) على `127.0.0.1` فقط، وعند `F5` تتصل به أداة **vscode-js-debug** وتراقب صفحات موقعك وحدها (لا تلمس صفحات الـ IDE نفسها مثل المحرر والمصمم).

## الخطوة 1: تأكد من تفعيل الخيار

افتح **Tools > Options** (أدوات > خيارات...) ثم الصفحة **Web**، وتأكد أن الخيار **Debug JavaScript in the Preview (F9 in .js files of a web site)** مُعلَّم (وهو مفعّل افتراضيًا). إن غيّرته أعد تشغيل RAD IDE ليعمل التغيير.

## الخطوة 2: صفحة فيها زر

1. أنشئ **Node.js Empty Site** باسم `ClickDemo` (الدرس 2).
2. من **Site > New File...** أنشئ الملف `public/js/app.js` واكتب فيه:

```js
// public/js/app.js - يعمل في المتصفح
let clicks = 0;

function cartTotal(prices, discountPercent) {
    const sum = prices.reduce((s, p) => s + p, 0);
    return sum - sum * discountPercent / 100;
}

document.getElementById('btnBuy').addEventListener('click', () => {
    clicks++;
    const total = cartTotal([120, 80, 50], clicks > 1 ? 10 : 0);
    document.getElementById('result').textContent = `الإجمالي: ${total} جنيه (ضغطة رقم ${clicks})`;
    console.log('clicked', clicks, total);
});
```

3. في `public/index.html` أضف قبل `</body>`:

```html
<button id="btnBuy">اشترِ</button>
<p id="result"></p>
<script src="/js/app.js"></script>
```

## الخطوة 3: نقطة توقف في المتصفح

1. في `public/js/app.js` ضع المؤشر على السطر `clicks++;` واضغط `F9`.
2. اضغط `F5`. يعمل الخادم والمعاينة ومعهما مصحح المتصفح.
3. اضغط الزر **اشترِ** داخل المعاينة.

يتوقف التنفيذ عند `clicks++;`، والصفحة متجمدة تنتظرك. الآن:

- في **Locals** ترى المتغيرات، وفي **Call Stack** ترى أن الاستدعاء جاء من حدث النقر.
- اضغط `F10` حتى تصل إلى سطر `total`، ثم `F11` على `cartTotal` لتدخل داخلها وتراقب `sum`.
- في **Immediate** اكتب `document.title` أو `clicks * 2` واضغط Enter.
- اضغط `F5` (**Continue**) فتكمل الصفحة ويظهر الإجمالي.

ورسائل `console.log` في الصفحة تظهر في نافذة **Output** أثناء التصحيح، بجانب رسائل الخادم.

## الخادم والمتصفح معًا

مع موقع Node.js (أو PHP) تشغّل `F5` **جلستين** معًا: مصحح الخادم ومصحح المتصفح. ضع نقاطًا في الاثنين: مثلًا في كود الصفحة قبل `fetch('/api/time')`، وفي مسار `/api/time` داخل `server.js`. ستتوقف أولًا في المتصفح، ثم بعد `F5` يصل الطلب إلى الخادم فتتوقف هناك. أوامر `F10` و`F5` و**Immediate** تعمل دائمًا على الجلسة المتوقفة حاليًا.

وفي مواقع **HTML / CSS / JavaScript Site** الثابتة (بلا خادم خاص) تعمل جلسة المتصفح وحدها بالطريقة نفسها. وفي تطبيقات React وVue وSvelte وAngular تعمل نقاط التوقف في ملفات المصدر (`.jsx` و`.vue` و`.ts`) بفضل **خرائط المصدر** (source maps)، وهذا في الدرس القادم.

## نصيحة: افصل المنطق عن الصفحة

الدالة `cartTotal` لا تلمس `document`، لذلك يمكن اختبارها في Node.js مباشرة بلا متصفح. كلما فصلت الحسابات عن كود الصفحة، سهل اختبارها وتصحيحها:

```js run
function cartTotal(prices, discountPercent) {
    const sum = prices.reduce((s, p) => s + p, 0);
    return sum - sum * discountPercent / 100;
}

console.log(cartTotal([120, 80, 50], 0));
console.log(cartTotal([120, 80, 50], 10));
console.log(cartTotal([], 10));
```

```text output
250
225
0
```

## أخطاء شائعة

- **لا يتوقف عند النقطة:** تأكد أنك ضغطت `F5` لا `Ctrl+F5`، وأن الخيار في **Tools > Options > Web** مفعّل (وأعدت تشغيل RAD IDE بعد تغييره)، وأن الملف هو نفسه الذي تحمّله الصفحة (`<script src="/js/app.js">`).
- **نقطة التوقف في كود الخادم بدل المتصفح:** كود `public/js` للمتصفح، و`server.js` للخادم. لا تخلط بينهما.
- **الصفحة في متصفح خارجي:** المصحح يراقب **Preview** داخل RAD IDE فقط. الصفحة المفتوحة بـ **Open in Browser** لها أدوات المطور الخاصة بمتصفحها (`F12` فيه).
- **`document is not defined`:** كتبت كود صفحة في ملف يعمل على الخادم.

## تمرين

اكتب دالة `formatPrice(value)` ستستخدمها الصفحة لعرض الأسعار: تقرّب إلى خانتين عشريتين وتضيف «جنيه»، وتعيد «مجانًا» للصفر. اختبرها في Node.js قبل وضعها في الصفحة.

```js exercise
function formatPrice(value) {
    // ...
}
console.log(formatPrice(12.5));
console.log(formatPrice(0));
console.log(formatPrice(99.999));
```

```js solution
function formatPrice(value) {
    if (value === 0) return "مجانًا";
    return `${value.toFixed(2)} جنيه`;
}
console.log(formatPrice(12.5));
console.log(formatPrice(0));
console.log(formatPrice(99.999));
```

```text output
12.50 جنيه
مجانًا
100.00 جنيه
```

## اختبر نفسك

```quiz
{"question": "أين يعمل الملف `public/js/app.js` في موقع Node.js؟", "choices": ["على الخادم في Node.js", "داخل الصفحة في المتصفح", "في نافذة Output", "لا يعمل"], "answer": 1, "explanation": "ملفات `public` تُرسل إلى المتصفح كما هي ويشغّلها هو."}
```

```quiz
{"question": "ما الذي تحتاجه لتتوقف عند نقطة في كود الصفحة؟", "choices": ["Ctrl+F5 فقط", "F5 مع تفعيل Debug JavaScript in the Preview في Tools > Options > Web", "فتح الصفحة في متصفح خارجي", "تثبيت Chrome"], "answer": 1, "explanation": "F5 يشغّل مصحح المتصفح الذي يتصل بالمعاينة عبر منفذ DevTools."}
```

```quiz
{"question": "وضعت نقطة في كود الصفحة ونقطة في الخادم وضغطت F5. ماذا يحدث؟", "choices": ["تعمل نقطة الخادم فقط", "تعمل الاثنتان، والأوامر تذهب إلى الجلسة المتوقفة", "تعمل نقطة الصفحة فقط", "يظهر خطأ"], "answer": 1, "explanation": "مع مواقع Node.js وPHP تعمل جلستا الخادم والمتصفح معًا."}
```

## الخلاصة

- كود الخادم يعمل في Node.js، وكود `public/js` يعمل في المتصفح، ولكل منهما مصححه.
- فعّل **Debug JavaScript in the Preview** في **Tools > Options > Web**، ثم `F9` و`F5` واضغط في المعاينة.
- مع مواقع Node.js تعمل الجلستان معًا، وفي تطبيقات Vite تعمل النقاط في ملفات المصدر بخرائط المصدر.
- افصل الحسابات في دوال لا تلمس `document` لتختبرها بسهولة.
