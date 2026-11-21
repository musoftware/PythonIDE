# Form1 screen - animations come from the Animations window (radkivyfx.py plays them).
# self.BeginAnimation("fx1") / self.StopAnimation("fx1") / self.SetVisible("lblInfo", False)
from Form1_designer import Form1Designer, RadEvent, run_app  # noqa: F401


class Form1(Form1Designer):
    _hidden = False

    def btnHide_Click(self):
        self._hidden = not self._hidden
        self.SetVisible("lblInfo", not self._hidden)


if __name__ == "__main__":
    run_app("Form1")
