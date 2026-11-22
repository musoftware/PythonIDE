# File Organizer (preview) - PowerShell (RAD IDE example)

Shows how the files of a folder would be sorted into Images, Documents, Music... folders - as a preview only.

## What it shows
- FolderBrowserDialog, TextBox with Enter to scan, CheckBox (sub-folders)
- `Get-ChildItem` + `Group-Object` in a module (`Organizer.ps1`)
- DataGridView summary per extension and a ListBox plan
- Export the plan to CSV (`Export-Csv`)
- Read-only: the program never moves, copies or deletes files

## RAD IDE features
- A **PowerShell GUI Bridge** project (`powershell-bridge`): the IDE draws the forms (designer + `Form*.form`), your PowerShell code handles the events.
- Designer: menus (MenuStrip editor), ToolBox controls, non-visual components (Timer / dialogs) in the component tray.
- Code editor with IntelliSense for PowerShell; handlers named `<Control>_<Event>` (double-click a control to add one).
- Modules: Project > Add Module (`Organizer.ps1`).
- F5 run, Build > Publish.

## Files
- `Form1.ps1` - event handlers
- `Organizer.ps1` - grouping and the plan

## How to run
1. File > Open Project... and choose this folder (`project.radproj`).
2. Press **F5**. Needs Windows PowerShell 5.1 (built into Windows) or PowerShell 7.
3. Browse... to a folder (or type it and press Enter).
4. Tick Include sub-folders and scan again.
5. File > Export plan (CSV) writes plan.csv into the project.

## Publish
Build > Publish makes a Windows program folder (and optionally an installer). The IDE uses a native
builder for PowerShell when one is available, otherwise the GUI Bridge host is bundled with the PowerShell files.

---

<div dir="rtl">

# منظّم الملفات (معاينة) - PowerShell (مثال من RAD IDE)

يعرض كيف ستُرتّب ملفات مجلد في مجلدات الصور والمستندات والموسيقى... كمعاينة فقط.

## ماذا يعرض
- مربع حوار اختيار مجلد، وEnter للفحص، وخيار المجلدات الفرعية
- `Get-ChildItem` و`Group-Object` في وحدة (`Organizer.ps1`)
- جدول ملخص لكل امتداد وقائمة بالخطة
- تصدير الخطة إلى CSV
- للقراءة فقط: لا ينقل أو ينسخ أو يحذف أي ملف

## مزايا بيئة التطوير المستخدمة
- مشروع **PowerShell GUI Bridge**: البيئة ترسم النماذج في المصمم، وكود PowerShell يعالج الأحداث.
- المصمم: القوائم وأدوات صندوق الأدوات والمكونات غير المرئية (المؤقت ومربعات الحوار).
- محرر الكود مع الإكمال التلقائي، والمعالجات بالاسم `<Control>_<Event>`.
- التشغيل بـ F5 والنشر من Build > Publish.

## طريقة التشغيل
1. من File > Open Project اختر هذا المجلد.
2. اضغط **F5**. يحتاج Windows PowerShell 5.1 (مدمج في ويندوز) أو PowerShell 7.
3. اختر مجلدًا بزر Browse أو اكتبه واضغط Enter.
4. فعّل المجلدات الفرعية وافحص مرة أخرى.
5. ملف > تصدير الخطة يكتب plan.csv في المشروع.

## النشر
Build > Publish يُنشئ مجلد برنامج لويندوز (ومثبّتًا اختياريًا).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
