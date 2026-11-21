# الدرس 3: باسكال ووحدة Crt

**في هذا الدرس ستتعلم:**

- مشروع **Turbo Pascal-style** يبنيه المترجم الحر Free Pascal لمعالج 8086.
- بنية برنامج باسكال: `program` و`var` و`begin ... end.`
- الإجراءات والدوال والسجلات (`record`) والمصفوفات.
- وحدة **Crt**: مسح الشاشة والألوان وتحريك المؤشر وقراءة المفاتيح والصوت.

## Turbo Pascal و Free Pascal

أصدرت شركة Borland عام 1983 **Turbo Pascal**: محرر ومترجم سريع جدًّا في ملف واحد، فصار من أشهر أدوات DOS، وتعلّم عليه طلاب الجامعات لسنوات. Turbo Pascal برنامج تجاري، لذلك تستخدم RAD IDE المترجم الحر **Free Pascal** (الإصدار 3.2.2) بنسخته التي تُنتج برامج DOS بـ 16 بت (الهدف `i8086-msdos`)، مع الوضع `-Mtp` المتوافق مع Turbo Pascal. يعمل المترجم على ويندوز مباشرة، والناتج ملف `.EXE` يعمل في DOSBox-X.

أنشئ المشروع: **File > New Project...** ثم **DOS** ثم **Turbo Pascal-style**، والقالب **Hello (Turbo Pascal style)**. الملف الرئيسي `MAIN.PAS`.

## أول برنامج

<!-- test: {"keys": "Sara~30~", "screen": true} -->

```dos-pascal run
program Hello;
var
  Name: string;
  Age: Integer;
begin
  Write('Your name: ');
  ReadLn(Name);
  Write('Your age: ');
  ReadLn(Age);
  WriteLn('Hello, ', Name, '!');
  WriteLn('Next year you will be ', Age + 1, '.');
end.
```

```text output
Your name: Sara
Your age: 30
Hello, Sara!
Next year you will be 31.
```

- كل برنامج يبدأ بـ `program الاسم;` وينتهي بـ `end.` (بنقطة).
- المتغيرات تُعرَّف في قسم `var` بنوعها: `Integer` عدد صحيح، و`Real` عشري، و`string` نص، و`Char` حرف، و`Boolean` صح أو خطأ.
- `Write` يطبع دون نزول سطر، و`WriteLn` ينزل سطرًا، و`ReadLn` يقرأ سطرًا يكتبه المستخدم.
- الإسناد بـ `:=` والمقارنة بـ `=`. وباسكال لا يفرق بين الحروف الكبيرة والصغيرة.

## الإجراءات والدوال والسجلات

```dos-pascal run
program Grades;
type
  TStudent = record
    Name: string[12];
    Mark: Integer;
  end;
var
  S: array[1..3] of TStudent;
  I: Integer;

function Grade(M: Integer): Char;
begin
  if M >= 90 then Grade := 'A'
  else if M >= 75 then Grade := 'B'
  else if M >= 60 then Grade := 'C'
  else Grade := 'F';
end;

procedure Show(const St: TStudent);
begin
  WriteLn(St.Name: 8, St.Mark: 5, '  ', Grade(St.Mark));
end;

begin
  S[1].Name := 'Omar';  S[1].Mark := 92;
  S[2].Name := 'Laila'; S[2].Mark := 78;
  S[3].Name := 'Yusuf'; S[3].Mark := 55;
  for I := 1 to 3 do
    Show(S[I]);
end.
```

```text output
    Omar   92  A
   Laila   78  B
   Yusuf   55  F
```

- `type` يعرّف أنواعًا جديدة. `record` يجمع عدة حقول في متغير واحد، ونصل إليها بالنقطة `S[1].Name`.
- `array[1..3] of TStudent` مصفوفة تبدأ من 1.
- الدالة `function` تُرجع قيمتها بالإسناد إلى اسمها، والإجراء `procedure` لا يُرجع شيئًا.
- `St.Name: 8` يطبع النص في عرض 8 خانات (محاذاة لليمين)، و`const` في المعامل يمنع تعديله ويوفر النسخ.

## وحدة Crt

`uses Crt;` تفتح أدوات الشاشة ولوحة المفاتيح التي جعلت برامج Turbo Pascal ملوّنة وتفاعلية:

