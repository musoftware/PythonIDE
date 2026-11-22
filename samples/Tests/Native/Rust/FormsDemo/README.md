# FormsDemo (Rust)

**rust-bridge (Rust), native build** - the forms of `C/FormsDemo` (menu, timer, progress bar, list, combo, check / radio
buttons in a group box, multi-line text, message box, Arabic text, a second form) with handlers written for the
normal GUI Bridge API. Build > Build Native Exe (or Publish) makes one standalone exe: FFI to radforms, cargo --release (opt-level z, LTO, panic abort), static CRT
(radide/deploy/native/rust_native.py, docs/NATIVE_BUILD.md).

**Try it:** F5 runs it through the GUI Bridge as usual; Build > Build Native Exe gives the exe in Publish\build\dist.
**Test:** `.venv\Scripts\python samples/Tests/Native/test_native_rust_go_lua.py` publishes, starts and drives it.

*Origin:* native Rust / Go / Lua builder agent (radforms FFI).
