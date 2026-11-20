# Editor extras - test sample

What it shows: split editor, Diff tool, Hex editor, Snippets manager, macros and keymaps
(`radide/features/editor_extras.py`, `radide/web/editor_extras.js`, `radide/web/diff.html`).
The screenshots in `screenshots/` come from the automated tests (real display, `widget.grab()`).

## How to try it

| Feature | Steps |
| --- | --- |
| Split editor | Open `compare_left.bas`, then **Window > Split Editor Right** (or `Ctrl+\` in the editor) / **Split Editor Down** / **Remove Split**. Both views edit the same text. |
| Diff | **Tools > Compare (Diff) > Compare Files...** and pick `compare_left.bas` then `compare_right.bas`. Use **Next / Previous** (`Alt+F5` / `Shift+Alt+F5`), **Side by Side** on/off, **Revert Change ->** (copy left to right), **<- Accept Change** (copy right to left), **Save Left / Save Right**. Also: Compare Current File with Saved / Git HEAD / Clipboard / another file. |
| Hex editor | Open `sample.bin` (binary files open in the hex editor), or **File > Open in Hex Editor**. Type hex digits or (after `Tab`) text, `Ins` toggles insert mode, `Ctrl+F` find (`DE AD BE EF` or text), `F3` next, `Ctrl+G` go to offset (`0x100`, `100h`, `256`), `Ctrl+Z/Y`, `Ctrl+S`. The bottom bar is a data inspector (u8 ... f64, little endian). |
| Snippets | **Tools > Code Snippets Manager... > Import...** `python.code-snippets` (VS Code format: comments, several prefixes, `scope`). In a `.py` file type `forr` and pick it from IntelliSense: `Tab` moves through `${1:i}`, `${2:10}`, `$0`. **Edit > Insert Snippet...** picks one from a menu. |
| Macros | Open `macro_list.txt`, caret on `apple`, **Ctrl+Shift+R**, press `Home`, type `- `, press `Down`, **Ctrl+Shift+R** again. **Ctrl+Shift+Alt+P** runs it on the next line. **Tools > Macros > Macro Explorer** saves, renames, runs N times, imports `macros_example.json`. |
| Keymaps | **Tools > Options > Keyboard** (or **Tools > Keymap**): Visual Studio, VS Code, Vim, Emacs. Vim shows a status line (`--NORMAL--`), `:w` saves, `:vs` splits. Multi-cursor keys are the same in VS / VS Code / Emacs: `Ctrl+Alt+Up/Down`, `Alt+Click`, `Shift+Alt+drag`, `Shift+Alt+.` (next match), `Shift+Alt+;` (all matches), `Shift+Alt+,` (remove last), `Shift+Alt+I`. |

User snippets and macros are stored in `%LOCALAPPDATA%\RADIDE\editor`.
