# Password Generator - PowerShell (RAD IDE example)

Generates strong passwords with a cryptographic random generator and shows their strength in English and Arabic.

## What it shows
- NumericUpDown and CheckBoxes as options
- `RandomNumberGenerator` (unbiased) and a Fisher-Yates shuffle in a module (`PwTools.ps1`)
- ProgressBar strength meter, an Arabic label
- Copy to the clipboard (`Set-Clipboard`)
- History ListBox; error MsgBox when no character set is chosen

## RAD IDE features
- A **PowerShell GUI Bridge** project (`powershell-bridge`): the IDE draws the forms (designer + `Form*.form`), your PowerShell code handles the events.
- Designer: menus (MenuStrip editor), ToolBox controls, non-visual components (Timer / dialogs) in the component tray.
- Code editor with IntelliSense for PowerShell; handlers named `<Control>_<Event>` (double-click a control to add one).
- Modules: Project > Add Module (`PwTools.ps1`).
- F5 run, Build > Publish.

## Files
- `Form1.ps1` - event handlers
- `PwTools.ps1` - generation and strength

## How to run
1. File > Open Project... and choose this folder (`project.radproj`).
2. Press **F5**. Needs Windows PowerShell 5.1 (built into Windows) or PowerShell 7.
3. Choose a length and press **Generate**.
4. Type your own password in the box to see its strength.
5. **Copy to clipboard**.

## Publish
Build > Publish makes a Windows program folder (and optionally an installer). The IDE uses a native
builder for PowerShell when one is available, otherwise the GUI Bridge host is bundled with the PowerShell files.

---

<div dir="rtl">

# مولّد كلمات المرور - PowerShell (مثال من RAD IDE)

يولّد كلمات مرور قوية بمولد أرقام عشوائية آمن ويعرض قوتها بالإنجليزية والعربية.

## ماذا يعرض
- خيارات عبر NumericUpDown ومربعات اختيار
- مولد عشوائي آمن وخلط Fisher-Yates في وحدة (`PwTools.ps1`)
- شريط تقدم لقوة كلمة المرور وتسمية عربية
- النسخ إلى الحافظة
- سجل في ListBox ورسالة خطأ إذا لم تُختر أي مجموعة أحرف

## مزايا بيئة التطوير المستخدمة
- مشروع **PowerShell GUI Bridge**: البيئة ترسم النماذج في المصمم، وكود PowerShell يعالج الأحداث.
- المصمم: القوائم وأدوات صندوق الأدوات والمكونات غير المرئية (المؤقت ومربعات الحوار).
- محرر الكود مع الإكمال التلقائي، والمعالجات بالاسم `<Control>_<Event>`.
- التشغيل بـ F5 والنشر من Build > Publish.

## طريقة التشغيل
1. من File > Open Project اختر هذا المجلد.
2. اضغط **F5**. يحتاج Windows PowerShell 5.1 (مدمج في ويندوز) أو PowerShell 7.
3. اختر الطول واضغط **Generate**.
4. اكتب كلمة مرورك لترى قوتها.
5. **Copy to clipboard**.

## النشر
Build > Publish يُنشئ مجلد برنامج لويندوز (ومثبّتًا اختياريًا).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
