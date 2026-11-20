# Rust in RAD IDE

## Pieces

| File | What it does |
| --- | --- |
| `radide/rust_tools.py` | Toolchain helpers with no Qt: finds the real rust-analyzer binary (`rustup which rust-analyzer`, not the `~/.cargo/bin` proxy), holds the rust-analyzer settings, reads `cargo metadata`, sets up the GNU-target environment, searches crates.io and parses libtest output. |
| `radide/lsp.py` | `server_command("rust")` uses `rust_tools.rust_analyzer()`. The rust-analyzer settings are sent as `initializationOptions` and in answer to `workspace/configuration`. One server runs per cargo workspace (`workspace_root`). The client also supports inlay hints, signature help with parameter docs, `experimental/serverStatus` and `$/progress`. |
| `radide/monaco_editor.py` + `radide/web/editor.html` | Hover, signature help and inlay hints come from the language server and are drawn by Monaco's own widgets. |
| `radide/features/rust_ide.py` | rust-analyzer diagnostics go to the Error List, including files that are not open. Also: the **Rust target** tool bar (combo, Reload, Clippy, Test), **Tools > Rust Settings...** (install rust-analyzer, clippy or check on save, inlay hints, rustfmt on save) and progress in the status bar. |
| `radide/foreign/cargo_project.py` | Opens plain Cargo projects and workspaces in place (`register_format`), runs targets, debugs with gdb, adds the cargo commands to the Native menu and connects the packages UI to cargo add, remove and search. |
| `radide/languages/rust_cargo.py` | New Project > Native > **Rust (Cargo)**: Console App, Library, GUI App (a RAD form made with the Rust GUI Bridge), egui Desktop App, Workspace. |
| `radide/testing` (`RustAdapter`) | Runs `cargo test` from the Test Explorer, workspace members included. |

## Installation

```
rustup component add rust-analyzer rust-src
rustup target add x86_64-pc-windows-gnu      # F5 debugging
```

To install the components from the IDE, use Tools > Rust Settings... > *Install rust-analyzer + rust-src*.

## Debugger choice

F5 builds the chosen target for **x86_64-pc-windows-gnu** with debug info. The linker is WinLibs gcc from
`%LOCALAPPDATA%\RADIDE\toolchains\mingw64`. The IDE then runs **gdb** over DAP (the same `gdb_session` that
the Rust GUI Bridge uses), which gives breakpoints, locals with Rust pretty printing, the call stack and
stepping.

MSVC builds write their debug info to PDB files, which gdb cannot read. Debugging an MSVC build needs LLDB
(CodeLLDB) or the Visual Studio debugger, and neither ships with the IDE. The GNU build is reliable and has
no other dependencies, so the IDE uses it. Ctrl+F5 (`cargo run`) still uses the default MSVC toolchain.

## Settings (QSettings)

* `rust/checkCommand`: `clippy` (the default) or `check`. This is what rust-analyzer runs on save.
* `rust/inlayHints`: turns the inlay hints on or off.
* `format/on_save` together with `format/on_save/rust`: runs rustfmt on save.
