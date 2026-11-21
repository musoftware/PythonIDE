# الدرس 7: تطبيقات React وVue وSvelte وAngular

**في هذا الدرس ستتعلم:**

- ما هي أطر الواجهة الأمامية (front-end frameworks)، وما هو **Vite**.
- إنشاء تطبيق React أو Vue أو Svelte أو Angular من RAD IDE بالمولّدات الرسمية.
- فهم ملفات المشروع، والتشغيل مع **التحديث الفوري** (HMR).
- تصحيح أخطاء التطبيق في المعاينة بنقاط توقف في ملفات المصدر.
- بناء نسخة الإنتاج (`npm run build`)، وإنشاء مكونات جديدة من القوائم.

## لماذا أطر الواجهة الأمامية؟

في الدرس السابق غيّرنا الصفحة بأيدينا: `document.getElementById(...).textContent = ...`. في تطبيق كبير فيه مئات العناصر يصبح هذا فوضى. أطر مثل **React** و**Vue** و**Svelte** و**Angular** تقلب الفكرة:

- تقسّم الواجهة إلى **مكونات** (components) صغيرة: زر، بطاقة منتج، قائمة.
- كل مكوّن له **حالة** (state): بيانات تتغير، مثل عدد الضغطات.
- أنت تغيّر الحالة فقط، والإطار يعيد رسم الجزء المتأثر من الصفحة وحده.

> **تشبيه:** بدل أن تعيد طلاء الجدار بنفسك كلما نقلت لوحة، تخبر «المهندس» أين تريد اللوحات (الحالة)، وهو يرتب الجدار. هذه هي فكرة «غيّر البيانات ثم أعد الرسم» التي رأيتها في مدير المهام في نهاية دورة JavaScript.

و**Vite** أداة تطوير وبناء سريعة جدًا: تشغّل خادم تطوير يحدّث الصفحة فور الحفظ، وتجمع ملفاتك في نسخة صغيرة للإنتاج. تستخدمها React وVue وSvelte، أما Angular فلها أداتها الخاصة **Angular CLI**.

## الخطوة 1: إنشاء التطبيق

طريقتان:

**من New Project:** **File > New Project > Web > Node.js Web Site (Express)**، ثم انزل في قائمة القوالب إلى مجموعة الأطر واختر واحدًا:

| القالب | ما ينشئه |
|---|---|
| **React (Vite)** | React بملفات `.jsx` |
| **React + TypeScript (Vite)** | React بملفات `.tsx` وفحص أنواع في المحرر |
| **Vue (Vite)** | Vue 3 بمكونات `.vue` |
| **Svelte (Vite)** | Svelte بمكونات `.svelte` |
| **Vanilla JavaScript (Vite)** | JavaScript عادية مع خادم Vite |
| **Angular** | تطبيق Angular بالأداة الرسمية `ng new` (يأخذ دقيقة تقريبًا أول مرة) |

**من قائمة الموقع:** **Site > New Front-end App (React, Vue, Svelte, Angular)...** (تطبيق واجهة أمامية جديد...). تختار **Framework:** و**Name:** و**Location:** ثم **OK**.

في الحالتين تفتح نافذة تقدّم وتشغّل RAD IDE المولّد الرسمي، مثل `npm create vite@latest . -- --template react`، ثم `npm install`. تحتاج اتصالًا بالإنترنت، وقد يأخذ ذلك دقيقة أو اثنتين.

## الخطوة 2: ملفات المشروع (React مثالًا)

| الملف | ما فيه |
|---|---|
| `index.html` | الصفحة الوحيدة، فيها `<div id="root">` وتحمّل `src/main.jsx` |
| `src/main.jsx` | نقطة البداية: تضع المكوّن `App` داخل `#root` |
| `src/App.jsx` | المكوّن الرئيسي، وهنا تبدأ التعديل |
| `src/*.css` | التنسيقات |
| `vite.config.js` | إعدادات Vite |
| `package.json` | السكربتات `dev` و`build` و`preview`، والحزم |

مكوّن React بسيط يعرض عدادًا (هذه صيغة **JSX**: HTML داخل JavaScript):

