load "Form1_designer.ring"

# Show this form with:  Form1_Show()

# ---------------- Event handlers ----------------

func Form1_Load
    # runs after the form is created

func rateFood_ValueChanged
    lblResult.setText("Food " + rateFood.value() + "/" + rateFood.maxStars() + " - Service " + rateService.value() + "/" + rateService.maxStars())


func rateService_ValueChanged
    lblResult.setText("Food " + rateFood.value() + "/" + rateFood.maxStars() + " - Service " + rateService.value() + "/" + rateService.maxStars())


func btnReset_Click
    rateFood.reset()
    rateService.setValue(1)

