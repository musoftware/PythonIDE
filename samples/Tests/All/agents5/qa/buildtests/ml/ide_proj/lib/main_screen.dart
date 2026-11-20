// MainScreen - bottom navigation switches the pages (Column containers); the drawer and the
// floating action button show messages; btnDetails opens the second screen with ShowForm.
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'main_screen_designer.dart';

class MainScreenCode extends MainScreenDesigner {
  final List<String> _words = ['apple', 'banana', 'cherry', 'flutter', 'kotlin', 'python', 'dart'];

  void MainScreen_Load() {
    showPage(BottomNav1.selectedIndex);
  }

  void showPage(int index) {
    pnlHome.visible = index == 0;
    pnlSearch.visible = index == 1;
    pnlProfile.visible = index == 2;
  }

  void BottomNav1_Changed(RadEvent e) {
    showPage(e.Index);
  }

  void Drawer1_Tap(RadEvent e) {
    Toast('Drawer: ${e.Text}');
  }

  void AppBar1_Click(RadEvent e) {
    if (e.Action == 'search') {
      BottomNav1.selectedIndex = 1;
      showPage(1);
    } else {
      MsgBox('RAD IDE Flutter template', 'More');
    }
  }

  void Fab1_Click() {
    lstNews.addItem('New item|added at ${TimeOfDay.now().format(context)}|star');
    Toast('Item added');
  }

  void btnDetails_Click() {
    ShowForm('DetailsScreen', lstNews.count);
  }

  void txtSearch_Submitted(RadEvent e) {
    final q = txtSearch.text.trim().toLowerCase();
    lstResults.setItems(_words.where((w) => w.contains(q)));
  }

  void sldSize_Changed(RadEvent e) {
    lblSize.text = 'Text size: ${sldSize.value.round()}';
  }

  void btnSave_Click() {
    RadApp.data['user'] = txtUser.text;
    Toast('Saved ${txtUser.text} (news: ${swNews.checked ? 'on' : 'off'})');
  }

  void lstNews_Tap(RadEvent e) {
    Toast('tapped ${e.Index}');
  }
}
