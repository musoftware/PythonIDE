# Third-party components

RAD IDE's own code is under the MIT License (see `LICENSE`, © Musoftware - https://musoftwares.com).
It uses and bundles components that keep their own licenses:

| Component | Where | License |
| --- | --- | --- |
| PyQt6, PyQt6-WebEngine (Riverbank) | Python dependency | GPL v3 (or commercial) |
| Qt 6 / QtWebEngine (Chromium) | via PyQt6 | LGPL v3 / GPL, Chromium BSD-style |
| Monaco Editor | `radide/web/monaco/` | MIT |
| monaco-vim | `radide/web/monaco-vim/` | MIT |
| GrapesJS | `radide/web/grapes/` | BSD-3-Clause |
| emmet-monaco-es | `radide/web/emmet/` | MIT |
| Adminer | `radide/web/adminer/` | Apache 2.0 / GPL v2 |
| Bootstrap | `radide/web_site/templates/html-bootstrap/assets/vendor/bootstrap/` | MIT |
| Python packages in `requirements.txt` | Python dependencies | their own licenses (mostly MIT/BSD/Apache) |
| pypcode (angr) - Ghidra SLEIGH engine for Python, https://github.com/angr/pypcode | Python dependency (firmware disassembly) | BSD-2-Clause; bundled Ghidra SLEIGH + processor specs Apache 2.0; zlib Zlib |
| C166 / ST10 SLEIGH module (Keyhan Asadi), https://github.com/keyhana/c166-ghidra-module @ 24229d2 | `third_party/ghidra-processors/C166/` | MIT |
| RL78 SLEIGH module (Ilya Zhuravlev), https://github.com/xyzz/ghidra-rl78 @ 128b929 | `third_party/ghidra-processors/RL78/` | MIT |
| VS Code reference data derived from microsoft/vscode @ 733a998 (command ids, vscode.d.ts signatures, context keys, contribution-point schemas, their English descriptions) | `radide/vsx/reference/*.json`, `COVERAGE.md` | MIT (see below) |
| Packages the example projects declare (not included in the repo; downloaded by npm / pip / bundler when an example is built): Express, Expo / React Native (npm); Flask, Django, FastAPI, Uvicorn, pygame, arcade, Kivy, Ursina (pip); Sinatra, Rack, rackup, WEBrick (gems) | `samples/Examples/*/*/package.json`, `requirements.txt`, `Gemfile` | MIT / BSD-3-Clause (each its own) |

