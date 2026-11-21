# AsmLsp

Tests of the optional [asm-lsp](https://github.com/bergercookie/asm-lsp) language server support
(radide/asm_intel/lsp.py, docs/ASSEMBLY.md "asm-lsp (optional)").

| File | What |
|---|---|
| `test_asm_lsp.py` | the install plan (the pinned release's archives for Linux / macOS; on Windows the release tag built with cargo because the release has no Windows binary), the release metadata from the GitHub API (names + SHA-256 digests), a real download + verification + unpack of the Linux archive into a temporary folder (not run), RAD IDE's LSP client (`radide.lsp.LspClient`, `rad-asm-nasm`) with the server - the real asm-lsp when it is installed, else `standin_asm_lsp.py` - for hover and completion, `server_command()` finding `tools\asm-lsp\bin\asm-lsp.exe`, and the fallback (`asm/useAsmLsp = false`: no server, the built-in provider answers) |
| `standin_asm_lsp.py` | a tiny stdio language server that answers like asm-lsp (initialize, didOpen / didChange, hover, completion) |

Run: `python samples/Tests/Assembly/AsmLsp/test_asm_lsp.py` (QSettings organisation RADIDE-TEST, cleared).
Installing the real server: Tools > Language Servers... > asm-lsp > Install (Windows needs Rust: Tools > Toolchains).
