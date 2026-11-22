# NativeShowcase - RAD Modern controls in a native C program

A C project (GUI Bridge, `radgui.h`) that uses the RAD Modern (Rm*) controls: a ribbon (application menu, quick
access, tabs, large / small / check / drop-down items), a side bar with groups and badges, a tab strip whose pages
hold gauges, a circular progress, tiles, a card panel, a grid (typed columns: check, combo, progress, button), and a
settings page with toggles, check / radio buttons, a slider, a theme combo box, a text box with an icon and a clear
button, a date picker, a split button and a calendar; a status bar, a toast and a themed message box. A timer moves
the gauges. The theme (Light / Dark / Office / Metro) changes at run time (View tab, the theme combo box, the Dark
mode toggle).

* **Run (F5)**: the IDE draws the form with its Tk runtime (the Rm* packages' python-tk classes).
* **Build > Publish** (kind *native*): one standalone exe of about 260 KB - radforms + the rm_*.c modules the form
  uses, Win32 only, no Python and no extra DLLs.

`Form1.c` shows the portable way to read item events: `rad_get("RmRibbon1", "EventItem")` (the native exe also has
`rad_arg(0)`). Properties and methods have the same names in every language (docs/plans/MODERN_CONTROLS.md);
docs/NATIVE_BUILD.md, section "Modern controls (Rm*)", explains the C ABI for other languages.

Tested by `samples/Tests/Native/test_native_modern.py`.

## بالعربية

مشروع C يستخدم عناصر RAD الحديثة: شريط Ribbon وشريط جانبي وتبويبات وعدادات وبلاطات وجدول متقدم ومفاتيح تبديل
وإشعارات وصندوق رسائل، مع تغيير السمة أثناء التشغيل. النشر الأصلي ينتج ملف exe واحداً مستقلاً (حوالي 260 كيلوبايت)
بلا Python وبلا مكتبات إضافية.

MIT License - Copyright (c) 2026 Musoftware.
