// ContactsScreen - a list of contacts. Tap a contact to edit it, + adds one.
// ShowForm('EditScreen', index) opens the second screen and waits for its result (CloseForm(result)).
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'contacts_screen_designer.dart';

class ContactsScreenCode extends ContactsScreenDesigner {
  final List<String> _all = [];

  void ContactsScreen_Load() {
    _all.addAll(lstContacts.items);
  }

  void _refresh() {
    final q = txtFilter.text.trim().toLowerCase();
    lstContacts.setItems(_all.where((c) => c.toLowerCase().contains(q)));
  }

  void txtFilter_Changed(RadEvent e) {
    _refresh();
  }

  Future<void> lstContacts_Tap(RadEvent e) async {
    final index = _all.indexOf(lstContacts.items[e.Index]);
    final result = await ShowForm('EditScreen', _all[index]);
    if (result is String) {
      _all[index] = result;
      _refresh();
      Toast('Contact saved');
    }
  }

  Future<void> fabAdd_Click() async {
    final result = await ShowForm('EditScreen', '');
    if (result is String) {
      _all.add(result);
      _refresh();
      Toast('Contact added');
    }
  }

  void AppBar1_Click(RadEvent e) {
    MsgBox('${_all.length} contacts. Made with RAD IDE + Flutter.', 'Hello Mobile');
  }
}
