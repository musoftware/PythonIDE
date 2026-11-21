# Motion_AnimationsUI

**python-tk: Animations window** - three animation presets kept in `Form1.form` (`"animations"`, plan
MOTION_VARIANTS_FOLDABLES contract 1.1): Button1 slides in from the left on load, Label1 fades in after it
(`after` chain), Button2 shakes when it is clicked.

**Try it:** open the folder, open Form1 and View > Animations. Select Button1 and press **Preview**, or
**Preview all on load** (the slide-in, then the fade-in). Right-click a control > **Add Animation** > a group >
a preset. Change the trigger / duration / easing / repeat (0 = Forever) in the window. **Convert to Storyboard**
turns an animation into keyframes in Objects and Timeline. The Error List shows that python-tk draws the fade
as a colour blend (Tk child widgets have no transparency).

**Automated:** `python samples/Tests/Motion/test_animations_ui.py` (offscreen, qh.py harness, 52 checks:
list / add / edit / undo, context menu, preview frames, Error List, rename, convert, save, Arabic).

*Origin:* slice B of the motion plan (Animations panel), made for the UI test.
