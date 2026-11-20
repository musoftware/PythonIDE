# Testing samples (Test Explorer, coverage, formatting, refactoring)

One small project per test framework. Every project has **one test that fails on purpose**, so the Test
Explorer shows green, red (and sometimes skipped) results.

| Folder | Framework | Needs |
|---|---|---|
| PyCalc_Pytest | pytest + unittest, coverage.py, Format Document, F2 rename | Python (the IDE's own works) |
| Node_NodeTest | `node --test` | Node.js 20+ |
| JS_Jest | Jest (+ coverage) | Node.js, `npm install` once |
| Go_GoTest | `go test` (+ coverage) | Go |
| Rust_CargoTest | `cargo test` | Rust (rustup) |
| CSharp_XUnit | `dotnet test` (xUnit) | .NET SDK 9 |
| PHP_PHPUnit | PHPUnit | PHP 8.1+, `composer install` once |
| Dart_Test | `dart test` | Dart / Flutter SDK, `dart pub get` once |
| Java_JUnit | JUnit 5 (console launcher, downloaded on first run) | JDK 17+ |
| Ring_Tests | Ring convention: `test_*.ring`, `func test_*` | Ring |
| VB_Tests | VB convention: `Test*.bas`, `Sub Test*()`, `AssertEqual` | nothing |

**Try it:** File > Open the folder, then **Test > Test Explorer** (Ctrl+E, T) and **Run All** (the double
green arrow). Double-click a test to jump to it; the *Test Detail* tab shows the failure message.
Dependencies (`node_modules`, `vendor`, `.dart_tool`, `bin/obj`, `target`) are not kept here - install them
once as written in the table (Terminal window).
