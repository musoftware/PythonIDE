// MainScreen - write your event handlers here (double-click a control in the designer).
// Controls: this.lblHello.Text = 'Hi'; this.txtName.Text; this.lstItems.AddItem('title|subtitle');
// Screens: this.ShowForm('Form2', args) / this.CloseForm() / this.FormArgs
// Dialogs: this.MsgBox('...'), this.Toast('...'), await this.InputBox('...'), await this.Confirm('...')
import { MainScreenDesigner } from './MainScreen_designer';
import { RadApp } from './radapp';

export default class MainScreen extends MainScreenDesigner {
  MainScreen_Load(e) {
    this.lblHello.Text = 'Type your name and tap the button.';
  }

  btnHello_Click(e) {
    const name = this.txtName.Text.trim();
    if (!name) {
      this.Toast('Please type your name first');
      return;
    }
    let text = `Hello, ${name}!`;
    if (this.swShout.Checked) text = text.toUpperCase();
    this.lstGreetings.AddItem(`chat|${text}|${new Date().toLocaleTimeString()}`);
    this.txtName.Text = '';
  }

  lstGreetings_Tap(e) {
    this.ShowForm('DetailsScreen', this.lstGreetings.Field(e.Index, 1));
  }

  btnDetails_Click(e) {
    this.ShowForm('DetailsScreen', 'Opened from the button');
  }

  AppBar1_Click(e) {
    this.MsgBox('Made with RAD IDE and React Native (Expo).', 'About');
  }
}
