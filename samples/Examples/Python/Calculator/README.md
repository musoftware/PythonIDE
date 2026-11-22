# Calculator (python-tk)

A pocket calculator with memory keys and keyboard input.

**What it shows**
- A grid of 24 Buttons laid out in the designer (colors, font sizes), all handled by one `press()` helper.
- A form-level key handler: type `12+7=` or use Enter, Backspace, Esc (C), Delete (CE).
- Memory keys MC / MR / M+ / M- with an "M" indicator Label, an expression line above the display.
- The logic in a **code module** (`CalcEngine.py`, Project > Add Module): decimal arithmetic (0.1 + 0.2 = 0.3),
  "=" repeats the last operation, division by zero message.  Other languages of a solution can call
  `CalcEngine.evaluate("2+3*4")` through RAD Hub.
- A fixed-size window (FormBorderStyle = FixedSingle).

**Run**: open the folder, **F5**.  **Publish**: Build > Publish (PyInstaller, about 26 MB).

---

# الآلة الحاسبة (بايثون Tkinter)

آلة حاسبة بأزرار الذاكرة وإدخال من لوحة المفاتيح.

**ماذا يوضح**
- شبكة من 24 زراً مصممة في المصمم، وكلها تستدعي دالة واحدة `press()`.
- معالج لوحة مفاتيح على مستوى النموذج: اكتب `12+7=` أو استخدم Enter و Backspace و Esc.
- أزرار الذاكرة MC / MR / M+ / M- مع مؤشر "M"، وسطر يعرض العملية الحالية.
- منطق الحساب في وحدة برمجية منفصلة `CalcEngine.py` (حساب عشري دقيق، وتكرار آخر عملية بالضغط على "=" مرة أخرى).
- نافذة بحجم ثابت.

**التشغيل**: افتح المجلد واضغط **F5**.  **النشر**: Build > Publish.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
