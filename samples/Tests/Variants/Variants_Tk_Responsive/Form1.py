from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Same sizes as Variants_Qt_Responsive (python-tk). Resize the window to see the layouts switch."""

    def Form1_Load(self):
        self.changes = 0

    def Form1_SizeVariantChanged(self):
        self.changes = getattr(self, "changes", 0) + 1
        self.lblStatus.configure(text=f"Sizes: {self.CurrentSizes or ['(designed size)']}")


if __name__ == "__main__":
    Form1().show()
