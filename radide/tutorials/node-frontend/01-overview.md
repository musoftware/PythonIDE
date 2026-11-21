# الدرس 1: خريطة مشاريع JavaScript في RAD IDE

هذا الدليل عملي: في كل درس ستعرف **أين تضغط** في RAD IDE لتنجز مهمة حقيقية، من موقع Node.js بسيط إلى تطبيق React أو Angular كامل. نفترض أنك تعرف أساسيات JavaScript (دورة «تعلّم JavaScript وTypeScript مع Node.js» في قائمة الدروس نفسها).

**في هذا الدرس ستعرف:**

- أنواع مشاريع JavaScript التي تصنعها RAD IDE، ومتى تختار كل نوع.
- ما الذي تحتاج إلى تثبيته.
- أهم النوافذ والقوائم التي سنستخدمها في الدليل.

## أنواع المشاريع

افتح **File > New Project** (ملف > مشروع جديد...) أو اضغط `Ctrl+Shift+N`. في شجرة اللغات على اليسار ستجد مجموعتين تهمّاننا:

| المجموعة (بالعربية) | العنصر | القوالب | متى تختاره |
|---|---|---|---|
| **Web & Script** (ويب وبرمجة نصية) | **JavaScript** و**TypeScript** | Windows Application، Console Application، Class Library... | برامج سطر أوامر، أو برامج سطح مكتب بنوافذ عبر GUI Bridge |
| **Web** (ويب) | **Node.js Web Site (Express)** | Node.js Empty Site، Express Site | خادم ويب: موقع أو واجهة برمجية (API) |
| **Web** (ويب) | **Node.js Web Site (Express)** | React (Vite)، React + TypeScript (Vite)، Vue (Vite)، Svelte (Vite)، Vanilla JavaScript (Vite)، Angular | تطبيق واجهة أمامية يعمل في المتصفح |
| **Web** (ويب) | **NestJS Web App (TypeScript)** | NestJS App، NestJS (nest new) | خادم كبير منظم بلغة TypeScript |
| **Web** (ويب) | **HTML / CSS / JavaScript Site** | HTML Empty Site | صفحات HTML وCSS وJavaScript بلا خادم خاص |

> **تشبيه:** المطعم له **صالة** يجلس فيها الزبائن (الواجهة الأمامية Front-end: ما يراه المستخدم في المتصفح)، و**مطبخ** يجهّز الطلبات (الواجهة الخلفية Back-end: الخادم). React وVue وAngular لبناء الصالة، وExpress وNestJS لبناء المطبخ، وNode.js يشغّل الاثنين.

## ما الذي تحتاجه؟

1. **Node.js 22 أو أحدث** (النسخة LTS من `https://nodejs.org`)، ومعه `npm` و`npx`.
2. **اتصال بالإنترنت** عند إنشاء المشاريع التي تحتاج حزمًا (Express وVite وAngular وNestJS)، لأن `npm install` ينزّلها.
3. **أدوات التصحيح**: تنزّلها RAD IDE وحدها في المرة الأولى التي تضغط فيها `F5` على موقع، في المجلد `%LOCALAPPDATA%\RADIDE\tools`. لا تحتاج صلاحيات المدير.

تأكد من التثبيت من **View > Terminal** (عرض > الطرفية):

```text
node --version
npm --version
```

## النوافذ التي ستستخدمها كثيرًا

| النافذة | بالعربية | من أين تفتحها | وظيفتها |
|---|---|---|---|
| **Preview** | معاينة | **View > Preview** أو تظهر وحدها عند التشغيل | متصفح داخل RAD IDE يعرض موقعك |
| **Requests** | الطلبات | **View > Requests** | كل طلب وصل إلى الخادم: الطريقة والمسار والحالة والزمن |
| **Output** | المخرجات | **View > Output** | ناتج الخادم (`console.log`) والأخطاء وأوامر npm |
| **Solution Explorer** | مستكشف الحلول | **View > Solution Explorer** | ملفات المشروع، وبالزر الأيمن أوامر كثيرة |
| **Terminal** | الطرفية | ``Ctrl+` `` | لكتابة أوامر `npm` و`npx` بنفسك |
| **REST Client** | عميل REST | **Tools > REST Client** أو `Ctrl+Alt+K` | تجربة الواجهات البرمجية (الدرس 4) |

وعندما يكون المشروع موقعًا تظهر في شريط القوائم قائمة **Site** (الموقع) فيها: **Run Site in Preview** (تشغيل الموقع في المعاينة)، و**Open in Browser** (فتح في المتصفح، `Ctrl+Alt+B`)، و**Restart Web Server** و**Stop Web Server** (إعادة تشغيل / إيقاف خادم الويب)، و**Site Settings...** (إعدادات الموقع...). وإن كان فيه `package.json` تظهر أيضًا قائمة **npm Scripts**.

## مفاتيح التشغيل

| المفتاح | الأمر | ما يحدث مع موقع |
|---|---|---|
| `F5` | **Start Debugging / Continue** | يشغّل الخادم **مع** مصحح الأخطاء: نقاط التوقف تعمل |
| `Ctrl+F5` | **Start Without Debugging** (بدء بدون تصحيح الأخطاء) | يشغّل الخادم ويعرض الموقع في المعاينة، أسرع |
| `Shift+F5` | **Stop Debugging** (إيقاف تصحيح الأخطاء) | يوقف الخادم |
| `F9` | **Toggle Breakpoint** (تبديل نقطة التوقف) | يضع نقطة توقف على السطر الحالي |

## اختبر نفسك

```quiz
{"question": "تريد بناء واجهة برمجية (API) ترسل بيانات JSON. أي مشروع تختار؟", "choices": ["JavaScript > Windows Application", "Node.js Web Site بقالب Express Site", "HTML / CSS / JavaScript Site", "React (Vite)"], "answer": 1, "explanation": "الواجهة البرمجية تعمل على الخادم، وExpress أشهر إطار لذلك."}
```

```quiz
{"question": "أين تظهر قائمة الطلبات التي وصلت إلى خادمك؟", "choices": ["نافذة Requests", "نافذة Properties", "Toolbox", "Error List"], "answer": 0, "explanation": "نافذة Requests (الطلبات) تعرض كل طلب بطريقته ومساره وحالته وزمنه."}
```

```quiz
{"question": "ما الفرق بين F5 وCtrl+F5 مع موقع؟", "choices": ["لا فرق", "F5 يشغّل مع مصحح الأخطاء فتعمل نقاط التوقف، وCtrl+F5 بدونه", "F5 يوقف الخادم", "Ctrl+F5 ينشر الموقع على الإنترنت"], "answer": 1, "explanation": "F5 = Start Debugging، وCtrl+F5 = Start Without Debugging."}
```

## الخلاصة

- **Web & Script** للبرامج والنوافذ، و**Web** للمواقع والخوادم وتطبيقات الواجهة الأمامية.
- تحتاج Node.js 22+ والإنترنت لتنزيل الحزم، وأدوات التصحيح تنزل تلقائيًا.
- النوافذ الأساسية: Preview وRequests وOutput وTerminal وREST Client، والقائمتان Site وnpm Scripts.
