// RAD IDE form helper for designed screens (written by the Flutter designer - do not edit, it is replaced).
//
// A TextFormField designed with validator rules is generated
//   validator: radValidate(const [RadRule.required(), RadRule.email()], custom: validateEmail),
// the rules run in order, the first message wins; `custom` (a handler of the screen's _events.dart file)
// runs last. A button event validate:<form> calls `<form>.currentState!.validate()`.
import 'package:flutter/widgets.dart';

/// The kind of a [RadRule].
enum RadRuleKind { required, email, minLength, maxLength, regex }

/// One validation rule of a designed TextFormField.
class RadRule {
  /// The field must not be empty (blank text counts as empty).
  const RadRule.required([this.message]) : kind = RadRuleKind.required, value = null;

  /// An e-mail address (empty text passes: combine with [RadRule.required]).
  const RadRule.email([this.message]) : kind = RadRuleKind.email, value = null;

  /// At least [length] characters (empty text passes).
  const RadRule.minLength(int length, [this.message]) : kind = RadRuleKind.minLength, value = length;

  /// At most [length] characters.
  const RadRule.maxLength(int length, [this.message]) : kind = RadRuleKind.maxLength, value = length;

  /// The whole text matches [pattern] (empty text passes).
  const RadRule.regex(String pattern, [this.message]) : kind = RadRuleKind.regex, value = pattern;

  final RadRuleKind kind;
  final Object? value;
  final String? message;

  static final _email = RegExp(r"^[\w.!#$%&'*+/=?^`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+$");

  /// The error message for [text], null when the rule passes.
  String? check(String? text) {
    final t = text ?? '';
    switch (kind) {
      case RadRuleKind.required:
        return t.trim().isEmpty ? (message ?? 'This field is required') : null;
      case RadRuleKind.email:
        return t.isNotEmpty && !_email.hasMatch(t.trim()) ? (message ?? 'Enter a valid e-mail address') : null;
      case RadRuleKind.minLength:
        final n = value as int;
        return t.isNotEmpty && t.length < n ? (message ?? 'Enter at least $n characters') : null;
      case RadRuleKind.maxLength:
        final n = value as int;
        return t.length > n ? (message ?? 'Enter at most $n characters') : null;
      case RadRuleKind.regex:
        if (t.isEmpty) return null;
        final m = RegExp(value as String).firstMatch(t);
        return m == null || m.start != 0 || m.end != t.length ? (message ?? 'Invalid format') : null;
    }
  }
}

/// A FormField validator running [rules] in order, then [custom].
FormFieldValidator<String> radValidate(List<RadRule> rules, {FormFieldValidator<String>? custom}) {
  return (value) {
    for (final r in rules) {
      final error = r.check(value);
      if (error != null) return error;
    }
    return custom?.call(value);
  };
}
