# Expense Tracker - Perl (RAD IDE example)

Records expenses with a category, shows them in a grid with totals per category and saves them to a CSV file.

## What it shows
- Data entry with validation messages (MsgBox)
- ComboBox of categories, DataGridView, ListBox of totals
- CSV save / load (quoted fields) in a data module (`ExpenseStore.pl`)
- Delete with a confirmation InputBox
- Enter in the amount box adds the row
- Menus: File (Save / Reload / Exit), Report (Totals)

## RAD IDE features
- A **Perl GUI Bridge** project (`perl-bridge`): the IDE draws the forms (designer + `Form*.form`), your Perl code handles the events.
- Designer: menus (MenuStrip editor), ToolBox controls, non-visual components (Timer / dialogs) in the component tray.
- Code editor with IntelliSense for Perl; handlers named `<Control>_<Event>` (double-click a control to add one).
- Modules: Project > Add Module (`expenses.csv`).
- F5 run, Build > Publish.

## Files
- `Form1.pl` - event handlers
- `ExpenseStore.pl` - rows, CSV, totals
- `expenses.csv` - example data

## How to run
1. File > Open Project... and choose this folder (`project.radproj`).
2. Press **F5**. Needs Perl 5 (perl.exe on PATH, e.g. Git for Windows / Strawberry Perl).
3. Type an item and an amount, choose a category and press **Add** (or Enter).
4. Select a row and press **Delete row**, then type YES.
5. Report > Totals by category.

## Publish
Build > Publish makes a Windows program folder (and optionally an installer). The IDE uses a native
builder for Perl when one is available, otherwise the GUI Bridge host is bundled with the Perl files.

---

<div dir="rtl">

# متابعة المصروفات - Perl (مثال من RAD IDE)

يسجّل المصروفات مع التصنيف ويعرضها في جدول مع الإجمالي لكل تصنيف ويحفظها في ملف CSV.

## ماذا يعرض
- إدخال بيانات مع رسائل تحقق
- قائمة منسدلة للتصنيفات وجدول DataGridView وقائمة الإجماليات
- حفظ وتحميل CSV في وحدة بيانات (`ExpenseStore.pl`)
- حذف مع تأكيد عبر InputBox
- زر Enter في خانة المبلغ يضيف الصف
- قوائم: ملف (حفظ / إعادة تحميل / خروج)، تقرير (الإجماليات)

## مزايا بيئة التطوير المستخدمة
- مشروع **Perl GUI Bridge**: البيئة ترسم النماذج في المصمم، وكود Perl يعالج الأحداث.
- المصمم: القوائم وأدوات صندوق الأدوات والمكونات غير المرئية (المؤقت ومربعات الحوار).
- محرر الكود مع الإكمال التلقائي، والمعالجات بالاسم `<Control>_<Event>`.
- التشغيل بـ F5 والنشر من Build > Publish.

## طريقة التشغيل
1. من File > Open Project اختر هذا المجلد.
2. اضغط **F5**. يحتاج بيرل 5 (perl.exe في PATH، مثل Git for Windows أو Strawberry Perl).
3. اكتب البند والمبلغ واختر التصنيف ثم **Add** أو Enter.
4. اختر صفًا واضغط **Delete row** ثم اكتب YES.
5. تقرير > الإجمالي حسب التصنيف.

## النشر
Build > Publish يُنشئ مجلد برنامج لويندوز (ومثبّتًا اختياريًا).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
