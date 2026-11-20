from Form1_designer import Form1Designer, EventArgs  # noqa: F401

# References (Solution Explorer > App > References): MathLib is a C# class library and
# VbText a VB6 class library of this solution. Their functions are called as Python code;
# the IDE generates MathLib.py / VbText.py and RAD Hub runs the real C# / VB6 code.
import MathLib
import VbText


class Form1(Form1Designer):
    """A Python (Tkinter) form that uses two libraries written in other languages."""

    def Form1_Load(self):
        self.btnCalc_Click()

    def btnCalc_Click(self):
        try:
            a, b = float(self.txtA_var.get()), float(self.txtB_var.get())
        except ValueError:
            self.lblSum.config(text="Type two numbers")
            return
        total = MathLib.Add(a, b)                  # C#
        self.lblSum.config(text=f"MathLib.Add (C#) = {total:g}")
        self.lblProduct.config(text=f"MathLib.Multiply (C#) = {MathLib.Multiply(a, b):g}")
        self.lblWords.config(text=f"VbText.Describe (VB6) = {VbText.Describe(total)}")   # VB6

    def btnGreet_Click(self):
        self.lblGreet.config(text=MathLib.Greet(self.txtName_var.get()))


if __name__ == "__main__":
    Form1().show()
