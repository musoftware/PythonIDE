from Form1_designer import Form1Designer, EventArgs  # noqa: F401
from radcall import RadCallError, radcall


class Form1(Form1Designer):
    """A Python (Tkinter) form that uses code written in VB6 and Ring."""

    def Form1_Load(self):
        self.lblStatus.config(text="MathVB.bas = VB6,  TextRing.ring + Form2 = Ring,  this form = Python")

    def btnAdd_Click(self):
        try:
            total = radcall("MathVB.AddNumbers", float(self.txtA_var.get()), float(self.txtB_var.get()))
            self.lblSum.config(text=f"= {total:g}")
        except (ValueError, RadCallError) as e:
            self.lblSum.config(text=f"error: {e}")

    def btnShout_Click(self):
        self.lblShout.config(text=radcall("TextRing.shout", self.txtText_var.get()))

    def btnChain_Click(self):
        self.lblChain.config(text=radcall("TextRing.chain", 21))

    def btnRingForm_Click(self):
        radcall("Form2.Show")             # Form2 runs as its own Ring program


if __name__ == "__main__":
    Form1().show()
