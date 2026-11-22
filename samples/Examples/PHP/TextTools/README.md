# Text Tools (PHP desktop form)

String utilities with PHP's multibyte functions: case, reverse, word frequency, slug, Base64, MD5 / SHA-256,
sort and unique lines.

**What it shows**
- Two multi-line `TextBox`es (input and read-only output), a `ComboBox` of 13 operations, a "Run when typing"
  `CheckBox` (runs on `TextChanged`), a statistics label (characters, words, lines, UTF-8 bytes).
- Menus with sample texts in English and **Arabic**: `mb_strtoupper`, `mb_str_split`, `preg_*` with `/u`, so Arabic
  is reversed, counted and slugged correctly.
- Errors (invalid Base64) thrown as exceptions in the module `TextOps.php` and shown with `rad_msgbox`.

**Run**: open the folder, **F5**, Samples > نص عربي, choose Reverse, Run.
**Publish**: Build > Publish (GUI Bridge program, Python inside; PHP needed on the PC).

---

# أدوات النصوص (نموذج سطح مكتب بلغة PHP)

أدوات للنصوص بدوال PHP متعددة البايت: تغيير حالة الأحرف، والعكس، وتكرار الكلمات، والروابط (slug)، وBase64،
وMD5 / SHA-256، وترتيب الأسطر وإزالة المكرر.

**ماذا يوضح**
- مربعا نص متعددا الأسطر، وقائمة منسدلة بـ 13 عملية، وخانة "التنفيذ أثناء الكتابة"، وإحصائيات النص.
- نصوص تجريبية بالإنجليزية و**بالعربية**، والعربية تُعكس وتُعد بشكل صحيح.
- الأخطاء تظهر في رسالة.

**التشغيل**: افتح المجلد واضغط **F5**.
**النشر**: Build > Publish (برنامج GUI Bridge، يحتاج PHP على الجهاز).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
