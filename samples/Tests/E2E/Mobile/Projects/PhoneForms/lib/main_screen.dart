// MainScreen - write your event handlers here (double-click a control in the designer).
// Controls are fields: lblHello.text = 'Hi'; txtName.text; lstGreetings.addItem('a|b');
// Screens: ShowForm('Form2') / CloseForm()   Dialogs: MsgBox('...'), Toast('...'), await InputBox('...')
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {



  void AppBar1_Click(RadEvent e) {
    MsgBox('Made with RAD IDE and Flutter.', 'About');
  }

  void btnAdd_Click() {
    final t = txtItem.text.trim();
    if (t.isEmpty) return;
    lstItems.addItem(t);
    lblCount.text = 'Items: ${lstItems.count}';
    txtItem.text = '';

    
  }
}
