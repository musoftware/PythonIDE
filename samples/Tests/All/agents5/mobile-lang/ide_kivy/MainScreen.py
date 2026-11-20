# MainScreen screen - write your event handlers here (double-click a control in the designer).
# Controls: self.lblHello.text = 'Hi'; self.txtName.text; self.swOn.active; self.lstItems.add_item('x')
# Screens: self.ShowForm('Form2')  self.CloseForm()   Dialogs: self.MsgBox('...'), self.Toast('...')
from MainScreen_designer import MainScreenDesigner, RadEvent, run_app  # noqa: F401


class MainScreen(MainScreenDesigner):
    def MainScreen_Load(self):
        self.lblHello.text = "Type your name and tap the button."

    def btnHello_Click(self):
        name = self.txtName.text.strip()
        if not name:
            self.Toast("Please type your name first")
            return
        text = f"Hello, {name}!"
        if self.swShout.active:
            text = text.upper()
        self.lstGreetings.add_item(text)
        self.txtName.text = ""

    def lstGreetings_Tap(self, e):
        self.MsgBox(e.Text, "You tapped")

    def AppBar1_Click(self, e):
        self.MsgBox("Made with RAD IDE and Kivy.", "About")


if __name__ == "__main__":
    run_app('MainScreen')
