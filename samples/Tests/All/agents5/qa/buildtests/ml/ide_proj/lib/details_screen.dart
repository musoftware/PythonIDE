// DetailsScreen - opened by ShowForm('DetailsScreen', value); FormArgs is that value.
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'details_screen_designer.dart';

class DetailsScreenCode extends DetailsScreenDesigner {
  void DetailsScreen_Load() {
    final user = RadApp.data['user'] ?? 'guest';
    lblInfo.text = 'Hello $user!\nThe home page has ${FormArgs ?? 0} news items.';
  }

  void btnBack_Click() {
    CloseForm();
  }
}
