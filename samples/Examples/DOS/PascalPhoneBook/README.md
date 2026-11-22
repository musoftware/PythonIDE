# Phone Book (Turbo Pascal style, DOS)

Records saved in a typed file PHONES.DAT: add, list, find, delete, sort by name - the data survives between runs.

## What it shows

* `record` types, `file of TContact`, Assign/Reset/Rewrite/Read/Write/Close with `{$I-}` + IOResult
* Crt unit: ClrScr, TextColor, ReadKey; ReadLn input
* insertion sort on records, case-insensitive search (UpCase, Pos)
* Free Pascal for 16-bit DOS (ppcross8086 -Tmsdos -Mtp)

## Run / build / publish

Ctrl+F5 builds PASCALPH.EXE and runs it in DOSBox-X. A add, L list, F find, D delete, S sort, Q quit.

Language / project type: `dos-pascal`. Files: `MAIN.PAS`, `project.radproj`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (DOSBox-X without a window, keys typed with RADKEYS, output and screen read back).

---

<div dir="rtl">

## دفتر الهاتف (بأسلوب Turbo Pascal، دوس)

سجلات تُحفظ في ملف من نوع محدد PHONES.DAT: إضافة وعرض وبحث وحذف وترتيب بالاسم - والبيانات تبقى بين مرات التشغيل.

### ماذا يعرض

* أنواع `record` و`file of TContact` مع Assign/Reset/Rewrite/Read/Write/Close و`{$I-}` و IOResult
* وحدة Crt: ClrScr و TextColor و ReadKey؛ وإدخال ReadLn
* ترتيب بالإدراج للسجلات وبحث لا يميز حالة الحروف (UpCase و Pos)
* Free Pascal لدوس 16 بت (ppcross8086 -Tmsdos -Mtp)

### التشغيل والبناء والنشر

Ctrl+F5 يبني PASCALPH.EXE ويشغله في DOSBox-X. A إضافة، L عرض، F بحث، D حذف، S ترتيب، Q خروج.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
