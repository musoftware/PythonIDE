# الدرس 7: التطوير البعيد: SSH و WSL والحاويات

**في هذا الدرس ستتعلم:**

- معنى **التطوير البعيد**: البيئة على جهازك، والملفات والتشغيل على جهاز آخر.
- الاتصال بخادم لينكس عبر **SSH** من **File > Open Remote > Connect to SSH Host...**.
- فتح مجلد داخل **WSL** (لينكس داخل ويندوز).
- العمل داخل **حاوية تطوير** (Dev Container).
- نافذة **Remote Explorer** والطرفية البعيدة والتشغيل والبناء على الخادم.

## جهاز التحكم عن بعد

تخيّل أنك تقود سيارة لعبة **بجهاز تحكم عن بعد**: يداك على الجهاز في غرفتك، والسيارة تتحرك في غرفة أخرى.
في التطوير البعيد: المحرر والقوائم والمصمم على جهازك (ويندوز)، أما الملفات والأوامر والتشغيل فعلى **جهاز آخر**: خادم في الشركة، أو خادم سحابي، أو لينكس داخل جهازك نفسه.

لماذا؟ لأن موقعك سيعمل في النهاية على خادم لينكس، أو لأن الخادم أقوى من جهازك، أو لأن المشروع يحتاج أدوات لا تعمل إلا على لينكس.

## قائمة File > Open Remote

| الأمر | الاسم العربي | المعنى |
|---|---|---|
| **Connect to SSH Host...** | الاتصال بمضيف SSH | خادم لينكس أو ماك عبر الشبكة |
| **Recent SSH Hosts** | مضيفات SSH الحديثة | آخر الخوادم التي اتصلت بها |
| **Open WSL Folder...** | فتح مجلد WSL... | مجلد في توزيعة لينكس داخل ويندوز |
| **Open Folder in Dev Container...** | فتح مجلد في حاوية تطوير | مجلد يعمل داخل حاوية Docker |
| **Remote Explorer** | المستكشف البعيد | شجرة ملفات الجهاز البعيد |
| **Remote Terminal** | الطرفية البعيدة | سطر أوامر على الجهاز البعيد |
| **Run on Remote** / **Build on Remote** | التشغيل / البناء على الخادم البعيد | تنفيذ أمر التشغيل أو البناء هناك |
| **Run Remote Command...** / **Stop Remote Command** | تنفيذ أمر بعيد / إيقافه | أي أمر تريده |
| **Reload Remote File** | إعادة تحميل الملف البعيد | قراءة الملف من الخادم من جديد |
| **Disconnect** | قطع الاتصال | |

## الاتصال عبر SSH

1. **File > Open Remote > Connect to SSH Host...**. نافذة **Connect to SSH Host**:

| الخانة | الاسم العربي | ماذا تكتب |
|---|---|---|
| **Saved:** | | اختر اتصالًا محفوظًا أو مضيفًا من ملف `~/.ssh/config`، أو **(new connection)** |
| **Host:** | المضيف | مثل `example.com` أو `192.168.1.10` |
| **Port:** | المنفذ | عادةً `22` |
| **User:** | المستخدم | اسم حسابك على الخادم |
| **Sign in with:** | تسجيل الدخول باستخدام | **Password** (كلمة مرور) أو **Private key** (مفتاح خاص، مع **Key file:** و **Passphrase:** إن كان مشفرًا) أو **SSH agent / default keys** |
| **Remember the password / passphrase in Windows Credential Manager** | تذكّر كلمة المرور في مدير بيانات اعتماد Windows | تُحفظ في خزنة ويندوز الآمنة، **لا** في ملف الإعدادات |
| **Folder:** | المجلد | المجلد الذي تفتحه، و `~` = مجلدك الرئيسي |

