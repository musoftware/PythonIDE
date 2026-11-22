# Greeting Card - multi-form, settings, Arabic / RTL (python-tk)

Two forms: the main window and a **modal Settings dialog**; the UI switches between English and Arabic.

**What it shows**
- A second form of the project (`frmSettings`, Project > Add Form) opened as a modal dialog from code:
  `frmSettings(master=self.root)`, `grab_set()`, `wait_window()`, then its `result` is read (None = Cancel).
- Settings saved as JSON in the user's application data folder
  (`%APPDATA%\RADExamples\SettingsMultiForm\settings.json`, module `AppSettings.py`) and loaded at the next start
  (language, card color, font size, "remember my name").
- **Arabic / right-to-left**: all texts in English and Arabic, Arabic menu caption (العربية), right-aligned labels
  and a mirrored layout when Arabic is chosen; the dialog follows the language too.

**Run**: open the folder, **F5**; try Language > العربية and File > Settings...
**Publish**: Build > Publish (PyInstaller).

---

# بطاقة ترحيب - عدة نماذج وإعدادات وواجهة عربية (بايثون Tkinter)

نموذجان: النافذة الرئيسية ونافذة **إعدادات** مشروطة (Modal)، والواجهة تتبدل بين الإنجليزية والعربية.

**ماذا يوضح**
- فتح نموذج ثانٍ من المشروع كنافذة حوار مشروطة وقراءة النتيجة بعد إغلاقها (موافق / إلغاء).
- حفظ الإعدادات بصيغة JSON في مجلد بيانات التطبيق الخاص بالمستخدم وتحميلها عند التشغيل التالي
  (اللغة، لون البطاقة، حجم الخط، تذكر الاسم).
- **العربية من اليمين لليسار**: كل النصوص بالعربية والإنجليزية، ومحاذاة لليمين، وعكس ترتيب العناصر عند اختيار العربية.

**التشغيل**: افتح المجلد واضغط **F5**، ثم جرّب قائمة Language > العربية و File > Settings.
**النشر**: Build > Publish.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
