# FormsDemo (TypeScript)

**typescript, native build (Node.js single executable)** - the forms of `C/FormsDemo` with handlers for the normal GUI
Bridge API, plus an npm package (`rad-shout`, vendored in `vendor/`: `npm install` puts it in node_modules), a CommonJS
module (`Helpers`), a global-script module (`Strings`) and `fs`. Build > Build Native Exe (or Publish) makes ONE exe that
is Node.js (V8) with the program inside and a native radforms forms host - no Python (radide/deploy/native/node_sea.py,
docs/NATIVE_BUILD.md).

**Try it:** `npm install`, then F5 (GUI Bridge) or Build > Build Native Exe.
**Test:** `.venv\Scripts\python samples/Tests/Native/test_native_rust_go_lua.py` (`RAD_TEST_ONLY=JS` for this part).

*Origin:* native Rust / Go / Lua / Node builder agent (radforms).
