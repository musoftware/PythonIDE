<!-- (c) 2026 Musoftware - https://musoftwares.com - MIT License -->

# Ring Notepad

Text editor in RingQt: menus, toolbar, Open/Save/Font dialogs, clipboard, live status bar.

## What it shows

- MenuStrip (File / Edit / Format / Help) and a ToolStrip whose buttons call the same handlers
- Multi-line TextBox (qTextEdit) docked to fill the form, TextChanged event
- OpenFileDialog / SaveFileDialog / FontDialog components (`dlgOpen.ShowDialog()`)
- Clipboard: Cut / Copy / Paste through qTextEdit
- StatusBar with lines / words / characters (UTF-8 aware, Arabic text counts correctly)
- Opening a file given on the command line (`sysargv`), `*` in the title for unsaved changes

**Language / project type:** `ring-qt`

## Run

F5 runs the form (needs Ring with RingQt - the IDE finds `C:\ring`). Type, use the toolbar, File > Save.

## Publish

Build > Publish makes `RingNotepad.exe` with ring2exe (Qt runtime next to it, no Python).

<div dir="rtl">

# مفكرة Ring

محرر نصوص بـ RingQt: قوائم وشريط أدوات ونوافذ فتح/حفظ/خط والحافظة وشريط حالة مباشر.

## ماذا يوضح

- قائمة رئيسية وشريط أدوات تستدعي أزراره نفس الأحداث
- مربع نص متعدد الأسطر يملأ النافذة وحدث TextChanged
- مكونات نوافذ الفتح والحفظ واختيار الخط
- الحافظة: قص ونسخ ولصق
- شريط حالة بعدد الأسطر والكلمات والحروف (يدعم العربية)
- فتح ملف يُمرَّر في سطر الأوامر وعلامة * عند وجود تعديلات غير محفوظة

## التشغيل

اضغط F5 لتشغيل النافذة (تحتاج Ring مع RingQt). اكتب ثم استخدم شريط الأدوات ثم ملف > حفظ.

## النشر

من القائمة Build > Publish لإنشاء ملف تنفيذي (انظر جدول النتائج).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License. Tested by `samples/Tests/Examples/test_examples_scripting.py --group ring`.
