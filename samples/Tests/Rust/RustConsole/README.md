# RustConsole

A Rust console application (cargo binary crate) used to test the IDE's Rust support.
Open the folder (or `Cargo.toml`) with File > Open Project: it opens in place, nothing is added to it.

What to try:

* **Ctrl+F5** runs the target chosen in the *Rust target* box (`bin: rustconsole`, `example: fizzbuzz`,
  `test: cli`, `test: all`): `cargo run`, `cargo run --example`, `cargo test ...`.
* **F5** debugs: put a breakpoint on `let total = r.area() + r.perimeter();` in `src/main.rs`. The IDE builds
  for the `x86_64-pc-windows-gnu` target and runs gdb, so you get locals (`r = Rect {width: 3, height: 4}`),
  the call stack and stepping.
* **IntelliSense** comes from rust-analyzer: type `HashMap::` or `r.` to get completions, hover `area` to see
  its docs, F12 goes to the definition, F2 renames `area` in `geometry.rs` and `main.rs` together.
  Inlay hints show the inferred types.
* **Errors**: write `let x: i32 = "text";` and save. The rustc error and the clippy warnings appear in the
  Error List. **Ctrl+.** offers quick fixes, for example *Import std::collections::HashSet*.
* **Test Explorer** (Test > Test Explorer) lists the unit tests (`tests::counts_words`,
  `geometry::tests::area` ...) and the integration test `tests/cli.rs`, and runs them.
* **Project > Manage Packages** runs `cargo add serde`, `cargo remove`, `cargo search` (crates.io).
