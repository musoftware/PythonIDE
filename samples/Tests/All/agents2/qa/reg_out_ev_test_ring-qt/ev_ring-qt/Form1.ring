load "Form1_designer.ring"

# Show this form with:  Form1_Show()

# ---------------- Event handlers ----------------

func Form1_Load
    # runs after the form is created

func Button1_MouseMove e
    # e.getx()  e.gety()  e.getbutton()  e.getWheelDelta()
    see "move " + e.getx() + nl

func Button1_Click
    

func TextBox1_KeyPress e
    # e.getKeyCode()  e.getKeyText()
    see "key " + e.getKeyText() + nl

func Form1_FormClosing e
    # call e.ignore() to keep the form open
    

func Form1_Resize
    

func NumericUpDown1_ValueChanged
    see "num " + NumericUpDown1.value() + nl

func TrackBar1_ValueChanged
    

func Label1_DoubleClick
    
