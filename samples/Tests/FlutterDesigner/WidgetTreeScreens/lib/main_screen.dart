// MainScreen - write your event handlers here (double-click a control in the designer).
// Controls are fields: lblHello.text = 'Hi'; txtName.text; lstGreetings.addItem('a|b');
// Screens: ShowForm('Form2') / CloseForm()   Dialogs: MsgBox('...'), Toast('...'), await InputBox('...')
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  void MainScreen_Load() {
    lblHello.text = 'Welcome! Type your name and tap the button.';
  }

  void btnHello_Click() {
    final name = txtName.text.trim();
    if (name.isEmpty) {
      Toast('Please type your name first');
      return;
    }
    final time = TimeOfDay.now().format(context);
    lstGreetings.addItem('Hello, $name!|said at $time');
    txtName.text = '';
  }

  void lstGreetings_Tap(RadEvent e) {
    MsgBox(lstGreetings.field(e.Index, 0), 'You tapped');
  }

  void AppBar1_Click(RadEvent e) {
    MsgBox('Made with RAD IDE and Flutter.', 'About');
  }
}
