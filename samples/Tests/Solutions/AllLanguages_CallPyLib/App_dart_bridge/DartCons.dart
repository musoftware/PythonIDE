import 'pylib_ref.dart' as PyLib;
Future<String> Test() async {
  final a = await PyLib.Add(2, 3);
  final g = await PyLib.Greet("Dart");
  return "$a|$g";
}
