# Motion_Qt_Presets

**python-qt (PySide6): animation presets** - the same form as `Motion_Tk_Presets`. On Qt the fades use real
transparency (`QGraphicsOpacityEffect`); rotate / flip / scale still fall back (no transforms on widgets) and are
listed as fallbacks. Triggers use a Qt event filter (`_RadFxEvents`).

**Try it:** F5; hover / click the buttons. **Checks:** `python samples/Tests/Motion/check_runtime.py` (offscreen).
