# Go_GoTest

Tests the Test Explorer with **go test -json** (`TestXxx(t *testing.T)` functions) and Go **coverage**
(`-coverprofile`) in the editor gutter. `TestFailsOnPurpose` fails.

**Try it:** open the folder, Test > Run All Tests -> 2 passed, 1 failed; Run All Tests with Coverage and
open `calc.go` (the `Sign(0)` branch is red). Needs Go (PATH or %LOCALAPPDATA%\RADIDE\toolchains\go).
