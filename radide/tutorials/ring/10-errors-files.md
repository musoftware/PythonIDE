# الدرس 10: الأخطاء والملفات

**في هذا الدرس ستتعلم:**

- أنواع الأخطاء، والتقاط أخطاء التشغيل بـ `try ... catch ... done`.
- إطلاق خطأ بنفسك بالدالة `raise()`.
- الكتابة في الملفات والقراءة منها: `write` و`read` و`fopen` و`fputs`.
- حفظ بيانات منظمة في ملف ثم قراءتها.

## نوعان من الأخطاء

1. **أخطاء الكتابة** (تبدأ رموزها بـ `C` أو `S`): مثل نسيان `ok`. تكتشفها Ring **قبل** التشغيل، والـ IDE تعرضها في **Error List** (قائمة الأخطاء) وأنت تكتب.
2. **أخطاء التشغيل** (تبدأ بـ `R`): تحدث **أثناء** التشغيل، مثل القسمة على صفر أو الوصول إلى عنصر غير موجود في قائمة. هذه يمكن التقاطها ومعالجتها.

## التقاط الأخطاء: `try ... catch ... done`

```ring
try
    كود قد يحدث فيه خطأ
catch
    ماذا نفعل إذا حدث خطأ
done
```

بدون `try` يتوقف البرنامج عند أول خطأ تشغيل. ومعها يقفز التنفيذ إلى `catch`، ونجد وصف الخطأ في المتغير `cCatchError`:

```ring run
aList = [10, 20, 30]
try
    see aList[5]
catch
    see "حدث خطأ: " + cCatchError + nl
done
see "البرنامج مستمر بشكل طبيعي" + nl
```

```text output
حدث خطأ: Error (R2) : Array Access (Index out of range)
البرنامج مستمر بشكل طبيعي
```

> **تشبيه:** `try` مثل شبكة الأمان تحت لاعب السيرك: إذا سقط، تلتقطه الشبكة (`catch`) بدل أن يرتطم بالأرض ويتوقف العرض.

### مثال: قسمة آمنة

```ring run
see safeDivide(10, 2) + nl
see safeDivide(10, 0) + nl

func safeDivide a, b
    try
        return "" + (a / b)
    catch
        return "لا يمكن القسمة على صفر"
    done
```

```text output
5
لا يمكن القسمة على صفر
```

## إطلاق خطأ بنفسك: `raise`

أحيانًا تريد أنت أن تعلن عن خطأ، مثل إدخال غير منطقي. الدالة `raise("الرسالة")` تطلق خطأ يمكن التقاطه:

```ring run
try
    withdraw(1000, 300)
    withdraw(100, 300)
catch
    see "تعذّرت العملية: " + cCatchError + nl
done

func withdraw nBalance, nAmount
    if nAmount > nBalance
        raise("الرصيد لا يكفي")
    ok
    see "تم سحب " + nAmount + "، والباقي " + (nBalance - nAmount) + nl
```

```text output
تم سحب 300، والباقي 700
تعذّرت العملية: الرصيد لا يكفي
```

## الملفات: الطريقة السهلة

| الدالة | العمل |
|---|---|
| `write(cFile, cText)` | ينشئ الملف (أو يمسح ما فيه) ويكتب النص |
| `read(cFile)` | يقرأ الملف كله ويُرجعه نصًا |
| `fexists(cFile)` | هل الملف موجود؟ (`1` أو `0`) |
| `remove(cFile)` | يحذف الملف |

```ring run
write("notes.txt", "اشترِ خبزًا" + nl + "ذاكر Ring" + nl)
see "هل الملف موجود؟ " + fexists("notes.txt") + nl
cContent = read("notes.txt")
see cContent
aLines = str2list(cContent)
see "عدد الأسطر: " + len(aLines) + nl
remove("notes.txt")
```

```text output
هل الملف موجود؟ 1
اشترِ خبزًا
ذاكر Ring
عدد الأسطر: 2
```

الملف يُنشأ في **المجلد الحالي** للبرنامج، وفي الـ IDE هو مجلد المشروع. ويمكنك إعطاء مسار كامل مثل `"C:/Data/notes.txt"` (استخدم `/` أو `\\`).

## الإضافة إلى آخر الملف: `fopen` و`fputs`

`write` تمسح الملف القديم. لإضافة أسطر دون مسح، نفتح الملف بالوضع `"a"` (append):

| الوضع | المعنى |
|---|---|
| `"r"` | قراءة |
| `"w"` | كتابة (يمسح القديم) |
| `"a"` | إضافة إلى الآخر |

```ring run
write("log.txt", "بدأ البرنامج" + nl)
fp = fopen("log.txt", "a")
fputs(fp, "تم حفظ الملف" + nl)
fputs(fp, "انتهى البرنامج" + nl)
fclose(fp)
see read("log.txt")
remove("log.txt")
```