```jsx
import { useState } from 'react';

export default function App() {
  const [count, setCount] = useState(0);          // حالة: القيمة ودالة تغييرها
  return (
    <main dir="rtl">
      <h1>عدّاد React</h1>
      <button onClick={() => setCount(count + 1)}>اضغطني</button>
      <p>عدد الضغطات: {count}</p>
    </main>
  );
}
```

والمكوّن نفسه في **Vue** (ملف `src/App.vue`):

```vue
<script setup>
import { ref } from 'vue';
const count = ref(0);
</script>

<template>
  <main dir="rtl">
    <h1>عدّاد Vue</h1>
    <button @click="count++">اضغطني</button>
    <p>عدد الضغطات: {{ count }}</p>
  </main>
</template>
```

لاحظ أنك لا تكتب `document.getElementById` أبدًا: تغيّر `count` فقط، والإطار يحدّث الفقرة.

وهذه المشاريع تستخدم صيغة **ES Modules**: `import ... from '...'` و`export default`، بدل `require` و`module.exports` التي رأيتها في Node.js. الفكرة نفسها: ملف يصدّر، وملف يستورد.

## الخطوة 3: التشغيل والتحديث الفوري

اضغط `Ctrl+F5`. تشغّل RAD IDE الأمر `npm run dev` (أو `ng serve` في Angular) على منفذ حر خلف خادمها، وتفتح **Preview**. عدّل نص العنوان في `src/App.jsx` واحفظ: تتغير الصفحة خلال جزء من الثانية **دون أن تضيع الحالة** (عدد الضغطات يبقى كما هو). هذا اسمه **Hot Module Replacement** (HMR). لذلك لا تعيد RAD IDE تحميل الصفحة بنفسها في هذه المشاريع، فالإطار يتولى ذلك.

## الخطوة 4: تصحيح الأخطاء في ملفات المصدر

1. افتح `src/App.jsx` وضع نقطة توقف (`F9`) على السطر الذي فيه `setCount(count + 1)` (ضع المؤشر داخل السطر).
2. اضغط `F5`.
3. اضغط الزر في المعاينة. يتوقف التنفيذ **في ملفك `App.jsx` نفسه**، مع أن المتصفح يشغّل في الحقيقة كودًا حوّله Vite.

السر هو **خرائط المصدر** (source maps): ملفات صغيرة تربط كل سطر في الكود المحوَّل بالسطر الأصلي في ملفك. والنوافذ نفسها تعمل: **Locals** و**Call Stack** و**Immediate** و`F10` و`F11`.

## الخطوة 5: إنشاء مكونات جديدة

مع مشاريع React وVue وSvelte تظهر في شريط القوائم قائمة باسم الإطار (**React** أو **Vue** أو **Svelte**) فيها:

- **Start Dev Server** و**Build** و**Preview the Build**.
- **New Component...**: يسألك عن اسم المكوّن وينشئ ملفه في `src/components` (بالامتداد المناسب: `.jsx` أو `.tsx` أو `.vue` أو `.svelte`). تجده أيضًا بالزر الأيمن على أي مجلد داخل `src` في **Solution Explorer**.
- **Run Tests** و**Lint** إن كان المشروع يحتوي سكربتاتها.

ومع Angular تظهر قائمة **Angular** فيها **Serve (ng serve)** و**Build (ng build)** و**Build Production**، والقائمة الفرعية **Generate** لإنشاء **New Component...** و**New Service...** و**New Directive...** و**New Pipe...** و**New Guard...** وغيرها (بالأمر `ng generate`)، و**Add Library (ng add)...** و**Run Tests (ng test)**.

## الخطوة 6: نسخة الإنتاج

خادم التطوير ثقيل ومناسب لجهازك فقط. للنشر تحتاج نسخة **مبنية** (build): ملفات HTML وCSS وJavaScript مضغوطة وصغيرة.

- **Site > Build Production (npm run build)** (بناء نسخة الإنتاج): يشغّل `npm run build` (أو `ng build`) ويظهر الناتج في **Output**. الملفات النهائية في المجلد `dist`.
- مجلد `dist` موقع ثابت، يمكن رفعه إلى أي استضافة ملفات ثابتة (سنتكلم عن النشر في الدرس 9).

## فصل المنطق عن المكوّن

