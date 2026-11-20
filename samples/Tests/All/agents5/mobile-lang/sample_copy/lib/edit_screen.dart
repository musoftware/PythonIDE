// EditScreen - FormArgs is the contact ("name|email|icon", '' = new); CloseForm(result) returns it.
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'edit_screen_designer.dart';

class EditScreenCode extends EditScreenDesigner {
  void EditScreen_Load() {
    final parts = (FormArgs as String? ?? '').split('|');
    txtName.text = parts.isNotEmpty ? parts[0] : '';
    txtEmail.text = parts.length > 1 ? parts[1] : '';
    swFavorite.checked = parts.length > 2 && parts[2] == 'star';
    lblStatus.text = txtName.text.isEmpty ? 'New contact' : 'Editing ${txtName.text}';
  }

  void btnSave_Click() {
    if (txtName.text.trim().isEmpty) {
      MsgBox('Please type a name.');
      return;
    }
    CloseForm('${txtName.text.trim()}|${txtEmail.text.trim()}|${swFavorite.checked ? 'star' : 'person'}');
  }

  void btnCancel_Click() {
    CloseForm();
  }

  Future<void> AppBar1_Click(RadEvent e) async {
    if (await Confirm('Discard the changes?')) {
      CloseForm();
    }
  }
}
