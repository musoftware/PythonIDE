// Form1 screen - the layout sizes come from the Sizes bar (RadVariant of lib/radlayout.dart).
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'form1_designer.dart';

class Form1Code extends Form1Designer {
  void Form1_Load() {
    // CurrentSizes = the layout sizes that apply now
  }

  void btnGo_Click() {
    lblTitle.text = 'Sizes: ${CurrentSizes.join(', ')}';
  }
}