كما في الدرس السابق: الحسابات التي لا تحتاج واجهة ضعها في دوال منفصلة (في ملف مثل `src/utils.js`)، فتختبرها بسهولة. مثال لدالة تصفية قائمة مهام يستخدمها مكوّن React:

```js run
function visibleTodos(todos, filter) {
    if (filter === "done") return todos.filter((t) => t.done);
    if (filter === "active") return todos.filter((t) => !t.done);
    return todos;
}

const todos = [
    { id: 1, text: "تعلم React", done: true },
    { id: 2, text: "بناء مشروع", done: false },
    { id: 3, text: "النشر", done: false },
];
console.log(visibleTodos(todos, "all").length);
console.log(visibleTodos(todos, "active").map((t) => t.text).join("، "));
console.log(visibleTodos(todos, "done").map((t) => t.text).join("، "));
```

```text output
3
بناء مشروع، النشر
تعلم React
```

## أخطاء شائعة

- **المجلد ليس فارغًا:** المولّدات تحتاج مجلدًا فارغًا. اختر اسمًا جديدًا.
- **Node.js قديم:** Vite وAngular الحديثان يحتاجان Node.js 20.19 أو 22.12 أو أحدث. RAD IDE تختار إصدارًا أقدم من Angular CLI تلقائيًا إن كان Node.js لا يناسب أحدث إصدار.
- **تعديل ملفات `dist`:** تُحذف وتُعاد مع كل بناء. عدّل في `src` دائمًا.
- **نسيان `export default`:** المكوّن الذي لا يُصدَّر لا يمكن استيراده في ملف آخر.
- **في JSX:** اكتب `className` بدل `class`، وأغلق كل وسم: `<br />` و`<img />`.

## تمرين

اكتب دالة `summary(todos)` يستخدمها مكوّن لعرض سطر الحالة: ترجع نصًا مثل `3 مهام، المتبقي 2`، وترجع `لا توجد مهام` للقائمة الفارغة.

```js exercise
function summary(todos) {
    // ...
}
console.log(summary([{ done: true }, { done: false }, { done: false }]));
console.log(summary([]));
```

```js solution
function summary(todos) {
    if (todos.length === 0) return "لا توجد مهام";
    const left = todos.filter((t) => !t.done).length;
    return `${todos.length} مهام، المتبقي ${left}`;
}
console.log(summary([{ done: true }, { done: false }, { done: false }]));
console.log(summary([]));
```

```text output
3 مهام، المتبقي 2
لا توجد مهام
```

## اختبر نفسك

```quiz
{"question": "ما فائدة Vite؟", "choices": ["قاعدة بيانات", "خادم تطوير سريع مع تحديث فوري، وأداة بناء لنسخة الإنتاج", "إطار خوادم مثل Express", "محرر أكواد"], "answer": 1, "explanation": "Vite يشغّل التطبيق أثناء التطوير مع HMR، ويبنيه في `dist` للإنتاج."}
```

```quiz
{"question": "وضعت نقطة توقف في `src/App.jsx` وضغطت F5. لماذا تتوقف في ملفك رغم أن المتصفح يشغّل كودًا محوّلًا؟", "choices": ["لأن المتصفح يفهم JSX مباشرة", "بفضل خرائط المصدر (source maps)", "لأن RAD IDE تنسخ الملف", "لا تتوقف أبدًا"], "answer": 1, "explanation": "خرائط المصدر تربط الكود المحوّل بأسطر ملفاتك الأصلية."}
```

```quiz
{"question": "أين تجد ملفات نسخة الإنتاج بعد Site > Build Production؟", "choices": ["في `src`", "في `node_modules`", "في `dist`", "في `public`"], "answer": 2, "explanation": "`npm run build` يضع الناتج في `dist` (أو المجلد الذي يحدده Angular)."}
```

## الخلاصة

- React وVue وSvelte وAngular تبني الواجهة من **مكونات** لها **حالة**، وVite (أو Angular CLI) يشغّلها ويبنيها.
- أنشئ التطبيق من **New Project** (قوالب الأطر) أو **Site > New Front-end App...**.
- `Ctrl+F5` للتشغيل مع HMR، و`F5` للتصحيح بنقاط توقف في ملفات المصدر.
- قائمة الإطار فيها **New Component...**، و**Site > Build Production** يبني `dist`.
