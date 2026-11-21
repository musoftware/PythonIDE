// SignUp screen - event handlers. This file is yours: the Flutter designer only adds new handler
// stubs. Named widgets are fields (txtEmail.text, chkRemember); call setState(() { ... }) after
// changing values shown on the screen. Extra imports: Screen properties > Imports.
part of 'sign_up.dart';

class SignUpEvents extends SignUpDesigner {
  /// Set by onSubmit (read by the widget test).
  String? submitted;

  @override
  String? checkPhone(String? value) {
    return (value ?? '').startsWith('000') ? 'Not a real number' : null;
  }

  @override
  String? checkPromo(String? value) {
    final v = value ?? '';
    return v.isEmpty || v == 'RAD2026' ? null : 'Unknown promo code';
  }

  @override
  void planChanged(String? value) {}

  @override
  void onSubmit() {
    setState(() => submitted = '${txtName.text} <${txtEmail.text}> plan=$rdoPlan');
  }
}
