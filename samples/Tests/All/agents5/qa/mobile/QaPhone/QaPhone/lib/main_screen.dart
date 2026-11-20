// MainScreen screen - write your event handlers here (double-click a control in the designer).
// Controls are fields: lblTitle.text = 'Hi'; txtName.text; chkAgree.checked; lstItems.addItem('x');
// Screens: ShowForm('Form2') / CloseForm()   Dialogs: MsgBox('...'), Toast('...'), await InputBox('...')
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void MainScreen_Load() {
    // runs when the screen is shown
  }

  void Button1_Click() {
    ListView1.addItem(TextField1.text);
    TextField1.text = ''; // qa
  }
}
