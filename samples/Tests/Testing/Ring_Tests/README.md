# Ring_Tests

Tests the **Ring test convention** of the Test Explorer: files named `test_*.ring` (or `*_test.ring`),
every `func test_*` is a test; `assertEqual(expected, actual)` and `assertTrue(cond)` are provided (a
Ring error or failed assert = failed test). Other files loaded with `load "x.ring"` still work.

**Try it:** open the folder, Test > Run All Tests -> 1 passed, 1 failed. Needs Ring (C:\ring).
