from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Animations are designed in the Animations window (form.extra["animations"]):
    the title slides in and types itself on load, Shake / Rotate / Move react to clicks, Hover me zooms
    while the mouse is over it and the blue panel changes colour every 2.5 s."""

    def btnHide_Click(self):
        # SetVisible plays lblInfo's "On hide" (fade out) / "On show" (fade in) animation
        self._hidden = not getattr(self, "_hidden", False)
        self.SetVisible("lblInfo", not self._hidden)

    def lblTitle_Click(self):
        # any preset from code, with options
        self.Animate("lblTitle", "pulse", durationMs=500)


if __name__ == "__main__":
    Form1().show()
