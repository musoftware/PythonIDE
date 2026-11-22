# MainScreen - notes list (written in the RAD IDE code editor).
import json
import os

from MainScreen_designer import MainScreenDesigner, RadEvent, run_app  # noqa: F401

NOTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes.json")


class MainScreen(MainScreenDesigner):
    def MainScreen_Load(self):
        self.notes = json.load(open(NOTES, encoding="utf-8")) if os.path.exists(NOTES) else []
        self.lstGreetings.clear()
        for n in self.notes:
            self.lstGreetings.add_item(n)
        self.lblHello.text = f"{len(self.notes)} notes"

    def btnHello_Click(self):
        text = self.txtName.text.strip()
        if not text:
            self.Toast("Write a note first")
            return
        self.notes.append(text)
        with open(NOTES, "w", encoding="utf-8") as f:
            json.dump(self.notes, f)
        self.lstGreetings.add_item(text)
        self.lblHello.text = f"{len(self.notes)} notes"
        self.txtName.text = ""

    def lstGreetings_Tap(self, e):
        self.ShowForm("DetailScreen", self.lstGreetings.items[e.Index])

    def AppBar1_Click(self, e):
        self.MsgBox("Notes - made with RAD IDE and Kivy.", "About")


if __name__ == "__main__":
    run_app('MainScreen')
