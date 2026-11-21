# الدرس 4: لغة C مع Open Watcom وذاكرة الشاشة

**في هذا الدرس ستتعلم:**

- مشروع **Turbo C-style** يبنيه المترجم الحر **Open Watcom** لبرامج DOS بـ 16 بت.
- الإدخال والإخراج بـ `printf` و`scanf`.
- دوال `conio.h` بأسلوب Turbo C: `clrscr` و`gotoxy` و`textcolor` و`cprintf` و`getch`.
- الكتابة مباشرة في ذاكرة الشاشة `B800` بمؤشر بعيد (`far`).
- استدعاء مقاطعات البيوس من C بـ `int86`.
- نماذج الذاكرة (small و large).

## Turbo C و Open Watcom

**Turbo C** من Borland (1987) كان مترجم C المفضل على DOS، وبعده Borland C++. وكلاهما تجاري. RAD IDE تستخدم **Open Watcom C** الحر، وهو المترجم نفسه الذي بُنيت به ألعاب شهيرة في التسعينيات، وتضيف عليه ملفات رأس من كتابتها تحاكي إضافات Turbo C:

- `tcconio.h`: `clrscr` و`gotoxy` و`textcolor` و`textbackground` و`cprintf` الملون و`wherex`... ويُضاف تلقائيًّا عندما يستعمل برنامجك هذه الدوال.
- `graphics.h`: جزء من مكتبة الرسوم BGI (خطوط ودوائر ومستطيلات بـ 16 لونًا) دون ملفات `.BGI`.

أنشئ مشروعًا من **File > New Project...** ثم **DOS** ثم **Turbo C-style** والقالب **Hello (Turbo C style)**. الملف الرئيسي `MAIN.C`.

## مرحبًا بـ C

<!-- test: {"keys": "Ali~2000~", "screen": true} -->

```dos-c run
#include <stdio.h>

int main(void)
{
    char name[40];
    int year;
    printf("Your name: ");
    scanf("%39s", name);
    printf("Year of birth: ");
    scanf("%d", &year);
    printf("Hello, %s! In 2030 you will be %d.\n", name, 2030 - year);
    return 0;
}
```

```text output
Your name: Ali
Year of birth: 2000
Hello, Ali! In 2030 you will be 30.
```

- `#include <stdio.h>` مكتبة الإدخال والإخراج القياسية.
- `printf` يطبع بقالب: `%s` نص، و`%d` عدد صحيح، و`\n` سطر جديد.
- `scanf("%d", &year)` يقرأ عددًا إلى المتغير؛ و`&` تعني «عنوان المتغير».
- `int main(void)` نقطة البداية، و`return 0` يعني أن البرنامج انتهى بنجاح.

## conio بأسلوب Turbo C

<!-- test: {"keys": "x"} -->

```dos-c run
#include <conio.h>

int main(void)
{
    int i;
    textbackground(BLUE);
    clrscr();
    textcolor(YELLOW);
    gotoxy(32, 2);
    cprintf("Turbo C style");
    for (i = 1; i <= 3; i++) {
        textcolor(WHITE);
        gotoxy(10, 3 + i * 2);
        cprintf("Item %d", i);
    }
    textcolor(LIGHTGREEN);
    gotoxy(10, 12);
    cprintf("Press a key...");
    getch();
    textcolor(LIGHTGRAY);
    textbackground(BLACK);
    gotoxy(1, 14);
    cprintf("Bye!");
    return 0;
}
```

```text output
                               Turbo C style


         Item 1

         Item 2

         Item 3


         Press a key...

Bye!
```

`getch()` ينتظر مفتاحًا دون أن يظهره، و`kbhit()` يخبرك هل ضُغط مفتاح دون انتظار، تمامًا مثل `ReadKey` و`KeyPressed` في باسكال.

## الكتابة في ذاكرة الشاشة مباشرة

أسرع طريقة للرسم في وضع النص: ذاكرة الشاشة تبدأ عند `B800:0000`، وكل خانة كلمة من بايتين: الحرف ثم لونه. الخانة في السطر `y` والعمود `x` (من الصفر) رقمها `y * 80 + x`:

<!-- test: {"keys": "x"} -->

