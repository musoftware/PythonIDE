from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """StarRating component package test (docs/COMPONENTS.md)."""

    def Form1_Load(self):
        self.show_result()

    def show_result(self):
        self.lblResult.setText("Food: %d/%d  Service: %d/%d" % (self.rateFood.Value, self.rateFood.MaxStars, self.rateService.Value, self.rateService.MaxStars))

    def rateFood_ValueChanged(self):
        self.show_result()

    def rateService_ValueChanged(self):
        self.show_result()

    def btnReset_Click(self):
        self.rateFood.Reset()
        self.rateService.SetValue(1)


if __name__ == "__main__":
    Form1().show()
