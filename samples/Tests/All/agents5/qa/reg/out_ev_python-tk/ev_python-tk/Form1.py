from Form1_designer import Form1Designer, EventArgs  # noqa: F401
import Helpers


class Form1(Form1Designer):
    """Write your event handlers here."""

    def Form1_Load(self):
        pass

    def Button1_MouseMove(self, e):
        print('move', e.X, e.Y)

    def Button1_Click(self):
        pass

    def TextBox1_KeyPress(self, e):
        print('key', e.KeyChar)

    def Form1_FormClosing(self, e):
        print('closing'); e.Cancel = False

    def Form1_Resize(self):
        pass

    def NumericUpDown1_ValueChanged(self):
        print('num', self.NumericUpDown1_var.get())

    def TrackBar1_ValueChanged(self):
        pass

    def Label1_DoubleClick(self):
        pass


if __name__ == "__main__":
    Form1().show()
