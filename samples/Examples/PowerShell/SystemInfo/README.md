# System Info - PowerShell (RAD IDE example)

A read-only dashboard of this PC: Windows, hardware, memory, drives and the processes that use the most memory.

## What it shows
- CIM/WMI queries (`Get-CimInstance`) in a module (`SysInfo.ps1`, loaded before the form)
- DataGridView, ListBoxes, ProgressBar (memory in use)
- Timer: a clock, plus auto refresh every 5 s (View menu toggle)
- SaveFileDialog: saves a text report
- Nothing on the computer is changed

## RAD IDE features
- A **PowerShell GUI Bridge** project (`powershell-bridge`): the IDE draws the forms (designer + `Form*.form`), your PowerShell code handles the events.
- Designer: menus (MenuStrip editor), ToolBox controls, non-visual components (Timer / dialogs) in the component tray.
- Code editor with IntelliSense for PowerShell; handlers named `<Control>_<Event>` (double-click a control to add one).
- Modules: Project > Add Module (`SysInfo.ps1`).
- F5 run, Build > Publish.

## Files
- `Form1.ps1` - event handlers
- `SysInfo.ps1` - the queries

## How to run
1. File > Open Project... and choose this folder (`project.radproj`).
2. Press **F5**. Needs Windows PowerShell 5.1 (built into Windows) or PowerShell 7.
3. Press **Refresh**.
4. View > Auto refresh.
5. File > Save report...

## Publish
Build > Publish makes a Windows program folder (and optionally an installer). The IDE uses a native
builder for PowerShell when one is available, otherwise the GUI Bridge host is bundled with the PowerShell files.

---

<div dir="rtl">

# معلومات النظام - PowerShell (مثال من RAD IDE)

لوحة معلومات للقراءة فقط عن الجهاز: ويندوز والعتاد والذاكرة والأقراص والعمليات الأكثر استهلاكًا للذاكرة.

## ماذا يعرض
- استعلامات CIM/WMI في وحدة (`SysInfo.ps1`)
- جدول DataGridView وقوائم وشريط تقدم لاستخدام الذاكرة
- مؤقت للساعة وتحديث تلقائي كل 5 ثوانٍ
- مربع حوار حفظ لتقرير نصي
- لا يغيّر أي شيء في الجهاز

## مزايا بيئة التطوير المستخدمة
- مشروع **PowerShell GUI Bridge**: البيئة ترسم النماذج في المصمم، وكود PowerShell يعالج الأحداث.
- المصمم: القوائم وأدوات صندوق الأدوات والمكونات غير المرئية (المؤقت ومربعات الحوار).
- محرر الكود مع الإكمال التلقائي، والمعالجات بالاسم `<Control>_<Event>`.
- التشغيل بـ F5 والنشر من Build > Publish.

## طريقة التشغيل
1. من File > Open Project اختر هذا المجلد.
2. اضغط **F5**. يحتاج Windows PowerShell 5.1 (مدمج في ويندوز) أو PowerShell 7.
3. اضغط **Refresh**.
4. عرض > تحديث تلقائي.
5. ملف > حفظ التقرير.

## النشر
Build > Publish يُنشئ مجلد برنامج لويندوز (ومثبّتًا اختياريًا).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
