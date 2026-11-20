load "Form2_designer.ring"

# A Ring form in a Python project. It is opened from Python with radcall("Form2.Show").

# ---------------- Event handlers ----------------

func Form2_Load
    cMsg = radcall("TextRing.shout", ["ring form loaded"])
    lblInfo.setText(cMsg)
    see "Form2 loaded: " + cMsg + nl

func btnAsk_Click
    lblAnswer.setText("VB6 says " + radcall("MathVB.AddNumbers", [40, 2]))