2. أول مرة تتصل بخادم، تعرض البيئة **بصمة مفتاحه** (SHA256 fingerprint) وتطلب قبولها. قارنها بما أعطاك مدير الخادم؛ هذا يحميك من خادم مزيّف.
3. بعد الاتصال تظهر نافذة **Remote Explorer**، واسم الخادم في شريط الحالة.

> 💡 الخادم يحتاج إلى SFTP وسطر أوامر POSIX (لينكس أو ماك أو BSD)، وهذا متوفر في كل خوادم لينكس تقريبًا.

## نافذة Remote Explorer

- **شريط المسار** وشجرة الملفات (تُحمَّل عند فتح كل مجلد).
- أزرار **Connect** و **Refresh** و **Run** و **Build**، ومربع **Search the remote folder** للبحث داخل ملفات الخادم.
- **بالزر الأيمن**: **New File...** و **New Folder...** و **Upload Files...** و **Download...** و **Rename...** و **Delete** و **Open Terminal Here** و **Run Command Here...** و **Search in Folder...** و **Disconnect**.
- **انقر ملفًا مرتين** ليُفتح في تبويب عادي. عند **الحفظ** (`Ctrl+S`) يُرفع إلى الخادم، والبيئة تتحقق أولًا أن أحدًا لم يعدّله هناك في أثناء ذلك.
- إن تغيّر ملف مفتوح على الخادم، تعيد البيئة تحميله تلقائيًا.

**التشغيل والبناء:** أول مرة تضغط **Run** أو **Build** تفتح نافذة **Run / Build on ...** لتكتب **Run command:** (مثل `python3 app.py`) و **Build command:** (مثل `make`). المخرجات تظهر في نافذة **Output**.

## WSL: لينكس داخل ويندوز

WSL (Windows Subsystem for Linux) يشغّل توزيعة لينكس (مثل Ubuntu) داخل ويندوز. ثبّتها مرة واحدة بالأمر `wsl --install` في طرفية بصلاحيات المسؤول.

1. **File > Open Remote > Open WSL Folder...**. نافذة **Open WSL Folder**:
   - **Distribution:** (التوزيعة) مثل `Ubuntu`، والافتراضية عليها **(default)**.
   - **Folder:** (المجلد) مثل `/home/sara/project`.
2. الملفات تُفتح عبر `\\wsl$`، أما الطرفية و Run و Build والبحث فتعمل **داخل لينكس** (`wsl -d Ubuntu`).

## حاويات التطوير (Dev Containers)

**الحاوية** صندوق مغلق فيه نظام وأدوات بإصدارات محددة. كل أعضاء الفريق يعملون في الصندوق نفسه، فتختفي جملة "عندي يعمل وعندك لا!".

- مجلد المشروع يحتوي ملف `.devcontainer/devcontainer.json` يصف الصندوق.
- **File > Open Remote > Open Folder in Dev Container...**: تشغّل البيئة الحاوية بأداة `docker` (تبنيها أول مرة)، وكل الأوامر تعمل داخلها.
- يلزمك **Docker Desktop** مثبتًا ويعمل.
- لإنشاء الملف تلقائيًا: **Tools > Docker > Generate Dockerfile / Compose / Dev Container...** (الدرس القادم).

مثال لملف `devcontainer.json` بسيط لمشروع Python. هذا السكربت يكتبه ثم يقرؤه ويتحقق من صحته كما تفعل البيئة قبل تشغيل الحاوية:

```powershell run
$dir = Join-Path $PWD '.devcontainer'
New-Item -ItemType Directory $dir -Force | Out-Null
@'
{
  "name": "Shop (Python 3.12)",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "forwardPorts": [8000],
  "postCreateCommand": "pip install -r requirements.txt"
}
'@ | Set-Content (Join-Path $dir 'devcontainer.json')

$cfg = Get-Content (Join-Path $dir 'devcontainer.json') -Raw | ConvertFrom-Json
Write-Output "name:  $($cfg.name)"
Write-Output "image: $($cfg.image)"
Write-Output "ports: $($cfg.forwardPorts -join ', ')"
Write-Output "after create: $($cfg.postCreateCommand)"
```