```text output
بدأ البرنامج
تم حفظ الملف
انتهى البرنامج
```

> **مهم:** لا تنسَ `fclose(fp)` بعد الانتهاء، وإلا قد لا تُحفظ البيانات كاملة.

## حفظ بيانات منظمة

نحفظ كل سجل في سطر، والحقول مفصولة بفاصلة، ثم نقرؤها بالطريقة التي تعلمناها في درس النصوص:

```ring run
aStudents = [["علي", 90], ["سارة", 95], ["يوسف", 78]]

# الحفظ
cText = ""
for aRow in aStudents
    cText += aRow[1] + "," + aRow[2] + nl
next
write("students.csv", cText)

# القراءة
nSum = 0
for cLine in str2list(read("students.csv"))
    aParts = str2list(substr(cLine, ",", nl))
    see aParts[1] + " حصل على " + aParts[2] + nl
    nSum += number(aParts[2])
next
see "المجموع: " + nSum + nl
remove("students.csv")
```

```text output
علي حصل على 90
سارة حصل على 95
يوسف حصل على 78
المجموع: 263
```

### قراءة ملف قد لا يكون موجودًا

```ring run
try
    cData = read("missing.txt")
catch
    see "تعذّر فتح الملف: " + cCatchError + nl
done
```

```text output
تعذّر فتح الملف: Error (R35) : Can't create/open the file
```

والأفضل أن تتحقق قبل القراءة: `if fexists("missing.txt") ... ok`.

## أخطاء شائعة

- **نسيان `done`:** جملة `try` تنتهي بـ `done` وليس `ok` أو `end`.
- **استخدام `write` للإضافة:** فيُمسح ما كان في الملف. استخدم `fopen(..., "a")`.
- **نسيان `fclose`.**
- **الشرطة المائلة في المسار:** `"C:\new\file.txt"` قد تعمل، لكن `/` أوضح وأضمن: `"C:/new/file.txt"`.

## تمارين

### التمرين 1: عمر آمن

اكتب دالة `checkAge(n)` تطلق خطأ بالرسالة «عمر غير صحيح» إذا كان `n` سالبًا أو أكبر من 150، وإلا تطبع «عمر مقبول». جرّبها على `30` ثم `-5`.

```ring exercise
try
    checkAge(30)
    checkAge(-5)
catch
    see cCatchError + nl
done

func checkAge n
    # أكمل
```

```ring solution
try
    checkAge(30)
    checkAge(-5)
catch
    see cCatchError + nl
done

func checkAge n
    if n < 0 or n > 150
        raise("عمر غير صحيح")
    ok
    see "عمر مقبول: " + n + nl
```

```text output
عمر مقبول: 30
عمر غير صحيح
```

### التمرين 2: عدّاد التشغيل

احفظ في الملف `count.txt` عدد مرات التشغيل: إذا لم يكن الملف موجودًا ابدأ من 0. شغّل المنطق 3 مرات في حلقة، ثم اطبع المحتوى الأخير واحذف الملف.

```ring exercise
for i = 1 to 3
    # اقرأ العدد (أو 0)، زِده 1، اكتبه في الملف
next
see "عدد مرات التشغيل: " + read("count.txt") + nl
remove("count.txt")
```

```ring solution
for i = 1 to 3
    nCount = 0
    if fexists("count.txt")
        nCount = number(read("count.txt"))
    ok
    nCount++
    write("count.txt", "" + nCount)
next
see "عدد مرات التشغيل: " + read("count.txt") + nl
remove("count.txt")
```

```text output
عدد مرات التشغيل: 3
```

## اختبر نفسك

```quiz
{"question": "بأي كلمة تنتهي جملة try في Ring؟", "choices": ["ok", "end", "done", "next"], "answer": 2, "explanation": "try ... catch ... done."}
```

```quiz
{"question": "أين نجد وصف الخطأ داخل catch؟", "choices": ["في المتغير cCatchError", "في المتغير error", "لا يمكن معرفته", "في الملف errors.txt"], "answer": 0, "explanation": "Ring تضع وصف الخطأ في cCatchError."}
```

```quiz
{"question": "كيف تضيف سطرًا إلى آخر ملف دون مسح محتواه؟", "choices": ["write", "fopen بالوضع \"a\" ثم fputs", "read", "remove ثم write"], "answer": 1, "explanation": "الوضع a يعني append: الإضافة إلى آخر الملف."}
```

## الخلاصة

- أخطاء C/S قبل التشغيل، وأخطاء R أثناءه.
- `try ... catch ... done` للالتقاط، و`cCatchError` للوصف، و`raise()` للإطلاق.
- `write` و`read` و`fexists` و`remove` للملفات ببساطة.
- `fopen` و`fputs` و`fclose` للإضافة والتحكم الدقيق.
