# Rust_CargoTest

Tests the Test Explorer with **cargo test**: `#[test]` functions inside `mod tests`, an `#[ignore]` test
(shown as skipped) and a failing `assert_eq!` (its panic message is in Test Detail).

**Try it:** open the folder, Test > Run All Tests -> 1 passed, 1 failed, 1 skipped. The first run compiles
(target/ is created - not kept in the sample). Needs Rust (rustup).
