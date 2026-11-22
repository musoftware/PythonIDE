# Focus Timer (JavaScript)

A "Pomodoro" timer: focus for 25 minutes, take a 5-minute break, repeat.

**What it shows**
- A `Timer` component (Interval 1000 ms) whose `Tick` handler counts down, a `ProgressBar` (`Max` / `Value`).
- A **modal second form**: `call("Settings", "ShowDialog")` shows the Settings dialog; its OK / Cancel handlers are
  in `Settings.js` and call `applySettings()` of `Form1.js` (both forms run in the same Node.js program).
  Controls of another form are addressed as `"Settings.numFocus"`.
- `NumericUpDown` and `CheckBox` values, a log `ListBox`, menus.
- Saved settings: `focustimer.settings.json` is read on start and written on OK.
- **Arabic interface**: tick "Arabic interface" in Settings - the captions switch to Arabic text.

**Run**: open the folder, **F5**, press Start (or Tools > Settings... first).
**Publish**: Build > Publish (GUI Bridge program, Python inside; Node.js needed on the PC).

---

# مؤقت التركيز (جافاسكربت)

مؤقت "بومودورو": تركيز 25 دقيقة ثم استراحة 5 دقائق، وهكذا.

**ماذا يوضح**
- مكون المؤقت `Timer` الذي يعد تنازليا كل ثانية، وشريط التقدم `ProgressBar`.
- **نموذج ثان مشروط (Modal)**: نافذة الإعدادات تُفتح بـ `call("Settings", "ShowDialog")`، ومعالجات زري موافق وإلغاء في
  `Settings.js` وتستدعي `applySettings()` في `Form1.js`.
- قيم `NumericUpDown` و`CheckBox`، وقائمة سجل، وقوائم.
- حفظ الإعدادات في `focustimer.settings.json` وقراءتها عند البدء.
- **واجهة عربية**: فعّل "الواجهة العربية" في الإعدادات فتتحول النصوص إلى العربية.

**التشغيل**: افتح المجلد واضغط **F5** ثم ابدأ.
**النشر**: Build > Publish (برنامج GUI Bridge، يحتاج Node.js على الجهاز).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
