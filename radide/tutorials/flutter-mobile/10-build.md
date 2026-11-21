# الدرس 10: بناء التطبيق: APK و App Bundle و Windows والويب

**في هذا الدرس ستتعلم:**

- تحويل مشروعك إلى ملف يثبّته الناس: `APK` لهواتف Android، و`App Bundle` لمتجر Google Play، وبرنامج Windows، وموقع ويب.
- أين تجد الملف بعد البناء.
- تغيير اسم التطبيق ورقم إصداره.

## الفرق بين «التشغيل» و«البناء»

- **التشغيل** (`F5`) نسخة **تصحيح** (debug): كبيرة الحجم وأبطأ، وفيها أدوات المطور وإعادة التحميل السريع.
- **البناء** نسخة **إصدار** (release): مضغوطة وسريعة، وهي التي ترسلها للناس.

> **تشبيه:** نسخة التصحيح مثل بروفة المسرحية: الممثلون يتوقفون ويعيدون. نسخة الإصدار هي العرض الحقيقي أمام الجمهور.

## القائمة Build > Mobile App

من القائمة **Build > Mobile App** (بناء > تطبيق موبايل):

| الأمر | الاسم العربي | الأمر الحقيقي | مكان الناتج داخل المشروع |
|---|---|---|---|
| **Android APK** | Android APK | `flutter build apk --release` | `build/app/outputs/flutter-apk/app-release.apk` |
| **Android App Bundle (Google Play)** | Android App Bundle (متجر Google Play) | `flutter build appbundle` | `build/app/outputs/bundle/release/app-release.aab` |
| **Windows EXE** | ملف Windows EXE | `flutter build windows` | مجلد `build/windows/x64/runner/Release` |
| **Web site** | موقع ويب | `flutter build web` | مجلد `build/web` |
| **Android APK (debug, faster)** | Android APK (تصحيح، أسرع) | `flutter build apk --debug` | `build/app/outputs/flutter-apk/app-debug.apk` |
| **Cancel Build** | إلغاء البناء | يوقف البناء الجاري | |

خطوات البناء:

1. احفظ كل شيء (الـ IDE يحفظ تلقائيًا قبل البناء، ويعيد توليد ملفات الشاشات).
2. اختر نوع البناء من القائمة.
3. تابع نافذة **Output**: أول بناء لـ Android يأخذ عدة دقائق (ينزّل Gradle وملفاته).
4. في النهاية يظهر السطر `Build succeeded:` ومعه مسار الملف.

> **ملحوظة:** إذا لم يكن في المشروع مجلد المنصة (`android` أو `windows` أو `web`) ينشئه الـ IDE أولًا بـ `flutter create`.

## أي نوع تختار؟

- **تجربة على هاتف صديق**: `Android APK`. أرسل الملف `app-release.apk`، وعلى الهاتف يجب السماح بتثبيت التطبيقات من مصادر غير معروفة.
- **النشر في Google Play**: `Android App Bundle`. المتجر يطلب ملف `.aab`، ويحتاج **توقيعًا** بمفتاحك الخاص (ابحث في توثيق Flutter عن "Signing the app").
- **برنامج لويندوز**: `Windows EXE`. انسخ **المجلد كله** `Release` (فيه ملف `.exe` ومكتبات بجانبه)، لا الملف `.exe` وحده.
- **موقع**: `Web site`. ارفع محتوى المجلد `build/web` إلى أي استضافة. للتجربة على جهازك:

```text
python -m http.server -d build/web
```

ثم افتح `http://localhost:8000` في المتصفح.

## اسم التطبيق ورقم الإصدار

افتح `pubspec.yaml`:

```yaml
name: flutter_app1
description: A RAD IDE Flutter app.
version: 1.0.0+1
```

- `version: 1.0.0+1`: الجزء `1.0.0` هو الإصدار الذي يراه المستخدم، و`+1` رقم البناء. **زِد رقم البناء** في كل مرة ترفع فيها نسخة جديدة إلى المتجر (`1.0.1+2`).
- عنوان التطبيق الظاهر في نافذة Windows أو تبويب المتصفح هو اسم المشروع (في `lib/main.dart` المولَّد).
- لون التطبيق الأساسي: خاصية المشروع `theme_color` (من **Project > Project Properties...**)، وإلا فاللون الافتراضي نيلي (`indigo`).

## حجم التطبيق

نسخة الإصدار أصغر بكثير من نسخة التصحيح. إذا أردت ملفات APK أصغر لكل نوع معالج، يمكنك البناء يدويًا من نافذة أوامر داخل مجلد المشروع:

```text
flutter build apk --split-per-abi
```

## أخطاء شائعة

- **"Android SDK not found"**: ثبّت Android Studio، أو اضبط المتغير `ANDROID_HOME`.
- **البناء يفشل بسبب الترخيص**: نفّذ مرة واحدة `flutter doctor --android-licenses` ووافق.
- **أرسلت `app.exe` وحده فلم يعمل**: البرنامج يحتاج ملفات المجلد `Release` كلها.
- **فتحت `build/web/index.html` بنقرة مزدوجة فظهرت صفحة بيضاء**: موقع Flutter يحتاج خادم ويب، استخدم `python -m http.server` كما سبق.

## اختبر نفسك

```quiz
{"question": "أي ملف يطلبه متجر Google Play؟", "choices": ["app-release.apk", "app-release.aab (App Bundle)", "index.html", "main.dart"], "answer": 1, "explanation": "المتجر يطلب App Bundle بامتداد .aab، أما APK فللتثبيت المباشر."}
```

```quiz
{"question": "أين تجد ناتج بناء الموقع؟", "choices": ["lib/web", "build/web", "assets/web", "android/web"], "answer": 1, "explanation": "flutter build web يضع الموقع في المجلد build/web."}
```

```quiz
{"question": "رفعت النسخة 1.0.0+1 إلى المتجر. ماذا تكتب في version للنسخة التالية؟", "choices": ["1.0.0+1", "1.0.1+2", "0.9.0+1", "لا تغيّر شيئًا"], "answer": 1, "explanation": "يجب أن يزيد رقم البناء (بعد +) مع كل رفع، والإصدار الظاهر يزيد عادةً أيضًا."}
```

```quiz
{"question": "ما الفرق الأساسي بين نسخة التصحيح ونسخة الإصدار؟", "choices": ["لا فرق", "الإصدار أسرع وأصغر وبلا أدوات المطور", "التصحيح لا يعمل على الهاتف", "الإصدار يحتاج إنترنت"], "answer": 1, "explanation": "نسخة الإصدار مُحسَّنة للمستخدمين، ونسخة التصحيح للتطوير."}
```

## الخلاصة

- **Build > Mobile App** يبني `APK` و `App Bundle` و Windows والويب، والناتج في مجلد `build`.
- `APK` للتجربة والتثبيت المباشر، و`.aab` لمتجر Google Play.
- `version` في `pubspec.yaml` يحدد رقم الإصدار، وزِد رقم البناء مع كل نشر.
