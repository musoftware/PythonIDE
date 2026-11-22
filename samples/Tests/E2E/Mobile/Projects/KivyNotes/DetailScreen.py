# DetailScreen - one note (written in the RAD IDE code editor).
from DetailScreen_designer import DetailScreenDesigner, RadEvent  # noqa: F401


class DetailScreen(DetailScreenDesigner):
    def DetailScreen_Load(self):
        self.lblNote.text = str(self.FormArgs or "(no note)")

    def btnBack_Click(self):
        self.CloseForm()
