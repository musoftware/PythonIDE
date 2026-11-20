# RustWorkspace

A cargo workspace with two member crates:

* `app` - a binary crate that uses the library;
* `core` - a library crate (`greet`, `Stats`) with unit tests.

Open the workspace folder: the Solution Explorer shows each member as a project (with its Dependencies,
`src/` and `Cargo.toml`), plus the root files. `rustworkspace_app` is the startup project.

* Ctrl+F5 runs the app (`cargo run -p rustworkspace_app`) and F5 debugs it.
* One rust-analyzer serves the whole workspace: F12 on `greet` in `app/src/main.rs` opens `core/src/lib.rs`,
  and F2 renames across both crates.
* The `test: workspace` target runs `cargo test --workspace`.