<!-- test: {"keys": "z"} -->

```dos-pascal run
program CrtDemo;
uses Crt;
var
  K: Char;
  I: Integer;
begin
  TextBackground(Blue);
  ClrScr;
  TextColor(Yellow);
  GotoXY(30, 3);
  Write('Turbo Pascal style');
  TextColor(White);
  for I := 1 to 3 do
  begin
    GotoXY(10, 4 + I * 2);
    Write('Line ', I, ' at row ', 4 + I * 2);
  end;
  GotoXY(10, 14);
  Write('Press a key...');
  K := ReadKey;
  GotoXY(10, 16);
  TextColor(LightGreen);
  Write('You pressed ', K);
  NormVideo;
  WriteLn;
end.
```

```text output
                             Turbo Pascal style


         Line 1 at row 6

         Line 2 at row 8

         Line 3 at row 10



         Press a key...

         You pressed z
```

| الإجراء | العمل |
|---|---|
| `ClrScr` | يمسح الشاشة بلون الخلفية الحالي |
| `GotoXY(عمود, سطر)` | ينقل المؤشر (العدّ من 1؛ لاحظ: العمود أولًا) |
| `TextColor(لون)` و`TextBackground(لون)` | الألوان: `Black` و`Blue` و`Green` و`Red` و`Yellow` و`White` و`LightGreen`... |
| `ReadKey` | ينتظر مفتاحًا ويُرجعه دون أن يظهر على الشاشة |
| `KeyPressed` | هل في لوحة المفاتيح مفتاح ينتظر؟ (دون انتظار) |
| `Delay(ms)` | انتظار بالملّي ثانية |
| `Sound(Hz)` و`NoSound` | صفّارة الحاسوب (PC Speaker) |
| `NormVideo` | يعيد الألوان العادية |

وحدة Crt تكتب في ذاكرة الشاشة مباشرة، لذلك يرى RAD IDE النص على شاشة DOSBox-X حتى في التشغيل الملتقط.

## حلقة لعبة صغيرة

`KeyPressed` مع `ReadKey` هما قلب كل لعبة نصية: تتحرك الأشياء والبرنامج يراقب المفاتيح. المفاتيح الخاصة (الأسهم) تُرجع أولًا `#0` ثم رمزها:

```dos-pascal
repeat
  if KeyPressed then
  begin
    K := ReadKey;
    if K = #0 then
      case ReadKey of
        #72: Dec(Y);   { up }
        #80: Inc(Y);   { down }
        #75: Dec(X);   { left }
        #77: Inc(X);   { right }
      end;
  end;
  GotoXY(X, Y); Write('@');
  Delay(50);
until K = #27;      { Esc }
```

## خطأ في البناء

<!-- test: {"error_line": 5} -->

```dos-pascal run
program Broken;
var
  Count: Integer;
begin
  Cout := 3;
  WriteLn(Count);
end.
```

يعرض **Error List** رسالة Free Pascal `Identifier not found "Cout"` عند `MAIN.PAS` السطر 5. انقرها نقرًا مزدوجًا للانتقال إليها.

> **تمرين:** اكتب برنامجًا بوحدة Crt يرسم إطارًا بالحروف `#201` و`#205` و`#187` و`#186` و`#200` و`#188` حول كلمة `PASCAL` في وسط الشاشة، ثم ينتظر مفتاحًا.

```quiz
{"question": "في وحدة Crt، ما ترتيب معاملي GotoXY؟", "choices": ["السطر ثم العمود", "العمود ثم السطر", "بالبكسل"], "answer": 1, "explanation": "GotoXY(X, Y): العمود أولًا ثم السطر، والعدّ من 1. أما LOCATE في QBasic فالسطر أولًا."}
```

```quiz
{"question": "ماذا تُرجع ReadKey أولًا عند الضغط على سهم؟", "choices": ["#0 ثم رمز السهم في الاستدعاء التالي", "رمز ASCII للسهم", "لا شيء"], "answer": 0, "explanation": "المفاتيح الموسعة تأتي على دفعتين: #0 ثم رمز المسح (72 لأعلى، 80 لأسفل، 75 لليسار، 77 لليمين)."}
```
