# VB_Tests

Tests the **VB test convention** of the Test Explorer: a module whose name starts or ends with "Test"
(`TestMath.bas`), every `Public Sub TestXxx()` is a test. Built-in helpers: `AssertEqual expected, actual
[, message]`, `Assert` / `AssertTrue` / `AssertFalse condition`, `Fail message`. The project's other modules
(`MathLib.bas`) are loaded, so tests call their functions.

**Try it:** open the folder, Test > Run All Tests -> 2 passed, 1 failed
(`2 + 2: expected <5> but was <4>`). Needs nothing but the IDE.
