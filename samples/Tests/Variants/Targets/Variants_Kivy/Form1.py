# Form1 screen - write your event handlers here (double-click a control in the designer).
# Controls: self.lblHello.text = 'Hi'; self.txtName.text; self.swOn.active; self.lstItems.add_item('x')
# Screens: self.ShowForm('Form2')  self.CloseForm()   Dialogs: self.MsgBox('...'), self.Toast('...')
from Form1_designer import Form1Designer, RadEvent, run_app  # noqa: F401


class Form1(Form1Designer):
    def Form1_Load(self):
        pass


if __name__ == "__main__":
    run_app('Form1')
