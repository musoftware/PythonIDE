from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Write your event handlers here."""

    def Button1_Click(self):
        # play the keyframe animation designed in "Objects and Timeline"
        self.Storyboard1.Begin()

    def Button2_Click(self):
        # switch the form between its custom "Big" state and the designed values
        self._big = not getattr(self, "_big", False)
        self.GoToState("Big" if self._big else "Normal")


if __name__ == "__main__":
    Form1().show()
