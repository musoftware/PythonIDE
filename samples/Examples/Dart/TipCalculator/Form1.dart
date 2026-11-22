// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// Tip Calculator - a Dart program with a RAD IDE form (GUI Bridge: the IDE draws the form, Dart runs the code).
// Shows: TextBox, ComboBox, TrackBar, NumericUpDown, CheckBox, ListBox, a MenuStrip, number parsing and
// validation, string formatting, live updates (ValueChanged events) and a second form (Form2, About).
import 'radgui.dart';

const _symbols = {'EGP': 'E£', 'USD': r'$', 'EUR': '€', 'SAR': 'SR'};

void Form1_Load(RadEvent e) {
  Rad.set('cboCurrency', 'Text', 'EGP');
  _calculate(addToHistory: false);
}

void cmdCalc_Click(RadEvent e) => _calculate(addToHistory: true);

void trkTip_ValueChanged(RadEvent e) {
  Rad.set('lblTipValue', 'Caption', '${Rad.get('trkTip', 'Value')} %');
  _calculate(addToHistory: false);
}

void nudPeople_ValueChanged(RadEvent e) => _calculate(addToHistory: false);

void chkRound_CheckedChanged(RadEvent e) => _calculate(addToHistory: false);

void cboCurrency_SelectedIndexChanged(RadEvent e) => _calculate(addToHistory: false);

void mnuFileClear_Click(RadEvent e) => Rad.call('lstHistory', 'Clear');

void mnuFileExit_Click(RadEvent e) => Rad.end();

void mnuHelpAbout_Click(RadEvent e) => Rad.show('Form2');

/// Reads the inputs, shows tip / total / per person; optionally adds a line to the history list.
void _calculate({required bool addToHistory}) {
  final bill = double.tryParse(Rad.get('txtBill', 'Text').trim().replaceAll(',', '.'));
  if (bill == null || bill < 0) {
    Rad.set('lblResult', 'Caption', 'Type a valid bill amount.');
    if (addToHistory) Rad.msgbox('The bill amount must be a number, e.g. 250 or 99.5');
    return;
  }
  final tipPercent = Rad.getNum('trkTip', 'Value').toInt();
  final people = Rad.getNum('nudPeople', 'Value').toInt().clamp(1, 1000);
  final roundUp = Rad.get('chkRound', 'Value') == '1'; // CheckBox.Value: 1 = checked
  final currency = Rad.get('cboCurrency', 'Text');
  final symbol = _symbols[currency] ?? currency;

  final tip = bill * tipPercent / 100;
  final total = bill + tip;
  var each = total / people;
  if (roundUp) each = each.ceilToDouble();

  final text = 'Tip $symbol${tip.toStringAsFixed(2)}  Total $symbol${total.toStringAsFixed(2)}  '
      'Each $symbol${each.toStringAsFixed(2)}';
  Rad.set('lblResult', 'Caption', text);
  if (addToHistory) {
    Rad.call('lstHistory', 'AddItem', ['$symbol${bill.toStringAsFixed(2)} + $tipPercent% / $people -> $text']);
    print('calc: $text'); // plain output goes to the IDE Output window
  }
}
