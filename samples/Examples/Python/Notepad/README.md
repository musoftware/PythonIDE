# RAD Notepad (python-tk)

A small Notepad clone: open, edit and save UTF-8 text files.

**What it shows**
- MenuStrip with File / Edit / Format / Help menus (handlers `mnuFileOpen_Click` ...) and keyboard shortcuts
  (Ctrl+N/O/S/F, F3, F5).
- Common dialogs placed from the Toolbox: `OpenFileDialog`, `SaveFileDialog`, `FontDialog` (`ShowDialog()`
  returns `"OK"` / `"Cancel"` and fills `FileName` / `FontName`).
- Clipboard: Cut / Copy / Paste / Select All, Undo.
- An inline **Find bar**: a hidden `Panel` (Visible = False, Dock = Top) shown on demand, with Match case.
- A docked multi-line `TextBox` (Dock = Fill) and a `StatusBar` with line / column / word count.
- "Save changes?" on New / Open / Exit and on the window's close box.

**IDE features**: Windows Forms designer (Dock, hidden Panel, non-visual components in the tray),
event handlers from the Properties window, Run (F5), Build > Publish.

**Run**: File > Open Project > `samples/Examples/Python/Notepad`, press **F5**.
**Publish**: Build > Publish (PyInstaller one-folder program, about 26 MB, Python inside).

---

# المفكرة RAD Notepad (بايثون Tkinter)

نسخة صغيرة من برنامج المفكرة: فتح ملفات نصية UTF-8 وتعديلها وحفظها.

**ماذا يوضح**
- شريط قوائم (ملف / تحرير / تنسيق / مساعدة) واختصارات لوحة المفاتيح.
- مربعات الحوار الجاهزة من صندوق الأدوات: فتح ملف، حفظ ملف، اختيار الخط.
- الحافظة: قص / نسخ / لصق / تحديد الكل، والتراجع.
- شريط بحث داخل النافذة (لوحة Panel مخفية تظهر عند الطلب) مع خيار مطابقة حالة الأحرف.
- مربع نص متعدد الأسطر يملأ النافذة وشريط حالة يعرض السطر والعمود وعدد الكلمات.
- سؤال "حفظ التغييرات؟" عند الجديد والفتح والخروج.

**التشغيل**: ملف > فتح مشروع ثم اختر المجلد، واضغط **F5**.
**النشر**: Build > Publish (برنامج PyInstaller، حوالي 26 ميجابايت، يحتوي على بايثون).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
