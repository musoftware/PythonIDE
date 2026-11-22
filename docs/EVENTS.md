# Event semantics of forms - every desktop language and execution path

RAD IDE forms raise the same **neutral events** (`Click`, `MouseDown`, `KeyPress`, `TextChanged`, `CheckedChanged`,
`SelectedIndexChanged`, `Tick`, `FormClosing` ... - `radide/controls.py`, the component packages
`radide/components/builtin/*/component.json`); VB6 code sees them under their VB6 names (`radide/runtimes/vbevents.py`:
`TextChanged` -> `Change`, `CheckedChanged` / `SelectedIndexChanged` -> `Click`, `Tick` -> `Timer`, `FormClosing` ->
`QueryUnload` + `Unload`, `FormClosed` -> `Terminate`). This page says **when** each event fires, in **which order**,
with **which arguments**, for every engine that runs a form, and lists the differences that are intentional.

The rules are checked by an automated matrix: `samples/Tests/Events/test_events.py` (spec: `spec.py`, projects:
`make_projects.py` -> `samples/Tests/Events/projects/<Language>`).

## Engines and families

| Language | Path | Engine | Family |
|---|---|---|---|
| VB6 | vbrun (F5 in the IDE, `radide/runtimes/vbrun.py`) | Tk | `vb6` |
| VB6 | native exe (FreeBASIC, `radide/deploy/native/vb6fb`) | Win32 (`rt/vbrt_forms.bi`) | `vb6` |
| Python | Tkinter project | Tk (generated designer, `radide/languages/python_tk.py`) | `tk` |
| C, C++, Rust, Go, Lua, JavaScript / TypeScript | native exe | radforms (`radide/runtimes/native/radforms/radforms.c`) | `neutral` |
| C# | native exe | WinForms (`radide/deploy/native/dotnet/RadWinForms.cs`) | `winforms` |
| Java | native exe | Swing (`radide/deploy/native/java/RadSwing.java`) | `swing` |
| every bridge language (C, C#, Java, Rust, Go, Lua, JS, Fortran, Perl, PHP, Ruby, Dart, PowerShell, Ring ...) | GUI Bridge (F5) | the IDE's Tk host (`radide/runtimes/bridge.py`) + the language client | `neutral` |

## Current matrix
Last full run (Windows 11, every toolchain installed; 17 engine paths, 224 steps passed, 0 failed, 11 skipped):

| Language:path | lifecycle | mouse | focus | keyboard | code | timer | selection |
|---|---|---|---|---|---|---|---|
| VB6:vbrun | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| VB6:native (FreeBASIC) | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| Python:tk | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| C / Rust / Go / Lua / JS : native (radforms) | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| C / C# / Java / Rust / Go / Lua / JS : bridge | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| CSharp:native (WinForms) | PASS | SKIP* | SKIP* | SKIP* | PASS | PASS | SKIP* (list) / PASS (check) |
| Java:native (Swing) | PASS | PASS | SKIP** | SKIP** | PASS | PASS | PASS |

\* the test window was not the foreground window on the shared desktop (WinForms checks capture /
`WindowFromPoint` / activation, see below); they run where the window gets the foreground.
\*\* Swing focus / keyboard need real input in the active window.

VB6 has 7 more steps and closes with Unload Me instead of a second WM_CLOSE (KeyAscii cancel / change, Validate
cancel / ok, DoEvents, Timer during MsgBox, an error in a handler): 13 steps per path, 20 for VB6.

## The rules

### Form life cycle
| | VB6 (`vb6`) | everything else |
|---|---|---|
| start | `Initialize`, `Load`, (`Resize`), `Activate` | `Load`, (`Activated`) |
| close box / `WM_CLOSE` | `QueryUnload(Cancel, UnloadMode = 0 vbFormControlMenu)`, `Unload(Cancel)`, `Terminate` | `FormClosing` (cancel: `e.Cancel = True` (C#, Java, Python) or `Set("Form1", "Cancel", True)` (every language)), `FormClosed` |
| `Unload Me` in a handler | `QueryUnload(UnloadMode = 1 vbFormCode)`, `Unload`; the rest of the handler still runs; the program ends when no form is loaded **and** no code runs; `Terminate` when the form object is released | - |
| Cancel | `Cancel = 1` in `QueryUnload` / `Unload` keeps the form | the first `FormClosing` that cancels keeps the form, the next close closes it |
| unhandled run-time error in a handler | message box, the rest of the handler is skipped, the program goes on (see *intentional differences*) | - |

`Activate` / `Activated` / `Deactivate` depend on which window the desktop activates (another program can take
the foreground at any time), so the matrix records but does not compare them.

### Mouse
* Order of a click: **`MouseDown`, `MouseUp`, `Click`** (VB6 help, *Click Event*: the click comes after the button
  is released over the control) - for buttons **and** for labels / pictures / panels (generic controls).
* Real WinForms (C# native) raises **`MouseDown`, `Click`, `MouseUp`** (`Control.WmMouseUp` / `ButtonBase.OnMouseUp`
  call `OnClick` before `OnMouseUp`) - documented .NET behaviour, kept.
* Arguments: VB6 `Button` (1 left, 2 right, 4 middle), `Shift` (1 Shift, 2 Ctrl, 4 Alt), `X`, `Y` in the
  container's `ScaleMode` (Pixel or Twip); neutral `e.X`, `e.Y` (pixels, or the form's ScaleMode in radforms),
  `e.Button` (1 left, 2 middle, 3 right). The raw argument text of the bridge protocol is `"X Y Button KeyCode KeyChar"`.
* Double click (documented, not part of the compared matrix): VB6 `MouseDown, MouseUp, Click, DblClick, MouseUp`
  (the second press raises `DblClick` instead of `MouseDown`); WinForms raises a second `MouseDown`.
* Swing: a `JButton` fires its action inside `mouseReleased`, before the MouseUp listeners; RadSwing delivers that
  `Click` after `MouseUp` so the Java native exe keeps the neutral order (a `JLabel` already does).

### Keyboard
* Order: **`KeyDown`, `KeyPress`, (`Change` / `TextChanged`), `KeyUp`**.
* VB6 `KeyPress(KeyAscii)` is ByRef: `KeyAscii = 0` swallows the key (no `Change`), another value types that
  character instead (`KeyAscii = Asc("B")`) - vbrun and the native exe.
* `KeyDown(KeyCode, Shift)`: `KeyCode` is the Windows virtual-key code (65 = A). Neutral `e.KeyCode`: the
  virtual-key code (bridge, WinForms, Swing) or the key name (`a`, `Return` - radforms' raw text); `e.KeyChar` the
  typed character (control characters are left out of the bridge text: they would break the line protocol).

### Focus
* **`LostFocus` of the old control before `GotFocus` of the new one** (all engines).
* VB6 `Validate(Cancel)`: before `LostFocus`, when the focus moves to another control of the same form;
  `Cancel = True` keeps the focus - no `LostFocus`, no `GotFocus` of the other control. vbrun and the native exe.
  Not raised when the whole program loses the focus to another window.
* A Tk button does not take the focus when it is clicked (Tk default); Win32 / WinForms buttons do. Steps that click
  buttons therefore do not compare focus events.

### Events raised by code
| | `txtA.Text = ...` | `chkA.Value = 1` | `lstA.ListIndex = 2` | when |
|---|---|---|---|---|
| VB6 | `Change` | `Click` | `Click` | **at once**, nested in the running handler |
| WinForms, Swing | `TextChanged` | `CheckedChanged` | `SelectedIndexChanged` | at once, nested |
| neutral (radforms, GUI Bridge) | `TextChanged` | `CheckedChanged` | `SelectedIndexChanged` | **queued**: after the running handler returns, in order |
| Python Tk | `TextChanged` (`StringVar.set`) | - | - | at once (Tk variable traces only) |

### Timers, DoEvents, modal dialogs
* A `Timer` / `Tick` handler runs after the handler that enabled the timer has returned.
* VB6 `DoEvents` inside a handler runs pending events (a timer tick) before the handler goes on.
* While a `MsgBox` is open in a handler, timers keep ticking (VB6 compiled exe behaviour); the handler goes on after
  the box is closed.

## Intentional differences
1. **WinForms mouse order** (C# native): `MouseDown, Click, MouseUp` - the real .NET order; the neutral contract
   keeps VB6's `MouseDown, MouseUp, Click`.
2. **Queued code events** (radforms natives and every GUI Bridge language): the program is single-threaded and
   the bridge protocol is request / answer (`SET` waits for `DONE` of no other event), so an event caused by the
   handler's own `Set` is delivered right after that handler, not inside it. Same order, later.
3. **Python Tk** projects are plain Tkinter: only Tk variable traces react to code (`txtA_var.set` raises
   `TextChanged`; `BooleanVar.set` and `Listbox.selection_set` raise nothing), a Tk button does not take the focus.
4. **Unhandled run-time error**: a compiled VB6 exe ends the program; RAD IDE (vbrun and the native exe) shows the
   message and keeps the program running (the handler is left at the error).
5. **`Form_Terminate`**: VB6 raises it when the form object is released; RAD IDE raises it when the form is
   unloaded and no form is left (vbrun) / after every unload (native exe, paired with `Initialize` on every load).
6. **Activate / Deactivate** follow the desktop's activation; they are not part of the compared matrix.

## Bugs found by the matrix and fixed
| Engine | Bug | Fix |
|---|---|---|
| Tk generator (Python Tk, vbrun, every bridge) | `MouseUp` of the left button never ran on a control / form that also had a `Click` handler (Tk only runs the most specific binding: `<ButtonRelease-1>` hid `<ButtonRelease>`) | `PythonTkPlugin.generic_bind_lines`: MouseUp also on `<ButtonRelease-1>`, before Click |
| vbrun | no `Form_Initialize`; no `Form_Terminate`; `KeyAscii = <other char>` ignored (only 0 worked); no `Validate`; `Unload Me` did not raise `QueryUnload` (UnloadMode 1) | `vbrun.py`: `call_form_event`, `bind_validate` / `_validate`, `_replace_key`, `unload` |
| FreeBASIC native | `Form_Initialize` and `Validate` made the build fall back to the Python runtime; `Label` / `LinkLabel` / `PictureBox` raised `Click` before `MouseUp`; `Unload Me` ended the program before the rest of the handler ran | `vb6fb/forms.py`, `translate.py` (ByRef arguments of another type through a temporary), `rt/vbrt_forms.bi` (`vbeInitialize`, `vbeValidate`, `VB_WM_REFOCUS`, click on `WM_LBUTTONUP`, `vbFireDepth`) |
| radforms | `Label` / `LinkLabel` / `PictureBox`: `Click` before `MouseUp` (`STN_CLICKED` comes with the press) | `rf_generic_click` |
| GUI Bridge host | `FormClosing` could not be cancelled (`SET Form1 Cancel True` was an error 438) and `FormClosed` was never sent | `bridge.py` `close_form` / `SET` |
| Swing (Java native) | `JButton`: `MouseDown, Click, MouseUp` while a `JLabel` gave `MouseDown, MouseUp, Click` | `RadSwing.wire` "Click": deferred after `mouseReleased` for a mouse click |
| C# and Java bridge clients | `e.Cancel` / `e.cancel` did not exist (code that cancels FormClosing compiled only natively) | `RadEvent.Cancel` + `SET <form> Cancel True` after the handler (`clients/csharp`, `clients/java`) |

## How the matrix drives the programs
* Win32 engines (FreeBASIC, radforms, WinForms): `WM_LBUTTONDOWN` / `WM_LBUTTONUP` posted to the control's window
  at control coordinates, `WM_KEYDOWN` / `WM_KEYUP` (the program's `TranslateMessage` makes `WM_CHAR`; its thread is
  switched to the US layout with `WM_INPUTLANGCHANGEREQUEST`), `WM_SETTEXT`, `WM_CLOSE`. Only the processes the test
  started are touched; there is no screen capture.
* WinForms checks real input: a button raises `Click` only when it holds the mouse capture and is the window under
  the point (`WindowFromPoint`), a text box takes the focus only in the active window. When the test window is not
  the foreground window (another program has it) the mouse / focus / keyboard / list-click steps are SKIPPED with
  that reason and buttons are pressed with `BM_CLICK` (`PerformClick`) for the other steps; on a desktop where the
  test window gets the foreground (CI) they run.
* Swing draws its controls itself and AWT sends a mouse message to the window under the REAL cursor, so the Java exe
  is a test build with `RadTestHook` (`RADIDE_NATIVE_TEST_HOOK=1`, never in a release): `mouse <obj> x y` posts the AWT
  events of a left click (pressed, released, clicked) to the component. Focus / keyboard need real input in the active
  window and are SKIPPED for Swing.
* Tk engines: Tk ignores posted mouse messages (it reads the button state with `GetKeyState`), so `tk_driver.py` runs
  the program in its own process and injects the input with `event generate` on the real widgets (the whole binding
  chain runs); the toplevel takes the thread's focus once; closing posts a real `WM_CLOSE`.
* Handlers log `EVT <Owner>_<Event> <args>` to `RADEVT_LOG` (VB6: `Debug.Print`); the log is normalised
  (`evcore.normalize`) and compared step by step. A run with failures is repeated (up to three runs; a step passes
  when one run passed) because another program can take the focus on a busy desktop.

---

## ملخص بالعربية

**دلالات الأحداث في النماذج لكل اللغات ومسارات التشغيل.** كل نماذج RAD IDE ترفع أحداثًا محايدة (Click و MouseDown
و KeyPress و TextChanged ...)، وكود VB6 يراها بأسمائها في VB6 (Change و Click و Timer و QueryUnload/Unload و Terminate).
مصفوفة الاختبار `samples/Tests/Events/test_events.py` تشغّل النموذج نفسه في كل لغة ومسار (vbrun داخل الـ IDE، و exe
FreeBASIC الأصلي، و Python Tk، و radforms لـ C/Rust/Go/Lua/JS، و WinForms لـ C#، و Swing لـ Java، و GUI Bridge لكل
لغات الجسر) بنفس المدخلات الحقيقية، وتقارن سجلّ الأحداث بالتسلسل المتوقع.

**القواعد:** ترتيب النقرة MouseDown ثم MouseUp ثم Click (كما في VB6) للأزرار والتسميات معًا؛ لوحة المفاتيح KeyDown ثم
KeyPress ثم Change ثم KeyUp، و KeyAscii = 0 يلغي الحرف وأي قيمة أخرى تكتب حرفًا بديلًا؛ التركيز LostFocus للقديم قبل
GotFocus للجديد، و Validate قبل LostFocus و Cancel يُبقي التركيز؛ إغلاق النموذج QueryUnload ثم Unload ثم Terminate في
VB6 و FormClosing ثم FormClosed في غيرها، والإلغاء يُبقي النموذج مفتوحًا؛ Unload Me داخل معالج يكمل بقية المعالج.

**فروق مقصودة:** WinForms الحقيقي يرفع Click قبل MouseUp؛ في radforms والجسر تُسلَّم الأحداث التي يسببها الكود بعد
انتهاء المعالج الجاري (بنفس الترتيب) لأن البرنامج أحادي الخيط وبروتوكول الجسر طلب/رد؛ مشاريع Python Tk هي Tkinter
خام فلا يرفع تغيير CheckBox أو ListBox من الكود حدثًا؛ الخطأ غير المعالج يعرض رسالة ويُبقي البرنامج يعمل بدل إنهائه؛
Activate/Deactivate تتبع تفعيل سطح المكتب فلا تُقارن.

**أخطاء أُصلحت:** ضياع MouseUp للزر الأيسر في مولّد Tk عند وجود Click؛ في vbrun: غياب Initialize و Terminate و
Validate، وتجاهل تغيير KeyAscii، وعدم رفع QueryUnload عند Unload Me؛ في FreeBASIC: Initialize و Validate كانا يُسقطان
البناء إلى Python، و Click للتسمية قبل MouseUp، وإنهاء البرنامج قبل إكمال المعالج بعد Unload Me؛ في radforms: Click
للتسمية قبل MouseUp؛ في الجسر: تعذّر إلغاء FormClosing وعدم إرسال FormClosed؛ وعميلا C# و Java بلا e.Cancel؛ وفي Swing كان JButton يرفع Click قبل MouseUp.

**طريقة القيادة:** رسائل Win32 حقيقية تُرسل لنوافذ البرنامج الذي شغّله الاختبار فقط (بدون لقطات شاشة)؛ Tk يتجاهل رسائل الفأرة المُرسلة فتُحقن بـ event generate داخل العملية نفسها؛ WinForms يتحقق من الالتقاط والنافذة الأمامية فتُتخطى خطوات الفأرة/التركيز/لوحة المفاتيح حين لا تكون نافذة الاختبار في المقدمة؛ و Swing يُقاد عبر RadTestHook في بناء الاختبار فقط، وتركيزه ولوحة مفاتيحه تُتخطى.