```text output
name:  Shop (Python 3.12)
image: mcr.microsoft.com/devcontainers/python:3.12
ports: 8000
after create: pip install -r requirements.txt
```

| الحقل | المعنى |
|---|---|
| `name` | اسم الحاوية |
| `image` | الصورة الجاهزة التي تبدأ منها (هنا Python 3.12) |
| `forwardPorts` | منافذ تصل إليها من متصفح جهازك (موقع على المنفذ 8000) |
| `postCreateCommand` | أمر يعمل مرة بعد إنشاء الحاوية (تثبيت المكتبات) |

## أيها أختار؟

| الموقف | الاختيار |
|---|---|
| موقعك يعمل على خادم لينكس وتريد تعديله هناك | **SSH** |
| تريد أدوات لينكس على جهازك دون جهاز آخر | **WSL** |
| تريد أن يعمل كل الفريق بالإصدارات نفسها تمامًا | **Dev Container** |

## أخطاء شائعة

- **"Connection refused" أو مهلة:** عنوان أو منفذ خطأ، أو الخادم يمنع SSH. جرّب `ssh user@host` في **View > Terminal** أولًا.
- **قبول بصمة مفتاح دون التحقق:** قد تكون متصلًا بخادم مزيّف. قارن البصمة.
- **كلمة المرور في ملف المشروع:** استخدم خانة **Remember** (خزنة ويندوز) أو المفاتيح الخاصة.
- **Dev Container لا يعمل:** Docker Desktop غير مشغّل. شغّله وانتظر حتى يصبح جاهزًا.
- **WSL غير مثبت:** `wsl --install` ثم أعد تشغيل الجهاز.

## تمرين

### مهمة عملية

1. إن كان لديك WSL: **File > Open Remote > Open WSL Folder...**، واختر التوزيعة ومجلدك الرئيسي.
2. في **Remote Explorer**: بالزر الأيمن **New File...** باسم `hello.py`، واكتب `print("hello from Linux")` واحفظ.
3. اضغط **Run** واكتب أمر التشغيل `python3 hello.py`، واقرأ النتيجة في **Output**.
4. افتح **File > Open Remote > Remote Terminal** واكتب `uname -a`.
5. **File > Open Remote > Disconnect**.

## اختبر نفسك

```quiz
{"question": "في التطوير البعيد عبر SSH، أين تعمل الأوامر وأين المحرر؟", "choices": ["الاثنان على جهازك", "المحرر على جهازك، والملفات والأوامر على الخادم", "الاثنان على الخادم", "على GitHub"], "answer": 1, "explanation": "مثل جهاز التحكم عن بعد: يداك هنا والسيارة هناك."}
```

```quiz
{"question": "أين تحفظ البيئة كلمة مرور SSH عند اختيار Remember؟", "choices": ["في ملف المشروع", "في مدير بيانات اعتماد Windows", "في GitHub", "لا تحفظها أبدًا"], "answer": 1, "explanation": "خزنة ويندوز الآمنة، لا ملف الإعدادات."}
```

```quiz
{"question": "ما فائدة Dev Container لفريق؟", "choices": ["تسريع الإنترنت", "يعمل الجميع في بيئة واحدة بالأدوات والإصدارات نفسها", "حذف ملفات Git", "تصميم النماذج"], "answer": 1, "explanation": "ملف devcontainer.json يصف الصندوق نفسه للجميع."}
```

## الخلاصة

- **File > Open Remote**: **Connect to SSH Host...** للخوادم، و **Open WSL Folder...** للينكس داخل ويندوز، و **Open Folder in Dev Container...** للحاويات.
- **Remote Explorer**: ملفات الخادم، والحفظ يرفع، و **Run** / **Build** والطرفية البعيدة على الخادم.
- الأمان: تحقق من بصمة المفتاح، واحفظ الأسرار في خزنة ويندوز لا في الملفات.
