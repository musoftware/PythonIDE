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
