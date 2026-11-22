# Batch Toolbox (DOS .BAT)

CHOICE menu with ERRORLEVEL, a second batch file called with an argument, notes kept in NOTES.TXT, FOR loops and DIR.

## What it shows

* CHOICE /C and ERRORLEVEL tested from the highest value down
* CALL NOTES.BAT ADD|SHOW with `%1`, IF EXIST / NOT EXIST
* redirection `>` and `>>`, TYPE, SET variables, FOR %%N IN (...)
* the IDE's batch "build" checks every GOTO / CALL target

## Run / build / publish

Ctrl+F5 runs MAIN.BAT in DOSBox-X (COMMAND.COM). Keys 1-6.

Language / project type: `dos-batch`. Files: `MAIN.BAT`, `NOTES.BAT`, `project.radproj`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (DOSBox-X without a window, keys typed with RADKEYS, output and screen read back).

---

<div dir="rtl">

## صندوق أدوات الدفعات (دوس .BAT)

قائمة CHOICE مع ERRORLEVEL، وملف دفعات ثانٍ يُستدعى بمعامل، وملاحظات تُحفظ في NOTES.TXT، وحلقات FOR و DIR.

### ماذا يعرض

* CHOICE /C و ERRORLEVEL تُختبر من الأعلى للأدنى
* CALL NOTES.BAT ADD|SHOW مع `%1` و IF EXIST / NOT EXIST
* إعادة التوجيه `>` و`>>` و TYPE ومتغيرات SET و FOR %%N IN (...)
* "بناء" ملفات الدفعات في البيئة يفحص كل أهداف GOTO و CALL

### التشغيل والبناء والنشر

Ctrl+F5 يشغل MAIN.BAT في DOSBox-X (COMMAND.COM). المفاتيح 1-6.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
