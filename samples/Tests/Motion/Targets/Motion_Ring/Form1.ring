load "Form1_designer.ring"

# Animations are designed in the Animations window (form.extra["animations"]); the runtime is _radfx.ring.
# Form1_BeginAnimation("fx1") / Form1_StopAnimation("fx1") / Form1_SetVisible("lblInfo", false)

lHidden = false

func Form1_Load
    # runs after the form is created

func btnHide_Click
    lHidden = not lHidden
    Form1_SetVisible("lblInfo", not lHidden)
