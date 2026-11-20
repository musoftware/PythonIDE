// DetailsScreen - write your event handlers here (double-click a control in the designer).
// Controls: this.lblHello.Text = 'Hi'; this.txtName.Text; this.lstItems.AddItem('title|subtitle');
// Screens: this.ShowForm('Form2', args) / this.CloseForm() / this.FormArgs
// Dialogs: this.MsgBox('...'), this.Toast('...'), await this.InputBox('...'), await this.Confirm('...')
import { DetailsScreenDesigner } from './DetailsScreen_designer';
import { RadApp } from './radapp';

export default class DetailsScreen extends DetailsScreenDesigner {
  DetailsScreen_Load(e) {
    this.lblMessage.Text = this.FormArgs || '(no message)';
  }

  sldSize_Changed(e) {
    this.lblMessage.FontSize = e.Value;
    this.lblSize.Text = `Text size: ${e.Value}`;
  }

  btnClose_Click(e) {
    this.CloseForm();
  }
}
