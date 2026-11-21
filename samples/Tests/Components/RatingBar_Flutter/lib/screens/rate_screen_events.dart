// RateScreen screen - event handlers (yours).
part of 'rate_screen.dart';

class RateScreenEvents extends RateScreenDesigner {
  int lastRating = -1;

  @override
  void onRate2ValueChanged() {
    lastRating = rate2.value;
  }
}
