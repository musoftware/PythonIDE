# Dart_Test

Tests the Test Explorer with **dart test --reporter json**: `group(...)` + `test(...)` names, durations
and `expect` failures. `fails on purpose` fails.

**Try it:** run `dart pub get` once (creates .dart_tool - not kept), open the folder, Test > Run All
Tests -> 2 passed, 1 failed. Flutter projects (`sdk: flutter`) use `flutter test --machine` and get coverage.
