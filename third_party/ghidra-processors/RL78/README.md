# Renesas RL78 SLEIGH module (vendored)

* Source: <https://github.com/xyzz/ghidra-rl78> (Ghidra processor module by Ilya Zhuravlev)
* Commit: `128b929728a15b858996b4f4261038341b50cb88` (2023-07-02)
* License: MIT (see `LICENSE` in this folder)
* Files taken: `data/languages/rl78.slaspec.in` (upstream Jinja2 template), `rl78.cspec`, `rl78.pspec`,
  `rl78.ldefs` - unchanged.
* Generated: `data/languages/rl78.slaspec` = `rl78.slaspec.in` rendered with Jinja2 (what upstream's `build.sh`
  does with `j2`), so RAD IDE needs no Jinja2 at run time.

## How RAD IDE uses it

`radide/firmware/analysis/sleigh_build.py` compiles `rl78.slaspec` to `rl78.sla` with the SLEIGH compiler from the
`pypcode` wheel on first use (cached in `%LOCALAPPDATA%\RADIDE\sleigh\RL78-<hash>`) and loads the language
`RL78:LE:16:default` through pypcode. No Java and no Ghidra installation are needed.
