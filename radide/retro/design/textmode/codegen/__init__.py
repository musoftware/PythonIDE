"""Code generators of the text-mode designer: basic (FreeBASIC / QuickBASIC / QBasic), pascal (Free Pascal /
Turbo Pascal, Crt), c (OpenWatcom / Turbo C / DJGPP) and asm (16-bit .COM, MASM / TASM / JWasm syntax).
Each has ``generate(screens, old_text="") -> (source, warnings)`` and ``handler_line(text, key)``."""
