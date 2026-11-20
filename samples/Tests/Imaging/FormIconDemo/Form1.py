from Form1_designer import Form1Designer, EventArgs  # noqa: F401
import resources as R


class Form1(Form1Designer):
    """Write your event handlers here."""

    def Form1_Load(self):
        self.lblGreeting.configure(text=R.strings.Greeting)   # a string resource
        print("HWND", self.root.wm_frame(), flush=True)


if __name__ == "__main__":
    Form1().show()
