// Form1 screen - the RatingBar component package on a phone form.
import 'package:flutter/material.dart';

import 'radapp.dart';

part 'form1_designer.dart';

class Form1Code extends Form1Designer {
  void Form1_Load() {}

  void rate1_ValueChanged() {
    lblOut.text = 'Rating: ${rate1.value}';
  }

  void btnSet_Click() {
    rate1.value = 2;
    lblOut.text = 'Set: ${rate1['Value']} of ${rate1.maxStars}';
  }
}
