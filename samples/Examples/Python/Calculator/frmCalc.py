# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Calculator - a button grid laid out in the RAD IDE designer, the logic in the CalcEngine module.

Shows: many Buttons sharing one helper, a form-level KeyPress / KeyDown handler (type 12+7= or use
Enter, Backspace, Esc, Delete), memory keys with an indicator Label, a fixed-size window (FormBorderStyle
FixedSingle) and a code module (CalcEngine.py) that other languages can also call through RAD Hub.
"""
from frmCalc_designer import frmCalcDesigner, EventArgs  # noqa: F401
import CalcEngine


class frmCalc(frmCalcDesigner):
    """Event handlers of the calculator window."""

    def frmCalc_Load(self):
        self.calc = CalcEngine.Calculator()
        self.root.bind("<Key>", self._on_key)
        self.refresh()

    # ------------------------------------------------------------------ display
    def refresh(self):
        c = self.calc
        self.lblDisplay.config(text=c.entry, font=("Segoe UI", 22 if len(c.entry) < 14 else 14, "bold"))
        self.lblExpr.config(text=c.expr)
        self.lblMemory.config(text="M" if c.memory else "")

    def press(self, key: str):
        """One key of the calculator: digits, '.', + - * /, '=', 'C', 'CE', 'back', '+/-', memory keys."""
        c = self.calc
        if key.isdigit():
            c.digit(key)
        elif key == ".":
            c.dot()
        elif key in "+-*/":
            c.operator(key)
        elif key == "=":
            c.equals()
        else:
            {"C": c.clear, "CE": c.clear_entry, "back": c.backspace, "+/-": c.sign, "MC": c.mem_clear,
             "MR": c.mem_recall, "M+": lambda: c.mem_add(1), "M-": lambda: c.mem_add(-1)}[key]()
        self.refresh()

    # ------------------------------------------------------------------ keyboard (form-level)
    def _on_key(self, e):
        special = {"Return": "=", "KP_Enter": "=", "BackSpace": "back", "Escape": "C", "Delete": "CE"}
        if e.keysym in special:
            self.press(special[e.keysym])
        elif e.char and e.char in "0123456789.+-*/=":
            self.press(e.char)
        elif e.char == ",":
            self.press(".")

    # ------------------------------------------------------------------ buttons
    def btn0_Click(self): self.press("0")
    def btn1_Click(self): self.press("1")
    def btn2_Click(self): self.press("2")
    def btn3_Click(self): self.press("3")
    def btn4_Click(self): self.press("4")
    def btn5_Click(self): self.press("5")
    def btn6_Click(self): self.press("6")
    def btn7_Click(self): self.press("7")
    def btn8_Click(self): self.press("8")
    def btn9_Click(self): self.press("9")
    def btnDot_Click(self): self.press(".")
    def btnAdd_Click(self): self.press("+")
    def btnSub_Click(self): self.press("-")
    def btnMul_Click(self): self.press("*")
    def btnDiv_Click(self): self.press("/")
    def btnEquals_Click(self): self.press("=")
    def btnClear_Click(self): self.press("C")
    def btnClearEntry_Click(self): self.press("CE")
    def btnBack_Click(self): self.press("back")
    def btnSign_Click(self): self.press("+/-")
    def btnMC_Click(self): self.press("MC")
    def btnMR_Click(self): self.press("MR")
    def btnMPlus_Click(self): self.press("M+")
    def btnMMinus_Click(self): self.press("M-")


if __name__ == "__main__":
    frmCalc().show()
