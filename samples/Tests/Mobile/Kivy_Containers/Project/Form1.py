from Form1_designer import Form1Designer


class Form1(Form1Designer):
    def btnInCol_Click(self):
        self.lblTitle.text = "Clicked"


if __name__ == "__main__":
    from radkivy import run_app
    run_app("Form1")
