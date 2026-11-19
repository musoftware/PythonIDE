import 'dart:io';
import 'pylib_ref.dart' as PyLib;
import 'perllib_ref.dart' as PerlLib;
import 'dartlib_ref.dart' as DartLib;

Future<void> main() async {
  print('DA ${await PyLib.Mul(6, 7)} ${await PyLib.Hello("Dart")}');
  print('DA ${await PerlLib.Add(2, 3)} ${await PerlLib.Stats([1, 2, 3])}');
  print('DA ${await DartLib.Range(2)} ${await DartLib.Shout("x")}');
  exit(0);
}
