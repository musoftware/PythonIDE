# Infineon C166 / C167 / ST10 SLEIGH module (vendored)

* Source: <https://github.com/keyhana/c166-ghidra-module> (Ghidra processor module by Keyhan Asadi)
* Commit: `24229d2768cadee65b3951f316bf1e9a0604420f` (2026-11-14)
* License: MIT (see `LICENSE` in this folder)
* Files taken: `data/languages/c166.slaspec`, `c166.sinc`, `c166.cspec`, `c166cr.pspec`, `c167cs.pspec`,
  `c166.ldefs` - unchanged. Not taken: the Java analyzers / p-code injectors, Ghidra scripts, tests and the
  Infineon instruction-set manual PDF.

## How RAD IDE uses it

`radide/firmware/analysis/sleigh_build.py` copies these files into a cache folder
(`%LOCALAPPDATA%\RADIDE\sleigh\C166-<hash>`), compiles `c166.slaspec` to `c166.sla` with the SLEIGH compiler that
ships in the `pypcode` wheel (`pypcode/bin/sleigh[.exe]`) on first use, and loads the language
`C166:LE:16:default` through pypcode. No Java and no Ghidra installation are needed.

Build-time adaptation (applied to the cached copy, the files here stay as upstream): Ghidra's Java SLEIGH compiler
accepts statements after `export` in a constructor body, the C++ compiler in pypcode does not. Eight constructors
(`[Rw+]` post-increment addressing) are rewritten so that the `export` is the last statement (the address is
taken before the increment, exactly as upstream intends). See `_fix_export_order()` in `sleigh_build.py`.

The upstream Java parts (DPP paging of `mem` operands, `[Rw+#data16]` addressing, switch tables) are user
operations (`GetPagedOffset`, `c166_reg_offset_addr`, `segment`) in the SLEIGH spec; RAD IDE resolves them itself
in `radide/firmware/analysis/sleigh.py` (DPP0-3 values tracked from the code, reset values 0/1/2/3, EXTP / EXTPR /
EXTS / EXTSR prefixes).
