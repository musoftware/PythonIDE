# Quiz Game (TypeScript)

A multiple-choice quiz: 5 random questions, 10 seconds each, a bonus for fast answers.

**What it shows**
- A `Timer` (1 s) driving a `ProgressBar` count-down; time-out counts as a wrong answer.
- Four answer `Button`s sharing one function; captions, `Enabled` and label `ForeColor` changed at run time.
- **Two forms**: `Results` is filled from `Form1` (`"Results.lstAnswers"`) and shown with `show("Results")`;
  its own buttons (`Results.ts`) hide it or start a new game.
- English and **Arabic** question sets (Language menu) in the typed module `Questions.ts`
  (`interface Question`, a tuple type for the four choices, `Record<Lang, Question[]>`), a generic
  `shuffled<T>()` function.
- The best score kept in `quiz.best.json`.

**Run**: open the folder, **F5**, press Start.
**Publish**: Build > Publish (GUI Bridge program, Python inside; Node.js needed on the PC).

---

# لعبة الأسئلة (TypeScript)

مسابقة اختيار من متعدد: 5 أسئلة عشوائية، 10 ثوان لكل سؤال، ونقاط إضافية للإجابة السريعة.

**ماذا يوضح**
- مؤقت `Timer` يحرك شريط التقدم تنازليا، وانتهاء الوقت يُحسب إجابة خاطئة.
- أربعة أزرار للإجابات بدالة واحدة، وتغيير النصوص والألوان أثناء التشغيل.
- **نموذجان**: نموذج النتائج يُملأ من النموذج الأول ويظهر بـ `show("Results")`.
- أسئلة بالإنجليزية و**بالعربية** (قائمة اللغة) في الوحدة `Questions.ts`.
- حفظ أفضل نتيجة في `quiz.best.json`.

**التشغيل**: افتح المجلد واضغط **F5** ثم ابدأ.
**النشر**: Build > Publish (برنامج GUI Bridge، يحتاج Node.js على الجهاز).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
