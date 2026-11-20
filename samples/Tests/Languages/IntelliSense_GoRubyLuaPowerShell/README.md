# IntelliSense_GoRubyLuaPowerShell

**Language servers (round 7, radide/lsp_servers.py)** - one small file per language, each with an
unfinished line so you can see completion, hover and live diagnostics come from a real language server:

| File | Server | Try |
|---|---|---|
| `main.go` (+ `go.mod`) | gopls | line 11 `strings.` - the strings package list; hover `greet` |
| `main.rb` | ruby-lsp | line 9 `Gre` - `Greeter`; hover `Greeter` (first start builds a small bundle in `.ruby-lsp/`, ~20 s) |
| `main.lua` | lua-language-server | line 4 `string.` - byte, char, find...; warnings "unused local" |
| `main.ps1` | PowerShell Editor Services | line 3 `Get-Chil` - Get-ChildItem; PSScriptAnalyzer warnings |

**How to try:** Tools > Language Servers and Debuggers... shows what is installed and installs what is missing
(official releases into `%LOCALAPPDATA%\RADIDE\tools`, sha256 checked). Then File > Open each file here: the status
bar says "Language server: gopls (go)" etc. Perl: PLS needs fork(), which Windows perl does not have, so on
Windows the Perl plugin's own IntelliSense is used.