**Important when you distribute RAD IDE as a program (e.g. an installer):** PyQt6 is GPL v3, so a
distribution that includes PyQt6 must as a whole respect the GPL v3 (source available, same freedoms).
The MIT license of RAD IDE's own code is compatible with that. The credit to Musoftware
(https://musoftwares.com) required by `LICENSE` must stay in every copy.

## Ghidra (via pypcode)

The firmware disassembler (`radide/firmware/analysis/sleigh.py`) uses Ghidra's SLEIGH library and processor
specifications as shipped inside the `pypcode` wheel. Ghidra is a software reverse engineering framework
developed by the National Security Agency (https://github.com/NationalSecurityAgency/ghidra), licensed under the
Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0); see `pypcode/docs/ghidra/LICENSE` and
`NOTICE` in the installed package. RAD IDE does not copy Ghidra files into this repository. The C166 and RL78
SLEIGH modules in `third_party/ghidra-processors/` keep their MIT `LICENSE` files and a README with source and
commit; they are compiled on first use with pypcode's SLEIGH compiler.

## Native .NET / Java builds (tools only, nothing vendored)

`radide/deploy/native/dotnet_winforms.py` and `java_native.py` contain no third-party code. They run tools of the
user's machine: the .NET SDK / Roslyn compiler (MIT, .NET Foundation) - or, without an SDK, the
`Microsoft.Net.Compilers.Toolset` NuGet package (MIT) downloaded from nuget.org into
`%LOCALAPPDATA%\RADIDE\tools\roslyn` - and the JDK tools javac / jdeps / jlink / jpackage (OpenJDK, GPL v2 with the
Classpath Exception). A standalone C# program contains the .NET runtime (MIT); a Java program contains a
jlink-made OpenJDK runtime with its `legal` folder. See docs/NATIVE_BUILD.md.

## FreeBASIC (VB6 native build, tool downloaded on use)

`radide/deploy/native/vb6_freebasic.py` translates VB6 projects to FreeBASIC and compiles them with the FreeBASIC
compiler 1.10.1 for Windows (https://www.freebasic.net, https://sourceforge.net/projects/fbc/), downloaded from the
official SourceForge page into `%LOCALAPPDATA%\RADIDE\tools\freebasic-win` on first use (SHA-256 checked); nothing of
it is copied into this repository. The compiler is GPL v2 or later; the FreeBASIC runtime library (libfb) that is
statically linked into a published program is LGPL v2.1 or later **with a static-linking exception** ("you may link
this library with independent modules to produce an executable, regardless of the license terms of these
independent modules"), so programs may be distributed under any licence. The bundled MinGW-w64 / GCC runtime
pieces linked by the compiler (crt, libgcc) carry the GCC Runtime Library Exception. The VB runtime the generated
code includes (`radide/deploy/native/vb6fb/rt/*.bi`) is RAD IDE's own code (MIT). MyFbFramework
(https://github.com/XusinboyBekchanov/MyFbFramework, LGPL with a static-link exception) was evaluated but is not
used or vendored.

## Lua 5.4 (Lua native build, source downloaded on use)

`radide/deploy/native/script_embed.py` builds Lua projects as one exe that embeds the Lua 5.4.9 interpreter
(https://www.lua.org, Copyright (C) 1994-2026 Lua.org, PUC-Rio, **MIT License**). The official source tarball
`https://www.lua.org/ftp/lua-5.4.9.tar.gz` (SHA-256 `2335b6c582a52654f94612bf10d2f4672805d05329aa6568b1d8cd9e5c6fb8e6`)
is downloaded on first use into `%LOCALAPPDATA%\RADIDE\toolchains\lua-src` and compiled there; nothing of it is
copied into this repository. A published Lua program contains the compiled Lua library: its MIT notice (in
`lua.h`) must be kept with the program's documentation when it is distributed.

## Native Rust / Go builds (tools only, nothing vendored)

`radide/deploy/native/rust_native.py` and `go_native.py` contain no third-party code; they run the user's Rust
toolchain (cargo / rustc, MIT or Apache 2.0; the Rust standard library linked into a program is MIT / Apache 2.0)
and Go toolchain (BSD-3-Clause; the Go runtime linked into a program is BSD-3-Clause), with MinGW-w64 gcc (GCC
Runtime Library Exception) or Visual C++ as the linker.
## Node.js / esbuild (JavaScript / TypeScript native build, tools only)

`radide/deploy/native/node_sea.py` contains no third-party code. A published JavaScript / TypeScript program is a
copy of the official Node.js binary (https://nodejs.org, **MIT License**; it includes V8, libuv, OpenSSL, ICU and
other libraries under their own licences, listed in Node's `LICENSE`) with the program added as a single
executable application; Node's `LICENSE` is copied next to the exe as `Node.js-LICENSE.txt`. Node.js is the one
installed on the machine or the LTS zip downloaded from nodejs.org (SHA-256 from the release's `SHASUMS256.txt`)
into `%LOCALAPPDATA%\RADIDE\toolchains\node`. npm packages are bundled with esbuild (https://esbuild.github.io,
**MIT License**), downloaded on use from the official npm package `@esbuild/win32-x64` (SHA-512 integrity checked)
into `%LOCALAPPDATA%\RADIDE\toolchains\esbuild`; the bundled packages keep their own licences.

## VS Code reference data (derived from microsoft/vscode)

`radide/vsx/reference/` holds machine-readable inventories extracted with `radide/vsx/reference/tools/extract.js`
from Visual Studio Code - Open Source ("Code - OSS"), https://github.com/microsoft/vscode, commit
`733a99842b0e0e14c3593dfab31fff2035478ba0` (version 1.148.0), plus `vscode.d.ts` of releases 1.90-1.147 for the
"since" column: built-in command ids with their titles, keybindings and argument descriptions, the vscode.d.ts API
declarations, RawContextKey names / descriptions and contribution-point JSON schemas. Some host code
(`radide/vsx/host/types.js`, `commands.js`, `treeview.js`) re-implements the documented behaviour of the
corresponding VS Code classes; no VS Code source file is copied. `usage_top_extensions.json` contains only
extension / command ids and counts gathered from public Open VSX manifests.

    MIT License

    Copyright (c) 2015 - present Microsoft Corporation

    Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
    documentation files (the "Software"), to deal in the Software without restriction, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
    permit persons to whom the Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all copies or substantial portions of
    the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
    THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
    TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
