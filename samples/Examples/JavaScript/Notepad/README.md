# Notepad (JavaScript)

A small text editor written in JavaScript (Node.js). The IDE draws the form (GUI Bridge); `Form1.js` holds the
event handlers and `TextUtils.js` the text helpers.

**What it shows**
- MenuStrip: File (New, Open..., Save, Save As..., Exit), Edit (Find..., Replace All..., Insert Date/Time),
  Format (UPPER / lower case, Sort Lines), Help (Statistics, About).
- `OpenFileDialog` / `SaveFileDialog` from the Toolbox: `call("dlgOpen", "ShowDialog")` returns `"OK"` and
  `get("dlgOpen", "FileName")` the chosen file; the file is read / written with Node's `fs`.
- A multi-line `TextBox` (its text keeps its line breaks across the bridge), InputBox / MsgBox, the form caption
  changed from code, a status label updated on `KeyUp`.
- "Discard changes?" before New / Open / Exit; the last opened file is remembered in `notepad.settings.json`.
- A second code module (`TextUtils.js`): its functions are called directly by the form.

**IDE features**: Windows Forms designer for a JavaScript project, menu editor, non-visual components in the
tray, modules, Run (F5), Build > Publish.

**Run**: File > Open Project > `samples/Examples/JavaScript/Notepad`, press **F5** (Node.js 18+ needed; the IDE
finds it or offers to download it).
**Publish**: Build > Publish - a GUI Bridge program (`Notepad.exe` + the bridge host, Python inside, about 73 MB;
the PC needs Node.js).

---

# المفكرة (جافاسكربت)

محرر نصوص صغير مكتوب بلغة جافاسكربت (Node.js). بيئة التطوير ترسم النموذج (GUI Bridge)، والملف `Form1.js` فيه
معالجات الأحداث و`TextUtils.js` فيه دوال النصوص.

**ماذا يوضح**
- شريط قوائم: ملف (جديد، فتح، حفظ، حفظ باسم، خروج)، تحرير (بحث، استبدال الكل، إدراج التاريخ والوقت)،
  تنسيق (أحرف كبيرة / صغيرة، ترتيب الأسطر)، مساعدة (إحصائيات، حول).
- مربعا الحوار فتح ملف وحفظ ملف من صندوق الأدوات، والقراءة والكتابة بوحدة `fs` في Node.
- مربع نص متعدد الأسطر، ومربعات الإدخال والرسائل، وتغيير عنوان النافذة من الكود، وشريط حالة.
- سؤال قبل تجاهل التغييرات، وتذكر آخر ملف مفتوح في `notepad.settings.json`.
- وحدة كود ثانية (`TextUtils.js`) يستدعي النموذج دوالها مباشرة.

**التشغيل**: ملف > فتح مشروع ثم اختر المجلد واضغط **F5** (يحتاج Node.js).
**النشر**: Build > Publish - برنامج GUI Bridge (حوالي 73 ميجابايت، يحتوي على بايثون، ويحتاج الجهاز إلى Node.js).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
