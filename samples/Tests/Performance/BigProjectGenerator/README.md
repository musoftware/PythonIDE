# Big project generator (performance tests, round 7)

`make_big_projects.py [folder]` writes two projects (default: `out\` next to the script, ~10 000 files, ~60 MB):

* `BigSite` - an HTML/CSS/JS web site project with 5000 files in 100 folders + 50 000-line `big\big50k.js`,
  `big50k.py`, `big50k.html`;
* `BigApp` - a Python (Tkinter) project with 5000 modules in project.radproj + `big50k.py`.

Open them in RAD IDE and try: opening the project, Solution Explorer, Find in Files (Ctrl+Shift+F, "func_"),
opening and scrolling/typing in the 50k-line files, IntelliSense in `big50k.py`.

Measured on this machine (busy: 10+ agents running), before -> after the round-7 fixes:

| Measure | Before | After |
| --- | --- | --- |
| Open BigSite (UI blocked) | 2.29 s | 0.36 s |
| Solution Explorer refill, BigSite | 2.58 s | 0.28 s |
| Open BigApp | 1.40 s | 0.71 s |
| Find in Files "func_", BigSite (2500 hits) | 58.2 s, files after the 5000th never searched (2498 hits) | 2.3 s, 2500 hits |
| Find in Files "func_", BigApp (5000 hits) | 49.0 s | 2.4 s |
| Monaco: open big50k.js (call / ready) | 0.81 s / 1.68 s | 0.08 s / 1.05 s |
| Monaco: one keystroke round trip, 2 MB file | 109 ms | 36 ms |
| Monaco: ten keystrokes, 2 MB file | 1134 ms | 312 ms |
| Monaco web workers | failed (ran on the UI thread) | load |
| pylsp first completion in big50k.py | 11.3 s | 10.6 s (pylsp/jedi itself; asynchronous, UI not blocked) |
