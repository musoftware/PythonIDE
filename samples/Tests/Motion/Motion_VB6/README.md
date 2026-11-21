# Motion_VB6

**vb-basic (VB6 runtime): animations from VB code.** The form is built by the Tk generator, so the designed
animations run unchanged; VB code adds:

```vb
lblInfo.Visible = Not lblInfo.Visible        ' plays its "On hide" / "On show" animation
lblTitle.Animate "slideIn", 500, "from=right" ' preset, duration (ms), "name=value" options
pnlBox.Animate "pulse"
fx10.Begin                                    ' an animation (or a Storyboard) as an object: Begin/Stop/Pause/Resume/Reverse/Seek
Form1.Animate "fadeIn"                        ' the form; Me.Animate "Command1", "shake"; Form1.BeginAnimation "fx3"
```

GUI-Bridge languages use the same objects: `CALL lblTitle Animate slideIn<TAB>500<TAB>from=right`.

**Try it:** F5, click *Hide / show*, the title and the blue panel. **Checks:** `python samples/Tests/Motion/check_vb6.py`.
