# Unit Converter (TypeScript)

Converts length, mass, temperature and data sizes while you type.

**What it shows**
- TypeScript forms: handlers are typed (`e: RadEvent`), Node.js strips the types when the program runs (no build
  step, Node 22.13+; with older Node the `typescript` npm package is used).
- `RadioButton`s in a `GroupBox` (`CheckedChanged`), two `ComboBox`es filled from code (`Clear` / `AddItem` /
  `ListIndex`), live conversion on `TextChanged` and `SelectedIndexChanged`, a `TrackBar` for the decimals,
  a Swap button and a log `ListBox`.
- A typed module `Units.ts`: a union type `Quantity`, an `interface Unit`, a `Record<Quantity, Unit[]>` table and
  temperature formulas.

**Run**: open the folder, **F5**.
**Publish**: Build > Publish (GUI Bridge program, Python inside; Node.js needed on the PC).

---

# محول الوحدات (TypeScript)

يحول وحدات الطول والكتلة ودرجة الحرارة وأحجام البيانات أثناء الكتابة.

**ماذا يوضح**
- نماذج TypeScript بمعالجات أحداث لها أنواع، وNode.js يزيل الأنواع عند التشغيل بدون خطوة بناء.
- أزرار اختيار داخل مجموعة، وقائمتان منسدلتان تُملآن من الكود، وتحويل فوري، وشريط تمرير لعدد الخانات العشرية.
- وحدة `Units.ts` بأنواع واضحة (union type و interface و Record).

**التشغيل**: افتح المجلد واضغط **F5**.
**النشر**: Build > Publish (برنامج GUI Bridge، يحتاج Node.js على الجهاز).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