```dos-c run
#include <stdio.h>
#include <conio.h>

unsigned short far *screen = (unsigned short far *)0xB8000000L;

void put_text(int x, int y, const char *s, unsigned char attr)
{
    while (*s) {
        screen[y * 80 + x] = (unsigned short)(attr << 8) | (unsigned char)*s;
        s++;
        x++;
    }
}

int main(void)
{
    int x;
    clrscr();
    for (x = 20; x < 60; x++)
        screen[5 * 80 + x] = (0x1E << 8) | 0xCD;     /* yellow on blue double line */
    put_text(28, 6, " Direct video memory ", 0x4F);  /* white on red */
    put_text(28, 8, "Press a key", 0x0A);            /* light green */
    getch();
    return 0;
}
```

```text output
                    ════════════════════════════════════════
                             Direct video memory

                            Press a key
```

- `far` مؤشر «بعيد» فيه المقطع والإزاحة معًا: `0xB8000000L` يعني `B800:0000`. هذا خاص ببرامج 16 بت على DOS.
- اللون بايت واحد: الأربع بتات العليا للخلفية والسفلى للحرف. `0x1E` = خلفية زرقاء (1) وحرف أصفر (E)، و`0x4F` = أحمر وأبيض.
- `0xCD` هو حرف `═` في CP437.

> **تنبيه:** الكتابة في الذاكرة مباشرة لا تحرّك المؤشر ولا تمر بـ `stdout`، لذلك لا يظهر شيء منها إن وجّهت المخرجات إلى ملف. هذا ما تفعله برامج المصمم في الدرس 6 لتبدو الشاشة كاملة في لحظة.

## مقاطعات البيوس من C

`int86` من `dos.h` (أو `i86.h`) يضع القيم في المسجلات ثم يستدعي المقاطعة. هنا نسأل البيوس عن وضع الشاشة الحالي (`INT 10h`، الدالة `AH = 0Fh`):

```dos-c run
#include <stdio.h>
#include <dos.h>

int main(void)
{
    union REGS r;
    r.h.ah = 0x0F;              /* get video mode */
    int86(0x10, &r, &r);
    printf("Video mode %d, %d columns\n", r.h.al, r.h.ah);
    return 0;
}
```

```text output
Video mode 3, 80 columns
```

الوضع 3 هو وضع النص الملوّن 80 × 25. مرّر الفأرة فوق `0x10` أو `0x0F` في محرر RAD IDE: تظهر نافذة بوظيفة المقاطعة ومسجلات الدخول والخروج بالعربية والإنجليزية، ومن **Tools > Retro > DOS Programming > DOS Interrupt Reference...** تتصفح جداول `INT 21h` و`10h` و`16h` و`33h` و`1Ah` كلها.

## نماذج الذاكرة

في برامج 16 بت لا يزيد المقطع الواحد عن 64 كيلوبايت، فيختار المترجم «نموذجًا»:

| النموذج | الكود | البيانات |
|---|---|---|
| tiny | مقطع واحد للكل (ملف `.COM`) | |
| small | 64 ك | 64 ك |
| medium | أكثر من 64 ك | 64 ك |
| compact | 64 ك | أكثر من 64 ك |
| large | أكثر من 64 ك | أكثر من 64 ك |

القيمة الافتراضية **small**، وتغيّرها من **Project > DOS Project Settings...**. البرامج التي تحمّل صورًا أو مصفوفات كبيرة تحتاج **large**.

## خطأ في البناء

<!-- test: {"error_line": 5} -->

```dos-c run
#include <stdio.h>

int main(void)
{
    printf("%d\n", total);
    return 0;
}
```

يظهر في **Error List** خطأ Open Watcom `Symbol 'total' has not been declared` عند `MAIN.C` السطر 5.

```quiz
{"question": "أين تقع الخانة في السطر 2 والعمود 10 (من الصفر) في ذاكرة الشاشة كمصفوفة كلمات؟", "choices": ["2 * 80 + 10 = 170", "10 * 25 + 2 = 252", "2 + 10 = 12"], "answer": 0, "explanation": "كل سطر 80 خانة، فالرقم = y * 80 + x = 170 (والعنوان بالبايت ضعف ذلك: 340)."}
```

```quiz
{"question": "ما معنى السمة 0x1E؟", "choices": ["حرف أزرق على خلفية صفراء", "حرف أصفر على خلفية زرقاء", "حرف أبيض يومض"], "answer": 1, "explanation": "البتات العليا للخلفية (1 = أزرق) والسفلى للحرف (E = أصفر)."}
```
