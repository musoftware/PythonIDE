# WordStats (console tool) - C

A command-line tool: counts the lines, words and characters of text files and lists the most frequent words. Options `--top N` and `--out report.txt`; exit codes 0 OK, 1 wrong arguments, 2 a file could not be read, 3 the report could not be written. Without arguments it reads sample.txt.

## What it shows

* a console project (no forms, a module with its own main) - F5 runs it in the Output window
* command-line arguments, file I/O, UTF-8 character counting
* a word-frequency table and sorting
* exit codes for errors

## IDE features

* console project: no forms, F5 builds and runs it in the Output window (bridge console mode)
* File > Open Project, F5 / Ctrl+F5, Build > Publish like any other project
* Build > Publish makes a native console exe (about 23 KB)

## Run it

1. File > Open Project... and choose this folder (or Help > Example Projects...).
2. Press F5. Needs gcc (MinGW-w64; the IDE finds or downloads it into %LOCALAPPDATA%\RADIDE\toolchains).
3. Try: F5 (reads sample.txt). After Build > Publish: `WordStats.exe --top 5 sample.txt`, `WordStats.exe missing.txt` (exit code 2).

## Publish

Build > Publish: a native console exe (about 23 KB). The test `samples/Tests/Examples/test_examples_compiled.py` builds, runs and publishes this project and starts the published exe.

## Files

* `project.radproj`
* `sample.txt`
* `WordStats.c`

---

## إحصاء الكلمات (برنامج كونسول) - C

أداة سطر أوامر: تعدّ الأسطر والكلمات والحروف في ملفات نصية وتعرض أكثر الكلمات تكرارًا. الخيارات `--top N` و`--out report.txt`؛ رموز الخروج 0 نجاح، 1 وسائط خاطئة، 2 تعذّرت قراءة ملف، 3 تعذّرت كتابة التقرير. بدون وسائط تقرأ sample.txt.

### ماذا يعرض

* مشروع كونسول (بدون نماذج، ووحدة لها main خاصة) - F5 يشغّله في نافذة المخرجات
* وسائط سطر الأوامر، وقراءة الملفات، وعدّ حروف UTF-8
* جدول تكرار الكلمات والترتيب
* رموز خروج للأخطاء

### مزايا الـ IDE المستخدمة

* مشروع كونسول: بدون نماذج، وF5 يبنيه ويشغّله في نافذة المخرجات
* ملف > فتح مشروع، وF5 / Ctrl+F5، والبناء > النشر مثل أي مشروع آخر
* البناء > النشر يصنع ملف exe كونسول أصلي (حوالي 23 ك.ب)

### التشغيل

1. ملف > فتح مشروع... واختر هذا المجلد (أو مساعدة > أمثلة المشاريع...).
2. اضغط F5. يحتاج gcc (MinGW-w64؛ يجده الـ IDE أو ينزّله في %LOCALAPPDATA%\RADIDE\toolchains).
3. جرّب: F5 (يقرأ sample.txt). بعد البناء > النشر: `WordStats.exe --top 5 sample.txt` و`WordStats.exe missing.txt` (رمز الخروج 2).

### النشر

البناء > النشر: ملف exe كونسول أصلي (حوالي 23 ك.ب).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
