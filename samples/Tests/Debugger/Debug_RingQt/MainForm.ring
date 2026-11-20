load "MainForm_designer.ring"

# Show this form with:  MainForm_Show()

# ---------------- Event handlers ----------------

func MainForm_Load
    nX = 42
    see "load done " + nX + nl

func btnHello_Click
    nSum = 0
    for i = 1 to 10
        nSum += i * i      # conditional breakpoint here: i = 5
    next
    see "sum of squares " + nSum + nl

func mnuFileExit_Click
    

func Timer1_Tick
    
