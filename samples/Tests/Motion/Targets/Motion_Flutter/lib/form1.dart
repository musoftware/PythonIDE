// Form1 screen - animations come from the Animations window (lib/radmotion.dart plays them).
// BeginAnimation('fx1') / StopAnimation('fx1') / SetVisible('lblInfo', false)
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'form1_designer.dart';

class Form1Code extends Form1Designer {
  bool _hidden = false;

  void btnHide_Click() {
    _hidden = !_hidden;
    SetVisible('lblInfo', !_hidden);
  }
}
