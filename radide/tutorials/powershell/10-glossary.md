# الدرس 10: قاموس المصطلحات (إنجليزي - عربي)

أهم المصطلحات التي مرت بك في دورة PowerShell، مع مثال لكل منها. ارجع إلى هذه الصفحة كلما نسيت معنى كلمة.

## أساسيات

| English | العربية | مثال في PowerShell |
|---|---|---|
| script | سكربت (برنامج نصي) | ملف `.ps1` |
| variable | متغير | `$name = "منى"` |
| string (expandable / literal) | نص (يستبدل المتغيرات / حرفي) | `"Hi $name"` / `'Hi $name'` |
| integer / double | عدد صحيح / عدد عشري | `[int]42` / `[double]3.5` |
| boolean | قيمة منطقية | `$true` / `$false` |
| null | لا شيء | `$null` |
| type cast | تحويل النوع | `[int]"12"` |
| comment | تعليق | `# ...` و`<# ... #>` |
| sub-expression | تعبير داخل نص | `"$(2 + 3)"` |
| here-string | نص متعدد الأسطر | `@" ... "@` |

## التحكم

| English | العربية | مثال |
|---|---|---|
| condition | شرط | `if ($x -gt 0) { }` |
| comparison operator | عامل مقارنة | `-eq -ne -gt -lt -ge -le` |
| logical operator | عامل منطقي | `-and -or -not` |
| switch | اختيار من عدة حالات | `switch ($x) { 1 { } }` |
| loop | حلقة تكرار | `for` / `foreach` / `while` |
| range | مدى | `1..10` |
| break / continue | اخرج من الحلقة / تخطَّ للدورة التالية | |

## المجموعات

| English | العربية | مثال |
|---|---|---|
| array | مصفوفة | `@(1, 2, 3)` |
| index | فهرس (رقم العنصر) | `$a[0]` |
| hashtable | جدول تجزئة (مفتاح وقيمة) | `@{ name = "Ali" }` |
| key / value | مفتاح / قيمة | `$h.Keys` / `$h.Values` |
| custom object | كائن مخصص | `[pscustomobject]@{ }` |

## الدوال وخط الأنابيب

| English | العربية | مثال |
|---|---|---|
| function | دالة | `function Get-Area($w, $h) { }` |
| parameter | معامل | `param([int]$Count = 1)` |
| return value | القيمة المرجعة | `return $x` |
| pipeline | خط الأنابيب | يمرر ناتج أمر إلى الأمر التالي بالخط العمودي |
| current pipeline object | العنصر الحالي في الأنبوب | `$_` |
| cmdlet | أمر جاهز (Verb-Noun) | `Get-Date`، `Where-Object` |
| verb-noun | فعل-اسم (تسمية الأوامر) | `Get-Process`، `Set-Content` |
| alias | اسم مختصر | `ls` = `Get-ChildItem` |
| scope | نطاق | `$script:count` |

## الكائنات والملفات والأخطاء

| English | العربية | مثال |
|---|---|---|
| object | كائن | ما تُرجعه `Get-Process` |
| property | خاصية | `$file.Length` |
| method | دالة الكائن (طريقة) | `$s.ToUpper()` |
| path | مسار | `C:\Users\...` |
| encoding | الترميز | `-Encoding UTF8` |
| CSV | ملف قيم مفصولة بفواصل | `Export-Csv` / `Import-Csv` |
| regular expression | تعبير نمطي | `-match "\d+"` |
| exception / error | استثناء / خطأ | `throw "..."` |
| try / catch / finally | جرّب / التقط / أخيرًا | `try { } catch { }` |
| terminating error | خطأ قاطع (يوقف التنفيذ) | `-ErrorAction Stop` |
| execution policy | سياسة التنفيذ | `Set-ExecutionPolicy` |

## الواجهة الرسومية في RAD IDE

| English | العربية | مثال |
|---|---|---|
| form | نموذج (نافذة) | `Form1` |
| control | أداة / عنصر تحكم | `Button`، `TextBox`، `Label` |
| form designer | مصمم النماذج | ترسم فيه النافذة |
| Toolbox | صندوق الأدوات | منه تسحب الأدوات |
| Properties window | نافذة الخصائص | تغيّر منها `Name` و`Text` |
| event | حدث | `Click`، `Load`، `Tick` |
| event handler | معالج الحدث | `function btnOk_Click($e) { }` |
| GUI Bridge | جسر الواجهة | الـ IDE ترسم النافذة وسكربتك يستقبل الأحداث |
| designer file | ملف المصمم (مولَّد) | `Form1_designer.ps1` |
| message box | رسالة منبثقة | `MsgBox "تم"` |
| input box | مربع إدخال | `InputBox "اسمك؟"` |
| timer | مؤقت | `$tmrTick.Interval = 1000` |
| list box | قائمة | `$lstItems.AddItem("x")` |

## اختبر نفسك

```quiz
{"question": "ما معنى $_ في PowerShell؟", "choices": ["آخر خطأ", "العنصر الحالي في خط الأنابيب", "اسم السكربت", "متغير فارغ"], "answer": 1, "explanation": "$_ (أو $PSItem) هو العنصر الذي يمر الآن في الأنبوب، داخل Where-Object وForEach-Object."}
```

```quiz
{"question": "أي هذه أسماء أوامر جاهزة (cmdlets) بالصيغة الصحيحة؟", "choices": ["GetDate", "Get-Date", "date.get", "get_date"], "answer": 1, "explanation": "الأوامر الجاهزة تُسمى بصيغة فعل-اسم مفصولين بشرطة."}
```

## ماذا بعد؟

- جرّب أتمتة عمل حقيقي تكرره كل أسبوع: نسخ احتياطي لمجلد، أو إعادة تسمية صور، أو تقرير عن المساحة.
- اقرأ مساعدة أي أمر بـ `Get-Help Get-ChildItem -Examples`.
- ثبّت وحدات من **PowerShell Gallery** من القائمة **Project > Manage Packages...** في RAD IDE.
