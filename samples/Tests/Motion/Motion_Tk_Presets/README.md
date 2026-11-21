# Motion_Tk_Presets

**python-tk: animation presets** (plan MOTION_VARIANTS_FOLDABLES, slice A). One form with ten animations in
`form.extra["animations"]`: the title slides in and types itself on load, *Shake me* shakes on click, *Hover me*
zooms while the mouse is over it (reverses on leave), *Move + bounce* moves 60 px and then bounces (chained with
`after`), *Rotate* wobbles (Tk has no rotation - listed as a fallback), *Hide / show* fades `lblInfo` out / in
(`self.SetVisible`, "On hide" / "On show"; Tk widgets have no alpha, so the fade is a colour blend into the
background), the blue panel changes colour every 2.5 s (timer + auto reverse). Clicking the title runs
`self.Animate("lblTitle", "pulse")` from code.

**Try it:** open the folder, F5. Set `RADIDE_REDUCED_MOTION=1` to see every animation jump to its end.

**Checks:** `python samples/Tests/Motion/check_runtime.py` (runs this form for real), `make_samples.py` rebuilds it.
