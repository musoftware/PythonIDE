# Calculator (JavaScript)

A pocket calculator: 20 buttons, keyboard input and a history list.

**What it shows**
- Many `Button` handlers (`cmd0_Click` ... `cmdEq_Click`) sharing small helper functions.
- Keyboard input through the display's `KeyPress` event: `e.KeyChar` is the typed character and the 4th field of
  `e.args` the key name (`Return`, `BackSpace`, `Escape`).
- A `ListBox` history (`call("lstHistory", "AddItem", ...)`), double-click a line to reuse its result.
- View menu: hide / show the history (`Visible`), clear it.
- The arithmetic in a separate module `CalcEngine.js` (also callable from other languages through RAD Hub:
  `radcall("CalcEngine.calculate", 6, "*", 7)`); no floating-point noise (0.1 + 0.2 = 0.3), division by zero
  shows `Error`.

**Run**: open the folder, **F5**. Click the buttons or click the display and type `12+30` Enter.
**Publish**: Build > Publish (GUI Bridge program, about 73 MB, Python inside; Node.js needed on the PC).

---

# الآلة الحاسبة (جافاسكربت)

آلة حاسبة: 20 زرا، وإدخال من لوحة المفاتيح، وقائمة بالعمليات السابقة.

**ماذا يوضح**
- معالجات كثيرة للأزرار تستخدم دوال مساعدة مشتركة.
- الإدخال من لوحة المفاتيح بحدث `KeyPress`: الحرف في `e.KeyChar` واسم المفتاح (Enter / BackSpace / Esc) في `e.args`.
- قائمة `ListBox` بالعمليات، والنقر المزدوج على سطر يعيد استخدام نتيجته.
- قائمة عرض لإخفاء القائمة أو إظهارها ومسحها.
- العمليات الحسابية في وحدة منفصلة `CalcEngine.js`، بدون أخطاء الكسور العشرية، والقسمة على صفر تعرض Error.

**التشغيل**: افتح المجلد واضغط **F5**.
**النشر**: Build > Publish (برنامج GUI Bridge، حوالي 73 ميجابايت، يحتاج Node.js على الجهاز).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
